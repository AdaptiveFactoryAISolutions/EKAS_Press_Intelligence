# Guided 1,500-ton line: implementation evidence

The approved scope is a generic continuous-strip line with ten die stations,
reel/slack loop/straightener/feeder, lubrication and offal handling, discharge,
hot-water spray washing and manual customer-container packing. Maximum press
speed is 10 strokes/minute (600/hour). The beginner preset runs at 8 SPM.

The eight-screen wizard resolves the actual native ScenarioConfig. Saved drafts
use revision checks; an immutable run binds configuration and runtime-manifest
hashes. Lost-response retries recover the existing run. Server checks remain
authoritative for direct API clients. The independently installable SDK uses
HTTP only. A separate external EKAS application's editable source and contract
have not been identified; no external connection is claimed.

## Numerical basis and source preservation

The model's [engineering basis](../../extensions/stamping_line/DESIGN.md)
documents generic assumptions, sensors, inventory and energy ledgers and limits.
The optimized C++ kernel preserves the Python RK4/event reference and its
maximum 0.1-second internal quantum. Native acquisition, controllers, instrument
faults, validation and exports remain in HistorianSim. Differential checks cover
state, counters, queues, events and observations; performance is not obtained
by shortening the native 14-day sweep or changing its tolerances.

The packing preset uses two people at six parts/minute each. With 50 parts per
container and a 30-second change, nominal effective capacity is
60/(60/12+30/50) = 10.714 parts/minute. This generic builder choice supports the
10-SPM ceiling; it is not a measured customer work standard. Deliberately lower
washing/packing capacity requires a saved bottleneck acknowledgment.

The complete protected upstream pins remain HistorianSim
`14e616c382a9db8026cbb4ab86bdd803d56ca72e` and HistorianRCA
`8d12a821395ce5f72e464dc78cc2c10d05cbb9ed`. Authored changes are explicit overlays
and eleven recorded patches. Patch 0011 fixes native short-episode sizing so a
short practice history is not assigned a minimum half-day fault. Existing
optional-PFD compatibility assertions remain explicitly disclosed in provenance.

## Verification record

- Core: 190 passed, zero skipped, 252.395 seconds. Report:
  `work/native-test-reports/core/76a8966f-3a2e-45fc-b6a5-1441e2334cdb`.
- Physics/PFD: 65 passed, zero skipped, 99.258 seconds. Report:
  `work/native-test-reports/physics/234ad5fe-6359-4955-8522-8a62bc454e89`.
  Its manifest has identical parsed contents/source/artifact hashes to R6;
  byte serialization ordering differs and both exact hashes are retained.
- Browser: 27 passed, zero skipped, 138.787 seconds, including real native
  wizard-to-evidence generation and the repaired request races. Report:
  `work/native-test-reports/browser/4082ce64-f0d4-43a3-8902-02dd848d77fd`.
- R6 model tests: 24 passed. Nine real native cases (healthy plus eight faults)
  passed faulted and twin engineering accounting. Full 14-day native catalog,
  day-six onset, seed 99, moderate severity and 20-second scan: all eight causes
  passed all five catalog checks in 139.60 seconds under concurrent test load.
  No undiagnosable cause, false-flat declaration, collision, wrong direction or
  dangling tag remained. Evidence: `work/line-r6-model-verification.json` and
  `work/line-r6-catalog-final.json`.
- Compiled/reference parity covers ten dynamic scenarios. One-day reference
  execution took 96.87 seconds versus 0.703 seconds compiled; the original
  integration quantum and events remain unchanged. These are observed host
  timings, not a performance guarantee.
- Server and standalone-client wheels built. Canonical client bytes match;
  standalone imports do not import simulator/server code. The client depends
  only on httpx. Server assets include the wizard JavaScript and CSS.
- R6 complete prepared-upstream suite: 188 passed, one failed, zero skipped,
  819.837 seconds. The failure correctly rejected practice metadata claiming
  the nine-cause RCA benchmark while declaring eight causes. Report:
  `work/native-test-reports/upstream/3aed3ae6-7909-48e9-a0f0-696597b3697c`.
  This is adverse evidence, not a passing full suite.

Pre-recipe-correction R6 manifest SHA256:
`281daab331f444082c128f3de2701cdacc4ca0c126bd5d59572b792e7537ce7f`.
Compiled kernel source SHA256:
`79366716cfa5c329f0ee8cbe55b9935a8796f429f71c91aa57d96e31c9a7494d`;
artifact SHA256:
`d8730d5317af6f01728cce8e200ed4a16ff679099d05de0a72a45b655c86337f`.
The derived-source verifier reproduced the complete runtime and compiler
artifact. Build flags prohibit fast-math and floating-point contraction.

The owned service on port 18729 was reloaded only after verifying process
identity, exact state/runtime paths and no active jobs. Its three earlier
datasets/runs remain. Final R6 SDK checks generated one-hour healthy job
`b373f5f8-1083-4117-bc27-c55899118c73` and feeder-slip job
`bdff8015-5f09-42df-8211-b04eb3858398`. Both passed engineering and public measured
queries; both retained failed native acquisition checks and UNQUALIFIED_PRACTICE.
The reference service on 18728 retains its five datasets, eleven jobs and frozen
submission; before/after record-value hashes were unchanged.

## Final R7 recipe correction

The custom practice scenario now declares eight unique causes explicitly and
does not claim `rca-benchmark`. The upstream's sole named benchmark recipe
requires nine causes across at least three symptoms; inventing a ninth fault
would not repair this generic practice scenario. Native duration profiles remain
available for the eight-case scenario; the separate wizard retains its exact
60-minute, zero-or-one-selected-fault configuration.

The entire unchanged upstream recipe test file passed: 14 cases, zero skips,
2.04 seconds. All eight pinned causes remain in quick/standard plans for seeds
1/7/42/123. No original test or threshold was modified; the correctly classified
practice scenario is no longer added to RCA-benchmark parametrization.
Evidence: `work/line-r7-recipe-verification.json`.

Final R7 manifest SHA256:
`d4fec6156a82d1d97825cf2fd88aa81fe6d8259f369cc910aeea7b7baa20ebc3`.
Derived-source verification passed. Comparing R6/R7 runtime hashes finds exactly
one changed file, `stamping_line/__init__.py`; all physics, compiled artifacts,
instruments and catalog expectations are unchanged. The final complete local
prepared-upstream rerun passed **187 tests, zero skipped**, in 1,536.744 seconds:
`work/native-test-reports/upstream/87367683-f70a-43c4-992f-fc6808c82ec9`.
Its source/test/configuration hashes remain recorded. The two invalid added
RCA-benchmark parametrizations disappear when practice is correctly classified;
no original test source was changed or skipped. Remote CI remains separately
blocked as recorded below.

R7 controlled reload preserved the five existing practice datasets/jobs. Final
one-hour healthy job `5d1c77e6-a731-4b1a-8bd7-8bf4857d99ac` and feeder-slip job
`fe5e01a3-faf4-4340-a07d-9aab5cb0d013` completed via the SDK with passing
engineering and public sample queries. Both remain unqualified and retain their
failed native acquisition checks. Final source-bound physics/PFD: 65 passed,
zero skipped, 116.921 seconds, report
`work/native-test-reports/physics/cdc4d532-e34a-4e46-8595-678d4fc63181`.
Final actual browser: 27 passed, zero skipped, 137.423 seconds, report
`work/native-test-reports/browser/c569ea44-378f-4b85-8574-66e34d8fcce8`.
Exact-head remote execution status and local upstream receipts are recorded in
[draft PR2](https://github.com/AdaptiveFactoryAISolutions/EKAS_Press_Intelligence/pull/2).

The [machine-readable software receipt](../../validation/native/guided-line-software-receipt.json)
binds these local results, source hashes and the remote execution block.

## Publication and remote execution block

Software commit `b314e3a4c705279e8bd0a3b026f2d7699f40e1ec` was published to the
candidate branch. GitHub native workflow `40921693639`, original validation
workflow `40921693702` and CodeQL workflow `40921679393` failed before executing
any steps. GitHub's annotation states: “The job was not started because your
account is locked due to a billing issue.” This was verified on native-upstream
check `123616343181` and Python CodeQL check `123616302165`.

No current-head remote test success or CodeQL clearance is claimed. Billing
settings, branch protections and failed checks were not changed or bypassed.
The account owner must resolve the lock before those remote checks can run.
The simulator and local evidence browsing remain available independently.

A duplicate final core run was stopped to reduce host memory pressure after its
owned process reached about 2.8 GB RSS; unrelated workloads were untouched.
Its retained report is marked TEST_INTERRUPTED and contains 187 passing cases
plus three worker timeout failures, not a passing layer:
`work/native-test-reports/core/88c596eb-7fad-4883-9fac-c483e69dc093`.
The three failed tests were rerun separately with unchanged deadlines and all
passed in 23.00 seconds (`work/final-worker-timeout-rerun.xml`). Memory pressure
fell from avg10 68.88% to 0.00% after the owned extra process was removed. This
supports an environmental timing explanation; it does not erase the adverse
report or substitute for a fresh remotely executed core check. The earlier
complete 190-test backend pass remains a separate receipt above.

All eight original project validation layers were also run locally through
their existing runner and passed: unit 52, simulation 23, contract 3, blind 38,
observability 6, API 20, UI 1 and browser 3. Layer counts overlap and must not be
summed as unique tests. Logs and result receipt are retained at
`work/final-legacy-layers-b314e3a`. Fresh browser artifacts were hash-compared
and retained there; previously published browser evidence was restored rather
than overwritten. No paid provider was called. The unchanged pinned 173-test
baseline's prior pass is preserved; no new remote baseline pass is asserted.

## Retained adverse and superseded results

- Python R2 full-upstream run was interrupted after 1,210.585 seconds because
  the new multi-day model made the suite impractically slow. Report:
  `work/native-test-reports/upstream/4f5047c9-bab4-4c7e-9f90-44664f1d66ea`.
  It is not a passing suite. The compiled implementation addresses execution
  cost without changing the numerical quantum.
- R3 upstream run was explicitly interrupted after 198.976 seconds when review
  found false single-channel competitor exclusions in fault metadata. Report:
  `work/native-test-reports/upstream/8689ec97-e453-4dd2-8e69-f8f11da08675`.
  Compatible causes must not be eliminated by a shared signal direction.
- R4 upstream run was interrupted after 265.299 seconds after the final
  long-horizon investigation demonstrated two false-flat secondary scrap
  declarations. Report:
  `work/native-test-reports/upstream/105b6c43-2559-4fc6-9d29-873260088dd4`.
  Those changes are delayed event-clock/acquisition-phase sensitivity, not
  physical scrap deterioration. Final catalog guidance says so explicitly.
- R3 physics collected 64 cases: 63 passed and one source-provenance check
  failed while source epochs were changing. Report:
  `work/native-test-reports/physics/e57a450d-45f4-47b8-b241-b438c59a1f9c`.
  The isolated exact check subsequently passed in 5.47 seconds; the final full
  layer is still required after source freeze.
- A browser run failed before launch because the repository-local Chromium
  cache path was absent from the shell environment. Report:
  `work/native-test-reports/browser/477c40d5-0905-40db-bf73-7c4a7c71b866`.
  The rerun used the installed cache, with no browser download or test skip.
- That rerun passed 24 of 25 cases and reproduced a real asynchronous dataset
  selection race after successful native generation. Report:
  `work/native-test-reports/browser/245bcfbb-1c51-433d-b93b-a6277d35c509`.
  Registry refresh must preserve the user's selected dataset while its metadata
  loads; a timed sleep is not an acceptable repair.

## Qualification boundary

All wizard output is explicitly **UNQUALIFIED_PRACTICE / UNVALIDATED**, even
when engineering accounting passes. The unchanged native validation battery
runs and retains its findings. Deterministic encoder coloring and healthy-run
fault/twin expectations are not waived. Engineering ledger failures still
block output registration. Software, browser, catalog or parity checks do not
establish manufacturer accuracy, physical safety or production qualification.

No paid provider calls, production activation, physical controller writes or
merge are part of this implementation. Earlier source epochs and adverse press
qualification records remain in the execution ledger.
