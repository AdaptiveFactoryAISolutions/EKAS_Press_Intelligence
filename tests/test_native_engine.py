from pathlib import Path
import pytest
from ekas_press_intelligence.native.engine import execute
from ekas_press_intelligence.native.catalog import capabilities
ROOT=Path(__file__).resolve().parents[1]

def test_native_catalog_and_strict_options(tmp_path):
    assert 'standard' in [p['name'] for p in capabilities(ROOT)['profiles']]
    with pytest.raises(ValueError): execute('generate',{'ignored_option':True},tmp_path,ROOT)
    with pytest.raises(ValueError): execute('generate',{'days':0},tmp_path,ROOT)
    with pytest.raises(ValueError): execute('generate',{'no_fault':True,'faults':2},tmp_path,ROOT)

def short_config():
    from historiansim.scenarios import build_scenario
    cfg=build_scenario('exchanger-fouling',profile='quick',seed=17,days=0.02,ballast=0,n_faults=0)
    cfg.episodes.n_benign=0
    cfg.episodes.baseline_days=0
    return cfg


def test_real_native_generate_parity_and_public_boundary(tmp_path):
    import json
    import pandas as pd
    from historiansim.pipeline import generate, write_dataset
    cfg=short_config()
    direct=tmp_path/'direct'
    write_dataset(generate(cfg),direct)
    result=execute('generate',{'config':cfg.model_dump(mode='json'),'validate':False},tmp_path/'service',ROOT)
    private=tmp_path/'service/private'; public=tmp_path/'service/public'
    for name in ['historian_10s.parquet','historian_60s.parquet']:
        pd.testing.assert_frame_equal(pd.read_parquet(direct/name),pd.read_parquet(private/name))
    assert (private/'metadata/ground_truth.json').exists()
    assert not (public/'metadata').exists()
    assert 'ground_truth' not in json.dumps(result)
    assert result['validation_performed'] is False
    assert result['passed'] is None
    assert result['dataset']['rows']>0


def test_non60_preserved_and_strict_full_config(tmp_path):
    cfg=short_config().model_dump(mode='json')
    result=execute('generate',{'config':cfg,'resample':120,'validate':False},tmp_path/'run',ROOT)
    assert result['resample']['native_challenge_canonical_60s_added']
    assert (tmp_path/'run/public/historian_120s.parquet').exists()
    assert (tmp_path/'run/public/historian_60s.parquet').exists()
    cfg['time']['ignored']=1
    with pytest.raises(ValueError): execute('generate',{'config':cfg},tmp_path/'bad',ROOT)


def test_real_native_operations(tmp_path):
    import json
    cfg=short_config()
    execute('generate',{'config':cfg.model_dump(mode='json'),'validate':False},tmp_path/'generated',ROOT)
    folder=str(tmp_path/'generated/private')
    validation=execute('validate',{'dataset_dir':folder},tmp_path/'validation',ROOT)
    assert len(validation['validation'])>0
    assert all(set(c)=={'name','passed','severity'} for c in validation['validation'])
    assert (tmp_path/'validation/private/validation.json').exists()
    assert isinstance(validation['passed'],bool)
    desc=execute('describe_process',{'dataset_dir':folder},tmp_path/'description',ROOT)
    assert 'PROCESS_DESCRIPTION.md'==desc['artifact']
    challenge=execute('make_challenge',{'dataset_dir':folder},tmp_path/'challenge',ROOT)
    assert challenge['dataset']['rows']>0
    plot=execute('plot',{'dataset_dir':folder,'tags':['TIC-101.PV'],'days':[0,0.01]},tmp_path/'plot',ROOT)
    assert (tmp_path/'plot'/plot['artifact']).stat().st_size>0
    report=execute('report',{'dataset_dir':folder},tmp_path/'report',ROOT)
    summary=execute('summarise',{'dataset_dir':folder},tmp_path/'summary',ROOT)
    assert report['evaluator_only'] and summary['evaluator_only']
    assert summary['text']
    stage=execute('plant_check',{'plant':'exothermic_cstr','stage':1},tmp_path/'plant',ROOT)
    assert stage['passed']


def test_native_silent_clamp_rejected(tmp_path):
    with pytest.raises(ValueError,match='dt_sim'):
        execute('generate',{'days':0.02,'dt_sim':20,'scan':10,'faults':0,'validate':False},tmp_path/'clamp',ROOT)


def test_plot_private_key_never_shades_by_default(tmp_path,monkeypatch):
    import historiansim.plotting
    calls=[]
    def capture(*args,**kwargs): calls.append(kwargs)
    monkeypatch.setattr(historiansim.plotting,'plot_dataset',capture)
    folder=tmp_path/'dataset'; folder.mkdir()
    result=execute('plot',{'dataset_dir':str(folder),'tags':['A']},tmp_path/'plot',ROOT)
    assert calls[0]['shade_episodes'] is False
    assert not result['evaluator_only']


def test_new_plant_scaffold_uses_native_template_without_vendor_mutation(tmp_path):
    from historiansim import scaffold
    original=Path(scaffold.__file__).parent/'plants'/'bounded_test_plant'
    assert not original.exists()
    result=execute('new_plant',{'name':'bounded_test_plant','equipment':'P-123'},tmp_path/'authoring',ROOT)
    assert result['evaluator_only']
    assert result['plant_directory'].endswith('plants/bounded_test_plant')
    plant=tmp_path/'authoring'/result['plant_directory']
    assert (plant/'DESIGN.md').exists()
    assert '{{NAME}}' not in (plant/'model.py').read_text()
    assert not original.exists()


def test_config_flags_strict_and_target_symlink(tmp_path):
    with pytest.raises(ValueError):
        execute('generate',{'config':short_config().model_dump(mode='json'),'validate':'false'},tmp_path/'wrongflag',ROOT)
    (tmp_path/'link').symlink_to(tmp_path/'real')
    with pytest.raises(ValueError): execute('describe_process',{'plant':'heated_tank'},tmp_path/'link',ROOT)
