from ekas_press_intelligence.rca.verification import verify
from ekas_press_intelligence.financial import estimate


def window(stops=10, **context):
    return {'control_provenance':{'source':'measured test fixture','controls':dict(job='J',die_id='D',material='steel',rate=60,**context)},'context':dict(job='J',die_id='D',material='steel',rate=60,**context),'metrics':dict(inspected_count=3000,exposure_s=3600,data_quality=1,microstops=stops,downtime_s=stops*5,spm=60,throughput=3000-stops*5,oee=.8,scrap_rate=.01,quality=1,repeat_faults=stops)}


def test_verified_only_comparable_measured_improvement():
    result=verify(window(),window(1),{'completed':True})
    assert result['status']=='VERIFIED'
    assert not result['sustained']
    after=window(1); after['context']['job']='other'
    assert verify(window(),after,{})['status']=='INCONCLUSIVE'
    assert verify(window(),window(),{'completed':True})['status']=='NOT_VERIFIED'
    assert verify({}, {}, {'completed':True})['status']=='INCONCLUSIVE'


def test_quality_regression_and_exposure_guard():
    after=window(1);after['metrics']['scrap_rate']=.1
    assert verify(window(),after,{})['status']=='NOT_VERIFIED'
    after=window(1);after['metrics']['exposure_s']=30
    assert verify(window(),after,{})['status']=='INCONCLUSIVE'


def test_samples_compute_and_sustained_explicit():
    def samples(stop):
        return {'context':window()['context'],'samples':[dict(t=t,press_run=t>stop,spm=60,part_count=max(0,t-stop),stroke_count=t,scrap_count=0,quality_measurement=1,press_fault=t<=stop) for t in range(3601)]}
    result=verify(samples(50),samples(10),{'sustained_duration_s':3600})
    assert result['status']=='VERIFIED'; assert result['sustained']


def test_financial_opportunity_is_not_savings():
    r=estimate({'lost_units':100},{'contribution_per_unit':2,'currency':'USD','provenance':'plant estimate'})
    assert r['potential_contribution_at_risk']==200
    assert r['verified_savings'] is None
    assert r['production_opportunity']==100
    assert 'assumptions' in r and 'unknowns' in r

import pytest

@pytest.mark.parametrize('field',['job','die_id','material','rate'])
def test_each_control_required(field):
    after=window(1); del after['context'][field]
    assert verify(window(),after,{})['status']=='INCONCLUSIVE'

@pytest.mark.parametrize('metric',['microstops','downtime_s','spm','throughput','oee','scrap_rate','quality','repeat_faults'])
def test_each_metric_required(metric):
    after=window(1);del after['metrics'][metric]
    assert verify(window(),after,{})['status']=='INCONCLUSIVE'

@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1])
def test_nonfinite_or_negative_exposure_is_inconclusive(value):
    after=window(1);after['metrics']['exposure_s']=value
    assert verify(window(),after,{})['status']=='INCONCLUSIVE'


def test_bad_data_quality_and_insufficient_sustained_exposure():
    after=window(1);after['metrics']['data_quality']=.5
    assert verify(window(),after,{})['status']=='INCONCLUSIVE'
    assert not verify(window(),window(1),{'sustained_duration_s':7200})['sustained']


def test_verified_financial_measurement_requires_provenance():
    metrics={'verification_status':'VERIFIED','measured_cost_before':200,'measured_cost_after':100}
    assert estimate(metrics,{})['verified_savings'] is None
    metrics['measurement_provenance']='metered records'
    assert estimate(metrics,{})['verified_savings']==100
    metrics['verification_status']='INCONCLUSIVE'
    assert estimate(metrics,{})['verified_savings'] is None


def test_good_part_count_oee_scrap_denominator_and_deviation():
    context=window()['context']
    def payload(good,scrap,deviation):
        return {'context':context,'samples':[dict(t=0,press_run=True,spm=60,part_count=0,scrap_count=0,stroke_count=0,quality_measurement=deviation),dict(t=3600,press_run=True,spm=60,part_count=good,scrap_count=scrap,stroke_count=good+scrap,quality_measurement=deviation)]}
    result=verify(payload(3000,100,.1),payload(3300,50,.02),{})
    assert result['status']=='VERIFIED'
    assert result['metrics']['before']['oee']==pytest.approx(3000/3600)
    assert result['metrics']['before']['scrap_rate']==pytest.approx(100/3100)


def test_sample_pathology_and_within_window_context_changes():
    context=window()['context']
    samples=[dict(t=t,press_run=True,spm=60,part_count=t,scrap_count=0,quality_measurement=.02,job='OTHER' if t==2 else 'J',die_id='D',data_quality={'spm':'STUCK'}) for t in range(301)]
    result=verify({'context':context,'samples':samples},{'context':context,'samples':samples},{})
    assert result['status']=='INCONCLUSIVE'

@pytest.mark.parametrize('metric',['microstops','downtime_s','spm','throughput','oee','scrap_rate','quality','repeat_faults'])
def test_nonfinite_metric_is_inconclusive(metric):
    after=window(1);after['metrics'][metric]=float('nan')
    assert verify(window(),after,{})['status']=='INCONCLUSIVE'


def test_unknown_financial_inputs_stay_unknown():
    r=estimate({}, {})
    assert all(r[k] is None for k in ('lost_capacity','production_opportunity','potential_contribution_at_risk','estimated_financial_impact','avoided_cost','verified_savings'))


def test_quality_deviation_increase_is_regression():
    after=window(1);after['metrics']['quality']=2
    assert verify(window(),after,{})['status']=='NOT_VERIFIED'


def test_changed_achieved_rate_needs_observed_equal_setpoint():
    def payload(rate,setpoint=None):
        rows=[dict(t=t,press_run=True,spm=rate,part_count=t*rate/60,scrap_count=0,quality_measurement=.02) for t in range(601)]
        if setpoint is not None:
            for row in rows:row['rate_setpoint']=setpoint
        return {'context':window()['context'],'samples':rows}
    assert verify(payload(42),payload(60),{})['status']=='INCONCLUSIVE'
    assert verify(payload(42,60),payload(60,60),{})['status']=='VERIFIED'
    assert verify(payload(42,42),payload(60,60),{})['status']=='INCONCLUSIVE'


def test_offline_metrics_require_control_provenance():
    b,a=window(),window(1);b.pop('control_provenance',None);a.pop('control_provenance',None)
    assert verify(b,a,{})['status']=='INCONCLUSIVE'


def test_sparse_quality_records_must_be_windowed_and_scrap_observed():
    rows=[dict(t=t,press_run=True,spm=60,part_count=t) for t in range(301)]
    p={'context':window()['context'],'samples':rows,'quality':[dict(t=0,quality_measurement=.02,scrap_count=0,good_count=0),dict(t=300,quality_measurement=.02,scrap_count=10,good_count=300),dict(t=9999,quality_measurement=99,scrap_count=1000,good_count=1000)]}
    result=verify(p,p,{})
    assert result['metrics']['before']['quality']==.02
    assert result['metrics']['before']['scrap_rate']==pytest.approx(10/310)
    p['quality']=[]
    assert verify(p,p,{})['status']=='INCONCLUSIVE'


def test_offline_control_provenance_must_match_context():
    before,after=window(),window(1)
    after['control_provenance']['controls']['rate']=42
    assert verify(before,after,{})['status']=='INCONCLUSIVE'


def test_nonfinite_data_quality_inconclusive():
    after=window(1);after['metrics']['data_quality']=float('nan')
    assert verify(window(),after,{})['status']=='INCONCLUSIVE'


def test_equivalent_rate_noise_cannot_verify_action():
    def payload(spm):
        return {'context':window()['context'],'samples':[dict(t=t,press_run=True,spm=spm,rate_setpoint=60,part_count=t,scrap_count=0,quality_measurement=.02,press_fault=False) for t in range(601)]}
    result=verify(payload(60),payload(60.001),{})
    assert result['status']!='VERIFIED'
    assert result['improvements']==[]


def test_controlled_real_drive_repair_distinguishes_scrap_sampling_noise():
    from ekas_press_intelligence.simulator.engine import simulate
    scheduled=[dict(event_class='press_speed_degradation',start_s=600,end_s=3000)]
    original=simulate(7,3600,'enhanced',events=scheduled).evidence
    repaired=simulate(7,3600,'enhanced',events=scheduled,repair_at_s=2000).evidence
    def cut(data,start,end):
        return dict(data,samples=[s for s in data['samples'] if start<=s['t']<=end],quality=[s for s in data['quality'] if start<=s['t']<=end])
    result=verify(cut(original,1200,1799),cut(repaired,2400,2999),{})
    assert result['metrics']['after']['spm']>1.4*result['metrics']['before']['spm']
    assert result['status']=='VERIFIED',result
    assert 'scrap_rate' not in result['regressions']
    assert result['comparisons']['scrap_rate']['assessment']=='COMPATIBLE_WITH_SAMPLING_NOISE'


def test_large_scrap_regression_blocks_large_rate_improvement():
    b,a=window(),window(1)
    b['metrics'].update(inspected_count=10000,scrap_rate=.001,spm=40)
    a['metrics'].update(inspected_count=10000,scrap_rate=.1,spm=60)
    result=verify(b,a,{})
    assert result['status']=='NOT_VERIFIED'
    assert 'scrap_rate' in result['regressions']


def test_scrap_uncertainty_requires_adequate_observed_counts():
    before,after=window(),window(1)
    before['metrics']['inspected_count']=20
    after['metrics']['inspected_count']=20
    result=verify(before,after,{})
    assert result['status']=='INCONCLUSIVE'
    assert result['comparisons']['scrap_rate']['assessment']=='INSUFFICIENT_EXPOSURE'


def test_report_retains_versioned_policy_thresholds_and_provenance():
    result=verify(window(),window(1),{})
    assert result['comparison_policy']['version']=='controlled-press-comparison-1.0'
    assert result['comparisons']['spm']['meaningful_change_threshold']>=3
    assert result['comparisons']['scrap_rate']['before_interval_95']
    assert result['comparisons']['spm']['provenance']['before']=='measured test fixture'
