# Historical EKAS Press Intelligence prototype

Independent synthetic press-line engineering prototype. It runs without EKAS_Demo_UI and integrates only through a versioned HTTP contract.

**Acceptance status:** see [MILESTONE_1_ACCEPTANCE.md](MILESTONE_1_ACCEPTANCE.md). Patrick's manual acceptance is the final gate. All displayed manufacturing data is synthetic; no SmartPAC, PLC or plant historian is connected.

## Run locally

Linux with Python 3.11+ and Bubblewrap is required for enforced diagnostic isolation. Install Bubblewrap through the host package manager. Do not disable the sandbox or expose this local service publicly.

```bash
git clone --recurse-submodules https://github.com/AdaptiveFactoryAISolutions/EKAS_Press_Intelligence.git
cd EKAS_Press_Intelligence
bash scripts/verify_upstreams.sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps -e 'vendor/HistorianSim[dev]' -e '.[dev]'
.venv/bin/python -m uvicorn ekas_press_intelligence.api:create_app --factory --host 127.0.0.1 --port 18727
```

Open http://127.0.0.1:18727 . Generate a campaign, choose an observed window and ask why production was lost. Inspect evidence and alternatives, compare instrumentation, freeze a benchmark submission, then reveal truth after scoring. Apply a synthetic action and compare controlled windows. INCONCLUSIVE and unresolved causes are supported results.

The default campaign is 86,400 seconds with a two-hour normal baseline, 16 event classes and recovery periods. Sparse and enhanced profiles observe identical underlying physics. A single-window UI claim intentionally leaves other campaign events missed; it is not the complete automated blind evaluation.

## Tests and retained evidence

```bash
.venv/bin/python -m playwright install chromium
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests -q
bash scripts/run_upstream_baseline.sh
.venv/bin/python scripts/validate_campaign.py
```

The upstream baseline helper must run in the activated environment (or set PATH to its bin directory). It requires exactly 173 upstream tests with no skips. CI separates preservation, upstream regression and eight EKAS test layers. On hosts that forbid user namespaces, diagnosis fails closed; there is no in-process fallback.

[VALIDATION_REPORT.md](VALIDATION_REPORT.md) links test, browser and full-duration artifacts. [validation/CAMPAIGN.md](validation/CAMPAIGN.md) records genuine evidence-only detection and diagnosis before evaluator truth is read. Previous adverse results remain under validation/history/. Raw historian data, private simulation truth, local state databases and installed runtimes remain in ignored work/.

## Engineering boundaries

- Integer stroke/feed/count transitions with continuous lubrication/load dynamics; unmodified HistorianSim RNG, colored noise, PID, RK4 and historian compression primitives.
- Public pairwise discrimination requirements and conditional sensor gains. Availability is structural diagnostic capacity, not a probability of real-world accuracy.
- OS-isolated evidence-only RCA; public physical priors and maintenance/quality/PFMEA context do not establish a cause by themselves.
- Temporal one-to-one scoring with failed-item/mechanism and relevant measured evidence requirements, false-positive and unsupported-certainty penalties.
- Controlled before/after verification with explicit significance thresholds and uncertainty. A recorded repair is not success.
- SQLite cases, evidence, transitions, actions, assessments and immutable scored submissions.
- API-backed UI; no RCA, coverage, scoring or verification logic in JavaScript.
- Financial opportunity estimates preserve assumptions; opportunity never becomes verified savings.
- Vendor-neutral optional source-observation contract. No advanced sensor, camera or NVIDIA hardware is required or connected.

This is a single-user local prototype, not an authenticated multi-tenant production deployment. Mechanics are idealized and uncalibrated; one-second scans do not constitute waveform acquisition. Synthetic benchmark results do not prove performance at a real plant. See architecture, fault catalog and acceptance limitations.

## Provenance

HistorianSim is pinned to 14e616c382a9db8026cbb4ab86bdd803d56ca72e (MIT); HistorianRCA to 8d12a821395ce5f72e464dc78cc2c10d05cbb9ed (CC BY 4.0). Scott Duncan's full repositories, histories, attribution, licenses, data, tests and validation documents remain preserved.

[UPSTREAM_PROVENANCE.md](UPSTREAM_PROVENANCE.md) · [LICENSES.md](LICENSES.md) · [PRESERVATION_ADAPTATION_MATRIX.md](PRESERVATION_ADAPTATION_MATRIX.md) · [API_CONTRACT.md](API_CONTRACT.md)
