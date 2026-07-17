# Preserve provider identity across explicit scope transitions

An explicit Projection Scope transition preserves a historical Source Unit when the newly projected provider key exactly matches that Unit. Selector changes such as GitHub ref A to B to A may change document locators, versions, and content, but they do not create a new provider identity. The existing Source Unit ledger is therefore reconciled against the target snapshot before authoritative absence is applied.

Historical locator reuse without an active scope transition remains a new incarnation unless the provider attests lineage, such as an authoritative rename. This keeps delete-and-recreate distinct from selector movement. A provider-key mismatch never gains continuity from the transition alone.

This decision is provider-neutral and belongs in projection orchestration. Lifecycle planning still sees only stable Source Units, Observations, and deltas; it does not inspect Jira, GitHub, Confluence, or other provider fields.

## Exact revision return

When a scope transition returns an exact historical Unit revision, the system replays its applied claim ledger instead of asking the extractor to rediscover unchanged claims. Replay requires equality of Source, Unit, Unit revision, Observation revisions, Evidence lineage, and access context. It may reactivate only Memories retired by the authoritative Unit-removal transition; active shared Memories only regain the returning Support.

Changed content, changed access, ordinary delete/recreate, missing proof, and incompatible Memory lifecycle state do not gain replay authority. They use normal extraction and reconciliation, while malformed historical proof fails closed.
