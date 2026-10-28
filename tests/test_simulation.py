import json
from ekas_press_intelligence.domain import catalog, profile_signals
from ekas_press_intelligence.simulator.engine import simulate

def test_catalog_contract():
    assert len(catalog()) >= 16
    for entry in catalog():
        assert set(('event_class','event_kind','asset','failed_item','failure_mechanism','symptoms','observable_signals','expected_directionality','timing_relationships','competing_causes','discriminating_signals','sparse_profile_observability','enhanced_profile_observability','verification_method')) <= entry.keys()

def test_deterministic_and_profile_invariant():
    a=simulate(7,1200,'sparse',events=[])
    b=simulate(7,1200,'enhanced',events=[])
    assert a == simulate(7,1200,'sparse',events=[])
    assert a.truth == b.truth
    for x,y in zip(a.evidence['samples'],b.evidence['samples']):
        assert all(x[k]==y[k] for k in profile_signals('sparse'))
        assert x['part_count'] <= x['stroke_count']
        assert x['press_run'] + x['press_stop'] == 1
    assert a.evidence['samples'][-1]['stroke_count'] > 1100

def test_mechanisms_and_repair():
    for entry in catalog():
        cls=entry["event_class"]
        evt=[dict(event_class=cls,start_s=120,end_s=600,severity=1)]
        run=simulate(4,900,'enhanced',events=evt)
        assert run.truth[0]['event_class']==cls
        assert 'failure_mechanism' not in json.dumps(run.evidence)
        assert run.evidence['samples'] != simulate(4,900,'enhanced',events=[]).evidence['samples']
    evt=[dict(event_class='lubrication_pressure_loss',start_s=120,end_s=850,severity=1)]
    run=simulate(4,900,'enhanced',events=evt,repair_at_s=450)
    assert run.truth[0]['end_s']==450
    assert run.evidence['samples'][440]['lube_pressure'] < 2
    assert run.evidence['samples'][700]['lube_pressure'] > 4

def test_public_context_and_default_baseline():
    run=simulate(8,86400,'enhanced')
    assert min(e['start_s'] for e in run.truth)>=7200
    assert len(run.truth)>=16
    assert len(run.evidence['samples'])==86400
    assert {'maintenance','quality','pfmea','control_plan'} <= run.evidence.keys()
    assert run.evidence['samples'][-1]['part_count']+run.evidence['samples'][-1]['scrap_count']==run.evidence['samples'][-1]['stroke_count']

def test_starvation_consumes_buffer_before_press_stops_and_recovers():
    run=simulate(4,1800,'enhanced',events=[dict(event_class='material_starvation',start_s=120,end_s=1200,severity=1)])
    rows=run.evidence['samples']
    assert rows[150]['press_run']==1
    assert rows[1000]['material_present']==0
    assert rows[1000]['press_stop']==1
    assert rows[1500]['press_run']==1
    assert rows[1000]['stroke_count']==rows[990]['stroke_count']

def test_dropouts_affect_observation_not_production():
    base=simulate(4,600,'enhanced',events=[])
    drop=simulate(4,600,'enhanced',events=[dict(event_class='historian_dropout',start_s=120,end_s=300,severity=1)])
    assert drop.evidence['samples'][200]['stroke_count'] is None
    assert drop.evidence['samples'][400]['stroke_count']==base.evidence['samples'][400]['stroke_count']

def test_wear_load_precedes_delayed_quality():
    rows=simulate(4,900,'enhanced',events=[dict(event_class='progressive_die_wear',start_s=120,end_s=600,severity=1)]).evidence['samples']
    assert rows[150]['tonnage']>rows[100]['tonnage']+1
    assert rows[150]['quality_measurement']==rows[100]['quality_measurement']
    assert rows[400]['quality_measurement']>.15

def test_input_validation():
    import pytest
    with pytest.raises(ValueError): simulate(duration_s=0)
    with pytest.raises(ValueError): simulate(profile='silent')
    with pytest.raises(ValueError): simulate(duration_s=100,events=[dict(event_class='misfeed',start_s=0,end_s=200)])

def test_operator_action_at_origin_is_a_public_record():
    run=simulate(4,120,'enhanced',events=[dict(event_class='operator_speed_change',start_s=0,end_s=90)])
    assert any(e['type']=='operator_speed_setpoint' and e['t']==0 for e in run.evidence['events'])

def test_all_mechanisms_manifest_recover_and_preserve_profile_truth():
    import statistics
    base=simulate(14,2400,'enhanced',events=[]).evidence['samples']
    signal_for={'feeder_sensor_drift':'feeder_position','feeder_mechanical_instability':'feeder_position','misfeed':'strip_progression','material_starvation':'material_present','decoiler_interruption':'decoiler_ready','lubrication_pressure_loss':'lube_pressure','die_protection_trip':'die_protection','progressive_die_wear':'quality_measurement','abnormal_tonnage':'tonnage','press_speed_degradation':'spm','repeated_microstops':'feed_complete','quality_deterioration':'quality_measurement','operator_speed_change':'spm','planned_stop':'press_stop','historian_dropout':'spm','stuck_sensor':'spm'}
    for entry in catalog():
        cls=entry['event_class']; events=[dict(event_class=cls,start_s=300,end_s=1500,severity=1)]
        enhanced=simulate(14,2400,'enhanced',events=events)
        sparse=simulate(14,2400,'sparse',events=events)
        assert enhanced.truth==sparse.truth
        rows=enhanced.evidence['samples']; sig=signal_for[cls]
        during=[r[sig] for r in rows[900:1400]]
        assert during != [r[sig] for r in base[900:1400]],cls
        if cls=='historian_dropout': assert all(x is None for x in during)
        elif cls=='stuck_sensor': assert len(set(during))==1
        else: assert any(abs(float(a)-float(b))>.01 for a,b in zip(during,[r[sig] for r in base[900:1400]])),cls
        # Restart and analog recovery: counts legitimately retain historical loss.
        assert rows[2200]['press_run']==1,cls
        assert abs(rows[2200]['spm']-base[2200]['spm'])<.001,cls
        for x,y in zip(sparse.evidence['samples'],rows):
            assert all(x[k]==y[k] for k in profile_signals('sparse'))

def test_buffer_reserve_recovers_after_material_supply_returns():
    rows=simulate(4,2400,'enhanced',events=[dict(event_class='material_starvation',start_s=120,end_s=1200,severity=1)]).evidence['samples']
    assert rows[2300]['loop_height']>.8

def test_plc_records_restart_and_material_count_conservation():
    run=simulate(8,600,'enhanced',events=[dict(event_class='planned_stop',start_s=120,end_s=300)])
    rows=run.evidence['samples']
    assert set(r['plc_state'] for r in rows[:100]) <= {'FEED','STROKE'}
    assert 'STROKE' in {r['plc_state'] for r in rows[:100]}
    assert rows[200]['plc_state']=='CHANGEOVER'
    assert rows[200]['stroke_count']==rows[150]['stroke_count']
    assert rows[400]['stroke_count']>rows[300]['stroke_count']
    assert all(r['strip_progression']==r['stroke_count'] for r in rows)
    assert any(e['type']=='plc_restart' and e['t']==300 for e in run.evidence['events'])

def test_observed_speed_setpoint_changes_and_returns_with_operator_record():
    from ekas_press_intelligence.domain import signals,profile_signals
    assert 'rate_setpoint' in profile_signals('sparse')
    assert next(s for s in signals() if s['signal_id']=='rate_setpoint')['existing']
    run=simulate(8,600,'sparse',events=[dict(event_class='operator_speed_change',start_s=120,end_s=300)])
    assert run.evidence['samples'][100]['rate_setpoint']==60
    assert run.evidence['samples'][200]['rate_setpoint']==42
    assert run.evidence['samples'][400]['rate_setpoint']==60
    assert any(e['type']=='operator_speed_setpoint' and e['t']==300 and e['rate_spm']==60 for e in run.evidence['events'])

def test_scan_endpoint_plc_state_matches_completed_strokes_at_normal_and_fractional_rate():
    for fractional in (False,True):
        events=[dict(event_class='operator_speed_change',start_s=0,end_s=600)] if fractional else []
        rows=simulate(8,600,'enhanced',events=events).evidence['samples']
        previous=0
        for row in rows:
            completed=row['stroke_count']-previous
            assert row['plc_state']==('STROKE' if completed else 'FEED'), (fractional,row['t'],completed,row['plc_state'])
            previous=row['stroke_count']
        assert rows[200]['rate_setpoint']==(42 if fractional else 60)
        if fractional: assert {'FEED','STROKE'}==set(r['plc_state'] for r in rows)

def test_stuck_flag_requires_observed_plateau_and_independent_production():
    rows=simulate(8,600,'sparse',events=[dict(event_class='stuck_sensor',start_s=120,end_s=300)]).evidence['samples']
    assert all('STUCK' not in r['data_quality'].values() for r in rows[120:150])
    assert rows[150]['data_quality']['spm']=='STUCK'
    assert not rows[301]['data_quality']
    normal=simulate(8,600,'sparse',events=[]).evidence['samples']
    planned=simulate(8,600,'sparse',events=[dict(event_class='planned_stop',start_s=120,end_s=300)]).evidence['samples']
    assert not any('STUCK' in r['data_quality'].values() for r in normal+planned)

def test_acquisition_monitor_detects_unlabeled_freeze_and_none_from_observations():
    from ekas_press_intelligence.acquisition import AcquisitionMonitor
    monitor=AcquisitionMonitor()
    for t in range(30):
        assert monitor.observe(t,{'spm':59.8,'stroke_count':t})=={}
    assert monitor.observe(30,{'spm':59.8,'stroke_count':30})=={'spm':'STUCK'}
    assert monitor.observe(31,{'spm':59.9,'stroke_count':31})=={}
    assert monitor.observe(32,{'spm':None,'stroke_count':None})=={'spm':'MISSING','stroke_count':'MISSING'}
    for t in range(33,100):
        assert monitor.observe(t,{'spm':0,'stroke_count':32})=={}
