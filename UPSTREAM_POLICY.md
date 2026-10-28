# Upstream Preservation and Adaptation Policy

## Purpose

HistorianSim and HistorianRCA contain substantial engineering and validation work. EKAS will use that work as a foundation, not recreate a reduced imitation.

## Mandatory rules

1. Preserve each upstream repository as a complete checkout under `vendor/` at the pinned commit.
2. Preserve every upstream license, copyright notice, documentation file, validation artifact, test, process model, simulator component, benchmark rule, and dataset-generation mechanism that exists at the pinned revision.
3. Do not delete an upstream capability merely because the first EKAS press prototype does not use it.
4. Do not edit upstream files in place for EKAS behavior. Prefer adapters, extension packages, new plant definitions, configuration, subclassing, composition, or patch layers with explicit provenance.
5. If an upstream defect must be corrected locally, record the change under `docs/upstream-patches/` with original behavior, reason, test, and upstream commit base.
6. Run upstream tests independently from EKAS tests.
7. Do not claim parity when upstream checkout verification or upstream tests fail.
8. Do not translate HistorianRCA's benchmark philosophy into canned press answers. Preserve blind ground truth, distractors, false-positive penalties, evidence requirements, and independent scoring.
9. Preserve reproducible seeds and exact scenario metadata.
10. Maintain a third-party notice with the exact pinned revisions and licenses.

## Current pins

| Upstream | Revision | License |
|---|---|---|
| ScottDuncanAI/HistorianSim | 14e616c382a9db8026cbb4ab86bdd803d56ca72e | MIT |
| ScottDuncanAI/HistorianRCA | 8d12a821395ce5f72e464dc78cc2c10d05cbb9ed | CC BY 4.0 |

## Adaptation strategy

HistorianSim remains the simulation engine and reference validation framework. EKAS adds discrete-manufacturing plant models, stamping fault catalogs, SmartPAC/PLC-style signals, sparse-observability profiles, and press-specific validation.

HistorianRCA remains a benchmark reference for blind diagnosis, evidence requirements, known ground truth, scoring, distractors, and false-positive discipline. EKAS adds manufacturing-specific RCA case semantics, multi-source evidence, maintenance/quality context, sensor-gap analysis, and action verification.
