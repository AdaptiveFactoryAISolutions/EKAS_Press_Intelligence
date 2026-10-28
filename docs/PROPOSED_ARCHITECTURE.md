# Proposed architecture — not implemented

Decision proposed for the charter checkpoint: preserve both complete upstream projects as pinned submodules and add composition-based Python extensions in the existing `src/ekas_press_intelligence/` package. No dependency on EKAS_Demo_UI is permitted.

## Boundaries

`vendor/HistorianSim/` and `vendor/HistorianRCA/` are UPSTREAM, unchanged. `src/ekas_press_intelligence/simulator/` will contain ADAPTED integration bridges and EKAS ORIGINAL press models. An external plant registration bridge will combine HistorianSim's continuous auxiliary dynamics with explicit stroke/feeder/decoiler/PLC transitions. Test the bridge against cycle-count, material-flow and timing invariants before using noisy outputs. Do not patch an upstream model to masquerade as a press.

Asset graph: Plant → Line 03 → Press 27, Feeder 27, Decoiler 27, lubrication, die, material, part, inspection and maintenance. Relationships include feeds, lubricates, uses-die, produces, inspects and maintains. Signal registry entries bind source, asset, units, acquisition quality and available instrumentation; sparse/enhanced profiles select observations from the same simulated physics.

## Evidence and truth

Simulation writes private truth, intervention state and reproducibility config to evaluator-owned storage. Historian output crosses an allowlisted evidence-export boundary. The RCA service receives only observed signals, quality, asset relationships and authorized maintenance/quality records. It has no truth-store handle, shared simulator object, file permission or route to retrieve answers. The benchmark evaluator alone reads both. An evaluated submission is frozen before post-score reveal; use distinct service identities/storage permissions and test import, file, serialization and API leakage. Naming folders alone is insufficient enforcement.

HistorianSim's full-resolution primary record, convenience grid, tag dictionary and validation artifacts remain available. Discrete signals require edge-safe export and alignment; quality failures must not become physical diagnoses.

## Observability and diagnosis

Define failure requirements and pairwise discriminators in versioned catalog data. Calculate identifiable classes and unresolved equivalence groups from available evidence. Coverage must state numerator, denominator and any explicit weights. Recompute the same model with each candidate signal to obtain marginal gain; do not add overlapping gains arithmetically. Installation recommendations distinguish existing PLC I/O, engineering confirmation, and hardware requirements. Prefer adequate discrete/analog signals before advanced providers.

RCA builds evidence-linked hypotheses and alternatives, with supported, contradicted or unresolved dispositions. PFMEA is prior knowledge only. Use exactly the charter states: OBSERVED_ANOMALY, CONTRIBUTOR, SUSPECTED_CAUSE, EVIDENCE_SUPPORTED_CAUSE, VERIFIED_ROOT_CAUSE, CORRECTIVE_ACTION, VERIFICATION, SUSTAINED. Promotion requires explicit evidence policy. A recorded repair alone cannot verify a cause or improvement.

Verification compares comparable operating windows, exposure, job/material mix and data quality for microstops, downtime, SPM, throughput, OEE, scrap, quality and repeat failures; inconclusive is an allowed result. Financial estimates retain assumptions and separate lost capacity, opportunity, contribution at risk, estimated impact, avoided cost and verified savings.

## Contract, persistence and UI

Versioned schemas and API routes implement the charter's assessment, investigation, cases/evidence/verification, sensor-gaps, assets/signals and benchmark operations. Persist cases, evidence references, decisions, action/verification records and immutable benchmark submissions. Typed failures expose unavailable data or ambiguous intent without silent substitutes. Authentication and truth-access separation must be tested at route level. The API is framework-neutral at the contract boundary; Python service framework and storage selection remain implementation decisions.

The chat-first UI consumes those APIs; KPI strip, rankings, evidence timeline/drawer, alternatives, observability, gaps, scoring and post-score truth reveal render server results. No diagnosis, scoring or confidence inference belongs in UI code. The archived HTML is reference-only. Sensor-provider interfaces accept provenance/quality/timing from optional vision, vibration, acoustic, current, tonnage waveform or thermal adapters without requiring a vendor.

## Qualification sequence

Preservation checkpoint → hybrid engine and 16-event catalog → sparse observability and blind evidence → governed RCA/verification/scoring → API/persistence → interactive UI → full automated and visible-browser acceptance. Keep upstream and EKAS tests separate. Explicitly test benign actions, artifacts, missing discriminators, misleading correlation, deterministic reproduction, physical consistency and answer leakage. Historical upstream validation and three starter tests do not qualify the press module.
