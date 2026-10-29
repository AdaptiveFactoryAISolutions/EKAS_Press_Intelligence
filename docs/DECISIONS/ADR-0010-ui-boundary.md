# ADR-0010 — Same-origin product UI and API boundary

Status: Implemented architectural decision; milestone acceptance remains separate.

## Decision

Serve local HTML/CSS/JavaScript with the Python service. UI requests investigation, evidence, coverage, benchmarks and corrective verification through v1 operations.

## Reason

Keep causal rules and financial/verification logic out of browser code. Inspect real network/browser flows beyond asset rendering tests.

## Consequences and limits

CI headless smoke complements visible-browser acceptance. Neither a rendered control nor an API unit test alone proves the complete user flow.
