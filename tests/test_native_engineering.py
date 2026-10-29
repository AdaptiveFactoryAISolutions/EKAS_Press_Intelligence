"""Real native generation must retain private quantitative engineering receipts."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def test_actual_press_job_retains_normalized_engineering_checks_without_public_truth():
    spec=importlib.util.spec_from_file_location('engineering_preparer',ROOT/'scripts/prepare_native_runtime.py')
    preparer=importlib.util.module_from_spec(spec);spec.loader.exec_module(preparer)
    with tempfile.TemporaryDirectory(prefix='engineering-native-',dir=ROOT/'work') as scratch:
        scratch=Path(scratch);runtime=preparer.prepare_runtime(ROOT,scratch/'runtime')
        code='''
import json,sys
from pathlib import Path
from historiansim.scenarios import build_scenario
from ekas_press_intelligence.native.engine import execute
cfg=build_scenario('stamping-press-rca',profile='quick',seed=7,days=.002)
cfg.episodes.n_faults=0;cfg.episodes.n_benign=0;cfg.episodes.baseline_days=0;cfg.ballast_tags=0
result=execute('generate',{'config':cfg.model_dump(mode='json'),'validate':False},Path(sys.argv[1]),Path(sys.argv[2]))
assert result['passed'] is None and result['validation_performed'] is False
assert result['engineering_acceptance']['passed'] is True
assert set(result['engineering_acceptance'])=={'passed','faulted','twin'}
assert (Path(sys.argv[1])/'private/metadata/engineering_validation.json').is_file()
assert not any(tag['tag'].startswith('AUDIT-') for tag in result['dataset']['tags'])
print(json.dumps({'passed':True,'faulted':result['engineering_acceptance']['faulted']['checks']}))
'''
        env=dict(os.environ,PYTHONPATH=str(runtime/'src')+os.pathsep+str(ROOT/'src'),
                 PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        run=subprocess.run([sys.executable,'-B','-c',code,str(scratch/'job'),str(ROOT)],cwd=ROOT,
                           env=env,capture_output=True,text=True,timeout=120)
        assert run.returncode==0,run.stderr
        assert json.loads(run.stdout.strip().splitlines()[-1])['passed']


def test_invalid_private_ledger_produces_failed_receipt_instead_of_losing_evidence():
    from types import SimpleNamespace
    from ekas_press_intelligence.native.engine import _press_engineering
    data=SimpleNamespace(cfg=SimpleNamespace(unit='stamping_press'),truth=SimpleNamespace(signals={}),twin=SimpleNamespace(signals={}))
    result=_press_engineering(data)
    assert result['passed'] is False
    for name in ('faulted','twin'):
        assert result[name]['passed'] is False
        assert result[name]['error']['code']=='PRIVATE_ENGINEERING_AUDIT_REQUIRED'
        assert result[name]['checks']['ledger_integrity']['passed'] is False


def test_failed_physics_job_cannot_register_dataset_and_receipt_is_private(tmp_path,monkeypatch):
    import pytest
    from fastapi.testclient import TestClient
    from ekas_press_intelligence.native.api import create_native_app
    from ekas_press_intelligence.native.worker import run_job
    import ekas_press_intelligence.native.engine as engine
    receipt={'passed':False,'faulted':{'passed':False,'private_ledger_detail':'test-only adverse ledger'},'twin':{'passed':True}}
    def failed_engine(operation,parameters,target,*_,**__):
        folder=target/'private/metadata';folder.mkdir(parents=True)
        (folder/'engineering_validation.json').write_text(json.dumps(receipt))
        return {'passed':False,'engineering_acceptance':receipt,'validation_performed':True,'public_directory':'public','dataset':{'name':'failed-physics'}}
    monkeypatch.setattr(engine,'execute',failed_engine)
    app=create_native_app(tmp_path,start_worker=False,tokens={'read':'analyst','judge':'evaluator','operate':'admin'})
    store=app.state.store;job=store.create('generate',{});store.claim('test')
    assert run_job(tmp_path,job['id'])==1
    failed=store.get(job['id'])
    assert failed['state']=='failed' and failed['error']['code']=='PHYSICS_VALIDATION_FAILED'
    assert failed['result']['engineering_acceptance']==receipt
    with pytest.raises(KeyError):store.dataset(job['id'])
    with TestClient(app) as client:
        path=f"/v2/jobs/{job['id']}/files/engineering_validation.json"
        for token in ('operate','judge'):
            response=client.get(path,headers={'Authorization':'Bearer '+token})
            assert response.status_code==200,response.text
            assert response.json()==receipt
        assert client.get(path,headers={'Authorization':'Bearer read'}).status_code==403
        assert client.get(f"/v2/jobs/{job['id']}/files",headers={'Authorization':'Bearer read'}).status_code==403
        assert job['id'] not in {d['id'] for d in client.get('/v2/datasets',headers={'Authorization':'Bearer read'}).json()['datasets']}
