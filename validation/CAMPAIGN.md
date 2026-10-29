# Full-duration synthetic campaign validation

Seed 7; 86400 seconds; evidence-only detection and OS-isolated RCA.

| Profile | Repeat digest | Physics | Windows | Detected | Correct | Unresolved | Incorrect | FP | Missed |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| sparse | True | True | 16 | 16 | 0 | 12 | 0 | 0 | 0 |
| enhanced | True | True | 16 | 16 | 12 | 0 | 0 | 0 | 0 |

Raw public datasets, compressed/regular historian exports, private truth and frozen claims remain in ignored `work/campaign/`. `campaign.json` retains hashes, artifact sizes/counts, per-class results, recovery and measured observability.

Measured diagnostic failures and unresolved cases remain visible; passing physics/determinism does not imply diagnostic or manual acceptance.
