# 3. Guided configuration of the 1,500-ton line

[Wiki home](Home.md) · [Next: testing](04-Testing-and-results.md)

**Planned wizard: these screens are not available yet.** This page is the operating sequence the implementation must deliver. Until it is implemented and verified, there is no supported click sequence that fully configures this line in the current workspace.

Every screen has a title, “Step X of 8”, a short explanation, **Back**, **Next**, and **Save and exit**. Completed steps remain visible in a progress list. Returning resumes your saved draft. The wizard does not advance past an error; it explains the problem next to the field and takes you there. The standard preset fills in all required simulation assumptions.

## Step 1 — Choose your line

1. Choose **Generic 1,500-ton continuous-strip press line**.
2. Read the equipment diagram and the prominent **Simulation only** label.
3. Name the saved setup, for example “Training line”.
4. Choose **Next**.

Expected result: ten die stations and the complete reel-to-packing route are already selected. Tank and reactor examples cannot be mistaken for this preset.

## Step 2 — Confirm capacity and production speed

1. Confirm the displayed force unit. The proposed generic preset uses **1,500 metric tonnes-force**; this is an explicit assumption, not confirmed customer hardware. A US-short-ton rating is a different force.
2. Leave the initial operating speed at **8 strokes/minute** (a proposed training default).
3. Check the maximum: **10 strokes/minute**, also displayed as **600 strokes/hour**.
4. Leave **one finished part per completed production stroke** selected unless the tooling is multi-out. The preset allows ten strokes to fill the initially empty die before steady output begins.
5. Choose **Next**.

The application must reject an operating speed above 10 SPM for this preset. Nominal capacity is a limit, not the force applied on every stroke. Lower speed does not automatically make an excessive die load acceptable.

## Step 3 — Confirm material supply and feeding

1. Confirm the route: reel → loop pit → multi-roll straightener → feeder → die.
2. Keep the standard sample material and progression unless deliberately changing the training case.
3. Check the displayed units for strip width, thickness and progression. “Progression” means distance advanced per stroke.
4. Leave loop capacity, reel controls and feeder timing at the preset values for your first run.
5. Choose **Next**.

The numerical material/geometry defaults are to be documented and mechanically checked during implementation. They are not copied from the old 100 mm-pitch, 60-SPM model. The setup summary must show the actual values before you can run.

## Step 4 — Confirm die stations, lubrication and scrap handling

1. Inspect the ten numbered stations. The strip remains connected through the die.
2. Keep each station's standard part/strip presence sensing and forming-load model enabled.
3. Confirm lubrication zones and their pressure, flow and delivery confirmation.
4. Choose the installed scrap removal pattern: shaker chutes, motorized conveyors, or the preset combination.
5. Choose **Next**.

Station loads must come from declared tooling assumptions. A station force shown by the simulator must say whether it represents a direct sensor or a derived estimate; the application must not pretend ordinary corner tonnage sensors directly measure every station.

## Step 5 — Confirm washing and manual packing

1. Confirm that finished parts leave the last station onto the washer-feed conveyor.
2. Keep **hot-water spray washer** selected. Review water temperature, spray flow/pressure, tank level, heating, pump and conveyor settings.
3. Review the queue capacities between press, washer and packing.
4. Confirm packing workers, their nominal packing rate, parts per customer container and container-change time.
5. Choose **Next**.

Packing is manual. Its rate can vary; it is not an automatic packer. The model must show what happens when washing or packing is slower than stamping. Customer-container identity is simulated training data.

## Step 6 — Choose your test

1. For your first run choose **Healthy line — first test**.
2. Keep the recommended duration, repeat number and measurement settings.
3. For later tests, choose one named problem such as **Feeder slipping**. Read what is introduced and when. Keep known answers hidden in a blind investigation.
4. Choose **Next**.

The repeat number (seed) makes a case reproducible. A short practice run must be labeled **Practice**, not qualification. The engine must check that there is enough time for warm-up, transport and any selected fault; it must never silently shorten a test or omit a fault.

## Step 7 — Choose where to view the result

1. Keep **Built-in workspace** for the first run. It needs no external application.
2. To use an EKAS application, choose an administrator-configured connection. Do not type secret tokens into ordinary setup fields.
3. Choose **Test connection**. Read whether the service is reachable, access is allowed and sample evidence can be read.
4. Choose **Next** after all required connection checks pass.

An unavailable EKAS connection must not silently switch to fictional demo data. You may explicitly return to the built-in workspace. Backend integration instructions are on [Connecting EKAS](05-Connecting-EKAS.md).

## Step 8 — Review and run

1. Read the line diagram and settings summary. Confirm ten stations and maximum 10 SPM.
2. Inspect any assumptions and warnings. Each section has an **Edit** link back to its step.
3. Choose **Check configuration**. The server checks the complete combination of settings, required sensors, timing, capacity and available resources.
4. When the checks pass, choose **Run test** once.
5. The application opens the run-progress screen with your saved configuration version and job number.

If checks fail, the run button stays unavailable and a specific correction link appears. You must not need raw JSON or a terminal to complete this workflow.

## Tooltips and help

Each unfamiliar setting has a short explanation available by mouse hover and keyboard focus. Essential instructions, units, bounds and errors remain visible on the page. Touch users can open an adjacent help button. Longer explanations link to this wiki. This follows [Microsoft Fluent 2 tooltip guidance](https://fluent2.microsoft.design/components/web/react/core/tooltip/usage) and [Field guidance](https://fluent2.microsoft.design/components/web/react/core/field/usage); a tooltip is supplemental help, not the only place an important rule appears.
