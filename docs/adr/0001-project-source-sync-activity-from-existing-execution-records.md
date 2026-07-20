# Project source sync activity from existing execution records

Local collection jobs, server processing runs, and lifecycle-maintenance jobs keep their independent durable lifecycles because they have different owners, leases, retries, and storage transactions. The Sources UI consumes one Source Sync Activity read model projected from those records, rather than introducing a cross-store master operation or extending one execution record to own the others.

This keeps execution recovery local to each existing state machine while giving every source type one refresh-safe progress contract and presenter. Server processing persists its latest Progress Snapshot on its run; local collection exposes the snapshot already persisted with its job; lifecycle maintenance contributes its durable status without pretending to have per-document progress. Active maintenance outranks stale terminal sync history, uses provider-neutral memory-update language, and blocks conflicting source mutations in the UI while storage remains authoritative. Completed maintenance shows a short terminal acknowledgement and then becomes visually quiet while still suppressing obsolete failed-sync history. A failed maintenance attempt remains in lifecycle history, but remains actionable on the Source row only while current lifecycle state is still blocking: the Source is gated, an open cutover finding exists, or lifecycle vector delivery remains incomplete. The projection selects the relevant activity and never treats progress-delivery failure as source-sync failure.

A terminal source-sync failure remains available through Last sync details, but
the Source row presents it as actionable only when the current viewer has the
Source capability to run sync. This prevents a managed or read-only Source from
offering an impossible Retry action while preserving the execution record.
Source sync capability is derived from the Source Gene's declared
`execution_kinds`; a Source type with no execution kind never enters manual,
scheduled, or worker-owned ordinary sync. Historical sync records remain
auditable, but are not projected as current Source activity for such a type.

When local collection successfully starts server processing, its terminal
result records the returned `SourceSyncRun` ID as an immutable handoff receipt.
A local sync cannot report success without that identity, and an idempotent
terminal retry must repeat the same identity. This correlates the two existing
state machines without a master execution record, replay ledger, or
cross-store transaction.
