# Prototype Roadmap

## WP0 — Repository integrity
- Bootstrap complete upstream projects.
- Verify pinned revisions and licenses.
- Run upstream test suites.
- Capture upstream baseline evidence.

## WP1 — Press observability model
- Define SmartPAC-like and PLC signal catalog.
- Define sparse instrumentation profile.
- Define enhanced instrumentation profile.
- Implement coverage and ambiguity analysis.

## WP2 — Stamping simulation
- Add progressive press plant model using HistorianSim extension mechanisms.
- Add control/state dynamics and historian behavior.
- Add 14-day normal baseline and reproducible scenarios.

## WP3 — Fault catalog
Initial target classes:
- Feeder sensor drift/intermittency
- Feeder mechanical slip/misfeed
- Material starvation / low loop
- Lubrication pressure loss
- Die wear progression
- Die protection event
- Press speed degradation
- Tonnage/load anomaly
- Quality deterioration
- Upstream material disturbance
- Operator speed/setpoint change (benign)
- Historian/communication artifact (benign)

## WP4 — Blind benchmark
- Hidden answer key.
- Evidence requirements.
- Distractors.
- False-positive scoring.
- Ground-truth comparison.

## WP5 — Governed RCA
- Evidence graph.
- Hypotheses.
- Alternatives.
- Confidence/qualification.
- Human verification gate.

## WP6 — Sensor-gap analysis
- Map unresolved alternatives to missing signals.
- Rank sensors by ambiguity reduction, cost class, and deployment burden.

## WP7 — Action verification
- Corrective action case.
- Before/after operational result.
- Sustainment monitoring.
- Financial classification.

## WP8 — Standalone UI prototype
- Chat-first RCA case.
- Evidence drawer.
- Signal timeline.
- Observability map.
- Sensor-gap recommendation view.
- Benchmark mode.

## WP9 — EKAS integration certification
Only after independent acceptance:
- Lock module contract v1.
- Add adapter in EKAS UI.
- Preserve Demo/Live separation.
- Full EKAS regression certification.
