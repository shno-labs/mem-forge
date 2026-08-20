# Separate conversation coverage from content and retention

Status: Accepted

## Context

Conversational connectors have two independent facts. The content plane states what messages were observed and projects them into durable Source Units. The coverage plane proves whether the connector completely checked the target scope required to treat an omission or an explicit age policy as destructive. Teams previously transported coverage as an empty `teams_scope_attestation` pseudo-unit and treated `max_age_days` as both initial collection history and a rolling removal horizon. That shape made control evidence look like corpus content and allowed the clock alone to remove old Support.

## Decision

Collection produces durable content items plus typed, attempt-scoped `ProjectionScopeAttestation` values. An attestation identifies its subject, collection attempt, target scope fingerprint, optional scope transition, and provider evidence. The existing immutable Collection Manifest binds and stores those values for the run and its retries. Attestations never enter Source Unit, Observation, Document, Evidence, Memory, Plan, Review, or corpus tables. `SourceProjectionAdapter` owns provider validation; Evidence and Lifecycle consume only provider-neutral projections and never branch on source type.

Teams content remains a stable thread or time-block Source Unit. The internal window policy is versioned as `teams-window-v1`; its 60-minute grouping and 100-message context budget are not user intent or projection scope. Existing block identities retain their recorded policy version, and a future policy version cannot reinterpret an existing block. Context-budget splitting remains computation detail rather than a business or lifecycle state.

Teams configuration separates:

- `initial_history_days`, default 14, which controls initial or expanded backfill and never authorizes removal;
- `rolling_retention_days`, default Forever (`None`), with explicit one-year and three-year choices;
- selected conversation identities, which remain the user-visible projection scope.

An existing `max_age_days` value normalizes to `initial_history_days`. It never becomes rolling retention. Legacy `conversation_gap_minutes` and `max_block_messages` are removed from public configuration and replaced by the versioned internal policy.

Provider absence and configured retention remain distinct removal reasons. A bounded successful poll may tombstone only an omitted prior window wholly inside the poll's proven interval. Explicit rolling retention may tombstone an older window only when the same collection attempt carries valid target-scope evidence and the stored window end precedes that attempt's exact retention cutoff. Missing, duplicate, stale, inaccessible, malformed, or incomplete evidence fails closed and preserves Support. Removing one Support retires a Memory only when no other active Support remains.

For example, let the previous windows be `{W1, W2, W3}` and the current returned windows be `{W1, W2}`. Content alone cannot distinguish “W3 was deleted” from “authentication or pagination missed W3.” Without valid coverage evidence, W3 remains supported and the destructive transition fails. A valid same-attempt attestation upgrades the omission to authoritative absence, allowing the normal Lifecycle Plan to remove W3's exact Support. The attestation does not itself remove anything and never becomes a Memory status.

## Falsifiable behavior

| Scenario | Required result |
|---|---|
| Normal incremental sync | Reconcile only returned or explicitly tombstoned windows; unproved absence preserves Support. |
| First import | Collect up to Initial History; an empty but completely checked target may complete with a zero-item manifest and attestations. |
| Initial History expansion | Earlier content may be added; no existing Support is removed. |
| Clock advancement with unchanged Initial History | Previously supported old windows remain supported. |
| Explicit rolling retention | Windows older than the exact run cutoff may be tombstoned only with valid same-attempt scope evidence. |
| Selector change | Removed conversations are reconciled from complete paged server inventory; target conversations require complete same-attempt evidence. |
| Window-policy version change | Existing window identity and membership are not silently rewritten; new policy behavior is explicit by version. |
| Partial or failed poll | No destructive transition; current Support remains. |
| Retry | Reuses the immutable manifest and its exact attempt evidence; stale or changed evidence is rejected. |

## Considered options

- Keep the pseudo-unit: rejected because control evidence would continue to travel through content validation and invite accidental persistence.
- Add a durable attestation subsystem or lifecycle status: rejected because the existing immutable Collection Manifest already owns attempt inputs and retries.
- Treat initial history as retention: rejected because collection breadth is not user authorization to delete established knowledge.
- Make grouping and context limits user-configurable projection scope: rejected because partitioning and batching are connector implementation policy, not product lifecycle intent.

## Consequences

SQLite and HANA store the same serialized attestation tuple on the existing manifest and return the same typed values to the durable worker. Provider validation remains inside `SourceProjectionAdapter`; Cloud adds only adapter parity and no Cloud-specific lifecycle branch or ADR. Public UI and config show selected conversations, Initial History, and explicit Rolling Retention consequences.

MemForge Rolling Retention is a Source Support policy, not a claim that Microsoft 365 compliance copies were deleted. Microsoft documents Teams retention as an explicit policy based on message creation time, with one- and three-year examples, and warns that client visibility differs from compliance retention state. See [Learn about retention for Teams](https://learn.microsoft.com/en-us/purview/retention-policies-teams) and [Manage retention policies for Microsoft Teams](https://learn.microsoft.com/en-us/microsoftteams/retention-policies).

## Non-goals

This decision adds no Graph fallback, webhook, provider repair, historical rebaseline, synthetic production write, new Memory status, attestation review queue, or compliance purge. It does not make extraction batches durable identity and does not infer that a missing live search result was previously retired.
