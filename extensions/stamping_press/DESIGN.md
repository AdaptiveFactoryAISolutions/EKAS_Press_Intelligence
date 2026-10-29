# P-27 stamping cell: approved implementation design

Status: approved for implementation under HistorianSim /simulate Step2; engineering and dataset qualification remain pending. All numeric values below are explicit synthetic design assumptions, not Patrick's machine specifications or validated plant calibration. This document and the private catalog must never be shipped in a blind analyst challenge.

## 1. Service

One stamping cell, including press drive, servo feeder, decoiler/loop buffer, lubrication supply, die thermal behavior and downstream dimensional inspection. Produce one stamped piece per permitted completed cycle from cold-rolled strip. Separate metal entering, in-process inventory, good parts, rejected parts and trim. Stop permissives and deliberate operator moves are controls, not injected symptoms.

Preserve the full TK-101/R-201 chemical reference functionality alongside this extension. Do not translate steam equations into press physics or relabel the chemical datasets as press records.

## 2. Equipment and flow

```
coil / DC-27 decoiler -> loop buffer LI-271 -> FD-27 servo feeder -> P-27 / DIE-27 -> dimensional inspection
         DI-271 ready      LIC-271 speed        FDC-271 command    SIC-271 drive     QI-271 gauge
         PI-271 tension    LI-272 independent   ZI-271 encoder      SI-272 independent QI-272 check sample
                                               ZI-272 progression JI-271 motor power count / scrap
                                               DI-272 complete    WI-271 force
                                                                  TI-271 die temp
LUBE-27 pump -> filter DPI-271 -> PI-272 controlled pressure -> bearings -> return / TI-272 oil temperature
              FI-271 flow       PI-273 independent pressure
CW-27 cooling -> FI-272 coolant flow / TI-273 supply -> die -> return
```

Every final native tag entry must state source, unit, range, role, loop, update period, sensor dynamics, quality, node and historian behavior. The final drawing must include every actual tag and loop; this provisional sketch cannot substitute for the rendered inspected PFD.

## 3. Design point and calculation

Assume 60 strokes/min; 100 mm pitch; strip 100 mm wide and 1.2 mm thick; density 7,850 kg/m3. Assume mean forming work 1,000 J/cycle and 300 W equivalent mechanical loss. Flywheel inertia 1,000 kg m2 and direct-reference angular speed 2 pi rad/s. Drive efficiency 0.90, full-scale torque 600 Nm. Lubrication: 5 bar at 5 L/min with a 10 L/min variable pump.

Calculation executed with Python before this document:

| Quantity | Calculated value |
|---|---:|
| Angular speed | 6.283185307 rad/s |
| Stored flywheel energy | 19,739.208802 J |
| Mean forming power | 1,000 W |
| Drive fraction for forming plus mechanical loss | 0.383150789 |
| Strip mass per pitch | 0.0942 kg |
| Strip mass rate | 339.12 kg/h |
| Lubrication hydraulic power | 41.666667 W |
| Nominal pump command | 0.50 |

These are initial balance checks, not a completed cycle-equilibrium or stability proof. Forming force versus displacement must integrate to the assumed work; motor/feeder limits, trim fraction and heat partitions must close before implementation is called physically correct. All values remain visible assumptions until replaced by qualified equipment data.

Initial transmitter ranges place normal readings in 20-60% of span: speed 0-150 SPM, feed travel 0-250 mm, lubrication 0-12 bar, loop 0-2.5 m, oil 0-100 degC. Force range is sized from the computed force-displacement envelope, not guessed to hide overloads. Actuator design commands must sit at 30-70% with actual loop headroom.

## 4. States and physics

Use six envelope states: mean drive angular speed, achieved feed-pitch envelope, mean buffer length, lubrication pressure, oil temperature, die temperature. Use a separate generic phase/event clock for crank passage, within-cycle motion, feed completion, material withdrawal, counters, trips, restart and delayed part inspection. An envelope is a cycle-averaged or completed-cycle quantity; it is never presented as an instantaneous within-stroke measurement. These are hybrid events, not arbitrary waveforms appended to finished historian tags.

Required balances and relations:

- Drive energy: d(0.5 J omega^2)/dt = eta P_motor - P_form - P_bearing - P_other. Compute forming work from force-displacement and material/die parameters. Reconstruct intra-cycle energy demand from the same work, not a prewritten speed dip.
- Feed response: the achieved pitch envelope follows measured completed-feed error and available servo/traction headroom. Its first-order time constant is derived from the declared overdamped servo assumption. Within-cycle motion has a prescribed acceleration-limited command trajectory; actual travel is constrained by available traction/backlash and must agree with the achieved pitch. A biased controlled encoder drives a real pitch error; independent strip progression is a different instrument. Do not claim that this envelope represents high-frequency servo dynamics or infer detailed vibration from it.
- Material: buffer accumulation equals decoiler delivery minus actual consumed strip. Feed/part counters change only on completed permitted events. No negative inventory or stroke without a valid feed.
- Lubrication: dp/dt = beta/V times (pump delivery - bearing demand - leakage). Pump delivery, hydraulic restriction and oil viscosity are physical parameters. Pressure control responds to the measured transmitter.
- Oil energy: m cp dT/dt = mechanical/pump losses entering oil - cooler/ambient heat removal.
- Die energy: m cp dT/dt = allocated forming/friction heat - coolant/ambient removal. Part dimension follows explicit thermal/material/feed relations. Inspection samples the part after its actual transport delay.

The envelope equilibrium and the cycle event model must agree on mean power, throughput and material consumption. Perform timestep/event convergence. The inherited continuous equilibrium test cannot be passed by pretending a rotating crank or growing counter is a stationary state. Retain its applicable envelope tests and add stricter hybrid periodic/conservation gates.

### Exact native gate and integration contract

Native stages 1 and 2 run on the same six-state envelope model used in production, through the actual native simulate and generate paths. No quiet-only replacement model or relaxed threshold is permitted. Every native noncascade loop has a stationary envelope PV at nominal operation:

| Native loop PV | Exact semantics for stages 1/2 and generation | Separate instantaneous/cycle observations |
|---|---|---|
| SIC-271.PV | Mean cycle speed, SPM | Independent tachometer SI-272 and phase/peak speed |
| FDC-271.PV | Last completed feed pitch held between completions, mm; healthy steady value 100 mm | Encoder trajectory ZI-271, independent progression ZI-272 and feed-complete events |
| LIC-271.PV | Mean loop inventory, m | Within-cycle buffer drawdown and limit events |
| PIC-272.PV | Header pressure at controller scan, bar | Independent pressure, flow and filter differential |
| TIC-271.PV | Lumped die temperature, degC | Part-bound delayed inspection and independent sample |

The feeder setpoint is desired pitch, not a permanently increasing absolute strip position. Native stage 2 therefore changes a constant pitch setpoint and tests settled completed-feed pitch. Trip/changeover/interlock behavior is tested additionally; it does not get excluded from the actual production simulation.

Author the press via upstream Plant/UnitModel/RootCause/TagSpec contracts. Use a generic optional CycleEventSource contract in the native integration path for phase/event advancement, event-boundary subdivision, controlled-sensor values and a measured public event stream. It must operate inside both the faulted and matched-twin evolution, before native measurement/export. Keep the stock simulate result and native pipeline.generate/write_dataset/challenge/audit functions as the orchestrators. The reproducible generic patch must extend those contracts and safe artifact allowlists together; it cannot monkey-patch a different simulator into pipeline.generate. For nonhybrid reference plants, numerical trajectories and artifacts must match the untouched upstream build exactly. Demonstrate this before relying on the extension.

Native equilibrium/step checks inspect the registered PV semantics above with their original 0.1%-hold and original step-settling limits. Hybrid gates independently check within-cycle speed/force, measured feed completion, stop permissives, material and energy. Neither projection alone establishes full press correctness.

This is a documented lumped engineering model at historian resolution. It must not be sold as finite-element tooling design, a high-frequency waveform generator or a validated real machine. Optional higher-frequency sensors need separate physical models and qualification.

## 5. Control

| Loop | Measures | Acts on | Diagnostic purpose |
|---|---|---|---|
| SIC-271 | controlled mean speed | motor demand | Speed held while load/friction consumes headroom |
| FDC-271 | controlled encoder position | feeder drive | Controller can follow a false reading; independent progression exposes it |
| LIC-271 | buffer length | decoiler delivery | Loose inventory regulation masks supply disturbances until reserve is depleted |
| PIC-272 | lubrication pressure | pump demand | Pressure held while pump/line faults change output, flow and filter differential |
| TIC-271 | die temperature | coolant demand | Temperature held while cooling loss consumes capacity |

Explicit PLC permissives govern feed, die protection, lubrication, buffer limits, overload, safe stop and restart. Controller modes, commands, measurements and independent measurements are separate native tags. Tuning intent and equilibrium command calculations precede gate 1. No stop is synthesized by directly forcing a production tag to zero.

## 6. Disturbances and measurement

Named SeedBank streams drive ambient/local weather, utility headers, material thickness/strength, supply variability and instrument-specific effects. Native colored noise, lag, quantization, calibration wander, freezes, spikes, node outages and historian compression are retained. No global random generator. Ordinary calibration wander and historian artifacts remain nonfault distractions in the canonical benchmark.

Full profile includes independent measurements needed for solvability. Sparse SmartPAC/PLC observation is a separately declared information restriction of the same physical run. It can remain ambiguous and must not be graded against the full profile's solvability promise. Report source availability and measured discrimination separately.

## 7. Symptom-first physical catalog

Nineteen candidates are proposed; group by first symptom. Before implementation completion each must have an upstream RootCause, real parameter/control/disturbance/instrument injection, component, mechanism, severity sizing, 3-7 evidence items and explicit rules_out for every competitor. The table is a design requirement, not proof these signatures exist.

| Class | Shared first symptom | Competing causes / failed items | Required discriminating relationships |
|---|---|---|---|
| S1 slow | Motor demand rises while mean speed is held | main-bearing drag; oil viscosity increase; strip-strength rise; die-insert wear; die-guide misalignment | Power, oil temperature/pressure, material reference, force/work envelope, dimensional/position symmetry |
| S2 cycling/acute | Feeder correction or ready interruptions | encoder gain failure; feed-roll traction loss; coupling backlash; strip-guide obstruction; decoiler brake drag; feeder controller left manual | Measured command/encoder versus independent progression, mode/output, tension, buffer and feed completion timing |
| S3 slow/acute | Pump output rises while pressure is held | hose leakage; pump volumetric wear; filter blockage; supply-voltage loss | Independent pressure, delivered/return flow, filter differential, motor command/power and supply reference |
| S4 slow | Dimensional drift or reject tendency | die-cooling loss; stock-thickness variation; film-delivery failure; inspection-gauge gain failure | Independent gauge/sample, die temperature/coolant duty, stock measurement and physical film/flow measurement |

At least half the catalog must demonstrably be masked by real closed-loop control before headroom is exhausted. Instrument and physical effects must be distinguishable through redundant or physically related observations, not supplied event names. Evidence declarations remain private; public process descriptions explain relationships without a cause menu.

## 8. Canonical benchmark scenario

Follow the native rca-benchmark recipe: 90 days, 10-second historian scan, fourteen normal baseline days, nine unique non-overlapping faults, at least two clean days on either side, two benign operator moves, and full instrument/neighbor distraction layers. Choose an internal integration/event step from convergence, not the historian scan. Preserve standard/campaign overrides as native functionality.

| Order | Cause / distinct component | Layer | Proposed severity | Initial physical change to size and verify |
|---|---|---|---|---|
| 1 | Main-bearing drag / main bearing | Process | Moderate | Friction coefficient +20% |
| 2 | Encoder gain failure / feeder encoder | Instrument in feedback and measurement | Obvious | Gain +3% |
| 3 | Pump wear / pump element | Process | Moderate | Volumetric efficiency -15% |
| 4 | Strip-strength increase / incoming stock strength | Disturbance | Subtle | Forming strength +8% |
| 5 | Roll traction loss / feed-roll surface | Process | Moderate | Traction capacity -20% |
| 6 | Cooling loss / cooling supply | Disturbance | Moderate | Available heat-transfer capacity -25% |
| 7 | Filter blockage / lubrication filter | Process | Obvious | Hydraulic resistance +80% |
| 8 | Feeder manual mode / feeder control station | Control | Moderate | MAN output initially 90% of required equilibrium |
| 9 | Gauge gain failure / inspection gauge | Instrument | Subtle | Gain +0.2%, distinct from ordinary calibration wander |

These are proposed amplitudes, not manufactured observations. Confirm subtle versus moderate versus obvious from matched measured twins, variability and first-observable time. Do not lower acceptance thresholds or prescribe tag effects to make these numbers pass. If physical sizing is wrong, recalculate and record it.

Benign moves: an authorized production-speed setpoint reduction and a planned tooling changeover. Setpoint/mode records must explain their legitimate plant response. Artifact distractions never earn physical-fault points.

## 9. Acceptance

Follow all five native stages in order; preserve failures. Additional hybrid gates prove integer events, no stroke without feed, material and energy closure, correct stop/restart, controller-transmitter feedback, no output-only physical faults, causal delay and convergence. Gate 3 measures every catalog cause against the same-weather no-fault twin; gate 4 proves evidence references and same-symptom discrimination. Gate 5 is iteration only.

Then complete the canonical full-duration generation and every native battery/layout/leakage/recipe check. Render/inspect PFD, inspect every event's confirming and eliminating tags, create the native challenge outside the repository, give a fresh analyst only that challenge, freeze CSV, independently adjudicate item and mechanism and record each miss. No answer key or cause list in the analyst environment.

Qualify additional seeds, operating points and severities declared before tuning. Full/sparse comparisons use identical physics. Passing one seeded campaign is insufficient. Release evidence must include actual native pipeline origins and any reviewed hybrid patch; the old rule-engine campaign cannot satisfy these gates.

### Fixed qualification matrix and quantitative criteria

Declare this matrix before implementing or tuning the press. Seed 7 at 60 SPM is development/reference. Seeds 19 and 42 and the 45/75 SPM points are held out from detector/analyst tuning. All three native severity levels are included. Record any later matrix revision as a changed design, preserving prior adverse results.

- Single-cause physics/discrimination sweeps: all 19 candidates x seeds 7/19/42 x rates 45/60/75 SPM x subtle/moderate/obvious = 513 injected cases, each paired with its identical-weather no-fault twin. Use the native sweep's tempo-based exposure and evidence/SNR checks; do not replace the native sweep with an arbitrary short pulse. Every required directional, flat and reference-integrity check must pass. Full instrumentation must have measured separating evidence; sparse omissions remain declared ambiguity.
- Full press datasets: six actual 90-day native rca-benchmark runs, at (seed,SPM) = (7,60), (19,60), (42,60), (19,45), (42,75), (42,45). Preserve all nine faults and both benign moves. Their sparse/enhanced exports derive from identical physical histories. Run all native battery, recipe, layout, leakage and solvability checks. Quick or reduced-duration runs cannot substitute.
- Masking: at least 10 of the 19 candidates at moderate severity must keep their controlled envelope PV within 1% of its nominal setpoint during the central 80% of the episode while a measured actuator/load signature exceeds the native directional-evidence threshold. Report which candidates qualify, time fractions and headroom. A flag in the catalog is not evidence.
- Event invariants: counters are integers; every good/reject piece corresponds to one permitted completed stroke; no withdrawal without available material; counter reconciliation and material-ledger accounting are exact in discrete units. Floating mass residual is at most 1e-6 of supplied mass over a completed ledger interval, with geometric trim explicitly accounted for.
- Energy: cycle work matches force-displacement integration and motor/loss/storage accounting to 0.1% of interval input energy, including stopped/restarted intervals. Expose numerical residuals, never add a balancing fudge term.
- Convergence: halving the chosen internal step changes mean physical PVs by at most 0.1%, within-cycle peak speed/force by at most 1%, and located event boundaries by at most 1 ms. Completed cycles must reconcile exactly; disclose a terminal partial cycle separately. The original reference plants retain their stricter native tests unchanged.
- Independent blind analysis: one fresh blind run for each of the six full datasets, with frozen submissions and independent item/mechanism adjudication. Report all detection, cause, timing and false-positive results, including failures. No minimum perfect-agent score is imposed: an analyst error is retained if an independent physics review demonstrates the necessary public evidence. A data-solvability failure blocks qualification. Never tune these held-out datasets into the already tested rule catalog.

## Implementation derivation: hybrid mean coordinates and permissive boundaries

This implementation detail preserves the six approved envelope states. It is a synthetic lumped model assumption requiring engineering review, not an assertion about a real P-27 machine.

For cycle phase `phi`, latched completed-feed travel `L` in metres, and a feed withdrawal at half a revolution, actual loop length is `mean_loop + L*phi - withdrawn_this_cycle`. When the completed feed differs from its prior envelope estimate, the mean coordinate changes by `(old_L-new_L)*phi`. That is the derived coordinate change which preserves actual inventory, not a fitted residual or an extra physical source. Exact incoming, in-process, trimmed and product mass remain separate ledger entries.

For latched forming work `W` and the cumulative triangular force/displacement integral `F(phi)` (zero before the forming half cycle, one at its end), instantaneous flywheel storage is `0.5*J*omega_mean^2 + W*(phi-F(phi))`. A newly known work value at feed completion changes the mean energy coordinate by `(old_W-new_W)*(phi-F(phi))`, preserving instantaneous storage. Actual forming energy increments by `W*(F(phi_end)-F(phi_start))`; energy validation compares motor input, physical losses, this actual work, and instantaneous storage. Mean forming power uses the same latched work and phase advance. No balancing residual is fed back into the model.

The synthetic press has an interlocked clutch and a viscous brake. A trip opens the clutch and holds crank phase and its partial forming work; the flywheel dissipates energy through the declared brake while oil, cooling, feed-servo envelope and buffer supply continue evolving. Restart closes the clutch only after the restart permissives return. This avoids a hidden empty stroke or a fictitious material withdrawal during a stop. A feed token retains in-process material across a pause. The brake coefficient is100 Nm/(rad/s), a synthetic engineering assumption.

Stop limits are lubrication2bar, mean loop0.15m, die80degC, work2500J, and pitch50–150mm. Automatic restart requires lubrication2.5bar, mean loop0.25m, die below75degC, work below2200J, and pitch55–145mm. Exact threshold crossings subdivide native integration steps; hysteresis prevents control chatter. Operator-controlled reset behavior on a real machine needs a separate qualified PLC design.

The phase clock uses mean cycle speed. Within-cycle speed is reconstructed from the declared energy coordinate, and the acceleration-limited feed trajectory uses the same phase. This is an explicit averaged kinematic reconstruction, not a rigid-body crankshaft or high-frequency drivetrain solution. Convergence and conservation are tested for this declared model; they cannot validate an actual machine's kinematics.

The force law is now parameterized independently by effective cutting perimeter0.376m and effective cold-strip shear strength221.631205674MPa. At1.2mm thickness their product gives100kN peak force. A triangular force envelope over20mm displacement integrates to1000J. The stated12% geometric trim is consistent with an88mm-wide rectangular product from100mm-wide strip at100mm pitch; its0.376m perimeter is the effective cutting perimeter. This is an explicit idealized geometry and effective strength assumption, not a tooling specification. `WI-271` is the peak force envelope; `WI-273` is the phase-based instantaneous force reconstruction. DCS work is computed from measured peak force and declared travel. Actual supply is independently measured; the DCS material-rate calculation uses measured strip progression, mean speed and permissive status.

The energy partitions are explicit:30% of forming work heats the lumped die and70% leaves with the strip/products;75% of auxiliary die friction heats the die and25% reaches ambient. Film delivery changes actual auxiliary mechanical loss by the declared inverse-film relation, limited at the dry-friction value of ten times nominal. Pump electrical input includes delivered hydraulic work plus motor losses divided by the declared pump efficiency; the recirculating hydraulic work and pump losses ultimately heat the oil. Bearing dissipation also heats oil. Brake energy reaches ambient. Thus every term heating oil or die has a corresponding physical energy source. At equilibrium, drive mechanical power plus pump input equals forming energy leaving with material, oil cooling, die cooling/ambient loss and other ambient dissipation. These partitions and the dry-friction limit remain synthetic assumptions.

Mid-stroke stopping opens the clutch and transforms the latched mean energy coordinate to actual free-flywheel storage. The partial work and feed token remain held. Before re-engagement, the flywheel must have enough stored energy to restore that coordinate and retain at least1rad/s mean speed. The readiness crossing is located as a physical event. Angular acceleration is evaluated in torque form, including its finite limit at zero speed, rather than dividing an energy balance by an artificial minimum speed. Actual drive power is torque times actual angular speed. These details are required to conserve energy through stopped and restarted intervals.

All hybrid integration steps are at most0.5s, including periods with no rotating crank. This ceiling was selected after a paused5s integration test failed the unchanged energy criterion; it is disclosed in addition to the configured outer native integration and controller clocks. The compiled C++ kernel evaluates the same six-state derivatives, RK4 stages, event roots, coordinate transforms, material, transport and energy ledgers as the retained Python reference. It uses strict IEEE floating point without fast-math and is built and hashed by runtime preparation. The default native press uses this kernel; `compiled_cycles=0` is the explicit reference/testing option. Native simulation, controller feedback, measurement, historian, truth, recipes, challenges and validation remain unchanged orchestrators.

The operator tooling changeover now deliberately sets the native speed setpoint to zero, holds production during an identical-tool replacement, and restores its original setpoint. It is a real control-system pause and restart, not a renamed feed-pitch move. Both the faulted and matched-twin runs execute the same native benign control event.

Each feed token binds actual completed pitch, material mass and stock thickness. Stamping and the delayed inspection use that piece's material and progression, even if incoming stock changes after it was fed. No inspection record is inferred from the material arriving ten seconds later.

### Declared sparse observation profile

The sparse profile represents an intentionally restricted PLC/press-controller export, not a claim that every SmartPAC installation has this exact instrument inventory. It retains five loop stations, primary force and inspection, feeder trajectories, counts, phase and permissive/latch status. It withholds independent shaft/progression/buffer/pressure checks, auxiliary oil temperature, transverse force, coupling displacement, leak drain, pump power, stock strength/thickness, voltage, film/cooling delivery, cooling return temperature, filter differential pressure, strip tension, and the second inspection gauge. Calculated supply and consumption are also withheld because their measured source tags are absent; retaining a truth-derived fallback would leak the omitted instruments. Exact native tag names are `PLANT.hard_mode_withheld`. Native measurement omission operates on the identical physical history; it cannot alter controllers, faults, events or truth. Missing independent references can leave competing causes ambiguous. Full-profile measured separation and sparse ambiguity must be reported independently.

### Independent travel cross-check

ZI274 observes within-cycle shaft travel; ZI275 observes within-cycle strip travel. ZI276 is a separate independent latched shaft-travel check with the same0..250mm span as the feeder stroke. Controlled transmitter calibration faults apply to FDC271.PV, not this independent reference. CALC-TRAVEL-GAP subtracts measured strip travel ZI272 from measured shaft travel ZI276. This is a measured relationship, never a fault-ID output. It stays near zero when actual shaft and strip travel change together; physical slip or lost travel separates them. Both the independent cross-check and its calculated difference are withheld in the sparse profile. No controller reads truth-only geometry.

### Acquisition and inspection correction after v22 adverse Gate5

The v22 native battery exposed a physical instrumentation mismatch: pulse-count position/speed had been assigned liquid-level/flow measurement dynamics, and real zero-centered analogue observations were clipped by unipolar calibration ranges. The new acquisition classes are declared before reevaluation in `instruments.py`: a16bit scaled pulse acquisition word has one-code resolution of configured span/65536, deterministic quantization and no invented analogue turbulence/wander. Quantization and actual calibration faults are inside native feedback. Optical acquisition is per arriving part: a5000pixel100mm field with half-pixel interpolation gives10um output increments; independent50um/600s OU thermal/illumination uncertainty and0.2um/day ordinary drift are explicit synthetic assumptions. Each irregular interval uses its actual elapsed time, not a nominal cycle period.

Inspection delivery is an exact physical event at stroke completion+10s. True physical classifications and measured PLC classifications both reconcile completed=accepted+rejected+pending; only measured classifications reach public COUNT272/273. The primary acquired gauge reading, including its actual gain faults, uncertainty, drift and quantization, determines public acceptance against100mm±0.25mm. COUNT274 reports pending inspection. The independent second gauge remains a separate acquired reference. Native historian quality is downstream of local PLC classification; a historian outage does not silently discard physical parts. Public journal code3 reports inspection delivery and cumulative delivered count, without dimensions or rejection decisions. Private dimensional event payloads remain private.

### Latched physical feed endpoint correction

An independent review retained an adversev28 reproduction: a40mm commanded amplitude reduction changed the projected endpoint by0.66114mm across a2us half-cycle interval because the old completed endpoint was replaced by the evolving envelope at feed completion. The corrected source latches active strip and shaft travel when the feed is admitted at phase zero, executes the symmetric acceleration-limited trajectory, and debits exactly that planned strip travel when completed. The evolving envelope schedules a subsequent cycle; it cannot rewrite executed stock travel. A stopped phase-zero cycle latches the settled command when its clutch is actually admitted; a stopped partial feed preserves its active plan. The phase coordinate resets only at a completed-stroke boundary, explicitly distinguished from physical backwards motion. Both authoritative backends carry the same plan in ABI6. At100mm travel over0.5s, the triangular-velocity profile has400mm/s peak speed and1600mm/s² acceleration magnitude; dense1ms and2us boundary regressions prove the stated limits, continuity and material timing. All19cause/severity/backend golden comparisons remain mandatory.
