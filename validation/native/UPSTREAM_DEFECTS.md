# Observed upstream export defects

Observed against immutable HistorianSim `14e616c382a9db8026cbb4ab86bdd803d56ca72e` on 2026-10-28. These are retained adverse results, not waived qualification checks. No vendor files were changed.

## U-001: 10-second grid overwrites the primary historian

`src/historiansim/layout.py:34` fixes the primary filename to `historian_10s.parquet`. `pipeline.py:295` writes the primary long-format record there; `pipeline.py:298` then writes the wide grid to `historian_{int(resample_s)}s.parquet`. With `resample_s=10`, the second write replaces the primary artifact.

Actual bounded reproduction used the original native pipeline, seed 17, quick exchanger-fouling, explicit 0.02 day / zero ballast / zero fault configuration, no benign events and zero baseline. This shortened configuration is a unit reproduction, never a qualification substitute:

```python
from historiansim.scenarios import build_scenario
from historiansim.pipeline import generate, write_dataset
cfg = build_scenario('exchanger-fouling', profile='quick', seed=17,
                     days=0.02, ballast=0, n_faults=0)
cfg.episodes.n_benign = 0
cfg.episodes.baseline_days = 0
write_dataset(generate(cfg), target, resample_s=10)
```

Observed `historian_10s.parquet` schema begins `timestamp, TIC-101.PV, TIC-101.SP, ...` and contains the full wide tag columns. Required primary columns `tag`, `value`, `quality` are absent. Native layout audit additionally returns:

```text
dataset_layout: FAIL
unexpected [], missing ['historian_60s.parquet']
no_answer_leak: PASS
```

Current wrapper protection: reject `resample=10` explicitly before generation. This is a disclosed unsupported native export option pending a generic upstream-compatible correction; it is not complete resampling parity.

## U-002: non60 grids disagree with native challenge, plotting and audit

The writer accepts a resampling period and writes the requested grid, but `layout.py:35,42` fixes the regular grid to 60 seconds. `challenge.py:219` copies that fixed file; `plotting.py:48-51` reads it; `validation/recipe.py:145-146` requires exactly the fixed native filenames.

Using the identical bounded configuration with `resample_s=120` preserved the correct primary schema `tag,timestamp,value,quality` and wrote `historian_120s.parquet`. The actual native audit returned:

```text
dataset_layout: FAIL
unexpected ['historian_120s.parquet'], missing ['historian_60s.parquet']
no_answer_leak: PASS
```

Current wrapper compatibility: retain the requested native grid; additionally use native `build_regular_grid(...,60)` to provide the canonical grid required by native challenge/plotting. Copy both public grids and disclose the added 60 second artifact in the result. The unmodified native layout audit still fails on the extra requested grid. These datasets must not receive qualified status merely because compatibility allows challenge/plot generation. Non60 audit parity remains unresolved; no audit check has been relaxed or silently omitted.

The writer also truncates fractional resampling periods in filenames with `int(resample_s)` while reconstruction uses the requested floating value. The wrapper currently accepts only positive integer seconds and discloses this constraint; fractional export parity remains unavailable pending a consistent naming contract.

## Retained evidence and correction requirements

Bounded raw reproductions and their JSON findings are retained under `work/reference-pfd-review/resample-defects/`; this document preserves the adverse findings without publishing generated answer keys. Existing native wrapper tests cover canonical Parquet equality, requested 120 second export preservation.

A future generic fix must preserve distinct primary and requested-grid artifacts, record the grid period in authoritative metadata, resolve challenge/plot readers from that metadata, and make layout audits recognize the actual declared exports. It requires red regressions for10 second, non60 and fractional naming behavior, direct native-versus-service artifact parity, and unchanged canonical 60 second reference behavior. No such source correction is claimed here.
