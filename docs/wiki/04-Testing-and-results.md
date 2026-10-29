# 4. Run a test and understand the result

[Wiki home](Home.md) · [Next: connect EKAS](05-Connecting-EKAS.md)

## Learn the current workflow with a reference model

This is a tank example. It verifies that you understand job submission and evidence viewing; it is not your press test. You may skip generation and explore an existing dataset instead.

1. Open **Native workflows** as an authorized administrator.
2. Set **Operation** to `generate`.
3. Set **Plant** to `heated_stirred_tank` and **Scenario** to `tank-clean`.
4. Set **Profile** to `quick` and **Seed** to `7`.
5. Leave **Native parameters / overrides (JSON object)** as `{}`. The planned press wizard will remove this technical field from the beginner path.
6. Read **Request preview**. It should contain operation `generate`, scenario `tank-clean`, profile `quick`, seed `7`. Do not use this example to represent a press.
7. Select **Queue native job** once.
8. Open **Durable jobs**, find the new job number and watch its recorded progress. Browser reload does not cancel it.
9. If it fails, read the error and retain the evidence. Do not disable validation to obtain a green result.
10. If successful and registered, open its dataset from the job, or use **Refresh datasets** in the explorer and select the new record.
11. Query a measurement and inspect its quality, units and dates.

The `quick` profile is for practice. A clean scenario means no injected fault, not perfectly flat measurements; normal variability remains. Duration, runtime and validation outcomes depend on the selected model and host. Do not promise a fixed completion time.

## Planned first press test

After the new line and wizard pass their checks:

1. Complete [the eight setup steps](03-Guided-press-setup.md).
2. Run **Healthy line — first test**.
3. Check the flow from coil consumption to completed parts, washing, packing and scrap.
4. Check that actual speed stays within 10 SPM and that station occupation reflects die fill and transport delays.
5. Check that total production is accounted for across in-process parts, rejects, good parts and packed parts. Ten stations must not multiply production by ten.
6. Run a copy with **Feeder slipping**. Compare commanded feed, measured shaft travel, measured strip progression, station sensing and production effects.
7. Run downstream restriction examples: scrap blockage, washer stoppage and slower packing. Check queue growth and recorded stop reasons.
8. Save the configuration version, job number, run summary and relevant public evidence.

These are acceptance requirements, not results already observed on the new line. The older press's qualification plan must be revised explicitly for 10 SPM; the old 45/60/75-SPM matrix cannot qualify this line.

## Investigation and paid provider runs

Exploring measurements does not require asking an external AI provider. **Queue blind analysis** and **Queue independent evaluation** can send authorized evidence to a configured provider and incur cost. Use them only under the agreed data-sharing and budget authorization. Do not enter private customer data into a training run without the customer's agreed handling arrangements.

For a blind test, the analyst sees public measured evidence and not the simulator's hidden fault schedule. A separate evaluator judges frozen claims. A completed provider job is not proof that a proposed cause is correct. Frozen submissions cannot be edited in place; use a new run/dataset for a new trial.

## Save, cancel and repeat

Use the recorded job number to return to a run. A client timeout only means the client stopped waiting; check the existing job before submitting again. Administrators can request cancellation in the job controls; wait for the recorded terminal status. Cancelled or interrupted output is not qualified data. Repeatable comparisons need the same configuration version, seed and runtime source; changing one must be visible in the result.
