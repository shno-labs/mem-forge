# Retire sources without erasing Support v2 history

Status: Accepted

## Context

Deleting a configured Source must remove it from the current product and stop
its knowledge from remaining usable. Support v2 also makes Source Projection,
Evidence, Plans, Reviews, Findings, and sync records immutable audit history.
Physically cascading those records would make ordinary Source removal rewrite
history, while rejecting removal leaves owners unable to clean up obsolete or
canary Sources.

## Decision

`DELETE /sources/{id}` is Functional Source Removal, not privacy erasure. The
operation acquires the existing Source activity fence and commits one atomic
relational transition:

- deactivate every active Support v2 assertion owned by the Source;
- remove only that Source's current `memory_sources` and Agent Knowledge
  projections;
- keep a Memory active when another active Support remains, otherwise retire it
  with reason `source_deleted` and remove its search/vector projection;
- mark the Source `retired`, disable scheduling, and remove current
  subscriptions, pins, and sync state;
- retain the Source tombstone plus Documents, Source Units and revisions,
  Observations and revisions, Evidence, derivations, lifecycle Plans, Reviews,
  Findings, sync runs/history, and immutable input snapshots.

Retired Sources are excluded from current discovery and cannot authorize new
work. Repeating the same DELETE is successful and has no further effect.
SQLite and HANA implement the same transition; HANA removes newly retired
vectors in the same user-visible transaction, while SQLite uses its durable
vector outbox.

Physical artifact or history erasure is a separate privacy/retention operation
and is not inferred from ordinary Source removal.

## Consequences

Source removal no longer conflicts with Support v2 history. Shared-support
Memories keep only surviving provenance, last-support removal becomes an
auditable retirement, and no source-type branch or migration-only bypass is
required. A future explicit restore operation would need new authorization and
revalidation; changing a retired row back to active is not part of this
decision.

## References

- [ADR 0011: Separate collection evidence from body materialization](0011-separate-collection-evidence-from-body-materialization.md)
- [Issue #381](https://github.com/shno-labs/mem-forge/issues/381)
