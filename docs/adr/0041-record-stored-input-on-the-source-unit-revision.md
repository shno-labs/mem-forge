# Record stored input on the Source Unit revision

Status: Accepted

Date: 2026-09-27

Amended: 2026-09-30, see [Amendment: stored bytes are read by what they are](#amendment-2026-09-30-stored-bytes-are-read-by-what-they-are).

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
revision (`get_source_unit_input`). Recorded file URIs must also satisfy the
Source and Document ownership rule in [ADR 0013](0013-bind-document-artifacts-to-document-identity.md);
a stored URI alone does not establish ownership. A tombstone or any other revision recorded
without input leaves the Unit without current input.

The input is one row per Unit rather than columns on `source_unit_revisions`.
Unit revision rows are immutable and content-addressed: a Unit that returns to
an earlier state (A, B, then A) reuses the stored row of A, and objects are
written in place per Source and Document, so the input of any revision but the
latest recorded one is no longer readable. The row names the revision it
belongs to instead. When a new input no longer names an object the replaced
input named (the Document was renamed or moved), that object is released for
cleanup (see below). `raw_content_sha256` identifies
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
Source's copy. `GET /api/v1/documents/{doc_id}/...` keeps its paths. Among
the Sources that hold the Document and that the caller can discover, it serves
the most recently recorded input whose requested object is still stored, so a
copy whose object is missing falls back to the next one; the manifest lists
the newest copy that still has any object. The manifest reports `source_id`
and `source_unit_id`. The plugin proxies accept both path families.

### Removal and object lifecycle are per Source

`delete_projected_document(doc_id, *, source_id)` removes one Source's copy:
it requires that no `memory_sources` edge of that Source names the Document,
deletes the input of that Source's Units that no longer hold it, and releases
their objects for cleanup. The Document row stays while another Source holds the
Document or any Memory names it, and its `source` is re-pointed to a Source
that still holds it; otherwise the row and its side tables are deleted.
`rebind_projected_document_support(old, new, *, source_id)` moves only that
Source's edges after its Unit moved; another Source that still holds the old
Document keeps its edges.

Deleting a Source keeps its Units and their input as history, as before, and
deletes no objects. A Document row that named it is re-pointed to a Source
that still holds the Document.

Whether a released object is deleted is decided when cleanup runs, not when it
is released. Keys are written in place per Source, Document and title, so the
same key can be written and named again before cleanup runs: a Document
renamed and renamed back, or removed and listed again. Releasing only queues
the URI in `source_artifact_cleanup_tasks`. `SourceArtifactCleanupService`
processes a Source's tasks while holding that Source's activity lease
(`MAINTENANCE`), the lease every sync of the Source holds while it writes
objects and records the input that names them. Under the lease it checks
`source_artifact_uri_is_referenced(uri, source_id=)` and deletes only an
object nothing names. A reference is any Source Unit input, a retained sync
input `raw_uri`, or the `unit_input` of a derivation of that Source that is
staged and not yet applied or superseded (`pending`, `retryable_failure`,
`completed`): a sync that writes its objects and stages its derivation but
fails before the commit has released its lease, and the next run resumes the
derivation and commits exactly those objects. A named object completes its
task without deletion, and its next release queues it again. The URI columns
of `source_unit_inputs` and `source_sync_inputs.raw_uri` are indexed for this
lookup; the derivation part is bounded by the `(source_id, status)` index on
`source_derivation_attempts`.

Cleanup processes tasks per Source, the Source with the oldest task first. A
Source whose lease another activity holds is skipped without using up the
batch, so one long sync does not hold back other Sources' cleanup. Cleanup
runs periodically: every minute from the OSS `SyncScheduler`
(`ARTIFACT_CLEANUP_JOB_ID`, `ARTIFACT_CLEANUP_BATCH_SIZE` tasks per run) and
on every pass of the Cloud workspace worker. A path that releases objects only
queues them; the Source deletion route still runs a batch right after
retiring the Source.

Two writers do not hold the Source lease: local-agent Artifact uploads and
local-agent package pushes. Each of their attempts writes a key of its own
(the attempt id is part of the Artifact id or the package file name), so a
task queued by an earlier failed or duplicate attempt names only the object
that attempt abandoned, and no later attempt writes it again. Taking the lease
does not fit these uploads: one collection pushes many inputs of the same
Source in parallel, and uploads run while the server syncs the Source, so an
exclusive lease would serialize them and reject uploads during every sync.
Recording the reference before the write does not fit either: the object store
chooses the key, and a package is built and written in one step before its
sync input is recorded. Deduplication is unchanged, because it keys on the
input hash recorded in `source_sync_inputs`, not on the object key; the
duplicate object of a lost race is queued for cleanup.

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
- A released object waits in the cleanup queue while its Source has an
  active sync or other activity; the next cleanup run after it ends deletes it.
- A duplicate or failed local-agent upload leaves its own object until the
  next periodic cleanup run, instead of being deleted in the request.
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
  `list_document_source_unit_inputs` (these are on the OSS `RelationalStore`
  protocol). The OSS orchestrator calls `list_indexed_doc_ids` and
  `count_missing_pdf_uris` on its `Database`, not through `RelationalStore`;
  on Cloud, `count_missing_pdf_uris` joins `WorkspaceDatabase` and
  `WORKSPACE_SYNC_RUNTIME_METHODS`, where `list_indexed_doc_ids` already is.
  `WorkspaceDatabase`, `WORKSPACE_SYNC_RUNTIME_METHODS` and
  `HanaRelationalStore` change with the rest.
  `get_content_hash` is removed. `DocumentRecord` loses `raw_content_uri`,
  `raw_content_type`, `normalized_content_uri` and `pdf_content_uri`.
- **Readers.** `count_documents(source=)`, `list_indexed_doc_ids`,
  `list_source_projects`, `find_reusable_source_projection_memberships`
  (`JSON_VALUE(ITEM_JSON, '$.version')`), `count_missing_pdf_uris`, the
  direct-write gate and `_source_id_for_doc_sync` read Source Units and their
  input. `CloudGeneSyncOrchestrator` drops its `_get_indexed_doc_ids` and
  `_count_missing_pdf_uris` overrides, which now equal the OSS ones.
- **Object store and cleanup.** `ObjectDocumentStore` keys are already per
  Source and Document; no change. The worker's `SourceArtifactCleanupService`
  now needs `source_artifact_uri_is_referenced`, `get_source`,
  `acquire_source_activity` and `release_source_activity` on the workspace
  database, plus `list_source_artifact_cleanup_source_ids` and a `source_id`
  filter on `list_source_artifact_cleanup_tasks`; HANA implements the new ones
  and has the others. `source_artifact_uri_is_referenced` also reads unapplied
  `SOURCE_DERIVATION_ATTEMPTS` of the Source through
  `JSON_VALUE(CONTEXT_PAYLOAD_JSON, '$.unit_input...')`. HANA indexes
  `SOURCE_UNIT_INPUTS` on each URI column and `SOURCE_SYNC_INPUTS` on
  `RAW_URI`. Releasing objects no longer checks references, so a batch that
  releases two inputs naming one URI queues it once.
- **Routes.** The admin app mounted by `proxy/workspace_proxy.py` gains the
  `/api/v1/source-units/...` routes; Evidence links use them. No proxy change.
- **Call sites.** `proxy/external_runtime.py` constructs the orchestrator and
  engine as before; no signature it calls changes. Cloud's `requirements.txt`
  pins the OSS commit and moves to the commit that carries this decision.
- No change to LLM configuration, `sap/` routes or environment-only
  configuration.

## Amendment 2026-09-30: stored bytes are read by what they are

### What happened

The upgrade rebuilt each migrated item from `DOCUMENTS.ITEM_EXTRA_JSON`. On
HANA that column was only written from 2026-09-26, one day before the
migration ran on 2026-09-27, so the migrated input of every Document not
synced again in between carries an empty `extra`. `GitHubRepoGene` decided
whether stored bytes were a local-push package by `item.extra.package_uri`
or `package_path`; with an empty `extra` it read the package as file text and
failed with `GitHub repository URL is required`. On EU12 dev, 656 current
local-push GitHub Units could not be reprocessed from storage. Teams window
packages were read by their own kind already, but stored input keeps only
bytes, not the attestation a fetch makes about them, so the stored input of a
tombstoned window failed the empty-content check. The reprocess preview did
not normalize or project, so it reported all of these Units as processable.

### Decision

A Gene decodes stored bytes by the bytes themselves, never by metadata stored
beside them. A local-agent package names its own kind (`package_kind`), and a
Gene reads bytes as its package only when they are a JSON object of exactly
its kind (`decode_package`); anything else is what the provider returned, so a
repository file that happens to be JSON is file text. `item.extra` stays
discovery metadata: `package_uri` and `package_path` still locate the package
for a fetch, and nothing decodes by them. Every Gene that reads packages
follows this (GitHub Repository, local Markdown, Jira, Teams), and the
projection adapters unwrap a Jira or Teams package only for its exact kind.

What the provider attested about the bytes is read back from them too.
`Gene.raw_from_stored_input(item, body, content_type)` rebuilds the raw content
of a stored input: a GitHub or local Markdown package whose file is empty and a
Teams tombstone package attest empty content, with the same evidence their
fetch gives; other bytes attest nothing. `load_stored_source_document` takes
the Gene and uses it.

Reprocessing from stored input and its preview run one check,
`project_stored_input`: normalize, require content the provider attests,
project with the committed Unit's identity and Artifacts, and require the
committed revision's location. A Unit that fails normalization or projection is
unavailable with `stored_input_invalid` (the underlying error in `detail`),
and one whose location differs with `stored_input_incomplete`, in the preview
and in the run alike, and neither is retried. The preview calls no provider and
no model.

### Consequences

- Migrated local-push GitHub inputs with an empty `extra` reprocess from
  storage. On EU12 dev, 638 of the 656 re-project to exactly their committed
  revision, so reprocessing them needs no extraction; 55 tombstoned Teams
  windows do the same. A read-only replay of all 3,973 current Units with
  stored input found no Unit that re-projected before and fails now.
- A stored input whose object holds another Document's package still fails the
  location check, as it should (18 GitHub Units on EU12 dev); it recovers when
  that file syncs again.
- For incrementally synced Sources (local-push GitHub, Teams, Confluence), "the
  next committed revision records input" can take a long time: a Document whose
  content does not change is never processed again, so its migrated input, with
  its empty `extra`, stays. Nothing may depend on migrated `extra` being
  present.
- The preview reports a Unit as available only when the run can process it.

### Cloud impact

None beyond the OSS pin: no HANA schema, storage protocol, `sap/` route or
configuration change, no data fix and no resync. The migrated rows stay as
they are and become readable with the new code.

## Related

- [ADR 0013](0013-bind-document-artifacts-to-document-identity.md): per-Source,
  per-Document object keys.
- [ADR 0039](0039-create-memories-within-the-source-unit.md): one Source Unit
  per Source and provider Document.
- [ADR 0040](0040-keep-stored-input-current-and-isolate-derivation-recovery.md):
  stored input is current and reprocess reads the provider when it can.
- [Source sync to Memory](../design/source-sync-to-memory.md): the complete flow.
