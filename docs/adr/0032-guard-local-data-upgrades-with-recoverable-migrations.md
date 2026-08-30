# ADR 0032: Guard local data upgrades with recoverable migrations

## Status

Accepted (2026-08-30)

## Context

A Docker image, uv tool environment, native binary, and desktop application
deliver executable bits. None of them makes a previously migrated data root
compatible with an older executable, restores deleted relational state, or
rolls back a Chroma storage or embedding-space change. Replacing a Docker image
while retaining its volume is therefore the same data-compatibility problem as
replacing an installed Python tool while retaining `MEMFORGE_HOME`.

The current SQLite path correctly runs numbered migrations before application
readiness, but commits each migration separately. It has no product-level
pre-migration recovery point, supported-hop or downgrade guard, compatibility
manifest, or cross-store receipt. A failed version hop may retain completed
earlier migrations, and some migrations legitimately rewrite or remove state.
Startup ordering alone is not a recovery contract.

The Personal Local Profile persists authoritative relational lifecycle state,
the Chroma vector projection, source Documents and Artifacts, configuration,
and credential references under one product boundary. A version change must
keep those parts correlated without pretending that one filesystem copy or
one image tag is an atomic rollback.

## Decision

Native and Docker invoke one application-owned upgrade, migration, uninstall,
and recovery contract. Packaging-specific entrypoints may stage executables,
but they do not implement separate data behavior.

Every data root carries a small checksummed **Data Compatibility Manifest**
outside the mutable SQLite database. It records at least the application
release, SQLite schema version, minimum compatible reader/writer release,
Chroma storage/index format, embedding provider/model/dimension/revision,
Document and Artifact format, active data-root generation, and last successful
migration receipt.

Before normal open, migration, restore, or reindex, MemForge acquires an
exclusive maintenance lock for the resolved data root. It validates the
manifest, installed runtime versions, requested version hop, keyring access,
available disk and RAM, recovery staging space, and current durable work. An
older application that cannot read the manifest refuses without mutating data.
Running an exact old executable is not a downgrade unless a matching backup is
restored or the manifest explicitly permits that reader.

Migrations have two classes:

- a **Minor Startup Migration** is additive or backward-compatible, bounded on
  the declared personal capacity, contained in one SQLite transaction with its
  version record, idempotent under crash/retry, and performs no destructive,
  Chroma, embedding, or Document rewrite;
- a **Major Explicit Upgrade** covers every destructive, long-running,
  multi-stage, cross-store, embedding, vector-index, or special-space change.
  It requires a read-only check plan, explicit apply, a verified recovery point,
  and a durable idempotent migration state machine.

The ordinary UX is equivalent to:

```bash
memforge upgrade --check --to X.Y.Z
memforge backup create --reason pre-upgrade
memforge upgrade --apply --to X.Y.Z
memforge doctor --strict
```

`--check` is non-mutating and reports the exact version hop, supported
intermediate releases, estimated downtime, required and available bytes,
relational row effects, vector/Document actions, credential prerequisites, and
downgrade boundary. `--apply` consumes that exact plan under stale guards. The
main listener is not bound, or exposes only a loopback maintenance endpoint
with readiness false, until verification commits the successful receipt.

A major recovery point is one checksummed versioned bundle. MemForge drains
workers, uses the SQLite Online Backup API for a consistent relational
snapshot, quiesces and snapshots Chroma, preserves Documents and Artifacts,
stores non-secret configuration plus credential aliases, and records the
manifest and component hashes. A Docker volume archive and a blind copy of a
live SQLite file are not substitutes. Backup retention and later deletion are
separate explicit policy.

An incompatible Chroma format or embedding revision is never rewritten in
place. MemForge builds a revision-named collection or index directory beside
the active one from authoritative relational Memory state, converges the
durable vector outbox from current truth under
[ADR 0019](0019-drain-vector-outbox-from-current-relational-truth.md), verifies
exact eligible Memory/vector coverage and query health, then atomically switches
the manifest or active pointer. The old index remains until the migration
receipt commits and cleanup is separately authorized.

Every completed or failed major attempt leaves a durable **Migration Receipt**
with the from/to releases, plan and backup identifiers, manifest hashes,
component and stage results, before/after row-vector-Document counts,
verification, timestamps, and final disposition. Logs supplement the receipt;
they are not its only durable record. A failure keeps readiness false, preserves
the original recovery point and any staged side-by-side index, and offers
deterministic resume, restore, or safe-mode export. It never marks partial state
complete or starts workers against mixed generations.

Recovery is a product surface, not an operator filesystem recipe:

```bash
memforge doctor --strict
memforge backup list
memforge restore --check BACKUP_ID
memforge restore BACKUP_ID
memforge reindex --check
memforge reindex --apply
memforge web --safe-mode
```

Restore validates checksums, required application release, formats, space, and
replacement scope; writes to a staging root; verifies it; and atomically
activates the recovered generation. Safe mode remains loopback-only, disables
scheduler, workers, and vector mutations, and permits bounded diagnostics and
export without accepting a failed migration as current.

Uninstall exposes three independent ownership layers:

1. service/integration removal stops and removes launchd, systemd, or other
   MemForge registration and runtime PID/socket state;
2. executable removal deletes the uv tool environment or container/image only;
3. durable data, keyring entries, browser profiles, logs, and caches remain by
   default. Cache deletion is separately safe; durable-data deletion previews
   exact paths and keyring aliases and requires explicit confirmation.

Removing the executable never implies removing user data. Documentation prints
the safe order before the executable disappears and retains an exact-version
recovery invocation for an otherwise uninstalled tool.

## Considered options

- **Run arbitrary migrations automatically from every container or native
  startup.** Rejected because restart is not authorization for destructive or
  long-running work and cannot provide a coherent cross-store rollback.
- **Rely on image or package rollback.** Rejected because executable rollback
  does not reverse a data format, schema, embedding, or deletion.
- **Copy the data directory before upgrade.** Rejected for a live SQLite WAL
  and cross-store state; backup must use application-aware quiescence and
  component verification.
- **Rebuild Chroma in place.** Rejected because a crash can destroy the last
  usable projection and leave relational/vector state mixed.
- **Create separate Docker and native migration implementations.** Rejected
  because packaging cannot own business state and parity drift would make one
  recovery path unsafe.

## Consequences

Major upgrades require downtime and enough free space for a recovery bundle
and, when applicable, a second vector index. The UI and CLI must make that cost
visible before mutation. A release cannot claim upgrade support from current
unit tests alone; clean installed native and Docker artifacts must exercise
fresh install, every supported version hop, crash at each durable stage,
downgrade refusal, restore, reindex, strict health, and the three uninstall
layers.

Existing migrations must be classified and brought behind this contract before
the native path replaces Docker as the front-page default. Docker remains the
fallback described by [ADR 0031](0031-distribute-personal-local-oss-as-an-installed-tool.md),
but it gains no weaker backup or recovery semantics.

This ADR defines the compatibility and recovery invariants. Concrete command
implementation, release staging, retention defaults, and supported hop matrix
are tracked in the coordinating implementation issue rather than becoming new
business or lifecycle states.

## References

- [Issue 341: Ship Personal Local OSS installation and recoverable upgrades](https://github.com/shno-labs/mem-forge/issues/341)
- [ADR 0019: Drain vector outbox from current relational truth](0019-drain-vector-outbox-from-current-relational-truth.md)
- [ADR 0029: Manage local collection as an operating-system user service](0029-manage-local-collection-as-a-user-service.md)
- [SQLite Online Backup API](https://www.sqlite.org/backup.html)
- [SQLite WAL](https://www.sqlite.org/wal.html)
- [uv: Using tools](https://docs.astral.sh/uv/guides/tools/)
- [PocketBase: Going to production and backups](https://pocketbase.io/docs/going-to-production/)
- [Meilisearch: Updating](https://www.meilisearch.com/docs/learn/update_and_migration/updating)
