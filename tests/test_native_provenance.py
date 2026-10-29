import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def test_unknown_runtime_is_rejected_before_app_import(tmp_path):
    env=dict(os.environ,EKAS_NATIVE_RUNTIME=str(tmp_path))
    result=subprocess.run([sys.executable,'-c','from ekas_press_intelligence.native.api import create_native_app'],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode!=0
    assert 'runtime' in result.stderr.lower()


def test_native_server_uses_protected_checkout_and_client_stays_independent():
    from ekas_press_intelligence.native.bootstrap import activate
    from ekas_press_intelligence.native.client import EKASNativeClient
    result=activate()
    assert result['kind']=='immutable_upstream'
    assert Path(result['source']).resolve()==ROOT/'vendor/HistorianSim/src'
