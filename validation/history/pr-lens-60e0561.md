# Hosted PR Lens review of 60e0561

Three medium findings were checked against current code and reproduced with failing regressions:

1. Contextual evidence IDs were not remapped with case-scoped supporting evidence IDs. Regression found dangling maintenance/PFMEA/control-plan references. Both evidence-reference fields now use the same namespace map.
2. Benchmark case lookup deserialized every stored case. Added an indexed SQLite run partition and Store.for_run; the regression checks isolated run results, restart and actual query-plan index usage.
3. PLC input feasibility was inferred from analog/discrete kind, making every candidate true. New hardware now returns null (unknown) until controller compatibility/capacity evidence exists. Existing synthetic control channels remain mapping candidates. The response schema and explanatory contract reflect the uncertainty.

All three regressions failed before fixes and passed afterward. Full suites, real browser acceptance and source-bound full-duration campaign were rerun. This preserves the adverse review rather than claiming the original candidate had no defects. Hosted results for the final correction belong to the PR checks.
