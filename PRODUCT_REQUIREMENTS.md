# Product Requirements

## PR-001 — Standalone module
The module must build and run independently of EKAS Demo UI.

## PR-002 — Complete upstream foundation
The valid development environment must include verified complete checkouts of both pinned upstream repositories.

## PR-003 — Press-line model
The prototype must model one progressive press line with press, feeder, decoiler, lubrication, die protection, production, quality, and maintenance context.

## PR-004 — Sparse observability
The simulator must support an instrumentation profile representative of plants with SmartPAC 2, PLCs, and limited auxiliary sensors.

## PR-005 — Enhanced observability
The same physical scenario must support added sensors so the benchmark can measure the information value of instrumentation.

## PR-006 — Hidden ground truth
Fault type, failed component, mechanism, start/end, injected severity, and repair state must remain hidden from the diagnostic path.

## PR-007 — Distractors
The benchmark must include benign operator actions, normal process variation, sensor artifacts, communication outages, drift, and unrelated signals.

## PR-008 — Evidence
Every fault claim must identify evidence signals/events. Unsupported claims fail benchmark scoring.

## PR-009 — False-positive discipline
A false fault claim must reduce the benchmark score.

## PR-010 — Alternative elimination
EKAS must record plausible alternatives and evidence that supports or rules out each alternative.

## PR-011 — Sensor-gap analysis
For unresolved cause ambiguity, EKAS must identify the missing observation and rank candidate signals by expected ambiguity reduction.

## PR-012 — Action verification
The module must compare pre-action and post-action performance and preserve the distinction between recommendation, execution, verification, and sustainment.

## PR-013 — Financial governance
Capacity loss, potential contribution at risk, estimated impact, avoided cost, and verified savings must remain separate measures.

## PR-014 — Future module API
The only permitted future dependency from EKAS UI is the versioned API/contract surface.

## PR-015 — No silent substitutions
The module must not substitute another metric, scope, period, asset, signal, or cause when requested information is unavailable.
