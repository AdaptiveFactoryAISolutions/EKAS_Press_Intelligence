#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/verify_upstreams.sh"
python -m pytest "$ROOT/vendor/HistorianSim/tests"
# HistorianRCA is primarily a benchmark/data repository. Preserve and validate
# its documented challenge/data artifacts separately as the EKAS benchmark import is implemented.
