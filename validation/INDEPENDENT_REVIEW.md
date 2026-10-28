# Independent review and corrective record

The independent reviewer inspected the implementation before the final corrections and reported five Important findings. This record preserves that adverse disposition; it does not relabel the initial review as a clean review or claim a second independent approval.

| Finding | Corrective evidence |
|---|---|
| PFMEA/control-plan list-valued signal violated response schema | Failing contract serialization regression; contextual signal is now null with separate signal_ids and explicit unscoped qualification; named response models validate route results |
| Sparse scrap defaulted to zero and inspection quality included future records | Failing in-window quality/count regressions; missing outcomes stay unknown; window and baseline quality separated; sparse inspection counts measured |
| Irrelevant ambient evidence earned cause credit | Failing ambient/unchanged-reference regressions; versioned evaluator now requires relevant, internally consistent mechanism evidence and documented alternatives |
| Available but conflicting component scope silently accepted | Failing objective/asset conflict regression; typed clarification replaces substitution |
| Commanded speed changes could masquerade as repair improvement | Failing setpoint-comparability regression; actual PLC rate_setpoint is observed and controlled separately from achieved speed |

Further implementation audits reproduced and corrected depleted-buffer recovery, inconsistent scan-end PLC state, truth-keyed stuck-quality flags, stale displayed case state, re-enabled frozen submission control, missing named OpenAPI responses, and use of an unrelated installed simulator. Each has a regression or negative test; earlier campaign results remain under history/.

Verification also rejects trivial performance noise and reports uncertainty using controlled-press-comparison-1.0. The actual seeded drive-repair test demonstrates a meaningful improvement while retaining compatible scrap uncertainty. A stopped/no-output comparison remains inconclusive when quality outcomes cannot be established.

Final source was checked through the complete EKAS suite, real browser flow, clean installed environment, unchanged pinned upstream suite and a regenerated full-duration blind campaign. Patrick's manual acceptance remains the final gate. No finding was waived to obtain a passing result.
