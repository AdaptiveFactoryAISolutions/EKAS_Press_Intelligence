# Milestone 1 validation report

Candidate branch: `milestone-1`, based on accepted preservation checkpoint `e1d04e539a87183a34835caf449395354c454b43`. The exact delivered commit is reported in the delivery message and PR head; this file does not embed a self-referential commit hash.

## Executed checks

| Layer | Actual result | Retained evidence |
|---|---:|---|
| Pinned HistorianSim complete suite | 173 passed, zero skips; exit 0 | validation/upstream-result.json; baseline helper enforces count |
| Complete EKAS suite | 135 passed, zero failures/errors/skips | validation/ekas-tests.xml |
| Clean installed environment, no PYTHONPATH | 132 non-browser passed; one test-client deprecation warning | validation/clean-environment-tests.xml; requirements-lock.txt |
| Simulation tests | 16 | test_simulation.py |
| Campaign/export tests and acceptance gate | 6 + 1 | test_campaign_validation.py, test_campaign_gate.py |
| Full-duration physical assertions | 17 passed | validation/campaign.json |
| Contract CI layer | 3 passed within the full suite | API OpenAPI operation test + 2 foundation tests |
| Optional source schema tests | 2 passed | test_sources.py |
| API tests | 15 passed | test_api.py |
| Persistence tests | 3 passed | test_storage.py |
| Blind RCA tests | 16 passed | test_blind_rca.py |
| OS/pinned-runtime negative tests | 2 passed | test_security.py |
| Temporal scoring tests | 20 passed | test_temporal_benchmark.py |
| Verification/financial tests | 43 passed | test_verification.py |
| Browser tests | 3 passed; 12 engineering-flow actions | browser-tests.xml; browser-flow.json; screenshots |
| Observability | 5 tests passed | test_observability.py + test_discrimination_model.py |

Categories overlap where explicitly noted; do not add the rows to infer a new test total. The complete-suite XML is authoritative. Three original starter tests now exercise canonical temporal scoring and catalog-based coverage; no truth-ID scorer or parallel heuristic remains.

## Full-duration blind result

86,400 seconds, seed 7, two-hour normal baseline, each profile generated twice. Repeat digests match. Shared observations and private truth match across profiles. The report records hashes of the actual unchanged simulation, acquisition, diagnosis, discrimination, evaluator and export sources used.

| Result | Sparse | Enhanced |
|---|---:|---:|
| Detected events | 16 | 16 |
| Correct physical cause | 0 | 12 |
| Correctly unresolved physical fault | 12 | 0 |
| Incorrect causes | 0 | 0 |
| False positives / missed | 0 / 0 | 0 / 0 |
| Evidence complete | 16 | 16 |
| Unsupported certainty | 0 | 0 |

Four events in each profile are benign or acquisition artifacts, not physical-fault points. Every enhanced mechanism manifests in measured data; eleven sparse primary mechanism observations are unavailable and remain explicitly qualified. All 16 recovery checks per profile pass. Aggregate metrics agree with independently computed per-class scores.

Primary evidence: [validation/CAMPAIGN.md](validation/CAMPAIGN.md), [campaign.json](validation/campaign.json). Final report SHA-256: `0ebe18ac104e6642eb2c060d1b234f52d9e577f272463292274940261fec6e34`. The campaign gate checks current qualification rather than treating successful file generation as acceptance. Earlier adverse results remain under validation/history/.

Historian exports retain 86,400 regular rows per profile, exact discrete changes/quality boundaries and compressed analog observations. File sizes, row counts and actual checksums are in the report; raw exports/private truth/frozen claims remain in ignored work/campaign/. The stuck-quality monitor derives its flag from at least 30 seconds of repeated public readings and advancing independent counts. It receives no event class or schedule.

## Real behavior and accessibility

Visible in-app browser testing exercised investigation, primary finding, evidence drawer, alternatives, formal ambiguity, sensor recommendations, submission freeze, score-gated truth reveal, synthetic action and measured verification. Automated Chromium exercised the same real API-backed flow and inspected console/network results: zero script errors and zero failed requests. Desktop and 390-pixel mobile layouts were inspected.

Accessibility result: language, main/h1 landmarks, editable/button accessible names, keyboard skip link and focus, native dialog behavior, desktop/mobile overflow checks passed. This is a bounded structural/keyboard audit, not complete WCAG certification. See validation/accessibility.json and browser screenshots.

## Verification and financial governance

The actual seeded drive-repair regression verifies a meaningful 39-to-60 SPM improvement under the same observed 60 SPM command, while reporting compatible scrap uncertainty. Trivial rate noise cannot verify a repair; significant quality regression blocks verification. Insufficient production/exposure, missing controls or unavailable outcomes remain INCONCLUSIVE. A no-output pre-repair window is not forced to success. Sustained requires its explicitly configured verified duration.

The financial API calculates opportunity using measured counts and baseline capacity plus explicit contribution/currency/source assumptions. It does not derive verified savings. Savings in the library require independently measured before/after costs, verification and provenance; no real savings are claimed.

## Review, CI and boundaries

Independent review initially found five Important defects. Their adverse record and corrective regressions are retained in validation/INDEPENDENT_REVIEW.md. Further scan/quality/UI/runtime-origin defects were reproduced and corrected. No known Critical or Important defect remains in the tested local prototype boundary.

CI has ten separate validation categories, with a full-duration campaign gate in simulation. Workflow definitions do not prove hosted-run success; live hosted status belongs to the PR checks. Local results above were actually executed. Dependencies were installed in a clean local environment; pip check found no broken requirements. The locked FastAPI/Starlette test-client path emits a deprecation warning; tests pass and production HTTP/browser traffic is unaffected.

Known limitations: idealized uncalibrated one-second mechanics; no high-frequency waveform or real plant integration; fixed inspection lag; finite engineering catalog and baseline feature rules; one declared full-duration reference seed rather than a statistically representative field-performance claim; conservative formal availability model retains planned-stop/dropout ambiguity even though runtime records can distinguish their observed kinds; local single-user broker without production authentication/tenant/TLS/backup controls; bounded objective/scope handling rather than a general natural-language query planner; no real verified savings or production readiness claim.

Both upstream commits remain pinned and unmodified. No EKAS_Demo_UI source, branch, build, runtime or working tree was accessed or changed by this task. Patrick's manual acceptance remains pending.
