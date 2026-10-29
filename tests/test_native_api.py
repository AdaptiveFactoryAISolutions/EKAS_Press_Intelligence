from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client(tmp_path):
    from ekas_press_intelligence.native.api import create_native_app
    with TestClient(create_native_app(tmp_path,start_worker=False,tokens={'read':'analyst','judge':'evaluator','operate':'admin'})) as c:
        yield c


def test_actual_original_dataset_queries_and_role_protection(client):
    assert client.get('/v2/datasets').status_code==401
    h={'Authorization':'Bearer read'}
    data=client.get('/v2/datasets',headers=h).json()
    assert data['datasets'][0]['id']=='historianrca'
    assert data['datasets'][0]['scoring_status']=='EXTERNAL_SCORING_REQUIRED'
    info=client.get('/v2/datasets/historianrca',headers=h).json()
    assert len(info['tags'])==90
    rows=client.get('/v2/datasets/historianrca/samples',params={'tags':'TIC-101.PV','max_points':5},headers=h)
    assert rows.status_code==200,rows.text
    assert rows.json()['rows']
    files=client.get('/v2/datasets/historianrca/files',headers=h).json()['files']
    assert all('ground_truth' not in f['name'] and 'FAULT_ANSWER' not in f['name'] for f in files)
    assert client.post('/v2/jobs',json={'operation':'report','parameters':{}},headers=h).status_code==403


def test_request_scope_paths_and_cross_origin_rejected(client):
    h={'Authorization':'Bearer operate'}
    body={'operation':'validate','parameters':{'dataset_dir':'/etc'}}
    assert client.post('/v2/jobs',json=body,headers=h).status_code==422
    invalid=client.post('/v2/jobs',json={'operation':'shell','parameters':{}},headers=h)
    assert invalid.status_code==422
    assert invalid.json()['detail']['code']=='INVALID_REQUEST'
    assert client.post('/v2/jobs',json={'operation':'generate','parameters':{},'surprise':True},headers=h).status_code==422
    assert client.post('/v2/jobs',json={'operation':'generate','parameters':{}},headers=dict(h,Origin='http://untrusted.example')).status_code==403
    assert client.get('/v2/datasets/historianrca/files/metadata%2Fground_truth.json',headers=h).status_code in (404,422)


def test_published_benchmark_never_gets_invented_score(client):
    h={'Authorization':'Bearer read'}
    csv='start_utc,end_utc,kind,root_cause,evidence_tags\n2024-03-20T00:00:00Z,2024-03-21T00:00:00Z,fault,test,TIC-101.PV\n'
    response=client.post('/v2/datasets/historianrca/submissions',json={'csv':csv},headers=h)
    assert response.status_code==201,response.text
    assert response.json()['frozen']
    assert client.post('/v2/datasets/historianrca/submissions',json={'csv':csv},headers=h).status_code==409
    response=client.get('/v2/datasets/historianrca/score',headers=h)
    assert response.status_code==409
    assert response.json()['detail']['code']=='EXTERNAL_SCORING_REQUIRED'


def test_measured_event_http_quality_missing_sources_and_bounds(client,tmp_path):
    import pandas as pd
    public=tmp_path/'events';public.mkdir()
    pd.DataFrame({'timestamp':pd.to_datetime(['2024-01-01T00:00:00.001Z','2024-01-01T00:00:00.002Z']),
                  'event_code':[3,-1],'count':[1.,float('nan')],'quality':[0,2]}).to_parquet(public/'cycle_event_journal.parquet')
    client.app.state.store.register_dataset('event-fixture',{'id':'event-fixture','public_path':str(public),'status':'UNVALIDATED'})
    h={'Authorization':'Bearer read'}
    response=client.get('/v2/datasets/event-fixture/events',headers=h)
    assert response.status_code==200,response.text
    assert response.json()['rows'][1]['count'] is None
    assert response.json()['rows'][1]['quality']==2
    assert response.json()['event_codes']['3']=='inspection delivery'
    limited=client.get('/v2/datasets/event-fixture/events',params={'max_points':1},headers=h).json()
    assert limited['truncated'] and len(limited['rows'])==1
    assert client.get('/v2/datasets/event-fixture/events',params={'source':'status'},headers=h).json()['detail']['code']=='EVENT_SOURCE_UNAVAILABLE'
    assert client.get('/v2/datasets/event-fixture/events',params={'source':'private'},headers=h).status_code==422
    assert client.get('/v2/datasets/event-fixture/events',params={'max_points':10001},headers=h).status_code==422


def test_analyst_cannot_self_adjudicate(client):
    h={'Authorization':'Bearer read'}
    csv='start_utc,end_utc,kind,root_cause,evidence_tags,cause_correct\n2024-03-20T00:00:00Z,2024-03-21T00:00:00Z,fault,test,TIC-101.PV,Y\n'
    assert client.post('/v2/datasets/historianrca/submissions',json={'csv':csv},headers=h).status_code==422
    assert client.post('/v2/datasets/historianrca/adjudicate',json={'judgments':[{'row':2,'correct':True,'reason':'self'}]},headers=h).status_code==403


def test_loopback_default_and_network_configuration(tmp_path):
    from ekas_press_intelligence.native.api import create_native_app
    with pytest.raises(ValueError):create_native_app(tmp_path,start_worker=False,local_only=False,tokens={})
    with TestClient(create_native_app(tmp_path,start_worker=False,tokens={})) as c:
        assert c.get('/v2/health').json()['role']=='admin'
        assert c.get('/v2/health',headers={'Host':'hostile.example'}).status_code==403


def test_openapi_documents_actual_bearer_roles_and_version(client):
    from ekas_press_intelligence import __version__
    schema=client.get('/openapi.json').json()
    assert schema['info']['version']==__version__
    assert schema['security']==[{'NativeRoleBearer':[]}]
    bearer=schema['components']['securitySchemes']['NativeRoleBearer']
    assert bearer['type']=='http' and bearer['scheme']=='bearer'
    assert 'analyst' in bearer['description'] and 'evaluator' in bearer['description']


def test_remote_peer_cannot_spoof_loopback_host(tmp_path):
    from ekas_press_intelligence.native.api import create_native_app
    with TestClient(create_native_app(tmp_path,start_worker=False,tokens={}),client=('198.51.100.25',1234)) as c:
        assert c.get('/v2/health',headers={'Host':'localhost'}).status_code==403


def test_analyst_cannot_discover_generation_schedule_or_source_catalog(client):
    admin={'Authorization':'Bearer operate'}; analyst={'Authorization':'Bearer read'}
    response=client.post('/v2/jobs',json={'operation':'generate','parameters':{'scenario':'exchanger-fouling','seed':123,'profile':'quick','days':1}},headers=admin)
    assert response.status_code==201,response.text
    ident=response.json()['id']
    assert client.get('/v2/jobs/'+ident,headers=analyst).status_code==403
    assert all(j['id']!=ident for j in client.get('/v2/jobs',headers=analyst).json()['jobs'])
    caps=client.get('/v2/capabilities',headers=analyst).json()
    assert not any(k in caps for k in ('plants','scenarios','profiles','recipes','generate_options'))
    assert client.get('/v2/capabilities',headers=admin).json()['scenarios']


def test_concurrent_scores_use_private_independent_csvs(client,tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    import pandas as pd
    import historiansim.challenge
    import historiansim.scoring
    store=client.app.state.store
    store.register_dataset('score-test',{'id':'score-test','public_path':str(tmp_path),'private_path':str(tmp_path),'scoring_status':'LOCAL_GENERATED_KEY'})
    store.freeze_submission('score-test','start_utc,end_utc,kind,root_cause,evidence_tags\n')
    barrier=threading.Barrier(2);paths=[]
    monkeypatch.setattr(historiansim.challenge,'load_scoring_key',lambda _:pd.DataFrame())
    def inspect_score(key,path):
        paths.append(path)
        barrier.wait(timeout=5)
        assert path.stat().st_mode & 0o777 == 0o600
        return {'detail':pd.DataFrame()}
    monkeypatch.setattr(historiansim.scoring,'score_submission',inspect_score)
    def score():return client.get('/v2/datasets/score-test/score',headers={'Authorization':'Bearer judge'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:score(),range(2)))
    assert all(r.status_code==200 for r in responses)
    assert len(set(paths))==2
    assert not any(p.exists() for p in paths)


def test_analysis_outputs_and_trusted_dataset_binding(client,tmp_path):
    analyst={'Authorization':'Bearer read'};admin={'Authorization':'Bearer operate'}
    response=client.post('/v2/jobs',headers=analyst,json={'operation':'blind_analysis','parameters':{'dataset_id':'historianrca'}})
    assert response.status_code==201,response.text
    job=response.json();store=client.app.state.store
    assert store.get(job['id'])['parameters']['dataset_id']=='historianrca'
    store.claim('test')
    root=store.directory/'artifacts'/job['id'];root.mkdir(parents=True)
    for name in ('submission.csv','analysis_notes.md','analysis_provenance.json','input_snapshot.json','provider_status.json','evidence_queries.jsonl'):(root/name).write_text('test')
    store.finish(job['id'],{'operation':'blind_analysis','artifacts':['submission.csv','analysis_notes.md','analysis_provenance.json','input_snapshot.json','provider_status.json','evidence_queries.jsonl']})
    names={f['name'] for f in client.get('/v2/jobs/'+job['id']+'/files',headers=analyst).json()['files']}
    assert names=={'submission.csv','analysis_notes.md'}
    assert client.get('/v2/jobs/'+job['id']+'/files/analysis_provenance.json',headers=analyst).status_code==404
    assert len(client.get('/v2/jobs/'+job['id']+'/files',headers=admin).json()['files'])==6


def test_failed_analysis_retains_only_protected_diagnostic_artifacts(client):
    store=client.app.state.store
    job=store.create('blind_analysis',{'dataset_id':'historianrca'});store.claim('fixture')
    root=store.directory/'artifacts'/job['id'];root.mkdir(parents=True)
    for name in ('input_snapshot.json','provider_status.json','submission.csv'):(root/name).write_text('{}')
    store.fail(job['id'],'PROVIDER_REQUEST_FAILED','Retained provider failure')
    admin={'Authorization':'Bearer operate'};analyst={'Authorization':'Bearer read'}
    names={f['name'] for f in client.get('/v2/jobs/'+job['id']+'/files',headers=admin).json()['files']}
    assert names=={'input_snapshot.json','provider_status.json'}
    assert client.get('/v2/jobs/'+job['id']+'/files',headers=analyst).json()['files']==[]


def test_blind_analysis_requires_registered_dataset(client):
    response=client.post('/v2/jobs',headers={'Authorization':'Bearer read'},json={'operation':'blind_analysis','parameters':{}})
    assert response.status_code==422

def test_transport_probe_requires_administrator(client):
    body={'operation':'blind_analysis','parameters':{'dataset_id':'historianrca','qualification_probe':True}}
    for token in ('read','judge'):
        assert client.post('/v2/jobs',headers={'Authorization':'Bearer '+token},json=body).status_code==403
    assert client.post('/v2/jobs',headers={'Authorization':'Bearer operate'},json=body).status_code==201


def test_evaluator_answer_key_requires_frozen_claims_even_for_admin_created_job(client,tmp_path):
    store=client.app.state.store
    store.register_dataset('key-test',{'id':'key-test','private_path':str(tmp_path),'public_path':str(tmp_path),'scoring_status':'LOCAL_GENERATED_KEY'})
    evaluator={'Authorization':'Bearer judge'};admin={'Authorization':'Bearer operate'}
    body={'operation':'summarise','parameters':{'dataset_id':'key-test'}}
    rejected=client.post('/v2/jobs',json=body,headers=evaluator)
    assert rejected.status_code==409
    assert rejected.json()['detail']['code']=='FROZEN_SUBMISSION_REQUIRED'
    response=client.post('/v2/jobs',json=body,headers=admin)
    assert response.status_code==201
    ident=response.json()['id'];store.claim('test')
    root=store.directory/'artifacts'/ident;root.mkdir(parents=True)
    (root/'FAULT_ANSWER_KEY.md').write_text('private key')
    store.finish(ident,{'text':'private key','artifact':'FAULT_ANSWER_KEY.md','evaluator_only':True})
    assert client.get('/v2/jobs/'+ident,headers=evaluator).status_code==409
    assert client.get('/v2/jobs/'+ident+'/files/FAULT_ANSWER_KEY.md',headers=evaluator).status_code==409
    assert all(j['id']!=ident for j in client.get('/v2/jobs',headers=evaluator).json()['jobs'])
    assert client.get('/v2/jobs/'+ident,headers=admin).status_code==200
    store.freeze_submission('key-test','start_utc,end_utc,kind,root_cause,evidence_tags\n')
    assert client.get('/v2/jobs/'+ident,headers=evaluator).status_code==200
    assert client.get('/v2/jobs/'+ident+'/files/FAULT_ANSWER_KEY.md',headers=evaluator).status_code==200
    assert client.post('/v2/jobs',json=body,headers=evaluator).status_code==201


def test_artifact_request_ids_cannot_be_paths_even_if_store_contains_noncanonical_id(client):
    """Defense in depth for imported/corrupt store rows, not an API insertion route."""
    store=client.app.state.store
    job=store.create('describe_process',{'plant':'heated_stirred_tank'});store.claim('test')
    store.finish(job['id'],{'artifact':'PROCESS_DESCRIPTION.md'})
    (store.directory/'artifacts').mkdir(exist_ok=True)
    (store.directory/'PROCESS_DESCRIPTION.md').write_text('PRIVATE_STATE_OUTSIDE_ARTIFACTS')
    with store.connect() as db:db.execute('UPDATE jobs SET id=? WHERE id=?',('..',job['id']))
    h={'Authorization':'Bearer read'}
    response=client.get('/v2/jobs/%2e%2e/files/PROCESS_DESCRIPTION.md',headers=h)
    assert response.status_code in (404,422)
    assert 'PRIVATE_STATE_OUTSIDE_ARTIFACTS' not in response.text
    listing=client.get('/v2/jobs/%2e%2e/files',headers=h)
    assert listing.status_code in (404,422)


def test_unknown_artifact_request_ids_never_resolve_existing_directory(client):
    from uuid import uuid4
    store=client.app.state.store;ident=str(uuid4())
    folder=store.directory/'artifacts'/ident;folder.mkdir(parents=True)
    (folder/'PROCESS_DESCRIPTION.md').write_text('UNREGISTERED_FILE')
    h={'Authorization':'Bearer read'}
    assert client.get('/v2/jobs/'+ident+'/files/PROCESS_DESCRIPTION.md',headers=h).status_code==404
    assert client.get('/v2/jobs/'+ident+'/files',headers=h).status_code==404
