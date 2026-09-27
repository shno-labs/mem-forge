# Record stored input on the Source Unit revision

Status: Accepted

Date: 2026-09-27

## Context

Each Source keeps one Source Unit per provider Document it includes, and Units
are never shared across Sources: a Jira issue matched by two JQLs, or a
Confluence page below two configured page trees, has one Unit in each Source.
Each Source also stores its own copy of the Document's input: object keys are
`{source}/{sha256(doc_id)}/{title}{extension}` for raw content, normalized
markdown and the PDF export, on the local filesystem and in Cloud's object
store alike ([ADR 0013](0013-bind-document-artifacts-to-document-identity.md)).

The `documents` table, however, is keyed by `doc_id` alone, one row per
workspace. The row held one Source's stored input (`raw_content_uri`,
`raw_content_type`, `normalized_content_uri`, `pdf_content_uri`, and the
normalized `content_hash`) next to the shared description of the Document, and
its `source` column was read as ownership. When two Sources include the same
Document, every sync of either Source overwrote the row, so the row pointed at
whichever Source synced last:

- On Cloud, 29 Jira Documents had a `documents.source` naming another Source.
  A reprocess of the Source that still had its own Unit and Memories for them
  refused them with `stored_document_missing`, because it required
  `document.source == source_id`.
- A reprocess from stored input could read raw content another Source stored,
  projected from a different provider state than its own Unit revision. The
  same held for the normalized hash a sync compares to detect a change, the
  previous markdown it diffs against, the objects it reuses and the PDF it
  requires.
- Removal detection listed a Source's Documents by `documents.source`: a
  Source that lost the row never saw its Document disappear, and the other
  Source's removal deleted the shared row and queued the objects it named for
  cleanup, which could be the first Source's objects.
- Source document counts, the project listing, the direct-write lifecycle gate,
  direct-write Source attribution, the Confluence PDF backfill check, content
  links and the memory health report all read the row the same way.

## Decision

### Stored input belongs to the Source Unit revision

A Unit's stored input is recorded in `source_unit_inputs`, one row per Source
Unit:

| Column | Meaning |
|---|---|
| `source_unit_id` | The Unit (primary key) |
| `source_id`, `document_id` | Its Source and the Document it was stored for |
| `unit_revision_id` | The revision the input was projected into |
| `item_json` | The item the Gene discovered, which a reprocess from stored input projects again |
| `raw_content_uri`, `raw_content_type`, `raw_content_sha256` | The raw provider content the revision was projected from |
| `normalized_content_uri`, `normalized_content_hash` | The normalized markdown and the hash the sync compares |
| `pdf_content_uri` | The PDF export, when the Gene exports one |
| `recorded_at` | When the input was recorded |

The input is recorded in the same transaction as the revision:
`RelationalStore.record_source_projection(projection, unit_input=...)` for a
revision that needs no semantic work, and
`apply_source_projection_lifecycle(..., unit_input=...)` for one committed with
its Lifecycle Plan. A staged derivation carries the input in its context
(`unit_input`), so recovery records it when it commits. A projection run that
was already recorded still records its input, unless a later revision of the
Unit is current. The order of [ADR 0040](0040-keep-stored-input-current-and-isolate-derivation-recovery.md)
is unchanged (store the raw content first, then record the revision), and it
now binds exactly that raw content to exactly that revision.

A reader uses the input only when `unit_revision_id` is the Unit's current
revision (`get_source_unit_input`). A tombstone or any other revision recorded
without input leaves the Unit without current input.

The input is one row per Unit rather than columns on `source_unit_revisions`.
Unit revision rows are immutable and content-addressed: a Unit that returns to
an earlier state (A, B, then A) reuses the stored row of A, and objects are
written in place per Source and Document, so the input of any revision but the
latest recorded one is no longer readable. The row names the revision it
belongs to instead. When a new input no longer names an object the replaced
input named (the Document was renamed or moved), that object is queued for
cleanup unless another Unit's input names it. `raw_content_sha256` identifies
the bytes the revision was projected from; the object at the URI can hold a
later uncommitted sync's input, as ADR 0040 describes.

The sync reads the Unit's input wherever it read the Document row before: the
normalized hash that decides whether the content changed, the previous
markdown for the update plan, the version for the changelog, the objects it
reuses when neither content nor revision changed, the `stored_extra` a Gene
may reuse (`ContentItem.stored_extra`), and the PDF requirement:
`Gene.requires_pdf_artifact(item=, stored_input=, existing_hash=, new_hash=)`
replaces the `existing_doc` argument.

### The Document row is the shared description

`documents` keeps what describes the Document itself: `source_url`, `title`,
`space_or_project`, `author`, `last_modified`, `labels`, `version`,
`content_hash`, `token_count`, `last_synced`, `client`, `item_extra_json` and
the row times, as the Source that synced it last saw them. The columns
`raw_content_uri`, `raw_content_type`, `normalized_content_uri` and
`pdf_content_uri` are removed.

`source` stays and names the Source that wrote the row last or, for a Document
no Source syncs (`user_memory`, `user_correction`), its writer. It is never
ownership. The Sources that hold a Document are the Sources with a current
Source Unit for it (`source_unit_document_lineage_history.is_current`). The
column is read only where the writer of the row matters: to attribute a direct
Memory write on a Document no Source Unit holds to its writer, to check that a
user correction or agent concept Document was written by its own writer, and,
when a Source is deleted or stops holding the Document, to re-point the row
to a Source that still holds it. Nothing reads it to decide which Source
holds, stores or may reprocess a Document.

| Reader | Now reads |
|---|---|
| Reprocess eligibility (`pipeline/stored_document.py`) | The Source's current Unit for the Document |
| Reprocess input: rediscovery item, stored raw content | The Unit's current input; rediscovery falls back to the Document row when the Unit has none |
| Sync change detection, previous markdown, object reuse, PDF requirement, `stored_extra`, changelog version | The Unit's current input |
| Removal detection (`list_indexed_doc_ids`), `count_documents(source=)`, source project listing | Current Source Units |
| Confluence PDF backfill (`count_missing_pdf_uris`), memory health `confluence_pdf_uri_missing` | Current Unit inputs |
| Projection reuse for local-agent snapshots (`find_reusable_source_projection_memberships`) | The version of the item in the Unit's current input |
| Direct-write lifecycle gate and Source attribution | Current Source Units; the row's `source` only for a Document no Unit holds; several holders require an explicit `source_id` |
| Tombstone lifecycle defaults (visibility, owner) | The projection's Source, as every other projected plan |
| `recent_changes` Source filter | `memory_sources.source_id` |
| Memory Evidence content and PDF links, review detail links | The input of the Unit that supports the Memory |
| Document artifact routes | The newest current input among Sources the caller can read |
| `delete_projected_document`, `rebind_projected_document_support` | Scoped to one Source (see below) |

### Content links name the Source Unit

`GET /api/v1/source-units/{source_unit_id}/content`, `/pdf`, `/artifacts` and
`/artifacts/{kind}` serve the stored input of that Unit's current revision,
when the caller can discover its Source. Memory Evidence and review details
link through the Unit that supports the Memory, so `get_resource` reads that
Source's copy. `GET /api/v1/documents/{doc_id}/...` keeps its paths and serves
the most recently recorded input among the Sources that hold the Document and
that the caller can discover; its manifest reports `source_id` and
`source_unit_id`. The plugin proxies accept both path families.

### Removal and object lifecycle are per Source

`delete_projected_document(doc_id, *, source_id)` removes one Source's copy:
it requires that no `memory_sources` edge of that Source names the Document,
deletes the input of that Source's Units that no longer hold it, and queues
their objects for cleanup. Objects are keyed per Source, so no other Source's
input names them. The Document row stays while another Source holds the
Document or any Memory names it, and its `source` is re-pointed to a Source
that still holds it; otherwise the row and its side tables are deleted.
`rebind_projected_document_support(old, new, *, source_id)` moves only that
Source's edges after its Unit moved; another Source that still holds the old
Document keeps its edges.

Deleting a Source keeps its Units and their input as history, as before, and
deletes no objects. A Document row that named it is re-pointed to a Source
that still holds the Document.

### Upgrade

A one-time startup migration (SQLite migration 104, HANA
`source-unit-stored-input-v1`) gives each current Unit (current revision,
current lineage) the input held by its Document row when the row's `source`
is the Unit's Source and names at least one object. The item is rebuilt from
the row's description and `item_extra_json`, `raw_content_sha256` is unknown
(`NULL`), and `normalized_content_hash` is the row's `content_hash`. The four
columns are then dropped. A Unit whose row another Source wrote gets no input:
a rediscovering Source (Jira server API, Confluence) reads the provider on
reprocess, and every Source records input with its next committed revision.
The migration runs once with its version record, and on a new schema it only
records the version.

### Provider namespace of `doc_id`

`doc_id` has no provider instance in it (`jira-SFPAY-123`,
`confluence-<page id>`, GitHub paths). Two Jira servers with the same project
key, or two Confluence instances with the same page id, in one workspace would
share one Document row and one `document_id` in Unit lineage. Units stay
separate, because their ids include the Source, and stored input now stays
separate with them; the shared description would be overwritten and Document
routes would mix the two. Adding the instance to `doc_id` changes the identity
used by Memory provenance, Evidence, lineage and object keys, so it is not part
of this decision.

## Consequences

- Two Sources that include the same Document each reprocess, detect changes
  in, link to and remove their own copy. The 29 Cloud Documents reprocess for
  the Source that holds them.
- A Unit whose Document row another Source overwrote before the upgrade has no
  stored input until its Source commits a new revision. A local-agent or
  uploaded Source fails such a Unit on reprocess with
  `stored_raw_content_missing`; the next sync of the Document that commits a
  revision records input.
- An unknown Document in a reprocess request fails with
  `stored_source_unit_missing` (it failed with `stored_document_missing`).
  `stored_document_missing` now means that the Unit exists but nothing
  describes the Document to rediscover it.
- A derivation staged before the upgrade has no `unit_input` in its context;
  committing it records the revision without input.
- A Document row that names a Source without a current Unit for it (a row
  written before Source Units existed) no longer counts as that Source's
  Document: a sync neither removes it nor fails on it.
- When a tombstone leaves another Source's Memory on the Document,
  `can_delete_document` is false and the removing Source's input and objects
  stay until a later removal succeeds; they are never read, because the Unit
  has no current input.
- Source document counts count Documents with a current Unit.

## Cloud impact

Cloud composes this package through its HANA store and the OSS admin app and
sync orchestrator.

- **Schema.** New table `SOURCE_UNIT_INPUTS` (`SOURCE_UNIT_ID NVARCHAR(255)
  PRIMARY KEY`, `SOURCE_ID`, `DOCUMENT_ID NVARCHAR(512)`, `UNIT_REVISION_ID`,
  `ITEM_JSON NCLOB`, `RAW_CONTENT_URI NVARCHAR(2048)`, `RAW_CONTENT_TYPE`,
  `RAW_CONTENT_SHA256 NVARCHAR(64)`, `NORMALIZED_CONTENT_URI`,
  `NORMALIZED_CONTENT_HASH`, `PDF_CONTENT_URI`, `RECORDED_AT`), created in
  `_migrate` right after `SOURCE_UNIT_REVISIONS`. The `DOCUMENTS` DDL loses
  the four stored-input columns.
- **Migration.** `source-unit-stored-input-v1` runs right after the new table
  is created, when `DOCUMENTS`, `SOURCE_UNITS` and
  `SOURCE_UNIT_DOCUMENT_LINEAGE_HISTORY` exist: it probes the four `DOCUMENTS`
  columns in `SYS.TABLE_COLUMNS`, upserts one `SOURCE_UNIT_INPUTS` row per
  current Unit whose Document row its own Source wrote, and drops the columns
  (`ALTER TABLE DOCUMENTS DROP (...)`), through
  `_apply_schema_migration_once`. A new empty schema creates the table and
  records the version. On EU12 dev, the 29 overwritten Jira Units get no input;
  their Sources rediscover on reprocess.
- **Storage protocol.** `record_source_projection` and
  `apply_source_projection_lifecycle` take `unit_input`;
  `delete_projected_document` and `rebind_projected_document_support` take a
  required `source_id`; new `get_source_unit_input` and
  `list_document_source_unit_inputs`; `count_missing_pdf_uris`, which the OSS
  orchestrator now calls on the store, joins the protocol. `WorkspaceDatabase`,
  `WORKSPACE_SYNC_RUNTIME_METHODS` and `HanaRelationalStore` change with it.
  `get_content_hash` is removed. `DocumentRecord` loses `raw_content_uri`,
  `raw_content_type`, `normalized_content_uri` and `pdf_content_uri`.
- **Readers.** `count_documents(source=)`, `list_indexed_doc_ids`,
  `list_source_projects`, `find_reusable_source_projection_memberships`
  (`JSON_VALUE(ITEM_JSON, '$.version')`), `count_missing_pdf_uris`, the
  direct-write gate and `_source_id_for_doc_sync` read Source Units and their
  input. `CloudGeneSyncOrchestrator` drops its `_get_indexed_doc_ids` and
  `_count_missing_pdf_uris` overrides, which now equal the OSS ones.
- **Object store.** `ObjectDocumentStore` keys are already per Source and
  Document; no change. Cleanup still runs through
  `SOURCE_ARTIFACT_CLEANUP_TASKS` and the worker's
  `SourceArtifactCleanupService`.
- **Routes.** The admin app mounted by `proxy/workspace_proxy.py` gains the
  `/api/v1/source-units/...` routes; Evidence links use them. No proxy change.
- **Call sites.** `proxy/external_runtime.py` constructs the orchestrator and
  engine as before; no signature it calls changes. Cloud's `requirements.txt`
  pins the OSS commit and moves to the commit that carries this decision.
- No change to LLM configuration, `sap/` routes or environment-only
  configuration.

## Related

- [ADR 0013](0013-bind-document-artifacts-to-document-identity.md): per-Source,
  per-Document object keys.
- [ADR 0039](0039-create-memories-within-the-source-unit.md): one Source Unit
  per Source and provider Document.
- [ADR 0040](0040-keep-stored-input-current-and-isolate-derivation-recovery.md):
  stored input is current and reprocess reads the provider when it can.
- [Source sync to Memory](../design/source-sync-to-memory.md): the complete flow.
