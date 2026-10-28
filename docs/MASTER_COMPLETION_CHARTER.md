# CODEX MASTER COMPLETION CHARTER
## EKAS Press Intelligence — Milestone 1

### Repository

`AdaptiveFactoryAISolutions/EKAS_Press_Intelligence`

Current accepted preservation checkpoint:

`e1d04e539a87183a34835caf449395354c454b43`

Upstream foundations:

- HistorianSim:
  `14e616c382a9db8026cbb4ab86bdd803d56ca72e`
- HistorianRCA:
  `8d12a821395ce5f72e464dc78cc2c10d05cbb9ed`

The preservation checkpoint is accepted.

You are now authorized to complete **Milestone 1**.

---

# 1. PRIMARY GOAL

Build a working, production-quality prototype of:

**EKAS Press Intelligence**

The prototype must prove that EKAS can operate in a realistic metal-stamping environment where:

- The press has SmartPAC 2-like data.
- A PLC provides basic states and faults.
- Auxiliary equipment has limited or no instrumentation.
- The plant knows production was lost but cannot reliably determine why.
- EKAS must distinguish:
  - What the data proves.
  - What the data suggests.
  - What remains ambiguous.
  - What additional signal would remove the ambiguity.
  - What action should be investigated first.
  - Whether the action actually improved performance.

This is not a UI mockup project.

This is not a random-data simulator.

This is not a scripted RCA demonstration.

Build the engineering system behind the product.

---

# 2. AUTONOMOUS EXECUTION

Use your full capabilities.

You are authorized to:

- Inspect the complete repository.
- Inspect both upstream repositories in detail.
- Read all source, tests, validation documents, schemas, and examples.
- Create branches.
- Write code.
- Refactor code.
- Add tests.
- Run tests.
- Run simulations.
- Run long-duration validation.
- Generate artifacts.
- Start local services.
- Exercise APIs.
- Drive a browser.
- Inspect network calls.
- Inspect browser console output.
- Inspect generated data.
- Compare simulated truth to RCA claims.
- Create documentation.
- Commit work.
- Open PRs if appropriate.
- Fix defects discovered during validation.
- Repeat until acceptance criteria pass.

Do not stop after producing a plan.

Do the work.

Do not ask for approval between normal engineering steps.

Stop only for:
- A genuine external credential requirement.
- An irreversible external action that requires explicit authorization.
- A material architectural conflict not resolvable from this charter.

Do not provide time estimates.

---

# 3. ABSOLUTE ISOLATION FROM EKAS_DEMO_UI

Do not modify:

`AdaptiveFactoryAISolutions/EKAS_Demo_UI`

Do not:

- Branch from it.
- Import its source.
- Add this repository as its dependency.
- Change its build.
- Run experimental writes against it.
- Copy incomplete code into it.

Future EKAS integration must occur only through the versioned module contract.

This repository must remain independently:

- Buildable.
- Testable.
- Runnable.
- Versionable.
- Deployable.

---

# 4. UPSTREAM PRESERVATION REMAINS MANDATORY

The accepted preservation rules remain in force.

Do not simplify or replace HistorianSim or HistorianRCA with reduced imitations.

Continue to preserve:

- Full source.
- Tests.
- Validation.
- Historian behavior.
- Noise models.
- Instrument pathology.
- RNG behavior.
- Fault scheduling.
- Challenge construction.
- Scoring philosophy.
- Blind truth separation.
- Evidence requirements.
- False-positive penalties.
- Reproducibility.
- Licenses.
- Attribution.

All EKAS-specific behavior must be implemented outside the upstream source unless a documented patch is absolutely necessary.

If an upstream patch becomes necessary:

1. Record original behavior.
2. Record the defect.
3. Record the reason.
4. Add a regression test.
5. Record the upstream base SHA.
6. Keep the patch isolated and auditable.

---

# 5. RESOLVE CURRENT CHECKPOINT GAPS FIRST

Before expanding capability, correct the known checkpoint inconsistencies.

## 5.1 RCA state vocabulary

Replace inconsistent state names with the charter vocabulary everywhere:

```text
OBSERVED_ANOMALY
CONTRIBUTOR
SUSPECTED_CAUSE
EVIDENCE_SUPPORTED_CAUSE
VERIFIED_ROOT_CAUSE
CORRECTIVE_ACTION
VERIFICATION
SUSTAINED
```

Update:

- Documentation.
- Runtime schemas.
- Tests.
- API contracts.
- Persistence models.

Do not leave parallel vocabularies.

---

## 5.2 Repository visibility documentation

The repository is now public.

Update historical documentation where necessary so current state is accurate.

Do not alter the historical meaning of the checkpoint.

---

## 5.3 CI

The existing CI that runs only starter tests is insufficient.

Build real CI that separately validates:

1. Upstream preservation.
2. HistorianSim upstream regression suite.
3. EKAS unit tests.
4. EKAS simulation invariants.
5. Contract tests.
6. Blind RCA tests.
7. Observability tests.
8. API tests.
9. UI tests.
10. Browser acceptance smoke tests where supported.

Do not represent starter CI as product qualification.

---

# 6. BUILD THE PRESS-LINE SIMULATION ENGINE

Use HistorianSim as the engineering foundation.

Create an EKAS stamping plant model outside upstream code.

Initial reference topology:

```text
Plant
└── Line 03
    ├── Press 27
    ├── Feeder 27
    ├── Decoiler 27
    ├── Lubrication system
    ├── Die
    ├── Material
    ├── Part
    ├── Quality inspection
    └── Maintenance history
```

The simulated process must behave as a system.

Do not simulate each signal independently.

---

# 7. HYBRID DISCRETE + CONTINUOUS MODEL

HistorianSim is primarily continuous-process oriented.

Stamping requires a hybrid architecture.

Implement explicit discrete behavior for:

- Press strokes.
- PLC sequence states.
- Feed cycles.
- Feed complete.
- Die protection.
- Part count.
- Scrap count.
- Machine stop.
- Restart.
- Operator intervention.
- Changeover.
- Material starvation.
- Fault transitions.

Use continuous models only where physically appropriate:

- Lubrication pressure.
- Motor current/load.
- Tonnage envelope.
- Temperature if introduced.
- Sensor drift.
- Vibration or analog health signals later.

Do not approximate discrete press events as continuous chemistry-style dynamics.

---

# 8. SMARTPAC / PLC SPARSE PROFILE

The first instrumentation profile must approximate the real-world plant condition discussed with Patrick.

Assume primarily:

### Available

- Press run state.
- Press stop state.
- Press fault.
- Stroke count.
- SPM.
- Part count.
- Job.
- Die identifier.
- Basic PLC state.
- Basic fault inputs.
- Existing die protection.
- Feeder ready/fault only if configured.
- Lubrication OK only if configured.

### Typically unavailable or incomplete

- Absolute feeder position.
- Strip progression.
- Loop height.
- Coil starvation.
- Feeder mechanical health.
- Lubrication analog pressure.
- Motor current waveform.
- Detailed die condition.
- Visual inspection.
- Auxiliary vibration.
- Acoustic signals.

The simulator must support this sparse instrumentation profile.

---

# 9. ENHANCED PROFILE

Use the same physical scenario and add selected signals.

Examples:

- Feeder position.
- Material-present sensor.
- Loop height.
- Lubrication pressure.
- Motor current.
- Tonnage waveform.
- Vibration.
- Camera-derived event.

This allows EKAS to measure the actual diagnostic value of added instrumentation.

The physics/event truth must not change merely because the profile changed.

Only observability changes.

---

# 10. IMPLEMENT THE FAULT / EVENT CATALOG

Implement at least these 16 governed event classes:

1. Feeder sensor drift.
2. Feeder mechanical instability.
3. Misfeed / strip progression fault.
4. Material starvation.
5. Decoiler interruption.
6. Lubrication pressure loss.
7. Die-protection trip.
8. Progressive die wear.
9. Abnormal tonnage/load.
10. Press speed degradation.
11. Repeated microstops.
12. Quality deterioration.
13. Operator speed change — benign.
14. Planned stop — benign.
15. Historian communication dropout — artifact.
16. Stuck sensor — artifact.

Do not stop at exactly 16 if realistic engineering requires supporting classes.

Each catalog entry must define:

```text
event_class
event_kind
asset
failed_item
failure_mechanism
symptoms
observable_signals
expected_directionality
timing_relationships
competing_causes
discriminating_signals
sparse_profile_observability
enhanced_profile_observability
verification_method
```

---

# 11. FAULT DESIGN QUALITY

Use the HistorianSim fault-design philosophy fully.

Faults must not simply flip a Boolean.

Use realistic mechanisms such as:

- Gradual drift.
- Intermittent instability.
- Threshold-dependent failure.
- Mechanical degradation.
- Increasing variance.
- Delayed downstream quality impact.
- Controller/PLC compensation masking the underlying problem.
- Fault onset before obvious production loss.

Where possible, create multiple causes with the same first symptom.

This is essential.

EKAS must distinguish causes through evidence, not through one unique obvious bit.

---

# 12. NORMAL BASELINE

Provide a clean normal baseline before faults.

Use enough baseline data to establish:

- Expected SPM.
- Normal cycle variation.
- Normal stop frequency.
- Normal tonnage/load.
- Normal feeder behavior.
- Normal scrap.
- Normal quality.
- Normal lubrication behavior.
- Normal PLC state transitions.

Use reproducible random seeds.

---

# 13. DISTRACTORS

Preserve HistorianRCA discipline.

Include:

- Benign operator actions.
- Planned stops.
- Normal changeover.
- Normal material variation.
- Weather/ambient variation where appropriate.
- Slow instrument drift that is not a target fault.
- Communication outages.
- Stuck values.
- Single-sample spikes.
- Irrelevant correlated signals.

False positives must be possible.

The benchmark must penalize them.

---

# 14. HIDDEN TRUTH IS A SECURITY BOUNDARY

Do not rely on folder names.

Implement enforced separation.

The RCA path must not have:

- Truth-store credentials.
- Truth-file access.
- Simulator object references exposing truth.
- Hidden configuration access.
- Ground-truth API access.
- Debug serialization leakage.
- Test-only answer injection.

Use distinct interfaces/processes/storage boundaries where practical.

Add negative tests proving the diagnostic runtime cannot access truth.

---

# 15. BUILD THE OBSERVABILITY MODEL

This is one of the most important product features.

Do not use a simplistic percentage.

Define:

```text
Fault class
Required observations
Competing fault classes
Discriminating observations
Available observations
Unresolved equivalence groups
```

From this model, determine:

- Fully distinguishable classes.
- Partially distinguishable classes.
- Indistinguishable classes.
- Classes not observable at all.

Produce an explainable coverage result.

Example:

```text
Feeder mechanical instability
vs
Material starvation

Shared evidence:
- Press stop.
- Production loss.

Missing discriminator:
- Feeder position.
- Material-present state.

Result:
Not distinguishable with current instrumentation.
```

That is more important than a raw percentage.

---

# 16. SENSOR-GAP ANALYSIS

For each unresolved ambiguity:

Evaluate candidate signals.

Calculate the marginal information gain from each candidate.

Do not add overlapping gains independently.

A recommended signal must state:

```text
Signal
Fault classes separated
Ambiguity reduced
Current source available?
PLC input possible?
Analog/discrete?
Hardware required?
Expected diagnostic gain
```

Prefer the simplest adequate signal.

Priority order:

1. Existing unused control signal.
2. Existing PLC data.
3. Added discrete input.
4. Added analog sensor.
5. Advanced waveform sensor.
6. Vision / edge AI.

Do not recommend expensive edge AI when a $50 switch solves the ambiguity.

---

# 17. RCA ENGINE

Build a governed RCA engine that produces:

```text
Observed problem
Evidence
Candidate causes
Alternative causes
Supporting evidence
Contradicting evidence
Unresolved evidence
Diagnosis state
Recommended investigation
Verification requirement
```

The engine must not be a phrase-to-answer lookup.

The engine must reason from structured evidence.

---

# 18. ALTERNATIVE-CAUSE ELIMINATION

For each RCA case:

```text
Primary hypothesis
Evidence for primary hypothesis

Alternative A
Evidence for A
Evidence against A
Disposition

Alternative B
Evidence for B
Evidence against B
Disposition

Remaining ambiguity
```

Allowed dispositions:

```text
SUPPORTED
CONTRADICTED
UNRESOLVED
NOT_OBSERVABLE
```

Do not force a winner when evidence is insufficient.

---

# 19. MAINTENANCE DATA

Create realistic synthetic maintenance context.

At minimum:

- Work order ID.
- Asset.
- Date.
- Failure description.
- Repair action.
- Component replaced.
- Technician note.
- Repeat failure.
- PM status.
- PM history.

Maintenance records can support RCA.

They cannot automatically prove a cause.

---

# 20. QUALITY DATA

Add:

- Good count.
- Scrap count.
- FPY.
- Defect class.
- Quality measurement.
- Quality drift.
- Hold event.

Use delayed quality effects where realistic.

For example:

Die wear can begin before scrap becomes obvious.

---

# 21. PFMEA AND CONTROL PLAN

Create representative synthetic PFMEA and Control Plan data.

Link:

```text
Process step
Failure mode
Potential effect
Potential cause
Prevention control
Detection control
Characteristic
Reaction plan
```

Use these as prior knowledge.

Do not let PFMEA determine the answer.

Observed evidence still governs.

---

# 22. BENCHMARK ENGINE

Create blind benchmark execution.

The evaluator knows truth.

The RCA engine does not.

Score at minimum:

- Event detection.
- Correct failed item.
- Correct failure mechanism.
- Evidence quality.
- Evidence completeness.
- Timing.
- Alternative-cause handling.
- Unsupported certainty.
- False positives.

Preserve HistorianRCA's strong false-positive discipline.

---

# 23. TEMPORAL MATCHING

Replace starter truth-ID scoring.

Claims must match events through time overlap, not shared IDs.

Implement explicit matching logic.

Test:

- One claim spanning multiple events.
- Two claims on one event.
- No overlap.
- Partial overlap.
- Delayed recognition.
- False positive.
- Benign event.
- Artifact.

Do not make benchmark success depend on access to hidden event IDs.

---

# 24. ROOT-CAUSE SCORING

A correct root cause requires both:

- Correct failed item.
- Correct mechanism.

Example:

Incorrect:

`Feeder problem`

Incorrect:

`Microstops`

Correct:

`Feeder position sensor mounting loosened, causing intermittent position feedback`

Symptoms are not root causes.

---

# 25. VERIFICATION

After corrective action, simulate or apply a repair.

Compare:

- Pre-action.
- Post-action.

Control for:

- Job.
- Die.
- Material.
- Production rate.
- Exposure time.
- Data quality.

Evaluate:

- Microstops.
- Downtime.
- SPM.
- Throughput.
- OEE.
- Scrap.
- Quality.
- Repeat fault rate.

Allowed result:

```text
VERIFIED
NOT_VERIFIED
INCONCLUSIVE
```

A completed work order is not evidence of success.

---

# 26. FINANCIAL GOVERNANCE

Implement distinct fields for:

- Lost capacity.
- Production opportunity.
- Potential contribution at risk.
- Estimated financial impact.
- Avoided cost.
- Verified savings.

Store assumptions and provenance.

Do not convert production opportunity directly into savings.

---

# 27. EXECUTABLE MODULE CONTRACT

Replace prose-only contract with executable schemas.

Use a versioned API.

At minimum:

```text
POST /v1/observability/assess

POST /v1/rca/investigate

GET /v1/rca/cases/{id}

GET /v1/rca/cases/{id}/evidence

POST /v1/rca/cases/{id}/verify

GET /v1/sensor-gaps

GET /v1/assets

GET /v1/signals

POST /v1/benchmark/run

POST /v1/benchmark/{id}/submit

GET /v1/benchmark/{id}/score
```

Use typed schemas.

Generate OpenAPI or equivalent machine-readable documentation.

Add contract tests.

---

# 28. PERSISTENCE

Persist:

- RCA cases.
- Evidence references.
- Hypotheses.
- Alternative dispositions.
- Diagnosis state transitions.
- Actions.
- Verification records.
- Observability assessments.
- Sensor-gap assessments.
- Benchmark runs.
- Benchmark submissions.
- Benchmark scores.

Preserve immutable benchmark submissions after scoring begins.

---

# 29. UI

Build a real UI consumer inside this repository.

Do not put RCA logic in the UI.

Required screens:

### Chat / investigation
- Chat-first interface.
- Direct answer.
- KPI strip.
- Primary finding.
- Causes.
- Alternatives.
- Recommended action.
- Qualification.

### Evidence drawer
- Time-aligned signals.
- Events.
- Data quality.
- Evidence provenance.

### Observability
- Available signals.
- Partial visibility.
- Missing signals.
- Distinguishable fault classes.
- Ambiguous fault groups.

### Sensor-gap
- Recommended new signals.
- Ambiguities resolved.
- Estimated diagnostic gain.
- Hardware requirement.

### Benchmark
- Scenario.
- Hidden truth status.
- Submitted diagnosis.
- Score.
- False positives.
- Truth reveal after scoring only.

### Verification
- Before/after comparison.
- Sustained result.

---

# 30. UI QUALITY

Use professional visual design.

Do not create a developer-admin interface as the primary product experience.

Make it appropriate for:

- Manufacturing engineer.
- Maintenance manager.
- Plant manager.
- Continuous-improvement leader.

Keep:

- Clear hierarchy.
- Scannable evidence.
- Minimal monolithic prose.
- Strong separation between facts, diagnosis, qualification, and action.

Do not claim ASD-STE100 implementation here unless EKAS-RSP-001 has formally begun.

This repository can prepare structured response data, but do not prematurely merge that separate SOP.

---

# 31. BROWSER TESTING

Use visible browser testing.

Test real user flows.

Required flows:

1. Open press investigation.
2. Ask why production was lost.
3. Review primary hypothesis.
4. Expand evidence.
5. View alternative causes.
6. View an unresolved ambiguity.
7. Open sensor-gap recommendation.
8. Run a benchmark.
9. Submit an RCA claim.
10. Reveal truth only after scoring.
11. Apply a synthetic corrective action.
12. Verify the result.

Inspect:

- Console.
- Network.
- Broken interactions.
- Layout.
- Accessibility.

API-only testing is insufficient for UI acceptance.

---

# 32. ADVERSARIAL TESTING

Create tests designed to make EKAS fail.

At minimum:

### Same symptom, different cause

Example:

Press stopped.

Possible causes:

- Feeder fault.
- Material starvation.
- Die protection.
- Operator stop.

Sparse instrumentation must sometimes report ambiguity.

---

### Misleading correlation

A signal changes at the same time but is not causal.

EKAS must not elevate it without supporting evidence.

---

### Missing discriminator

The required signal is not available.

EKAS must say:

`NOT_OBSERVABLE`

or equivalent governed result.

---

### Benign event

Operator lowers SPM intentionally.

Do not call it a press fault.

---

### Historian artifact

Communication drops.

Do not call it equipment failure.

---

### Repeat failure

A maintenance record shows the same pattern occurred previously.

Use it as evidence but not automatic proof.

---

# 33. LONG-DURATION SIMULATION ACCEPTANCE

Do not qualify the simulator using only short tests.

Generate at least one full-duration Milestone 1 dataset.

Use:

- Normal baseline.
- Fault episodes.
- Benign events.
- Artifacts.
- Sparse profile.
- Enhanced profile.

Verify:

- Deterministic regeneration.
- Dataset structure.
- Signal ranges.
- Fault manifestation.
- Recovery.
- No answer leakage.
- Evidence availability.
- Ambiguity behavior.

Retain validation artifacts.

---

# 34. BLIND RCA ACCEPTANCE

Run a genuine blind RCA evaluation.

The RCA engine must not see truth.

Evaluate all implemented fault classes.

Record:

```text
Detected
Correct cause
Incorrect cause
Unresolved correctly
False positives
Missed
Evidence completeness
Unsupported-certainty violations
```

Do not hide failures.

Fix root causes and rerun.

---

# 35. OBSERVABILITY ACCEPTANCE

Prove that the sparse profile behaves differently from the enhanced profile.

Example:

Sparse:

```text
Feeder fault
vs
Material starvation

UNRESOLVED
```

Enhanced with feeder-position + material-present signals:

```text
DISTINGUISHABLE
```

The result must come from the formal discrimination model, not hard-coded UI text.

---

# 36. SENSOR-GAP ACCEPTANCE

Prove that the recommended sensor actually changes the discrimination model.

A sensor recommendation is invalid unless:

- It resolves at least one documented ambiguity.
- The model recomputes coverage correctly.
- The same gain is not double-counted with another signal.
- The result is reproducible.

---

# 37. UPSTREAM REGRESSION

Before Milestone 1 acceptance:

Run the complete HistorianSim upstream tests again.

Do not weaken or skip them without documented justification.

Preserve the previous baseline:

`173 passed`

If the upstream count changes because the pinned upstream does not change, investigate before accepting.

---

# 38. EKAS TEST QUALITY

Every important bug found during development must receive a regression test.

A regression test must:

1. Fail before the fix.
2. Pass after the fix.

Do not write tests only after implementation if the original defect can no longer be reproduced.

---

# 39. NO CANNED ANSWERS

Do not implement:

```text
if question contains "feeder":
    answer feeder fault
```

Do not build phrase-specific RCA.

Natural-language interpretation must produce structured intent.

RCA must operate on structured evidence.

---

# 40. NO SILENT SUBSTITUTION

Never substitute:

- Metric.
- Asset.
- Period.
- Signal.
- Fault class.
- Scope.
- Dataset.

If something is unavailable:

Say so.

If evidence is insufficient:

Say so.

If two causes cannot be distinguished:

Say so.

That is a product feature.

---

# 41. DOCUMENTATION

Update or create:

```text
README.md
ARCHITECTURE.md
PRODUCT_REQUIREMENTS.md
UPSTREAM_PROVENANCE.md
PRESERVATION_ADAPTATION_MATRIX.md
FAULT_CATALOG.md
OBSERVABILITY_MODEL.md
SENSOR_GAP_MODEL.md
RCA_GOVERNANCE.md
BENCHMARK_STANDARD.md
API_CONTRACT.md
TEST_STRATEGY.md
VALIDATION_REPORT.md
MILESTONE_1_ACCEPTANCE.md
```

Documentation must reflect actual implemented behavior.

Do not document future capability as complete.

---

# 42. DECISION RECORDS

Create ADRs for material architectural choices.

At minimum:

- Hybrid discrete/continuous architecture.
- Hidden-truth isolation.
- Observability coverage model.
- Sensor-value model.
- Benchmark matching/scoring.
- Persistence.
- API framework.
- UI/API boundary.

---

# 43. COMPLETION EVIDENCE

At the end, provide exact evidence.

Include:

```text
Repository
Branch
Final commit SHA
Tree status
Upstream SHAs
Upstream test count
EKAS test count
Simulation validation count
Contract test count
API test count
Browser test count
Accessibility result
Known defects
Known limitations
```

Do not use vague language such as:

- "looks good"
- "mostly complete"
- "essentially done"
- "should work"

---

# 44. MILESTONE 1 ACCEPTANCE

Milestone 1 is complete only when all of these are true:

- Independent repository remains isolated.
- Upstream sources remain preserved.
- Full HistorianSim suite passes.
- Hybrid press simulator exists.
- At least 16 governed event classes exist.
- Full-duration dataset generation succeeds.
- Sparse profile works.
- Enhanced profile works.
- Hidden truth is technically isolated.
- Blind RCA runs.
- False positives are penalized.
- Root causes require item + mechanism.
- Alternative causes are evaluated.
- Observability model works.
- Sensor-gap analysis works.
- Maintenance context works.
- Quality context works.
- PFMEA/control-plan context works.
- Corrective-action verification works.
- Financial terminology is governed.
- Versioned API is executable.
- Persistence works.
- UI consumes the API.
- Visible browser acceptance passes.
- No RCA logic exists in UI components.
- No known critical defects remain.
- Documentation matches implementation.

---

# 45. FINAL VERDICT

Use only one of these verdicts:

`EKAS PRESS INTELLIGENCE — MILESTONE 1 NOT READY`

or

`EKAS PRESS INTELLIGENCE — MILESTONE 1 READY FOR PATRICK ACCEPTANCE`

Do not mark it complete merely because automated tests are green.

Patrick's manual acceptance remains the final gate.

---

# 46. WORKING PRINCIPLE

Throughout the build, preserve this product principle:

> EKAS must never manufacture certainty from missing instrumentation.

When the available plant signals cannot distinguish two causes, the correct EKAS answer is not a guess.

The correct answer is:

```text
These causes cannot be distinguished with the current evidence.

The missing signal is X.

Adding X would separate A from B because...
```

That capability is central to the product.

---

# 47. BEGIN NOW

Start from the accepted checkpoint.

Inspect the existing implementation first.

Resolve the known checkpoint gaps.

Then implement Milestone 1 in the order that gives the strongest technical foundation.

Do not begin with UI polish.

Build:

1. Truth.
2. Simulation.
3. Observability.
4. RCA.
5. Benchmark.
6. Verification.
7. API.
8. Persistence.
9. UI.
10. Full acceptance.

Continue until you can produce the final Milestone 1 verdict with evidence.