# P-27 engineering qualification status

Status: development, not qualified for release. No benchmark data-solvability or blind-analysis result has been claimed.

The protected upstream source remains unchanged. The native runtime is reconstructed from commit `14e616c382a9db8026cbb4ab86bdd803d56ca72e` and explicit generic patches. Native `core.sim.simulate`, `pipeline.generate`, instruments, pathologies, historian, truth and validation remain the orchestrators. The optional phase hook runs separately inside the faulted and matched-twin native simulations. The public cycle file contains native measured status channels on the scan grid; detailed exact-boundary event and conservation ledgers remain private.

The approved six-state envelope is mean speed, achieved pitch, mean inventory, header pressure, oil temperature and die temperature. The controlled feeder transmitter holds the last completed encoder travel; independent strip progression is separate. There are separate feed-complete and stroke-complete boundaries, acceleration-limited feed trajectory, transport-delayed inspection, a material feed token, lubrication and buffer permissives, drive-energy removal and dissipative braking on a trip, and automatic restart when the declared permissives return. Automatic permissive recovery is an explicit development assumption requiring engineering review before qualification.

## Preserved verification

- Initial red native tests demonstrated missing model/event integration.
- First stage1 and stage2 passed unchanged upstream limits; those logs apply to the earlier hybrid implementation.
- A transient event convergence test failed at 1.066 ms against the fixed 1 ms limit. Phase quadrature and boundary location were corrected. The limit was not relaxed.
- A drive-trip test failed because motor energy remained applied at low lubrication. A physical permissive/brake was then added; the test passed.
- The current eight focused engineering tests passed before the runtime-verification test was added. They cover real native simulation, encoder feedback, parameter effects, integer event counts, feed-before-stroke, material and energy, convergence, stop/restart and unchanged original-reference arrays.
- Current hybrid revision stage1 passed unchanged native limits. Stage2 is being rerun before stage3.
- The initial stage3 sweep was interrupted after the independent convergence finding; no completed stage3 result exists from that run.

## Release work still required

Stage2 on final source, native stages3/4/5, complete measured discrimination correction, 513 cases, masking measurements, the six actual 90-day runs, sparse/full paired exports, all layout/recipe/leakage/solvability checks, the final rendered/inspected PFD, and six independent blind submissions/adjudications remain mandatory. No reduced-duration run can substitute for them.

The matrix remains exactly the approved19causes x3seeds x3rates x3severities=513cases. Full datasets remain `(7,60),(19,60),(42,60),(19,45),(42,75),(42,45)`, each90days. Seed7/rate60 is development; the held-out cases remain held out from detector/analyst tuning.


## Current development revision

The material and energy projections were derived explicitly and tested against stopped/restarted operation. The earlier low-buffer restart case had exactly0.1m of unexplained mean/discrete inventory difference. Its corrected phase-coordinate projection closes near1e-10m. An independent stop/restart convergence case initially differed95.8ms and0.877% between integration steps; exact permissive-boundary location and explicit hysteresis reduced differences near1e-9s and1e-10relative. The original thresholds remain1ms and0.1%.

Global thermal accounting now includes pump hydraulic work heating the recirculating oil. Film-related die heating draws real auxiliary mechanical power, partitioned75% to die and25% to ambient. Force is independently parameterized by cutting geometry and effective shear strength and integrates to the cycle work. DCS calculations are rebuilt from measured force, delivery, progression, speed and permissive observations.

The v5 focused suite passed15tests. The next snapshot additionally hardens source provenance against forged self-consistent manifests, unexpected source siblings and symbolic-link ancestors. Actual original-reference arrays and all written default dataset artifact bytes matched the untouched source with the same authored PFD overlays for both reference plants. This establishes the tested default-output parity; it does not establish press qualification.

The current generic public cycle file contains measured scan values of status/counter/phase tags. It does not expose the private exact-boundary event ledger and must not be described as a timestamp-per-stroke PLC event journal. Qualification must explicitly assess whether this public resolution is sufficient or implement and qualify a separate measured event-time export.

## Compiled candidate and measured catalog correction

The v15 candidate passed all21focused engineering/native tests and actual native Gates1/2. Its full native14day/19cause Gate3 failed six documented feed evidence claims, retained in `work/press-stages34-v15.log`; Gate4 did not run because Gate3 failed. B2's feeder/decoiler demands were not flat; B3/B4's feeder response did not rise and decoiler demand was not flat. These are adverse results, not qualification. The physical equations remain authoritative. The corrected full observation set includes an independent latched shaft-travel cross-check ZI276 and measured CALC-TRAVEL-GAP from ZI276−ZI272; actual strip travel and shaft travel now have separate trajectory projections. The catalog uses that independent physical relationship rather than an incorrect controller-response prediction. Subsequent gates remain pending.

The sparse profile is now an explicit23tag restriction via native `PLANT.hard_mode_withheld`. Same-truth measurement regression proves retained measurements are identical and omitted channels absent; derived supply/consumption/travel-gap calculations are also omitted when their source observations are absent. This focused proof does not substitute for complete paired90day exports or ambiguity adjudication.

An optional generic digital journal (`cycle_event_journal.parquet`) supplements the measured status scan table. Its public schema is timestamp, event_code, count, quality; codes0/1/2 mean permissive hold/stroke complete/feed complete. Physical edge timestamps are quantized to a1ms PLC acquisition clock. Quality is the actual corresponding native digital status acquisition quality at the preceding scan; this explicitly models held scan acquisition quality, not an independently qualified network/event-buffer model. Non-GOOD acquisition masks the code as−1 and count asNaN. Private pitch, piece rejection result and conservation ledgers are excluded. Native writer/challenge tests verify safe schema, exact public copying, clock, quality masking and counter reconciliation. Events may extend from the last regular scan to the requested run end, because native simulation advances that final interval; counter reconciliation uses matching acquisition timestamps. Full90day leakage/layout/solvability checks remain pending.

## v22 adverse battery and new acquisition epoch

Actual native v22 Gates1–4 passed, but Gate5 failed range-clamping and PCA dimensionality (27 components for95% across41analog tags). Its complete adverse log remains `work/press-stage5-v22.log`; v22 is not qualified. A new physical acquisition epoch corrects pulse encoder classes, signed analogue measurement margins, and exact delayed measured inspection classification. It does not change battery thresholds or inject cross-sensor noise correlation. Thirty focused native/engineering tests passed in development v26, including both authoritative backend event/ledger comparisons, actual gauge-gain classification, digital feedback quantization and original reference byte parity. Final PFD/source freeze and all five native gates are still required; the513case matrix and six90day runs remain pending. Progress evidence is recorded outside this extension to preserve frozen source maps.
