# Deepen the extraction lifecycle hot path

Status: Accepted

## Context

The source-processing path performs a document-wide enrichment call before
claim extraction, then coordinates entity resolution, historical Memory
context, and lifecycle validation through several caller-owned loops. The
enrichment result also maintains document vectors and generated summaries,
tags, entity kinds, relationships, and complexity even though no independent
document-search product consumes that index. These extra stages add model
calls, serial storage reads, schema surface, and rollback work without adding
Memory lifecycle authority.

Cross-document and cross-source discovery are still required, but they are
non-destructive retrieval concerns. Loading unbounded workspace Memory history
into extraction would couple ingestion cost to corpus size and would confuse
discovery recall with the complete same-source coverage required for destructive
lifecycle decisions.

## Decision

### Keep extraction claim-sized and lifecycle authority explicit

One structured semantic extraction pass runs per token-bounded Source Unit
batch. It emits the existing transient Memory candidate shape, including exact
revision-pinned Evidence localization and the entity mentions attributable to
that candidate. Extraction does not receive unbounded workspace history.

Same-source destructive reconciliation still covers every Memory in the
Mandatory Incumbent Scope. Exact Evidence anchors and Revision Delta impact may
prove an incumbent disjoint and give it a deterministic `NOOP`; overlapping,
unknown, and unanchored incumbents are classified in bounded structured batches.
One `CoverageProof` validates exactly one decision for every incumbent before a
Lifecycle Plan may commit. Cross-document and cross-source discovery run after
that commit through the bounded, non-destructive Relation Discovery contract in
[ADR 0009](0009-bound-cross-document-relation-discovery.md).

### Remove unused enrichment and document indexing

The default source path has no separate document-wide enrichment call.
Generated document summaries, tags, inferred relationships, entity kinds, and
LLM-judged complexity are not part of extraction or lifecycle state. The
document `doc_type` input, when still useful as prompt context, comes from
deterministic source/projection metadata rather than another model call.

`DocumentVectorIndex` and the `documents` vector collection are removed because
they have no product query, authorization, or lifecycle consumer. Memory vector
storage, hybrid Memory retrieval, RRF fusion, and Relation candidate retrieval
remain unchanged. A future document-search feature requires a new explicit
query, visibility, lifecycle, and acceptance contract rather than reviving this
dormant index.

### Resolve entities as one bounded batch

`EntityResolver` owns a batch interface. It canonicalizes and deduplicates
mentions, performs bulk exact and alias lookup, embeds only unresolved unique
mentions in one batch, retrieves bounded top-k candidates through the shared
storage contract, and coalesces genuinely ambiguous matches into bounded
structured adjudication calls. It validates every returned ID against the
supplied candidate set and maps resolved IDs back only to the Memory candidates
that mentioned them.

Embedding is recall, never merge authority. No retrieved candidate means a new
Entity without an LLM call. A confirmed same-entity decision may learn an alias;
proactive document-wide alias generation is removed. The alias table remains
because exact alias lookup and query-time expansion have real consumers.

Generated tags are removed end to end from document, Memory, and Entity models,
prompts, APIs, UI, indexes, and adapter contracts. Entity kind is removed with
them because it has no resolver, retrieval, relation, or lifecycle consumer.
Source-native labels remain source metadata and are not reclassified as
MemForge tags.

### Batch storage context and reuse semantic decisions

Callers request entity, Memory, Support, and Evidence context through bounded
batch storage operations. Adapters apply the same current-state, source,
visibility, owner, repository, and access predicates and may internally chunk
bind sets. Database round trips scale with adapter batches, not with the number
of returned entities, Memories, or supports.

When Memory identity admission classifies a pair but does not select an
`EQUIVALENT` target, its complete `REFINES`, `CONTRADICTS`, or `UNRELATED`
decision is carried into the existing durable Relation Discovery request as a
candidate-content-hash- and classifier-version-pinned seed. The request already
pins the challenger content hash, Source Unit revision, actor/access scope and
current Evidence lookup. Relation discovery
revalidates the stale guards and reuses valid overlapping decisions while still
retrieving and classifying additional candidates. This input is part of normal
relation work, not a replay or classification ledger.

Lifecycle stale-guard input is loaded through one batch support-state operation
that returns the active Evidence Reference IDs and canonical support-set hash
for every requested Memory, including explicit empty states. Callers do not
issue separate reference and hash queries per incumbent.

The transient complete Candidate Ledger remains until measured cohorts show it
adds no quality value. It has no lifecycle or provenance authority.

### Keep observability aggregate and content-free

The shared structured-LLM boundary and existing stage timing/RSS hooks report
stage call count, elapsed time, provider token usage when present, retry or
structured-output fallback count, and the bounded stage-specific candidate or
incumbent counts. Missing token usage is unknown, not estimated. Logs and audit
payloads never contain prompts, source content, excerpts, owner identifiers,
credentials, or bindings. No tracing table or source-specific telemetry path is
introduced.

The first implementation records extraction prompt character count, structured
call count and model elapsed time, then aggregates those content-free values
across bounded Source Unit batches. Entity resolution additionally reports
unique mentions, exact/alias hits, embedded and ambiguous mentions, candidate
count, embedding batches, adjudication calls, new identities, and elapsed time
through the existing memory/RSS stage event. Provider token counts remain
optional until the configured client exposes them; prompt text is never
persisted as telemetry.

## Storage consequences

SQLite and HANA keep one shared behavioral contract for surviving fields and
batch methods. Existing SQLite workspaces are disposable and need no data
compatibility bridge; schema migration may rebuild the local tables or the
workspace may be recreated.

HANA cleanup is deliberately separate from runtime behavior. The runtime change
first removes every obsolete reader, writer, admin-search filter, payload, and
API surface.
A focused Cloud maintenance change then inventories every affected workspace,
records exact dry-run counts and parameterized SQL/DDL shapes, drops only the
obsolete tag and document-index storage, restarts the affected processes, and
verifies HANA, API, Memory search, lifecycle, and UI behavior. It preserves
Memory content, Evidence, Support, Relations, Reviews, Findings, Plans, source
lineage, and terminal history.

## Consequences

Ingestion model cost no longer grows from an unconditional enrichment call or
from unbounded historical context. Entity resolution and incumbent validation
become deep modules with one complete caller-facing contract instead of
caller-coordinated N-call loops. Cross-source recall remains bounded and
provider-neutral, while destructive lifecycle safety remains complete and
fail-closed.

Acceptance covers call and query counts, attribution, invalid/stale classifier
output, complete Coverage Proof, relation-decision reuse, SQLite/HANA adapter
parity, source-type canaries, end-to-end latency, queue impact, and worker RSS.
Increasing document lifecycle concurrency is a separate, measured follow-up and
is not part of this decision.

## References

- [ADR 0006: Bound Memory identity recall before semantic proof](0006-bound-memory-identity-recall-before-semantic-proof.md)
- [ADR 0008: Prune only proven-disjoint incumbents before reconciliation](0008-prune-only-proven-disjoint-incumbents.md)
- [ADR 0009: Bound cross-document relation discovery](0009-bound-cross-document-relation-discovery.md)
