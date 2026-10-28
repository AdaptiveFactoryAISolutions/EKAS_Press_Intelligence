# EKAS Press Intelligence & RCA

> **Status: upstream-preservation checkpoint only.** The press adaptation and
> Milestone 1 acceptance are incomplete. Existing source/UI are supplied bootstrap
> material, not qualified product behavior. Start with [the checkpoint](docs/CHECKPOINT.md),
> [provenance](UPSTREAM_PROVENANCE.md), [the capability matrix](docs/PRESERVATION_ADAPTATION_MATRIX.md)
> and [proposed architecture](docs/PROPOSED_ARCHITECTURE.md).

Standalone EKAS add-on prototype for press-line observability, governed root-cause analysis (RCA), synthetic fault benchmarking, sensor-gap analysis, corrective-action verification, and financial impact.

## Isolation rule

This repository is intentionally independent from `EKAS_Demo_UI`.

- Do not import this repository from `EKAS_Demo_UI` during prototype development.
- Do not add this repository as a submodule of `EKAS_Demo_UI` during prototype development.
- Do not copy experimental code into `EKAS_Demo_UI`.
- Integration is permitted only through the versioned module contract under `contracts/` after independent acceptance.

## Upstream foundation

This project is designed to comprehensively use, preserve, and extend two upstream projects:

- `ScottDuncanAI/HistorianSim` pinned at `14e616c382a9db8026cbb4ab86bdd803d56ca72e`
- `ScottDuncanAI/HistorianRCA` pinned at `8d12a821395ce5f72e464dc78cc2c10d05cbb9ed`

The upstream projects are not rewritten into simplified substitutes. `scripts/bootstrap_upstreams.sh` obtains the complete repositories and verifies the pinned commits. EKAS-specific press-line behavior is implemented beside them through adapters, contracts, and new plant models.

Read `UPSTREAM_POLICY.md` before changing simulator or benchmark code.

## Product objective

A typical stamping plant has useful press signals but limited auxiliary instrumentation. EKAS Press Intelligence & RCA must answer four questions:

1. What can the current signals prove?
2. What can they not prove?
3. What is the strongest evidence-supported cause of production loss?
4. What minimum additional signal will reduce the most important RCA ambiguity?

The module must never create certainty from missing instrumentation.

## First prototype

The first prototype models one progressive press line with:

- SmartPAC-like press state and production signals
- PLC sequence and fault bits
- Feeder, decoiler, lubrication, die-protection, production, quality, and maintenance domains
- Configurable instrumentation coverage so the same simulated physical process can be viewed through a sparse real-world signal set or an enhanced signal set
- Hidden fault ground truth
- Benign operator actions and data-quality artifacts
- Evidence-based diagnosis and alternative-cause elimination
- Sensor-gap recommendations
- Post-action verification

## Repository map

```text
contracts/                 Versioned EKAS integration boundary
docs/                      Architecture, requirements, decisions
src/ekas_press_intelligence/
  benchmark/               Hidden truth, challenge scoring, blind-test logic
  contracts/               Runtime models for module API
  observability/           Signal coverage and sensor-gap analysis
  rca/                     Evidence, hypotheses, alternatives, verification
  simulator/               HistorianSim integration and press-line plant model
  terminology/             Canonical manufacturing terms and aliases
ui-prototype/               Isolated prototype UI assets
vendor/                     Complete upstream checkouts after bootstrap
scripts/                    Reproducible setup and verification
```

## Quick start

```bash
./scripts/bootstrap_upstreams.sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
python -m ekas_press_intelligence.demo
```

The upstream bootstrap is a required gate. A local build without verified upstream sources is an incomplete development environment, not a valid product build.
