# Deepen the extraction lifecycle hot path

Status: Accepted (2026-07-22)

Amended: 2026-07-28 to bind entity-adjudication judgments through
datastore-owned fixed response slots instead of model-repeated mention strings.

Amended: 2026-07-29 to bound the complete Memory identity-resolution working
set, including challenger embeddings and semantic-pair objects, rather than
only bounding the final structured-model calls, and to make Candidate Ledger
actions authoritative over non-applicable response fields. A bounded Candidate
Ledger batch whose provider response remains invalid after its validation retry
now conservatively keeps that batch; deterministic invariants over the assembled
datastore-bound ledger still fail closed.

Amended: 2026-07-29 to admit structured-model calls through one process-wide
bounded concurrency contract and to run only already-independent batch plans
concurrently. Candidate Ledger, entity adjudication, and relation
classification preserve deterministic input order and complete validation
before results escape. Memory identity worksets remain sequential and bounded;
their storage recall is batched instead of increasing semantic concurrency.

Amended: 2026-07-30 to make every extraction entrypoint consume one shared,
source-neutral durable-Memory quality contract. Projection batches may not
weaken the code-recoverable, future-usefulness, deduplication, or meta-Memory
rules applied by full-document, change, and deterministic-unit extraction.

Amended: 2026-07-30 to make the language of each candidate follow its owned
source Evidence through that same shared contract. Read-only context may
resolve meaning but cannot translate a candidate or select a different
language.

Amended: 2026-08-03 to replace the transient Candidate Ledger and entity
adjudication nullable fixed-slot responses with ordered decision arrays.
Request-specific exact coverage is validated in application code. Candidate
Ledger retains one validation retry and all-KEEP fallback; entity adjudication
retains one validation retry and fails before Entity or alias writes.

Amended: 2026-08-03 to apply the same ordered-decision contract to both
authoritative lifecycle reconciliation phases. Candidate relation and incumbent
support audit keep their existing 24- and 30-item business batches and complete
lifecycle coverage; application code validates exact response count and binds
each array position to request-owned candidate or incumbent identity. One
validation retry remains, followed by fail-closed reconciliation.

Amended: 2026-08-03 to let a deployment explicitly select Anthropic's current
`output_config.format` native-schema transport when a gateway capability
registry lags the deployed model. The provider SDK simplifies only the wire
schema; the original Pydantic model remains response authority.

Amended: 2026-08-03 to give Memory-pair relation classification one bounded
coverage retry. Duplicate caller-owned `pair_index` entries are reduced
deterministically by keeping the first provider decision. A missing or
unexpected index regenerates the complete batch with explicit expected
indices; a second incomplete or foreign ledger fails closed and leaves the
durable Relation Discovery work retryable.

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

All extraction modes apply the same durable-Memory quality contract before a
candidate enters lifecycle processing. Generated query text, schema columns,
aliases, file paths, and other facts directly recoverable from current source
are not Memories merely because they occur in a large authoritative document.
Reusable decisions, reasons, constraints, invariants, conclusions, and
procedures in that same document remain eligible. This is a content-quality
contract, not a source-type, path, file-size, SQL-ratio, or provider special
case. The optional Candidate Ledger can remove additional explicit low-value
or redundant candidates, but its conservative `KEEP` semantics do not replace
the extraction boundary.

That shared contract also preserves the language of each candidate's owned
source Evidence. Chinese Primary Evidence produces Chinese Memory content;
English Primary Evidence produces English Memory content; exact technical
identifiers and genuinely mixed-language evidence remain unchanged. Context
Evidence may resolve references and chronology but does not own the claim and
cannot select its language. This is a per-candidate Evidence rule, not a
document-, batch-, source-type-, or adapter-level heuristic.

Changing this extraction contract governs new derivations and real source
changes only. An unchanged Source Projection has no extraction batch, so a
contract deployment does not reprocess, translate, or rewrite existing
Memories. Explicit recovery and reprocessing operations retain their existing
authority and lifecycle safeguards.

Same-source destructive reconciliation still covers every Memory in the
Mandatory Incumbent Scope. Exact Evidence anchors and Revision Delta impact may
prove an incumbent disjoint and give it a deterministic `NOOP`; overlapping,
unknown, and unanchored incumbents are classified in bounded structured batches.
One `CoverageProof` validates exactly one decision for every incumbent before a
Lifecycle Plan may commit. Cross-document and cross-source discovery run after
that commit through the bounded, non-destructive Relation Discovery contract in
[ADR 0009](0009-bound-cross-document-relation-discovery.md).

Both lifecycle classification phases return ordered decision arrays. Candidate
relation requires exactly one decision per ordered candidate in a cell and may
refer only to an incumbent position supplied in that request. Incumbent support
audit requires exactly one decision per ordered incumbent. Application code
rejects a short or long response, binds every accepted position to datastore-owned
identity, retries that bounded phase once with validation feedback, and then
fails the complete reconciliation closed. The provider schema therefore remains
constant while the request-specific exact-count invariant stays in application
code; batch size is not encoded as nullable schema fields.

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
context; a single oversized case fails closed.

Each adjudication batch returns an ordered decision array with exactly one
judgment per ordered mention. The model returns only `matched_id`, confidence,
and reason; it never repeats or invents mention identity. Code validates the
exact response count and binds each array position back to its request-owned
mention before any Entity or alias write occurs. A count mismatch receives one
bounded validation retry; a second mismatch fails the complete resolver call
before Entity or alias writes. Every returned ID is validated against the
candidate set supplied for that mention, and resolved IDs map back only to the
Memory candidates that mentioned them.

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

Memory identity resolution applies exact active-identity lookup before semantic
recall, then processes unresolved challengers through one bounded workset at a
time. Challenger embeddings are submitted together for that workset, while
each challenger still receives the fixed top-k, access-compatible candidate
recall required by [ADR 0006](0006-bound-memory-identity-recall-before-semantic-proof.md).
Only that workset's embeddings, recalled Memories, and semantic-pair objects
remain live during classification. The resolver retains ordered compact
decisions across worksets: candidate identity, content and access stale-guard
inputs, relation, direction, and reason. A selected `EQUIVALENT` target remains
available for corroboration and Lifecycle Plan stale guards; non-target Memory
content, extraction context, and semantic-pair objects do not survive the
workset. The resolver releases those transient recall objects before the
complete Source Unit enters its one atomic Lifecycle Plan.

This batching is an execution partition, not a reduction in lifecycle or
identity scope. It must not introduce a global candidate cap, discard a large
but valid Source Unit, change exact/equivalence authority, or commit partial
worksets independently. If measured peak RSS remains unsafe after this bounded
working-set design, deployment memory is increased; the algorithm is not
fragmented into progressively smaller semantic units merely to fit an
undersized worker.

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

Each relation-classification batch returns one decision array keyed only by its
caller-owned `pair_index` values. Application code keeps the first decision for
each expected index and ignores later duplicates for that same pair. It never
fills a missing decision or admits an unexpected index. Missing or unexpected
coverage receives one bounded regeneration of the complete batch with the
exact expected indices; a second incomplete or foreign response fails closed
before relation outcomes are committed.

Lifecycle stale-guard input is loaded through one batch support-state operation
that returns the active Evidence Reference IDs and canonical support-set hash
for every requested Memory, including explicit empty states. The same result
separately exposes the exact current-Observation subset used to fence reusable
semantic decisions. This preserves explicitly contested historical support for
lifecycle safety without treating it as current relation Evidence. Adapters
chunk large bind sets internally. Callers do not issue separate reference and
hash queries per incumbent.

The transient complete Candidate Ledger remains until measured cohorts show it
adds no quality value. It has no lifecycle or provenance authority. Its action
is the response discriminator: `canonical_index` is consumed and validated only
for `DROP_REDUNDANT`; a value returned in that inactive field for `KEEP` or
`DROP_LOW_VALUE` is discarded at the structured-response boundary. Missing,
forward, invisible, or otherwise invalid canonical identity for an actual
`DROP_REDUNDANT` rejects that provider response and receives the existing one
bounded validation retry. If the batch still cannot satisfy the response
contract, the optional admission gate conservatively emits `KEEP` for every
candidate in that batch and continues, with fixed fallback batch and candidate
counts. Once responses have been bound and accepted, complete coverage,
datastore-owned index identity, and canonical-chain invariants over the
assembled ledger remain deterministic code contracts and fail closed. This
preserves the model's explicit valid admission actions without allowing one
stochastic invalid batch to abort and replay a complete large Source Unit.
The response is an ordered decision array: application code requires exactly
one decision per active candidate and binds it to the datastore-owned candidate
index by array position. No provider-specific batch size or dynamic schema is
used to express request-specific length.

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
count, embedding batches, adjudication calls, validation retries, new
identities, and elapsed time through the existing memory/RSS stage event.
Provider token counts remain optional until the configured client exposes them;
prompt text is never persisted as telemetry.
Identity admission reports classified pair count, structured call count, prompt
characters, and elapsed time through that same event.
The Candidate Ledger reports input/selected/exact-drop/semantic-drop counts,
logical structured calls, validation retries, prompt characters, and elapsed
model time through the same Source Unit result and audit path.

### Bound provider concurrency without serializing independent batches

Every structured-model client in one process participates in the same bounded
admission limit. One permit covers the complete logical call, including
provider retries and schema fallback, so a retry cannot temporarily exceed the
configured provider concurrency. Queue time does not consume the logical
provider deadline. Source processing and background Relation Discovery use the
same admission boundary rather than independently multiplying concurrency.

After request payloads and datastore-owned response identities have been
planned, Candidate Ledger batches, entity-adjudication batches, and relation
classification batches may execute concurrently up to that shared limit.
Their results are restored to deterministic plan order and the existing
coverage, positional-binding, canonical-identity, access, and stale-guard validations still
close before any result becomes lifecycle input. An exception cancels sibling
work and no partial aggregate escapes. This is execution concurrency only: it
does not widen a batch, reduce candidate or Evidence scope, change fallback
semantics, or weaken the one atomic Lifecycle Plan.

Memory identity worksets remain sequential because each workset owns bounded
embeddings, recalled Memories, and semantic-pair objects whose release is part
of the memory-safety design. Within one workset, exact and reactivation lookup,
embedding transport, vector recall, and vector-hit Memory loading use adapter
batch operations so their round trips scale with bounded adapter batches rather
than challenger count. The bounded entity fallback retains its per-challenger
ranking and exclusions; it is not replaced by an unmeasured, cross-query
overfetch. The optimization does not retain non-target pair objects or make
multiple identity worksets live at once.

### Bound transient work before increasing document admission

`DocumentLifecycleAdmission` remains the count-based process-wide guard around
one complete document lifecycle. It does not guess a weight before collection
has established the Source Unit, extraction batches, and Artifact sizes.
Increasing its deployed limit is a measured capacity rollout, gated by
single-lifecycle RSS/HWM headroom rather than source type or worker count.
Resuming a durable Source Unit derivation is the same lifecycle at a later
execution boundary, not lightweight run setup. Recovery therefore acquires the
same process-wide document admission before resuming extraction, Candidate
Ledger, identity, reconciliation, and the atomic Lifecycle Plan. It reports the
bounded derivation workset as `recovering_derivations` progress while it waits
and runs; `reconciling` remains reserved for authoritative removed-item
detection.
This prevents a recovered large document from overlapping another source's
admitted PDF, image, extraction, or lifecycle work, without adding a second
scheduler or reducing semantic scope.

Within an admitted document, extraction uses a bounded worker loop instead of
creating one task per unit or Projection batch. Document outline and glossary
context are derived once and shared immutably across unit prompts.
`ExtractionWorkPool` remains the process-wide source-fair heavy-work boundary
and additionally admits at most one multimodal batch initially. A multimodal
batch acquires that permit before general worker capacity, so image work waiting
for its conservative memory budget cannot occupy the text worker pool.
Model-supported image inputs are identified from the provider-neutral planned
batch, not a source type. Image bodies are loaded only after both permits are
held and remain batch-local. Other stored binary media, such as PDFs, do not
consume multimodal admission or report model-input bytes unless the structured
LLM contract actually accepts and sends them.

This deliberately introduces no byte-weighted scheduler, live-RSS controller,
provider-specific branch, or second executor. The existing Artifact persistence
and inference budgets in
[ADR 0014](0014-model-binary-artifacts-as-revision-pinned-source-evidence.md)
continue to govern immutable evidence storage and inference eligibility. The
per-call raw-image batch budget additionally leaves explicit headroom for
base64 and JSON request expansion. Queue wait, raw binary input,
multimodal-call count, and maximum concurrent multimodal work are added to the
existing content-free extraction metrics; no tracing table is introduced.

The structured-LLM boundary validates every image before provider invocation.
It preserves a valid image already inside the portable transport envelope.
Otherwise it derives one bounded JPEG transport representation: EXIF
orientation is applied, animation is reduced to its first frame, transparency
is flattened against white, the longest dimension is at most 2000 pixels, and
the encoded body fits the partner-safe image byte limit. The current envelope
follows the portable recommendations and partner-platform limits documented by
[Anthropic vision](https://platform.claude.com/docs/en/build-with-claude/vision)
and
[Amazon Bedrock Anthropic messages](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages-request-response.html).
The derivative is transient: the original Object Store bytes, Evidence hash,
media metadata, Source Observation identity, and Evidence Reference remain
unchanged. The response continues to attribute the image to that original
Source Observation.

Image preparation happens once per logical call outside the retry/fallback
loop, and every attempt reuses the same prepared bytes. Invalid or still
oversized image evidence fails closed before a provider request; it is never
silently omitted and cannot produce a text-only success. Preparation is
provider- and source-type-neutral and adds neither a caption model call nor a
second persisted artifact.

One configured request timeout is the wall-clock budget for the complete
logical structured call, not a fresh allowance for each provider retry or
native-schema-to-JSON transition. The boundary computes one monotonic deadline,
passes only the remaining budget to each provider attempt, and owns one shared
bounded transport-retry budget with LiteLLM internal retries disabled. A native
schema incompatibility may transition once to JSON text under that same
deadline; exhausted transport failures, authentication failures, and deadline
expiry do not trigger a second strategy that cannot repair them. Deadline
expiry remains fail-closed.

Native strict-schema admission follows the provider/model capability registry
by default. A deployment integration may explicitly select Anthropic's current
`output_config.format` transport when a bounded live provider probe proves that
the gateway supports it even though its generic registry entry still reports
false. The shared client knows only the selected transport, not the gateway or
source type. For that transport, Anthropic's public schema transformer removes
unsupported wire constraints and adds `additionalProperties: false`; MemForge
still validates every response against the original Pydantic model and retains
its exact-count, identity, and business invariants.

Without an explicit transport, a model that does not advertise native response
schema support uses the existing JSON-text path from its first attempt. An
invalid native result may still make the one existing bounded transition to
JSON text; a provider error does not. Provider transport constraints do not
become domain fields, source-specific branches, or additional lifecycle states.

The same boundary emits one content-free terminal metric per logical call
containing issued attempts, transport retries, schema fallback count, final
mode, elapsed time, terminal category, and provider token usage only when every
relevant response reports it. A context-local collector aggregates those
terminal outcomes across all structured operations that execute inside one
bounded Source Unit lifecycle. Child async tasks inherit the collector, while
concurrent Source Units remain isolated; no process-global callback is used.

After a real Source Unit identity has been bound, each lifecycle execution
records exactly one `source_unit_llm_summary` through the existing audit and log
path, including executions with zero logical calls and executions that fail.
The summary reports logical calls, issued provider attempts, retries, schema
fallbacks, known/unknown usage counts, reported input/output/total token sums,
terminal and operation counts, summed logical-call latency, and independent
Source Unit wall latency. Missing or failed-attempt usage stays unknown rather
than being estimated as zero. Failures before a Source Unit exists have no
Source Unit summary. This shared contract introduces neither a tracing table nor
a source-specific telemetry path.

External provider failures cross the structured-LLM seam as a content-free
failure value containing only a stable category and error code. Raw provider
exception text is neither chained nor copied into the returned error because it
may contain prompts, encoded image requests, credentials, or other unbounded
transport state. Provider retry backoff begins only after the caught exception
and its traceback have been released. The source pipeline likewise projects a
document exception into a bounded failure value before retry delay or durable
state; it never retains an Exception or traceback across that delay or through
the remainder of a source run. This is both a confidentiality contract and a
transient-memory contract.

When an adapter such as LiteLLM flattens a transport cause into a generic
connection exception, the shared boundary may refine that outer code through a
small provider-neutral allowlist such as remote disconnect, connect/read
timeout, TLS, DNS, or payload-too-large. It examines only exception types and a
bounded transient message prefix, then discards them; telemetry and audit state
receive only the stable code and its aggregate count. Unknown failures retain
the outer exception code. This is diagnostic classification, not a new retry
policy or provider compatibility branch.

Retry ownership is stage-specific and single-layer. The structured-LLM boundary
owns bounded transient retry for extraction calls under its one logical
deadline. When extraction returns a terminal failure, the document loop does
not replay fetch, Projection planning, successful extraction batches, or the
failed logical call under another retry budget. Document-level retry remains
available for later storage and lifecycle-application failures that are fenced
and safe to repeat. This prevents one failed batch from multiplying every
successful batch while preserving atomic Lifecycle Plan application: transient
batch results are committed only when the complete extraction outcome succeeds.

Once the owning retry attempts are exhausted, a `partial` source result is
terminal for the durable run: successful document commits are preserved and the
complete source run is not automatically replayed. Run-level retry remains for
failures that prevent a final source result, including lease recovery after a
process crash. Any future targeted failed-document recovery must use the
existing bounded reprocess input rather than silently repeating successful
extraction, provider, or lifecycle work.

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
Document lifecycle concurrency may increase only after the bounded transient
work above is deployed and representative text, attachment, and mixed cohorts
prove lifecycle parity and sufficient single-lifecycle memory headroom.
Necessary optimized multimodal working-set cost may remain higher than
text-only extraction; that does not justify globally serializing text work.
When the optimized attachment cohort still lacks headroom, keep complete
document admission and multimodal admission conservative and evaluate the
existing deployment's process-memory split before introducing a more granular
scheduler.

## References

- [ADR 0006: Bound Memory identity recall before semantic proof](0006-bound-memory-identity-recall-before-semantic-proof.md)
- [ADR 0008: Prune only proven-disjoint incumbents before reconciliation](0008-prune-only-proven-disjoint-incumbents.md)
- [ADR 0009: Bound cross-document relation discovery](0009-bound-cross-document-relation-discovery.md)
- [ADR 0014: Model binary Artifacts as revision-pinned Source Evidence](0014-model-binary-artifacts-as-revision-pinned-source-evidence.md)
- [Structured LLM logical deadline research](../research/structured-llm-logical-deadline.md)
- [Python traceback object and frame lifetime](https://docs.python.org/3/library/traceback.html)
- [Python exception chaining semantics](https://docs.python.org/3/reference/simple_stmts.html#the-raise-statement)
- `memforge-cloud` Issue #220
- `memforge-cloud` Issue #266
