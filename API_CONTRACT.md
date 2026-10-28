# Executable v1 module contract

`src/ekas_press_intelligence/contracts/api.py` defines Pydantic request models. `create_app()` in `api.py` binds FastAPI operations; `/openapi.json` is the generated machine-readable contract and `/docs` the interactive reference. API version is 1.0.0. Inputs reject unknown fields and nonfinite numeric values. Times are elapsed seconds within the selected synthetic dataset. Origin is carried in dataset context. Error responses preserve explicit scope/unavailability instead of substituting assets, periods or signals.

| Operation | Purpose |
|---|---|
| GET /v1/health | Version and synthetic-source status |
| GET /v1/assets | Relational asset catalog |
| GET /v1/signals | Signal metadata |
| POST /v1/observability/assess | Assess explicit available signals or named profile; persist result |
| GET /v1/sensor-gaps | Recompute profile sensor recommendations |
| POST /v1/benchmark/run | Generate seeded sparse/enhanced evidence and private evaluator truth |
| GET /v1/datasets/{run_id}/samples | Bound, downsampled public evidence window |
| POST /v1/rca/investigate | Investigate explicit run, asset and period through isolated worker |
| GET /v1/rca/cases/{case_id} | Persisted diagnosis with qualification |
| GET /v1/rca/cases/{case_id}/evidence | Provenance and sampled observations |
| POST /v1/benchmark/{run_id}/submit | Freeze claims and calculate temporal score |
| GET /v1/benchmark/{run_id}/score | Score only after submission |
| GET /v1/benchmark/{run_id}/truth | Reveal evaluator truth only after scoring |
| POST /v1/rca/cases/{case_id}/actions | Apply synthetic repair replay |
| POST /v1/rca/cases/{case_id}/verify | Compare server-held before/after evidence |

Run requests use seed (default 7), duration_s (10,800–604,800), and profile (`sparse` or `enhanced`). Investigation requests require run_id, asset_id, question, start_s and end_s. Claims carry interval, event_kind, failed_item, failure_mechanism, public evidence references, alternatives and governed diagnosis_state. They carry no hidden event ID. Verification selects action_id and ordered disjoint before/after windows, with sustained_duration_s. Work-order completion and client-supplied financial/verification metrics do not prove improvement.

Important error classes include 422 for validation or unavailable/ambiguous scope, 404 for missing resources, 409 for immutable submissions or a score/truth request before scoring, and 503 when diagnostic isolation is unavailable. Consult generated OpenAPI and response `detail.code` for actual endpoint behavior; not every error is represented as one universal envelope.

## Local operation and deployment boundary

After setup described in TEST_STRATEGY.md, run from the repository root:

```bash
EKAS_STATE_DIR=work/runtime python3 -m uvicorn ekas_press_intelligence.api:create_app --factory --host 127.0.0.1 --port 8765
```

Open the local origin in a browser. The UI calls the same-origin versioned API. `EKAS_STATE_DIR` selects SQLite state, including a distinct evaluator vault; preserve that directory for restart durability. Restrictive local file permissions and worker mounts separate truth from diagnosis. The API/evaluator process itself owns truth. This is a single-node synthetic prototype, without user authentication, tenant authorization, TLS termination, retention administration, backup orchestration or a real plant connector. Bind to loopback for local evaluation. Public hosting or plant deployment requires those controls and separate operational acceptance; this contract is not production deployment qualification.

## Additional governed surfaces

POST /v1/rca/cases/{case_id}/actions applies a declared synthetic mechanism correction. POST /v1/rca/cases/{case_id}/financial accepts nonnegative contribution assumptions, currency and their source; it measures case-window capacity opportunity and never derives savings. Generated contracts/openapi-v1.json provides named executable request/response schemas for every required operation. Optional source observations have their own schema and require explicit provenance, quality and synthetic labeling.
