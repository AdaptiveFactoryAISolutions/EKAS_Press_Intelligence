# Implemented architecture

## Isolation and provenance

The repository is independent of EKAS_Demo_UI. Both upstreams remain complete pinned submodules, with no local source changes. New modules are EKAS ORIGINAL; bridges using preserved upstream primitives are adaptations implemented outside upstream trees. The preservation matrix distinguishes retained upstream capabilities from the specific primitives used by this prototype; no full continuous-process runtime parity is claimed for the discrete press extension.

## Runtime

```text
Browser UI → versioned FastAPI broker → SQLite public resources
                                  ↘ evaluator-only configuration / truth vault
Public evidence → Bubblewrap worker → hypotheses / provenance / qualification
Evaluator → immutable claims + private truth → versioned temporal score
Recorded action → seeded physical replay → controlled measured verification
```

The broker coordinates the local prototype and owns evaluator state. The diagnostic runtime is a separate process with private user, PID, mount and network namespaces. It mounts Python runtime files and only public domain.py, rca/engine.py and observability/model.py. No home, repository tree, simulator, API, storage code, truth/configuration file or environment credential is mounted. Input is JSON evidence over stdin; output is JSON findings. Namespace setup failures disable diagnosis with a typed 503. Private truth access through the evaluator API is permitted only after atomic frozen submission and scoring.

The local broker itself is trusted and is not a hostile multi-tenant service. It binds to loopback in documented launch commands. Authentication, role administration and public hosting are outside this prototype's qualified boundary.

## Physical and observation models

simulator/engine.py advances at one-second resolution. Integer strokes require material, feed, lubrication and die/overload permissives. Strokes consume strip pitch and create exactly one good or scrap part. A phase accumulator supports fractional SPM without fractional parts. Buffer refill has surplus capacity after starvation. PLC stop, changeover and restart records derive from state changes. Pressure uses preserved PID/RK4 primitives; seeded colored disturbances and process fault ramps affect load, feedback, pressure and delayed dimensions. Quality inspection lags forming by 60 seconds.

The public signal profile is selected after physical evolution. Sparse and enhanced simulations therefore retain identical truth and shared observations. Acquisition dropout and stuck-register artifacts corrupt observations, not physical truth. Ambient/material distractors cannot establish mechanism causality. The catalog is public prior knowledge; campaign schedules and private states are evaluator-only.

A compressed historian exporter reuses upstream swinging-door compression for analog channels and preserves discrete changes/quality boundaries exactly. A regular CSV-gzip record and checksum manifest remain available.

## Diagnosis and observability

domain.py defines 16 mechanisms, kinds, assets, observations, alternatives, pairwise requirements and temporal feature rules. observability/model.py evaluates all 120 pairs against available observations. Coverage reports explicit class and pair numerators/denominators. Connected unresolved components are navigation groups; they are not asserted to be mathematical equivalence relations. Candidate sensor gain is the actual difference after recomputation, never an independently additive score.

RCA uses robust baseline/current moments, temporal trends, peaks, variance, acquisition quality and recorded operating events. It evaluates conjunctive signatures, contradictions and missing essential observations. Maintenance, PFMEA and control-plan links are contextual priors; inspection records retain explicit provenance. A physical cause becomes evidence-supported only with adequate measured discrimination. Missing observations remain NOT_OBSERVABLE or unresolved.

Exactly these diagnosis states are valid: OBSERVED_ANOMALY, CONTRIBUTOR, SUSPECTED_CAUSE, EVIDENCE_SUPPORTED_CAUSE, VERIFIED_ROOT_CAUSE, CORRECTIVE_ACTION, VERIFICATION, SUSTAINED. The evidence-only engine never emits VERIFIED_ROOT_CAUSE. Action and verification records do not fabricate physical root-cause certainty.

## Verification, finance and persistence

Verification uses server-held before/after observations. Job, die, material, commanded rate, exposure and acquisition quality are controlled; achieved speed may improve under the same measured setpoint. The versioned comparison policy reports thresholds, intervals, meaningful improvements/regressions and compatible uncertainty. Sparse inspection counts fill observed quality/scrap context; unavailable outcomes yield INCONCLUSIVE. Sustained requires explicit verified exposure.

Financial estimates derive lost capacity from observed counts and baseline rate, retain stated contribution assumptions and provenance, and separate opportunity/risk/impact/avoided cost/savings. The case estimate API never derives savings from opportunity.

SQLite resources persist cases, evidence/hypotheses/dispositions, state snapshots, actions, verification, assessments, sensor gaps, runs, claims and scores. Append-only audit triggers retain transitions. Benchmark submission and score are frozen atomically, and update/delete triggers reject replacements.

## Contracts, UI and extensions

contracts/api.py defines strict versioned request models and response models; FastAPI generates OpenAPI. Scope/period/signal conflicts return typed failures. intent.py resolves objective/scope constraints only; language is never mapped to a cause.

The same-origin UI renders server findings, evidence and qualifications. Its charts use observed samples. Coverage, diagnosis, score and verification are never computed in UI code. The original ui-prototype HTML remains a labeled historical presentation reference.

contracts/sources.py defines a vendor-neutral ObservationProvider/SourceObservation boundary for future PLC, historian, vision, vibration, acoustic, current, tonnage-waveform and thermal providers. It requires source, asset, aware timestamp, units, quality, calculation and explicit synthetic labeling. No physical provider is installed or simulated as a real connection.

ADRs 0003–0010 record the material choices. See TEST_STRATEGY.md and VALIDATION_REPORT.md for evidence and limits.
