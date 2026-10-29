from fastapi.testclient import TestClient
import pytest


def test_export_api_admin_strict_registered_binding(tmp_path):
    from ekas_press_intelligence.native.api import create_native_app
    with TestClient(create_native_app(tmp_path,start_worker=False,tokens={'a':'admin','r':'analyst','e':'evaluator'})) as c:
        body={'operation':'observability_export','parameters':{'dataset_id':'historianrca','profile':'sparse'}}
        for token in ('r','e'):
            assert c.post('/v2/jobs',json=body,headers={'Authorization':'Bearer '+token}).status_code==403
        h={'Authorization':'Bearer a'}
        for extra in ({'plant':'stamping_press'},{'dataset_dir':'/etc'},{'profile':'invented'}):
            bad={'operation':body['operation'],'parameters':dict(body['parameters'],**extra)}
            assert c.post('/v2/jobs',json=bad,headers=h).status_code==422
        response=c.post('/v2/jobs',json=body,headers=h)
        assert response.status_code==201,response.text
        assert c.get('/v2/jobs/'+response.json()['id'],headers={'Authorization':'Bearer r'}).status_code==403
        caps=c.get('/v2/capabilities',headers=h).json()
        assert 'observability_export' in caps['operations']
        assert caps['observability_options']['profile']['enum']==['enhanced','sparse']

from test_native_observability import source

@pytest.mark.parametrize('has_key',[True,False])
@pytest.mark.parametrize('profile',['sparse','enhanced'])
def test_export_http_owned_worker_preserves_lineage_and_parquet(source,tmp_path,has_key,profile):
    import json,time
    from pathlib import Path
    import pandas as pd
    from ekas_press_intelligence.native.api import create_native_app
    from ekas_press_intelligence.native.jobs import JobStore
    public,contract=source;state=tmp_path/'state';store=JobStore(state)
    private=tmp_path/'private'
    if has_key:
        (private/'metadata').mkdir(parents=True)
        (private/'metadata/manifest.json').write_text(json.dumps({'config':{'unit':'heated_stirred_tank'}}))
        (private/'metadata/ground_truth.json').write_text('{}')
    parent={'id':'fixture','label':'Bounded real Parquet fixture','source':'generated' if has_key else 'observability_export',
            'status':'UNVALIDATED','public_path':str(public),'private_path':str(private) if has_key else None,
            'scoring_status':'LOCAL_GENERATED_KEY' if has_key else 'EXTERNAL_SCORING_REQUIRED'}
    if not has_key:parent['parent_dataset_id']='historianrca'
    store.register_dataset('fixture',parent)
    with TestClient(create_native_app(state,start_worker=True,tokens={'a':'admin'})) as c:
        h={'Authorization':'Bearer a'}
        response=c.post('/v2/jobs',json={'operation':'observability_export','parameters':{'dataset_id':'fixture','profile':profile}},headers=h)
        assert response.status_code==201,response.text
        ident=response.json()['id'];deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            job=c.get('/v2/jobs/'+ident,headers=h).json()
            if job['state'] in ('succeeded','failed','cancelled','interrupted'):break
            time.sleep(.1)
        assert job['state']=='succeeded',job
        derived=store.dataset(ident)
        assert derived['private_path']==parent['private_path']
        assert derived['scoring_status']==parent['scoring_status']
        assert derived['parent_dataset_id']=='fixture' and derived['source_dataset_id']=='fixture'
        assert derived['status']=='UNVALIDATED' and derived['observability_profile']==profile
        expected=pd.read_parquet(public/'historian_60s.parquet')
        retained=[n for n in expected if profile=='enhanced' or n=='timestamp' or n not in contract['withheld_tags']]
        pd.testing.assert_frame_equal(pd.read_parquet(Path(derived['public_path'])/'historian_60s.parquet'),expected[retained])
        info=c.get('/v2/datasets/'+ident,headers=h).json()
        assert info['source_dataset_id']=='fixture' and info['observability_profile']==profile
        assert c.get('/v2/datasets/'+ident+'/files/SOURCE_AVAILABILITY.json',headers=h).status_code==200
        assert not (Path(derived['public_path'])/'metadata').exists()


def test_export_client_payload():
    from ekas_press_intelligence.native.client import EKASNativeClient
    with EKASNativeClient('http://127.0.0.1') as client:
        calls=[]
        client.submit_job=lambda *a: calls.append(a) or {'state':'queued'}
        assert client.export_observability('id','sparse','idem')['state']=='queued'
        assert calls==[('observability_export',{'dataset_id':'id','profile':'sparse'},'idem')]
        with pytest.raises(ValueError):client.export_observability('id','other')


def test_export_worker_rejects_forged_binding_and_untrusted_identity(source,tmp_path):
    from ekas_press_intelligence.native.jobs import JobStore
    from ekas_press_intelligence.native.worker import run_job,export_plant
    public,_=source;state=tmp_path/'state';store=JobStore(state)
    store.register_dataset('registered',{'id':'registered','public_path':str(public),'private_path':None,'scoring_status':'EXTERNAL_SCORING_REQUIRED'})
    with pytest.raises(ValueError,match='PLANT_IDENTITY_UNAVAILABLE'):
        export_plant(store,store.dataset('registered'))
    job=store.create('observability_export',{'dataset_id':'registered','dataset_dir':str(tmp_path/'forged'),'profile':'sparse'})
    store.claim('test')
    import signal
    handlers={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
    try:assert run_job(state,job['id'])==1
    finally:
        for sig,handler in handlers.items():signal.signal(sig,handler)
    assert store.get(job['id'])['error']['code']=='DATASET_MISMATCH'
    assert [d['id'] for d in store.datasets()]==['registered']
    store.register_dataset('cycle',{'id':'cycle','parent_dataset_id':'cycle','private_path':None})
    with pytest.raises(ValueError,match='DATASET_LINEAGE_INVALID'):
        export_plant(store,store.dataset('cycle'))
