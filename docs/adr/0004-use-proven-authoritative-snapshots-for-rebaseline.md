# Use proven authoritative snapshots as the rebaseline corpus

A completed force-full snapshot defines the current rebaseline corpus only when the source contract explicitly declares authoritative collection. The snapshot must match the current source configuration, have an immutable boundary with no collection or upload failure, contain unique stable document identities, retain fully attested artifacts, and pass non-mutating provider coverage validation. Non-authoritative sources continue to replay every current document and may not infer deletion from absence.

Rebaseline atomically fences ordinary sync, validates the snapshot, resets derived lifecycle state, and replays that snapshot. Documents present only in the old index are then reconciled as authoritative absence, including legacy projections without Source Unit lineage; no compatibility bridge preserves them. Removing a document removes only its Source Support: multi-document and cross-source support remain active, and a Memory is retired only after its final active support is gone.

Every rebaseline stage must use the same process-wide document-lifecycle admission as ordinary source sync, regardless of whether execution begins in a worker or a maintenance route. A maintenance caller may not construct an unconstrained runtime; this is an execution-safety invariant and does not change snapshot authority or lifecycle semantics.

Each sync run owns its per-document tasks. Cancellation or another non-local exit must cancel and drain every sibling task before the run releases its database and source-runtime resources; maintenance fencing must never leave detached document work behind.

A process exit cannot prove that partially executed destructive maintenance is
safe to resume. A queued or running maintenance job therefore remains active
only while its Source Activity lease is current. A provider-neutral worker
sweep finds jobs with missing or expired leases and atomically records them as
failed, advances the Source Activity epoch to fence stale commits, and preserves
their history, gate, and findings; a later retry starts as a new explicit
attempt.

Replay scalability is enforced below source adapters. The shared embedding transport bounds request batches and validates one returned vector per input, while entity-index refresh embeds only new or renamed canonical entities. Source adapters must not add provider-specific batching workarounds as their corpus grows.

Provider-backed extraction has one lifecycle write path: a Source Projection and its complete incumbent plan are applied atomically, while authoritative absence is expressed as a projected tombstone. The former raw extraction-unit `process_memories` path and direct orphan-retirement helper are removed rather than retained as alternate or compatibility engines; manual user Memory commands and compliance purge remain separate explicit authorities.

Exact active claims from ordinary extraction are resolved relationally before vector or model-based equivalence. The lookup spans Source Units and sources in the same visibility, owner, and repository access context; Project remains a relevance dimension, not an identity boundary. A match reuses the Memory ID and attaches revision-pinned Support from the new Unit. Lifecycle Plan commit repeats the check inside the source write boundary, so a concurrent stale CREATE within that source rolls back and normal document retry replans it as Support attachment. Explicit Agent Knowledge concept/claim writes use their dedicated atomic commit authority and retain their own concept identity contract instead of using this admission; every ordinary candidate channel, including active exact lookup, rebaseline reactivation, vector recall, and the commit guard, therefore excludes Memories held by Agent Claims. This is deterministic admission, not a replay ledger or semantic consolidation.

Any incomplete proof fails before reset and keeps the source gated. The rule is provider-neutral and must have SQLite/HANA parity plus add, change, rename, delete, empty-snapshot, concurrency, multi-support, and cross-source canaries for every authoritative source type.
