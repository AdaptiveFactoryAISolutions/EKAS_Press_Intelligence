from ekas_press_intelligence.benchmark.evaluator import score


def event(start=10, end=20, kind='fault'):
    return dict(start_s=start,end_s=end,event_kind=kind,event_class='feeder_sensor_drift',failed_item='position transducer',failure_mechanism='calibration bias increases until feedback rejects feed',asset='press')


def claim(start=10,end=20,**kw):
    return dict(start_s=start,end_s=end,event_kind='fault',failed_item='position transducer',failure_mechanism='calibration bias increases until feedback rejects feed',evidence=['sample:12'],alternatives=[],diagnosis_state='SUSPECTED_CAUSE',**kw)


def test_longest_overlap_one_to_one_duplicates_and_spanning():
    result=score([event(),event(30,60)],[claim(10,60),claim(30,60)])
    assert result['detected']==2
    assert result['matches'][0]['truth_index']==1
    assert score([event()],[claim(),claim()])['false_positives']==1


def test_temporal_no_partial_delayed_and_tolerance():
    assert score([event()],[claim(22,25)])['missed']==1
    assert score([event()],[claim(19,25)])['detected']==1
    assert score([event()],[claim(19,25)])['timing']['recognition_delay_s']==[9]
    assert score([event()],[claim(21,25)])['detected']==1


def test_item_and_mechanism_and_validated_evidence():
    c=claim(); c['failure_mechanism']='wear'
    assert score([event()],[c])['incorrect_cause']==1
    assert score([event()],[claim()])['evidence_completeness']==0
    assert score([event()],[claim()],{'sample:12':{'t':12,'signal':'feeder_position','quality':'good','calculation':{'baseline_mean':100,'current_mean':102,'difference':2}}})['evidence_completeness']==1
    assert score([event()],[claim()],{'sample:12':{'t':100,'signal':'feeder_position','quality':'good','calculation':{'baseline_mean':100,'current_mean':102,'difference':2}}})['evidence_completeness']==0


def test_benign_artifact_and_unsupported_certainty():
    assert score([event(kind='benign')],[claim()])['false_positives']==1
    c=claim(); c['event_kind']='artifact'
    assert score([event(kind='artifact')],[c])['detected']==1
    c=claim(); c['diagnosis_state']='VERIFIED_ROOT_CAUSE'
    result=score([event()],[c]); assert result['unsupported_certainty_violations']==1
    assert result['points']==0


def test_arbitrary_alternatives_do_not_earn_correct_unresolved_credit():
    c=claim(); c.update(failed_item=None,failure_mechanism=None,alternatives=['anything'])
    assert score([event()],[c],{'sample:12':{'t':12,'signal':'feeder_position','quality':'good','calculation':{'baseline_mean':100,'current_mean':102,'difference':2}}})['unresolved_correctly']==0


def test_one_spanning_claim_cannot_detect_two_events():
    assert score([event(),event(30,60)],[claim(10,60)])['detected']==1

import pytest

@pytest.mark.parametrize('value',[float('nan'),float('inf')])
def test_nonfinite_intervals_rejected(value):
    with pytest.raises(ValueError):score([event()],[claim(value,25)])


def test_bad_or_missing_evidence_catalog_reference():
    for catalog in ({},{'sample:12':{'t':12,'signal':'spm','quality':'bad'}},{'invented':{'t':12,'signal':'feeder_position','quality':'good','calculation':{'baseline_mean':100,'current_mean':102,'difference':2}}}):
        assert score([event()],[claim()],catalog)['evidence_completeness']==0


def test_correct_unresolved_requires_true_candidate_and_reason():
    c=claim(); c.update(failed_item=None,failure_mechanism=None,alternatives=[dict(failed_item='position transducer',failure_mechanism='calibration bias increases until feedback rejects feed',disposition='UNRESOLVED',reason='missing discriminator')])
    result=score([event()],[c],{'sample:12':{'t':12,'signal':'feeder_position','quality':'good','calculation':{'baseline_mean':100,'current_mean':102,'difference':2}}})
    assert result['unresolved_correctly']==1
    assert result['correct_cause']==0


def test_no_cause_points_without_evidence_and_no_benign_easy_points():
    assert score([event()],[claim()])['correct_cause']==0
    c=claim();c['event_kind']='benign'
    assert score([event(kind='benign')],[c])['points']==0


def test_die_cause_rejects_ambient_or_zero_change_as_only_proof():
    from ekas_press_intelligence.domain import catalog
    t=next(x for x in catalog() if x['event_class']=='progressive_die_wear')|{'start_s':10,'end_s':20}
    c={k:t[k] for k in ('failed_item','failure_mechanism','start_s','end_s')}; c.update(evidence=['x'],event_kind='fault')
    for signal in ('ambient_temperature','quality_measurement'):
        refs={'x':dict(t=15,signal=signal,quality='GOOD',calculation={'baseline_mean':22,'current_mean':22,'difference':0})}
        result=score([t],[c],refs)
        assert result['correct_cause']==0
        assert result['evidence_completeness']==0


def test_wear_cause_needs_both_changed_quality_and_rising_load():
    from ekas_press_intelligence.domain import catalog
    t=next(x for x in catalog() if x['event_class']=='progressive_die_wear')|{'start_s':10,'end_s':20}
    c={k:t[k] for k in ('failed_item','failure_mechanism','start_s','end_s')};c.update(evidence=['q','load'],event_kind='fault')
    def record(signal,base,current):return dict(t=15,signal=signal,quality='GOOD',calculation={'baseline_mean':base,'current_mean':current,'difference':current-base})
    refs={'q':record('quality_measurement',.02,.2),'load':record('tonnage',100,130)}
    assert score([t],[c],refs)['correct_cause']==1
    refs.pop('load')
    assert score([t],[c],refs)['correct_cause']==0
    refs['load']=record('tonnage',100,80)
    assert score([t],[c],refs)['correct_cause']==0


def test_reference_cannot_override_governed_signals_or_fake_difference():
    c=claim();c['observable_signals']=['ambient_temperature']
    record={'t':12,'signal':'ambient_temperature','quality':'GOOD','calculation':{'baseline_mean':20,'current_mean':30,'difference':10}}
    assert score([event()],[c],{'sample:12':record})['correct_cause']==0
    record.update(signal='feeder_position',calculation={'baseline_mean':100,'current_mean':100,'difference':100})
    assert score([event()],[c],{'sample:12':record})['correct_cause']==0


def test_sparse_unresolved_uses_shared_loss_without_missing_primary_sensor():
    c=claim();c.update(failed_item=None,failure_mechanism=None,alternatives=[dict(failed_item=event()['failed_item'],failure_mechanism=event()['failure_mechanism'],disposition='NOT_OBSERVABLE',reason='position signal unavailable')])
    refs={'sample:12':dict(t=12,signal='spm',quality='GOOD',calculation={'baseline_mean':60,'current_mean':42,'difference':-18})}
    result=score([event()],[c],refs)
    assert result['unresolved_correctly']==1
    assert result['correct_cause']==0


def test_artifact_metadata_is_good_evidence_of_bad_acquisition():
    from ekas_press_intelligence.domain import catalog
    t=next(x for x in catalog() if x['event_class']=='historian_dropout')|{'start_s':10,'end_s':20}
    c=claim();c.update(event_kind='artifact',evidence=['quality-missing'])
    refs={'quality-missing':dict(t=15,signal='data_quality',source='historian_quality',quality='GOOD',observed_quality='MISSING',calculation={'affected_samples':5})}
    assert score([t],[c],refs)['evidence_completeness']==1


def test_material_quality_tolerates_normal_load_noise():
    from ekas_press_intelligence.domain import catalog
    t=next(x for x in catalog() if x['event_class']=='quality_deterioration')|{'start_s':10,'end_s':20}
    c={k:t[k] for k in ('failed_item','failure_mechanism','start_s','end_s')};c.update(event_kind='fault',evidence=['q','load'])
    refs={key:dict(t=15,signal=signal,quality='GOOD',calculation={'baseline_mean':base,'current_mean':cur,'difference':cur-base}) for key,signal,base,cur in [('q','quality_measurement',.02,.2),('load','tonnage',100,100.3)]}
    assert score([t],[c],refs)['correct_cause']==1


def test_transient_overload_needs_peak_and_corroborating_fault():
    from ekas_press_intelligence.domain import catalog
    t=next(x for x in catalog() if x['event_class']=='abnormal_tonnage')|{'start_s':10,'end_s':20}
    c={k:t[k] for k in ('failed_item','failure_mechanism','start_s','end_s')};c.update(event_kind='fault',evidence=['load','fault'],diagnosis_state='EVIDENCE_SUPPORTED_CAUSE')
    refs={'load':dict(t=15,signal='tonnage',quality='GOOD',calculation={'baseline_mean':100,'current_mean':0,'difference':-100,'robust_window_peak':123.7}),'fault':dict(t=15,signal='press_fault',quality='GOOD',calculation={'baseline_mean':0,'current_mean':1,'difference':1})}
    result=score([t],[c],refs)
    assert result['correct_cause']==1
    assert result['unsupported_certainty_violations']==0
    refs.pop('fault')
    assert score([t],[c],refs)['correct_cause']==0


@pytest.mark.parametrize('event_class,signal',[('operator_speed_change','operator_speed_setpoint'),('planned_stop','planned_changeover')])
def test_recorded_operator_action_credits_benign_classification_only(event_class,signal):
    from ekas_press_intelligence.domain import catalog
    t=next(x for x in catalog() if x['event_class']==event_class)|{'start_s':10,'end_s':20}
    c={k:t[k] for k in ('failed_item','failure_mechanism','start_s','end_s')};c.update(event_kind='benign',evidence=['operator'])
    refs={'operator':dict(t=15,signal=signal,source='operator_plc_record',quality='GOOD',calculation=None)}
    result=score([t],[c],refs)
    assert result['evidence_completeness']==1
    assert result['points']==0
    assert result['correct_cause']==0
    refs['operator']['source']='untrusted_note'
    assert score([t],[c],refs)['evidence_completeness']==0
