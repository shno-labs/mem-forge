# Create Memories within the Source Unit

Status: Accepted

Date: 2026-09-26

## Context

A Source Unit revision decides its own Memories synchronously: candidate
admission merges same-round duplicates, Sparse Relation compares every admitted
Candidate with every active old Memory of the Unit, and the
SupportRelationCoordinator combines Relation with Support Assessment
([ADR 0034](0034-unify-incremental-support-and-claim-assessment.md)).
Relations with Memories of other Source Units are discovered after the commit and
recorded as annotations ([ADR 0037](0037-record-cross-document-conflicts-as-relations.md)).

Source sync also ran a synchronous identity step between the coordinator and the
Lifecycle Plan ([ADR 0006](0006-bound-memory-identity-recall-before-semantic-proof.md),
and the Same-Unit identity backstop of ADR 0034). For each ADD Candidate it
looked for an active Memory with the exact claim text in the same access
context, and otherwise recalled up to `DEDUP_CANDIDATE_LIMIT` Memories of any
Unit or Source by vector proximity and shared entities and asked a sparse
relation catalog request (`memory-relation-v4-sparse`) whether one of them was
equivalent. A match made the Plan attach the Candidate's Evidence Unit as
Support to the matched Memory instead of creating one. Old Memories that the
round deleted, superseded, updated or sent to Review were excluded from the
recall, and the store rejected a Plan that created a claim whose exact text had
meanwhile become an active Memory elsewhere.

That step made the Unit's commit depend on Memories owned by other Units, and it
caused four problems:

- The boundary "same document synchronous, cross document asynchronous" had an
  exception. A revision read Memories of other Units, wrote Support onto them,
  and could fail because of them.
- Merging hides disagreement between sources. When a Jira issue and a
  Confluence page state the same claim, they share one Memory. When Jira later
  updates the claim, the shared Memory loses the Jira Support and stays active on
  the Confluence Support with the old text. Nothing tells the reader that Jira
  now says something else. With one Memory per source, the Jira Memory is
  updated or superseded by its own Unit, the Confluence Memory keeps the old
  text, and cross-document discovery labels the pair `updates`.
- Merging is not needed to keep knowledge that one source drops. A Memory
  created from another source stays active and searchable on its own Support.
- Bounded recall is not reliable. On 2026-09-26 the Unit SFPAY-166801 in a
  development workspace failed on every sync: its identity request carried 53
  candidate pairs, and the recall list of one new claim did not contain an obvious
  equivalent Memory that the same request listed for another claim. The model
  reported the pair anyway, the catalog rule that each Candidate may only name
  its own allowed Memories rejected the response, the one correction was
  rejected the same way, and the Unit could not commit.

The step also cost, for every revision that added Candidates, one model
request, one batched embedding and vector query, an entity query per
Candidate, an exclusion set that had to agree with the planner's decisions, an
attach path with its own Plan rules, and a store guard in both SQLite and HANA.

## Decision

Memory creation in source sync depends only on the Source Unit being processed.

- Every admitted ADD Candidate of a Source Unit revision that the coordinator and
  the planner keep as an ADD creates its own Memory with its own Evidence Unit
  Support. Source sync never attaches a Candidate to a Memory of another Source
  Unit, whether the match is semantic or exact text.
- Duplicates within the Unit are decided only by candidate admission's same-round
  deduplication and by Sparse Relation, which reads every active old Memory of
  the Unit. A Relation omission is not repaired by a later step.
- Sameness across Source Units, including across Sources, is recorded only by
  the asynchronous cross-document relation discovery of ADR 0037 with the label
  `equivalent`. Discovery never merges, retires or rewrites a Memory.
- A Lifecycle Plan attaches Support only to a Memory it creates or to an old
  Memory in its own incumbent ledger. Plan validation rejects any other
  `ATTACH_SUPPORT`.
- The store applies a Plan without looking up active Memories by claim text.
  Two Units may hold active Memories with the same text.
- Entity Resolution stays in source sync. Its entity links are stored with each
  new Memory, and relation discovery uses shared entities as one of its
  candidate channels.
- Sync still commits the run's Units, including deferred commits, before it
  detects deletions, because absence is authoritative only when every document
  of the run committed. A Memory that already carries Support from several Units
  keeps the deferred commit path when one of its Units supersedes or retires it.

The following are removed:

- `memory/identity_resolver.py` and `memory/sparse_relation_classifier.py`, the
  `MemoryPairClassifier` protocol in `memory/relation_classifier.py`,
  `LiteLlmStructuredClient.discover_memory_relations`, and
  `MemoryRelationCatalogResponse` with its row and edge models.
- `MemoryEngine.identity_resolver`, `_build_memory`, the identity call, its
  statistics (`identity_resolution_*` and `corroborated`) and the corroboration
  fields of the prepared lifecycle inputs.
- `identity_excluded_incumbent_ids`, the corroboration parameters of
  `build_lifecycle_plan`, the identity attach branch, and the rule that rejects
  an identity attach to an old Memory the Plan does not keep.
- The `MemoryStore` identity candidate queries and `_embed_many`, and the
  `RelationalStore` methods `find_active_exact_claim_candidate`,
  `find_active_exact_claim_candidates`, `list_active_ordinary_claim_memories` and
  `find_active_ordinary_claim_memories_by_entities`.
- The exact claim guard in Plan apply and `ClaimIdentityPolicy`, which existed
  only to switch that guard off for agent claims.

User-created Memories (`create_memory`) keep their own near-duplicate check in
`MemoryStore.deduplicate_and_insert`; this decision covers source sync only.

## Consequences

- A revision reads and writes only its own Unit's Memories, its new Memories and
  its own Evidence. It makes no model call about other Units.
- Search can return the same knowledge once per Source Unit. Search already
  leaves out a Memory that is `equivalent` to a higher-ranked returned Memory
  (ADR 0037), so a duplicate is visible until discovery labels the pair, or
  when discovery misses the pair. Further folding of search results is out of
  scope until duplicates are shown to matter.
- A duplicate within one Unit that Sparse Relation misses becomes a second
  Memory. Discovery compares a Memory only with Memories of other documents, so
  the pair stays unlabeled.
- Every new Memory now gets a relation discovery request, including those that
  identity previously attached to an existing Memory.
- A user correction or retirement acts on one Memory. It does not change the
  Memory it is `equivalent` to in another Source Unit.
- When a Source Unit's provider identity changes, the new Unit creates new
  Memories and the old Unit's Memories retire once their last Support is
  removed. Memory IDs were not promised to survive this, and corrections bound
  to the old Memory IDs do not move to the new ones.
- Existing Memories that carry Supports from several Units stay valid. Each
  Unit maintains its own Support on them, and retirement still requires that no
  active Support remains.
- A revision with ADD Candidates makes one model request and one embedding call
  fewer, and no recall queries.
- `memory-relation-v4-sparse` leaves the lifecycle operation input manifest, so
  `operation_input_hash` changes for every revision. The `candidate_admission`
  and `claim_assess` work journals include that hash in their scope, so a
  revision that was prepared but not committed before the upgrade repeats those
  requests once. Committed revisions are not affected. Relation runs stored
  with `memory-relation-v4-sparse` remain readable history.

## Cloud impact

Cloud composes this package and takes these changes with one pin update:

- Storage protocol (`src/memforge/storage/adapters/protocols.py`):
  `find_active_exact_claim_candidate`, `find_active_exact_claim_candidates`,
  `list_active_ordinary_claim_memories` and
  `find_active_ordinary_claim_memories_by_entities` are removed from
  `RelationalStore`. The HANA workspace database implementations and the
  `HanaRelationalStore` delegates are deleted in the same pin update, together
  with their signature and behavior tests.
- Plan apply: the HANA exact claim guard
  (`_assert_no_active_exact_claim_conflicts_on_connection`) and the
  `ClaimIdentityPolicy` switch are deleted, so `_apply_lifecycle_plan_sync` and
  the agent claim apply call one Plan apply. Without this change a Cloud Unit
  that states a claim already active in another Unit fails its commit with
  "lifecycle plan exact claim stale guard failed" on every sync.
- `VectorStore.query_many` and `within_dedup_threshold` stay: the retrieval
  evaluation runner and user-created Memory deduplication use them.
- `LiteLlmStructuredClient` loses `discover_memory_relations`. Its constructor
  does not change. `MemoryEngine`'s constructor and `pair_classifier` do not
  change, so `proxy/external_runtime.py` needs no change. Test stubs that define
  `discover_memory_relations` drop it.
- Contract strings: `memory-relation-v4-sparse` is no longer produced and no
  longer part of the lifecycle operation input manifest. The error text
  "lifecycle plan exact claim stale guard failed" and "identity attach targets an
  old Memory this Plan deletes, replaces or reviews" disappear, and a Plan that
  attaches Support outside its incumbent ledger and its created Memories fails
  validation. Sync statistics lose the `identity_resolution_*` keys.
- No HANA migration, no SQLite migration and no configuration change. Model
  access through LiteLLM `sap/` routes and environment-only configuration are
  unchanged; one model request per revision with ADD Candidates goes away.

## Related

- [ADR 0006](0006-bound-memory-identity-recall-before-semantic-proof.md):
  pre-creation identity recall, superseded here.
- [ADR 0034](0034-unify-incremental-support-and-claim-assessment.md): same-Unit
  admission, Relation and coordination. Its Same-Unit identity backstop is
  superseded here.
- [ADR 0037](0037-record-cross-document-conflicts-as-relations.md): the
  asynchronous `equivalent`, `updates` and `contradicts` relations, which are now
  the only record of sameness across Source Units.
- [Source sync to Memory](../design/source-sync-to-memory.md): the complete flow.
