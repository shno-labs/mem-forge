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

## Decision

Treat support provenance as one bidirectional storage invariant for every
active configured-source Support on an active Memory:

- each `memory_sources(memory_id, source_id, doc_id)` row requires active,
  validated same-source Support; and
- each active Support Assertion requires the exact
  `memory_sources(memory_id, source_id, evidence_unit.doc_id)` row.

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

The projection remains an index/read model rather than lifecycle authority;
this decision does not add another semantic graph or replay mechanism. It
clarifies the exact consistency contract between the existing Support graph
and existing provenance projection.

## References

- [ADR 0009: Bound cross-document relation discovery](0009-bound-cross-document-relation-discovery.md)
- [MCP memory search facets](../design/mcp-memory-search-facets.md)
