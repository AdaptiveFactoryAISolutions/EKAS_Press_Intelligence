"""Owned subprocess execution for durable native jobs. Never shells out user text."""
import argparse
import json
from contextlib import nullcontext
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from uuid import uuid4
from .bootstrap import activate
NATIVE_SOURCE=activate()
from .jobs import JobStore,JobConflict,TERMINAL,process_identity
from .logs import capture_log
from .thread_limits import apply_thread_limit,THREAD_VARIABLES

REPO=Path(NATIVE_SOURCE['repository'])


def signal_verified_worker(pid,start,signum):
    """Signal the persisted exact process, never a numeric PID after reuse."""
    if not start:return False
    fd=None
    try:
        fd=os.pidfd_open(pid)
        if process_identity(pid)!=start:return False
        signal.pidfd_send_signal(fd,signum)
        return True
    except (ProcessLookupError,OSError):return False
    finally:
        if fd is not None:os.close(fd)


def export_source(store,ident):
    if ident=='historianrca':
        return {'id':ident,'public_path':str(REPO/'vendor'/'HistorianRCA'),'private_path':None,
                'scoring_status':'EXTERNAL_SCORING_REQUIRED','source':'original'}
    return store.dataset(ident)


def export_plant(store,parent):
    """Resolve native identity from protected generation configuration/lineage."""
    seen=set()
    while True:
        ident=parent['id']
        if ident in seen:raise ValueError('DATASET_LINEAGE_INVALID: cycle in registered lineage')
        seen.add(ident)
        if ident=='historianrca':return 'heated_stirred_tank'
        if parent.get('private_path'):
            path=Path(parent['private_path'])/'metadata'/'manifest.json'
            if path.is_symlink() or not path.is_file() or path.stat().st_size>4_000_000:
                raise ValueError('PLANT_IDENTITY_UNAVAILABLE: bounded protected native manifest required')
            unit=json.loads(path.read_text())['config']['unit']
            if not isinstance(unit,str) or not unit:raise ValueError('PLANT_IDENTITY_UNAVAILABLE: native unit missing')
            return unit
        previous=parent.get('parent_dataset_id') or parent.get('source_dataset_id')
        if not previous:raise ValueError('PLANT_IDENTITY_UNAVAILABLE: registered generation lineage required')
        parent=export_source(store,previous)


def run_job(directory,ident):
    store=JobStore(directory);job=store.get(ident)
    if job['state']!='running':return 1
    store.heartbeat(ident,pid=os.getpid(),process_start=process_identity(os.getpid()))
    stopping=threading.Event()
    def stopped(*_):
        stopping.set()
        raise SystemExit(130)
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
    def watch():
        while not stopping.wait(1):
            try:
                current=store.get(ident)
                if current['state']=='cancel_requested':os.kill(os.getpid(),signal.SIGTERM);return
                if current['state'] in TERMINAL:return
                from .resource_guard import memory_pressure
                try:pressure=memory_pressure()
                except ValueError as exc:
                    pressure={'code':'RESOURCE_CONFIG_INVALID','message':str(exc)}
                if pressure:
                    store.fail(ident,pressure['code'],pressure['message'],result={'resource_guard':pressure})
                    os.kill(os.getpid(),signal.SIGTERM);return
                store.heartbeat(ident)
            except Exception:
                # An expired lease will be visibly interrupted, never successful.
                return
    thread=threading.Thread(target=watch,daemon=True);thread.start()
    target=Path(directory)/'artifacts'/ident
    try:
        submission=None;adjudication=None
        from .line_source import check_binding
        check_binding(store.line_binding(ident))
        if job['operation']=='independent_evaluation':
            from .evaluation import execute_evaluation
            parameters=dict(job['parameters']);dataset_id=parameters.pop('dataset_id',None)
            if not dataset_id or dataset_id=='historianrca':raise ValueError('EXTERNAL_SCORING_REQUIRED: local generated key required')
            registered=store.dataset(dataset_id)
            if not registered.get('private_path') or Path(registered['private_path']).resolve()!=Path(parameters['dataset_dir']).resolve():
                raise ValueError('DATASET_MISMATCH: evaluation key is not the registered private dataset')
            frozen=store.submission(dataset_id)
            if frozen['judgments']:raise ValueError('IMMUTABLE_OR_CONFLICT: existing judgments cannot be replaced')
            parameters.update(submission_csv=frozen['csv'],submission_sha256=frozen['sha256'])
            result=execute_evaluation(parameters,target,REPO,lambda p:store.heartbeat(ident,p))
            if result.get('submission_sha256')!=frozen['sha256']:raise ValueError('EVALUATION_DIGEST_MISMATCH: evaluation is not bound to frozen claims')
            adjudication=(dataset_id,frozen['sha256'],result['judgments'])
            result.update(dataset_id=dataset_id,evaluator_only=True)
            result['provider_proposal_status']=result.get('status')
            result['status']='INDEPENDENT_JUDGMENTS_RECORDED'
        elif job['operation']=='observability_export':
            from .observability import execute_observability
            parameters=dict(job['parameters']);dataset_id=parameters.pop('dataset_id',None)
            if not dataset_id:raise ValueError('DATASET_REQUIRED: registered export dataset required')
            parent=export_source(store,dataset_id)
            if Path(parameters.get('dataset_dir','')).resolve()!=Path(parent['public_path']).resolve():
                raise ValueError('DATASET_MISMATCH: export input is not registered public evidence')
            if set(parameters)-{'dataset_dir','profile'}:raise ValueError('INVALID_PARAMETERS: unknown export option')
            plant=export_plant(store,parent)
            result=execute_observability(dict(parameters,plant=plant),target,REPO,lambda p:store.heartbeat(ident,p))
            result.update(source_dataset_id=dataset_id,observability_profile=parameters['profile'])
        elif job['operation']=='blind_analysis':
            from .analysis import execute_analysis,validate_submission
            parameters=dict(job['parameters']);dataset_id=parameters.pop('dataset_id',None)
            if not parameters.get('qualification_probe'):
                if not dataset_id:raise ValueError('DATASET_REQUIRED: registered analysis dataset required')
                source=REPO/'vendor'/'HistorianRCA' if dataset_id=='historianrca' else Path(store.dataset(dataset_id)['public_path'])
                if source.resolve()!=Path(parameters['dataset_dir']).resolve():raise ValueError('DATASET_MISMATCH: analysis input is not the registered public dataset')
            result=execute_analysis(parameters,target,REPO,lambda p:store.heartbeat(ident,p))
            if not result.get('qualification_probe'):
                path=target/'submission.csv'
                if path.is_symlink() or not path.is_file() or path.stat().st_size>4_000_000:
                    raise ValueError('INVALID_AGENT_SUBMISSION: bounded regular submission artifact required')
                csv=path.read_text(encoding='utf-8');validated=validate_submission(csv)
                if validated['sha256']!=result.get('submission',{}).get('sha256'):
                    raise ValueError('INVALID_AGENT_SUBMISSION: frozen digest does not match submission artifact')
                submission=(dataset_id,csv)
                result['dataset_id']=dataset_id
        else:
            from .engine import execute
            parameters=dict(job['parameters']);parameters.pop('dataset_id',None)
            result=execute(job['operation'],parameters,target,REPO,
                           progress=lambda phase:store.heartbeat(ident,phase))
        binding=store.line_binding(ident)
        if binding:
            result['line_setup']=binding
            if result.get('dataset'):result['dataset']=dict(result['dataset'],name='Generic 1,500-ton ten-station line',line_setup=binding)
        result['worker_configuration']={'requested_blas_threads':os.environ.get('EKAS_NATIVE_BLAS_THREADS'),
                                        'blas_environment':{name:os.environ.get(name) for name in THREAD_VARIABLES}}
        if store.get(ident)['state']=='cancel_requested':store.cancelled(ident);return 130
        if result.get('passed') is False:
            engineering_failed=(result.get('engineering_acceptance') or {}).get('passed') is False
            store.fail(ident,'PHYSICS_VALIDATION_FAILED' if engineering_failed else 'NATIVE_VALIDATION_FAILED',
                       'Native or private engineering validation did not pass; artifacts remain unqualified',result)
            return 1
        dataset=None
        if result.get('public_directory') and result.get('dataset'):
            public=(target/result['public_directory']).resolve()
            if not public.is_relative_to(target.resolve()):raise ValueError('Native artifact path escaped job directory')
            private=target/'private';parent=None
            if job['operation']=='make_challenge':
                source=Path(job['parameters']['dataset_dir']).resolve()
                parent=next((d for d in store.datasets() if d.get('private_path') and Path(d['private_path']).resolve()==source),None)
                if parent is None:raise ValueError('CHALLENGE_PARENT_UNAVAILABLE: registered source dataset required')
                private=Path(parent['private_path'])
            if job['operation']=='observability_export':
                parent=export_source(store,job['parameters']['dataset_id'])
                private=Path(parent['private_path']) if parent.get('private_path') else None
            dataset={'id':ident,'label':result['dataset'].get('name',ident),'source':'generated',
                     'status':'NATIVE_VALIDATED' if result.get('passed') is True and result.get('validation_performed',True) else 'UNVALIDATED',
                     'scoring_status':'LOCAL_GENERATED_KEY' if private is not None and (private/'metadata'/'ground_truth.json').exists() else 'EXTERNAL_SCORING_REQUIRED',
                     'public_path':str(public),'private_path':str(private) if private is not None else None,
                     'job_id':ident,'metadata':result['dataset']}
            if parent is not None:dataset['parent_dataset_id']=parent['id']
            if job['operation']=='observability_export':
                dataset.update(source='observability_export',source_dataset_id=parent['id'],observability_profile=result['profile'],
                               plant=plant,scoring_status=parent['scoring_status'],status='UNVALIDATED',
                               information_restriction=result['profile']=='sparse',same_physical_run=True,resimulated=False)
                dataset['metadata']=dict(dataset['metadata'],observability_profile=result['profile'],source_dataset_id=parent['id'],same_physical_run=True,resimulated=False)
            result['dataset_id']=ident
        store.finish(ident,result,dataset=dataset,submission=submission,adjudication=adjudication)
        return 0
    except (KeyboardInterrupt,SystemExit):
        # Native/provider context managers have now unwound and cleaned owned
        # children. Only then may cancellation release the single-worker slot.
        try:store.cancelled(ident)
        except JobConflict:pass
        raise
    except Exception as exc:
        message=str(exc)
        code=message.split(':',1)[0] if ':' in message and message.split(':',1)[0].isupper() else 'NATIVE_EXECUTION_FAILED'
        # Detailed stack trace belongs only to the owned private log.
        import traceback;traceback.print_exc()
        try:store.fail(ident,code,message)
        except JobConflict:pass
        return 1
    finally:stopping.set();thread.join(timeout=2)


class JobManager:
    def __init__(self,directory):
        self.store=JobStore(directory);self.identity=str(uuid4());self.stop=threading.Event()
        self.thread=None;self.process=None
        self.orphan_signalled=set()

    def start(self):
        self.store.recover()
        if self.thread and self.thread.is_alive():return
        self.thread=threading.Thread(target=self._loop,daemon=True);self.thread.start()

    def _loop(self):
        while not self.stop.wait(.1):
            self._cancel_orphans()
            self.store.recover()
            job=self.store.claim(self.identity)
            if job is None:continue
            logs=self.store.directory/'logs';logs.mkdir(exist_ok=True)
            with nullcontext(logs/(job['id']+'.log')) as log:
                env=dict(os.environ,PYTHONUNBUFFERED='1')
                try:threads=apply_thread_limit(env)
                except ValueError as exc:
                    self.store.fail(job['id'],'THREAD_CONFIG_INVALID',str(exc));continue
                runtime=env.get('EKAS_NATIVE_RUNTIME')
                if runtime:
                    source=Path(runtime).resolve()/'src'
                    if not (source/'historiansim'/'pipeline.py').is_file():
                        self.store.fail(job['id'],'INVALID_NATIVE_RUNTIME','Prepared native runtime is unavailable');continue
                    # Bootstrap verifies and adds native source after trusted
                    # imports; never let unverified siblings shadow dependencies.
                    env['PYTHONPATH']=str(REPO/'src')
                try:
                    self.process=subprocess.Popen([sys.executable,'-m','ekas_press_intelligence.native.worker',
                        '--state',str(self.store.directory),'--job',job['id']],cwd=REPO,env=env,
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
                except OSError as exc:
                    self.store.fail(job['id'],'WORKER_START_FAILED',str(exc));continue
                owned=self.process;start=process_identity(owned.pid)
                self.store.heartbeat(job['id'],phase=f'Native worker started; BLAS threads={threads}',pid=owned.pid,process_start=start)
                def log_failed(error,ident=job['id'],process=owned,identity=start,store=self.store):
                    try:store.record_log_failure(ident,error['message'])
                    finally:signal_verified_worker(process.pid,identity,signal.SIGTERM)
                log_reader=threading.Thread(target=capture_log,args=(owned.stdout,log),kwargs={'on_error':log_failed},daemon=True)
                log_reader.start()
                while self.process.poll() is None:
                    if self.stop.wait(.2):
                        # Shutdown owns exactly this subprocess group, not other sessions.
                        self.store.request_cancel(job['id']);self._signal_owned(signal.SIGTERM)
                        try:self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:self._signal_owned(signal.SIGKILL);self.process.wait()
                        break
                    current=self.store.get(job['id'])
                    if current['state']=='cancel_requested':
                        self._signal_owned(signal.SIGTERM)
                        try:self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:self._signal_owned(signal.SIGKILL);self.process.wait()
                        break
                log_reader.join(timeout=3)
                current=self.store.get(job['id'])
                if current['state'] not in TERMINAL:
                    if current['state']=='cancel_requested':self.store.cancelled(job['id'])
                    else:self.store.fail(job['id'],'WORKER_EXITED',f'Owned worker exited with status {self.process.returncode}')
                self.process=None

    def _signal_owned(self,signum):
        try:os.killpg(self.process.pid,signum)
        except ProcessLookupError:pass  # Owned child exited between poll and kill.

    def _cancel_orphans(self):
        """Cancel a surviving worker after manager restart without trusting a PID."""
        for job in self.store.cancellation_targets():
            pid=job['pid'];start=job['process_start'];identity=(pid,start)
            if not start or identity in self.orphan_signalled:continue
            if self.process is not None and self.process.pid==pid:continue
            if signal_verified_worker(pid,start,signal.SIGTERM):self.orphan_signalled.add(identity)

    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=8)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--state',required=True);parser.add_argument('--job',required=True)
    args=parser.parse_args();apply_thread_limit(os.environ);raise SystemExit(run_job(args.state,args.job))
