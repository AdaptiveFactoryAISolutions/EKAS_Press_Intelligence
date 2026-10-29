import time


def test_actual_native_worker_and_restart(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore
    from ekas_press_intelligence.native.worker import JobManager
    store=JobStore(tmp_path)
    job=store.create('describe_process',{'plant':'heated_stirred_tank'})
    manager=JobManager(tmp_path);manager.start()
    try:
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            current=store.get(job['id'])
            if current['state'] in ('succeeded','failed','interrupted'):break
            time.sleep(.05)
        assert current['state']=='succeeded',current
        assert 'TK-101' in str(current['result'])
    finally:manager.close()
    assert JobStore(tmp_path).get(job['id'])['state']=='succeeded'


def test_completed_registration_is_atomic(tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore
    s=JobStore(tmp_path);job=s.create('generate',{});s.claim('worker')
    s.finish(job['id'],{'dataset_id':job['id']},dataset={'id':job['id'],'source':'generated'})
    assert s.dataset(job['id'])['source']=='generated'
    assert s.get(job['id'])['state']=='succeeded'


def test_challenge_retains_generated_parent_private_key(tmp_path,monkeypatch):
    from ekas_press_intelligence.native.jobs import JobStore
    from ekas_press_intelligence.native.worker import run_job
    import ekas_press_intelligence.native.engine as engine
    private=tmp_path/'parent/private';(private/'metadata').mkdir(parents=True)
    (private/'metadata/ground_truth.json').write_text('{}')
    store=JobStore(tmp_path/'state')
    store.register_dataset('parent',{'id':'parent','private_path':str(private),'scoring_status':'LOCAL_GENERATED_KEY'})
    job=store.create('make_challenge',{'dataset_dir':str(private)})
    store.claim('test')
    monkeypatch.setattr(engine,'execute',lambda *a,**kw:{'public_directory':'public','dataset':{'name':'challenge'}})
    assert run_job(store.directory,job['id'])==0
    data=store.dataset(job['id'])
    assert data['private_path']==str(private)
    assert data['scoring_status']=='LOCAL_GENERATED_KEY'
    assert data['parent_dataset_id']=='parent'


def test_validated_output_is_not_claimed_fully_qualified(tmp_path,monkeypatch):
    from ekas_press_intelligence.native.jobs import JobStore
    from ekas_press_intelligence.native.worker import run_job
    import ekas_press_intelligence.native.engine as engine
    store=JobStore(tmp_path);job=store.create('generate',{});store.claim('test')
    monkeypatch.setattr(engine,'execute',lambda *a,**kw:{'public_directory':'public','dataset':{'name':'native'},'passed':True,'validation_performed':True})
    assert run_job(tmp_path,job['id'])==0
    assert store.dataset(job['id'])['status']=='NATIVE_VALIDATED'


def test_spawn_failure_does_not_kill_scheduler(tmp_path,monkeypatch):
    from ekas_press_intelligence.native.worker import JobManager
    import ekas_press_intelligence.native.worker as worker
    manager=JobManager(tmp_path)
    first=manager.store.create('describe_process',{'plant':'heated_stirred_tank'})
    second=manager.store.create('describe_process',{'plant':'exothermic_cstr'})
    def unavailable(*a,**kw):raise OSError('controlled spawn failure')
    monkeypatch.setattr(worker.subprocess,'Popen',unavailable)
    manager.start()
    try:
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and manager.store.get(second['id'])['state']!='failed':time.sleep(.01)
        assert manager.store.get(first['id'])['error']['code']=='WORKER_START_FAILED'
        assert manager.store.get(second['id'])['state']=='failed'
        assert manager.thread.is_alive()
    finally:manager.close()


def test_blind_analysis_registers_exact_frozen_claims(tmp_path,monkeypatch):
    import hashlib
    from ekas_press_intelligence.native.worker import run_job
    from ekas_press_intelligence.native.jobs import JobStore
    import ekas_press_intelligence.native.analysis as analysis
    csv='start_utc,end_utc,kind,root_cause,evidence_tags,notes\n2024-01-01T00:00:00Z,2024-01-02T00:00:00Z,fault,Valve obstruction,A,Observed response\n'
    store=JobStore(tmp_path);public=tmp_path/'public';public.mkdir()
    store.register_dataset('blind',{'id':'blind','public_path':str(public)})
    job=store.create('blind_analysis',{'dataset_dir':str(public),'dataset_id':'blind'});store.claim('test')
    def execute(parameters,target,*args):
        assert 'dataset_id' not in parameters
        target.mkdir(parents=True);(target/'submission.csv').write_text(csv)
        return {'submission':{'artifact':'submission.csv','sha256':hashlib.sha256(csv.encode()).hexdigest()},'qualification_probe':False}
    monkeypatch.setattr(analysis,'execute_analysis',execute)
    assert run_job(tmp_path,job['id'])==0
    assert store.submission('blind')['csv']==csv
    assert store.submission('blind')['sha256']==hashlib.sha256(csv.encode()).hexdigest()


def test_analysis_probe_never_freezes_dataset_claims(tmp_path,monkeypatch):
    import pytest
    from ekas_press_intelligence.native.worker import run_job
    from ekas_press_intelligence.native.jobs import JobStore
    import ekas_press_intelligence.native.analysis as analysis
    store=JobStore(tmp_path);job=store.create('blind_analysis',{'dataset_id':'probe','qualification_probe':True});store.claim('test')
    monkeypatch.setattr(analysis,'execute_analysis',lambda *a,**k:{'qualification_probe':True})
    assert run_job(tmp_path,job['id'])==0
    with pytest.raises(KeyError):store.submission('probe')


def test_cancel_exit_race_does_not_kill_scheduler(tmp_path,monkeypatch):
    from ekas_press_intelligence.native.worker import JobManager
    import ekas_press_intelligence.native.worker as worker
    manager=JobManager(tmp_path);job=manager.store.create('describe_process',{})
    class Exiting:
        import io
        stdout=io.BytesIO()
        pid=987654;returncode=0
        def poll(self):return None
        def wait(self,timeout=None):return 0
    monkeypatch.setattr(worker.subprocess,'Popen',lambda *a,**kw:Exiting())
    def gone(*a):raise ProcessLookupError('exited before cancellation')
    monkeypatch.setattr(worker.os,'killpg',gone)
    manager.start()
    try:
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and manager.store.get(job['id'])['state']=='queued':time.sleep(.01)
        manager.store.request_cancel(job['id'])
        while time.monotonic()<deadline and manager.store.get(job['id'])['state'] not in ('cancelled','failed'):time.sleep(.01)
        assert manager.store.get(job['id'])['state']=='cancelled'
        assert manager.thread.is_alive()
    finally:manager.close()


def test_orphan_worker_cancel_after_manager_restart_reaps_provider_children(tmp_path):
    import os,subprocess,sys,json
    from pathlib import Path
    from ekas_press_intelligence.native.jobs import JobStore
    from ekas_press_intelligence.native.worker import JobManager
    store=JobStore(tmp_path/'state');job=store.create('describe_process',{});store.claim('crashed-manager')
    child=tmp_path/'child.pid'
    provider=tmp_path/'provider.py'
    provider.write_text('import subprocess,sys,time,json\np=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"])\nopen('+repr(str(child))+',"w").write(str(p.pid))\nprint(json.dumps({"type":"system","subtype":"init","tools":["StructuredOutput"],"plugins":[]}),flush=True)\ntime.sleep(60)\n')
    code='''
import os,sys
from pathlib import Path
from ekas_press_intelligence.native import worker,engine
from ekas_press_intelligence.native.analysis import run_broker
def execute(operation,parameters,target,repo,progress=None):
    target.mkdir(parents=True)
    run_broker([sys.executable,sys.argv[3]],'prompt',target,os.environ.copy(),60,[],target/'status.json')
    return {}
engine.execute=execute
raise SystemExit(worker.run_job(sys.argv[1],sys.argv[2]))
'''
    process=subprocess.Popen([sys.executable,'-c',code,str(store.directory),job['id'],str(provider)],start_new_session=True)
    manager=JobManager(store.directory)
    try:
        deadline=time.monotonic()+10
        while not child.exists() and time.monotonic()<deadline:time.sleep(.02)
        assert child.exists()
        assert store.get(job['id'])['process_start']
        manager.start();store.request_cancel(job['id'])
        assert process.wait(timeout=8)==130
        assert store.get(job['id'])['state']=='cancelled'
        status=Path('/proc')/child.read_text()/'status'
        assert not status.exists() or 'State:\tZ' in status.read_text()
    finally:
        manager.close()
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        if child.exists():
            try:os.kill(int(child.read_text()),15)
            except ProcessLookupError:pass


def test_configured_resource_pressure_stops_owned_worker_and_preserves_failure(tmp_path):
    import subprocess,sys
    from ekas_press_intelligence.native.jobs import JobStore
    store=JobStore(tmp_path);job=store.create('describe_process',{});store.claim('manager')
    code='''
import sys,time
from ekas_press_intelligence.native import worker,engine,resource_guard
resource_guard.memory_pressure=lambda:{'code':'RESOURCE_LIMIT_EXCEEDED','message':'controlled memory pressure','measurements':{'rss_bytes':123}}
engine.execute=lambda *a,**k:time.sleep(60)
raise SystemExit(worker.run_job(sys.argv[1],sys.argv[2]))
'''
    process=subprocess.Popen([sys.executable,'-c',code,str(store.directory),job['id']],start_new_session=True)
    try:
        assert process.wait(timeout=12)==130
        current=store.get(job['id'])
        assert current['state']=='failed'
        assert current['error']['code']=='RESOURCE_LIMIT_EXCEEDED'
        assert current['result']['resource_guard']['measurements']['rss_bytes']==123
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=5)


def test_log_open_failure_stops_only_owned_worker_and_next_job_runs(tmp_path):
    from ekas_press_intelligence.native.worker import JobManager
    manager=JobManager(tmp_path)
    first=manager.store.create('describe_process',{'plant':'heated_stirred_tank'})
    second=manager.store.create('describe_process',{'plant':'heated_stirred_tank'})
    logs=tmp_path/'logs';logs.mkdir();(logs/(first['id']+'.log')).mkdir()
    manager.start()
    try:
        deadline=time.monotonic()+40
        while time.monotonic()<deadline and manager.store.get(second['id'])['state'] not in ('succeeded','failed'):time.sleep(.05)
        failed=manager.store.get(first['id'])
        assert failed['state']=='failed'
        assert failed['error']['code']=='LOG_CAPTURE_FAILED'
        assert failed['audit_failures'][0]['code']=='LOG_CAPTURE_FAILED'
        assert manager.store.get(second['id'])['state']=='succeeded'
    finally:manager.close()


def test_verified_signal_rejects_mismatched_process_identity():
    import subprocess,sys,signal
    from ekas_press_intelligence.native.jobs import process_identity
    from ekas_press_intelligence.native.worker import signal_verified_worker
    process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
    try:
        identity=process_identity(process.pid)
        assert identity
        assert signal_verified_worker(process.pid,identity+'-mismatch',signal.SIGTERM) is False
        assert process.poll() is None
        assert signal_verified_worker(process.pid,identity,signal.SIGTERM) is True
        assert process.wait(timeout=5)==-signal.SIGTERM
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=5)


def test_explicit_unvalidated_physics_output_keeps_unvalidated_status(tmp_path,monkeypatch):
    from ekas_press_intelligence.native.jobs import JobStore
    from ekas_press_intelligence.native.worker import run_job
    import ekas_press_intelligence.native.engine as engine
    store=JobStore(tmp_path);job=store.create('generate',{'validate':False});store.claim('test')
    monkeypatch.setattr(engine,'execute',lambda *a,**k:{'public_directory':'public','dataset':{'name':'unvalidated'},'passed':None,'validation_performed':False,'engineering_acceptance':{'passed':False}})
    assert run_job(tmp_path,job['id'])==0
    assert store.dataset(job['id'])['status']=='UNVALIDATED'
    assert store.get(job['id'])['result']['passed'] is None
