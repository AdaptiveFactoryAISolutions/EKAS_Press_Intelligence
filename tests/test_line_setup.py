import math
import pytest


def test_standard_line_is_complete_and_coherent():
    from ekas_press_intelligence.line_setup import LineSetup, fields, preflight
    config=LineSetup()
    result=preflight(config)
    assert config.stations==10 and config.speed_spm==8
    assert result['passed'] and result['practice']
    assert len(result['config_sha256'])==64
    assert {x['name'] for x in fields()}==set(type(config).model_fields)
    assert all(x['help'] and x['tooltip'] for x in fields())
    assert set(x['step'] for x in fields())=={2,3,4,5,6}


def test_default_packing_supports_maximum_press_speed_with_container_changes():
    from ekas_press_intelligence.line_setup import LineSetup, preflight
    result=preflight(LineSetup(speed_spm=10))
    assert result['passed']
    assert not result['requires_bottleneck_acknowledgment']


@pytest.mark.parametrize('change',[
    {'speed_spm':600},{'stations':9},{'stations':10.5},{'speed_spm':True},
    {'speed_spm':math.nan},{'coil_mass_kg':-1},{'force_unit':'ton'},
    {'unexpected':1},{'feed_window_s':.01},{'loop_initial_m':20},
    {'forming_force_tons':2000},{'packers':1.5},{'duration_minutes':.01},
    {'thickness_mm':3},
    {'buffer_parts':1,'parts_per_stroke':4},
])
def test_invalid_configuration_is_rejected(change):
    from ekas_press_intelligence.line_setup import LineSetup
    with pytest.raises(ValueError):LineSetup.model_validate(change)


def test_units_convert_actual_force_and_hash_changes():
    from ekas_press_intelligence.line_setup import LineSetup, preflight, parameters
    ratio=9806.65/8896.443230521
    metric=LineSetup();short=LineSetup(force_unit='short_ton_force',capacity_tons=1500*ratio,forming_force_tons=1000*ratio)
    assert parameters(metric)['capacity_n']==pytest.approx(1500*9806.65)
    assert parameters(short)['capacity_n']==pytest.approx(parameters(metric)['capacity_n'])
    assert parameters(short)['forming_force_n']==pytest.approx(parameters(metric)['forming_force_n'])
    assert preflight(metric)['config_sha256']!=preflight(short)['config_sha256']


def test_bottleneck_is_explicit_warning_not_invalid_base_config():
    from ekas_press_intelligence.line_setup import LineSetup,preflight
    result=preflight(LineSetup(packers=1,packing_rate_per_min=1))
    assert result['passed'] and any('packing' in x.lower() for x in result['warnings'])
    assert result['requires_bottleneck_acknowledgment']
    assert not preflight(LineSetup(packers=1,packing_rate_per_min=1,allow_bottleneck='yes'))['requires_bottleneck_acknowledgment']


def test_scheduled_fault_fits_practice_run():
    from ekas_press_intelligence.line_setup import LineSetup
    with pytest.raises(ValueError):LineSetup(test_case='feed_slip',fault_start_minutes=59,duration_minutes=60)
