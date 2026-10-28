import importlib.util
from pathlib import Path


def test_campaign_gate_rejects_a_green_physics_report_with_diagnostic_failure():
    spec=importlib.util.spec_from_file_location('campaign_gate',Path(__file__).parents[1]/'scripts/check_campaign.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.violations({'source_stable_during_run':True,'profiles':{}})
    bad={'source_stable_during_run':True,'profiles':{'enhanced':{
        'physics':{'passed':True},'scoring':{'incorrect_cause':1,'false_positives':0,'missed':0},
        'deterministic':True}}}
    assert module.violations(bad)
