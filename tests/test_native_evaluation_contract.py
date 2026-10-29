import hashlib
import pytest
from fastapi.testclient import TestClient
from ekas_press_intelligence.native.jobs import JobStore,JobConflict
from ekas_press_intelligence.native.api import create_native_app

CSV='start_utc,end_utc,kind,root_cause,evidence_tags\n'

def test_evaluation_registration_is_atomic_and_bound_to_frozen_hash(tmp_path):
    store=JobStore(tmp_path);frozen=store.freeze_submission('data',CSV)
    job=store.create('independent_evaluation',{'dataset_id':'data'});store.claim('worker')
    judgment={'row':2,'correct':True,'reason':'Component and physical mechanism both agree.'}
    with pytest.raises(JobConflict,match='digest'):
        store.finish(job['id'],{},adjudication=('data','wrong',[judgment]))
    assert store.get(job['id'])['state']=='running'
    assert store.submission('data')['judgments']==[]
    store.finish(job['id'],{},adjudication=('data',frozen['sha256'],[judgment]))
    assert store.get(job['id'])['state']=='succeeded'
    assert store.submission('data')['judgments']==[judgment]

def test_evaluator_job_requires_role_frozen_claims_and_local_key(tmp_path):
    app=create_native_app(tmp_path,start_worker=False,tokens={'a':'analyst','e':'evaluator','m':'admin'})
    store=app.state.store
    store.register_dataset('generated',{'id':'generated','public_path':str(tmp_path/'public'),'private_path':str(tmp_path/'private'),'scoring_status':'LOCAL_GENERATED_KEY'})
    with TestClient(app) as client:
        body={'operation':'independent_evaluation','parameters':{'dataset_id':'generated'}}
        assert client.post('/v2/jobs',json=body,headers={'Authorization':'Bearer a'}).status_code==403
        assert client.post('/v2/jobs',json=body,headers={'Authorization':'Bearer e'}).status_code==409
        store.freeze_submission('generated',CSV)
        response=client.post('/v2/jobs',json=body,headers={'Authorization':'Bearer e'})
        assert response.status_code==201,response.text
        job=store.get(response.json()['id'])
        assert job['parameters']['dataset_dir']==str(tmp_path/'private')
        assert 'submission_csv' not in job['parameters']
        body['parameters']['dataset_id']='historianrca'
        assert client.post('/v2/jobs',json=body,headers={'Authorization':'Bearer e'}).status_code==409
