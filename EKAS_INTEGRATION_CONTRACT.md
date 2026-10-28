# EKAS integration boundary

Canonical executable contract: [contracts/openapi-v1.json](contracts/openapi-v1.json), generated from contracts/api.py and api.py. Human reference: API_CONTRACT.md. Optional source-provider schema: contracts/source-observation-v1.json.

EKAS may later consume this module over the versioned /v1 API. It must not import UI components, simulator objects, SQLite files, private configuration, evaluator truth or upstream implementation internals. No integration with EKAS_Demo_UI has been performed.

Consumers must preserve explicit asset/period/run scope, acquisition quality, missing observations, alternative dispositions, governed state and qualification. Unsupported/ambiguous requests remain typed failures rather than default substitutions. A score is not verified physical causality; a recorded action is not a successful result; opportunity is not savings.

The current transport is a local single-user HTTP prototype. Authentication, deployment authorization, tenant boundaries and production EKAS integration require a separate qualified deployment. All present data is synthetic.
