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

## Amendment 2026-09-30: a recorded object is reused only when it is the Document's own

### What happened

"Existing recorded artifact URIs remain readable by their exact URI" was
applied to more than reading. A sync reuses the objects its Source recorded
for a Unit while the content is unchanged, and it reused them without asking
whose keys they lay under. Title-keyed URIs recorded before this decision
therefore stayed in use, and the ADR 0041 upgrade copied them, and for some
Jira Units another Source's URI, into the stored input of Source Units. Each
later sync of an unchanged Document named the same object again. On EU12 dev,
175 current Units pointed at an object that held another Document's content;
149 of them had active Memories. The content routes and `get_resource` served
that content, the next update of such a Unit diffed against it, and a
reprocess from stored input would have projected it. Evidence text lives in
the relational store and was not affected. Eight Units recorded a raw
SHA-256 that no longer matched their object, because a same-titled Document
overwrote it after it was recorded.

### Decision

An object belongs to a Document only when its key lies under the keys this
Source writes for that Document (`{source}/{document identity}/`).
`DocumentStore.belongs_to_document(uri, source_id=, doc_id=)` states this rule
once; the local store compares the file's directory, and the Cloud object
store compares the key prefix. Every reuse of a recorded object checks it:

- A sync reuses a raw, normalized or PDF URI only when it belongs to the
  Document being recorded. Any other URI is written again under the Document's
  own keys, as if nothing had been stored.
- The previous normalized content of an update is read only from an object
  that belongs to the stored input's Source and Document; otherwise the update
  has no previous content and is planned as such.
- A reprocess from stored input reads the raw object only when it belongs to
  the input's Document and its bytes match the recorded SHA-256 (when one was
  recorded). Otherwise the Unit is unavailable with
  `stored_raw_content_mismatch`, in the preview and the run alike.

Reading a recorded URI stays exact: the content routes still serve the URI a
Unit's stored input names, so they show the stored object until the next sync
of that Document replaces it.

### Consequences

- A Unit whose stored input names an object outside its keys writes that
  object again on the next sync that processes its Document, and records the
  new URI. The old object is released to cleanup and deleted once nothing
  names it. No data migration or resync is run. On EU12 dev (inventory of
  2026-09-30), 1,068 current Units name at least one such object, almost all
  title-keyed objects written before 2026-07-23; they include the 175 whose
  object holds another Document's content. A Document that an incremental sync
  does not process again keeps its stored input until it changes.
- A reprocess from stored input refuses a raw object outside the Unit's keys
  even when its bytes are the Unit's own: ownership is decided by the key,
  never by the content. On EU12 dev this refuses 934 Units, among them 601
  local-agent packages (586 of one local-push GitHub Source) uploaded before
  2026-07-23 whose content is their own. They become processable again once
  their Document syncs again. A Source that rediscovers its Documents (Jira
  server API, Confluence) reads the provider on reprocess and is not affected.
- Until a Unit syncs again, its content route still shows the object its
  stored input names.
- Local-agent packages uploaded since 2026-07-23 are stored per upload under
  the Document's own keys, so they always belong to their Document.

### Cloud impact

`ObjectDocumentStore` implements `belongs_to_document` by key prefix
(`workspaces/{workspace}/documents/{source}/{document identity}/`). No HANA
schema, storage protocol of the workspace database, `sap/` route or
configuration change, no data migration and no resync. Cloud's
`requirements.txt` pins the OSS commit that carries this amendment.

## References

- [ADR 0010: Keep Support provenance projection complete](0010-keep-support-provenance-projection-complete.md)
- [ADR 0011: Separate collection evidence from body materialization](0011-separate-collection-evidence-from-body-materialization.md)
- [ADR 0041: Record stored input on the Source Unit revision](0041-record-stored-input-on-the-source-unit-revision.md)
- `memforge-cloud` Issue #221
