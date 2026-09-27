# Fence Source writes with activity leases alone

Status: Accepted

Date: 2026-09-27

## Context

Every Source carried an activity epoch (`sources.activity_epoch`). Source
activity leases, local-agent sync job payloads, snapshot manifests, staged
derivation contexts and Artifact input metadata copied it when they were
created, and every fenced write compared the copy with the Source's current
value. Destructive lifecycle maintenance (cutover, backfill, rebaseline)
advanced the epoch when it started and when an orphaned maintenance job was
recovered, so work started before the maintenance failed at its next write
even when it no longer held a lease ([ADR 0004](0004-use-proven-authoritative-snapshots-for-rebaseline.md),
[ADR 0001](0001-project-source-sync-activity-from-existing-execution-records.md)).

[ADR 0038](0038-make-evidence-unit-support-the-only-support-model.md) removed
that maintenance, and with it every writer of the epoch. Each Source's epoch is
now fixed, and every expected value is copied from that fixed value, so every
comparison passes.

## Decision

Source writes are fenced by the records that identify the executing attempt.
There is no Source activity epoch.

- **Source activity leases.** A Source has at most one unexpired lease (`sync`,
  `external_collection`, `agent_patch`, `maintenance`). A fenced write locks the
  Source row and checks, before its changes and again before commit, that the
  lease row exists with the same id, kind and capability and has not expired.
  A durable sync run's lease capability is its lease attempt count, so a
  recovered run invalidates the previous attempt's lease. An expired lease is
  deleted by the next acquisition, so its holder fails at its next write.
- **Local-agent job leases.** A daemon attempt is current while its job is
  leased to the same owner with the same attempt count and an unexpired lease,
  and its payload's `source_config_revision` matches the Source's current
  collection scope. A configuration change or a new attempt fails every upload,
  manifest and processing request of the old one. Snapshot manifests record the
  job, attempt and configuration revision they were collected under, and a
  manifest is reused only under the same configuration revision.
- **Derivation identity.** A staged derivation commits only when its
  projection, context and Document identity hashes still match, the Source
  Unit's current revision is the derivation's base (`AuthorityPlanStaleError`
  otherwise), and its required work is complete. The access context hash is part
  of derivation and Evidence work identity, and an extraction contract change
  supersedes pending work.

The epoch is removed from `SourceActivityLease`, the storage protocols
(`expected_source_activity_epoch`, `expected_activity_epoch`, `expected_epoch`,
`get_source_activity_epoch`), local-agent sync job payloads, snapshot manifest
status, derivation contexts and authority-plan identities, and Artifact input
descriptors. The local-agent heartbeat no longer ends jobs as
`local_agent_source_activity_epoch_stale`.

## Consequences

- Every fenced write checks one fewer column and no longer reads the Source's
  epoch.
- A future operation that must invalidate work started before it runs, as
  lifecycle maintenance did, takes the Source's `maintenance` lease and
  releases it when done. If it must also fail work that holds no lease at that
  moment, it defines that guard as part of its own design.
- Derivation context and authority-plan identities no longer include the epoch,
  so a derivation staged before the upgrade can no longer pass its context
  identity check at commit. The upgrade migration supersedes every unapplied
  derivation (`pending`, `retryable_failure`, `completed`) whose context carries
  the epoch, with `DERIVATION_INPUT_SUPERSEDED`. The next incremental sync
  derives such a Unit again because its current revision has not moved. A
  superseded reprocess or full-sync derivation is not requested again by an
  ordinary sync; an operator reprocesses the Source, as for the derivations
  [ADR 0040](0040-keep-stored-input-current-and-isolate-derivation-recovery.md)
  supersedes. The extraction contract version does not change.
- Upgrading when no sync is running, no derivation is unapplied and no
  local-agent job is queued or leased, the same condition as ADR 0038, avoids
  that repeated work. Correctness does not depend on it.
- Artifact input descriptors no longer include the epoch, so their input hash
  changes: the first upload of an Artifact after the upgrade records a new
  sync input instead of reusing the one recorded before it.
- Jobs that ended as `local_agent_source_activity_epoch_stale` keep that error
  code in their history. The admin UI shows it as a generic sync failure.
- Stored job payloads, Artifact input metadata and derivation contexts may
  still hold a `source_activity_epoch` key. Nothing reads it.
- SQLite migration 105 supersedes those derivations and drops
  `sources.activity_epoch`, `source_activity_leases.epoch` and
  `source_sync_snapshot_manifests.source_activity_epoch` in one transaction.
  None of the columns is indexed or referenced by a constraint, view or
  trigger. A new database never has them after the migration, and the
  migration drops each column only where it exists.

## Cloud impact

Cloud composes this package through its HANA store, the proxied admin app and
its own local-agent job routes, and changes in the same release as its OSS pin.

- **Schema.** A one-time migration `remove-source-activity-epoch-v1`, through
  `_apply_schema_migration_once`, supersedes the unapplied
  `SOURCE_DERIVATION_ATTEMPTS` whose context carries the epoch and drops
  `SOURCES.ACTIVITY_EPOCH`, `SOURCE_ACTIVITY_LEASES.EPOCH` and
  `SOURCE_SYNC_SNAPSHOT_MANIFESTS.SOURCE_ACTIVITY_EPOCH`. It runs in `_migrate`
  after the three tables and `SOURCE_DERIVATION_ATTEMPTS` with all its columns
  exist, probes each epoch column in `SYS.TABLE_COLUMNS` and drops only those
  present. A new empty schema creates the tables without the columns and only
  records the version. No HANA index, view or constraint names these columns.
- **Storage protocol.** `acquire_source_activity` loses `expected_epoch`;
  `record_source_projection` and `apply_source_projection_lifecycle` lose
  `expected_source_activity_epoch`; `create_source_sync_input`,
  `attach_source_sync_inputs_to_snapshot` and
  `attest_source_sync_input_artifact` lose `expected_activity_epoch`;
  `get_source_activity_epoch` is removed. `WorkspaceDatabase`,
  `WORKSPACE_SYNC_RUNTIME_METHODS` and `HanaWorkspaceDatabase` change with it.
  `get_source_sync_snapshot_manifest_status` no longer returns
  `source_activity_epoch`, and `SourceActivityLease` has no `epoch`.
- **Routes.** `routes/local_agent_jobs.py`: a targeted retry compares only
  `source_config_revision`; leasing no longer ends sync jobs whose payload lacks
  the epoch; the heartbeat no longer ends stale-epoch jobs and acquires the
  `external_collection` lease without an expected epoch.
  `routes/workspace_proxy_router.py`: the Service Metadata lease validator no
  longer compares the epoch.
- **Lifecycle canary.** The `activity_leases` query no longer selects `EPOCH`.
- **Rollout.** An instance of the previous version reads and writes the dropped
  columns, so its lease acquisitions, fenced writes and manifest records fail
  once the migration has run. Stop the previous instances before the new
  version migrates, as for earlier column removals.
- No change to LLM configuration, `sap/` routes or environment-only
  configuration.

## Related

- [ADR 0001](0001-project-source-sync-activity-from-existing-execution-records.md):
  durable server-run attempts own their Source activity lease.
- [ADR 0004](0004-use-proven-authoritative-snapshots-for-rebaseline.md):
  introduced the epoch advance for recovered maintenance.
- [ADR 0011](0011-separate-collection-evidence-from-body-materialization.md):
  local collection manifests and their lease binding.
- [ADR 0017](0017-stage-recoverable-source-unit-derivation-before-lifecycle-commit.md):
  staged derivation identity and recovery.
- [ADR 0038](0038-make-evidence-unit-support-the-only-support-model.md):
  removed the last operation that advanced the epoch.
