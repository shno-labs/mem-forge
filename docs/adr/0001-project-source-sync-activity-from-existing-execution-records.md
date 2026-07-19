# Project source sync activity from existing execution records

Local collection jobs, server processing runs, and lifecycle-maintenance jobs keep their independent durable lifecycles because they have different owners, leases, retries, and storage transactions. The Sources UI consumes one Source Sync Activity read model projected from those records, rather than introducing a cross-store master operation or extending one execution record to own the others.

This keeps execution recovery local to each existing state machine while giving every source type one refresh-safe progress contract and presenter. Server processing persists its latest Progress Snapshot on its run; local collection exposes the snapshot already persisted with its job; lifecycle maintenance contributes its durable status without pretending to have per-document progress. Active maintenance outranks stale terminal sync history, uses provider-neutral memory-update language, and blocks conflicting source mutations in the UI while storage remains authoritative. Completed maintenance shows a short terminal acknowledgement and then becomes visually quiet while still suppressing obsolete failed-sync history; failed maintenance remains actionable until newer activity supersedes it. The projection selects the relevant activity and never treats progress-delivery failure as source-sync failure.

When local collection successfully starts server processing, its terminal
result records the returned `SourceSyncRun` ID as an immutable handoff receipt.
A local sync cannot report success without that identity, and an idempotent
terminal retry must repeat the same identity. This correlates the two existing
state machines without a master execution record, replay ledger, or
cross-store transaction.
