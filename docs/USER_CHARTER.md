# CODEX CHARTER
## EKAS Press Intelligence & RCA — Independent Repository Build

### Mission

Build a new independent GitHub repository for:

**EKAS Press Intelligence & RCA**

This is an EKAS add-on module for discrete manufacturing, initially focused on metal-stamping press lines.

This work must remain completely isolated from the existing `EKAS_Demo_UI` repository.

Do not modify, branch from, import experimental code into, or otherwise affect `EKAS_Demo_UI`.

The objective is to build a production-quality prototype that can later integrate with EKAS through a stable module contract.

---

# 1. NON-NEGOTIABLE QUALITY STANDARD

This project does not accept:

- Partial implementations presented as complete
- Placeholder logic presented as production logic
- Canned RCA answers
- Phrase-specific hacks
- Fake sensor integrations
- Hard-coded expected conclusions
- Test weakening
- Silent fallbacks
- Synthetic evidence presented as real evidence
- Architecture shortcuts that prevent later EKAS integration
- Reimplementation of upstream work when the complete upstream implementation can be preserved and used
- “Almost there” or “good enough” completion claims

If a capability is not complete, identify it explicitly as incomplete.

The standard is:

**professional, inspectable, reproducible, testable software.**

---

# 2. REPOSITORY ISOLATION

Create a NEW repository.

Preferred repository name:

`EKAS_Press_Intelligence`

Alternative:

`EKAS_Press_Intelligence_RCA`

Target organization:

`AdaptiveFactoryAISolutions`

The repository must have no dependency on the working tree, build system, or runtime of `EKAS_Demo_UI`.

The only future EKAS dependency must be a versioned API/module contract.

Target relationship:

```text
EKAS
  ↓
Versioned module contract
  ↓
EKAS Press Intelligence & RCA
  ↓
Plant / historian / simulator sources
```

---

# 3. PRESERVE THE TWO UPSTREAM PROJECTS

The following repositories are foundational reference implementations:

## HistorianSim

Repository:

`ScottDuncanAI/HistorianSim`

Pinned baseline:

`14e616c382a9db8026cbb4ab86bdd803d56ca72e`

License:

MIT

## HistorianRCA

Repository:

`ScottDuncanAI/HistorianRCA`

Pinned baseline:

`8d12a821395ce5f72e464dc78cc2c10d05cbb9ed`

License:

CC BY 4.0

Do not loosely recreate selected ideas from these repositories.

Preserve the complete upstream work at the pinned revisions.

Maintain:

- Original license files
- Attribution
- Original source history/reference information
- Upstream commit pins
- Provenance documentation

The project must distinguish clearly between:

```text
UPSTREAM
ADAPTED
EKAS ORIGINAL
```

Do not modify upstream source silently.

Prefer an architecture such as:

```text
upstream/
  historiansim/
  historianrca/

ekas/
  press_simulator/
  press_rca/
  observability/
  contracts/
  ui/
```

or an equivalent architecture that preserves the upstream boundary.

If Git submodules are the best technical mechanism, use them.

If vendoring is necessary, document exactly why and preserve provenance.

---

# 4. PRODUCT PURPOSE

The module addresses a common real-world manufacturing condition:

- Presses have basic PLC control.
- SmartPAC 2 or similar press-control systems are available.
- Press-level information exists.
- Auxiliary equipment has limited instrumentation.
- Feeder, decoiler, lubrication, material-flow, and die-condition visibility is often incomplete.
- Plants know production was lost but cannot defensibly determine why.

EKAS Press Intelligence must determine:

1. What the plant can observe now.
2. What the plant cannot observe.
3. Which causes can be distinguished.
4. Which causes remain ambiguous.
5. What minimum additional signal would remove the most important ambiguity.
6. What evidence supports an RCA hypothesis.
7. What alternative causes can be ruled out.
8. What corrective action should be investigated first.
9. Whether the corrective action worked.
10. What operational and financial impact resulted.

---

# 5. FIRST PRODUCT CAPABILITY — PRESS OBSERVABILITY ASSESSMENT

Implement a governed observability model.

Example:

```text
AVAILABLE
Press state
SPM
Stroke count
Job
Part count
Press fault

PARTIAL
Die protection
Feeder state
Lubrication state

NOT OBSERVABLE
Strip position
Coil starvation
Feeder mechanical condition
Die degradation
Motor load signature
Visual progression
```

The system must calculate an explainable RCA coverage assessment.

Do not invent a percentage arbitrarily.

Define:

- fault classes
- evidence requirements
- currently available signals
- ambiguity relationships
- distinguishable causes
- indistinguishable causes

Then calculate coverage from that model.

---

# 6. SENSOR GAP ANALYSIS

This is a core differentiator.

Given existing plant signals, determine which additional measurement provides the greatest diagnostic value.

Example:

```text
Current RCA coverage: 46%

Add feeder position:
+17 percentage points

Add lubrication pressure:
+9 percentage points

Add material-present signal:
+8 percentage points

Projected coverage:
80%
```

Every recommendation must explain:

- Which ambiguity it resolves
- Which fault classes become distinguishable
- Why the signal is valuable
- Whether a discrete or analog signal is sufficient
- Whether existing PLC I/O can provide it
- Whether additional hardware is necessary

Do not recommend NVIDIA, cameras, vibration, or advanced sensors unless simpler instrumentation cannot satisfy the requirement.

---

# 7. PRESS-LINE DIGITAL MODEL

Create a discrete-manufacturing reference cell.

Initial topology:

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

The model must support relationships between assets.

Do not model components as unrelated tags.

---

# 8. SMARTPAC / PLC REALITY MODEL

The prototype must model the limited instrumentation that exists in real plants.

Initial available signals can include:

- Run state
- Stop state
- Press fault
- Stroke count
- SPM
- Part count
- Job
- Die identifier
- Basic die-protection signals
- PLC sequence state
- Existing feeder ready/fault where available
- Existing lubrication OK where available

Do not assume advanced auxiliary sensing exists.

The prototype must work meaningfully under this constrained state.

---

# 9. SYNTHETIC PRESS-LINE SIMULATOR

Adapt the full HistorianSim philosophy to a discrete press line.

Do not merely generate random manufacturing data.

Model relationships between:

- press cycle
- feeder
- strip progression
- decoiler/material supply
- die
- lubrication
- tonnage/load
- production
- quality
- maintenance events
- PLC states
- sensor behavior
- operator actions
- historian behavior

The simulator must support:

- normal operation
- realistic noise
- drift
- missing signals
- communication failures
- stuck values
- false alarms
- operator actions that are not faults
- fault ramp-in
- recovery
- known hidden ground truth
- reproducible seeds

---

# 10. INITIAL FAULT CATALOG

Implement at least these fault classes:

1. Feeder sensor drift
2. Feeder mechanical instability
3. Misfeed / strip progression fault
4. Material starvation
5. Decoiler interruption
6. Lubrication pressure loss
7. Die-protection trip
8. Progressive die wear
9. Abnormal tonnage/load
10. Press speed degradation
11. Repeated microstops
12. Quality deterioration
13. Operator speed/setpoint change — benign event
14. Planned stop — benign event
15. Historian communication dropout — artifact
16. Stuck sensor — artifact

Faults must have ground-truth definitions.

Each must specify:

- Cause
- Failed item
- Failure mechanism
- Start
- End
- Expected evidence
- Alternative causes
- Signals that distinguish those alternatives

---

# 11. HIDDEN GROUND TRUTH

Ground truth must be inaccessible to the RCA engine during diagnosis.

Maintain separation between:

```text
simulation truth
and
RCA evidence
```

The RCA engine must operate blind.

Only the benchmark evaluator can access both.

This separation must be enforced in code and tested.

---

# 12. RCA STATES

Use explicit governed states:

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

Do not label an observed correlation as a root cause.

A verified root cause requires additional verification evidence.

---

# 13. ALTERNATIVE-CAUSE ELIMINATION

For each significant diagnosis, EKAS must show:

```text
Primary hypothesis
Supporting evidence
Alternative cause A
Evidence against A
Alternative cause B
Evidence against B
Remaining ambiguity
```

A good RCA does not merely identify the most correlated tag.

It must explain why competing explanations are weaker.

---

# 14. BENCHMARK SCORING

Adapt the strongest concepts from HistorianRCA.

Score:

- Correct event detection
- Correct failed item
- Correct failure mechanism
- Evidence completeness
- Correct event timing
- Alternative-cause elimination
- False positives
- False root-cause claims

False positives must reduce the score.

Do not reward a system that labels every abnormal condition as a fault.

---

# 15. DATA QUALITY

Explicitly model and distinguish:

```text
PROCESS FAULT
CONTROL FAULT
INSTRUMENT FAULT
DATA ARTIFACT
OPERATOR ACTION
PLANNED EVENT
```

The system must not classify historian/dropout artifacts as physical machine faults.

---

# 16. MAINTENANCE INTEGRATION

Add synthetic maintenance records.

Support:

- Work orders
- Previous repairs
- PM history
- Repeat failures
- Maintenance notes
- Corrective action
- Verification

The RCA engine must be able to use maintenance history as additional evidence.

---

# 17. QUALITY INTEGRATION

Add synthetic quality evidence.

Support:

- Good count
- Scrap
- FPY
- Defect category
- Quality hold
- Measurement trend
- Die-related quality deterioration

Quality evidence must help distinguish production interruption from process degradation.

---

# 18. PFMEA / CONTROL PLAN EVIDENCE

Create prototype PFMEA and Control Plan data.

Link:

```text
Asset
→ Process step
→ Failure mode
→ Effect
→ Cause
→ Prevention control
→ Detection control
→ Actual event evidence
```

Do not use PFMEA as automatic proof of cause.

Use it as governed prior knowledge.

---

# 19. FINANCIAL IMPACT

Support distinct terms:

- Lost capacity
- Production opportunity
- Potential contribution at risk
- Estimated financial impact
- Avoided cost
- Verified savings

Never call opportunity value verified savings.

Link financial estimates to their source assumptions.

---

# 20. CORRECTIVE-ACTION VERIFICATION

After a simulated repair:

Compare before and after:

- Microstop rate
- Downtime
- SPM
- Throughput
- OEE
- Scrap
- Quality
- Repeat fault rate

The system must determine whether evidence supports improvement.

Do not declare success merely because a corrective action was recorded.

---

# 21. NVIDIA / ADVANCED EDGE

Treat advanced edge AI as optional.

Design an extension interface for:

- Computer vision
- Vibration
- Acoustic analysis
- High-frequency current
- Tonnage waveform
- Thermal imaging

Do not make NVIDIA hardware a requirement.

The architecture must remain vendor neutral.

The observability engine should determine whether advanced sensing is justified.

---

# 22. MODULE CONTRACT

Create an explicit integration contract for future EKAS use.

Suggested initial API surfaces:

```text
POST /observability/assess
POST /rca/investigate
GET  /rca/cases/{id}
GET  /rca/cases/{id}/evidence
POST /rca/cases/{id}/verify
GET  /sensor-gaps
GET  /assets
GET  /signals
POST /benchmark/run
GET  /benchmark/{id}/score
```

Use structured versioned schemas.

Do not couple the contract to React components.

---

# 23. UI PROTOTYPE

Recreate the previously demonstrated EKAS RCA experience inside this new repository.

Required:

- Chat-first interface
- Investigation case
- KPI strip
- Cause ranking
- Evidence timeline
- Alternative causes ruled out
- Recommended first action
- Qualification
- Evidence drawer
- Observability view
- Sensor-gap view
- Benchmark view
- Hidden-ground-truth reveal after scoring

The UI is a consumer of the module API.

It must not contain RCA business logic.

---

# 24. TEST STRATEGY

Required test layers:

### Unit
- fault generation
- signal behavior
- observability logic
- ambiguity calculation
- RCA evidence
- benchmark scoring

### Contract
- all module APIs
- schema compatibility

### Simulation invariants
- deterministic seed reproduction
- known fault ground truth
- physical/logical consistency
- no answer leakage

### Blind RCA
The RCA engine receives no answer key.

### Adversarial
- missing signals
- misleading correlation
- multiple plausible causes
- benign operator event
- historian artifact
- incomplete evidence

### Browser
Use visible browser testing for final UI acceptance.

---

# 25. PROVENANCE

Every conclusion must preserve:

```text
source
signal
asset
timestamp
calculation
rule/model
confidence
qualification
```

The prototype must make evidence inspectable.

---

# 26. DOCUMENTATION

Create:

```text
README.md
ARCHITECTURE.md
PRODUCT_REQUIREMENTS.md
UPSTREAM_PROVENANCE.md
LICENSES.md
FAULT_CATALOG.md
OBSERVABILITY_MODEL.md
RCA_GOVERNANCE.md
BENCHMARK_STANDARD.md
EKAS_INTEGRATION_CONTRACT.md
TEST_STRATEGY.md
```

Document all upstream modifications explicitly.

---

# 27. FIRST MILESTONE

Do not attempt the entire plant.

Milestone 1 is:

**One governed synthetic press line with constrained SmartPAC/PLC-level observability.**

Acceptance requires:

1. Complete press-line simulator.
2. At least 16 defined event/fault classes.
3. Hidden ground truth.
4. Baseline operating period.
5. Synthetic historian output.
6. RCA investigation.
7. Alternative-cause elimination.
8. Sensor-gap analysis.
9. Corrective-action verification.
10. Benchmark scoring.
11. Interactive UI prototype.
12. Stable EKAS module contract.
13. Full automated tests.
14. No dependency on `EKAS_Demo_UI`.

---

# 28. FIRST ACTIONS FOR CODEX

Begin by:

1. Unpack and inspect the supplied bootstrap package.
2. Verify that no path points into `EKAS_Demo_UI`.
3. Create the new independent repository.
4. Fetch the complete pinned HistorianSim repository.
5. Fetch the complete pinned HistorianRCA repository.
6. Verify both commit SHAs.
7. Verify both licenses.
8. Record upstream provenance.
9. Inventory every major capability in both upstream repositories.
10. Produce a preservation/adaptation matrix.

The matrix must classify every meaningful upstream capability as:

```text
PRESERVE
ADAPT
EXTEND
NOT APPLICABLE
```

For `NOT APPLICABLE`, give the technical reason.

Do not discard an upstream capability merely because the original domain is chemical manufacturing.

Determine how the underlying capability maps to stamping first.

---

# 29. STOP CONDITION

Before writing the press adaptation, report:

- New repository URL
- New repository HEAD
- Upstream SHAs
- License verification
- Preservation/adaptation matrix
- Proposed architecture
- Confirmation that `EKAS_Demo_UI` was not modified

Only after these are established should the implementation proceed.

This prevents an incomplete or distorted adaptation of the upstream work.

---

# 30. SUCCESS CONDITION

The prototype succeeds when it can answer:

> Why is this press losing production?

and correctly distinguish:

```text
WHAT THE DATA PROVES
WHAT THE DATA SUGGESTS
WHAT THE DATA CANNOT DISTINGUISH
WHAT ADDITIONAL SIGNAL IS NEEDED
WHAT ACTION SHOULD BE INVESTIGATED
WHETHER THE ACTION WORKED
```

That is the product.