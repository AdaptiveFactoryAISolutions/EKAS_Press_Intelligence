from ekas_press_intelligence.observability.coverage import assess_observability
from ekas_press_intelligence.domain import profile_signals


def test_missing_discriminator_is_reported_not_invented():
    result=assess_observability(['press_run'])
    feeder=next(c for c in result['classes'] if c['event_class']=='feeder_sensor_drift')
    assert feeder['status']=='NOT_OBSERVABLE'
    assert any('feeder_position' in p['missing_discriminators'] for p in result['pairs'])


def test_signal_can_resolve_ambiguity():
    result=assess_observability(profile_signals('enhanced'))
    feeder=next(c for c in result['classes'] if c['event_class']=='feeder_sensor_drift')
    assert feeder['status']=='FULLY_DISTINGUISHABLE'
