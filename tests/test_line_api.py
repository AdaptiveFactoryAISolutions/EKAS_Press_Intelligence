import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    from ekas_press_intelligence.native.api import create_native_app
    with TestClient(create_native_app(tmp_path,start_worker=False,tokens={'admin':'admin','reader':'analyst'})) as c:
        c.headers['Authorization']='Bearer admin'
        yield c


def create(client):
    config=client.get('/v2/line/preset').json()['config']
    r=client.post('/v2/line/drafts',json={'name':'Training line','step':1,'config':config})
    assert r.status_code==201,r.text
    return r.json()


def test_preset_and_role_boundary(client):
    r=client.get('/v2/line/preset');assert r.status_code==200,r.text
    assert len(r.json()['steps'])==8 and r.json()['config']['speed_spm']==8
    assert client.get('/v2/line/preset',headers={'Authorization':'Bearer reader'}).status_code==403


def test_draft_save_resume_stale_conflict_and_invalid_config(client):
    d=create(client);ident=d['id'];d['config']['speed_spm']=600
    body={k:d[k] for k in ['name','step','config','revision']};body['step']=2
    r=client.put('/v2/line/drafts/'+ident,json=body)
    assert r.status_code==200 and r.json()['revision']==2
    assert client.get('/v2/line/drafts/'+ident).json()['config']['speed_spm']==600
    assert client.put('/v2/line/drafts/'+ident,json=body).status_code==409
    r=client.post('/v2/line/preflight',json={'config':d['config']})
    assert r.status_code==422 and r.json()['detail']['errors'][0]['location']==['config','speed_spm']
    assert client.get('/v2/line/drafts').json()['drafts'][0]['id']==ident


def test_step_checks_do_not_block_on_later_screen(client):
    d=create(client);d['config']['speed_spm']=600
    assert client.post('/v2/line/check-step',json={'step':1,'config':d['config']}).status_code==200
    assert client.post('/v2/line/check-step',json={'step':2,'config':d['config']}).status_code==422


def test_run_is_revision_bound_idempotent_and_immutable(client,monkeypatch):
    import ekas_press_intelligence.native.line_api as module
    monkeypatch.setattr(module,'runtime_ready',lambda:True)
    monkeypatch.setattr(module,'native_config',lambda config:{'name':'test','params':{'speed_spm':config.speed_spm}})
    d=create(client);path='/v2/line/drafts/'+d['id']+'/run';body={'revision':1,'idempotency_key':'one-click'}
    a=client.post(path,json=body);assert a.status_code==201,a.text
    b=client.post(path,json=body);assert b.json()['id']==a.json()['id']
    assert len(client.app.state.store.list())==1
    d['config']['speed_spm']=7
    assert client.put('/v2/line/drafts/'+d['id'],json={k:d[k] for k in ['name','step','config','revision']}).status_code==200
    assert client.app.state.store.get(a.json()['id'])['parameters']['config']['params']['speed_spm']==8
    assert client.post(path,json={'revision':1,'idempotency_key':'another'}).status_code==409
    assert client.post(path,json={'revision':2,'idempotency_key':'one-click'}).status_code==409


def test_unavailable_runtime_blocks_run_and_reports_correction(client,monkeypatch):
    import ekas_press_intelligence.native.line_api as module
    monkeypatch.setattr(module,'runtime_ready',lambda:False)
    d=create(client)
    r=client.post('/v2/line/drafts/'+d['id']+'/run',json={'revision':1,'idempotency_key':'x'})
    assert r.status_code==409 and r.json()['detail']['code']=='LINE_RUNTIME_UNAVAILABLE'
    assert not client.app.state.store.list()


def test_drafts_cannot_store_unknown_or_secret_fields(client):
    d=create(client);d['config']['provider_token']='secret'
    assert client.post('/v2/line/drafts',json={k:d[k] for k in ['name','step','config']}).status_code==422


def test_bottleneck_requires_recorded_acknowledgment(client):
    d=create(client);d['config'].update(packers=1,packing_rate_per_min=1)
    response=client.post('/v2/line/preflight',json={'config':d['config']})
    assert response.status_code==422
    assert response.json()['detail']['errors'][0]['location']==['config','allow_bottleneck']


def test_run_records_model_source_digest(client,monkeypatch):
    import ekas_press_intelligence.native.line_api as module
    monkeypatch.setattr(module,'runtime_ready',lambda:True)
    monkeypatch.setattr(module,'native_config',lambda config:{'name':'test','params':{}})
    d=create(client)
    response=client.post('/v2/line/drafts/'+d['id']+'/run',json={'revision':1,'idempotency_key':'bound'})
    assert response.status_code==201
    binding=client.app.state.store.line_binding(response.json()['id'])
    assert len(binding['model_sha256'])==64
    from ekas_press_intelligence.native import line_source
    line_source.check_binding(binding)
    monkeypatch.setattr(line_source,'model_digest',lambda:'different-source')
    with pytest.raises(ValueError,match='LINE_SOURCE_CHANGED'):line_source.check_binding(binding)


def test_changed_runtime_requires_service_restart_before_new_preflight(client,monkeypatch):
    import ekas_press_intelligence.native.line_api as module
    d=create(client);monkeypatch.setattr(module,'model_digest',lambda:'changed')
    response=client.post('/v2/line/preflight',json={'config':d['config']})
    assert response.status_code==409 and response.json()['detail']['code']=='LINE_SOURCE_CHANGED'


def test_unchanged_save_preserves_revision_and_server_recovers_run(client,monkeypatch):
    import ekas_press_intelligence.native.line_api as module
    monkeypatch.setattr(module,'runtime_ready',lambda:True)
    monkeypatch.setattr(module,'native_config',lambda config:{'name':'test','params':{}})
    d=create(client);path='/v2/line/drafts/'+d['id']
    same=client.put(path,json={k:d[k] for k in ['name','step','config','revision']}).json()
    assert same['revision']==d['revision']
    run=client.post(path+'/run',json={'revision':d['revision'],'idempotency_key':'recover'}).json()
    resumed=client.get(path).json()
    assert resumed['last_run']['job_id']==run['id']
    assert resumed['last_run']['revision']==d['revision']
    assert resumed['last_run']['idempotency_key']=='recover'
