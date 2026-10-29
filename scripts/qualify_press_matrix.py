"""Execute the declared 513 full-exposure native cases, with immutable evidence.

Requires a separately prepared, verified source epoch. No tuning, gate skipping,
shortened exposure or altered native threshold is supported by this runner.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from threading import Event

STOP=Event()

ROOT=Path(__file__).resolve().parents[1]
SEEDS=(7,19,42)
RATES=(45,60,75)
SEVERITIES=('subtle','moderate','obvious')


def write_once(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
    Path(path).chmod(0o400)


def source_epoch():
    paths=[Path(os.environ['EKAS_NATIVE_RUNTIME'])/'NATIVE_RUNTIME_PROVENANCE.json',
           Path(__file__).resolve(),ROOT/'src/ekas_press_intelligence/native/qualification.py']
    return {str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def verify_epoch(path):
    expected=json.loads(Path(path).read_text())
    if source_epoch()!=expected:raise RuntimeError('MATRIX_SOURCE_EPOCH_CHANGED')
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def batch(args):
    from ekas_press_intelligence.native.bootstrap import activate
    verified=activate()
    epoch_hash=verify_epoch(args.epoch)
    from ekas_press_intelligence.native.qualification import envelope_metrics,measured_effects,masking_gate,validate_matrix_config,engineering_acceptance
    import numpy as np
    from historiansim.plants import get_plant
    from historiansim.measurement.instrument import INSTRUMENT_CLASSES
    from historiansim.validation.catalog import (sweep_catalog,Effect,undiagnosable,
        flat_violations,direction_mismatches,indistinguishable,dangling_tags,MIN_SNR)
    plant=get_plant('stamping_press');original=plant.loops
    def operating_loops():
        loops=original()
        for loop in loops:
            if loop.name=='SIC-271':loop.sp=float(args.rate)
        return loops
    plant.loops=operating_loops
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    manifest=Path(os.environ['EKAS_NATIVE_RUNTIME'])/'NATIVE_RUNTIME_PROVENANCE.json'
    binding={'source_epoch_sha256':epoch_hash,'seed':args.seed,'rate_spm':args.rate,'severity':args.severity,'days':14.,
             'onset_s':6*86400.,'dt_scan':20.,'native_runtime_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
             'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'metrics_sha256':hashlib.sha256((ROOT/'src/ekas_press_intelligence/native/qualification.py').read_bytes()).hexdigest()}
    write_once(out/'binding.json',binding)
    floors={s.name:INSTRUMENT_CLASSES[s.instrument].noise_sigma*(s.hi-s.lo) for s in plant.tags()}
    full={};cases={};started=time.time()
    def observe(cid,measured,twin,cfg,truth,truth_twin):
        validate_matrix_config(cfg,args.seed,args.rate,measured.n,twin.n)
        cause=plant.catalog.causes[cid];fault=cause.make(binding['onset_s'],args.severity)
        dt=cfg.time.dt_scan;onset=int(binding['onset_s']/dt)
        end=min(measured.n,int(fault.end_s/dt)) if getattr(fault,'end_s',None) is not None else measured.n
        lo=onset+int((end-onset)*.1);hi=onset+int((end-onset)*.9)
        union=sorted({e.tag for c in plant.catalog.causes_for(cause.symptom) for e in c.evidence})
        actual=measured_effects(measured,twin,union,onset,end,dt,floors)
        full[cid]={tag:Effect(**effect) for tag,effect in actual.items()}
        masks=[]
        for loop in cfg.loops:
            pv=loop.pv_source;op=loop.name+'.OP';measured_pv=loop.name+'.PV'
            if pv not in truth.signals or op not in measured.values or measured_pv not in measured.values:continue
            physical=envelope_metrics(truth.signals[pv][lo:hi],truth_twin.signals[pv][lo:hi],loop.sp,dt)
            observed=envelope_metrics(measured.values[measured_pv][lo:hi],twin.values[measured_pv][lo:hi],loop.sp,dt)
            load=measured_effects(measured,twin,[op],onset,end,dt,floors)[op]
            demand=np.asarray(measured.values[op][lo:hi],dtype=float)
            mode_tag=loop.name+'.MODE'
            if mode_tag not in truth.modes:raise ValueError('MISSING_ACTUAL_CONTROLLER_MODE: '+mode_tag)
            gate=masking_gate(physical,load,demand,truth.modes[mode_tag][lo:hi],MIN_SNR,loop.out_min,loop.out_max)
            masks.append({'loop':loop.name,'physical_envelope':physical,'measured_pv':observed,
                          'measured_actuator_effect':load,**gate})
        residuals={name:float(np.max(np.abs(values))) for name,values in truth.signals.items() if name in ('CALC-MATERIAL-RESIDUAL','CALC-ENERGY-RESIDUAL')}
        engineering={'faulted':engineering_acceptance(truth),'twin':engineering_acceptance(truth_twin)}
        case={**binding,'cause_id':cid,'symptom':cause.symptom,'actual_config':cfg.model_dump(mode='json'),
              'episode_scan_interval':[onset,end],'central_eighty_percent_scan_interval':[lo,hi],
              'fully_measured_symptom_union':actual,'masking':masks,'physical_residual_maxima':residuals,'engineering_acceptance':engineering,
              'disclosure':'Raw measured PV fractions and one-hour envelope metrics are reported separately. Physical envelope masking uses the actual mean-state signal, not a fault-minus-twin surrogate. Residual maxima are diagnostics; independent energy/material qualification remains required.'}
        write_once(out/(cid+'.json'),case);cases[cid]=case
        print(json.dumps({'case':cid,**binding,'completed':len(cases)}),flush=True)
    try:
        native=sweep_catalog(plant,days=14.,onset_s=binding['onset_s'],severity=args.severity,
                             dt_scan=20.,seed=args.seed,observer=observe)
        findings={'undiagnosable':undiagnosable(native),'flat_violations':flat_violations(native),
                  'direction_mismatches':direction_mismatches(native),'dangling_tags':dangling_tags(plant),
                  'native_indistinguishable':indistinguishable(plant,native),
                  'fully_measured_union_indistinguishable':indistinguishable(plant,full)}
        findings['engineering_ledger_failures']=[cid for cid,case in cases.items() if not all(value['passed'] for value in case['engineering_acceptance'].values())]
        # Native SNR alone can resolve a tiny same-noise difference. Require a
        # public measured separation above instrument resolution as well.
        observable={cid:{tag:Effect(**{**asdict(e),'snr':e.snr if max(abs(e.peak),abs(e.sustained))>e.noise_floor else 0.}) for tag,e in effects.items()} for cid,effects in full.items()}
        findings['above_instrument_floor_indistinguishable']=indistinguishable(plant,observable)
        masked=[cid for cid,c in cases.items() if any(m['qualifies'] for m in c['masking'])]
        passed=len(cases)==19 and not any(findings.values()) and (args.severity!='moderate' or len(masked)>=10)
        activate()  # Reverify actual source bytes, not only the unchanged manifest.
        verify_epoch(args.epoch)
        result={**binding,'passed':passed,'cases':len(cases),'findings':findings,'masked_causes':masked,
                'native_effects':{cid:{tag:asdict(effect) for tag,effect in effects.items()} for cid,effects in native.items()},
                'case_artifacts':{cid+'.json':hashlib.sha256((out/(cid+'.json')).read_bytes()).hexdigest() for cid in cases},
                'elapsed_seconds':time.time()-started,'runtime_kind':verified['kind']}
        write_once(out/'result.json',result)
        return 0 if passed else 1
    finally:plant.loops=original


def launch(args,seed,rate,severity):
    if STOP.is_set():raise RuntimeError('MATRIX_CANCELLED')
    out=Path(args.output)/f'seed-{seed}_rate-{rate}_{severity}'
    out.mkdir(parents=True,exist_ok=False)
    command=[sys.executable,'-B',str(Path(__file__).resolve()),'--batch','--epoch',str(args.epoch),'--seed',str(seed),'--rate',str(rate),'--severity',severity,'--output',str(out)]
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',EKAS_NATIVE_BLAS_THREADS='1')
    env['PYTHONPYCACHEPREFIX']=str(out/'cache')
    started=time.time()
    with (out/'stdout.log').open('w') as log:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while process.poll() is None:
                if STOP.is_set():raise RuntimeError('MATRIX_CANCELLED')
                if time.time()-started>args.timeout:raise TimeoutError('NATIVE_MATRIX_BATCH_TIMEOUT')
                # Protect other active workloads; never reclaim their resources.
                available=next(int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
                if available<2147483648:raise RuntimeError('HOST_MEMORY_RESERVE_EXHAUSTED')
                time.sleep(1)
        except BaseException as exc:
            from ekas_press_intelligence.native.qualification import terminate_owned
            terminate_owned(process)
            write_once(out/'runner_failure.json',{'code':str(exc),'returncode':process.returncode})
            raise
    result=json.loads((out/'result.json').read_text()) if process.returncode==0 else {}
    if process.returncode==0 and (result.get('source_epoch_sha256')!=verify_epoch(args.epoch) or result.get('passed') is not True or result.get('cases')!=19):
        raise RuntimeError('MATRIX_RESULT_BINDING_INVALID')
    if process.returncode==0:
        artifacts=result.get('case_artifacts',{})
        if len(artifacts)!=19 or any(Path(name).name!=name or hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest for name,digest in artifacts.items()):
            raise RuntimeError('MATRIX_CASE_ARTIFACTS_CHANGED')
    return {'seed':seed,'rate':rate,'severity':severity,'returncode':process.returncode,'output':str(out)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--epoch',type=Path);parser.add_argument('--output',required=True,type=Path);parser.add_argument('--batch',action='store_true')
    parser.add_argument('--seed',type=int,choices=SEEDS);parser.add_argument('--rate',type=int,choices=RATES)
    parser.add_argument('--severity',choices=SEVERITIES);parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--timeout',type=int,default=3600)
    args=parser.parse_args()
    if not os.environ.get('EKAS_NATIVE_RUNTIME'):parser.error('EKAS_NATIVE_RUNTIME must bind a frozen prepared source epoch')
    if not 1<=args.workers<=6 or not 1<=args.timeout<=7200:parser.error('workers1..6 and timeout1..7200 required')
    os.nice(15)
    if args.batch:
        if None in (args.seed,args.rate,args.severity):parser.error('batch requires seed/rate/severity')
        if args.epoch is None:parser.error('batch requires parent source epoch')
        return batch(args)
    args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=False)
    args.epoch=args.output/'source_epoch.json';write_once(args.epoch,source_epoch())
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,lambda *_:STOP.set())
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(launch,args,seed,rate,severity) for seed in SEEDS for rate in RATES for severity in SEVERITIES]
        results=[]
        for future in as_completed(futures):
            try:results.append(future.result())
            except Exception as exc:results.append({'returncode':1,'runner_failure':str(exc)})
            print(json.dumps(results[-1]),flush=True)
    verify_epoch(args.epoch)
    summary={'source_epoch_sha256':verify_epoch(args.epoch),'batches':results,'required_batches':27,'required_cases':513,'passed':len(results)==27 and all(r['returncode']==0 for r in results)}
    write_once(args.output/'summary.json',summary)
    return 0 if summary['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
