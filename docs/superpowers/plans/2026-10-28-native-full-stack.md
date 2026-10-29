# Native historian full-stack implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. User approved the full design and native workflow; execute continuously without routine approval pauses.

**Goal:** Deliver the comprehensive native HistorianSim/HistorianRCA workflows, a genuine native press extension, durable application and executable EKAS integration, qualified against the approved engineering gates.

**Architecture:** Preserve immutable upstream submodules. Use actual upstream functions in a job worker and public Parquet data service, a separate analyst/evaluator boundary, and a same-origin native workspace. Implement the press through native plant contracts plus an explicitly versioned generic hybrid patch where necessary; original reference behavior must remain unchanged.

**Tech Stack:** Python 3.12, actual pinned HistorianSim, pandas/PyArrow, FastAPI/Pydantic, SQLite durable orchestration, separate worker processes, JavaScript browser consumer, Chromium qualification, Claude Code broker for independent blind workflow.

**Spec:** docs/superpowers/specs/2026-10-28-upstream-full-stack-design.md and press-line/DESIGN.md, approved by Patrick in chat.

## Global constraints

- Native pins: HistorianSim 14e616c382a9db8026cbb4ab86bdd803d56ca72e; HistorianRCA 8d12a821395ce5f72e464dc78cc2c10d05cbb9ed.
- Full source/history/licenses remain preserved. No EKAS_Demo_UI access or modifications. No automatic merge or solution publication.
- Actual generation, measurement, native export, audit, recipe, challenge and scoring functions; no fallback to the previous custom simulator/rules.
- Original fixed benchmark's private answer key is absent; official scoring is unavailable locally until authorized external evidence exists.
- All physics faults inside evolution; controlled-sensor faults affect feedback; named colored-noise streams; blind analyst never sees private truth/catalog/source/configuration.
- Full-duration standard/campaign execution and native checks, press matrix/holdouts/tolerances exactly as approved. Quick is iteration only.
- Tests run red before risky behavior is implemented. Preserve adverse evidence. Commit coordinated changes without including another worker's unfinished edits.

## Review focus

- Restart, worker crash or cancellation must never turn partial native output into a qualified dataset; Task 2 tests interrupted leases and exact owned-process cancellation.
- Traversal, symlink, oversized query, interpolation and bad-quality inputs must not expose private files or manufacture evidence; Task 1/3 tests real Parquet and safe file access.
- Analyst-written cause_correct, key access or mutable submission must not create credit; Task 3 tests role separation and immutability against native scoring.
- Hybrid phase/counter states must not fake native equilibrium or bypass native pipeline; Task 4 tests envelope mapping, event conservation and original-reference parity.
- Missing provider credentials or model errors must be typed failures, not canned diagnosis; Task 6 tests unavailable and real isolated blind runs separately.

## Ownership and interfaces

- Native engine/data implementer owns native/engine.py, native/data.py, native/catalog.py and corresponding test_native_engine/data.py. Functions defined below.
- Press implementer owns extensions/stamping_press/, patches/, scripts/prepare_native_runtime.py, tests/test_press_native.py and press engineering evidence. Does not edit native worker/API/UI.
- Browser implementer owns native_ui/ and tests/test_native_browser.py. No diagnosis, scoring or simulation logic in JavaScript.
- Root owns native/jobs.py, native/worker.py, native/api.py, native/client.py, native/security.py, native/analysis.py, tests for these, contracts/deployment/docs/CI, and integration/reviews.

### Task 1: Actual native engine and original data access

Interfaces: native.catalog.capabilities(repo_root: Path)->dict; native.engine.execute(operation: str, parameters: dict, target: Path, repo_root: Path, progress=None)->dict. Supported native operations generate, validate, plant_check, describe_process, make_challenge, plot, report, summarise. Trusted target contains original private output and separate public challenge files. Return JSON-safe result including public dataset metadata and validation, never inline private answer keys in general generation results. native.data.dataset_info(path: Path)->dict; query_samples(path: Path,tags:list[str],source='grid',start=None,end=None,max_points=2000)->dict; public_files(path: Path)->list[dict]; resolve_public_file(path:Path,name:str)->Path. Original HistorianRCA file naming supported directly. query rows contain UTC timestamp, tag/value/quality for raw and timestamp/tag columns for grid; return source, rows, truncation/aggregation disclosure and no fabricated gaps.

- [ ] Write and run red parity/data/security tests with real native config and real Parquet.
- [ ] Implement exact native dispatch/config validation, provenance, original benchmark metadata and file/query allowlists.
- [ ] Verify native CLI parity, invalid/ignored-option rejection, primary versus grid, quality and path escape behavior.
- [ ] Review implementation and commit owned files only.

### Task 2: Durable jobs and native worker

Files native/jobs.py, worker.py, tests/test_native_jobs.py. JobStore(path:Path) methods create(operation,parameters,idempotency_key=None), get(id), list(), claim(worker_id), heartbeat(id,phase), finish(id,result), fail(id,code,message), request_cancel(id), recover(). JSON-safe job object: id,operation,parameters,state,phase,created_at,updated_at,result,error. Native worker executes Task 1 in an owned subprocess and records original private target, public dataset registration and hashes. Dataset IDs are UUIDs plus fixed historianrca.

- [ ] Red tests for concurrent claims, idempotency, malformed operations, interruption/restart, cancellation and failed-output exclusion.
- [ ] Implement transactions, immutable terminal states, bounded logs, heartbeats and worker ownership.
- [ ] Run actual generate/validate jobs, cancel a real owned job, restart broker and verify dataset persistence.
- [ ] Review and commit.

### Task 3: Protected API, native scoring and EKAS client

Files native/api.py, security.py, client.py, tests/test_native_api/client/security.py. Factory create_native_app(state_dir=None,start_worker=True,tokens=None,local_only=True). Local service initially port18728; old18727 untouched. Configured tokens map to analyst/evaluator/admin; non-loopback deployment requires configured tokens. Origin/host checks protect local operations. Pydantic requests forbid extra fields.

UI contract: GET /v2/capabilities; GET /v2/datasets; GET /v2/datasets/{id}; GET /v2/datasets/{id}/tags; GET /v2/datasets/{id}/samples?tags=A,B&source=raw|grid&start=ISO&end=ISO&max_points=2000; GET /v2/datasets/{id}/files and /files/{filename}; POST /v2/jobs {operation,parameters,idempotency_key?}; GET /v2/jobs and /v2/jobs/{id}; POST /v2/jobs/{id}/cancel; POST /v2/datasets/{id}/submissions {csv}; GET /v2/datasets/{id}/submission; POST /v2/datasets/{id}/adjudicate {judgments:[{row,correct,reason}]}; GET /v2/datasets/{id}/score. Jobs accept all Task1 operations. GET /v2/health. API error detail {code,message}. Additional evidence/case/agent routes documented when implemented. Public job results and scores redact private paths and true-cause text. Full original file downloads remain streaming.

- [ ] Red tests exercising native dispatch, original reference registration, strict requests, hostile filenames/Origin/roles, immutable CSV and analyst cause_correct rejection.
- [ ] Implement native six-hour scoring via upstream score_submission/load_scoring_key; evaluator judgment separate and audited. Fixed benchmark returns EXTERNAL_SCORING_REQUIRED.
- [ ] Implement typed separate-process EKAS client and live HTTP contract tests, including cancellation/failure.
- [ ] Export executable OpenAPI, deployment commands and protected configuration; verify backup/restore.
- [ ] Review and commit.

### Task 4: Approved native press extension

Files extensions/stamping_press/*, patches/*, scripts/prepare_native_runtime.py, tests/test_press_native.py. prepare runtime creates reproducible full source build under ignored work/, preserving vendor. Model/tag/loop/fault/description modules meet native contracts. Generic CycleEventSource extension evolves faulted/twin inside native core and native pipeline, never replacing pipeline.generate. Original native references must remain numerically identical. Report exact patched origins.

- [ ] Write red tests for native registration, equilibrium/step semantics, physical feedback, parameter-only faults and event/material/energy invariants.
- [ ] Implement six-state envelope and cycle model, generic hook only if necessary, 19 symptom-first causes, native scenarios and native safe public event artifacts.
- [ ] Pass stages1/2, then all single causes and discrimination references, then quick battery; repair exact failures in order.
- [ ] Render and inspect conceptual PFD with actual tags/loops, following bundled PFD skill.
- [ ] Execute the approved 513 single-cause matrix and six full native 90-day press datasets with matching sparse/enhanced physics and fixed holdouts; preserve results and every adverse gate.
- [ ] Review generic patch and model before native runtime becomes default; commit.

### Task 5: Real browser workspace

Files native_ui/index.html, app.js, app.css, tests/test_native_browser.py. Consume Task3 endpoints, display all native choices/options, durable jobs/status/cancel, original benchmark and generated datasets, tag metadata, raw/grid trends with quality/gap/truncation disclosure, process/PFD, files, free-text CSV submissions, evaluator-only judgments and score status. Clear authentication entry when configured, no client causal/scoring logic and no fabricated placeholders.

- [ ] Red real-HTTP browser flow tests for original dataset, asynchronous jobs and errors, primary/grid switching, submission and evaluator boundary.
- [ ] Implement responsive accessible native workspace on a separate app mount. Keep existing UI as historical prototype.
- [ ] Exercise actual desktop/mobile keyboard/dialog/console/network behavior; preserve screenshots and adverse evidence.
- [ ] Review and commit.

### Task 6: Native reference qualification and independent blind analysis

Files native/analysis.py, scripts/qualify_native.py, tests/test_native_analysis.py, validation/native/ (public summaries only). Claude Code is installed/authenticated; credential broker and evidence-only tools still require actual negative-access proof. Independent evaluator only after frozen claims. Do not commit original benchmark solution or private generated answers to public Git.

- [ ] Red tests for isolated challenge-only tools, absent credentials/provider errors and key/catalog/config/source/network denial.
- [ ] Implement native challenge agent and independent evaluator workflow, recording exact provider/version/inputs, evidence queries and frozen CSV hashes.
- [ ] Run all upstream tests and all five native gates for both references; full90-day standard datasets for both and full campaign-profile execution with actual native validation/audits/PFD/plots.
- [ ] Run the independent blind workflow for references and all six full press datasets, retaining analyst errors and independently classifying data versus agent failures.
- [ ] Match native versus service artifact/scoring results, verify every parity row, and qualify source/path/auth/cancellation/restart/backup/browser/client behavior.
- [ ] Whole-branch independent review; red regressions for defects, fixes and scoped re-review; actual CI on exact final head.
- [ ] Deliver exact counts/SHAs, known limitations and manual acceptance boundary. No readiness claim while any required row/gate is incomplete.
