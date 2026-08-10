# Separate lexical candidate eligibility from term rarity

Status: Accepted (2026-08-10)

## Context

Ranked search unions independent vector, content lexical, metadata lexical, and
relationship candidates before weighted rank fusion and page slicing. Source
and time listing remains a deterministic operation rather than a ranked search
channel.

The lexical channels currently conflate two different questions:

1. Does a row match enough of the query to become a candidate?
2. How much ranking evidence does each matched term provide?

An all-term lexical predicate answers the first question too strictly. A query
such as `process map failed command error` can describe the correct Jira issue
while its extracted Memories use `process tree`, `non-retryable`, and
`persisted`. Conversely, treating any one ordinary word such as `process` or
`error` as sufficient admits a very large low-quality pool. Calling a term
"highly discriminative" does not solve this deterministically: structured
anchors can be recognized from syntax, but statistical rarity is a property of
the caller-visible indexed corpus.

Metadata and content also have different contracts. A source title, external
identifier, or path is short identity-bearing evidence shared by every Memory
supported by that source record. Memory content is longer explanatory text.
One global minimum-match rule across both surfaces would either suppress valid
metadata recall or make content recall too broad.

## Decision

### Candidate generation remains channel-local and recall-first

The shared SearchEngine constructs one normalized Query Plan and asks each
retrieval adapter for independent candidates. The plan preserves the complete
query for vector retrieval and represents lexical ordinary terms, quoted
phrases, and structured anchors separately. Candidate sets are unioned before
fusion; response `top_k` never becomes the per-channel candidate window.

Structured anchors are syntax-recognizable identifiers, exact quoted error
phrases, and code symbols, for example `SFPAY-181363`, a UUID,
`HandlePeriodInitializationCommand`, `PROCESS_MAP_VALIDATION_STATE`, or
`"No process tree found"`. One exact anchor match is sufficient to enter the
appropriate lexical candidate set. Statistical rarity never changes anchor
recognition.

Ordinary terms use order-independent term coverage. The initial metadata
policy requires all terms for one- or two-term queries and
`ceil(0.60 * term_count)` for queries of three or more terms. For a five-term
query this is three terms. This threshold is a shared Query Plan decision, not
an adapter constant.

Metadata coverage is term-centric across the short metadata fields of one
caller-visible source-support record. Terms may match different fields on that
same record, but matches from different support records must not be combined to
qualify a Memory. Exact identifier/title phrase evidence outranks ordinary
term coverage, which outranks alias normalization and trigram fallback.

Content eligibility remains a separate policy. The metadata threshold must not
be copied to content without content-specific GoldenEval evidence. A content
adapter may use a native soft-AND operator, but the Query Plan owns the required
coverage and the shared tests own its observable behavior.

### Document frequency affects ranking, not eligibility

For an ordinary term `t`:

- `N` is the number of distinct Memories in the caller-visible query corpus.
- `df(t)` is the number of those distinct Memories whose relevant lexical
  surface contains `t` under the adapter's normalized token semantics.
- the adapter may use a smoothed weight such as
  `ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))`.

The corpus applies the same authorization and hard query constraints as the
candidate read: lifecycle status, workspace/private visibility, configured
Source access, explicit Source and time facets, memory type, and hard project
scope. This prevents term statistics from leaking inaccessible content and
keeps scoring aligned with the candidates the caller can actually receive.

DF/IDF weights the contribution of matched ordinary terms after the coverage
gate. It does not let one statistically rare ordinary word bypass minimum
coverage, and it is not part of structured-anchor recognition.

### Keep the adapter seam deep

The SearchEngine does not call a public `get_df(term)` method and does not
orchestrate database-specific term-statistics queries. It passes the Query
Plan, Access Scope, hard facets, and bounded candidate limit through the keyword
retrieval interface. Each adapter returns ranked candidates with safe evidence
such as channel, matched fields, matched terms, coverage, and term-weight
contributions.

SQLite may use FTS5 token indexes and its native BM25 implementation. HANA may
use fuzzy text indexes, `CONTAINS`, and adapter-local DF/IDF calculations. The
shared contract requires equivalent candidate eligibility, anchor precedence,
visibility, provenance, and GoldenEval rank gates; it does not require equal
raw scores or identical SQL.

No adapter may claim full BM25 from DF alone. Full BM25 additionally requires
term frequency and document-length normalization. An adapter that exposes only
exact token membership and DF implements IDF-weighted term coverage, not BM25.

## Consequences

Metadata/title recall can admit a complete source-supported Memory cluster
without forcing every member into the response page. Fusion still decides final
order, and diagnostics distinguish candidate generation from later truncation.

Content soft matching cannot be treated as the repair for a metadata wording
gap. GoldenEval must independently cover metadata 3-of-5 recall, quoted and
structured anchors, reordered terms, source-support isolation, content
precision, and SQLite/HANA observable parity.

Implementations need bounded per-query term-statistics work. Adapters may issue
one bounded multi-term database request or use a visibility-safe cache whose
invalidation and privacy semantics are explicit. A long-text substring scan is
not an acceptable production fallback for token DF.

## Implementation

The SearchEngine builds a provider-neutral lexical Query Plan with exact
anchors, normalized ordinary metadata terms, and the shared coverage gate.
SQLite evaluates term membership and caller-visible DF in FTS5-backed CTEs,
groups coverage by one source-support record, and returns matched-term evidence
to retrieval diagnostics. Exact anchors are independently eligible and rank
above ordinary coverage.

GoldenEval case `metadata_three_of_five_source_cluster_recall` preserves the
SFPAY-181363 failure shape: six Memories whose content uses different wording
must all enter the top ten through one Jira title that covers three of five
ordinary query terms. The content candidate threshold remains separately owned
and was not changed by this decision.

## References

- [Elasticsearch minimum_should_match](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-minimum-should-match)
- [Elasticsearch combined_fields query](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-combined-fields-query)
- [SQLite FTS5](https://sqlite.org/fts5.html)
- [SAP HANA Cloud fuzzy text search](https://help.sap.com/docs/hana-cloud-database/sap-hana-cloud-sap-hana-database-search-developer-guide/fuzzy-text-search)
- [SAP HANA Cloud soft AND](https://help.sap.com/docs/hana-cloud-database/sap-hana-cloud-sap-hana-database-search-developer-guide/soft-and)
