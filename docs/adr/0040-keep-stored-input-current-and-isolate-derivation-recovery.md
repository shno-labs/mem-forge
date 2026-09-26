# Keep stored input current and isolate derivation recovery

Status: Accepted

Date: 2026-09-27

## Context

A Source sync stores each Document's raw provider payload next to its
normalized markdown, and the Document row points at both. An operator reprocess
([ADR 0034](0034-unify-incremental-support-and-claim-assessment.md), the
`REPROCESS` Source sync run) reprojected named Documents from that stored raw
content without contacting the provider, projected it as a complete snapshot,
and committed the result like any other revision. Derivations staged by an
interrupted run are finished by the next run of the Source before it reads the
provider ([ADR 0017](0017-stage-recoverable-source-unit-derivation-before-lifecycle-commit.md)).

On 2026-09-26 nine reprocess runs over 314 Jira Documents in the EU12 dev
workspace showed four problems in how these parts fit together:

- **The stored raw content was older than the committed revision.** The raw
  payload was stored again only when the normalized markdown hash changed.
  Provider changes that never reach the markdown (Jira changelog entries for
  RemoteIssueLink, Rank, Fix Version, Epic Child and Sprint, a changelog
  author's display name) moved the Unit to a new revision while the Document
  kept the older raw content. 37 of the 314 Documents had such stale raw
  content.
- **Reprocess treated stale storage as the provider's current state.** The
  complete snapshot built from it removed 67 real changelog Observations in 36
  Documents. Their Evidence went with them: 11 Memories whose only Support
  cited those entries were retired, and 8 active Memories lost a Support.
- **A historical revision id conflicted with its own stored row.** For
  SFPAY-170693 the stale raw content carried an older author display name, so
  the projection produced the ids of two changelog revisions stored on
  2026-07-17. Observation Revision ids are derived from the Observation and the
  semantic hash, but the store compared the whole row, metadata included. The
  stored rows predated the Jira changelog `semantic_class` annotation (added the
  same day), the new ones carried it, and the lifecycle commit failed with
  "immutable projection identity mismatch" after every model call of the Unit
  had been paid for.
- **One failed derivation blocked the Source.** Recovery re-raised any
  exception. The staged derivation of SFPAY-170693 stayed `completed`, so the
  next run stopped after recovering 3 of 6 staged derivations, and every later
  run of the Source, scheduled syncs included, would have stopped at the same
  point.

## Decision

### Stored input is current

A sync that commits a new Unit revision stores the raw content that revision was
projected from, whether or not the normalized markdown changed. Every path uses
one order: the raw content (with the normalized markdown and any PDF export) is
stored first, then the Unit revision is recorded, by the lifecycle commit when
the revision needs semantic work and by the projection record when it only moves
the Unit (location or access), and the Document row that points at the stored
raw content is written with or right after it. A failed raw save therefore fails
the Document before anything commits. The stored raw content is never older than
the committed revision: it is the input of that revision, or of a later sync
that stored its input and has not committed yet. A sync whose projection keeps
the committed revision and whose markdown is unchanged keeps the stored raw
content as it is.

### Reprocess reads the provider when the Source has one to ask

A Gene declares whether a Source with a given configuration can ask its provider
for one Document by id (`Gene.rediscovers_documents(config)`), and implements
`Gene.rediscover(item)`: given the item rebuilt from the stored Document, it
returns the item discovery would yield for that Document now, in the
representation discovery uses, or `None` when the provider no longer has it.
Rediscovery answers exactly the question an ordinary sync answers about presence:
it returns `None` only in the cases where a full sync would stop listing the
Document, and it is never stricter. The ordinary `fetch` then reads the
Document's current state. A reprocess of such a Source authenticates the Gene, rediscovers
each named Document and processes it like a sync of that one Document, with the
reprocess authorization and Support reading of ADR 0034.

| Source | Reprocess reads |
|---|---|
| Jira (server API) | The provider: the issue by its numeric id, with the fields and changelog discovery requests. The issue is missing only when Jira answers 404 or 410. The Source's JQL is not applied: real JQLs carry moving windows (`updated >= -30d`), and an issue that ages out of the window still exists |
| Confluence | The provider: the page by its id, with the page representation every discovery mode reads (`version,metadata.labels,space`). The page is missing when Jira answers 404 or 410, when it carries an excluded label, and when full discovery would not list it: in space mode a page that is not current (archived, trashed) or not in a configured space; in page tree mode a page other than the root that is not current, not below the root, or reached only through a page that is not current or carries an excluded label, or any page other than the root when children are not included |
| Jira collected by a local agent | Stored input |
| GitHub Repository (cloud pull) | Stored input. Its fetch reads the blob SHA pinned at discovery, and the current file at a path is only known from a tree walk; a single-path rediscovery can be added to the Gene later without changing this contract |
| GitHub Pages | Stored input. Its fetch requires the SHA or content hash discovery recorded |
| Teams | Stored input. Collection runs in the local agent, and the server-side fetch needs the discovery message cache |
| Agent sessions, local Markdown, GitHub Repository (local push) | Stored input. The uploaded or pushed package is the only copy |

A Source without a provider to ask reprocesses its stored input, which the first
rule keeps current. A Document the provider no longer returns under its id (a
404 or 410 from the provider, or an item with another Document id) fails that
Document with `provider_document_missing`; the reprocess commits nothing for it
and infers no removal. Removal stays with a sync whose discovery proves it. A
Document without stored raw content can now be reprocessed when its Source
rediscovers.

The admin route keeps its path and request shape: `POST
/api/v1/sources/{id}/reprocess` with `document_ids` and `dry_run`. `dry_run`
still does not contact the provider; for a rediscovering Source it reports a
Unit as available without requiring stored raw content. The route and run no
longer promise to work without the provider for such a Source: a Source whose
provider is unreachable fails the reprocess at authentication, as a sync does.

### Observation Revisions are content-addressed

An Observation Revision's id is derived from its Observation and semantic hash,
and its Evidence Representation Profile fixes how Evidence addresses its
content. These three are its identity. When a projected revision's id is
already stored, whether as the current revision or as any historical one, the
stored row is that revision:

- The projection reads the stored rows of the ids it produces
  (`RelationalStore.get_source_observation_revisions`) and carries them as they
  are, so extraction and Evidence see exactly what the store keeps. Metadata the
  adapter derives now, such as `semantic_class`, does not replace stored
  metadata. The one permitted change is unchanged: a stored revision without a
  source time takes the one the projection gives.
- The store compares only the identity of an existing row. A different
  Observation, semantic hash or profile under one id raises
  `ProjectionIdentityConflict`, which is not retryable.

Derived annotations in revision metadata must therefore be complete on stored
rows. Migration 102 gives every stored Jira changelog revision without a
`semantic_class` the class computed from its content with the same function the
adapter uses. It is a Minor Startup Migration in the sense of
[ADR 0032](0032-guard-local-data-upgrades-with-recoverable-migrations.md): it
adds one derived key, runs in one transaction with its version record, and is
idempotent. The other metadata keys need no backfill:

- `claim_evidence_scope` (Jira comments, Teams messages) is part of the semantic
  hash. A revision stored before it has a different id, so the key never
  appears on a row that a projection reuses.
- `provider_key` has been written with every revision since projections
  existed.
- Artifact revision metadata is not determined by the semantic hash, which is
  the Artifact's SHA-256. `sha256`, `size_bytes` and `media_type` follow from
  the bytes, and `artifact_id` from the Source Unit and the provider key. The
  other keys describe how the bytes were delivered: `provider_revision`,
  `filename`, `uri`, `inference_eligible`, `inference_ineligible_reason` and
  `parent_observation_id`. When a projection reuses a stored Artifact revision,
  these keep the values stored with it, as reuse of the current revision always
  did; a later delivery of the same bytes under another filename or provider
  revision does not change them. They are recorded facts, not annotations
  derived by code, so there is nothing to backfill. An image summary added after
  extraction is a selection hint; the stored row keeps the summary it was
  committed with.

### Recovery isolates Source Units

Recovery classifies a failure with the rule every sync stage already uses
(`failure_retryable`): a model failure is retryable when it is transient
(provider error or timeout), and any other failure states it with its
`retryable` property, retryable by default. The lifecycle engine carries that
rule on the `SourceUnitLifecycleExecutionError` it wraps a failure in, so a
wrapped failure is classified by its cause.

- A failure that is not retryable repeats on every attempt. It supersedes the
  staged derivation with the new reason code `DERIVATION_DETERMINISTIC_FAILURE`,
  the Document counts as failed in this run unless the run's provider pass
  processes the same Unit again, and recovery continues with the next staged
  derivation. `ProjectionIdentityConflict` and an invalid model response are
  such failures. The Unit stays at its committed revision. It is derived again
  when the provider changes the Document and an incremental sync picks it up,
  or when an operator reprocesses it; nothing retries the superseded
  derivation, so a superseded reprocess or full-sync derivation is not retried
  by later incremental syncs. The failure is visible in that run's failed
  Documents and in the attempt's reason code. None of the existing codes fits: `DERIVATION_INPUT_SUPERSEDED`
  means newer input replaced the derivation, and `CONTRACT_SUPERSEDED` means the
  extraction contract changed.
- A retryable failure stops the run and leaves the derivation staged for the
  next run. This covers a Source activity fence the run no longer holds,
  storage errors (SQLite, HANA, the object store), a provider error or timeout
  of a model call, and any exception that does not declare itself not
  retryable.

Source Unit derivation checks projection identity before it stages anything:
`SourceUnitDeriver.derive` reads the stored rows of the projection's revision
ids and raises `ProjectionIdentityConflict` on a conflict. A projection that
cannot be committed costs no model call, and a staged derivation whose
projection can no longer be committed is ended by recovery before any model
call. The store still checks identity when it records the projection.

## Consequences

- A sync whose projection changes stores the raw payload even when the markdown
  is the same. For Jira this adds one object write per changed issue; the
  payload is already in memory.
- Reprocessing a Jira or Confluence Document makes the provider requests of one
  discovery item and one fetch. A Confluence reprocess also exports the page PDF
  again, as a forced sync does. The run fails when the provider is unreachable.
- A reprocess of a rediscovering Source commits the provider's current state.
  When the Unit changed since its last sync, the reprocess commits that change,
  as the next sync would.
- Stored raw content that is stale from before this decision stays stale until
  the Unit's next revision; for rediscovering Sources this no longer matters to
  reprocess, and for the others a sync that commits a new revision refreshes it.
- Confluence page tree discovery now reads the page space for child pages, as
  space discovery and the root page already did. A child page whose Document
  had an empty `space_or_project` gets its space key on its next sync, and a
  Project binding that reads that field (`by_field`) now resolves for it. The
  Unit Title and the Unit revision do not change: the fetch already reported the
  space.
- A value that returns to an earlier one (A, B, then A) reuses the stored
  revision of A and its metadata. After migration 102 that metadata is complete.
- A staged derivation built from stale stored input before this decision is
  not detected by recovery, because its revisions no longer conflict with the
  stored rows; applied, it would regress the Unit to the stale input. Only a
  reprocess sets `support_without_baseline` in a derivation context, so
  migration 103, a one-time startup migration, supersedes every unapplied
  derivation (`pending`, `retryable_failure`, `completed`) that carries it, with
  `DERIVATION_INPUT_SUPERSEDED` and the current `updated_at`. It runs once with
  its version record, so reprocess derivations staged after the upgrade are
  untouched. Self-hosted installations get it on their next start. The Unit
  keeps its committed revision and is derived again when the provider changes
  the Document and an incremental sync picks it up, or when an operator
  reprocesses it.
- A retryable failure in recovery still stops the run, as before; the next run
  resumes the staged derivation. Only failures that cannot succeed on retry are
  taken out of the way, and nothing retries them automatically: a Unit whose
  provider does not change the Document again needs an operator reprocess, found
  through the run's failed Documents or the `DERIVATION_DETERMINISTIC_FAILURE`
  reason code.

## Cloud impact

Cloud composes this package through its HANA store and the OSS admin app.

- **Storage protocol.** `RelationalStore` gains
  `get_source_observation_revisions(revision_ids) -> Mapping[id, revision]`.
  `SourceUnitDeriver` also calls it through the derivation store. Cloud
  implements it in `HanaWorkspaceDatabase` (one `SELECT ... WHERE ID IN (...)`
  on `SOURCE_OBSERVATION_REVISIONS`, chunked by the bind limit), delegates it in
  `HanaRelationalStore`, and adds it to the `WorkspaceDatabase` protocol and its
  method list in `core-integration`. No schema change.
- **Identity comparison.** `_record_source_projection_sync` compares an
  existing `SOURCE_OBSERVATION_REVISIONS` row by `OBSERVATION_ID`,
  `SEMANTIC_HASH` and the five profile columns only, and raises
  `ProjectionIdentityConflict` (from `memforge.source_projection`) for this and
  the Unit, Observation and Unit revision identity checks. Without this change
  a Cloud Unit whose projection reuses a historical revision with different
  metadata still fails its commit.
- **Staging-time check.** It lives in the shared `SourceUnitDeriver`, so
  `stage_source_derivation` in HANA needs no change.
- **Backfill.** A one-time HANA migration
  (`jira-changelog-semantic-class-v1`) reads `SOURCE_OBSERVATION_REVISIONS`
  rows of `changelog` Observations of `jira_issue` Units whose
  `METADATA_JSON` has no `semantic_class`, computes the class from `CONTENT`
  with `jira_changelog_semantic_class`, and updates `METADATA_JSON` through
  `_apply_schema_migration_once`. In EU12 dev this covers at least 317 rows
  (2 in src-e47815b5, 315 in src-70cb236e).
- **Superseding stale reprocess derivations.** A second one-time HANA
  migration (`stored-input-reprocess-derivations-v1`) runs the same update as
  OSS migration 103 on `SOURCE_DERIVATION_ATTEMPTS`: `STATUS = 'superseded'`,
  `TERMINAL_REASON_CODE = 'DERIVATION_INPUT_SUPERSEDED'` and `UPDATED_AT`, for
  unapplied rows whose `CONTEXT_PAYLOAD_JSON` has `support_without_baseline`
  true, through `_apply_schema_migration_once`. `_migrate` runs it after
  `SOURCE_DERIVATION_ATTEMPTS` and its added columns exist, so a new workspace
  schema initializes. No manual step remains.
- **Recovery.** `supersede_source_derivation` already stores any reason code
  (`TERMINAL_REASON_CODE NVARCHAR(255)`); no constraint changes. HANA driver
  errors (`hdbcli.dbapi.Error`) do not declare themselves not retryable, so a
  HANA outage during recovery stops the run and leaves the derivation staged.
- **Raw content.** Cloud's `ObjectDocumentStore.store_raw` is unchanged; it is
  called once more per changed Unit whose markdown did not change, and always
  before the revision is recorded.
- **Reprocess.** Cloud's Jira and Confluence Sources rediscover through the OSS
  Genes and need provider credentials at reprocess time; the route shape is
  unchanged. `reprocess_preview` gains the keyword `rediscovers`, called only by
  the OSS admin app. The HANA sync run queue's reprocess wording ("stored
  Documents") changes with the OSS wording, including the error "a reprocess run
  names its Documents only".
- **After deploying**, reprocess the 36 Documents that lost changelog entries,
  which now reads Jira, and check whether the 11 retired Memories were
  extracted again.
- No change to LLM configuration, `sap/` routes or environment-only
  configuration. `proxy/external_runtime.py` needs no change.

## Related

- [ADR 0017](0017-stage-recoverable-source-unit-derivation-before-lifecycle-commit.md):
  staged derivation and recovery, which this decision isolates per Unit.
- [ADR 0034](0034-unify-incremental-support-and-claim-assessment.md): the
  reprocess run, which now reads the provider for rediscovering Sources.
- [ADR 0032](0032-guard-local-data-upgrades-with-recoverable-migrations.md):
  migration classes.
- [Source sync to Memory](../design/source-sync-to-memory.md): the complete flow.
