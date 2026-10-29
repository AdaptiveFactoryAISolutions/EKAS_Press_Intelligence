# EKAS press simulator: start here

This wiki is stored with the code so everyone sees instructions for the same version. You do not need a separate GitHub Wiki checkout. Start with the route below that matches your task.

| I want to… | Open this page |
|---|---|
| Understand what is ready | [What works today](01-What-works-today.md) |
| Install or open the system | [Installation and first use](02-Installation-and-first-use.md) |
| Configure our 1,500-ton line | [Guided press setup](03-Guided-press-setup.md) |
| Run and understand a test | [Testing and results](04-Testing-and-results.md) |
| Connect an EKAS demo or backend | [Connecting EKAS](05-Connecting-EKAS.md) |
| Solve a problem or understand a word | [Help and glossary](06-Help-and-glossary.md) |

**Current status, 29 October 2026:** the native reference workspace works. The complete 1,500-ton, ten-station line and its beginner setup wizard are specified, but are not implemented or qualified yet. Do not mistake the older press model for this complete line. Each page distinguishes current instructions from planned screens.

The intended experience is simple: select the standard line, follow one screen at a time, check the summary, run a test and inspect the result. Ordinary users should not edit program code, environment settings or JSON (a developer's structured settings format).

Your line, in order:

**Coil reel → slack loop pit → multi-roll straightener → feeder → continuous strip through ten die stations → finished-part conveyor → hot-water spray washer → manual packing into customer containers.**

Offal leaves separately through shaker chutes or motorized scrap conveyors. The press capacity is described as 1,500 tons; the exact force unit must be visible in the configuration. Maximum speed is **600 strokes/hour = 10 strokes/minute**, not 600 SPM. Ten stations do not imply ten finished parts per stroke.

[Detailed implementation design](../superpowers/specs/2026-10-29-guided-1500t-line-design.md) · [Technical operations](../NATIVE_OPERATIONS.md) · [Evidence ledger](../FULL_STACK_EXECUTION_LEDGER.md)
