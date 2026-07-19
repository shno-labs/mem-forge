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
attempt. Recovery is isolated per job so one malformed orphan cannot prevent
other stale jobs from being fenced.

Destructive reset renews the exact maintenance capability immediately before
the reset. Every maintenance mutation transaction then validates the durable
lease identity, capability, source, epoch, and expiry while holding the source
row; it repeats the validation before commit. Projection commits retain their
source-row epoch fence. Losing authority therefore fails closed for document,
gate, finding, evidence, reference, support, reset, and projection writes
instead of allowing a stale executor to continue after recovery.

A resolved cutover finding is terminal history. Retrying its upsert is a full
no-op, including the Source gate; it cannot reopen the finding or re-gate the
Source after validated resolution.

One finding ID is permanently bound to its Source and Memory. Upsert accepts
only open findings and may refine the reason and diagnostic payload while the
finding remains open; only the explicit resolution path may change its status.

When a provider-neutral lifecycle plan, source rebaseline, or final Source
Support removal makes a Memory terminal, the same transaction marks every
pending Memory Review that names that Memory, including related challengers,
as stale. Review history is preserved; a review may not remain actionable
against a retired or superseded target.

Rebaseline acceptance includes the source-scoped lifecycle vector outbox.
After authoritative replay, the maintenance flow drains successive bounded
outbox batches while they make progress, before running the gate-opening
lifecycle audit. A remaining failed or non-progressing task fails maintenance
and leaves destructive lifecycle gated. Ordinary document sync remains
decoupled from vector delivery failure because its relational lifecycle commit
is already authoritative.

Replay scalability is enforced below source adapters. The shared embedding transport bounds request batches and validates one returned vector per input, while entity-index refresh embeds only new or renamed canonical entities. Source adapters must not add provider-specific batching workarounds as their corpus grows.

Provider-backed extraction has one lifecycle write path: a Source Projection and its complete incumbent plan are applied atomically, while authoritative absence is expressed as a projected tombstone. The former raw extraction-unit `process_memories` path and direct orphan-retirement helper are removed rather than retained as alternate or compatibility engines; manual user Memory commands and compliance purge remain separate explicit authorities.

Exact active claims from ordinary extraction are resolved relationally before vector or model-based equivalence. The lookup spans Source Units and sources in the same visibility, owner, and repository access context; Project remains a relevance dimension, not an identity boundary. A match reuses the Memory ID and attaches revision-pinned Support from the new Unit. Lifecycle Plan commit repeats the check inside the source write boundary, so a concurrent stale CREATE within that source rolls back and normal document retry replans it as Support attachment. Explicit Agent Knowledge concept/claim writes use their dedicated atomic commit authority and retain their own concept identity contract instead of using this admission; every ordinary candidate channel, including active exact lookup, rebaseline reactivation, vector recall, and the commit guard, therefore excludes Memories held by Agent Claims. This is deterministic admission, not a replay ledger or semantic consolidation.

Any incomplete proof fails before reset and keeps the source gated. The rule is provider-neutral and must have SQLite/HANA parity plus add, change, rename, delete, empty-snapshot, concurrency, multi-support, and cross-source canaries for every authoritative source type.
