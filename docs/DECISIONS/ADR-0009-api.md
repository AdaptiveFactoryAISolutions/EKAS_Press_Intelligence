# ADR-0009 — FastAPI executable v1 API

Status: Implemented architectural decision; milestone acceptance remains separate.

## Decision

Bind Pydantic requests and response contracts through FastAPI and generate OpenAPI from actual routes. Validate intervals, explicit scopes and nonfinite inputs.

## Reason

A prose-only module contract cannot enforce shape or expose machine-checkable operation coverage.

## Consequences and limits

Some response payloads are extensible to retain structured engine evidence. Authentication and public production hosting remain outside this local prototype.
