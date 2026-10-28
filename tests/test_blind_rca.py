from ekas_press_intelligence.rca.engine import investigate


def evidence(changes=None, quality=None, events=None):
    rows=[]
    for t in range(120):
        row={'t':t,'spm':60.,'lube_pressure':4.,'tonnage':100.,'press_run':True,'part_count':t,'data_quality':quality or {}}
        if t>=60: row.update(changes or {})
        rows.append(row)
    return {'samples':rows,'context':{'duration_s':120,'analysis_start_s':0,'analysis_end_s':119},'events':events or []}


def test_question_cannot_inject_cause_and_missing_evidence_stays_uncertain():
    a=investigate(evidence({'spm':40.}), 'feeder failure')
    b=investigate(evidence({'spm':40.}), 'lubrication failure')
    assert a['hypotheses']==b['hypotheses']
    assert a['diagnosis_state'] != 'VERIFIED_ROOT_CAUSE'
    assert a['alternatives']
    assert all('missing_evidence' in h for h in a['hypotheses'])


def test_pressure_evidence_and_provenance():
    result=investigate(evidence({'lube_pressure':1.,'spm':40.}))
    assert result['hypotheses'][0]['event_class']=='lubrication_pressure_loss'
    assert result['hypotheses'][0]['supporting_evidence']
    assert all({'id','source','signal','asset','timestamp','calculation','rule','confidence','qualification'} <= e.keys() for e in result['evidence'])


def test_artifact_is_not_equipment_failure():
    result=investigate(evidence({'spm':0.}, {'spm':'MISSING'}))
    assert result['hypotheses'][0]['event_class']=='historian_dropout'
    assert result['diagnosis_state'] != 'VERIFIED_ROOT_CAUSE'


def test_operator_change_is_benign():
    result=investigate(evidence({'spm':40.},events=[{'t':60,'type':'operator_speed_change','message':'Rate changed'}]))
    assert result['hypotheses'][0]['event_class']=='operator_speed_change'


def test_ambient_correlation_and_truth_injection_do_not_influence_hypotheses():
    clean=evidence()
    altered=evidence({'ambient_temperature':45.})
    altered['truth']={'event_class':'lubrication_pressure_loss'}
    result=investigate(altered)
    assert all(h['disposition']!='SUPPORTED' for h in result['hypotheses'])
    assert result['diagnosis_state']=='OBSERVED_ANOMALY'


def test_period_filters_operator_records():
    result=investigate(evidence({'spm':40.},events=[{'t':999,'type':'operator_speed_change'}]))
    assert result['hypotheses'][0]['event_class']!='operator_speed_change'


def test_data_quality_has_provenance():
    result=investigate(evidence(quality={'spm':'MISSING'}))
    assert any(e['source']=='historian_quality' for e in result['evidence'])


def test_all_catalog_mechanisms_against_blind_measured_simulation():
    from ekas_press_intelligence.simulator.engine import simulate
    from ekas_press_intelligence.domain import catalog
    for entry in catalog():
        result=simulate(7,1600,'enhanced',events=[{'event_class':entry['event_class'],'start_s':300,'end_s':1500}])
        public=result.evidence
        public['baseline_samples']=public['samples'][:250]
        public['context'].update(analysis_start_s=300,analysis_end_s=1450)
        diagnosis=investigate(public)
        assert diagnosis['hypotheses'][0]['event_class']==entry['event_class']
        assert diagnosis['diagnosis_state']!='VERIFIED_ROOT_CAUSE'
        assert diagnosis['period']=={'start_s':300,'end_s':1450}
        known={fact['id'] for fact in diagnosis['evidence']}
        for hypothesis in diagnosis['hypotheses']:
            assert set(hypothesis['supporting_evidence']) <= known


def test_sparse_shared_stop_does_not_verify_failure():
    from ekas_press_intelligence.simulator.engine import simulate
    run=simulate(7,1600,'sparse',events=[{'event_class':'material_starvation','start_s':300,'end_s':1500}])
    public=run.evidence;public['baseline_samples']=public['samples'][:250]
    public['context'].update(analysis_start_s=300,analysis_end_s=1450)
    result=investigate(public)
    material=next(h for h in result['hypotheses'] if h['event_class']=='material_starvation')
    assert material['disposition']=='NOT_OBSERVABLE'
    assert result['diagnosis_state']!='VERIFIED_ROOT_CAUSE'


def test_isolated_sensor_spike_is_not_physical_failure():
    public=evidence()
    public['samples'][100]['feeder_position']=140.
    for sample in public['samples']:
        sample.setdefault('feeder_position',100.)
    result=investigate(public)
    assert not any(h['disposition']=='SUPPORTED' and h['event_kind']=='fault' for h in result['hypotheses'])


def test_enhanced_complete_mechanism_eliminates_shared_stop_symptoms():
    from ekas_press_intelligence.simulator.engine import simulate
    run=simulate(7,2200,'enhanced',events=[{'event_class':'material_starvation','start_s':300,'end_s':2100}])
    public=run.evidence;public['baseline_samples']=public['samples'][:250]
    public['context'].update(analysis_start_s=900,analysis_end_s=2099)
    result=investigate(public)
    assert result['hypotheses'][0]['event_class']=='material_starvation'
    assert result['diagnosis_state']=='EVIDENCE_SUPPORTED_CAUSE'
    assert next(h for h in result['hypotheses'] if h['event_class']=='repeated_microstops')['disposition']=='CONTRADICTED'


def test_missing_essential_mechanism_cannot_be_contradicted_by_secondary_symptom():
    public=evidence({'spm':20.,'press_fault':1.})
    result=investigate(public)
    hypothesis=next(h for h in result['hypotheses'] if h['event_class']=='abnormal_tonnage')
    # Without measured load, stop-state behavior cannot rule out a load fault.
    public_no_load=evidence({'spm':20.,'press_fault':1.})
    for row in public_no_load['samples']: row.pop('tonnage')
    result=investigate(public_no_load)
    assert next(h for h in result['hypotheses'] if h['event_class']=='abnormal_tonnage')['disposition']=='NOT_OBSERVABLE'


def test_sparse_trip_does_not_eliminate_uninstrumented_feed_alternative():
    from ekas_press_intelligence.simulator.engine import simulate
    run=simulate(7,1600,'sparse',events=[{'event_class':'die_protection_trip','start_s':300,'end_s':1500}])
    public=run.evidence;public['baseline_samples']=public['samples'][:250]
    public['context'].update(analysis_start_s=300,analysis_end_s=1450)
    result=investigate(public)
    assert result['diagnosis_state']=='SUSPECTED_CAUSE'
    assert result['cause_claim_eligible'] is False


def test_static_position_offset_does_not_prove_progressive_drift():
    public=evidence({'spm':0.})
    for sample in public['samples']: sample['feeder_position']=102.
    public['baseline_samples']=[dict(row,feeder_position=100.) for row in public['samples'][:30]]
    result=investigate(public)
    drift=next(h for h in result['hypotheses'] if h['event_class']=='feeder_sensor_drift')
    assert drift['disposition']!='SUPPORTED'


def test_context_records_link_to_hypotheses_without_overriding_measurements():
    public=evidence()
    public['maintenance']=[{'work_order_id':'WO-1','asset':'Feeder 27','repeat_failure':True,'date':'2026-10-01'}]
    public['pfmea']=[{'process_step':'Feed strip','failure_mode':'Incomplete feed','asset':'Feeder 27','detection_control':'feed_complete'}]
    public['control_plan']=[{'asset':'Feeder 27','process_step':'Feed strip','reaction_plan':'Stop and inspect'}]
    result=investigate(public)
    target=next(h for h in result['hypotheses'] if h['event_class']=='feeder_mechanical_instability')
    assert {'maintenance-0','pfmea-0','control-plan-0'} <= set(target['contextual_evidence'])
    assert target['disposition']!='SUPPORTED'
    context=[f for f in result['evidence'] if f['source'] in ('maintenance_record','pfmea_prior','control_plan_prior')]
    assert len(context)==3
    assert all(f['quality']=='CONTEXTUAL' for f in context)


def test_inspection_quality_trend_is_explicit_measured_evidence():
    public=evidence()
    for row in public['samples']: row.pop('tonnage')
    public['quality']=[{'t':t,'quality_measurement':.02 if t<60 else .25,'scrap_count':0 if t<60 else (t-60)//5} for t in range(0,120,5)]
    result=investigate(public)
    quality=next(h for h in result['hypotheses'] if h['event_class']=='quality_deterioration')
    assert 'inspection-quality_measurement' in quality['supporting_evidence']
    assert quality['disposition']=='NOT_OBSERVABLE' # missing load prevents die-wear elimination
    assert any(f['source']=='quality_inspection' and f['quality']=='GOOD' for f in result['evidence'])
