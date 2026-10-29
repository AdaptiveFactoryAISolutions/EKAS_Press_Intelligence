# Connected generic line model and verification boundary

`stamping_line` is a distinct native HistorianSim `UnitModel` with the native
`cycle_event_source` hook. The original `stamping_press`, pinned vendor source
and historical runtime remain unchanged. Runtime preparation copies and hashes
both overlays, applies authored patches and verifies the derived source tree.

## Numerical design basis

The guided-line configuration owns the flat numeric setup parameters. Forces
cross the API boundary once into `capacity_n` and `forming_force_n` in N. Work
is J; dimensions retain named mm units; density kg/m3; speeds explicitly SPM,
m/s or m/min. Default geometry/material and capacities match the implementation
plan. These are generic builder assumptions, not manufacturer calibration.

Additional declared generic assumptions: 20% of incoming segment mass becomes
offal; three-second discharge transit; seven straightener rollers, 50mm bending
radius, 0.95-times-thickness gap, steel E=210GPa, 0.5s speed response; 50L lube
reservoir, 90% return, ten timed branches; 0.5m reel core; 120s operator coil
replacement; scrap routes 1=shaker 0.4kg/s, 2=conveyor 0.5kg/s, 3=combined
0.9kg/s and 20kg high accumulation trip; 5kW running mechanical losses and
1kW stopped standby; water heat capacity4180J/(kg K), steel500J/(kg K),
water latent heat2.26MJ/kg, 200W/K washer ambient loss, makeup up to0.25L/s,
evaporation0.005L/s plus0.1% of spray circulation, part heat-transfer
coefficient0.02/s. Packing rate has deterministic ±10% variation on a30s
phase scale; container changes use the configured delay. Wash cleaning requires
30 equivalent seconds at60C and nominal spray; dose accumulates throughout
residence, scaled by temperature and spray-pressure/flow availability.

## Connected physics and instruments

A finite reel supplies the loop through the straightener speed/load model.
The strip/drive inventory response is integrated together using RK4. Loaded
coils and replacement intervals are counted, and new stock is explicitly added
to the supply ledger. The feeder advances finite shaft/strip travel during its
permitted window. Slip creates a measured following difference and physically
debits partial strip into pending feed inventory. A failed feed holds the cycle;
a repaired traction condition completes the remaining movement before resuming.

Nine retained segments connect the ten stations. The tenth operation releases
a part on the tenth stroke. Presence and station force are occupancy-dependent,
with separate directly instrumented station assumptions and four corner loads.
The entered force/work recipe references600mm width,1.5mm thickness and800mm
progression. Generic force scales with width×thickness; work additionally scales
with progression. Lubrication restriction multiplies both by the inverse surviving
film fraction (bounded below at0.2). This is an explicitly generic scaling law,
not an empirical tooling calibration. Geometry changes therefore alter actual
force/current, and an exceeded force, stroke-work travel or motor envelope stops
production. A triangular load versus ram-displacement envelope integrates to this
resolved work; lubrication loss raises force/work and capacity/drive checks can stop the
cycle. Drive power and current use the same efficiency/power-factor calculation
as time-integrated electrical energy. Stops reduce demand to standby. This is
an averaged cycle-energy model, not a rigid-crank or flywheel safety model.

Lube header pressure responds dynamically, branch deliveries are timed to the
cycle, reservoir inventory loses the nonreturned fraction and low inventory
interlocks. Scrap accumulation/removal has its own mass ledger and stop path.
Finite discharge, washer and pack queues propagate downstream blockage upstream.
Before a releasing stroke, discharge capacity is reserved for the entire multi-out
batch; partial free capacity never permits an oversized atomic release.
The washer integrates water inventory, makeup, evaporation, actual heater duty,
ambient/latent heat and heat transferred into resident parts. Dose accumulates
for each resident part, so an in-transit spray/heat change affects the eventual
inspection. A declared synthetic manual visual inspection at washer exit makes
the public accepted/rejected decision; hidden dose is not exported. Packing is
manual service with finite queues, variable rate and container changeovers.

The maximum numerical integration quantum is0.1s. Native acquisition is1s and
the public digital journal retains cycle/feed/product/packing event times;
trend export is independent. Encoder instruments retain declared deterministic
digital quantization. No arbitrary colored noise or signal-class reassignment
was added to satisfy a validation gate. Journal codes retain the existing press
meanings:1stroke,2feed;4product discharge and5packing extend them.

## Accounting and evidence

Private native ledgers separately retain coil, loop, pending feed/die, outputs,
offal and removed offal. Produced equals packed+rejected+discharge+washer+pack
queue exactly. Electrical input, averaged forming energy and losses reconcile.
Water inventory and washer thermal inputs/outputs/storage also reconcile.
`engineering_acceptance` independently recomputes these arithmetic relationships
and rejects inconsistent reported residuals. Limits are material/water1e-6
relative, mechanical/thermal energy0.001 relative, exact integer counters,
without startup exemptions. These ledgers are not public tags.

Focused regressions exercise native registration, stock/output conservation,
first part on stroke10, stops/resume, finite packing blockage, actual slip,
coil replacement, lube effects on current, power/current consistency, actual
heater duty, in-residence washer faults, force/displacement work, native sensor
acquisition isolation, and numerical convergence. Halving the actual quantum
0.1→0.05s preserves event counts and changes remaining coil by under0.001kg
(under1e-7 of initial stock); calling-clock convergence is checked separately.
Mass closure remains independently bounded at1e-6 relative.

Native ten-minute generation/export was exercised for healthy plus all eight
catalog faults. Exact source-bound checks are retained under work/. The initial
prototype's adverse report remains at work/guided-line-native-evidence; subsequent
source epochs have separate work/guided-line-native-final*/ reports.

The unchanged native battery still rejects short practice datasets on colored
noise and historian irregularity; healthy no-fault data also fails the upstream
faulted/twin-divergence requirement. PCA dimensionality warns. These adverse
checks remain visible. Explicit practice registration is UNVALIDATED and must
never be described as qualified. A separate approved qualification campaign and
reviewed acquisition/validation scope are still required. This model does not
qualify physical equipment, finite-element tooling behavior, safety functions,
real worker ergonomics or manufacturer process capability.

## Compiled execution and multi-day catalog scope (R3)

`compiled_cycles=1` selects the compiled C++ RK4/event implementation by default;
`compiled_cycles=0` retains the Python reference. Both use the same maximum0.1s
quantum, event splits, equations, queues and native lifecycle. The shared library
uses the same deterministic compiler flags as the original press; compiler,
source and artifact SHA256 are recorded in the runtime manifest and reproduced
by the derived-source verifier. Missing/incorrect ABI artifacts fail explicitly.

Differential tests compare every scalar, state, public/private observation,
transport queue, event code/count/time and conservation ledger across healthy,
each physical fault, recovery, operator stops, coil changes and multi-out
capacity. State differences in the measured R3 comparison were exactly zero;
relative/absolute guards remain in regression tests to catch future drift.
The native sensor-fault test separately verifies acquisition corruption without
physical inventory changes.

For multi-day operation a declared automatic lube makeup utility supplies up to
0.02L/s toward the50L reservoir target. It never clamps the reservoir or erases
loss: initial inventory+integrated makeup−integrated loss equals actual inventory,
with an independent1e-6 relative check. Actual makeup flow is public. This avoids
an unmaintained healthy reservoir emptying before the unchanged day-six fault
onset. The configurable generic packing default is now6parts/min/operator;
two operators and30s/50-part container changes yield10.714parts/min effective
capacity, supporting the maximum10SPM one-out preset.

Each catalog cause documents the same eight acquired evidence channels, with
physically supported directional/flat cross-effects. Shaft-minus-strip error is
recomputed from acquired encoder readings, rather than exported hidden error.
Inputs and calculation share one native acquisition node, preserving correlated
bad-quality intervals. Loop PV/SP/OP/MODE roles explicitly select native sensor
feedback and percentage scaling. The all-eight-cause catalog sweep retains the
full14day horizon, day6 onset,20s native scan and original effect thresholds.
No validation scope, adverse battery result, upstream test or schedule is waived.


R4 changes catalog cross-reference metadata only: a nonflat instrument supports
all candidates with the same documented signature. Individual evidence rows
make no elimination claim (`rules_out` is empty); diagnosis requires the full
measured evidence set and causal timing. This corrects overly broad R3 cross
references without changing physics, schedules, evidence expectations or gates.


R5 corrects two secondary evidence expectations after the full14day sweep
rejected their previously predicted flat scrap readings. Washer cold/low-flow
first alter product inspection/packing. Changing container/event timing changes
the integration/event split history; small loop/coil differences can accumulate
into reel/cycle phase shifts. A20s sample aliases the short scrap inventory pulse,
so its recorded mean can shift even with the same final stroke count. The R4
investigation found no blocked-state difference, first scrap change about16.4h
after the fault, at most one stroke difference transiently and identical final
159148stroke totals. `WI-SCRAP` is therefore documented as a secondary timing
phase/aliasing excursion (`erratic`), without a promised sign or independent scrap-defect claim.
This explicitly records long-horizon event-clock sensitivity; it is not proof
of real-machine upstream deterioration. Original failed flat checks remain
private adverse evidence. No physical equation, noise model, instrument class,
threshold,14day horizon or day-six onset changes in R5.
