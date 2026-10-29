# Plain run report implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the user-approved plain report available from each completed guided press run.

**Architecture:** An admin-only read endpoint summarizes the immutable run configuration and original public readings. A separate UI module renders those facts with fixed explanatory wording and individual graphs. The existing technical explorer remains available.

**Tech stack:** FastAPI, streaming PyArrow, vanilla JavaScript/SVG, pytest and Chromium.

**Spec:** User-approved `outputs/Press-Run-Report.md`, with the supplied ASD-STE100 Issue 9 as the language reference.

## Global constraints

- No simulation changes, private truth access, resimulation, paid calls, or merge.
- Report scope is completed guided stamping-line practice runs; admin access only prevents blind-role disclosure of setup/fault instructions.
- Use whole-file primary readings for summaries. Never use the truncated explorer query or reconstructed grid for final totals.
- Preserve missing/invalid/poor-quality data as unavailable; zero is a measurement, not a missing-value default.
- Keep validation findings, numerical uncertainty, source hashes, report version, and language-review limits visible.
- Use separate graph units; show stored points, no added values. Summaries cover all primary records; plotted point selection is explicitly disclosed.
- Follow the STE sentence/terminology rules; do not falsely claim full vocabulary conformance.

## Review focus

1. Missing or bad final counters must not yield invented balances or totals.
2. Fault cases and changed settings must not receive the healthy default narrative.
3. Unknown/missing validation findings must not become a pass.
4. Paths, HTML, script injection, blind-role access and failed/running jobs must stay bounded.
5. Large datasets require bounded memory and explicit plot reduction without truncated summaries.

## Task 1: Evidence report endpoint

**Files:** create `native/practice_report.py`, `tests/test_practice_report.py`; modify `native/api.py`.

**Interface:** `build_report(job, binding, public_path) -> dict`; GET `/v2/jobs/{ident}/practice-report`, admin-only, completed guided generation only. Returns stable structured sections, per-tag complete statistics/selected points, findings, provenance and scope; no private files.

- [x] Write failing tests for actual primary Parquet values, grid/final-time mismatch, quality/missing counters, noninteger counters, altered target and fault settings, validation unknown/failure, all-role boundary, pending/failed/unguided runs, safe path resolution and bounded plots.
- [x] Run tests and confirm expected missing-endpoint/module failures.
- [x] Implement streaming statistics and fixed evidence-qualified explanations; validate complete final counter observations before reconciliation.
- [x] Run report and existing line API suites; record results.

## Task 2: Beginner UI and printable report

**Files:** create `native_ui/report.js`, `native_ui/report.css`; modify `native_ui/index.html`, `native_ui/app.js`, distribution verifier; create `tests/test_practice_report_browser.py`.

**Interface:** `window.PracticeReport.open(jobId)` uses existing authenticated API and view bridge. Primary job action is “Read my results”; secondary action opens technical measurements. Print uses browser print and a print stylesheet.

- [x] Write/run failing Chromium checks for primary action, report contents, safe escaping, individual graph units, accessible descriptions, missing-data warnings, navigation, error recovery and printable layout.
- [x] Implement report section, request sequence protection, fixed readable templates, real-unit SVG graphs, expandable evidence and print support.
- [x] Verify real service/Chromium behavior and preserve screenshots.

## Task 3: Language, documentation and release checks

**Files:** add report language/term review in `docs/`; update wiki testing page, OpenAPI and execution ledger.

- [x] Record report technical nouns, fixed copy review and partial-versus-full STE review status. Check fixed sentence lengths without claiming an automatic conformance check.
- [x] Run related API/browser suites and the repository test command; preserve any environmental or unrelated failures separately.
- [x] Build server/client wheels and verify new asset inclusion. Review diff with a fresh reviewer; address material findings with regressions.
- [x] Activate the changed wrapper on the owned local service only after checking no worker is active; preserve state and native model pins.
- [x] Publish on the existing draft branch/PR. Remote checks remain separately subject to the known GitHub billing block.

## Execution record

Ruling: Implement inline after the user's “proceed”; no additional plan approval is needed. This continues the approved report format.

Pre-flight: endpoint JSON is the UI contract; source public observations plus immutable job config are the report authority. This endpoint is separate from evaluator-only native report/scoring operations.
