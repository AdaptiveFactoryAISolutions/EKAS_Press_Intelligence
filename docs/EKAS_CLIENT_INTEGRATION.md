# EKAS integration through the native HTTP boundary

The separate client distribution requires Python3.11+ and httpx. It imports no simulator, local datasets, provider broker or answer key. Install the `sdk/` project from this checkout in the EKAS application environment; install the full server checkout separately on its service host. Both packages use the same client source, not copied implementations.

```python
import os
from ekas_historian_client import EKASNativeClient, NativeAPIError

with EKASNativeClient(os.environ['EKAS_HISTORIAN_URL'],
                      token=os.environ['EKAS_HISTORIAN_TOKEN']) as historian:
    capabilities = historian.capabilities()
    datasets = historian.datasets()
    evidence = historian.samples('historianrca', ['TIC-101.PV'],
                                  source='raw', max_points=1000)
```

Use a separate server-issued role credential for each trusted application actor. Administrator credentials permit generation and private engineering access; they must never be used for a blind analyst. HTTPS certificate verification is always enabled for remote connections. A private deployment CA can be supplied through the standard `SSL_CERT_FILE` environment variable. Embedded URL credentials, remote plaintext HTTP and redirects are rejected.

Long operations return durable job IDs. Keep the ID in EKAS application state and call `job(id)` after a disconnect or restart. `wait_for_job` timing out raises `CLIENT_WAIT_EXPIRED`; it does not cancel the server operation. Treat failed/cancelled/interrupted terminal states as failures and retain their evidence. Do not convert a health response or `NATIVE_VALIDATED` dataset into an engineering qualification claim.

`export_observability(dataset_id, 'sparse')` submits an information restriction of an existing run. It does not regenerate physics or recover withheld channels. `events(dataset_id, source='journal')` retrieves bounded measured edges, including unavailable acquisitions; scan status is a separate source. Honor `truncated`, quality codes and null counts rather than filling gaps.

Freeze the analyst's free-text CSV with `freeze_submission`. Independent evaluation uses a separate authorized evaluator and the immutable frozen digest. The native scorer preserves its six-hour matching tolerance. The published HistorianRCA record has no local private answer key: `EXTERNAL_SCORING_REQUIRED` is an explicit unresolved dependency, not an empty score.

Actual local HTTPS, certificate rejection, private-CA trust and role enforcement are covered by `tests/test_native_tls.py`. Production reverse proxy, identity lifecycle and deployment-specific EKAS application wiring still require target-environment qualification.
