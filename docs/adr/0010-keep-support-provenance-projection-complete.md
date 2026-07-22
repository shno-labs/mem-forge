# Keep the support provenance projection complete

Status: Accepted

## Context

`MemorySupportAssertion` is lifecycle authority, while `memory_sources` is the
materialized provenance projection used by source facets, source-card counts,
source timestamps, access filtering, and document-level provenance views. A
legacy cutover path could leave an active Support Assertion without the exact
`memory_sources` row for its Evidence document. Lifecycle lineage remained
present, but source-scoped search and source-card counts then omitted the
supported Memory.

Checking only that every active `memory_sources` edge has same-source Support
is insufficient. The reverse mismatch is equally invalid, and accepting any
row from the same Source can hide a wrong-document projection.

The earlier physical identity `(memory_id, doc_id)` also assumed that one
provider document could belong to only one Configured Source. That assumption
is false when two independently configured scopes overlap: each Source has its
own Source Unit, Observation revision, access policy, and Support lineage even
when both resolve to the same provider object and legacy document identifier.
Collapsing those rows makes the most recent projection overwrite the other
Source while both authoritative Support Assertions remain active.

## Decision

Treat support provenance as one bidirectional storage invariant for every
active configured-source Support on an active Memory:

- each `memory_sources(memory_id, source_id, doc_id)` row requires active,
  validated same-source Support; and
- each active Support Assertion requires the exact
  `memory_sources(memory_id, source_id, evidence_unit.doc_id)` row.

The physical projection identity is therefore exactly
`(memory_id, source_id, doc_id)`. `source_id` is required, not inferred when a
Lifecycle Plan already carries the Configured Source identity. Distinct
Configured Sources may project the same Memory and document independently;
removing one edge must preserve the other Source's provenance and metadata
search projection.

Removal APIs therefore require the Configured Source identity; `(memory_id,
doc_id)` is not a valid deletion key. Deleting a Configured Source removes only
that Source's Support, Evidence, and provenance edges. If another current
Source Unit, Evidence Unit, or Memory provenance edge still references the
legacy document row, the document and its artifacts remain and the row is
assigned deterministically to a surviving Configured Source. Document side
tables and artifact cleanup are deleted only when no surviving Source lineage
remains.

Document-owned ingestion convenience APIs may derive only the persisted
Document's owning Configured Source. They read, update, and replace that exact
`(memory_id, source_id, doc_id)` projection. They must not select or delete an
arbitrary row by `(memory_id, doc_id)`. A secondary Configured Source that
overlaps the same provider document is attached or removed only through a
validated Lifecycle Plan that already carries its explicit `source_id`.

Removing one Support deletes only that exact Support Assertion, its mutable
current Evidence Relation, and its provenance read-model row. Evidence Units,
Relation Runs, Relation Candidates, and immutable per-run relation snapshots
are historical audit and remain available; they are garbage-collected only by
an explicit whole-source or purge boundary after no surviving Support or
relation depends on them. Preserving the immutable run snapshot is required for
deterministic retry validation.

If exact Support removal retires the last-supported Memory, the relational
retirement and a lifecycle vector-delete outbox task commit together. Vector
delivery is a retryable post-commit side effect; failure must not compensate or
reopen the committed Support, relation, provenance, or Memory state.

`ATTACH_SUPPORT` commits the Support Assertion and this materialized provenance
row in the same lifecycle transaction. A non-authoritative cross-document
Relation alone does not grant Support and does not create source membership.
Source filters and source-card counts continue to read `memory_sources`; they
must not bypass the projection by scanning Support Assertions independently.

Lifecycle gates, migration inventory, and operator evaluation check both
directions. Historical divergence is repaired only by an explicit operator
action that proves the active Memory, support-granting Evidence Reference,
current Observation revision, matching Source, exact Evidence document, and
access compatibility before one transactional projection write. Runtime
startup, search, and ordinary sync never infer or silently repair provenance,
and semantic similarity is never repair evidence.

## Consequences

SQLite, HANA, and future adapters expose the same aggregate invariant at the
storage seam and must pass adapter contract tests. Tests that insert Support
without its provenance projection are invalid fixtures rather than acceptable
shortcuts. A strict lifecycle audit fails closed on either direction of drift.

Existing two-column projection tables are migrated only after every row has a
non-empty `source_id`. SQLite rebuilds the read-model and metadata projection
under the shared schema migration. HANA expands the primary key only after its
source-id backfill and NOT NULL checks succeed; ambiguous legacy key shapes
continue to require controlled operator maintenance.

The projection remains an index/read model rather than lifecycle authority;
this decision does not add another semantic graph or replay mechanism. It
clarifies the exact consistency contract between the existing Support graph
and existing provenance projection.

The globally keyed legacy Document table remains a content read model rather
than Configured Source identity. Shared-document preservation is derived from
the existing provenance and lineage tables; this decision does not introduce a
new ownership ledger or Source-type-specific deletion policy.

## References

- [ADR 0009: Bound cross-document relation discovery](0009-bound-cross-document-relation-discovery.md)
- [MCP memory search facets](../design/mcp-memory-search-facets.md)
