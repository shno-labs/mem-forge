# Authoritative Source Rebaseline Design

## Status

Approved in the MemForge lifecycle closure task on 2026-07-16.

This design deliberately does not preserve obsolete source projections merely
for backward compatibility. Historical derived data may be removed when a
current authoritative snapshot proves that it is absent. The correctness target
is the steady-state lifecycle produced by the current source contract.

## Problem

MemForge currently prepares a local-source rebaseline by requiring the indexed
document set to match the replay manifest. That requirement is safe against an
incomplete upload, but it also rejects every legitimate authoritative change in
which the current corpus differs from the old index:

- a provider record was deleted;
- a path or provider identity was renamed;
- a conversational windowing algorithm replaced old windows;
- an old document has no Source Unit lineage and must be removed during cutover;
- the source is now empty.

The production Teams canary exposed this exact state. A successful full
collection produced a terminal snapshot containing 19 fully attested canonical
windows, while the old index contained 28 documents. Nine old documents were
absent from the new snapshot. Requiring equality prevents the rebaseline replay
from reaching the existing complete-absence deletion path.

The opposite rule, treating every missing item as deleted, is also unsafe. An
incomplete page traversal, partial upload, stale configuration, or ambiguous
provider identity must never authorize destructive lifecycle.

## Decision

A source execution contract explicitly classified as **authoritative** may use
a proven full snapshot as the complete current corpus for rebaseline. Once the
proof passes, the replay set is the snapshot manifest, not the old indexed
document set.

For an authoritative snapshot:

```text
current snapshot ∩ old index  -> keep or update through normal projection
current snapshot - old index  -> create through normal projection
old index - current snapshot  -> reconcile as authoritative absence
```

For a non-authoritative source, absence remains non-destructive. Rebaseline must
retain the current-document replay constraint because the collected inputs do
not prove that an omitted record was removed.

This decision changes deletion authority, not Memory identity. A Memory remains
a canonical claim with one or more active Support Assertions. Removing one
document removes only the support derived from that document. A Memory remains
active when another document, Source Unit, or source still supports it. The
last-support rule alone may retire it.

## Terms

### Authoritative collection

A source-specific collection mode whose contract guarantees that one completed
full snapshot enumerates every record in the configured scope, including an
explicit empty result. The current registry function
`local_agent_collection_is_authoritative(source_type)` is the ownership seam;
routes and lifecycle planners do not infer authority from provider names.

### Snapshot manifest

The immutable set of `SourceSyncInput` rows bound to one `input_snapshot_id`.
Each input projects exactly one current provider document identity and carries
the retained artifact URI, semantic input hash, version, and package
attestation.

### Old-index difference

Documents currently stored for the source but not returned by the proven
snapshot. This difference is stale derived state, not compatibility state.

### Rebaseline

A maintenance operation that fences ordinary sync, proves a complete replay,
resets derived source lifecycle, replays the current corpus, reconciles proven
absence, audits the result, and only then enables destructive lifecycle.

## Required Proof

An authoritative local snapshot may drive rebaseline only when all of the
following are true:

1. The source type declares authoritative collection in the source contract.
2. The latest accepted run belongs to the same source and workspace.
3. The run is a force-full collection with an immutable `input_snapshot_id`.
4. The run is terminal `success`, or terminal `failed` after a successful local
   collection already persisted the complete immutable input boundary. A
   package selection or upload failure cannot create this accepted boundary;
   rebaseline preflight independently validates every retained input before
   trusting a failed processing run.
5. The saved source configuration revision equals the run configuration
   revision.
6. The source activity epoch and maintenance lease fence competing sync writes.
7. The snapshot was completed without package selection or upload failure.
8. Snapshot document identities are non-empty and unique.
9. Every snapshot entry has one retained input, exact document/version/hash
   identity, and matching top-level and manifest package attestation.
10. Reading and validating every retained artifact succeeds.
11. Provider projection coverage for every replayed Source Unit proves complete
    absence authority.

Pagination completion by itself is not sufficient. Stable provider identity,
configured-scope completeness, snapshot completion, and artifact identity are
independent proof dimensions.

Any failed proof leaves the lifecycle job failed, the source gate closed, the
existing data intact, and an operator-visible error or durable finding. No
fallback guesses, semantic matching, or provider-specific route exception may
authorize deletion.

## Rebaseline Flow

### 1. Acquire the maintenance boundary

The rebaseline request atomically:

- locks the source;
- cancels any active SourceSyncRun for that source;
- removes its sync activity lease;
- bumps `source_activity_epoch`;
- acquires the maintenance lease;
- creates one durable lifecycle job.

Workers must supply the old expected epoch when committing projection or
lifecycle state. A fenced worker may finish local computation but cannot commit
after the maintenance boundary moves.

### 2. Select the replay corpus

For authoritative local collection:

- read only the inputs bound to the accepted `input_snapshot_id`;
- project their unique manifest entries;
- validate all retained artifacts;
- use the manifest document ids as the replay corpus;
- do not add old indexed documents to the manifest;
- allow an empty manifest when the completed snapshot explicitly represents an
  empty configured scope.

For non-authoritative local collection:

- read retained inputs at or below the accepted generation watermark;
- require every current indexed document and version to have a valid retained
  artifact;
- do not infer deletion from omitted inputs.

Server-pull sources continue to use fresh provider discovery and the shared
coverage proof. They do not use local snapshot identity as a substitute for
provider completeness.

### 3. Run non-mutating preflight

`REBASELINE_PREFLIGHT` fetches and normalizes the selected corpus, projects each
item as a full snapshot, and verifies provider-neutral complete coverage. It
does not write Documents, Source Units, Observations, Memories, Support
Assertions, vectors, deletion tombstones, sync state, or sync history.

Preflight failure preserves all existing derived state.

### 4. Reset and replay

Only after successful preflight does the memory store reset the source's
derived lifecycle state. `REBASELINE_REPLAY` then:

- writes canonical Source Units, Unit Revisions, Observations, and Observation
  Revisions for the snapshot;
- extracts or reuses canonical Memories through the normal lifecycle engine;
- writes active Support Assertions and evidence lineage;
- treats `old index - snapshot` as authoritative absence;
- writes tombstones for traceable Source Units;
- removes legacy projected documents without Source Unit lineage through the
  existing `rebaseline_legacy_absence` path;
- removes source-local support before applying the last-support retirement rule;
- preserves independent cross-document and cross-source support.

No compatibility bridge recreates an obsolete document solely because an older
MemForge version indexed it.

### 5. Audit and reopen the gate

The lifecycle job completes only if the post-replay audit proves:

- no open lifecycle finding for the source;
- every active source-backed Memory has valid active support;
- every active support points to the current Observation revision;
- no stale projection or orphaned configured-source edge;
- no pending lifecycle review;
- no incomplete vector outbox work;
- no active scope transition;
- the source lifecycle gate is enabled.

Finding and job history remain durable after resolution.

## Failure Semantics

- Incomplete discovery, partial upload, missing snapshot boundary, stale config,
  duplicate identity, unattested artifact, invalid package, or unknown coverage
  fails before reset.
- A maintenance epoch change rejects late sync commits.
- A replay failure after reset leaves the source gated and the durable job
  failed. It does not claim success or enable destructive lifecycle.
- An ambiguous legacy Memory remains represented by an open Lifecycle Cutover
  Finding. Text similarity cannot close it.
- Cross-source conflict never grants deletion authority. Independent support or
  conflict remains governed by Support Assertions and the review gate.

## Source-Type Contract

The shared lifecycle layer consumes a provider-neutral contract:

```text
CollectionAuthority:
  AUTHORITATIVE_FULL_SNAPSHOT | NON_AUTHORITATIVE

ReplayBoundary:
  source_id
  source_config_revision
  source_activity_epoch
  input_snapshot_id | input_generation_watermark
  force_full_sync
  terminal_status

ReplayItem:
  stable_document_id
  provider_unit_identity
  version
  semantic_input_hash
  retained_artifact_identity
  package_attestation
```

Provider adapters own stable identity and coverage production. The rebaseline
orchestrator owns proof validation and phase ordering. The lifecycle engine owns
Support and Memory decisions. Storage owns atomic fences and invariants. No
layer branches on Jira, GitHub, Confluence, Teams, or other provider fields.

## Test Contract

The implementation must add provider-neutral tests, with SQLite and HANA parity
where persistence is involved.

### Replay selection

- authoritative snapshot equals old index;
- authoritative snapshot adds a document;
- authoritative snapshot removes a traceable document;
- authoritative snapshot removes a legacy document without Source Unit lineage;
- authoritative rename produces a new identity and removes the old projection;
- authoritative empty snapshot removes the old corpus;
- non-authoritative input omission does not authorize deletion;
- current-config mismatch fails before reset;
- non-terminal or non-full boundary fails before reset.

### Artifact and completeness safety

- every snapshot artifact is validated before reset;
- missing top-level or manifest attestation fails closed;
- conflicting attestation fails closed;
- duplicate snapshot document identity fails closed;
- partial selection, upload failure, incomplete pagination, or incomplete
  coverage fails closed;
- stale retained URI or corrupt bytes fail closed;
- zero-item authoritative completion is distinguished from collection failure.

### Lifecycle closure

- removing one support preserves a multi-document Memory;
- removing the last same-source support preserves independent cross-source
  support;
- losing the final active support retires the Memory;
- tombstone lineage targets the current Source Unit revision;
- legacy orphan cleanup leaves an audit context;
- post-replay open finding, review, or outbox work keeps the gate closed.

### Concurrency and durability

- rebaseline atomically cancels a pending, running, or recovering source run;
- a late worker cannot commit Document, projection, lifecycle, or vector state
  after the epoch fence;
- retrying the same maintenance request does not create two active jobs;
- two workers cannot process the same source boundary concurrently;
- rebaseline failure is durable and restart-safe;
- local-agent jobs are leased one at a time and long processing cannot expire a
  later idle lease.

### Long-running source canary

Every authoritative source type must pass:

```text
create source
-> initial full sync
-> no-op sync
-> add
-> content change
-> rename/move
-> delete
-> concurrent enqueue/retry
-> multi-document support
-> cross-source support
-> last-support retirement
-> search + get-memory provenance
-> HANA lineage/outbox/gate audit
```

Teams is the first production canary. A deliberately bounded GitHub Repository
source follows only after Teams closes. Large repositories must not be expanded
until the same contract passes on the bounded corpus.

## Rollout and Acceptance

1. Implement the replay-selection change test-first in OSS.
2. Apply storage/protocol parity in Cloud HANA without route-level provider
   special cases.
3. Run focused and full OSS/Cloud tests, Ruff, and diff checks.
4. Commit and push both repositories, exact-pin OSS in Cloud, and deploy through
   the checked 2 GB Cloud Foundry workflow after warning the user about downtime.
5. Run exactly one Teams full collection and one rebaseline attempt.
6. Require zero Teams findings, support gaps, reviews, stale projections, and
   vector outbox work; verify search, provenance, HANA, and UI.
7. Freeze the provider-neutral contract tests.
8. Run the bounded GitHub local-daemon canary, then every remaining source type.
9. Complete the global write-path audit and only then declare the lifecycle goal
   complete.

The rollout does not retain obsolete data for compatibility. It retains only
durable audit history and unresolved findings required to explain or block an
unsafe lifecycle decision.
