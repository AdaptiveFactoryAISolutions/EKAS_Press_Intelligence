# Upstream provenance — preservation checkpoint

Captured 2026-10-28. This is a preservation checkpoint, not Milestone 1 acceptance.

| Upstream | Source | Pinned commit | License declaration | Tracked files |
|---|---|---|---|---:|
| HistorianSim | https://github.com/ScottDuncanAI/HistorianSim | `14e616c382a9db8026cbb4ab86bdd803d56ca72e` | MIT, copyright 2026 Scott Duncan | 107 |
| HistorianRCA | https://github.com/ScottDuncanAI/HistorianRCA | `8d12a821395ce5f72e464dc78cc2c10d05cbb9ed` | CC BY 4.0, copyright 2026 Scott Duncan | 12 |

Both are complete non-shallow Git clones, recorded as submodules under `vendor/`. Their pinned ancestor histories contain respectively 15 and 2 commits. Both passed `GIT_NO_REPLACE_OBJECTS=1 git fsck --full --no-dangling`. Both working trees were clean. No upstream source changes were made. The entire pinned trees, including tests, skills, examples, data and diagrams, remain available. Source instructions are retained as upstream material; inspection does not authorize executing their workflows or contacting anyone.

`docs/upstream-inventory.json` records every pinned path, tree identity, license-file SHA-256, archive SHA-256 and verification snapshot. License verification here means inspection of the actual pinned license declarations and preservation of the original files. HistorianSim also includes the PFD-generator license at `.claude/skills/simulate/pfd-generator/LICENSE`; it remains preserved independently. HistorianRCA's `CITATION.cff` remains authoritative attribution metadata. See [LICENSES.md](LICENSES.md).

## Bootstrap provenance and changes

Input: `EKAS_Press_Intelligence_RCA_bootstrap.zip`, SHA-256 `ca538477a2f43ac44aeade93bfc2aed13750a0bc92789a8afc97fb31d5ec2fa3`.

26 source files were extracted. Embedded `.git`, `.pytest_cache` and `__pycache__` entries were excluded; the original archive remains unchanged at its supplied location. Extraction preflight found no absolute paths, parent traversal or symlink entries. Text references to `EKAS_Demo_UI` were isolation documentation, not executable dependencies. The vendor README has a relative command whose wording is inconsistent with running from the repository root; it is not an external repository reference.

The new repository was initialized independently on `main`; no branch or code was taken from EKAS_Demo_UI. We did not access or modify that repository. The assertion is based on operations performed in this task, not an audit of concurrent activity elsewhere.

Local setup changes: registered both submodules; made shell scripts executable; accepted Git-file submodule metadata in bootstrap/verification scripts; initialized submodules during bootstrap; disabled replacement-object interpretation in those scripts. Added preservation and checkpoint documentation. Existing product code and UI remain bootstrap material, not newly qualified implementation. No upstream patch layer exists because no upstream changes were made.

## Reproduce

```bash
git clone --recurse-submodules https://github.com/AdaptiveFactoryAISolutions/EKAS_Press_Intelligence.git
cd EKAS_Press_Intelligence
bash scripts/verify_upstreams.sh
git submodule status
```

Submodule pins, not moving upstream branches, define the baseline. Upstream baseline execution is separate from preservation verification. Test execution and limitations are recorded in `docs/CHECKPOINT.md`.

HistorianRCA intentionally withholds its answer key. Its public pinned repository contains no scorer implementation or automated test suite. Preserve the challenge; do not fabricate an upstream score or retrieve private answers as part of a blind investigation.

## Milestone 1 continuation

The accepted preservation checkpoint is historical. Milestone 1 replaces the starter truth-ID scorer and coverage heuristic with canonical temporal and pairwise entry points; the original demo command now launches the real API-backed product. New adaptations remain outside upstream. Both pins and original license files remain unchanged. Startup rejects shallow/modified upstream trees or a HistorianSim import from an unrelated installation. Current implementation/test evidence is in MILESTONE_1_ACCEPTANCE.md and VALIDATION_REPORT.md.
