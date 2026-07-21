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
a concurrent change fails the run closed instead of persisting a stale edge. Runtime
telemetry is kept outside the deterministic RelationRun payload; RelationRun
identity includes the selected candidate snapshot.

This supersedes the assumption that a truncated cross-document discovery page
is an incomplete mandatory lifecycle ledger.

## Consequences

Memory corpus size remains behind indexed stores instead of becoming process
heap. The detector makes no exhaustive cross-document recall claim, so candidate
recall must be evaluated with representative cases and live latency, queue, and
RSS measurements. Channel failure is audited but does not authorize destructive
fallback behavior. Adding a future retrieval backend requires only another
ranked-ID channel and the same access/provenance postfilter.

The ranking choice follows the original RRF method and current production-search
practice; bounded candidate generation follows standard entity-resolution
blocking and filtered nearest-neighbor retrieval patterns.

## References

- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Elastic RRF API](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)
- [A Survey of Blocking and Filtering Techniques for Entity Resolution](https://arxiv.org/abs/1905.06167)
- [Filtered Vector Search: State of the Art and Research Opportunities](https://research.google/pubs/filtered-vector-search-state-of-the-art-and-research-opportunities/)
