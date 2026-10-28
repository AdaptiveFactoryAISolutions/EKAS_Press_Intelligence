# ADR-0008 — SQLite resources and immutable benchmark records

Status: Implemented architectural decision; milestone acceptance remains separate.

## Decision

Persist JSON resources and append-only audit history in SQLite with database triggers protecting scored submissions/scores and audit records. Keep evaluator vault distinct.

## Reason

Restart durability and immutable scored submissions require more than process memory. SQLite suits a single-node prototype.

## Consequences and limits

No distributed storage, external backup or multi-tenant access boundary is implemented. Protect and back up the complete state directory before operational use.
