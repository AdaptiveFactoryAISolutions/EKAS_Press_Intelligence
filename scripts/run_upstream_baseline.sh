#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/verify_upstreams.sh"
cd "$ROOT"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 - <<'PY'
import pathlib, sys, types, tempfile, xml.etree.ElementTree as ET
import pytest
root = pathlib.Path.cwd()
sys.path.insert(0, str(root/'vendor/HistorianSim/src'))
p = root/'vendor/HistorianSim/tests'
module = types.ModuleType('tests')
module.__path__ = [str(p)]
sys.modules['tests'] = module
with tempfile.TemporaryDirectory() as directory:
    report = pathlib.Path(directory)/'upstream.xml'
    result = pytest.main([str(p), '-q', '--junitxml='+str(report)])
    if result:
        raise SystemExit(result)
    cases = ET.parse(report).getroot().findall('.//testcase')
    if len(cases) != 173 or any(c.find('skipped') is not None for c in cases):
        raise SystemExit('Pinned upstream baseline must execute exactly 173 tests with no skips')
print('Pinned HistorianSim baseline: 173 passed, zero skips')
PY
