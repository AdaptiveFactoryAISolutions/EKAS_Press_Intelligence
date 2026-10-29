"""Run named CI layers; absent files, no collected tests and skips fail closed."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

LAYERS = {
    'unit': ['tests/test_foundation.py','tests/test_storage.py','tests/test_verification.py','tests/test_benchmark_scoring.py','tests/test_sources.py'],
    'simulation': ['tests/test_simulation.py','tests/test_campaign_validation.py','tests/test_campaign_gate.py'],
    'contract': ['tests/test_api.py::test_versioned_machine_contract_covers_every_operation','tests/test_foundation.py'],
    'blind': ['tests/test_blind_rca.py','tests/test_security.py','tests/test_temporal_benchmark.py'],
    'observability': ['tests/test_observability.py','tests/test_discrimination_model.py'],
    'api': ['tests/test_api.py','tests/test_storage.py'],
    'ui': ['tests/test_api.py::test_routes_and_ui_assets'],
    'browser': ['tests/test_browser.py'],
}

def main():
    if len(sys.argv)!=2 or sys.argv[1] not in LAYERS:
        raise SystemExit('Usage: python3 scripts/test_layer.py '+ '|'.join(LAYERS))
    targets=LAYERS[sys.argv[1]]
    for target in targets:
        if not Path(target.split('::')[0]).is_file():raise SystemExit('Missing required test: '+target)
    env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    with tempfile.TemporaryDirectory() as directory:
        report=Path(directory)/'tests.xml'
        result=subprocess.run([sys.executable,'-m','pytest','-q',*targets,'--junitxml='+str(report)],env=env,timeout=1800)
        if result.returncode:return result.returncode
        cases=ET.parse(report).getroot().findall('.//testcase')
        if not cases or any(case.find('skipped') is not None for case in cases):
            raise SystemExit('Required CI layer may not be empty or skipped')
    return 0

if __name__=='__main__':raise SystemExit(main())
