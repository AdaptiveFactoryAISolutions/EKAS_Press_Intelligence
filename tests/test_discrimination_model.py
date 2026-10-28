from ekas_press_intelligence.observability.model import assess, sensor_gaps
from ekas_press_intelligence.domain import profile_signals


def test_pairwise_coverage_and_recomputed_gain():
    sparse = profile_signals('sparse')
    result = assess(sparse)
    assert result['coverage']['denominator'] == 16
    assert result['pair_coverage']['denominator'] > 0
    assert result['unresolved_equivalence_groups']
    for gap in sensor_gaps(sparse):
        augmented = assess(sparse + [gap['signal']])
        assert gap['expected_diagnostic_gain']['pairs'] == augmented['pair_coverage']['numerator'] - result['pair_coverage']['numerator']
        assert gap['expected_diagnostic_gain']['pairs'] > 0
    assert assess(profile_signals('enhanced'))['pair_coverage']['numerator'] >= result['pair_coverage']['numerator']


def test_required_pair_observations_and_partial_upgrade():
    base=profile_signals('sparse')
    def pair(result,a,b):
        return next(p for p in result['pairs'] if set(p['classes'])=={a,b})
    a='feeder_mechanical_instability'; b='material_starvation'
    initial=pair(assess(base),a,b)
    assert not initial['distinguishable']
    assert set(initial['missing_discriminators'])=={'feeder_position','material_present'}
    assert not pair(assess(base+['feeder_position']),a,b)['distinguishable']
    assert pair(assess(base+['feeder_position','material_present']),a,b)['distinguishable']


def test_gains_are_conditional_not_independently_additive():
    base=profile_signals('sparse')
    first=sensor_gaps(base)
    chosen=next(g['signal'] for g in first)
    second=sensor_gaps(base+[chosen])
    assert chosen not in [g['signal'] for g in second]
    for gap in second:
        augmented=assess(base+[chosen,gap['signal']])
        current=assess(base+[chosen])
        assert gap['expected_diagnostic_gain']['pairs']==augmented['pair_coverage']['numerator']-current['pair_coverage']['numerator']


def test_new_hardware_plc_feasibility_is_unknown_without_controller_evidence():
    gaps=sensor_gaps(profile_signals('sparse'))
    existing=[g for g in gaps if g['current_source_available']]
    hardware=[g for g in gaps if g['hardware_required']]
    assert existing and hardware
    assert all(g['plc_input_possible'] is True for g in existing)
    assert all(g['plc_input_possible'] is None for g in hardware)
