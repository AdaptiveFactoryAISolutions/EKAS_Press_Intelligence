# ADR-0001 — Independent Repository and Contract-Only Integration

Status: Accepted

## Decision
Build EKAS Press Intelligence & RCA in its own repository. Do not develop it inside EKAS Demo UI. Future integration occurs only through a versioned module API.

## Reason
The simulator and RCA work is experimental, computationally different from the UI, and must not destabilize or delay the current Demo UI certification.
