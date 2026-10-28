# Preservation / adaptation matrix

This is a capability inventory and proposed mapping, not proof that the press adaptation exists. All upstream files remain PRESERVED byte-for-byte regardless of intended runtime use. The classification column describes future use: PRESERVE unchanged; ADAPT through an external adapter; EXTEND with additional capability; NOT APPLICABLE only where technically unsuitable for press execution. Paths are relative to the named submodule. The exhaustive path inventory is `upstream-inventory.json`.

## HistorianSim

| Capability | Source evidence | Classification | Press mapping / qualification |
|---|---|---|---|
| Layered generation pipeline | `pipeline.py` under `src/historiansim/` | ADAPT | Retain ordered physics, controls, measurement, historian, truth stages; add discrete cycle events rather than generated trends. |
| Plant interface and auto registry | `plants/base.py`, `plants/__init__.py` | ADAPT | External registration/composition for press topology; no in-place upstream edits. |
| Continuous unit model | `plants/unit.py`, `core/sim.py` | ADAPT | Hybrid discrete-event bridge for stroke, feeder and PLC transitions; continuous submodels only where physically justified. Existing interface alone is insufficient. |
| RK4 integration | `core/integrator.py` | PRESERVE | Use for continuous auxiliary dynamics; do not approximate discrete counter transitions by integration. |
| Independent named random streams | `core/rng.py` | PRESERVE | Seed-stable noise, fault, operator and acquisition streams. |
| Clock, local cycles and DST | `core/clock.py` | PRESERVE | UTC evidence with local shift/ambient effects. |
| Colored noise, random walk, diurnal drivers | `core/noise.py` | ADAPT | Instrument-class and operating-state calibration; no identical noise for all signals. |
| Transport deadtime and filter | `core/deadtime.py` | ADAPT | Material travel, measurement and downstream quality delay. |
| PID, cascades, ratio, mode and tracking | `core/pid.py`, `core/sim.py` | ADAPT | Applicable feeder/auxiliary controls; press sequencing is a separate state machine. |
| Valve characteristics and stiction | `core/valve.py` | ADAPT | Lubrication/auxiliary actuation where appropriate, not a surrogate press mechanic. |
| Saturated-steam property correlations | `core/steam.py` | NOT APPLICABLE | No steam circuit in the specified press cell. Preserve for regression and possible future utility models; do not map steam enthalpy onto press load. |
| Validated configuration and hash | `config/schema.py` | EXTEND | Add versioned cycle, instrumentation, topology and scenario fields. |
| Precomputed independent disturbances | `disturbances/bundle.py`, `drivers.py` | ADAPT | Coil/material variability, ambient, supply variation independent of fault injection. |
| Fault profiles and injection layers | `faults/base.py` | EXTEND | Retain step/linear/exponential/erratic ramps and process/control/instrument separation; add discrete failure mechanisms. |
| Symptom-first catalog and discriminating evidence | `faults/catalog.py` | EXTEND | At least 16 governed press event classes, explicit competing causes and unavailable discriminators. |
| Campaign scheduling and clean windows | `faults/scheduler.py` | ADAPT | Baseline, recovery, repair and benign actions; press timescales. Explicitly version any overlapping-fault extension. |
| Benign control actions | `plants/base.py`, reference plant faults | EXTEND | Operator speed changes and planned stops never automatically become physical faults. |
| Instrument classes, lag, quantization, quality | `measurement/instrument.py`, `apply.py` | ADAPT | Sparse SmartPAC/PLC profile; model digital transitions distinctly from analog signals. |
| Sensor drift, spikes, freezes, node outages | `measurement/pathology.py` | EXTEND | Stuck/missing communications and false alarms, separated from actual machine failures. |
| Swinging-door compression and reconstruction | `historian/swinging_door.py` | ADAPT | Preserve analog compression; digital edge/counter semantics need lossless handling. |
| Primary long record, regular grid, tag master | `historian/export.py`, `tags.py` | EXTEND | Source quality, topology identifiers, timestamps and press units; retain raw evidence when grids interpolate. |
| Neighboring-unit ballast | `ballast.py`, `tags.py` | ADAPT | Related-looking irrelevant signals, shared weather and misleading correlation. |
| Ground truth and labels | `truth/manifest.py`, `truth/labels.py`, `layout.py` | EXTEND | Private evaluator-only truth, benign/artifact labels, failed item/mechanism, propagation and timing. Existing files alone are not an access-control boundary. |
| Blind challenge export | `challenge.py` | EXTEND | Allowlist evidence export, exclude key/config/labels and enforce separate storage/process permissions. |
| Claim scoring and one-to-one interval matching | `scoring.py` | EXTEND | Preserve +1 detection/+2 cause/-1 false-positive reference; add failed item, mechanism, evidence, alternative elimination and unsupported certainty dimensions. |
| Answer-key report from measured effects | `summary.py` | ADAPT | Evaluator report after immutable scoring only; never expose to diagnostic path. |
| Scenario profiles and recipes | `scenarios.py` | ADAPT | Version press baseline and realistic discrete-event campaigns; quick profile cannot qualify full-duration acceptance. |
| Dataset realism validation battery | `validation/battery.py` | EXTEND | Retain noise, lag, range, historian and solvability checks; add cycle/material/production/quality invariants. Chemical balance checks remain for chemical references only. |
| Catalog-wide effect and discrimination sweeps | `validation/catalog.py` | EXTEND | Inject each press failure independently; compare alternatives under sparse/enhanced signals. Missing distinguishability is a valid reported ambiguity. |
| Staged plant gates | `validation/plant_checks.py` | ADAPT | Quiet baseline, controlled interventions, single failures, consistency, then noisy campaigns. |
| Recipe and leakage audit | `validation/recipe.py` | EXTEND | No truth in analyst description/tags; prohibit serialized hidden parameters and API leakage. |
| Difficulty/report formatter | `validation/report.py` | ADAPT | Publish coverage, ambiguity and incomplete checks without converting them into qualification. |
| Computed process description | `process_doc.py` | ADAPT | Press assets, relationships, units, controls and limitations computed from configuration; no answer hints. |
| Trend plotting | `plotting.py` | ADAPT | Evidence-linked event windows and raw versus interpolated quality. |
| CLI, layout and plant scaffolding | `cli.py`, `layout.py`, `scaffold.py`, `plants/_template/` | ADAPT | Preserve CLI reference; external EKAS commands/templates rather than writing into upstream checkout. |
| Heated tank reference plant | `plants/heated_stirred_tank/` | PRESERVE | Keep complete physics, faults, loops, tags and description as regression foundation, not a press surrogate. |
| Exothermic CSTR reference plant | `plants/exothermic_cstr/` | PRESERVE | Keep independent generalization reference including DESIGN; not presented as stamping physics. |
| Generation workflow and PFD renderer | `.claude/skills/simulate/`, nested `pfd-generator/` | ADAPT | Preserve fault-design/unit/validation references, ISA/layout rules, examples and license; press topology drawing needs mechanical conventions and remains conceptual. Not executed automatically. |
| Design, instructions and historical validation | `docs/design-spec.md`, `docs/validation/cstr-rca-s7.md`, `CLAUDE.md`, `.claude/settings.json` | PRESERVE | Retain upstream claims as historical evidence, not current press acceptance or active user instructions. |
| Packaging, license and regression suite | `pyproject.toml`, `LICENSE`, `README.md`, `tests/` | PRESERVE | Run separately; keep failure records and exact baseline. No test weakening. |

## HistorianRCA

| Capability | Source evidence | Classification | Press mapping / qualification |
|---|---|---|---|
| Complete fixed primary historian dataset | `historian.parquet` | PRESERVE | Independent chemical-domain regression data; no relabeling as a press or real plant. |
| Regular one-minute grid | `historian_60s.parquet` | PRESERVE | Reference convenience view; interpolation and short-feature limitations remain. |
| Rich tag dictionary | `tags.csv` | ADAPT | Press asset ownership, I/O, role, instrument, node, update and deadband metadata. |
| First-principles process model documentation | `PROCESS_DESCRIPTION.md` | ADAPT | Supply press relationships rather than tag correlation alone. Chemical thermodynamics remain in upstream reference. |
| PFD SVG and PNG | `tk-101-hold-tank.svg`, `.png` | PRESERVE | Keep originals; create separate press topology later. |
| Blind task and baseline | `CHALLENGE.md`, `README.md` | ADAPT | Preserve baseline and unknown-event discovery; sparse press evidence may be fundamentally insufficient, unlike fully solvable upstream benchmark. |
| Specific failed item plus mechanism | `CHALLENGE.md` | EXTEND | Structured claims, qualification and competing-cause disposition; symptoms are not root causes. |
| Event classification and distractor discipline | `CHALLENGE.md`, `README.md` | ADAPT | Artifacts/operator actions not physical faults. Press feeder sensor drift may be a target instrument event, whereas slow calibration drift is excluded upstream; explicitly version this semantic difference. |
| Submission format and evidence requirement | `submission_template.csv`, `CHALLENGE.md` | EXTEND | Time-bounded claims with evidence provenance; invalid or evidence-free rows cannot silently earn credit. |
| Matching, points and ranking specification | `CHALLENGE.md` | ADAPT | One-to-one longest overlap, six-hour extension and timing tie-breaker retained as reference; any press time tolerance needs a separately versioned rationale. No upstream executable scorer is present. |
| Private answer key and organizer adjudication | `README.md`, `CHALLENGE.md` | NOT APPLICABLE | Private key is absent from the pinned public tree. No authorized local scoring possible on this fixed dataset; preserve documentation and use separately generated private press truth. No outreach authorized. |
| Citation, license, readme and ignore metadata | `CITATION.cff`, `LICENSE`, `README.md`, `.gitignore` | PRESERVE | Credit Scott Duncan, preserve CC BY 4.0 links and version metadata, document adaptations. |

## EKAS ORIGINAL additions required later

No complete upstream implementation exists for asset-linked press topology, SmartPAC signal profiles, maintenance and quality records, PFMEA/control-plan priors, explainable coverage and marginal sensor value, governed RCA state transitions, corrective-action verification, financial terminology, API service persistence, chat-first consumer UI, or advanced-sensor provider interface. Implement these separately after the checkpoint, reusing upstream mechanisms above. The static bootstrap HTML is a presentation reference, not qualified API-backed behavior.
