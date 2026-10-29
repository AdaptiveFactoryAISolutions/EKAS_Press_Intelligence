# 5. Connect an EKAS demo or backend

[Wiki home](Home.md) · [Next: help](06-Help-and-glossary.md)

## What the connection does

The simulation service stores the dataset. An EKAS backend reads its public measurements through an API (an agreed way for programs to exchange information). The UI displays the backend's response. The hidden answer key stays on the simulation service.

**EKAS UI → EKAS backend/adapter → native historian API**

The built-in workspace already uses that API. A separate EKAS demo is not connected merely because it looks similar or is open on the same computer. No specific external demo URL, editable source or target backend has been identified for this new integration. The steps below define the actual adapter work; they do not claim it is installed.

## User steps once an adapter has been installed

1. Ask the installer which EKAS environment is connected: training demo or backend test environment.
2. Select the saved connection in wizard Step 7.
3. Choose **Test connection** and require both an access check and a public sample-data check.
4. Run the simulation.
5. In EKAS open the dataset with the same recorded ID and configuration version.
6. Check that its source says **Synthetic simulation**, its dates match, and a selected measurement matches the built-in workspace, including unavailable readings.

These wizard controls are planned. Until available, a developer uses the API/SDK procedure below. Do not accept a successful health check alone as proof of UI integration.

## Developer: connect a backend today

1. Obtain the service URL from the installer. On the same host use `http://127.0.0.1:18728`; on another host use a verified HTTPS address. A container's `127.0.0.1` is that container, not the host service.
2. Obtain a server-issued **analyst** token for public investigation access. Keep generation/admin and evaluator credentials separate. Never embed these secrets in browser JavaScript.
3. Install Python 3.11+ in the EKAS backend environment. From this repository's root, run `python -m pip install ./sdk`. This installs the HTTP-only client, not the simulation engine.
4. Set `EKAS_HISTORIAN_URL` and `EKAS_HISTORIAN_TOKEN` in the backend's private environment/secret settings. These are adapter variable names used in this example; they are not an automatic discovery mechanism.
5. Run this read-only smoke check from the backend environment:

```python
import os
from ekas_historian_client import EKASNativeClient

with EKASNativeClient(
    os.environ["EKAS_HISTORIAN_URL"],
    token=os.environ.get("EKAS_HISTORIAN_TOKEN"),
) as service:
    print(service.health())
    datasets = service.datasets()
    for item in datasets:
        print(item["id"], item.get("status"))
    record = service.dataset("historianrca")
    # TIC-101.PV belongs to the original tank benchmark, not to the press.
    response = service.samples(
        "historianrca", ["TIC-101.PV"], source="raw", max_points=20
    )
    print(response)
```

6. Implement a backend adapter using `datasets()`, `dataset(id)`, `samples(...)` and `events(...)`. Obtain signal IDs from dataset metadata; do not map a tank temperature tag to a press measurement. Raw samples preserve recorded quality; a grid is a reconstruction, not a new measurement.
7. Map timestamps, units, quality and `truncated` explicitly to the EKAS UI contract. A missing/bad reading remains unavailable; it is not zero. Add a visible synthetic-data label and dataset ID.
8. Keep privileged job submission on trusted server routes. Use `submit_job`, retain its `id`, then poll `job(id)`. A wait timeout is not cancellation. Surface typed errors and terminal job failures in the UI.
9. Compare one interval from the UI with the native response. Test unreachable service, unauthorized role, unknown dataset, bad-quality data, truncated history, failed job and page reload during a running job. No fallback to fabricated success.
10. Record the target EKAS version, API contract, dataset ID, runtime/configuration identifiers and results. Only then label that environment connected.

The API schema is available at `/openapi.json`; the committed snapshot is [NATIVE_OPENAPI.json](../NATIVE_OPENAPI.json). Core routes are `GET /v2/health`, `GET /v2/datasets`, `GET /v2/datasets/{id}`, `GET /v2/datasets/{id}/tags`, `GET /v2/datasets/{id}/samples`, and `GET /v2/jobs/{id}`. Generation requires `POST /v2/jobs` with an authorized role and validated parameters.

## Frontend-only demos

Use a small trusted backend adapter to keep role tokens private and avoid assuming that cross-origin browser requests are enabled. Configure the demo to call its adapter. Do not weaken authentication or add unrestricted cross-origin access to make a screenshot work. A demo without editable source cannot be wired safely by changing a compiled bundle; obtain its source first.

## Ignition

Ignition integration is a separate data-source task. The current simulator does not read a customer gateway. Start with an agreed historical export and map actual tag names, units, quality and timestamps. An Ignition connection must never silently replace synthetic simulation or vice versa; the active data source must be visible.

For HTTPS, roles, private certificate authorities and deployment boundaries see [the integration contract](../EKAS_CLIENT_INTEGRATION.md) and [operations](../NATIVE_OPERATIONS.md).
