# Make Evidence Unit Support the only Support model

Status: Accepted

Date: 2026-09-26

## Context

[ADR 0030](0030-compile-revision-pinned-evidence-fragments.md) introduced
Evidence Unit Support (`evidence-unit-set-v2`): one Support Assertion names one
complete Evidence Unit, and lifecycle Plans add and remove Support by Evidence
Unit identity. Workspaces moved to it through a one-time Support cutover, and
the code kept the earlier reference-scoped Support (`reference-set-v1`) beside
it: a Support scope marker, a branch in every Support read and write, the
extraction contract `projection-extraction-v8` selected by that marker, and the
per-Source lifecycle cutover subsystem (legacy lineage backfill, recovery jobs,
findings and their repair, unprovable retirement, and Source rebaseline).

Every Cloud workspace and every known OSS workspace now records
`evidence-unit-set-v2`. The two-version code had become a source of defects
rather than a compatibility path:

- Memory Evidence reads merged frozen reference-scoped rows into the result, so
  Evidence whose Unit Support had been removed reappeared as legacy groups.
- Finding resolution and unprovable retirement read only reference-scoped rows.
- Correction rollback called a document deletion that refuses documents after
  the cutover, which masked the original error and left the correction document.
- The lifecycle cutover subsystem could only write reference-scoped Support.
  Under Evidence Unit Support its backfill failed and its rebaseline refused
  every request.

## Decision

Evidence Unit Support is the only Support model.

- Storage keeps no reference-scoped Support table, cutover report, or cutover
  lease. New SQLite workspaces never create them, and a migration drops them
  from existing workspaces.
- The Support scope marker stays as one row. SQLite checks it when a workspace
  opens and refuses to open a workspace whose marker is not
  `evidence-unit-set-v2`. Cloud keeps the row as the first lock of its
  lock order. No code branches on the marker.
- An older SQLite workspace that has no reference-scoped Support rows moves to
  Evidence Unit Support when it opens. One that still holds such rows refuses to
  start and tells the operator to finish the cutover with an earlier version or
  to rebuild the workspace. This version contains no conversion code.
- `projection-extraction-v9` is the only extraction contract. Its version string
  and the Evidence Unit scope string stay unchanged because both are hashed into
  stored identities: derivation and batch ids, Evidence Unit ids, and Support
  set hashes. Stored derivations under any other contract are superseded, never
  resumed. Offline derivation replay plans the same Evidence work and therefore
  requires each case to pin the access context and inference capability hashes
  of the derivation it came from.
- The lifecycle cutover subsystem is removed: backfill, recovery jobs, findings,
  finding repair, unprovable retirement, Source rebaseline, rebaseline
  reactivation, and the maintenance jobs that fenced sync, local-agent jobs, and
  Source writes. The lifecycle gate stays. A new Source enables it at creation;
  a Source without an enabled gate stays gated. Support recovery is forward-only:
  a later sync of the current Source revision is the only way to attach new
  Support.
- A pending lifecycle Review whose proposal names Support without Evidence Unit
  ids, or a mutation type this version no longer applies, fails its stale guard.
  Approval marks it stale and returns a conflict.
- `legacy_limited` stays a readable stored value on Evidence Units, Support
  provenance rows, and relation runs. Nothing writes it, and the admin API, MCP
  proxy, and admin UI no longer show it.

## Consequences

- Every Support read and write has one path and one invariant check.
- There is no operator path that rebuilds a Source's Memories. If one is needed,
  it is a new feature built on Evidence Unit Support.
- The Source activity epoch is still compared on every fenced write, but no
  operation advances it now that lifecycle maintenance jobs are gone. Whether to
  keep this fence is a separate decision.
- Lifecycle Plan payloads no longer carry a Support scope version or Evidence
  Reference ids, so a Plan staged before the upgrade and retried after it fails
  its payload comparison. Upgrades need no staged Plans in flight.

## Cloud impact

Cloud composes this package and must take these changes when it upgrades its
pin:

- Storage protocol (`src/memforge/storage/adapters/protocols.py`): the
  reference-scoped Support methods, the Support cutover methods,
  `get_support_scope_version`, `rebaseline_source_lifecycle`,
  `find_rebaseline_reactivation_candidate(s)`, `list_legacy_memory_provenance`,
  `count_active_source_memories`, `gate_destructive_lifecycle`, every cutover
  finding and lifecycle backfill job method, and
  `get_active_memory_support_evidence` are removed. The HANA adapter,
  its delegates, and the core-integration method lists drop them.
- Data types: `SupportScopeVersion` becomes the string constant
  `EVIDENCE_UNIT_SUPPORT_SCOPE`; `ActiveMemorySupportState`, `StaleGuard`,
  `LifecycleMutation`, `ContestedSupportEdge`, and `MemoryEvidenceUnitProjection`
  lose their reference-scoped and `legacy_limited` fields; the cutover finding,
  backfill job, legacy provenance, and rebaseline result types and
  `SourceSyncMode` are removed.
- `run_source_sync` loses its `execution_mode` and `lifecycle_job_id`
  parameters, so `proxy/external_runtime.py` changes its signature and call.
- Cloud's worker stops recovering stale lifecycle jobs and checking the active
  lifecycle job fence, and the local-agent job route drops the same fence.
- The proxied admin app no longer serves the Source lifecycle backfill,
  rebaseline, and finding repair routes. The Source lifecycle view no longer
  returns jobs and findings, the Source list no longer returns
  `lifecycle_maintenance`, and Memory Evidence no longer returns
  `support_scope_version` or `legacy_limited`.
- HANA keeps the Support scope marker row and its lock, and compares it with
  `EVIDENCE_UNIT_SUPPORT_SCOPE` at startup. Dropping the reference-scoped and
  lifecycle cutover HANA tables is a Cloud migration of its own.
- Model access, LiteLLM `sap/` routes, and environment-only configuration do not
  change.

## Related

- [ADR 0030](0030-compile-revision-pinned-evidence-fragments.md): Evidence
  Fragments and Evidence Unit Support. Its Support cutover and legacy-limited
  recovery sections are superseded here.
- [ADR 0004](0004-use-proven-authoritative-snapshots-for-rebaseline.md): Source
  rebaseline, removed here.
- [ADR 0034](0034-unify-incremental-support-and-claim-assessment.md): Support
  assessment on the only Support model.
