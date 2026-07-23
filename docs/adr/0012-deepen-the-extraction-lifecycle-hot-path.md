# Deepen the extraction lifecycle hot path

Status: Accepted (2026-07-22)

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
mentions, performs chunked exact and alias lookup, embeds only unresolved unique
mentions in bounded batches, retrieves bounded top-k candidates through the
shared storage contract, and coalesces genuinely ambiguous matches into
case- and prompt-bounded structured adjudication calls. The hard prompt bound
applies to the final rendered prompt, including its template and document
context; a single oversized case fails closed. Every adjudication batch must
return exactly one decision per supplied mention before any Entity or alias
write occurs. It validates every returned ID against the supplied candidate set
and maps resolved IDs back only to the Memory candidates that mentioned them.

Embedding is recall, never merge authority. No retrieved candidate means a new
Entity without an LLM call. A confirmed same-entity decision may learn an alias;
proactive document-wide alias generation is removed. The alias table remains
because exact alias lookup and query-time expansion have real consumers.
Canonical Entity IDs remain workspace-internal graph identities rather than
Evidence or access authority. Resolver-confirmed aliases carry the lifecycle
access-context hash that authorized the decision, and that hash participates in
alias identity and lookup; extraction cannot reuse a private or
repository-incompatible learned alias. Query expansion and global alias FTS
admit only authoritative manual and deterministic aliases, which remain
workspace-wide. Manual aliases outrank deterministic aliases, which outrank
access-scoped learned aliases. If the highest eligible priority maps one alias
to multiple canonical IDs, it is not an exact alias hit; those IDs become
bounded adjudication candidates.

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
candidate-content-hash-, current-Support-hash-, both-side-access-context-, and
classifier-version-pinned seed. The request already pins the challenger content
hash, Source Unit revision, actor/access scope and current Evidence lookup. Relation discovery
revalidates the stale guards before classification and again inside the fenced
completion transaction, including candidate current-Support-set hashes. It
reuses valid overlapping decisions while still retrieving and classifying
additional candidates. This input is part of normal relation work, not a replay
or classification ledger.

Lifecycle stale-guard input is loaded through one batch support-state operation
that returns the active Evidence Reference IDs and canonical support-set hash
for every requested Memory, including explicit empty states. The same result
separately exposes the exact current-Observation subset used to fence reusable
semantic decisions. This preserves explicitly contested historical support for
lifecycle safety without treating it as current relation Evidence. Adapters
chunk large bind sets internally. Callers do not issue separate reference and
hash queries per incumbent.

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
Identity admission reports classified pair count, structured call count, prompt
characters, and elapsed time through that same event.
The Candidate Ledger reports input/selected/exact-drop/semantic-drop counts,
logical structured calls, validation retries, prompt characters, and elapsed
model time through the same Source Unit result and audit path.

One configured request timeout is the wall-clock budget for the complete
logical structured call, not a fresh allowance for each provider retry or
native-schema-to-JSON transition. The boundary computes one monotonic deadline,
passes only the remaining budget to each provider attempt, and owns one shared
bounded transport-retry budget with LiteLLM internal retries disabled. A native
schema incompatibility may transition once to JSON text under that same
deadline; exhausted transport failures, authentication failures, and deadline
expiry do not trigger a second strategy that cannot repair them. Deadline
expiry remains fail-closed.

The same boundary emits one content-free terminal metric containing issued
attempts, transport retries, schema fallback count, final mode, elapsed time,
terminal category, and provider token usage only when every relevant response
reports it. Missing or failed-attempt usage stays unknown rather than being
estimated. Source Unit latency continues through the existing extraction-stage
metric so this shared contract does not introduce a tracing table or
source-specific telemetry path.

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
- [Structured LLM logical deadline research](../research/structured-llm-logical-deadline.md)
