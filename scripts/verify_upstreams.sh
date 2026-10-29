#!/usr/bin/env bash
set -euo pipefail
export GIT_NO_REPLACE_OBJECTS=1
unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIM="$ROOT/vendor/HistorianSim"
RCA="$ROOT/vendor/HistorianRCA"
SIM_SHA="14e616c382a9db8026cbb4ab86bdd803d56ca72e"
RCA_SHA="8d12a821395ce5f72e464dc78cc2c10d05cbb9ed"
fail(){ echo "UPSTREAM VERIFY FAIL: $*" >&2; exit 1; }
[[ -e "$SIM/.git" ]] || fail "HistorianSim complete checkout missing"
[[ -e "$RCA/.git" ]] || fail "HistorianRCA complete checkout missing"
[[ "$(git -C "$SIM" rev-parse HEAD)" == "$SIM_SHA" ]] || fail "HistorianSim revision mismatch"
[[ "$(git -C "$RCA" rev-parse HEAD)" == "$RCA_SHA" ]] || fail "HistorianRCA revision mismatch"
[[ -f "$SIM/LICENSE" ]] || fail "HistorianSim LICENSE missing"
[[ -f "$RCA/LICENSE" ]] || fail "HistorianRCA LICENSE missing"
[[ -f "$SIM/README.md" ]] || fail "HistorianSim README missing"
[[ -f "$RCA/CHALLENGE.md" ]] || fail "HistorianRCA challenge definition missing"
for upstream in "$SIM" "$RCA"; do
  [[ "$(git -C "$upstream" rev-parse --is-shallow-repository)" == false ]] || fail "Shallow upstream history"
  [[ -z "$(git -C "$upstream" status --porcelain --untracked-files=normal)" ]] || fail "Upstream working tree modified"
done
echo "UPSTREAM VERIFY PASS"
