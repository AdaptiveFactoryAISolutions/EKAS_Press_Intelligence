# Plain report language review

Reference: the user-supplied ASD-STE100 Issue 9, dated January 15, 2025.
The standard is not copied into this repository.

## What this review covers

The user approved the plain report's format and explanations.
The application now combines fixed explanatory sentences with facts from each saved run.
It does not ask a language model to invent the report or a cause for a result.
The report is for the administrator's practice workflow, not blind evaluation.

## Rules applied

- Part 1, rules 1.1 to 1.4: use the dictionary as the reference for word choice and meaning.
- Rules 1.5 to 1.11: identify technical nouns and use a consistent name for each concept.
- Rule 1.14: use American English spelling.
- Rules 3.2 to 3.6: prefer simple tenses and active voice.
- Rules 4.1 to 4.5: give clear sentences with necessary articles and connecting words.
- Rules 5.1 to 5.3: keep instructions short and use one action per instruction.
- Rules 6.1 to 6.6: introduce facts gradually; keep a paragraph on one topic.

The descriptive sentence limit is 25 words. The procedural limit is 20 words.
The paragraph limit is six sentences. A simple token screen is not the formal section 8 word count.

The report starts with the result and its use limits. It then gives the equipment, settings, time, graphs, counts, checks, actions, terms, and sources.
Technical identifiers are in the expandable evidence section rather than the main explanation.

## Technical noun register

These terms are proposed for this project. This document does not claim company terminology approval.

| Term | Meaning in this product |
| --- | --- |
| Simulation | A computer test of a process, separate from real equipment. |
| Model | The software description of equipment and behavior. |
| Press stroke | One press cycle. |
| Die station | One position in the die where the strip undergoes a process step. |
| Loop pit | A space that holds slack strip. |
| Feeder | Equipment that moves a length of strip into the press. |
| Signal | One measured or calculated value. |
| Primary reading | An original stored observation rather than a reconstructed grid value. |
| Quality code | The recorded condition of a reading, not part quality. |
| Packing queue | Parts that wait for packing. |
| Target | The configured control value, separate from an acceptance limit. |
| Validation | Checks of the model or its data, each with a limited scope. |
| UTC | The reference time used in the stored files. |
| Kilonewton | A unit of force. |
| Ampere | A unit of electric current. |

Unit names, file names, product names and recorded check identifiers remain exact where traceability needs them.
The report explains a check before it exposes its recorded technical name.

## Factual controls

- Never replace unknown check results with a pass.
- Never replace missing/bad readings with zero or an earlier good value presented as the final value.
- Never claim a fault cause from the selected practice case.
- Do not infer cleaning quality from water temperature.
- Do not infer real equipment accuracy from an internal quantity check.
- Separate rejected parts from parts still in the line.
- Use a real-unit graph for each measurement type. Do not stretch tiny changes to a shared normalized height.
- Show the observation period separately from the computer job dates.

## Remaining language review

The report explicitly states `NOT_FULLY_REVIEWED` in the API and gives the same scope in the UI.
A complete word-by-word meaning/part-of-speech review remains open, including dynamic units, captions, and selected-point explanations.
The technical noun register still needs a project terminology disposition.
No automated checker or independent STE language specialist has certified conformance.
Do not label the report ASD-STE100 compliant on the basis of short sentences alone.
