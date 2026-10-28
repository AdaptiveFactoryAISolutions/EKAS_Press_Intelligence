# Architecture

## Product boundary

EKAS Press Intelligence & RCA is an optional EKAS module. It must be deployable, testable, and releasable without `EKAS_Demo_UI`.

The future EKAS UI integration boundary is the versioned contract in `contracts/module-api-v1.md`. The UI cannot depend directly on simulator internals, historian files, fault catalogs, or press-specific implementation classes.

## Governing flow

```text
Physical press / simulator
        ↓
Raw signals and events
        ↓
Source adapters
        ↓
Canonical signal registry
        ↓
Time alignment + quality
        ↓
Normalized manufacturing events
        ↓
Observability assessment
        ↓
RCA evidence graph
        ↓
Hypothesis + alternative elimination
        ↓
Governed diagnosis state
        ↓
Recommended investigation/action
        ↓
Human confirmation
        ↓
Verification + sustainment
        ↓
Operational / financial result
```

## Simulation and benchmark flow

```text
HistorianSim upstream engine
        ↓
EKAS stamping plant model
        ↓
Known hidden physical truth
        ↓
Sparse or enhanced instrumentation profile
        ↓
Historian-style outputs + events
        ↓
Blind EKAS RCA
        ↓
Evidence-backed claim
        ↓
Independent benchmark scorer
        ↓
Ground-truth comparison
```

## Truth states

RCA claims use these states only:

- OBSERVATION
- CORRELATION
- CONTRIBUTOR
- SUSPECTED_CAUSE
- EVIDENCE_SUPPORTED_CAUSE
- VERIFIED_ROOT_CAUSE
- CORRECTIVE_ACTION
- VERIFIED_RESULT
- SUSTAINED_RESULT

The module cannot promote a cause to `VERIFIED_ROOT_CAUSE` without explicit verification evidence or human confirmation defined by policy.

## Sparse instrumentation principle

Missing sensor coverage is a first-class result, not an error to hide.

If two physical causes create the same observable signature under the active instrumentation profile, EKAS reports an ambiguity. Sensor-gap analysis can then recommend the minimum signal needed to distinguish the causes.

## Vendor neutrality

NVIDIA, edge inference, cameras, vibration sensors, and advanced waveform processing are optional signal providers. They are not required architectural components.
