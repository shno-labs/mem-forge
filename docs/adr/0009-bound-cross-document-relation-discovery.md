# Bound cross-document relation discovery before semantic classification

Status: Accepted

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
