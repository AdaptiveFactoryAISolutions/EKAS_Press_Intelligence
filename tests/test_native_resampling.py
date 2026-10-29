import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def test_native_resample_collision_and_layout_regression():
    runtime=ROOT/'work/resampling-test-runtime'
    prepared=subprocess.run([sys.executable,'scripts/prepare_native_runtime.py','--target',str(runtime)],cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert prepared.returncode==0,prepared.stderr[-4000:]
    code='''
import tempfile
from pathlib import Path
import pandas as pd
from historiansim.pipeline import generate,write_dataset
from historiansim.scenarios import build_scenario
from historiansim.validation.recipe import audit_dataset_dir
from historiansim.challenge import make_challenge
from historiansim.challenge import load_scoring_key
from historiansim.scoring import score_submission
cfg=build_scenario('tank-clean',profile='quick',seed=7,days=.02,ballast=0,n_faults=0)
cfg.episodes.n_benign=0;cfg.episodes.baseline_days=0
data=generate(cfg)
with tempfile.TemporaryDirectory() as directory:
    base=Path(directory)
    for seconds in (1,2.5,10,15,25,30,60,120):
        target=base/str(seconds);write_dataset(data,target,resample_s=seconds)
        assert set(pd.read_parquet(target/'historian_10s.parquet').columns)=={'timestamp','tag','value','quality'}
        assert (target/'historian_60s.parquet').exists()
        checks=audit_dataset_dir(target)
        assert all(c.passed for c in checks),[(c.name,c.detail) for c in checks if not c.passed]
        challenge=base/('challenge'+str(seconds));make_challenge(target,challenge)
        suffix=str(seconds).replace('.','p')
        grid='historian_grid_10s.parquet' if seconds==10 else f'historian_{suffix}s.parquet'
        assert (challenge/grid).exists()
        exported=pd.read_parquet(challenge/grid)
        assert exported.timestamp.diff().dropna().dt.total_seconds().eq(seconds).all()
        labels=pd.read_parquet(target/'metadata'/f'labels_{suffix}s.parquet')
        assert labels.timestamp.equals(exported.timestamp)
        assert not (challenge/'metadata').exists()
    cfg.time.dt_scan=7.0
    cfg.time.dt_sim=1.0
    data=generate(cfg)
    target=base/'scan7';write_dataset(data,target,resample_s=15)
    canonical=pd.read_parquet(target/'historian_60s.parquet')
    labels=pd.read_parquet(target/'metadata/labels_60s.parquet')
    assert canonical.timestamp.equals(labels.timestamp)
    frozen=base/'empty.csv';frozen.write_text('start_utc,end_utc,kind,root_cause,evidence_tags\\n')
    score=score_submission(load_scoring_key(target),frozen)
    assert score['max_points']==0 and score['false_positives']==0 and score['discarded_rows']==0
    from ekas_press_intelligence.native.engine import execute
    result=execute('generate',{'config':cfg.model_dump(mode='json'),'resample':2.5,'validate':False},base/'service',Path.cwd())
    assert (base/'service/public/historian_2p5s.parquet').exists()
    assert any(f['name']=='historian_2p5s.parquet' for f in result['files'])
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(runtime/'src')),capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stderr[-4000:]
