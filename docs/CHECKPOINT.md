# Charter section 29 — preservation checkpoint

Date: 2026-10-28. Scope: sections 28–29 only; no new press adaptation written.

Repository: https://github.com/AdaptiveFactoryAISolutions/EKAS_Press_Intelligence (private).
The checkpoint commit is the `main` commit containing this report. The delivery message supplies its exact SHA, verified against the GitHub branch after push; this avoids embedding a self-referential commit hash.

| Required item | Result |
|---|---|
| New independent repository | Created under the requested organization; initialized independently on `main` |
| HistorianSim SHA | `14e616c382a9db8026cbb4ab86bdd803d56ca72e` |
| HistorianRCA SHA | `8d12a821395ce5f72e464dc78cc2c10d05cbb9ed` |
| Licenses | Actual pinned MIT and CC BY 4.0 declarations inspected; originals and attribution preserved; nested PFD-generator MIT retained |
| Complete upstream preservation | Non-shallow, clean, pinned submodules; 107 + 12 tracked files; full Git integrity checks passed |
| Preservation/adaptation matrix | `PRESERVATION_ADAPTATION_MATRIX.md`; every major subsystem plus exhaustive file inventory in `upstream-inventory.json` |
| Proposed architecture | `PROPOSED_ARCHITECTURE.md`; proposed only |
| EKAS_Demo_UI isolation | No access, changes, branch, runtime or build dependency introduced by this task |

## Checks and limitations

- ZIP path inspection: no absolute paths, traversal or symlink entries. Archive hash and 26 extracted source-file provenance recorded. Embedded Git metadata, caches and bytecode excluded.
- Both commits checked out and independently verified with replacement-object interpretation disabled. Both `git fsck --full --no-dangling` runs exited 0. Both upstream working trees clean.
- `bash scripts/verify_upstreams.sh`: PASS after reproducing and fixing the directory-only `.git` check to accept submodule Git files. This was a setup correction, not upstream source modification.
- Starter EKAS tests: `PYTHONPATH=src python3 -m pytest tests -q`: **3 passed**. These tests cover only starter behavior; no product qualification follows.
- HistorianRCA Parquet metadata readable: 5,650,781 primary rows; 129,600 regular-grid rows; 90 tag records. This is structural inspection, not complete data-content or diagnostic validation.
- HistorianRCA has no public answer key, executable scorer or automated test suite in this pinned tree. No blind submission or upstream score is claimed.
- HistorianSim complete upstream test suite: **173 passed in 391.36 seconds (6:31)**, exit 0. Initial collection resolved an unrelated installed `tests` package rather than upstream `tests.conftest`. Rerun uses an explicit in-memory `tests` namespace pointing to the preserved test directory and disables unrelated host pytest plugins. No upstream file or assertion changed. This is test-suite evidence, not a separate full-duration dataset-generation acceptance run.

Baseline harness used from the repository root:

```bash
PYTHONPATH=vendor/HistorianSim/src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 - <<'PY'
import pathlib, sys, types, pytest
p = pathlib.Path('vendor/HistorianSim/tests').resolve()
m = types.ModuleType('tests')
m.__path__ = [str(p)]
sys.modules['tests'] = m
raise SystemExit(pytest.main([str(p), '-q']))
PY
```

## Bootstrap discrepancies requiring later implementation

The retained bootstrap `ARCHITECTURE.md` uses different state names from the charter. The proposed architecture uses the charter's exact vocabulary. Resolve the retained document and runtime schemas together during adaptation.

Starter scoring uses truth event IDs and string matching instead of blind temporal matching; a nonempty evidence-ID tuple is not evidence validation. Observability counts classes connected to missing signals without a complete pairwise discrimination/coverage model. The static HTML is a UI reference, not an API consumer acceptance result. The module contract is prose only; there is no complete API, service persistence, enforced truth isolation, physical press simulator, 16-class implemented catalog, maintenance/quality integration, financial verification or browser acceptance.

Inherited CI runs only the three starter tests and does not qualify upstream or full product behavior. It must not be used as a release-readiness claim. The baseline helper uses `python` and presumes an installed test environment; this host exposes `python3` and the isolated harness is recorded explicitly.

No top-level open-source license for EKAS original/bootstrap material has been selected. Upstream licenses retain their own scope. No blanket project license is inferred.

The checkpoint establishes inspectable sources and an adaptation proposal. It does not establish upstream runtime parity, Milestone 1, real sensor integration, physical root-cause diagnosis or production readiness. Work stops here for the requested report before press adaptation.
