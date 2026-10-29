# Native stack operations — qualification in progress

This checkout contains the original prototype and the new native stack. The native stack uses the pinned complete HistorianSim source and the original HistorianRCA public record. It is not yet fully qualified for EKAS deployment. Consult FULL_STACK_EXECUTION_LEDGER.md for outstanding gates.

## Install and verify

Use Python3.12 with a private virtual environment. Install requirements-lock.txt, then install this checkout editable without changing the locked dependencies. Initialise both complete submodules with `git submodule update --init --recursive`; run `bash scripts/verify_upstreams.sh` before starting a server. The verifier checks exact revisions, complete history and clean source.

`python scripts/prepare_reference_runtime.py` creates work/reference-runtime from immutable upstream blobs plus the explicitly authored reference diagrams. `python scripts/prepare_native_runtime.py` creates work/native-runtime from the same source with reviewed generic patches and the press extension. Each includes a source manifest; server and worker verify actual source hashes before importing. Restart when changing source; an already imported runtime cannot be switched in process.

## Local service

Set EKAS_NATIVE_RUNTIME to the absolute prepared runtime directory and EKAS_NATIVE_STATE_DIR to an absolute private state directory. Start `python -m uvicorn ekas_press_intelligence.native.api:create_native_app --factory --host 127.0.0.1 --port 18728`. The browser workspace is at `/`; the typed contract is `/openapi.json`. Loopback mode without configured tokens is a trusted engineering session with administrator access. It is not a blind analyst session.

For role testing, configure EKAS_NATIVE_TOKENS as a JSON object mapping separate secret tokens to analyst, evaluator and admin. Supply tokens through a private environment file or secret manager, never repository files, command history or URLs. The browser sends the chosen bearer token. Analyst access excludes generation schedules/configuration and answer keys. Evaluator reports, summaries and key artifacts require a frozen submission. Administrator access is for trusted engineering and includes source/configuration access.

Remote deployment requires EKAS_NATIVE_LOCAL_ONLY=0, configured role tokens, and HTTPS terminated by a trusted reverse proxy. Bind the application to a protected private listener. Disable proxy-header trust unless the peer is an explicitly trusted proxy; loopback development is checked against the socket peer, not the Host header. Restrict filesystem access to the service account and retain state directory mode0700/database0600. Actual local TLS certificate rejection/private-CA trust and role checks passed; remote proxy deployment remains unqualified. The standalone HTTP-only SDK and its boundary are described in EKAS_CLIENT_INTEGRATION.md.

## Jobs and data

POST `/v2/jobs` with an operation, strict parameters and optional idempotency key. Poll the returned job ID. A client polling timeout leaves the durable server job running; explicit cancellation requires administrator authority. Concurrent managers share one SQLite claim guard. Qualified generation requires passing native validation; failures retain adverse artifacts. NATIVE_VALIDATED means the native checks passed for that run; it does not imply press engineering qualification or EKAS readiness.

The guided `stamping_line` workflow explicitly creates unqualified practice. Its native battery still runs and all findings are retained. With passing engineering accounting, the result can register as UNVALIDATED / UNQUALIFIED_PRACTICE; it never registers as qualified, even if the battery passes. Engineering accounting failures block registration. Draft revisions, idempotency and immutable configuration/runtime bindings are documented in the [guided-line evidence](validation/guided-1500t-line.md) and [wiki](wiki/Home.md).

The original reference dataset is `historianrca`. Its private key was not published, so scoring returns EXTERNAL_SCORING_REQUIRED. Generated datasets retain their private key on the server. Freeze a free-text CSV through `/v2/datasets/{id}/submissions`; a separate evaluator records item/mechanism judgments, then the original native scorer applies its matching and six-hour timing rules. Analyst self-adjudication is rejected. Frozen submissions and judgments cannot be edited in place.

Raw samples retain recorded quality. Regular grids are the original native reconstruction, including nulls for bad quality. Bounded queries return an explicitly truncated prefix when appropriate; use a chosen time interval, download or the full-range native plot for long records.

Administrator operation `observability_export` accepts a registered dataset_id and profile `enhanced` or `sparse`. It streams the existing public records into a separate artifact set without re-simulation, preserving retained values, timestamps and quality. Native plant withholding metadata determines availability; callers cannot supply arbitrary paths or plants. Derived exports keep the parent key association and are labelled UNVALIDATED information restrictions. SOURCE_AVAILABILITY.json binds their input/output hashes and declares withheld channels. Sparse exports do not promise unique diagnosis and cannot be upgraded to enhanced by inventing withheld channels.

GET `/v2/datasets/{id}/events` distinguishes measured journal edges (`source=journal`) from native historian scan status (`source=status`). Journal timestamps are quantized to1ms; unavailable acquisitions retain masked code/count and their recorded quality. No private conservation ledger, pitch truth or rejection detail is exposed by this route.

## Capacity and numerical threads

`EKAS_NATIVE_BLAS_THREADS` is an explicit integer1..64, default1. Workers set OPENBLAS_NUM_THREADS, OMP_NUM_THREADS and MKL_NUM_THREADS before numerical imports. A single thread avoids severe native autocorrelation oversubscription; it does not replace the original numerical checks. Set the same numerical environment before starting the server.

`EKAS_NATIVE_MAX_ESTIMATED_BYTES` defaults to12000000000 and bounds the native preflight memory estimate. Requests above it fail with CAPACITY_EXCEEDED; the server never silently shortens duration or changes scan/resampling periods. An explicitly larger limit may be required for the full365-day profile. Patched resampling separately bounds requested grid rows with HISTORIANSIM_MAX_GRID_ROWS, default10000000.

Optional `EKAS_NATIVE_MAX_RSS_BYTES` and `EKAS_NATIVE_MIN_AVAILABLE_BYTES` enable positive-byte Linux worker-memory and host-reserve checks. Unavailable telemetry or exceeded limits fail the job and retain partial, unqualified artifacts. These are monitored process safeguards, not an exclusive kernel memory reservation. Choose limits for the host's other workloads; never reclaim or stop unrelated processes to make a run fit.

## Verification identities

The protected stock HistorianSim suite remains unmodified and its173-test result is recorded separately. The prepared-runtime suite is identified as `native_patched_upstream_compatibility`; it includes the press's native catalog parameterizations. Patch0010 changes exactly two layout-test assertions to account for upstream's documented optional PFD files and additionally verify their exact source→dataset→challenge bytes. It retains key-leakage and native audit checks and changes no physical, noise, solvability or scoring threshold. The source/test/pytest-configuration digests and patch application changes are bound in the runtime manifest. A passing patched suite must not be described as an unmodified stock-suite result.

Default upstream activation compares package files with pinned committed blobs, including files Git would ignore. It rejects unknown executable files and source-root siblings; only declared editable-install metadata and non-symlink package caches are permitted. A new private import-cache prefix prevents reuse of those runtime caches. Prepared reference and hybrid modes independently verify their derived package contents and source-root boundaries. A clean Git status alone is insufficient source authentication.

## Evidence runtime

The evidence namespace uses the selected interpreter and matching standard library, rather than assuming `/usr/bin/python3` has the same ABI as installed numerical extensions. Startup uses `-I -S`, an explicit dependency allowlist and read-only standard-library children; site/dist-packages and customization modules are excluded, and escaping standard-library symlinks fail closed. Actual transport verifies the Python major/minor ABI and imports NumPy, Pandas and PyArrow under the namespace. Existing read-only system loader/library mounts remain; this is not a claim that the namespace contains only the listed Python files. Home, repository, generated keys, provider credentials and network access remain denied by the tested boundary.

## Backup and restore

Stop accepting new work and wait for jobs to finish or explicitly cancel them. Run `python -m ekas_press_intelligence.native.backup create /absolute/state /absolute/new-snapshot`. The snapshot transaction blocks database writers and refuses active jobs. It includes private evidence, keys, frozen submissions and an integrity manifest; protect it like the live state.

Stop the service before restore. Preserve the existing directory elsewhere, then run `python -m ekas_press_intelligence.native.backup restore /absolute/original-state /absolute/snapshot`. Restore requires the original absolute state path and an empty target, verifies every file hash and SQLite integrity, and refuses symlinks. It does not overwrite a live state directory or silently relocate internal evidence paths. Restart with the same verified runtime and configuration after restoring.
