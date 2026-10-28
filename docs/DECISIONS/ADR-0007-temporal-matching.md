# ADR-0007 — Temporal benchmark scoring

Status: Implemented architectural decision; milestone acceptance remains separate.

## Decision

Use longest-overlap one-to-one matching with a versioned one-second tolerance. Reward evidence-backed item plus mechanism; penalize false positives and unsupported certainty.

## Reason

Shared truth IDs leak answers. Duplicate and spanning claims must not inflate detection. Preserve the upstream +1/+2/-1 philosophy with explicit evidence checks.

## Consequences and limits

BENCHMARK_STANDARD.md governs actual semantics. Valid references establish provenance, not automatic causal sufficiency. Correct unresolved candidates remain visible.
