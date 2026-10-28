# ADR-0004 — OS boundary for diagnostic truth separation

Status: Implemented architectural decision; milestone acceptance remains separate.

## Decision

Run standard-library diagnosis in a Bubblewrap worker with unshared namespaces, cleared environment and individually mounted public modules. Pass public evidence through stdin; never mount simulator, stores or repository.

## Reason

The evaluator keeps truth in a separate SQLite vault. Folder naming and private Python attributes are not access controls.

## Consequences and limits

Linux Bubblewrap/user namespaces are mandatory. The service/evaluator remains trusted and owns truth; isolation does not protect against compromise of that process.
