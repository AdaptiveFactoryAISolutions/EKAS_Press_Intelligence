# Synthetic press-cell event catalog

The public catalog is executable in `domain.catalog()` and includes 16 classes. It
contains engineering priors, never the scenario schedule. Every entry records asset,
failed item, mechanism, symptoms, required observations, direction, timing,
competitors, pairwise discriminators, profile visibility and verification method.

| Class | Physical or observation mechanism | Downstream effect |
|---|---|---|
| feeder_sensor_drift | Ramp in position feedback bias | Feed permissive drops beyond tolerance |
| feeder_mechanical_instability | Increasing intermittent position deviation from coupling backlash | Repeated incomplete feed and lost strokes |
| misfeed | Intermittent guide blockage | Progression stops and die-protection interlock acts |
| material_starvation | Incoming strip supply falls; stored loop is consumed | Delayed material-present loss and press stop |
| decoiler_interruption | Decoiler output stops; loop buffer drains | Same delayed press symptom, distinct ready signal |
| lubrication_pressure_loss | Hose leak exceeds PID pump compensation | Continuous pressure decay, increased load and lube interlock |
| die_protection_trip | Periodic slug obstruction | Protection trip, stopped press and restart |
| progressive_die_wear | Ramp in forming force and dimensional error | Load rises before 60-second inspection lag and rejects |
| abnormal_tonnage | Misalignment increases forming load | Overload threshold stops strokes |
| press_speed_degradation | Drive slip reduces achieved stroke rate and raises current | Lost throughput without a commanded setpoint change |
| repeated_microstops | Feed-ready contact opens intermittently | Short feed-interlock stops |
| quality_deterioration | Material temper increases dimensional error | Delayed inspection drift and probabilistic rejects |
| operator_speed_change | Public authorized command reduces rate | Benign capacity reduction |
| planned_stop | Scheduled changeover blocks strokes | Benign downtime and PLC changeover state |
| historian_dropout | Samples become missing while physical evolution continues | Observation gap, no manufactured equipment fault |
| stuck_sensor | SPM register freezes while physical counters continue | Observation artifact |

`simulate(seed=7, duration_s=86400, profile='sparse', events=None,
repair_at_s=None)` returns evaluator-side `SimulationResult(evidence, truth)`.
The diagnostic boundary must receive only `evidence`. This object itself is not a
security boundary. `events=[]` requests a normal twin; explicit schedules use
`event_class`, `start_s`, `end_s`, and optional severity `(0,1]`. Invalid intervals
and profiles fail explicitly. A repair clips active truth intervals and removes
mechanism forcing; pressure and buffer inventory recover through dynamics.

The default 24-hour campaign starts after two clean hours, separates all 16
classes with recovery exposure and retains one-second samples. Shorter custom
runs need explicit schedules if their duration cannot support the baseline.
Profiles select exported observations only; identical seeds and schedules keep
physics, counters and truth identical. All measurement noise uses independent
HistorianSim SeedBank substreams and colored OU noise. Lubrication uses its PID
and RK4 primitives without changing upstream code.

One-second scans accumulate fractional stroke phase into integer strokes. Feed,
material, protection, overload and lubrication permissives gate every stroke.
Each stroke consumes a strip pitch and creates exactly one good or scrap part.
The loop supply controller replenishes the reserve after interruptions. Public
quality records contain good/scrap counts, FPY, defect class, lagged measurement,
drift and holds. Synthetic maintenance, PFMEA and control-plan records provide
fallible historical context. Ambient variation, normal material variation and a
single-sample ambient spike provide noncausal distractors.

Physical limits: this is a reduced synthetic engineering model, not a calibrated
press digital twin or machinery safety controller. A one-second historian scan
does not resolve the within-stroke waveform or servo-feed trajectory. Tonnage is
an envelope, not a strain-gauge waveform. Misfeed/relay/slug intermittency is
idealized periodic forcing; wear and failure clear at repair rather than modeling
technician work. Quality transport delay is fixed at 60 seconds. No camera,
vibration or acoustic waveform is claimed. Sparse ambiguity and enhanced signal
availability express possible discrimination, not proof of a physical cause.

The sparse profile exports 13 configured PLC/press observations: commanded
`rate_setpoint`, `press_run`, `press_stop`, `press_fault`, `stroke_count`, `spm`,
`part_count`, `job`, `die_id`, `plc_state`, `die_protection`, `feeder_ready` and
`lube_ok`. Commanded rate is an existing control variable, distinct from measured
achieved SPM. The operator episode changes the public command from 60 to 42 SPM
and records its return to 60 SPM; drive slip changes achieved rate while leaving
the command unchanged. Configuration at a real plant still requires confirmation.

PLC state uses a scan-end convention: `STROKE` means at least one integer stroke
completed during the represented one-second scan. `FEED` means the press is
running between stroke completions. Stop/changeover states complete no strokes.
The timestamp labels the scan index, and counters include that scan's completed
work. Feed and forming occur within the scan; sampled PLC states do not claim to
resolve those subsecond phases. This convention also applies at fractional rates
such as 42 SPM (0.7 strokes/second).

Acquisition quality is derived from acquired values, never the injected event
class. `MISSING` means an acquired value is `None`. The public acquisition
monitor reports `STUCK` only after positive SPM repeats exactly for at least 30
elapsed seconds while an independent stroke counter advances, with progress in
the last five seconds. A changed value or missing acquisition resets the plateau;
normal zero-speed stops cannot trigger it. This is suspected acquisition behavior,
not verification of a sensor failure mechanism. The monitor accepts no schedule,
event class or truth input, and its rule is included in public dataset context.
