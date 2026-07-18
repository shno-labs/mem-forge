# Use proven authoritative snapshots as the rebaseline corpus

A completed force-full snapshot defines the current rebaseline corpus only when the source contract explicitly declares authoritative collection. The snapshot must match the current source configuration, have an immutable boundary with no collection or upload failure, contain unique stable document identities, retain fully attested artifacts, and pass non-mutating provider coverage validation. Non-authoritative sources continue to replay every current document and may not infer deletion from absence.

Rebaseline atomically fences ordinary sync, validates the snapshot, resets derived lifecycle state, and replays that snapshot. Documents present only in the old index are then reconciled as authoritative absence, including legacy projections without Source Unit lineage; no compatibility bridge preserves them. Removing a document removes only its Source Support: multi-document and cross-source support remain active, and a Memory is retired only after its final active support is gone.

Every rebaseline stage must use the same process-wide document-lifecycle admission as ordinary source sync, regardless of whether execution begins in a worker or a maintenance route. A maintenance caller may not construct an unconstrained runtime; this is an execution-safety invariant and does not change snapshot authority or lifecycle semantics.

Each sync run owns its per-document tasks. Cancellation or another non-local exit must cancel and drain every sibling task before the run releases its database and source-runtime resources; maintenance fencing must never leave detached document work behind.

Replay scalability is enforced below source adapters. The shared embedding transport bounds request batches and validates one returned vector per input, while entity-index refresh embeds only new or renamed canonical entities. Source adapters must not add provider-specific batching workarounds as their corpus grows.

Provider-backed extraction has one lifecycle write path: a Source Projection and its complete incumbent plan are applied atomically, while authoritative absence is expressed as a projected tombstone. The former raw extraction-unit `process_memories` path and direct orphan-retirement helper are removed rather than retained as alternate or compatibility engines; manual user Memory commands and compliance purge remain separate explicit authorities.

Any incomplete proof fails before reset and keeps the source gated. The rule is provider-neutral and must have SQLite/HANA parity plus add, change, rename, delete, empty-snapshot, concurrency, multi-support, and cross-source canaries for every authoritative source type.
