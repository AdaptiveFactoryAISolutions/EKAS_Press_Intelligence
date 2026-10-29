# 1. What works today

[Wiki home](Home.md) · [Next: installation](02-Installation-and-first-use.md)

A simulation is a virtual machine. It produces measurements from modeled equipment behavior. It does not operate your real press.

| Feature | Available now? | Meaning |
|---|---|---|
| Native historian browser, saved jobs and public measurements | Yes | You can explore existing datasets and run supported native operations. |
| Reference tank and reactor simulations | Yes | Useful for learning the workflow; they are not press models. |
| Earlier experimental stamping model | In a separate prepared runtime | It has a different design basis and incomplete qualification. |
| Your complete generic 1,500-ton line, ten stations, washer and packing | Yes, for practice | A distinct connected native plant, with conservation tests and unresolved native measurement findings. |
| One-screen-per-step press configuration | Yes | Eight screens, filled-in defaults, help, validation, saved progress and immutable runs. |
| HTTP client for another application | Yes | A developer can read datasets through the backend API. |
| Existing EKAS demo automatically connected | No | It needs an explicit adapter and an end-to-end check. |
| Customer Ignition data connected | No | No customer gateway or real press is connected. |

Use `http://127.0.0.1:18729/#setup` for the configured press line. Navigation includes **Guided press setup**, **Dataset explorer**, **Native workflows**, **Durable jobs**, **Investigation & submission**, **Evaluation**, and **Sources & capabilities**. Start in guided setup; the expert native form is not needed for ordinary press configuration.

## What a result means

- **Succeeded:** the requested job completed. Read the result to understand what was checked.
- **NATIVE_VALIDATED:** the native checks passed for that dataset. This does not certify a real press or prove diagnostic accuracy.
- **UNVALIDATED:** the record has not passed the required native qualification. Sparse/enhanced exports can carry this status even when their source run passed checks.
- **Failed:** keep the error and evidence. Do not treat missing output as a successful empty dataset.
- **EXTERNAL_SCORING_REQUIRED:** the local system lacks the original benchmark's private answer key. It cannot invent a score.

The earlier press model passed some engineering gates but failed an encoder measurement check. That remains recorded. The new line has its own source-bound evidence and does not inherit qualification from it. Its unchanged native battery reports deterministic encoder coloring, short-history retention and (for healthy cases) a fault/twin divergence expectation. Practice runs retain these findings and register as **UNVALIDATED**, even when their engineering accounting passes. Engineering accounting failures still block registration.
