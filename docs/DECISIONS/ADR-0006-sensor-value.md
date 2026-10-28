# ADR-0006 — Recomputed sensor information value

Status: Implemented architectural decision; milestone acceptance remains separate.

## Decision

Evaluate each missing-signal augmentation against the same discrimination model, returning newly separated ambiguity pairs and acquisition metadata.

## Reason

Independent additive gains double-count overlapping information. Recommendations must resolve actual modeled ambiguities.

## Consequences and limits

Gains describe catalog separation, not priced hardware ROI or measured site reliability.
