# EKAS Native Historian Platform

The full-stack rebuild uses the actual complete [HistorianSim](https://github.com/ScottDuncanAI/HistorianSim) and [HistorianRCA](https://github.com/ScottDuncanAI/HistorianRCA) repositories. HistorianSim owns simulation, instruments, controllers, compression, native validation and scoring. This checkout adds durable jobs, authenticated role boundaries, a browser workspace and an independently installable EKAS HTTP client. The press extension evolves inside the native simulation pipeline.

**Qualification is in progress.** The press is not yet qualified for EKAS deployment. The [execution ledger](docs/FULL_STACK_EXECUTION_LEDGER.md) records passing checks, adverse results and outstanding gates. All process data is synthetic; no physical press, SmartPAC, PLC or customer historian is connected.

## Start here: plain-language wiki

The [user wiki](docs/wiki/Home.md) explains installation, configuration, testing and EKAS integration. The complete generic continuous-strip line now has an eight-step setup wizard, saved profiles, plain-language help and real native execution. On the development workstation open [Guided press setup](http://127.0.0.1:18729/#setup). Follow the [press-line installation guide](docs/wiki/02-Installation-and-first-use.md) for a fresh installation. This is unqualified practice: all native findings are retained and engineering ledger failures still block output registration. The separate reference service remains on port 18728.

## Start the native reference workspace

Use Linux, Python3.12, Bubblewrap, g++ and OpenSSL. Bubblewrap must support the required namespaces; the blind workflow fails closed if isolation is unavailable. Use the `full-stack-foundation` candidate branch in [draft PR2](https://github.com/AdaptiveFactoryAISolutions/EKAS_Press_Intelligence/pull/2), with both complete submodules. The public default branch still contains the earlier prototype.

```bash
git clone --recurse-submodules --branch full-stack-foundation https://github.com/AdaptiveFactoryAISolutions/EKAS_Press_Intelligence.git
cd EKAS_Press_Intelligence
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps -e 'vendor/HistorianSim[dev]' -e '.[dev]'
bash scripts/verify_upstreams.sh
.venv/bin/python scripts/prepare_reference_runtime.py
export EKAS_NATIVE_RUNTIME="$PWD/work/reference-runtime"
export EKAS_NATIVE_STATE_DIR="$PWD/work/native-service"
export EKAS_NATIVE_BLAS_THREADS=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
.venv/bin/python -m uvicorn ekas_press_intelligence.native.api:create_native_app \
  --factory --host 127.0.0.1 --port 18728
```

Open [the native workspace](http://127.0.0.1:18728). It exposes the original published historian, both native reference plants, full configuration choices, actual asynchronous native operations, raw/grid observations, process diagrams, frozen submissions and evaluator scoring. Missing provider access and unavailable keys produce explicit failures. The original HistorianRCA private key was not published; its score remains `EXTERNAL_SCORING_REQUIRED`.

The separate press runtime is prepared with `scripts/prepare_native_runtime.py`. It includes the documented generic patches and press model while preserving the vendor trees. It must pass the approved engineering gates, 513-case matrix and six full90-day runs before press qualification can be claimed. Changing source requires a newly verified runtime and process restart; imported native source is never hot-swapped.

## EKAS and deployment

[EKAS client integration](docs/EKAS_CLIENT_INTEGRATION.md) describes the standalone `ekas-historian-client` distribution in `sdk/`, which depends only on httpx. EKAS connects through HTTP; it does not receive the simulator or private answer keys. [Native operations](docs/NATIVE_OPERATIONS.md) covers role credentials, HTTPS, resource limits, durable state, cancellation, immutable claims and backup/restore.

Sparse/enhanced exports derive from the same physical run. Retained observations, acquisition quality and source hashes remain auditable. Sparse evidence may leave causes unresolved; the application does not fabricate missing evidence or a confident diagnosis.

## Verify

```bash
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/run_native_tests.py core
.venv/bin/python scripts/run_native_tests.py browser
.venv/bin/python scripts/run_native_tests.py physics
.venv/bin/python scripts/run_native_tests.py upstream
```

The native CI runs these layers without accepting empty or skipped required layers. Full-duration physics, data-solvability and independent blind evaluation are separate qualification evidence; ordinary unit-test success does not substitute for them. Preserve adverse findings when repairing a source epoch.

## Upstream preservation and historical work

HistorianSim is pinned to `14e616c382a9db8026cbb4ab86bdd803d56ca72e` (MIT); HistorianRCA to `8d12a821395ce5f72e464dc78cc2c10d05cbb9ed` (CC BY4.0). Complete repositories, history, data, tests, documentation, attribution and licenses remain preserved. Authored process diagrams are explicitly identified as engineering overlays.

[Upstream provenance](UPSTREAM_PROVENANCE.md) · [Licenses](LICENSES.md) · [Approved native design](docs/superpowers/specs/2026-10-28-upstream-full-stack-design.md) · [Press design](docs/superpowers/specs/press-line/DESIGN.md)

The earlier shallow prototype remains available as [historical work](LEGACY_PROTOTYPE.md). Its service on18727 and its acceptance evidence are separate from this native rebuild. No merge, production activation or final acceptance has occurred.
