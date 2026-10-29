# ADR-0003 — Hybrid discrete and continuous press model

Status: Implemented architectural decision; milestone acceptance remains separate.

## Decision

Use explicit per-second press/feed/PLC transitions and cumulative good/scrap/stroke counters, with coupled physical fault mechanisms and analog noise. Reuse pinned HistorianSim primitives outside upstream source.

## Reason

Continuous analog models alone cannot preserve stroke counts or feed interlocks. Sparse and enhanced profiles project the same physical run; instrumentation changes observation, not scenario truth.

## Consequences and limits

One-second resolution is a synthetic reference model; it is not a controller scan or validated plant digital twin.
