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

## Amendment 2026-10-01: a Document uses only its own stored objects

This amendment replaces the paragraph that kept recorded artifact URIs
readable by their exact URI and left historical rows unrewritten.

### What happened

Keeping recorded URIs readable was applied to more than reading. A sync reused
the objects its Source recorded for a Unit while the content was unchanged,
without asking whose keys they lay under, so title-keyed URIs recorded before
this decision stayed in use. The ADR 0041 upgrade copied them into the stored
input of Source Units, and some Jira Units recorded another Jira Source's
object for the same Document. Each later sync of an unchanged Document named
the same object again. The content routes and `get_resource` served whatever
such an object held, the next update of the Unit diffed against it, and a
reprocess from stored input would have projected it. Evidence text lives in
the relational store and was not affected. On EU12 dev (planning step of
2026-10-01), 1,117 of 4,000 current stored inputs name at least one object
outside their Document's keys; 174 normalized objects among them hold
content other than the Unit's.

### Decision

**One rule at runtime.** An object belongs to a Document only when its key
lies under the keys its Source writes for that Document
(`{source}/{document identity}/`). `DocumentStore.belongs_to_document(uri,
source_id=, doc_id=)` states the rule once: the local store compares the
file's directory and the Cloud object store compares the key prefix. Every
use of a recorded object follows it:

- A sync reuses a raw, normalized or PDF object only when it belongs to the
  Document being recorded. Otherwise it writes the object again under the
  Document's keys, as if nothing had been stored.
- The previous normalized content of an update is read only from an object
  that belongs to the stored input's Source and Document. Otherwise the update
  has no previous content and is planned as such.
- A reprocess from stored input reads a raw object only when it belongs to the
  input's Document. Otherwise the Unit has no stored raw content and is
  unavailable with `stored_raw_content_missing`, in the preview and the run
  alike.

The rule has no exception for objects recorded before it.

**One upgrade makes the recorded history satisfy the rule.** OSS SQLite
migration 109 and the Cloud HANA migration `stored-object-ownership-v1` share
`memforge.storage.stored_object_ownership`. For every recorded stored input,
each object outside the Document's keys is proven or no longer named:

| Recorded object | Proven when | Proven | Not proven or missing |
| --- | --- | --- | --- |
| raw | its bytes match the recorded SHA-256, or it is a local-agent package whose `package_kind` is the Source's own kind (`decode_package`) and that names this Document | copied under the Document's keys; the SHA-256 of the copy is recorded | URI and SHA-256 cleared, so the input has no stored raw content |
| normalized | its bytes match the recorded normalized content hash | copied under the Document's keys | URI cleared; the hash stays, because it describes the committed revision's content and decides whether the next sync must extract |
| PDF | never: no fingerprint of a PDF is recorded | | URI cleared |

An unapplied derivation whose stored input names an object outside its
Document's keys is superseded, because applying it would record that object
again. Source Artifacts need no upgrade: their keys hold the Source, the
Artifact identity and the SHA-256 that the revision cites
([ADR 0014](0014-model-binary-artifacts-as-revision-pinned-source-evidence.md)).
Retained sync inputs belong to a Source, not a Document, and a Gene checks a
package's hash and Document id when it reads one.

The upgrade is recoverable in the sense of
[ADR 0032](0032-guard-local-data-upgrades-with-recoverable-migrations.md). A
read-only planning step classifies every object. Proven objects are then
copied, each named by the SHA-256 of its bytes, before one transaction records
the new inputs (guarded by each input's `recorded_at`, so an input recorded by
a sync after planning stays as it is), queues every replaced object to the
cleanup of released stored input, supersedes the derivations and records the
migration. A copy whose object changed after planning fails the upgrade. A run
that stops before the transaction leaves every input as recorded, and the next
run plans again and writes the same copies. The upgrade deletes nothing
itself: the cleanup deletes a replaced object once no stored input, retained
sync input or unapplied derivation names it. The planning counts per class
are logged as `Stored object ownership: {...}`.

Opening a database with recorded stored input needs the workspace's document
store (`Database(db_path, document_store=...)`,
`HanaWorkspaceDatabase(..., document_store=...)`); without it the upgrade
refuses to run.

### Why not accept older objects at runtime

Accepting an object at runtime when any of several proofs holds (its key, a
matching recorded hash, or a package that names the Document) would keep
three rules on every read path permanently, and each path would need the same
set. A proof from the bytes also holds only at the moment it is checked:
title-keyed objects are shared by same-titled Documents and can be overwritten
after they pass. Checking the recorded hash at runtime would also refuse
legitimate input, because the raw object under the Document's own keys can be
newer than the committed revision when a later sync of the same Source stored
its input and has not committed yet. The upgrade proves each object once,
copies it to where the rule looks, and leaves one rule.

### Consequences

On EU12 dev (planning step of 2026-10-01, read-only):

| Class | Count | Upgrade |
| --- | ---: | --- |
| raw, package of the Source's kind naming its Document (GitHub local push 587, local Markdown 7) | 594 | copied |
| raw, package naming another Document | 20 | cleared |
| raw, no recorded hash and no package of the Source's kind (Jira 219, Confluence 34, GitHub cloud pull 113, agent session 2) | 368 | cleared |
| raw, object missing | 2 | cleared |
| normalized, bytes match the recorded hash | 941 | copied |
| normalized, bytes differ from the recorded hash | 174 | cleared |
| normalized, object missing | 2 | cleared |
| PDF outside the Document's keys (Confluence) | 33 | cleared |
| unapplied derivations naming such an object (of 12) | 0 | superseded |

- A Unit whose raw object is cleared reports `stored_raw_content_missing` for
  a reprocess from stored input until its next committed revision records
  input. Jira and Confluence rediscover their Documents and read the provider
  on reprocess, so they are not affected. For the 113 GitHub cloud-pull Units
  (77 of them known to name another file's content), the 22 local-push Units
  and the 2 agent-session Units, reprocess from storage is unavailable until
  the Document changes.
- A Unit whose normalized object is cleared has no previous content for its
  next update, and its content route has no normalized content until the
  Document syncs again. A cleared PDF is exported again by the next sync that
  processes the page.
- Every replaced object is deleted by the ordinary cleanup once nothing names
  it.
- The upgrade runs when a workspace's store first opens after the release. On
  the largest EU12 dev workspace, planning read its objects in 90 seconds; the
  copies add one write per proven object.

### Cloud impact

`ObjectDocumentStore` implements `belongs_to_document` by key prefix
(`workspaces/{workspace}/documents/{source}/{document identity}/`). The HANA
workspace store runs `stored-object-ownership-v1` in its migrations, with the
document store that `build_store` now passes to `HanaWorkspaceDatabase`; the
SQLite store passes its `LocalDocumentStore` to `Database`. No HANA schema,
`sap/` route or configuration change. Cloud's `requirements.txt` pins the OSS
commit that carries this amendment.

## References

- [ADR 0010: Keep Support provenance projection complete](0010-keep-support-provenance-projection-complete.md)
- [ADR 0011: Separate collection evidence from body materialization](0011-separate-collection-evidence-from-body-materialization.md)
- [ADR 0014: Model binary Artifacts as revision-pinned Source Evidence](0014-model-binary-artifacts-as-revision-pinned-source-evidence.md)
- [ADR 0032: Guard local data upgrades with recoverable migrations](0032-guard-local-data-upgrades-with-recoverable-migrations.md)
- [ADR 0041: Record stored input on the Source Unit revision](0041-record-stored-input-on-the-source-unit-revision.md)
- `memforge-cloud` Issue #221
