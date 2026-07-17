# Preserve provider identity across explicit scope transitions

An explicit Projection Scope transition preserves a historical Source Unit when the newly projected provider key exactly matches that Unit. Selector changes such as GitHub ref A to B to A may change document locators, versions, and content, but they do not create a new provider identity. The existing Source Unit ledger is therefore reconciled against the target snapshot before authoritative absence is applied.

Historical locator reuse without an active scope transition remains a new incarnation unless the provider attests lineage, such as an authoritative rename. This keeps delete-and-recreate distinct from selector movement. A provider-key mismatch never gains continuity from the transition alone.

This decision is provider-neutral and belongs in projection orchestration. Lifecycle planning still sees only stable Source Units, Observations, and deltas; it does not inspect Jira, GitHub, Confluence, or other provider fields.

## Exact revision return

When a scope transition returns an exact historical Unit revision, stable provider identity lets the system reuse the Source Unit and Observation lineage. It does not restore a historical Memory snapshot. The returned Unit goes through normal extraction and reconciliation against the current cross-source Memory state.

Semantically equivalent output may reuse a current canonical Memory through reconciliation; otherwise the system creates a new Memory identity. Changed content, changed access, ordinary delete/recreate, missing proof, and incompatible lifecycle state follow the same path. This keeps scope re-entry subject to current lifecycle and cross-source authority instead of a historical replay optimization.

## Repeated cycles and retries

Transition identity includes the preceding transition, so A to B, B to A, and a later A to B are three cycles. Concurrent creation and retries from the same predecessor still resolve to one transition.

Destructive lifecycle identity uses the transition ID for scope changes and the durable Source Sync Run plus lease-attempt identity for ordinary provider updates. A failed run may adopt a newer coalesced input boundary, so each lease attempt is a new reconciliation cycle; the extractor's random run ID remains telemetry only. A re-entry retry remains idempotent at the lifecycle-plan boundary, while a later cycle always receives a new Lifecycle Plan even when it reaches the same tombstone revision.

Before the successful run owner releases its lease, it makes one source-scoped delivery attempt for every pending or failed lifecycle-vector task selected by the bounded outbox batch. Delivery failure remains durable outbox state and never changes the already-authoritative relational graph or the source run's successful terminal state.
