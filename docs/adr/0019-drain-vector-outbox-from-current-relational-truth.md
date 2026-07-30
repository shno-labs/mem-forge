# Drain the Memory-vector outbox from current relational truth

Status: Accepted (2026-07-30)

## Context

Memory lifecycle transactions commit relational state and a durable vector
outbox row together. The vector provider remains an external projection, so
delivery is necessarily at least once and must not roll back an authoritative
relational commit.

The original implementation attempted one bounded outbox batch from producer
paths such as Source Projection application and source-run completion. It did
not give the shared worker an independent recurring consumer. A plan producing
more than one batch could therefore leave untouched rows indefinitely after
the source run became terminal.

The stored operation also described the state at publication time. If a later
lifecycle plan retired a Memory before an earlier `upsert` was delivered, the
consumer treated the now-nonactive Memory as an error. Repeating that historical
operation would be unsafe because it could restore vector visibility that the
relational lifecycle had already removed.

## Decision

An outbox row is a durable request to converge one Memory's vector projection,
not permission to replay a historical visibility state.

For every delivery attempt, the consumer reads the current relational Memory:

- an active Memory is embedded and upserted with current access and source
  metadata;
- a missing, retired, or superseded Memory is idempotently deleted from the
  vector index.

After the external operation, the consumer derives the target projection
again. If relational truth changed during delivery, it repeats the convergence
within a small bound before completing the row. If the target does not
stabilize, the row remains failed for a later attempt. Completion is
idempotent, so duplicate at-least-once consumers cannot revert an already
completed row.

The shared Source Sync Worker processes one bounded vector-outbox slice during
its normal maintenance cadence even when no source run exists. Producer-side
attempts remain a latency optimization, but no longer own eventual delivery.
The worker does not synchronously drain an unbounded backlog and does not
replay Source Units, extraction, or lifecycle planning.

Failed rows retain the initiating error, increment a bounded attempt count,
and receive a durable exponential retry time. Ready selection interleaves
older pending work and eligible failed work by their effective age. Exhausted
rows remain visible as failed operational state instead of spinning forever.

This design does not add a second job table or a distributed lease. Vector
delete and upsert are idempotent, every duplicate reconciles from current
relational truth, and the post-write stability check closes a lifecycle change
that overlaps an external write. A future throughput optimization may add
claims to suppress duplicate cost, but correctness must not depend on a lease
because lease expiry still permits at-least-once execution.

## Consequences

Backlogs larger than one delivery batch converge independently from source
sync. A stale `upsert` for a retired Memory becomes a vector delete rather than
a permanent failure, so later lifecycle truth cannot be resurrected.

SQLite and Cloud adapters expose the same ready-task and retry-time contract.
The HANA implementation adds the retry timestamp to the existing outbox table;
it does not add a Cloud-only lifecycle path.

There can still be duplicate embedding or vector calls when multiple workers
observe the same ready row. That is bounded operational cost, not a correctness
gap. The current Cloud worker uses one recurring maintenance cadence per
worker slot, and duplicate-cost suppression should be considered only if
measured scaling evidence justifies it.

## References

- [Cloud Issue #286](https://github.com/dodoman-sun/memforge-cloud/issues/286)
- [AWS transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
- [SAP HANA SELECT and locking](https://help.sap.com/docs/hana-cloud-database/sap-hana-cloud-sap-hana-sqlscript-reference/20fcf24075191014a89e9dc7b8408b26.html)
- [ADR 0005: Preserve provider identity across explicit scope transitions](0005-preserve-provider-identity-across-scope-transitions.md)
- [ADR 0011: Separate collection Evidence from body materialization](0011-separate-collection-evidence-from-body-materialization.md)
