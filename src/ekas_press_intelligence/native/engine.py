"""Actual native dispatch. Private generated artifacts never become public by inference."""
from __future__ import annotations
from contextlib import redirect_stdout
from dataclasses import asdict, is_dataclass
from pathlib import Path
import hashlib
import inspect
import io
import json
import math
import os
from .data import dataset_info, public_files

OPS={
 'new_plant':{'name','equipment'},
 'generate':{'scenario','profile','seed','days','scan','dt_sim','ballast','faults','difficulty','resample','no_fault','validate','start','timezone','baseline_days','config'},
 'validate':{'dataset_dir'}, 'plant_check':{'plant','stage','seed'},
 'describe_process':{'dataset_dir','plant'},'make_challenge':{'dataset_dir'},
 'plot':{'dataset_dir','tags','episode','days','shade_episodes'},'report':{'dataset_dir'},'summarise':{'dataset_dir'},
}

def _json(value):
    if is_dataclass(value): value=asdict(value)
    if hasattr(value,'model_dump'): value=value.model_dump(mode='json')
    if isinstance(value,dict): return {str(k):_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [_json(v) for v in value]
    if isinstance(value,Path): return str(value)
    if hasattr(value,'tolist'): return _json(value.tolist())
    if hasattr(value,'isoformat'): return value.isoformat()
    if hasattr(value,'item'): return _json(value.item())
    if isinstance(value,float) and not math.isfinite(value): return None
    return value

def _folder(value):
    p=Path(value)
    if not p.is_dir(): raise ValueError('INVALID_DATASET: dataset directory does not exist')
    if any(q.is_symlink() for q in (p,*p.parents)): raise ValueError('INVALID_DATASET: symlink path')
    # Trusted worker chooses this input; prohibit symlinks in files read by native functions.
    for q in p.rglob('*'):
        if q.is_symlink(): raise ValueError('INVALID_DATASET: symlink artifact')
    return p

def _config(p):
    from historiansim.config.schema import ScenarioConfig
    from historiansim.scenarios import build_scenario
    if 'config' in p:
        if set(p)-{'config','resample','validate'}: raise ValueError('INVALID_PARAMETERS: config cannot be combined with scenario overrides')
        # Native Pydantic currently permits ignored extras; recursively check before parsing.
        def check(model,data):
            if not isinstance(data,dict): return
            unknown=set(data)-set(model.model_fields)
            if unknown: raise ValueError('INVALID_PARAMETERS: unknown config fields '+','.join(sorted(unknown)))
            for key,val in data.items():
                annotation=model.model_fields[key].annotation
                if isinstance(annotation,type) and hasattr(annotation,'model_fields'): check(annotation,val)
        check(ScenarioConfig,p['config'])
        return ScenarioConfig.model_validate(p['config'])
    for k in ('days','scan','dt_sim','baseline_days','resample'):
        if k in p and (isinstance(p[k],bool) or not isinstance(p[k],(int,float)) or not math.isfinite(p[k]) or p[k]<=0): raise ValueError('INVALID_PARAMETERS: '+k+' must be positive finite')
    for k in ('seed','faults','ballast'):
        if k in p and (type(p[k]) is not int or (k!='seed' and p[k]<0)): raise ValueError('INVALID_PARAMETERS: '+k+' must be integer')
    for k in ('no_fault','validate'):
        if k in p and type(p[k]) is not bool: raise ValueError('INVALID_PARAMETERS: '+k+' must be boolean')
    if p.get('no_fault') and 'faults' in p: raise ValueError('INVALID_PARAMETERS: no_fault conflicts with faults')
    aliases={'scan':'dt_scan','faults':'n_faults'}
    overrides={aliases.get(k,k):v for k,v in p.items() if k in {'days','scan','dt_sim','ballast','faults','difficulty','start','timezone','baseline_days'}}
    if p.get('no_fault'): overrides['n_faults']=0
    cfg=build_scenario(p.get('scenario','exchanger-fouling'),profile=p.get('profile','standard'),seed=p.get('seed',42),**overrides)
    if 'dt_sim' in p and cfg.time.dt_sim!=p['dt_sim']: raise ValueError('INVALID_PARAMETERS: dt_sim exceeds scan; native would silently clamp it')
    if cfg.time.n_steps<2: raise ValueError('INVALID_PARAMETERS: duration must contain at least two native scans')
    return cfg

def _checks(checks):
    return [{'name':c.name,'passed':bool(c.passed),'severity':c.severity} for c in checks]

def _write_checks(checks, private):
    private.mkdir(parents=True,exist_ok=True)
    (private/'validation.json').write_text(json.dumps([_json(c) for c in checks],indent=2),encoding='utf-8')

def _passed(checks):
    return all(c.passed or c.severity!='error' for c in checks)

def execute(operation:str,parameters:dict,target:Path,repo_root:Path,progress=None)->dict:
    if operation not in OPS: raise ValueError('INVALID_OPERATION: '+str(operation))
    if not isinstance(parameters,dict) or set(parameters)-OPS[operation]: raise ValueError('INVALID_PARAMETERS: unknown operation option')
    p=dict(parameters); target=Path(target)
    for flag in ('validate','no_fault','shade_episodes'):
        if flag in p and type(p[flag]) is not bool: raise ValueError('INVALID_PARAMETERS: '+flag+' must be boolean')
    if any(q.is_symlink() for q in (target,*target.parents)): raise ValueError('INVALID_TARGET: symlink path')
    target.mkdir(parents=True,exist_ok=True)
    if any(target.iterdir()): raise ValueError('INVALID_TARGET: operation requires an empty target')
    def phase(name):
        if progress is not None: progress(name)
    from historiansim import pipeline
    from historiansim.validation import run_battery
    from historiansim.validation.recipe import audit_dataset_dir
    result={'operation':operation,'evaluator_only':operation in ('report','summarise','plant_check','new_plant')}
    origin=Path(inspect.getfile(pipeline)).resolve()
    result['provenance']={'runtime':'actual historiansim','pipeline_sha256':hashlib.sha256(origin.read_bytes()).hexdigest()}
    if operation=='new_plant':
        import re
        import shutil
        import subprocess
        import sys
        if not isinstance(p.get('name'),str) or not re.fullmatch(r'[a-z][a-z0-9_]*',p['name']): raise ValueError('INVALID_PARAMETERS: native plant name must be snake_case')
        if not isinstance(p.get('equipment'),str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._-]{0,79}',p['equipment']): raise ValueError('INVALID_PARAMETERS: equipment must be a bounded equipment designation')
        source=Path(repo_root)/'vendor'/'HistorianSim'
        _folder(source)
        clone=target/'authoring'/'HistorianSim'
        shutil.copytree(source,clone,ignore=shutil.ignore_patterns('.git','__pycache__','*.egg-info'))
        env=os.environ.copy(); env['PYTHONPATH']=str(clone/'src')
        phase('native_scaffold')
        code='import sys; from historiansim.scaffold import scaffold_plant; scaffold_plant(sys.argv[1],sys.argv[2])'
        subprocess.run([sys.executable,'-c',code,p['name'],p['equipment']],env=env,cwd=clone,check=True,capture_output=True,text=True)
        directory=Path('authoring')/'HistorianSim'/'src'/'historiansim'/'plants'/p['name']
        result.update(plant_directory=str(directory),authoring_directory='authoring/HistorianSim',status='SCAFFOLDED_REQUIRES_DESIGN_AND_NATIVE_GATES')
    elif operation=='generate':
        cfg=_config(p)
        resample=p.get('resample',60.)
        if isinstance(resample,bool) or not isinstance(resample,(int,float)) or not math.isfinite(resample) or resample<=0: raise ValueError('INVALID_PARAMETERS: resample must be positive finite seconds')
        from historiansim import layout
        safe_grids=hasattr(layout,'grid_filename')
        if hasattr(layout,'period_label'):layout.period_label(resample)
        elif resample<1 or int(resample)!=resample:raise ValueError('INVALID_PARAMETERS: fractional grids require the verified corrected runtime')
        if resample==10 and not safe_grids: raise ValueError('INVALID_PARAMETERS: stock upstream resample 10 overwrites primary historian_10s.parquet; use verified corrected runtime')
        n=cfg.time.n_steps
        if n<2: raise ValueError('INVALID_PARAMETERS: duration must contain at least two native scans')
        from historiansim.plants import get_plant
        tag_count=len(get_plant(cfg.unit).tags())+cfg.ballast_tags
        estimate=int(n*tag_count*8*16)
        requested_grid_rows=int(math.floor((n-1)*cfg.time.dt_scan/resample))+1
        if resample!=60:estimate+=requested_grid_rows*tag_count*16
        limit=int(os.environ.get('EKAS_NATIVE_MAX_ESTIMATED_BYTES','12000000000'))
        if estimate>limit: raise ValueError(f'CAPACITY_EXCEEDED: estimated {estimate} bytes exceeds configured {limit}; duration unchanged')
        phase('native_generate'); data=pipeline.generate(cfg)
        private=target/'private'; public=target/'public'
        phase('native_export'); pipeline.write_dataset(data,private,resample_s=resample)
        compatibility=False
        if resample!=60 and not safe_grids:
            # Native make_challenge and plotting require canonical 60 s export.
            from historiansim.historian.export import build_regular_grid
            build_regular_grid(data.measured,data.index,60.).to_parquet(private/'historian_60s.parquet',index=False)
            compatibility=True
        elif resample!=60:compatibility=True
        checks=[]
        if p.get('validate',True):
            phase('native_validate'); checks=run_battery(data)+audit_dataset_dir(private)
            _write_checks(checks,private/'metadata')
        phase('native_make_challenge')
        from historiansim.challenge import make_challenge
        make_challenge(private,public)
        if resample!=60 and not safe_grids:
            import shutil
            shutil.copy2(private/f'historian_{int(resample)}s.parquet',public/f'historian_{int(resample)}s.parquet')
        import sys
        modules={}
        for name,module in list(sys.modules.items()):
            location=getattr(module,'__file__',None)
            if location and name.startswith(('historiansim','extensions.stamping_press')):
                file=Path(location)
                if file.is_file(): modules[name]={'origin':str(file.resolve()),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
        (private/'metadata'/'execution_provenance.json').write_text(json.dumps({'modules':modules,'config':cfg.model_dump(mode='json')},indent=2),encoding='utf-8')
        result.update(dataset=dataset_info(public),public_directory='public',private_directory='private',validation=_checks(checks),passed=_passed(checks) if p.get('validate',True) else None,validation_performed=p.get('validate',True),capacity={'estimated_bytes':estimate,'configured_limit_bytes':limit,'steps':n,'duration_days':cfg.time.days,'requested_grid_rows':requested_grid_rows},resample={'requested_seconds':resample,'native_challenge_canonical_60s_added':compatibility},files=public_files(public))
    elif operation=='plant_check':
        from historiansim.validation.plant_checks import run_plant_checks
        if 'plant' not in p: raise ValueError('INVALID_PARAMETERS: plant required')
        stage=p.get('stage')
        if stage is not None and (type(stage) is not int or stage not in range(1,6)): raise ValueError('INVALID_PARAMETERS: stage must be 1..5')
        if 'seed' in p and type(p['seed']) is not int: raise ValueError('INVALID_PARAMETERS: seed must be integer')
        lines=[]; phase('native_plant_check')
        ok=run_plant_checks(p['plant'],stages=None if stage is None else [stage],seed=p.get('seed',7),echo=lines.append)
        result.update(evaluator_only=True,passed=bool(ok),report='\n'.join(lines),stages=list(range(1,6)) if stage is None else [stage])
    elif operation=='describe_process':
        from historiansim.process_doc import build_process_description
        folder=_folder(p['dataset_dir']) if p.get('dataset_dir') else None
        if folder is None and not p.get('plant'): raise ValueError('INVALID_PARAMETERS: dataset_dir or plant required')
        text=build_process_description(folder,plant_name=p.get('plant'))
        (target/'PROCESS_DESCRIPTION.md').write_text(text,encoding='utf-8')
        result.update(text=text,artifact='PROCESS_DESCRIPTION.md')
    else:
        if not p.get('dataset_dir'): raise ValueError('INVALID_PARAMETERS: dataset_dir required')
        folder=_folder(p['dataset_dir'])
        if operation=='validate':
            from historiansim.config.schema import ScenarioConfig
            manifest=json.loads(pipeline.manifest_path(folder).read_text())
            cfg=ScenarioConfig.model_validate(manifest['config'])
            phase('native_regenerate'); checks=run_battery(pipeline.generate(cfg))+audit_dataset_dir(folder)
            _write_checks(checks,target/'private')
            result.update(validation=_checks(checks),passed=_passed(checks))
        elif operation=='make_challenge':
            from historiansim.challenge import make_challenge
            make_challenge(folder,target/'public')
            result.update(dataset=dataset_info(target/'public'),public_directory='public',files=public_files(target/'public'))
        elif operation=='plot':
            from historiansim.plotting import plot_dataset
            tags=p.get('tags')
            if isinstance(tags,str): tags=[t.strip() for t in tags.split(',')]
            if tags is not None and (not isinstance(tags,list) or not tags or any(not isinstance(t,str) for t in tags)): raise ValueError('INVALID_PARAMETERS: tags must be names')
            window=p.get('days')
            if isinstance(window,str): window=[float(t) for t in window.split(',')]
            if window is not None and (len(window)!=2 or any(not math.isfinite(v) for v in window) or window[0]>window[1]): raise ValueError('INVALID_PARAMETERS: days must be ordered pair')
            if 'shade_episodes' in p and type(p['shade_episodes']) is not bool: raise ValueError('INVALID_PARAMETERS: shade_episodes must be boolean')
            plot_dataset(folder,tags=tags,episode=p.get('episode'),window_days=tuple(window) if window is not None else None,out=target/'plot.png',shade_episodes=p.get('shade_episodes',False))
            result.update(artifact='plot.png',evaluator_only=bool(p.get('episode') or p.get('shade_episodes')))
        elif operation=='summarise':
            from historiansim.summary import build_summary
            text=build_summary(folder); (target/'FAULT_ANSWER_KEY.md').write_text(text,encoding='utf-8')
            result.update(text=text,artifact='FAULT_ANSWER_KEY.md')
        elif operation=='report':
            # Preserve the native complete report including evidence/confusion sets.
            from historiansim.cli import report
            capture=io.StringIO()
            with redirect_stdout(capture): report(folder)
            result['text']=capture.getvalue()
    phase('complete')
    return _json(result)
