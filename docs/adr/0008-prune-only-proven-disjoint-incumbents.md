# Prune only proven-disjoint incumbents before reconciliation

Status: Accepted

## Decision

The Memory Engine may resolve current Support Anchors against the provider-neutral
Revision Delta before invoking semantic incumbent reconciliation. When a changed
Source Unit produced no new Memory candidate, an incumbent whose complete scoped
evidence is `DISJOINT` receives an explicit `NOOP` decision and is omitted from
the model input. `AFFECTED`, `UNKNOWN`, legacy, and mixed-impact incumbents remain
in the complete model ledger.

When any new Memory candidate exists, every incumbent remains in semantic
reconciliation even if its current evidence is location-disjoint. This preserves
same-unit equivalence detection and prevents the optimization from creating a
duplicate Memory identity. Explicit absence and tombstones keep their existing
deterministic lifecycle paths.

## Consequences

The optimization applies equally to document and conversational projections and
does not add a provider branch, replay ledger, or unchecked top-N cap. Coverage
Proof still contains one explicit disposition for every incumbent. Runtime
samples record the complete incumbent count, model incumbent count,
deterministic-disjoint KEEP count, structured-model calls, and latency so the
optimization can be accepted from live evidence rather than fixture-specific
timing.
