# Document Memory Lifecycle

This document defines how document updates mutate memories when a claim has
multiple provenance edges. The core rule is deliberately small:

```text
A document owns its support edges.

A memory row can be mutated directly only when the mutation remains compatible
with every valid support edge, or every conflicting support edge is owned by the
current operation.
```

## Model

```text
Memory
  id
  content
  status: active | pending_review | superseded | retired

Support edge
  memory_id
  doc_id
  support_kind: extracted | corroborated
  excerpt
```

A memory stays active while at least one valid support edge remains. Extracted
support gives the current document authority to propose claim mutations.
Corroborated support is evidence only: it can be added, refreshed, or removed by
the supporting document, but it cannot rewrite claim content.

A valid support edge points to an existing source document whose latest
normalized content still directly supports the memory. For extracted support,
validity is maintained by same-document reconciliation. For corroborated support,
validity is maintained by supporter verification and excerpt refresh/removal.

## Update Flow

```text
normalize updated document
  -> choose update mode
  -> extract RawMemory candidates from changed content
  -> value-sensitive dedup against active and pending memories
  -> same-document reconciliation for current-doc extracted memories
  -> supporter verification for corroborated and related memories
  -> contradiction classification for new or changed active claims
  -> MemoryStore applies lifecycle/index changes
```

Same-document reconciliation may only see active memories where the current
document has `support_kind = extracted`. Candidate dedup is broader: it checks
the full active/pending memory space before deciding whether a candidate is new.

## Operations

### ADD

Insert a memory and add current-document extracted support when no equivalent
active or pending memory exists.

If an equivalent memory exists, do not insert a duplicate. Add or refresh support
on the existing memory instead.

Equivalence is value-sensitive. Similar text with a changed version, date,
environment, owner, status, or other material value is not equivalent.

### UPDATE

Update an existing memory in place only for canonical wording changes where all
valid support edges remain compatible with the new content. If any support edge
still validates the old wording but not the new wording, create a review case.

### SUPERSEDE

Supersede when the current document extracted the old claim, the update materially
replaces it, and no remaining support edge validates the old claim as current.

If another support edge still supports the old claim, stage a challenger and
create a review case. The incumbent remains active until review resolves.

### DELETE

DELETE means remove the current document's support edge. It does not hard-delete
the memory. If no valid support remains after removal, MemoryStore retires the
memory and removes search indexes. If corroborated support remains, the memory
stays active but future content mutation requires review or a new extracted owner.

### Review

Review is a case over a proposed operation. The incumbent usually remains active.
`pending_review` memory status is reserved for hidden challengers or hidden
suspect memories, not for every reviewed operation.

An active incumbent may temporarily retain only the prior-revision Support
edges that its durable Review explicitly stages for `REMOVE_SUPPORT`. Those
edges are contested rather than current. Storage validation continues to
reject every unrelated stale edge and every source or lineage mismatch; the
presence of a Review is never a Plan-wide validation bypass.

When a later lifecycle transaction makes the incumbent terminal, that same
transaction marks every pending proposal Review and relation/conflict Review
that targets the Memory as stale. Review rows remain durable history, but no
Review remains actionable against a retired or superseded Memory.

An approval Plan resolves its target Review before applying the approved
mutations inside the same transaction. This prevents terminal-review cleanup
from staling the Review being approved; if any approved mutation fails, the
Review resolution rolls back with the rest of the Plan.

Create review when:

- a mutation would conflict with another valid support edge
- a memory has only corroborated support and needs content mutation
- a model proposes lifecycle action outside current-document authority
- a high-risk support removal would retire an important memory; the current
  policy treats 3 or more support edges as high-risk
- cross-document classification finds a contradiction or ambiguous temporal claim

Cross-document differences are classified before action:

```text
CONTRADICTION | TEMPORAL | CLARIFICATION | UNRELATED
```

Only contradictions or ambiguous replacements should quarantine a challenger.

Cross-document candidate discovery is not the destructive lifecycle ledger. It
retrieves bounded IDs from entity, vector, and lexical channels, fuses them with
RRF, applies exact access/provenance predicates to lightweight rows, and loads
full Memory content only for the final candidates. A discovery result may add a
Relation or Review; it cannot supersede or retire another source's Memory. The
same-source reconciliation path separately retains complete coverage of every
directly affected incumbent.

## Case Matrix

| # | Situation | Correct operation |
|---:|---|---|
| 1 | Doc A extracts a new claim and no equivalent memory exists. | Insert active memory M and add Doc A extracted support. |
| 2 | Doc B extracts the same claim as active M from Doc A. | Do not insert a duplicate. Add Doc B extracted support to M. Canonical wording may refresh only if every support validates it. |
| 3 | Doc B extracts a near duplicate with a critical value change, such as PostgreSQL 15 to PostgreSQL 16. | Do not attach as equivalent support. Stage challenger N, classify against M, and create review if contradictory. |
| 4 | Doc A is the only support and changes wording without changing meaning. | Direct UPDATE M and reindex. |
| 5 | Doc A is the only support and materially changes the claim. | Direct SUPERSEDE: old M becomes superseded, replacement N becomes active. |
| 6 | Doc A changes the claim, but Doc B still corroborates the old claim. | No direct supersede. Stage challenger/review because Doc B remains valid old evidence. |
| 7 | Doc A changes the claim and Doc B is revalidated as supporting the new claim. | Direct mutation is allowed because Doc A has extracted authority and Doc B no longer conflicts. Doc B's corroborated support proves compatibility; it does not authorize the rewrite. |
| 8 | Doc A removes its extracted claim and Doc B also extracted the same claim. | Remove Doc A extracted support only. M stays active due to Doc B extracted support. |
| 9 | Doc A removes the last extracted support, but Doc B corroborated support remains. | Remove Doc A support. M stays active and searchable, but content mutation requires review or a new extracted owner. |
| 10 | Doc A removes the only support. | Remove Doc A support. MemoryStore retires M and removes search indexes. |
| 11 | Doc B previously corroborated M and still directly supports it after update. | Refresh Doc B corroborated support/excerpt only. |
| 12 | Doc B no longer supports M, but Doc A still extracted it. | Remove Doc B corroborated support. M stays active. |
| 13 | Doc B was the only support and no longer supports M. | Remove Doc B support. MemoryStore retires M. Gate review first when policy marks the retirement high-risk. |
| 14 | Doc A says "in 2025 Service A used PostgreSQL 15"; Doc B says "in 2026 Service A uses PostgreSQL 16". | Classify TEMPORAL. Keep scoped/temporal memories or create temporal relation/review if ambiguous. |
| 15 | Doc A says production uses PostgreSQL 15; Doc B says staging uses PostgreSQL 16. | Classify CLARIFICATION or UNRELATED by environment scope. Keep both; no supersede. |
| 16 | Model asks Doc B to DELETE M, but Doc B only has corroborated support. | Reject lifecycle decision and audit authority rejection. Supporter may separately remove Doc B support if unsupported. |
| 17 | Decision snapshot says Doc A is sole extracted owner, but Doc C adds extracted support before commit. | Optimistic support-set check fails. Do not commit direct mutation; escalate to review. |
| 18 | Reviewer approves cross-document challenger N over incumbent M. | Resolve old support first: remove stale support edges, preserve temporal support on a scoped/temporal incumbent, or mark old support overridden by the reviewer. Then MemoryStore activates N and supersedes or retires the old current claim. |
| 19 | Reviewer rejects challenger N. | Retire or hide N. M stays active. |
| 20 | A retired memory's claim reappears later. | Insert a fresh active memory with new extracted support. Do not automatically resurrect retired M. Dedup active/pending by default. |

## Audit Requirements

Audit must make authority and side effects visible:

```text
document_update_strategy_selected
memory_change_extraction_completed
reconciliation_failed
reconciliation_decision_returned
reconciliation_authority_rejected
reconciliation_review_gated
memory_insert_committed
memory_update_committed
memory_supersede_committed
source_support_added
source_support_removed
source_support_removal_retired_memory
cross_doc_contradiction_recorded
memory_pending_review_committed
memory_retire_committed
fts_* / chroma_* / index_operation_failed
```

Lifecycle-changing events should include the current document id, support kind,
remaining support count where relevant, challenger id, review id, and the reason
the operation was allowed or routed to review.

## Implementation Invariants

```text
All lifecycle/index writes go through MemoryStore.
Same-document reconciliation only mutates current-doc extracted memories.
Corroborated support never grants content-mutation authority.
Support removal can retire a memory only when no valid support remains.
Direct UPDATE/SUPERSEDE requires every remaining support edge to validate the new claim.
Cross-document contradictions create review; they do not automatically mutate incumbents.
```
