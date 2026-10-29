# 1. What works today

[Wiki home](Home.md) · [Next: installation](02-Installation-and-first-use.md)

A simulation is a virtual machine. It produces measurements from modeled equipment behavior. It does not operate your real press.

| Feature | Available now? | Meaning |
|---|---|---|
| Native historian browser, saved jobs and public measurements | Yes | You can explore existing datasets and run supported native operations. |
| Reference tank and reactor simulations | Yes | Useful for learning the workflow; they are not press models. |
| Earlier experimental stamping model | In a separate prepared runtime | It has a different design basis and incomplete qualification. |
| Your complete 1,500-ton line, ten stations, washer and packing | Not yet | Defined in the new design; not created by changing a label. |
| One-screen-per-step press configuration | Not yet | The required wizard is described in this wiki and design. |
| HTTP client for another application | Yes | A developer can read datasets through the backend API. |
| Existing EKAS demo automatically connected | No | It needs an explicit adapter and an end-to-end check. |
| Customer Ignition data connected | No | No customer gateway or real press is connected. |

The current local workspace is normally at `http://127.0.0.1:18728/`. Its navigation includes **Dataset explorer**, **Native workflows**, **Durable jobs**, **Investigation & submission**, **Evaluation**, and **Sources & capabilities**. These are current labels. The proposed beginner wizard is a new entry point, not a renamed raw settings form.

## What a result means

- **Succeeded:** the requested job completed. Read the result to understand what was checked.
- **NATIVE_VALIDATED:** the native checks passed for that dataset. This does not certify a real press or prove diagnostic accuracy.
- **UNVALIDATED:** the record has not passed the required native qualification. Sparse/enhanced exports can carry this status even when their source run passed checks.
- **Failed:** keep the error and evidence. Do not treat missing output as a successful empty dataset.
- **EXTERNAL_SCORING_REQUIRED:** the local system lacks the original benchmark's private answer key. It cannot invent a score.

The earlier press model passed some engineering gates but failed an encoder measurement check. That remains recorded. The newly requested line requires a new configuration and evidence; it does not inherit qualification from tank tests or the older press model.
