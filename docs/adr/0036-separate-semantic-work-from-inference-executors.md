# ADR 0036: Separate semantic work from inference executors

## Status

Accepted as target design on 2026-09-21; amended on 2026-09-22 to make classification model-neutral, remove confidence-based fallback, admit complete same-Unit pair classification and add Change Impact Classification. Implementation is deferred.

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

1. Domain planners return an immutable backend-neutral `ContextBundle` plus either `GenerationWork` or `JudgmentWork`. Authority, selectability, exact references, access identity and complete manifests remain application-owned.
2. `GenerationExecutor` handles open-vocabulary output and dependent multi-field proposals. Claim Extraction and complete Support Assessment use it. `JudgmentExecutor` handles complete-input, closed-label, independent classification or ranking. Its configured classifier model may be TypeSafe/Jev or a small-parameter LLM that satisfies the same application contract.
3. Classifier eligibility is granted for an entire task contract from a fixed evaluation suite. Runtime probabilities are diagnostic only. There is no per-item confidence fallback, hidden LLM substitution or provider cascade. Missing/incomplete output is a typed work failure and retries with the same configured backend and work identity.
4. Change Impact Classification is eligible judgment work. It receives one fixed claim and one capacity-safe `ChangeBundle`, and returns `AFFECTED` or `UNAFFECTED`. Multiple groups should share one bundle when they fit; multiple bundles are OR-reduced by code. `MODIFIED`, `REMOVED` and `AMBIGUOUS` Evidence bypass this classifier and enter Support Assessment; `UNKNOWN` is deterministically `insufficient` and KEEP.
5. Same-Unit Claim Reconciliation consumes deterministic exact matches, then classifies the complete remaining Candidate × Active-incumbent pair manifest. Catalog bodies are shared state; every pair returns one of `EQUIVALENT`, `REFINES`, `CONTRADICTS`, `UNRELATED`, `INSUFFICIENT`. Token-aware partitioning and bounded concurrency are computation details and cannot alter coverage, atomicity or business state. Cross-document relation discovery remains bounded retrieval followed by classification over `K` pairs.
6. Complete Support Assessment remains compound `GenerationWork`. `EvidenceFragment`, `ReadingGroup`, `AssessmentContext` and `AssessmentScope` are distinct. Its discriminated wire result requires selectors only for `SUPPORTED`; `UNSUPPORTED` and `INSUFFICIENT` forbid them. The planner sends old exact excerpt only for `MODIFIED`, `REMOVED` and `AMBIGUOUS`; `EXACT_UNCHANGED` and `CONTAINER_CHANGED` use current material, while `UNKNOWN` does not invoke the model.
7. `REBIND_SUPPORT` preserves Memory identity and claim, materializes or reuses target-Revision Evidence, and atomically attaches the new Support assertion while marking the replaced assertion inactive. Prior Support rows, Evidence and lifecycle history remain immutable and auditable.
8. Structured LLM prompt caching supports two deterministic layouts. `REVISION_FIRST` evidence-fixed work places the current catalog before changing Memory cohorts; `COHORT_FIRST` cohort-fixed streaming places fixed unresolved claims before changing AssessmentContexts. The selected work plan declares one layout and retries preserve it. Cache identity and retention never affect correctness.
9. Classifier adapters render shared state plus independent closed-label questions. Jev gains efficiency from shared in-request state and parallel questions; no cross-request Jev prompt cache is assumed. A small-model LLM adapter must return the identical application schema.
10. Provider results remain proposals. Exact selector validation, complete coverage, Source authority, destructive validation, lifecycle reduction and atomic stale-guarded commit remain application-owned.

The complete interface, task inventory, cache layouts and rollout contract are in
[Semantic judgment execution and context reuse](../design/semantic-judgment-execution.md).
The parser, classifier and prompt-cache evidence is recorded in
[Structure-preserving parsers, Jev judgments, and repeated-context caching](../research/2026-09-21-structure-parsers-jev-prompt-cache.md)
and
[Prompt-cache-aware batch scheduling](../research/2026-09-21-prompt-cache-aware-batch-scheduling.md).

## Consequences

- The domain names a classifier role rather than a Jev stage; Jev and a small-model LLM are replaceable adapters at one seam.
- Same-Unit relation work trades sparse LLM discovery for explicit complete pair coverage with cheap parallel classifiers.
- Change Impact avoids sending every exact-rebound claim to compound Support Assessment while preserving a complete claim manifest over every changed bundle.
- Complete Support Assessment remains one implementation and one validator; classifier outputs do not recreate a second Support engine.
- Stable revision context can be reused by provider prompt caches or classifier shared state without becoming lifecycle state.
- Model/backend changes participate in work identity and require task-specific evaluation.

## Non-goals

- no one-size-fits-all inference interface;
- no per-item confidence fallback or hidden model substitution;
- no classifier claim generation, image understanding or complete Support Assessment;
- no semantic retrieval pruning of mandatory same-Unit relation pairs;
- no correctness dependency on prompt-cache retention;
- no model-owned Source authority, lifecycle verbs or selector membership;
- no human confirmation stage for ordinary source reconciliation;
- no automatic historical reprocessing when an executor profile changes.
