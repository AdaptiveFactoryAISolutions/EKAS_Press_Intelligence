# Plain run report: software evidence

Date: October 29, 2026. Base: `fbf4743cd6ce99f9a44bc2b6d4d0392ec548ce91`.
Scope: the user-approved plain report, added to completed guided press runs.
This does not qualify the simulated equipment or its diagnostic accuracy.

## Delivered behavior

- Admin-only `GET /v2/jobs/{ident}/practice-report` reads immutable run settings and full original public observations.
- **Read my results** is the primary practice-run action. The report explains settings, dates, graphs, counts, findings, terms, sources, and next steps.
- Separate real-unit graphs show stored good observations. No added samples, resimulation, private truth access, or causal invention occurs.
- Streaming summaries cover all primary observations. Plots retain at most 960 selected stored points per signal.
- The part balance requires synchronized usable final readings for produced, packed, rejected, discharge, washer, and packing-queue counts.
- Rejected parts remain separate from parts still in the line. Missing, invalid and bad-quality readings do not become zero or an earlier final value.
- Print styling removes workspace navigation. **Print or save as PDF** uses the browser print function.
- Report language references the supplied ASD-STE100 Issue 9. Full vocabulary/terminology review remains explicitly open; no conformance certification is claimed.

## Local verification

| Check | Result | Evidence |
| --- | --- | --- |
| Core layer | 206 passed, zero skips; 176.890 seconds | `work/native-test-reports/core/f0a7ea05-d57e-4f90-886f-988d7824a61e` |
| Browser layer | 29 passed, zero skips; 115.327 seconds | `work/native-test-reports/browser/3a79e7b2-a7a5-44db-8694-bbbbe3d5e834` |
| Final focused report/API/browser regressions | 16 passed; 15.08 seconds | `work/practice-report-final.xml` |
| Installable packages | Both wheels built; distribution checks passed | `work/wheels-plain-report`, `work/plain-report-wheels.log` |
| Packaged source | Nine UI/backend files byte-match the final checkout | Local wheel inspection |
| Original repositories | Protected pins and trees verified unchanged | `bash scripts/verify_upstreams.sh` |
| Independent code review | Rejected-part finding fixed and rechecked; no remaining material findings | Review recorded in this session |

The focused checks cover complete primary versus earlier grid totals, bad/missing/noninteger/negative/null counters, mismatched observation times, absent check results, changed settings, labeled fault requests, source symlinks, bounded plots, subsecond time order, role boundaries, unsupported jobs, print layout and real HTTP/Chromium rendering.

The core/browser totals overlap the focused report tests; do not add the totals together.
The last changes to requested-case labels and graph tick labels received the final focused rerun.

## Actual user's run and preservation

The new endpoint and actual Chrome page opened run `4063c830-4290-4bcf-8bb4-494d14d63fdb`.
Its last primary readings at `2024-03-01T00:59:59Z` show 467 produced, 459 packed, six in the washer, two waiting for packing, zero on discharge and zero rejected.
The eight-part difference reconciles. Native validation findings remain visible.

The owned wrapper service on port 18729 restarted only after confirming no active jobs and making a SQLite backup.
Before/after hashes matched for all rows in jobs, datasets, line drafts, line runs, submissions, and judgments.
Preserved counts: 19 jobs, 16 datasets, nine drafts, nine line-run bindings, zero submissions and zero judgments.
The frozen R7 model/runtime and both vendor pins remain unchanged.
No production activation, merge, paid call, physical-controller write, or source resimulation occurred.

## Adverse attempts retained

- The initial sandbox report test printed ten failures, then stalled during the API fixture. The owned test process was stopped and rerun with local socket access. It did not touch user state.
- A test fixture initially tried to put a fractional value in an integer pandas column. The fixture now uses float storage so it can exercise noninteger-counter rejection; the backend guard was not weakened.
- The one-process repository `pytest` command stopped during collection in `test_native_evaluation_contract.py`: the import guard rejected mixed native source trees. Evidence: `work/plain-report-full-suite.log` and XML. The guard remains intact. The repository's isolated core/browser layers passed instead; this is not an all-in-one-suite pass.
- Independent review reproduced incorrect rejection accounting. Both nonzero-rejection and missing-rejection regressions failed before the correction. Evidence: `work/practice-report-rejection-red.log`.
- A subsecond ordering regression failed before native timestamp ordering replaced ISO-string comparison. Evidence: `work/practice-report-time-red.log`.
- A readability regression rejected fractional-minute graph labels before rounded whole-period tick positions were added. Evidence: `work/practice-report-ticks-red.log`.

Remote CI/CodeQL remains separately blocked by the previously confirmed GitHub account billing lock. No remote clearance is claimed.
