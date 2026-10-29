# EKAS native historian platform: design for approval

Status: proposed, not implemented or qualified. Supersedes the earlier prototype as the target architecture; does not rewrite its historical results.

## Intent and authority

Patrick requested the comprehensive functionality of ScottDuncanAI/HistorianSim and ScottDuncanAI/HistorianRCA, downloaded and built according to their instructions, usable by EKAS without reduced substitutes. The complete native workflows are the baseline. The previous custom simulator and fixed-rule diagnosis are not accepted as replacements.

Downloaded sources, full history and current remote main were verified:

- HistorianSim: 14e616c382a9db8026cbb4ab86bdd803d56ca72e.
- HistorianRCA: 8d12a821395ce5f72e464dc78cc2c10d05cbb9ed.

The original checkout and service remain untouched. Work is isolated on full-stack-foundation. No EKAS_Demo_UI changes or source access are authorized. Integration is through a versioned module API and typed client.

## Source instructions and approval

HistorianSim/CLAUDE.md requires its /simulate workflow, parameter-level physical faults, controlled-transmitter feedback, named random streams, process descriptions without answers, and staged plant gates. Its .claude/skills/simulate/SKILL.md Step 2 says to write DESIGN.md and wait for approval before new plant implementation. The accompanying press DESIGN.md is part of this approval package.

HistorianRCA is a published dataset and challenge, not an executable diagnosis engine. Its public checkout has no answer key. Preserve and expose its actual data and workflow; never fabricate a local official score or guess a private answer key. Its instructions prohibit public answer disclosure. No contact with its author, public submission, or solution publication is authorized.

## Full native capability parity

Each row is a required deliverable and an independently recorded acceptance result. A preserved source tree or a route stub does not satisfy a row.

| Native capability | Implementation boundary | Required demonstration |
|---|---|---|
| Plant/scenario/profile/recipe discovery; describe | Actual upstream registry and scenario functions | Both reference plants and every shipped scenario/options visible; compare with native CLI |
| Generation, overrides and fault-free twin | Actual build_scenario and pipeline.generate | Same config/seed produces identical native and service artifacts; options not silently ignored |
| Full pipeline | Native controls, disturbances, fault layers, measurement, pathology, ballast, historian, truth | Execution provenance records actual module origins and source hashes |
| Standard and campaign profiles | Preserve shipped 90-day/365-day settings and explicit overrides | Full standard qualification for both references; separate complete campaign-profile execution; quick results labelled iteration only |
| Validation/regeneration | Native run_battery and written-folder audits | Actual per-check results, failures and warnings; no simplified replacement battery |
| Staged plant checks | Native stages 1 through 5 | Full evidence per stage, stop on failure, no renamed or relaxed gate |
| Describe process and conceptual PFD | Native process description and /simulate PFD instructions | Every loop and tag agrees; inspect rendered SVG/PNG; no hidden fault names in public materials |
| Native data artifacts | Native write_dataset, tags and layout | Original Parquet schemas, quality codes, UTC, irregular samples and regular grids retained |
| Dataset/challenge audit | Native layout/leakage and recipe audits | Traversal/symlink/metadata restrictions plus exact public challenge file allowlist |
| Challenge generation | Native make_challenge | Separate analyst directory without configuration, keys, labels, private descriptions or source catalog |
| Submission/scoring | Native submission parser and score_submission | Preserve one-to-one matching, six-hour rule, points, rejection and explicit cause adjudication; compare against CLI fixtures |
| Reports/answer-key summaries | Native report/summary functions | Evaluator-only results after frozen submission; raw key never enters analyst worker |
| Plotting | Native plot_dataset plus browser exploration | Same selected tags/time interval, primary/raw versus interpolated distinction, quality gaps visible |
| New-plant authoring | Native template, Plant/UnitModel/catalog contracts and /simulate workflow | Approved design, real model, all gates and blind challenge; not a catalog-only shell |
| Original HistorianRCA | Actual complete downloaded 90-day dataset, tag dictionary, process/PFD/task/template | Data queries match Parquet; free-text item/mechanism submission export; official scoring unavailable until an authorized key/organizer result exists |

Profiles are discovered rather than recreated with another hard-coded registry. The source is authoritative where prose and actual defaults differ. Standard rca-benchmark has nine unique non-overlapping physical faults, fourteen baseline days, two benign moves and two-day clean gaps. Do not replace it with the old one-day/sixteen-event demonstration.

## System boundaries

Keep Python, the actual native engine and the existing API framework. Use a durable relational job/resource store and a real worker process, a same-origin browser application, and a typed EKAS client. These are engineering choices, not claims that Patrick specified a framework.

1. Source/provenance service verifies full checkouts, licenses, original pins and any reviewed patch manifest. Baseline sources remain immutable.
2. Generation worker consumes a validated native config, calls native code, stores original private artifacts, records hashes, configuration, seed, module origins and every check. It cannot silently substitute the legacy engine.
3. Public dataset service exposes only allowlisted public files, bounded queries and immutable dataset manifests with public provenance. Streaming/export supports full records; a UI sampling limit never silently changes analytical results.
4. Analyst process receives only a native challenge directory and explicit evidence tools. No evaluator database, source tree, scheduler, catalog, labels, cloud credentials or organizer keys. Network/process/filesystem access is denied unless the selected provider explicitly requires a documented broker.
5. Evaluator service owns private generated keys and manual cause adjudication. Analyst claims are frozen before access to scoring. Published HistorianRCA remains externally scored; no generated twin is represented as its original key.
6. UI provides source/native-workflow status, plant/scenario configuration, durable jobs, raw/grid data explorer, tag metadata, process/PFD viewer, free-form investigation workspace, evidence/alternative ledger, submissions, role-separated adjudication and results, native validation detail and artifact downloads. It must show failures and unknowns, not only polished results.
7. EKAS v2 API/client provides job lifecycle, cancellation, dataset registration, capabilities, evidence querying, cases, frozen submissions, evaluations and artifact references. Contract tests execute a separate client process. No target EKAS checkout is modified.

## Durable execution and access

Jobs have queued/running/cancel-requested/cancelled/succeeded/failed/interrupted states, persisted leases/heartbeats, bounded logs, progress phases and explicit failure codes. Restart must not claim that a lost worker completed. Idempotency prevents duplicate launches. Cancellation terminates only the owned process group; partial outputs remain non-qualified. Default one worker protects host resources. Capacity limits are explicit, configurable and fail visibly; no shortened simulation is substituted.

The upstream full-generation path may retain large arrays and is not naturally chunkable. Do not invent a streaming physics engine for the wrapper. Bound concurrent jobs, preflight the requested footprint and disclose an actual capacity failure. Full supported native profiles remain available.

Local development binds loopback. Network deployment requires authentication and separate analyst/evaluator/admin permissions; keys remain server-side, never JavaScript or logs. Mutations require authorization, same-origin/CSRF protection where cookies are used, safe filenames, bounded upload parsing, auditing and immutable submission evidence. Backup/restore and worker restart are tested. Do not label a deployment production-qualified until these checks actually pass.

## Diagnosis and native blind workflow

The standard accepts free-text failed item and mechanism, with evidence and explicit alternatives. A fixed list of press rules cannot stand in for the native investigation. Support human-led analysis and a configured agent worker. No pretend provider: missing credentials or an unavailable runtime produces a typed unavailable state.

For release qualification, follow /simulate Step 6: a fresh analyst receives only the challenge, writes the original CSV format and notes, then an independent evaluator adjudicates item plus mechanism against the private generated key. Preserve mistakes and explain whether evidence was missing or the analyst missed it. Do not require a perfect agent score as a reason to simplify the data. Passing isolation tests is necessary but does not establish general diagnostic accuracy.

Operational choice for mandatory blind runs: the installed authenticated Claude Code runtime (verified version 2.1.289, authentication status true without exposing identity or credentials) follows the upstream agent workflow. A fresh analyst has no inherited conversation, answer key, source catalog or repository mounts. Expose only bounded public evidence queries and challenge-file reads, not arbitrary host shell/file tools. Provider authentication stays in the broker/client boundary, inaccessible to evidence tools; explicitly test that boundary before running a blind qualification. An unavailable broker or isolation failure blocks the blind gate, not a fallback to fixed rules. A separate fresh evaluator receives frozen claims, public evidence and the generated private key for explicit item/mechanism adjudication. Preserve its justifications and unresolved judgments; Patrick remains the final human acceptance authority. Do not let the analyst self-mark cause_correct.

Published HistorianRCA findings remain private local artifacts and are not committed to the public repository. An authorized external scoring result can be attached later; until then official detection/cause accuracy is unknown.

## Press extension and exact upstream use

The press must be authored through the native plant contracts and full native layers described in the companion DESIGN.md. Physical generation and controlled-sensor effects stay inside evolution; instrument corruption remains downstream except feedback sensors. Keep original reference models working unchanged.

The upstream is a continuous-process engine. Exact material/stroke events require a generic, documented hybrid extension; falsely passing a pure equilibrium check over ever-increasing counters is not acceptable. First prove what the existing contracts can express. If a shared-engine change is necessary, maintain a separate reproducible patch against the immutable source, document its generic contract and add regression tests preserving every original trajectory. Execute the full native pipeline on that explicitly identified patched build. Never describe patched runtime as unmodified upstream, and never quietly replace pipeline.generate with the earlier custom simulator.

Native steady-state/setpoint gates apply to the same equilibrium envelope model used for generation, with the precise PV mapping and generic native-cycle contract in press-line/DESIGN.md. Additional periodic-energy, exact event, material and timing gates apply to its hybrid extension. Do not remove or relax any applicable native check. A claimed full press qualification requires both sets and the full recipe, not just adapter imports. That document fixes the 513-case single-cause matrix, six full press datasets, holdouts, masking and conservation/convergence criteria before tuning.

## Acceptance and integration

- Original full suites pass without omitted tests or fabricated XML. New tests exercise real native generation/exports/audits and worker API paths.
- Native-versus-service parity for artifacts, checks, scoring and options is measured from the same config/seed; differences are failures, not presentation tolerances.
- Both reference processes complete full standard datasets and reviews. The full campaign profile is actually exercised and reported independently of quick tests.
- Original HistorianRCA data are queried and explored without synthetic substitution. Official answer-key absence remains explicit.
- The new press passes design, physical/cycle, control, single-cause, discrimination, quick, full recipe, independent blind and multi-condition qualification. Training/reference cases and held-out seeds/operating points/severities are separated before tuning. Preserve all adverse runs.
- Real browser acceptance covers configuration, job restart/cancel/failure, raw data, quality gaps, PFD, evidence, free-text submission, protected evaluator workflow and full artifact download. Include keyboard/mobile/access checks and actual console/network inspection.
- EKAS client integration runs outside the server process against versioned contracts. Hardware connectivity is separately qualified; no synthetic dataset is represented as a real SmartPAC installation.
- Source capability inventory has no unexplained missing or replaced row. Report native results, wrappers, new engineering and unavailable external authority separately.
- Patrick performs manual acceptance; no automatic merge, public solution disclosure or target EKAS modification.

## Build order

After approval: native setup/baselines; capability inventory and parity tests; durable worker and original data workspace; original native generation/validation/challenge/scoring API; full browser and EKAS client; approved press model and generic extension if required; staged physics gates; complete reference/full press datasets; independent blind/held-out validation; security/restart/deployment tests; exact evidence and review. The plan must track every parity row and failed gate to closure.

The project is not complete when a dashboard renders, when upstream tests alone pass, or when newly authored rules recognize their own scenarios.
