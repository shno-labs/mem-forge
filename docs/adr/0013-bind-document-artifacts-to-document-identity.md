# Bind document artifacts to stable Document identity

Status: Accepted (2026-07-23)

## Context

Document artifact writers historically derived raw, normalized, and PDF
locations from Configured Source identity plus a slug of the Document title.
Titles are presentation metadata and are not unique within a source. Two
repository files, pages, or other source items with the same title could
therefore write the same location even though they had different `doc_id`
values. Exact provenance and `get_resource(doc_id)` routing would still select
the correct Document row, but that row could point to bytes last written by a
different Document.

This is an artifact identity defect. It is not a retrieval, ranking, or
Memory-lifecycle ambiguity.

## Decision

`DocumentStore` requires the stable `doc_id` for every raw, normalized, and PDF
write. Each adapter derives a collision-resistant Document namespace from that
identity and writes all artifact kinds inside it. Source identity remains an
outer ownership namespace; title and extension remain human-readable filename
metadata but do not establish uniqueness.

The shared contract applies to local filesystem and Cloud object-storage
adapters. Callers must provide `doc_id` explicitly; adapters do not infer it
from title, source URL, source type, or content. No source-specific
disambiguation or read-time fallback is permitted.

Existing recorded artifact URIs remain readable by their exact URI. New writes
use the Document-identity namespace. Historical colliding rows require a
bounded inventory and controlled rematerialization from authoritative source
evidence; this decision does not silently rewrite their URIs or bytes.

Artifact cleanup continues to operate on exact recorded URIs. A cleanup task
for one Document must not derive or delete a sibling Document's location.

## Consequences

Documents with the same title in one source have distinct raw, normalized, and
PDF identities, while content updates for one stable Document continue to
replace only that Document's artifact. Exact `get_resource(doc_id)` routing can
therefore return bytes attributable to the selected Document without changing
Memory, Support, Evidence, or source-lineage identity.

The `DocumentStore` interface gains one required parameter, and every adapter,
caller, and test fake must satisfy it. SQLite/local and Cloud/HANA deployments
share the same behavior even though their URI formats differ.

## References

- [ADR 0010: Keep Support provenance projection complete](0010-keep-support-provenance-projection-complete.md)
- [ADR 0011: Separate collection evidence from body materialization](0011-separate-collection-evidence-from-body-materialization.md)
- `memforge-cloud` Issue #221
