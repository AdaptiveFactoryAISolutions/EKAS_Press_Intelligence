# EKAS Press Intelligence Module API v1 — Draft

This contract is intentionally technology-neutral.

## Operations

### assess_observability
Input: plant/line/asset scope and available signal catalog.
Output: observable capabilities, ambiguities, unobservable failure classes, and sensor-gap recommendations.

### analyze_event
Input: scope, period/event, question or investigation objective.
Output: governed RCA case with evidence and qualification.

### get_rca_case
Output fields include:

- case_id
- scope
- period
- observed_problem
- loss_metrics
- evidence[]
- hypotheses[]
- alternatives[]
- diagnosis_state
- recommended_actions[]
- verification_plan
- financial_context
- provenance
- certification

### start_benchmark
Creates a hidden-truth challenge from a pinned simulator scenario and seed.

### submit_benchmark_claim
Submits diagnosis plus evidence without revealing ground truth.

### score_benchmark
Scores event detection, root cause, evidence completeness, false positives, timing, and unsupported certainty.

### verify_action
Compares post-action results with the pre-action baseline.

## Integration rule

No EKAS UI component may read files under `vendor/`, `simulator/`, or benchmark hidden-truth storage directly.
