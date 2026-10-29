# 6. Help and glossary

[Wiki home](Home.md)

## When something goes wrong

| What you see | What to do |
|---|---|
| Browser cannot connect | Confirm the address with the installer and whether the service is running. On another computer, `127.0.0.1` points to that computer. |
| No press option | The running reference runtime contains tank/reactor examples. The full requested press preset is not implemented yet; renaming a tank will not create it. |
| Access denied / 403 | Use the credential for your role. Ask the administrator rather than borrowing an admin credential for blind analysis. |
| Invalid parameters | Read the exact field error. In the current expert form inspect the request preview. The planned wizard will link the error to the relevant screen. |
| CAPACITY_EXCEEDED | Ask the installer to review memory requirements and resource limits. Do not shorten a qualification run silently. |
| A job stays queued | Check **Durable jobs**; another job may own the single worker. Do not submit repeated copies. |
| Waiting timed out | Reopen the same job number. The server job may still be running. |
| Validation failed | Retain the result. Passing other checks does not cancel the failure. Ask the maintainer to investigate the specific cause. |
| Missing or flat readings | Inspect quality and source availability before inferring a machine fault. A bad/missing reading is not a measured zero. |
| Only early history appears | The query may be truncated. Set a smaller UTC interval or use a complete public download/native plot. |
| No event journal | Some datasets do not contain one. This does not prove no events occurred. |
| No score | The original published benchmark lacks a local private answer key; generated submissions also need independent evaluation. |
| Provider unavailable | Check authorized provider installation/access with the maintainer. Evidence browsing can still be used without a provider run. |
| My setup differs from someone else's | Compare configuration version, dataset ID, seed and runtime source. Do not compare only the display names. |

For a useful support report, provide the page name, job/dataset ID, error code, time and expected behavior. Omit passwords, role tokens, private answer keys and customer-confidential data.

## Common words

| Word | Plain meaning |
|---|---|
| SPM | Strokes per minute. This line's maximum is 10 SPM. |
| Progression / pitch | Distance the strip advances during each feed. |
| Station | One forming position in the die; not an extra finished part per stroke. |
| Offal | Scrap material separated from the useful parts. |
| Buffer | Space/material held between operations so they need not move at identical rates. |
| Tag / signal | A named measurement or equipment status. |
| Dataset | A saved collection of measurements and related evidence. |
| Job | A task running on the server, with its own tracking number. |
| Seed / repeat number | A number that helps repeat the same simulated case. |
| Raw | Recorded acquisitions with their original quality information. |
| Grid | Data arranged on regular time intervals using the native reconstruction rules. |
| Quality | Whether an acquisition is usable, uncertain or bad; not product quality. |
| Tonnage | Forming force; always check which ton/tonne-force unit is meant. |
| Preset | A named, versioned set of settings already filled in. |
| Validation | Specific checks against declared rules; it is not blanket real-world certification. |
| Backend | The server that performs work and stores results. |
| UI | The screens a person uses. |
| API | The agreed interface programs use to exchange requests and results. |
| Blind investigation | Investigation without access to the hidden simulated answer. |

## Maintaining this wiki

Update the wiki in the same change as the behavior it describes. Mark planned screens as available only after their browser and backend checks pass. Keep visible labels, supported limits and examples synchronized with the actual application. Preserve previous adverse evidence; do not rewrite a failed qualification as a pass.
