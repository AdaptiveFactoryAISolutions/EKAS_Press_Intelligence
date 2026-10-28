import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('validate_campaign',Path(__file__).parents[1]/'scripts/validate_campaign.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_public_detector_detects_loss_quality_artifact_without_schedule():
    rows=[dict(t=t,spm=60 if not 300<=t<420 else 0,press_stop=int(300<=t<420),data_quality={},quality_measurement=.02 if t<600 else .2) for t in range(900)]
    rows[480]['data_quality']={'spm':'MISSING'}; rows[480]['spm']=None
    e={'samples':rows,'quality':[],'context':{'duration_s':900}}
    windows=module.detect_windows(e,baseline_s=180)
    assert any(a<=300<b for a,b in windows)
    assert any(a<=480<b for a,b in windows)
    assert any(a<=700<b for a,b in windows)
    assert all(a>=180 for a,b in windows)

def test_export_honors_discrete_counts_missing_quality_and_hashes(tmp_path):
    from ekas_press_intelligence.simulator.export import export_historian
    rows=[dict(t=t,spm=60.0 if t!=4 else None,stroke_count=t,plc_state='FEED' if t%2 else 'STROKE',data_quality={'spm':'MISSING'} if t==4 else {}) for t in range(10)]
    manifest=export_historian({'samples':rows,'context':{'sample_period_s':1}},tmp_path)
    assert manifest['regular_rows']==10
    assert manifest['compressed_rows']>=10
    assert manifest['signals']['spm']['missing_samples']==1
    assert manifest['signals']['stroke_count']['compressed_samples']==10
    assert all(len(f['sha256'])==64 for f in manifest['files'])

def test_per_class_incorrect_unresolved_agrees_with_scoring():
    truth=[dict(event_class='x',event_kind='fault',failed_item='motor',failure_mechanism='slip',start_s=0,end_s=10)]
    claims=[dict(start_s=0,end_s=10,failed_item=None,failure_mechanism=None,alternatives=[],diagnosis_state='SUSPECTED_CAUSE')]
    result=module.evaluate_by_class(truth,claims,{'matches':[dict(truth_index=0,claim_index=0,overlap_s=10,valid_evidence=['a'])]},[])
    assert result[0]['incorrect_cause'] is True

def test_claim_cause_gate_is_public_engine_decision_only():
    evidence={'context':{},'samples':[dict(t=t,spm=45) for t in range(10)],'events':[]}
    def worker(public,question):
        assert 'truth' not in public
        return {'cause_claim_eligible':True,'diagnosis_state':'SUSPECTED_CAUSE','hypotheses':[dict(event_class='drive',event_kind='fault',failed_item='belt',failure_mechanism='slip',disposition='SUPPORTED',reason='Measured rate/current signature')],'evidence':[]}
    claims,_,_=module.frozen_claims(evidence,[(0,10)],worker)
    assert claims[0]['failed_item']=='belt'
    assert claims[0]['failure_mechanism']=='slip'

def test_per_class_requires_scorer_sufficient_mechanism_evidence():
    event=dict(event_class='progressive_die_wear',event_kind='fault',failed_item='cutting insert',failure_mechanism='edge wear raises load before delayed dimensional drift',start_s=0,end_s=100)
    claim=dict(event,diagnosis_state='SUSPECTED_CAUSE',evidence=['ambient'],alternatives=[])
    facts={'ambient':dict(t=50,signal='ambient_temperature',quality='GOOD',calculation=dict(baseline_mean=20,current_mean=25,difference=5))}
    metrics={'matches':[dict(truth_index=0,claim_index=0,overlap_s=100,valid_evidence=['ambient'])]}
    result=module.evaluate_by_class([event],[claim],metrics,[],facts)
    assert not result[0]['correct_cause']
    assert result[0]['incorrect_cause']

def test_campaign_rejects_plc_feed_state_with_completed_stroke():
    evidence={'context':{'duration_s':2,'profile':'sparse'},'samples':[dict(t=0,press_run=1,press_stop=0,spm=60,stroke_count=1,part_count=1,plc_state='STROKE'),dict(t=1,press_run=1,press_stop=0,spm=60,stroke_count=2,part_count=2,plc_state='FEED')]}
    result=module.check_physics(evidence)
    assert not result['passed']
    assert 'scan-end PLC state matches completed strokes' in result['errors']
    assert result['checks']==7
