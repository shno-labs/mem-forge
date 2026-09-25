# Bound cross-document relation discovery before semantic classification

Status: Accepted. Its Review output, relation labels and reuse of identity
completion snapshots are superseded by
[ADR 0037](0037-record-cross-document-conflicts-as-relations.md); bounded
retrieval, leasing and fenced completion remain in force.

## Context

Cross-document relation detection previously loaded full Memory rows from one
shared-entity query capped at 200. The cap was then treated as incomplete
mandatory lifecycle coverage. A large candidate set could therefore consume
memory and block classification even though this detector is discovery-only and
has no authority to supersede or retire another source's Memory.

## Decision

Keep two different candidate contracts:

- Same-source lifecycle reconciliation must cover every directly affected
  incumbent and may perform destructive actions only after complete coverage.
- Cross-document detection is bounded, non-destructive discovery. It may add an
  Evidence Relation or Review, but it cannot retire or supersede a Memory.

Cross-document discovery queries entity graph, semantic vector, and lexical BM25
channels independently with a bounded rank window. A shared storage-neutral RRF
primitive fuses IDs from those channels. The detector applies exact access and
provenance predicates to lightweight candidate rows, adaptively selects between
32 and 128 candidates, and only then batch-loads full Memory content. Access and
provenance are revalidated after classification and before any Relation write;
a concurrent change fails the run closed instead of persisting a stale edge.

The authoritative Lifecycle transaction commits Memory, Evidence, Support,
vector-outbox work, and a narrow durable Relation Discovery request. It does not
wait for non-destructive cross-document classification. A bounded worker later
leases that content- and revision-pinned request, performs retrieval and batched
classification, then atomically commits its RelationRun, relations, any required
cross-source Review, and work completion. Lease owner/token fencing and current
Memory, Source Unit revision, Evidence, Support, access, subscription, and
candidate-provenance guards reject stale completion. One selected candidate
ledger is indivisible; slice budgets decide whether to start another work item,
not whether to silently complete a truncated ledger.

Source-row dependencies distinguish actual Configured/Managed Capture Sources
from Direct User document provenance. The existing `user_memory` and
`user_correction` namespaces do not require configured Source rows. They remain
selected candidates subject to the same current Memory, persisted provenance,
Support, access, and lease guards; a returned origin marker alone grants nothing.
This distinction applies only to candidate provenance: the work's owning Source
and Source-backed Support dependencies still require their real Source rows.
Missing or unknown Source identities cannot be dropped to make completion pass.
Adapters reuse the shared provenance rule within their native transaction and
locking boundaries; no additional origin field or lifecycle state is persisted.

The current Evidence Relation projection has two ownership planes. The
authoritative Lifecycle write owns source-support relations and may rebuild the
whole projection when source evidence changes. Post-commit discovery owns only
non-authoritative relations and replaces only that part of the projection; an
empty discovery outcome therefore cannot remove authoritative support. If both
planes address the same Evidence/Memory pair, authoritative support remains the
current projection while each RelationRun retains its immutable audit snapshot.
This supersedes the earlier assumption that the latest RelationRun owned every
current relation for an Evidence Unit.

Request creation, candidate retrieval, relation authority, and the final storage
fence resolve the same effective access principal. Private work persists its
owner as the durable principal, while execution and completion rederive that
principal from the current locked challenger Memory; an optional request actor
cannot widen or erase the boundary. Private candidates and Reviews require the
same owner and an exactly matching optional repository scope: all records may
be unscoped, but scoped/unscoped mixtures and different repositories fail
closed. A contradiction is a cross-source conflict
only when the two Evidence lineages belong to different sources, and only that
exact authority case may create the pending Review. A same-source contradiction
remains an independent, non-destructive relation. Sharing an owner or repository
therefore permits discovery but never converts a conflict into automatic
lifecycle authority.

Before constructing the retrieval and classifier runtime, an idle worker uses a
bounded read-only readiness probe with the same retry-attempt ceiling as the
lease policy. The probe is only an initialization guard; the fenced lease
remains the authority, so a concurrent enqueue is picked up on the next poll
without weakening durability or correctness.

Relation discovery may persist `EQUIVALENT`, directional `REFINES`, or
`CONTRADICTS`, but it never changes Memory identity or retires or supersedes a
Memory. An independent cross-source contradiction preserves both lineages and
creates a deterministic pending Review unless an explicit Source Authority
Policy is introduced later. Runtime telemetry is kept outside the deterministic
RelationRun identity, which includes the selected candidate snapshot.

This supersedes the assumption that a truncated cross-document discovery page
is an incomplete mandatory lifecycle ledger.

### Sparse catalog completion

Identity recall and cross-document discovery share request-local catalogs and
coverage validation with same-Unit claim assessment. A request contains each
challenger and selected incumbent once, plus the allowed incumbent IDs for each
challenger. Role references use three uppercase letters and four digits, such as
`NEW-0001` and `MEM-0001`; they are not durable Memory identities. Conflicting
snapshots cannot share a catalog key, and reference overflow is a capacity failure.

The model returns exactly one completion row per challenger and only explicitly
discovered equivalent, directional refinement, or contradiction edges. Empty
edge arrays are valid. Omission means no relationship proposed, never proven
independence. Missing or duplicate completion rows, duplicate edges, unknown or
out-of-set references, and unfinished provider responses fail closed. Existing
structured transport correction, capacity planning and retry remain the execution
boundary; fitting catalogs have no fixed pair-count subdivision.

Identity completion snapshots retain all checked candidates and optional edges
in the existing preclassified work payload. A null relationship records no
proposed edge; it must not become `UNRELATED` or a negative semantic proof.
Discovery may reuse that completed inspection only with unchanged challenger
and candidate content, current Support, access context, and classifier contract.
Stale snapshots are reclassified. Discovery still revalidates its entire selected
candidate universe before fenced completion, including candidates without edges.
The work JSON contract changes without adding a table, migration, lifecycle
state, scheduler, or mutation authority. SQLite and Cloud use the same serializer.

This supersedes the complete per-pair output requirement for these two bounded,
non-destructive discovery responsibilities. Complete destructive incumbent
coverage and conditional exact comparisons between competing same-Unit refiners
remain mandatory under ADR 0034. The common module owns catalog interning and
reference/coverage validation only; business proof, retrieval, Evidence, access,
transaction and lifecycle gates retain their existing owners.

The product explicitly accepts the interval between a supported Memory's commit
and discovery of its cross-document conflicts. Readability is not gated on a
completed conflict scan; queue failure or bounded recall can prolong or leave
gaps in annotations. Completion and failure remain visible, and neither an
empty queue nor a successful run proves global consistency.

## Consequences

Memory corpus size remains behind indexed stores instead of becoming process
heap. The detector makes no exhaustive cross-document recall claim, so candidate
recall must be evaluated with representative cases and live latency, queue, and
RSS measurements. Channel failure is audited but does not authorize destructive
fallback behavior. Adding a future retrieval backend requires only another
ranked-ID channel and the same access/provenance postfilter.

Source synchronization is not held open by discovery latency or a transient
discovery failure. Failed work remains durable with bounded exponential retry;
one worker slice cannot consume all attempts, and an exhausted item remains
auditable as failed. Source-sync and relation slices are fairly interleaved so a
continuous ingestion backlog cannot starve discovery. This is a dedicated
domain work contract, not a replay ledger or generic job framework, and SQLite,
HANA, and future adapters implement the same lease and completion semantics.
Adapters must also preserve the same projection ownership rule: Lifecycle
replacement invalidates stale discovery, whereas discovery replacement cannot
delete or overwrite authoritative support.
An empty relation queue does not initialize vector or LLM runtime components,
which keeps idle startup and test/application shutdown independent of heavy
retrieval initialization.

The ranking choice follows the original RRF method and current production-search
practice; bounded candidate generation follows standard entity-resolution
blocking and filtered nearest-neighbor retrieval patterns.

## References

- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Elastic RRF API](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)
- [A Survey of Blocking and Filtering Techniques for Entity Resolution](https://arxiv.org/abs/1905.06167)
- [Filtered Vector Search: State of the Art and Research Opportunities](https://research.google/pubs/filtered-vector-search-state-of-the-art-and-research-opportunities/)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [Microsoft background job security guidance](https://learn.microsoft.com/en-us/azure/architecture/best-practices/background-jobs)
- [JSON Schema string patterns](https://json-schema.org/understanding-json-schema/reference/string#regular-expressions)
