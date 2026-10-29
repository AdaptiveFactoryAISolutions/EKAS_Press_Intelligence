# Guided generic 1,500-ton stamping line

Date: 29 October 2026. Status: user-approved design implemented as unqualified practice. Exact-head publication checks are recorded in draft PR2; production qualification remains separate.

Independent builder check completed: no consequential unanswered planning questions or misleading current-versus-planned claims found. Generic engineering values and implementation choices are explicitly delegated; target-specific external EKAS wiring still needs identified source/contract. The user approved this full design and implementation on 29 October 2026.

## Purpose and user outcome

An inexperienced user must be able to configure and test a representative complete stamping line without writing JSON, reading source code or knowing historian terminology. A ready-made generic configuration must support the full line, not just a collection of independently generated sensor values. The same public evidence must be usable by the built-in workspace and an EKAS backend/demo adapter. A plain-language repository wiki must mirror the screens.

User-specified line: stock loaded on a reel, through a slack loop pit for long progression, multi-roll straightener, feeder, press window and ten-station die. Strip stays continuous through the stations. Offal leaves through shaker chutes or motorized conveyors. Finished parts leave the last station onto a conveyor, pass through a hot-water spray washer, then are packed manually into customer containers. Press rating is 1,500 tons; maximum speed is 600 strokes/hour, equal to 10 SPM. Include in-die lubrication, individual station sensing, tonnage monitoring, SPM and drive current.

Treat this as a continuous-strip multi-station arrangement, whatever terminology an operator uses for the press. Do not add separate blank handling or transfer fingers without a separately declared variant.

## Existing system and preservation

Extend the actual protected HistorianSim pipeline through authored runtime overlays/patches, preserving both vendor pins and original datasets. Keep the earlier prototype and current reference service intact. Do not edit ignored generated runtime source as the source of truth. The existing press is a different, incomplete design basis (60-SPM single-cell assumptions); changing a name or speed field does not implement this line.

Retain native jobs, public/private evidence separation, independent evaluation, source manifests, registration checks, capacity limits and adverse results. Earlier gates/results remain historical evidence, not qualification of this source epoch. No physical press commands, live PLC writes, production activation or merge are part of this design.

## Proposed engineering assumptions

These are builder choices, not customer-provided specifications:

- Initial force unit: metric tonnes-force, explicitly displayed; 1,500 tf ≈14.71 MN. A selectable short-ton-force option must convert actual force consistently, never just change a label.
- Nominal training speed 8 SPM, hard preset maximum 10 SPM. Speed is a user-facing SPM quantity, with strokes/hour shown alongside it. No inherited 45–75-SPM scenarios may enter this preset.
- One finished part per production stroke after ten-station die fill. Station 1 receives new strip each advance; downstream station occupancy and output have actual cycle delays. Multi-out tooling is an explicit positive-integer parameter.
- Generic mechanical press with flywheel/drive and declared averaged cycle-energy dynamics. It is not an exact rigid-crank, emergency-stop or machine-safety qualification model. Actual motor current follows a declared drive/efficiency/power model rather than being equated directly to force.
- At most one active run per current worker policy. Practice runs use explicit short durations; diagnostic/qualification runs use independently approved schedules.

Before implementing the preset, the builder must select and document a coherent representative strip material, width, thickness, progression, coil size, reel/loop/straightener/feeder capacities, die load/travel curves, drive power/energy, line speed, washer operating envelope, buffers, staffing and container size. Numerical choices must be internally checked and recorded as generic assumptions, not manufacturer calibration. This selection is delegated to the builder; it does not require customer hardware specifications for a generic model. No blank required fields may remain in the delivered preset. Load feasibility must consider force versus stroke position, energy per stroke and thermal/drive recovery, not rated tonnage alone.

## Connected model requirements

| Subsystem | Minimum modeled behavior | Public evidence |
|---|---|---|
| Reel | Shrinking coil, payout response, available stock, drive demand | Diameter/remaining stock, payout speed, current, ready/fault |
| Loop pit | Finite slack inventory, upstream/downstream material balance | Loop amount/level, limits, supply demand and interlocks |
| Straightener | Declared roller recipe, traction/load and speed response | Settings, speed, motor current/load, material presence, condition indicators |
| Feeder | Finite movement in permitted window, actual shaft versus strip movement, slip and readiness | Command/actual travel, feed complete, following error, current, strip progression |
| Press and die | Ten stations with occupancy, load/travel relationships, die fill, valid stroke completion | Position/phase, speed, drive current/energy, corner tonnage and total measured load |
| Station sensing | Declared directly measured versus derived signals, sensor quality and fault behavior | Presence/strip position, protection signals and declared station force channels/estimates |
| In-die lube | Reservoir, pump/header and zoned delivery; lubrication affects forming condition | Level, pressure, flow, temperature, delivery timing and branch confirmation |
| Offal removal | Scrap mass per operation, chute/conveyor capacity and accumulation | Jam/high accumulation, motion/current, relevant scrap counts/mass |
| Product discharge | Finite transit and accumulation; loss/reject paths explicit | Part detection, conveyor speed/current, queue counts and stops |
| Hot spray washer | Water inventory and heating, spray/pump/filter condition, residence time, loss/makeup | Temperature, level, pressure/flow, filter differential, heater/pump power/current, conveyor speed and cleaning indicators |
| Manual packing | Worker availability/rate variability, finite queues, containers and changeovers | Ready-to-pack, packed/reject counts, container identity/fill/completion, packing state |

A washer fault must not instantly change upstream forming physics; its effects propagate through queues/interlocks. Packing slower than press output must grow a finite queue, then produce a modeled block/stop. Offal mass must be distinct from product rejects. Rework, if unsupported, must not silently disappear into good product.

Separate true process state from instruments, local controllers and exported historian data. Sensor failures/dropouts must not change physical inventory or give analysts hidden true values. Expose measured product inspection/cleanliness only where a declared inspection device or manual inspection exists. Hidden synthetic defect/cleanliness truth stays private.

Capture event/cycle measurements sufficiently to represent a six-second minimum cycle and station timing. A coarse historian trend cannot prove detailed timing. Keep numerical integration, acquisition, event clock and trend export rates distinct and validated. Resolve the previous deterministic-encoder/colored-noise gate conflict by a declared physically defensible acquisition model and reviewed validation scope. Do not add arbitrary colored noise, waive a failed gate silently or reclassify signals to bypass it.

## Beginner configuration wizard

Use the existing web delivery/runtime where practical; do not rebuild the whole application solely to add a wizard. Add a dedicated beginner entry while keeping expert native operations separate. Use Microsoft Fluent 2 interaction, spacing, typography, focus, field and tooltip guidance. Prefer actual supported Fluent web components where compatible; pin and bundle dependencies locally rather than runtime CDN loading. Record exact package/component version and accessibility behavior during planning. If a component gap requires a custom implementation, declare it and test it; do not claim component certification.

One screen per step; no scrolling through all eight forms. Each shows Step X of 8, progress, a clear heading, one primary Next action, Back, Save and exit, current preset/version and Simulation only. The progress control supports returning to completed steps without losing data. No unexplained dropdowns, raw JSON, provider configuration or secrets in the beginner path.

1. **Choose your line:** standard preset and name; full equipment diagram; no accidental reference-tank selection.
2. **Capacity and speed:** explicit force unit, operating speed, fixed preset maximum 10 SPM/600 SPH, parts per stroke.
3. **Material and feed:** ready-filled material/geometry, coil/slack capacities, straightener and feeder recipe, timing. Units/helper text always visible.
4. **Die, lubrication and scrap:** ten station cards, sensing and load assumptions; zones; shaker/conveyor routing. Station details are expandable without losing wizard position.
5. **Wash and pack:** washer recipe/capacity, queues, manual staffing/rate, customer container capacity and changes.
6. **Choose a test:** healthy first test, then named bounded fault cases; duration and repeat number. Plain-language preset recommendations, no hidden shortening.
7. **Choose result destination:** built-in workspace by default; administrator-provisioned EKAS connection; test reachability, role and public evidence read. Connection failure has a specific correction, not a simulated success.
8. **Review and run:** complete resolved summary, assumptions, Edit links, server preflight and explicit Run test. Failed checks link back to exact fields/steps.

After submission, show progress in plain language, configuration version, job ID, cancellation state and a single View results action. Refresh/reconnect must attach to the existing job. Results must identify simulation, configuration, model/source version, units, quality, warnings, validation and practice/qualification scope. Never show a blanket green “qualified” because only configuration validation passed.

## Preventing mistakes

The server is authoritative. Browser validation improves feedback but cannot be bypassed by a direct API request. Reject unknown fields, empty required values, nonfinite numbers, fractional counts, impossible dimensions, negative capacity/rates and invalid routing. Enforce speed 0<SPM≤10 for production; stopped state is separate. Enforce ten stations for this preset. Convert units once at the boundary into declared canonical units. Validate die load/energy against the press envelope, feeder movement against the usable cycle window, progression against feed capability, physical buffers and the conservation relationships.

A downstream station being slower may be a valid deliberate bottleneck test, not an invalid configuration: show its predicted consequence, require an explicit scenario selection/acknowledgment and preserve it in the run record. Block contradictions, not all adverse operating conditions. Fault injection may exceed healthy limits only through a bounded declared fault specification; it cannot bypass base configuration validation.

Persist validated draft data on the backend using the existing access/role boundary, a schema version and revision. Browser storage may cache nonsecret navigation state but must not be the sole authoritative configuration. Do not store role/provider secrets in drafts. Save/restore by revision; reject stale updates with a readable conflict and recovery choice. Upstream changes invalidate dependent preflight, summaries and run confirmation. Run submission atomically binds an immutable full resolved configuration and model digest, with an idempotency key to prevent duplicate clicks. Old profiles are never silently upgraded; incompatible profiles require an explicit migration/review.

Preset and resource failures are recoverable: Retry check, return to the affected step, or explicitly save and exit. Save-and-exit/reload acceptance includes every step. Validation messages say what is wrong, expected range/unit and how to fix it. Status must use words/icons in addition to color.

## Fluent help and accessibility

Use visible helper text for essential units/ranges/constraints. Add concise supplemental tooltips to unfamiliar labels and accessible info controls. Show on hover/focus, dismiss with Escape/blur, connect with aria-describedby, avoid obscuring the target and support a touch-accessible explanation. Essential errors must never exist only in a tooltip or only on a disabled button. Longer help uses an accessible popover/link to the matching wiki section. Keyboard navigation and screen-reader names must work for all steps; validation focuses the first invalid field while preserving the full error summary.

Example: **Press speed (strokes/minute)**, helper “Maximum 10 strokes/minute (600/hour)”, tooltip “One stroke is one complete press cycle. Ten die stations do not mean ten finished parts each cycle.” Error: “Enter a speed above 0 and no higher than 10 strokes/minute.”

Sources: [Fluent 2 Tooltip](https://fluent2.microsoft.design/components/web/react/core/tooltip/usage), [Fluent 2 Field](https://fluent2.microsoft.design/components/web/react/core/field/usage). Follow guidance; do not copy whole source pages into help.

## Backend and EKAS integration

Add typed versioned preset/configuration/draft/preflight endpoints, not arbitrary config blobs. The precise route names and frontend module organization are delegated to the builder; publish the actual contract and SDK methods before integration acceptance. Existing `/v2` public dataset/job routes remain compatible. Add tests at the server boundary for direct invalid requests and stale revisions.

Use the built-in workspace for the immediate fully working end-to-end delivery. Deliver a documented backend adapter contract/example for EKAS using the existing HTTP-only SDK and public evidence. Tokens remain server-side; the browser talks through its trusted backend. Preserve tags, units, timestamps, quality, unavailable data, bounded-query flags and provenance. Do not implement frontend causal claims or let an analyst access private engineering truth/key artifacts.

Targeted external EKAS UI/backend wiring requires an identified editable source and actual response contract. Neither has been provided for this scope; do not search/edit other sessions' repositories or compiled bundles. This is the only external integration dependency: deliver/test the built-in path and portable adapter first, then bind the identified EKAS target when supplied. Missing target access must be reported specifically, not used to call the entire task complete.

No new paid provider run is required for wizard/configuration acceptance. Full independent diagnostic qualification remains a separate authorized provider/data/budget workflow.

## Tests and acceptance

Use failing tests first for risky model, validation, persistence and job-binding behavior. Preserve numerical/source evidence and full native checks appropriate to this new model. At minimum:

- A new user completes all eight screens with the standard preset, without terminal commands/JSON after administrator installation; summary shows every physical assumption and connected subsystem.
- Each step saves/restores after refresh; Back does not lose data; stale simultaneous edits are rejected; upstream edits force revalidation; a double click makes one job.
- Keyboard-only path, help open/close, touch-help behavior, readable contrast/focus and accessible error announcements; screenshot/manual beginner walkthrough with actual field errors.
- API rejects >10 SPM, 600 treated as SPM, wrong station count, invalid force-unit conversion, unknown fields, impossible geometry, oversubscribed feed timing and invalid capacities. UI and API error mappings agree.
- Healthy cycle-resolved flow through ten stations into washer/packing; die fill/output/warm-up, steady state, stoppage/resume and coil/container changes conserve stock, parts and scrap.
- Mass/energy/integer ledgers use declared thresholds at least as strict as existing 1e-6 material relative error, 0.001 energy relative error and exact integer accounting where applicable. Add convergence checks before endorsing integration/acquisition intervals. Per-subsystem ledger boundaries and startup tolerances must be documented.
- Force/time, current/power and cycle energy stay mechanically consistent with the declared model; no unsupported waveform/real-machine accuracy claim.
- Independently exercise feed slip, loop starvation, lubrication restriction, station sensor failure, scrap blockage, washer cold/low-flow and packing slowdown; verify causal order and public/private separation, not just job completion.
- Backend adapter reads the same public evidence as the explorer; test unauthorized/unavailable/truncated/bad-quality cases and no fictional fallback.
- All relevant original and native software checks pass. Native validation failures remain visible and block qualified registration. Revise the old 45/60/75-SPM matrix and six-run plan explicitly for this line before executing press qualification; do not quietly reuse irrelevant evidence or silently reduce required coverage.

## Deliverables and order

1. Repository wiki plus this reviewed design, clearly marking planned versus current behavior.
2. Implementation plan with generic numerical design basis, source epoch and dependency versions.
3. Fully configured connected line model and backend configuration/preset validation.
4. Eight-step Fluent-guided wizard, saved profiles, progress/results and accessible help.
5. Built-in end-to-end training cases; EKAS adapter and target-specific wiring when source/contract is available.
6. Updated wiki with exact actual screens, first-use walkthrough and verified results. Qualification report and remaining external dependencies stated separately.

The design does not promise that all human confusion is impossible. Acceptance is a tested beginner path plus explicit prevention of known invalid configurations, with recoverable errors and no hidden assumptions or silent data-source substitution.
