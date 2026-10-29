import pytest
from fastapi.testclient import TestClient
from ekas_press_intelligence.api import create_app


@pytest.fixture(scope='module')
def service(tmp_path_factory):
    app = create_app(tmp_path_factory.mktemp('api'))
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope='module')
def run(service):
    response = service.post('/v1/benchmark/run', json={'seed':7,'duration_s':10800,'profile':'enhanced'})
    assert response.status_code == 201, response.text
    return response.json()


def test_versioned_machine_contract_covers_every_operation(service):
    spec = service.get('/openapi.json').json()
    required = ['/v1/observability/assess','/v1/rca/investigate',
                '/v1/rca/cases/{case_id}','/v1/rca/cases/{case_id}/evidence',
                '/v1/rca/cases/{case_id}/verify','/v1/sensor-gaps','/v1/assets',
                '/v1/signals','/v1/benchmark/run','/v1/benchmark/{run_id}/submit',
                '/v1/benchmark/{run_id}/score']
    assert set(required) <= set(spec['paths'])
    assert spec['info']['version'] == '1.0.0'
    for path in required:
        for operation in spec['paths'][path].values():
            success=next(v for k,v in operation['responses'].items() if k in ('200','201'))
            assert success['content']['application/json']['schema'].get('$ref'),path


def test_benchmark_truth_inaccessible_before_score(service, run):
    rid=run['run_id']
    assert 'truth' not in run and 'failed_item' not in str(run)
    assert service.get(f'/v1/benchmark/{rid}/truth').status_code == 409
    assert service.get(f'/v1/benchmark/{rid}/score').status_code == 409


def test_investigate_real_evidence_and_persist_case(service, run):
    result=service.post('/v1/rca/investigate',json={'run_id':run['run_id'],
        'asset_id':'Press 27','question':'Explain the lost production', 'start_s':7200,'end_s':7380})
    assert result.status_code == 201, result.text
    case=result.json()
    assert case['diagnosis_state'] in ('OBSERVED_ANOMALY','SUSPECTED_CAUSE','EVIDENCE_SUPPORTED_CAUSE')
    assert case['hypotheses'] and case['evidence']
    assert service.get('/v1/rca/cases/'+case['case_id']).json()==case
    ev=service.get('/v1/rca/cases/'+case['case_id']+'/evidence').json()
    assert ev['evidence'] and ev['samples']


@pytest.mark.parametrize('field,value', [('run_id','missing'),('asset_id','Press 999'),('end_s',50000)])
def test_unavailable_scope_never_silently_substituted(service,run,field,value):
    request={'run_id':run['run_id'],'asset_id':'Press 27','question':'Investigate loss','start_s':7200,'end_s':7380}
    request[field]=value
    assert service.post('/v1/rca/investigate',json=request).status_code in (404,422)


def test_assessment_rejects_unknown_signal_and_persists(service):
    assert service.post('/v1/observability/assess',json={'signals':['fiction']}).status_code==422
    response=service.post('/v1/observability/assess',json={'profile':'sparse'})
    assert response.status_code==201
    assert response.json()['assessment_id']


def test_submission_frozen_then_scored_and_revealed(service,run):
    rid=run['run_id']
    first=service.post(f'/v1/benchmark/{rid}/submit',json={'claims':[]})
    assert first.status_code==201,first.text
    assert service.get(f'/v1/benchmark/{rid}/score').json()['missed']>0
    assert service.get(f'/v1/benchmark/{rid}/truth').json()['truth']
    assert service.post(f'/v1/benchmark/{rid}/submit',json={'claims':[]}).status_code==409


def test_routes_and_ui_assets(service):
    for route in ['/','/static/app.js','/static/app.css','/v1/assets','/v1/signals','/v1/sensor-gaps']:
        assert service.get(route).status_code==200
    assert service.post('/v1/rca/investigate',json={}).status_code==422


def test_named_asset_in_question_cannot_override_explicit_scope(service,run):
    result=service.post('/v1/rca/investigate',json={'run_id':run['run_id'],
        'asset_id':'Press 27','question':'Why did Press 28 lose production?', 'start_s':7200,'end_s':7380})
    assert result.status_code==422
    assert result.json()['detail']['code']=='CLARIFICATION_REQUIRED'


def test_evidence_references_are_unique_across_cases(service,run):
    body={'run_id':run['run_id'],'asset_id':'Press 27','question':'Explain loss','start_s':7200,'end_s':7380}
    first=service.post('/v1/rca/investigate',json=body).json()
    second=service.post('/v1/rca/investigate',json=body).json()
    assert not {e['id'] for e in first['evidence']} & {e['id'] for e in second['evidence']}


def test_apply_and_verify_uses_held_samples_not_client_metrics(service,run):
    c=service.post('/v1/rca/investigate',json={'run_id':run['run_id'],'asset_id':'Press 27',
        'question':'Investigate the feed loss','start_s':7200,'end_s':7800}).json()
    path=f"/v1/rca/cases/{c['case_id']}"
    a=service.post(path+'/actions',json={'target_event_class':'feeder_sensor_drift',
        'repair_at_s':7801,'description':'Recalibrate and secure the position transducer'})
    assert a.status_code==201,a.text
    v={'action_id':a.json()['action_id'],'before_start_s':7201,'before_end_s':7800,
       'after_start_s':7861,'after_end_s':8460}
    response=service.post(path+'/verify',json=v)
    assert response.status_code==200,response.text
    assert response.json()['status'] in ('VERIFIED','NOT_VERIFIED','INCONCLUSIVE')
    assert service.post(path+'/verify',json=dict(v,metrics={'oee':1})).status_code==422


def test_context_records_respect_the_requested_evidence_window():
    from ekas_press_intelligence.api import evidence_window
    payload={'context':{'duration_s':1000},'samples':[{'t':t} for t in range(1000)],
             'quality':[{'t':0},{'t':200},{'t':900}], 'events':[{'t':0},{'t':300},{'t':800}]}
    selected=evidence_window(payload,100,500)
    assert selected['quality']==[{'t':200}]
    assert selected['events']==[{'t':300}]


def test_question_asset_must_match_the_requested_component_scope():
    from ekas_press_intelligence.intent import interpret,ClarificationRequired
    with pytest.raises(ClarificationRequired):
        interpret('Why did Feeder 27 stop?','Decoiler 27',100,500)


def test_financial_assumptions_never_turn_opportunity_into_verified_savings(service,run):
    c=service.post('/v1/rca/investigate',json={'run_id':run['run_id'],'asset_id':'Press 27',
        'question':'Investigate production loss','start_s':7200,'end_s':7800}).json()
    path=f"/v1/rca/cases/{c['case_id']}/financial"
    response=service.post(path,json={'contribution_per_unit':2.5,'currency':'USD',
        'assumption_source':'Illustrative contribution assumption; not an approved quote'})
    assert response.status_code==200,response.text
    result=response.json()
    assert result['verified_savings'] is None
    assert result['potential_contribution_at_risk']==result['lost_capacity']*2.5
    assert result['assumptions']['provenance']
    assert service.post(path,json={'contribution_per_unit':-1,'currency':'USD','assumption_source':'bad'}).status_code==422


def test_context_references_resolve_after_case_namespacing(service,run):
    response=service.post('/v1/rca/investigate',json={'run_id':run['run_id'],'asset_id':'Press 27',
        'question':'Investigate production loss','start_s':7200,'end_s':7800})
    assert response.status_code==201,response.text
    case=response.json(); ids={e['id'] for e in case['evidence']}
    references=[ref for group in ('hypotheses','alternatives') for h in case[group]
                for ref in h['contextual_evidence']]
    assert references
    assert set(references)<=ids
    assert all(ref.startswith(case['case_id']+':') for ref in references)
