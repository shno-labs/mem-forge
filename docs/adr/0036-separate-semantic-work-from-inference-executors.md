# ADR 0036: Separate semantic work from inference executors

## Status

Accepted as target design on 2026-09-21. Implementation is deferred. TypeSafe/Jev
production eligibility remains conditional on operation-specific evaluation;
this ADR does not declare Jev a drop-in replacement for every existing LLM call.

## Context

The shared structured client currently exposes open-vocabulary generation,
closed-set classification, ranking, semantic verification and Evidence selection
through one provider-shaped interface. Domain callers render prompt strings
before the transport seam. This makes repeated revision context difficult to
reuse, obscures which calls are classifiers, and couples application work to one
generative model contract.

Large revision workloads also repeat stable instructions and current Source
context across claim cohorts. Provider prompt caching can reduce that transport
cost only when stable prefix material is deliberately ordered before changing
cohort and retry material. Cache behavior must remain an optimization rather
than execution state.

TypeSafe/Jev supplies fast typed Choice, Noul and Score judgments over shared
text state. It does not generate open-vocabulary claims or explanations, does
not currently accept images, and evaluates questions in one request
independently. Treating it as another generic chat model would leak those
differences into callers or silently weaken existing contracts.

## Decision

1. Domain planners return an immutable backend-neutral `ContextBundle` plus
   either `GenerationWork` or `JudgmentWork`. They do not return provider prompt
   strings. Context is ordered by semantic role and stability: versioned
   contract, revision-static state, cohort work, ReadingGroup, carried state and
   attempt-only diagnostics. Authority, selectability, exact references, access
   identity and complete work manifests remain application-owned.
2. Introduce two narrow interfaces. `GenerationExecutor` handles work that
   creates open-vocabulary text or one dependent multi-field structured proposal,
   including a complete Support Assessment with status, Primary, Required and
   carried witness state. `JudgmentExecutor` handles independent
   application-defined Choice, Boolean or Score work. A Structured LLM adapter
   may implement both; a Jev adapter implements only eligible judgment work.
   Capability admission rejects unsupported modality, option count, dependency
   or output shape before a provider call.
3. The Structured LLM adapter uses a deterministic contract-declared cache
   layout. Revision-first places a repeated ReadingGroup before changing claim
   cohorts; cohort-first places fixed claims before changing ReadingGroups, as in
   streamed Support Assessment. Each work contract declares its layout and
   retries preserve it; no runtime optimizer chooses between layouts. The
   adapter may request provider prompt caching at the largest repeated prefix
   supported by the configured route. It never pads, duplicates or enlarges
   semantic work for a cache hit. Cache hits, misses, TTLs and provider cache
   keys never affect work identity, correctness, recovery or stale guards.
   Telemetry records reported cache creation/read tokens, uncached input and
   latency.
4. Cache-aware dispatch reuses the existing bounded collector and global
   Structured LLM semaphore. Stateful dependency lanes remain sequential and
   naturally warm their later requests; independent lanes remain concurrent.
   Same-prefix independent requests are contiguous, but version one adds no
   warm-up call, cache registry, persistent cache key or non-streaming leader
   barrier. A response-start single-flight gate is a future transport
   optimization requiring measured evidence, not part of this decision.
5. The Jev adapter renders one structured `state` and independent Choice, Noul
   or Score questions. Raw probabilities are diagnostic input to a calibrated,
   versioned application policy. Low confidence or incomplete answers produce an
   unresolved result and may invoke an explicitly configured fallback. They
   never directly authorize lifecycle mutation.
6. Configuration separates the generation executor from the judgment profile.
   User-selectable judgment profiles may use Structured LLM only, Jev with an
   LLM fallback, or Jev without hidden fallback for registered eligible work.
   Executor, model, question/output contract and context digest participate in
   durable work identity; changing configuration does not itself reprocess an
   unchanged Source.
7. Jev begins in sampled shadow evaluation. Eligibility is granted separately
   for candidate admission, single-proposition source support, entity
   adjudication, relation classification, reranking, offline judging and
   agent-session authority. Complete Support Assessment is explicitly ineligible:
   its status, Primary, multiple Required selections and carried witness state
   are one dependent Evidence-plan proposal and remain on the Structured LLM
   path. Claim and managed-patch generation also remain generative work. Making
   complete Support Assessment Jev-eligible requires a later ADR; shadow mode or
   fallback configuration cannot widen this boundary.
8. Provider results remain proposals. Existing exact selector validation,
   complete coverage, automatic destructive validation, Source authority,
   lifecycle reduction and atomic stale-guarded commit remain unchanged.

The complete interface, current-call classification, cache layout and rollout
contract are documented in
[Semantic judgment execution and context reuse](../design/semantic-judgment-execution.md).
The parser, TypeSafe API and prompt-cache research supporting the decision is
recorded in
[Structure-preserving parsers, Jev judgments, and repeated-context caching](../research/2026-09-21-structure-parsers-jev-prompt-cache.md).
The batch concurrency and cache-visibility decision is supported by
[Prompt-cache-aware batch scheduling](../research/2026-09-21-prompt-cache-aware-batch-scheduling.md).

## Consequences

- LLM and Jev adapters can share domain context without making callers understand
  provider request formats.
- Stable revision context can be reused by provider prompt caches or Jev
  multi-question state without becoming duplicated lifecycle state.
- A model that cannot satisfy one work contract fails at capability admission
  rather than triggering source-specific fallback behavior.
- Existing provider wrappers are migrated by semantic responsibility. Obsolete
  L3/L4-era wrappers do not each receive a parallel Jev implementation.
- Jev probabilities enable measured confidence policies, but add model/version
  calibration and telemetry requirements.

## Non-goals

- no one-size-fits-all inference interface;
- no Jev claim generation, image understanding or semantic Evidence search;
- no Jev shadow, fallback or production path for complete Support Assessment;
- no correctness dependency on prompt-cache retention;
- no model-owned Source authority, lifecycle verbs or selector membership;
- no human confirmation stage for ordinary source reconciliation;
- no automatic historical reprocessing when an executor profile changes.
