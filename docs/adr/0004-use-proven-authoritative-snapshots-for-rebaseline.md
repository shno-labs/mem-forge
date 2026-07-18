# Use proven authoritative snapshots as the rebaseline corpus

A completed force-full snapshot defines the current rebaseline corpus only when the source contract explicitly declares authoritative collection. The snapshot must match the current source configuration, have an immutable boundary with no collection or upload failure, contain unique stable document identities, retain fully attested artifacts, and pass non-mutating provider coverage validation. Non-authoritative sources continue to replay every current document and may not infer deletion from absence.

Rebaseline atomically fences ordinary sync, validates the snapshot, resets derived lifecycle state, and replays that snapshot. Documents present only in the old index are then reconciled as authoritative absence, including legacy projections without Source Unit lineage; no compatibility bridge preserves them. Removing a document removes only its Source Support: multi-document and cross-source support remain active, and a Memory is retired only after its final active support is gone.

Every rebaseline stage must use the same process-wide document-lifecycle admission as ordinary source sync, regardless of whether execution begins in a worker or a maintenance route. A maintenance caller may not construct an unconstrained runtime; this is an execution-safety invariant and does not change snapshot authority or lifecycle semantics.

Any incomplete proof fails before reset and keeps the source gated. The rule is provider-neutral and must have SQLite/HANA parity plus add, change, rename, delete, empty-snapshot, concurrency, multi-support, and cross-source canaries for every authoritative source type.
