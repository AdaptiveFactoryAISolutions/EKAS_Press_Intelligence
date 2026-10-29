"""Optional configuration-aware events must preserve all original schedules."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def test_original_episode_plans_including_benign_moves_are_exactly_preserved():
    spec=importlib.util.spec_from_file_location('native_benign_preparer',ROOT/'scripts/prepare_native_runtime.py')
    preparer=importlib.util.module_from_spec(spec);spec.loader.exec_module(preparer)
    code='''
import json,sys
from dataclasses import asdict
from historiansim.core.rng import SeedBank
from historiansim.faults.scheduler import build_episode_plan
from historiansim.scenarios import build_scenario
from historiansim.plants.base import BenignEvent
if sys.argv[1]=='patched':
 assert hasattr(BenignEvent,'build_for_config'),'Declared configuration hook patch was not applied'
records={}
for scenario in ('tank-rca','cstr-rca'):
 for seed in (7,19,42):
  cfg=build_scenario(scenario,profile='standard',seed=seed)
  plan=build_episode_plan(cfg,SeedBank(seed))
  assert sum(ep.kind=='benign' for ep in plan.episodes)>=2
  records[scenario+':'+str(seed)]=asdict(plan)
print(json.dumps(records,default=str,sort_keys=True))
'''
    (ROOT/'work').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='native-benign-parity-',dir=ROOT/'work') as scratch:
        runtime=preparer.prepare_runtime(ROOT,Path(scratch)/'runtime')
        records=[]
        for label,source in [('stock',ROOT/'vendor/HistorianSim/src'),('patched',runtime/'src')]:
            env=dict(os.environ,PYTHONPATH=str(source),PYTHONDONTWRITEBYTECODE='1',
                     PYTHONPYCACHEPREFIX=str(Path(scratch)/'cache'))
            result=subprocess.run([sys.executable,'-B','-c',code,label],cwd=ROOT,env=env,
                                  capture_output=True,text=True,timeout=60,check=True)
            records.append(json.loads(result.stdout))
    assert len(records[0])==6 and records[0]==records[1]
