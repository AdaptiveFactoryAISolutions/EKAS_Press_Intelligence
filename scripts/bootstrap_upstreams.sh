#!/usr/bin/env bash
set -euo pipefail
export GIT_NO_REPLACE_OBJECTS=1
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR="$ROOT/vendor"
SIM_REPO="https://github.com/ScottDuncanAI/HistorianSim.git"
RCA_REPO="https://github.com/ScottDuncanAI/HistorianRCA.git"
SIM_SHA="14e616c382a9db8026cbb4ab86bdd803d56ca72e"
RCA_SHA="8d12a821395ce5f72e464dc78cc2c10d05cbb9ed"
mkdir -p "$VENDOR"
git -C "$ROOT" submodule update --init --recursive
clone_pin(){
  local url="$1" dir="$2" sha="$3"
  if [[ ! -e "$dir/.git" ]]; then
    git clone "$url" "$dir"
  fi
  git -C "$dir" fetch --all --tags --prune
  git -C "$dir" checkout --detach "$sha"
  test "$(git -C "$dir" rev-parse HEAD)" = "$sha"
}
clone_pin "$SIM_REPO" "$VENDOR/HistorianSim" "$SIM_SHA"
clone_pin "$RCA_REPO" "$VENDOR/HistorianRCA" "$RCA_SHA"
"$ROOT/scripts/verify_upstreams.sh"
echo "Verified complete pinned upstream repositories."
