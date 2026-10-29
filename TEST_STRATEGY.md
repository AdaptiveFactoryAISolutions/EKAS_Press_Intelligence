# Test strategy

CI has ten independently visible categories: preservation, pinned HistorianSim regression (exactly 173 tests, no skips), EKAS unit, simulation invariants, executable contract, blind RCA and isolation, observability, API, UI assets, and browser smoke. `scripts/test_layer.py` maps each EKAS category to concrete test files or node IDs. It fails for missing tests, zero collection, test failures or skips. Overlap between categories is intentional; category totals must not be added to report a unique test count.

Preservation checks immutable upstream SHAs and submodule cleanliness. `scripts/run_upstream_baseline.sh` uses python3, disables ambient pytest plugins, explicitly installs the upstream tests namespace to avoid collision with unrelated installed `tests` packages, then checks exactly 173 executed tests. It never changes upstream source.

Blind tests exercise public measured evidence, alternative causes, artifacts, misleading correlations and sparse ambiguity. OS tests require Linux Bubblewrap and working user namespaces; unavailable isolation is failure, not a skip or an in-process fallback. API tests use the actual ASGI application and temporary SQLite state. Contract tests inspect generated OpenAPI and exact diagnosis vocabulary. Browser tests exercise the real HTTP service and Chromium; CI sets `EKAS_BROWSER_HEADLESS=1`, while local visible-browser acceptance is separate evidence. A static asset test alone does not prove UI workflow behavior.

Focused regression tests must fail before fixes and pass after. The full-duration campaign is separately executable with `python3 scripts/validate_campaign.py --duration-s 86400`; its retained artifacts distinguish physics/determinism, evidence-only diagnostic performance, unresolved cases and incorrect claims. Short simulation tests do not replace this campaign. A passing workflow does not constitute Patrick's final acceptance.

## Local setup and checks

Use Linux with Python 3.11 or newer, Git, Bubblewrap and user namespaces available under the host security policy. Clone recursively; run `bash scripts/verify_upstreams.sh`. In an isolated Python environment:

```bash
python3 -m pip install -e 'vendor/HistorianSim[dev]' -e '.[dev]'
python3 -m playwright install chromium
bash scripts/run_upstream_baseline.sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
python3 scripts/test_layer.py browser
```

A system package administrator may need to install Bubblewrap and Chromium system libraries. Do not change host security policy merely to bypass a failing isolation test. The CI runner uses Ubuntu 22.04 and installs Bubblewrap and Chromium dependencies; a runner lacking supported namespaces fails closed.

Reports must state which commands actually ran, unique test counts, browser visibility/headless mode, skips, limitations and known defects. CI configuration is a future run instruction until a run produces evidence.
