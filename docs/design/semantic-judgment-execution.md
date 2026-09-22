# Semantic judgment execution and context reuse

Date: 2026-09-21; classifier-boundary amendment: 2026-09-22. This document is a target design. It does not claim that
TypeSafe/Jev, provider prompt caching, or the described executor interfaces are
implemented or deployed.

The complete Source lifecycle remains defined by
[Source sync to Memory](source-sync-to-memory.md). Exact Fragment and
ReadingGroup compilation remain governed by
[ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md), and
incremental Support and claim reconciliation remain governed by
[ADR 0034](../adr/0034-unify-incremental-support-and-claim-assessment.md).

## 1. Decision summary

MemForge will separate application-owned semantic work from provider-specific
inference transport:

```text
domain planner
  -> ContextBundle + GenerationWork or JudgmentWork
  -> capability-checked executor
     -> Structured LLM adapter
     -> classifier adapter: TypeSafe/Jev or a small-model LLM
  -> application-owned validation and reducer
  -> existing Lifecycle Plan / retrieval / evaluation consumer
```

There are two interfaces rather than one universal model interface:

```python
class GenerationExecutor(Protocol):
    async def generate(self, work: GenerationWork) -> GenerationResult: ...

class JudgmentExecutor(Protocol):
    async def judge(self, work: JudgmentWork) -> JudgmentResult: ...
```

`GenerationWork` may create open-vocabulary text such as a new claim or one
dependent multi-field structured proposal such as a complete Support Assessment.
`JudgmentWork` independently chooses, scores or verifies values already defined
by application code. A Structured LLM may implement both interfaces. A classifier
adapter, backed by TypeSafe/Jev or a small-parameter LLM, implements only the
second. Backend admission is granted for an entire task contract from a fixed
evaluation set; runtime confidence does not switch individual items between
backends.

The model never owns Source authority, exact offsets, allowed selectors,
complete work coverage, lifecycle verbs, stale guards or atomic commit. Those
remain application facts and validators regardless of executor.

## 2. Context is a domain plan, not a prompt string

Each domain planner produces one immutable, backend-neutral `ContextBundle`:

```python
ContextBundle(
    contract=ContextSegment(...),
    revision_static=ContextSegment(...),
    cohort=ContextSegment(...),
    assessment_context=ContextSegment(...),
    carried_state=ContextSegment(...),
    attempt=ContextSegment(...),
    manifest=WorkManifest(...),
)
```

Every segment has:

- a semantic role, exact content and content digest;
- revision, access and work identity where applicable;
- selectable versus read-only material;
- one stability class: `CONTRACT`, `REVISION_STATIC`, `COHORT`,
  `ASSESSMENT_CONTEXT`, `CARRIED_STATE`, or `ATTEMPT`;
- a deterministic order within its stability class.

The bundle contains structured application state, not provider messages,
TypeSafe questions or a serialized prompt. Executor adapters render it:

- the Structured LLM adapter creates system/user content, response schema,
  images and provider cache breakpoints;
- a classifier adapter creates shared state plus independent closed-label
  questions; a Jev adapter uses Choice/Noul/Score while a small-model LLM adapter
  returns the same application-owned schema;
- tests can inspect the same canonical bundle without parsing either wire
  format.

The domain planner, not either executor, decides which AssessmentScope, AssessmentContexts, ReadingGroups, fixed claims,
candidates, Evidence catalogs, historical excerpts and cumulative witnesses are
logically required. Switching executor cannot silently widen or
narrow the context.

## 3. Cache-aware Structured LLM layout

The application cannot manage a provider's raw KV cache. It can make prompt
prefixes reusable and request prompt caching through a supported transport.
For repeated calls over one revision, the Structured LLM adapter renders the
same named segments using one of two contract-declared layouts:

```text
REVISION_FIRST                         COHORT_FIRST

1. CONTRACT                            1. CONTRACT
   instructions/schema/tools              instructions/schema/tools

2. REVISION_STATIC                     2. COHORT
   revision identity/catalog              fixed claims/candidates

3. READING_GROUP                       3. REVISION_STATIC
   current structure/context              revision identity/catalog

4. COHORT                              4. READING_GROUP
   claims/pairs/allowed refs              current structure/context

5. CARRIED_STATE                       5. CARRIED_STATE
6. ATTEMPT                             6. ATTEMPT
```

`REVISION_FIRST` is used when one Evidence Catalog or AssessmentContext is
evaluated against several claim cohorts. `COHORT_FIRST` is used when one fixed
unresolved cohort scans several AssessmentContexts. A Support work plan declares
`REVISION_FIRST` for evidence-fixed batching and `COHORT_FIRST` for cohort-fixed
streaming; it never changes layout mid-work or on retry. This is a deterministic
consequence of the logical partition, not a cache-hit optimizer. Serialization
order changes, but named content, digest, coverage and instructions do not.

A provider cache breakpoint, if supported, is placed after the largest actually
repeated prefix. Calls sharing that prefix should be adjacent while still
respecting complete coverage, latency and concurrency limits. The planner must
not pad input to meet a cache threshold, duplicate content, enlarge a semantic
batch or reorder dependent work solely to chase a cache hit.

For Anthropic-compatible routes, exact-prefix order is `tools`, then `system`,
then `messages`. Stable tool/response definitions therefore come before the
stable system contract and the selected repeated message prefix; variable
ReadingGroup or cohort work, carried state and repair diagnostics follow the
final reusable breakpoint.
Changing a tool or schema before that breakpoint invalidates the cumulative
prefix. Other providers may expose different caching contracts, so the adapter
must advertise and test the actual route capability instead of assuming this
layout is portable.

Prompt caching is a cost and latency optimization only:

- a cache miss is behaviorally equivalent to a hit;
- cache identity never replaces a work hash, stale guard or execution receipt;
- provider TTL or eviction cannot cause a retry to observe different domain
  input;
- request telemetry records cache creation/read input tokens when the provider
  reports them;
- telemetry compares cacheable-prefix tokens, cache reads/writes and uncached
  input so the optimization is accepted only when the configured route shows a
  material saving;
- cached and uncached results use the same schema and application validators.

Anthropic documents prefix caching, automatic or explicit `cache_control`
breakpoints, and 5-minute or 1-hour TTLs. The implementation must confirm that
the configured SAP/Bedrock/gateway route actually forwards and reports those
features before enabling them. LiteLLM transport support alone is not evidence
that a particular deployment route produced a cache hit. See
[Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
and [LiteLLM prompt caching](https://docs.litellm.ai/docs/completion/prompt_caching).

Dynamic request-specific selector enums remain suitable for a small correction
request. Expanding hundreds of per-work enums in the main response schema can
duplicate the catalog and destabilize the reusable prefix, so the ordinary
request keeps one compact structural schema plus exact application validation.

### Minimal cache-aware batch dispatch

Prompt caching does not introduce another batch planner or queue. The existing
logical planner still creates capacity-safe requests and dependency lanes; the
existing bounded collector and Structured LLM semaphore remain the only
concurrency controls.

- A stateful lane, such as one Support cohort scanning several ReadingGroups,
  remains sequential inside the lane. Its first real request can create the
  cache entry and later requests naturally reuse the fixed cohort prefix.
- Independent lanes run concurrently up to the existing configured limit.
- Independent requests with the same rendered prefix are emitted contiguously.
  The first active worker wave may be cold; requests dequeued after a response
  has begun may hit the provider cache. No extra warm-up inference is sent.
- The adapter may derive a content-free prefix digest from the actual serialized
  prefix for telemetry and test assertions. It is not caller input, a provider
  cache key, persisted state or a scheduling correctness dependency.

Anthropic documents that a cache entry becomes available only after the first
response begins. The current MemForge LiteLLM path is non-streaming, so it cannot
observe that event without waiting for the complete response. Version one does
not add a leader barrier that would hold independent work behind a long complete
call. A future transport may release same-prefix followers on a provider
`message_start` event, but only after measured latency/cost evidence justifies the
extra single-flight mechanism. Leader failure must never strand followers.

## 4. Classifier-model execution

A classifier task has complete bounded input, application-defined labels and independent per-item answers. The runtime name is **classifier model (Jev or small-parameter LLM)**; Jev is one adapter, not a domain stage. A task is admitted to this interface only as a whole after a fixed evaluation set meets its label-quality and coverage criteria. Raw probabilities remain diagnostic telemetry and offline calibration data; they do not create per-item confidence fallback branches.

The two Source-lifecycle classifier contracts are:

```text
ChangeImpactClassifier
  fixed claim + capacity-safe ChangeBundle
  -> AFFECTED | UNAFFECTED

SameUnitRelationClassifier
  admitted Candidate + Active incumbent Memory
  -> EQUIVALENT | REFINES | CONTRADICTS | UNRELATED | INSUFFICIENT
```

ChangeBundles contain all changed ReadingGroups that fit one shared state. Three groups plus 300 fixed claims therefore produce 300 questions, not 900. If capacity requires several bundles, application code OR-reduces each claim's labels: any `AFFECTED` routes that claim to complete Support Assessment. Evidence already classified `MODIFIED`, `REMOVED` or `AMBIGUOUS` bypasses Change Impact and enters Support Assessment directly; `UNKNOWN` is an application-owned unresolved coverage result and KEEP. It is not a semantic classifier label.

Same-Unit Relation consumes deterministic exact matches first, then constructs the complete remaining `N × M` pair manifest. Catalog bodies occur once in shared state and questions carry IDs. Requests are packed by estimated input capacity and run with bounded concurrency. Every pair must return exactly one label before reduction; partitioning cannot weaken coverage, introduce lifecycle state or publish partial results. Whole-workspace relation discovery remains retrieve-then-classify over bounded `K` because its Cartesian product is unbounded and non-destructive discovery accepts recall loss.

TypeSafe/Jev evaluates independent Choice, Noul or Score questions over shared text state. A small-model LLM adapter emits the same application-owned result schema. Jev's current 64k request limit, text-only input and Choice option limit are adapter capabilities, not domain semantics. Jev has no documented cross-request prompt cache; its efficiency comes from many questions sharing one state. See [Models](https://docs.typesafe.ai/models), [System One](https://docs.typesafe.ai/concepts/system-one.md) and [Parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions.md).

Complete Support Assessment remains `GenerationWork`, even though its final semantic result is a small union. One Primary, zero or more Required refs, opposing witnesses and streamed previous state form one dependent Evidence-plan proposal. Splitting them into independent classifier questions would recreate a second Support engine in application code.

Missing answers, unknown IDs, incomplete manifests, unsupported modality, capacity failure or provider failure are technical work failures. They never become labels and do not trigger a hidden backend fallback. Retry uses the configured backend and exact work identity; changing backend is an explicit operation policy/configuration change.

### Support planning and execution contract

The boundary is task-shaped rather than confidence-shaped:

| Step | Owner | Input | Output |
| --- | --- | --- | --- |
| Exact Evidence correspondence | application code | prior Evidence metadata + current Fragment catalog + provider coverage | `EXACT_UNCHANGED / CONTAINER_CHANGED / MODIFIED / REMOVED / AMBIGUOUS / UNKNOWN` |
| Support context planning | application code | correspondence + CatalogDiff + ReadingGroups + complete current manifest + capacity forecast | Delta contexts + remaining Full contexts + coverage receipt |
| Change Impact | classifier model (Jev or small-parameter LLM) | fixed claims + one shared capacity-safe ChangeBundle | exactly one `AFFECTED / UNAFFECTED` per claim |
| Delta/Full semantic scan | Structured LLM | fixed claims + current AssessmentContext catalog + rule-governed historical excerpt + carried current witnesses | next witness state; at phase end `SUPPORTED / NEEDS_FULL / UNSUPPORTED` as allowed below |
| Final validation and lifecycle reduction | application code | model proposal + complete manifest + allowed refs + current Support set + stale guards | `COMPLETED` or `UNRESOLVED`; guarded KEEP/REBIND/REMOVE proposal |

The classifier is used only for an independent closed-label question whose full
input is already supplied: “can this changed bundle affect this fixed claim?” It
does not search for or compose Evidence. The Structured LLM is used where several
current fragments may jointly support a claim and one Primary plus Required refs
must be selected as a coherent unit.

`RevisionContextPlanner` is deterministic application code. It uses exact
Fragment correspondence, CatalogDiff, provider coverage, capacity estimates and
the current-revision manifest to produce this conceptual plan:

```json
{
  "work_manifest": ["WRK-0001"],
  "initial_scope": "DELTA",
  "delta_contexts": ["CTX-0001"],
  "remaining_full_contexts": ["CTX-0002", "CTX-0003"],
  "provider_coverage": "COMPLETE",
  "current_ref_catalog": ["PRM-0001", "REQ-0002"]
}
```

The planner starts at `FULL_CURRENT_REVISION` when Delta already covers the
complete Full manifest, or when the complete serialized Full plan is no more
expensive than Delta followed by its continuation. It does not ask a
model whether a negative Delta is conclusive, and the plan has no
`negative_conclusive` field. Delta may finalize only a positive `SUPPORTED`
result. A Delta scan that cannot build complete current Support transitions to
the already-planned Full continuation. Only a completed Full manifest under
authoritative coverage may finalize `UNSUPPORTED`.

Each non-final Structured-LLM scan call receives only semantic material:

```json
{
  "phase": "delta_scan",
  "context": {
    "context_id": "CTX-0001",
    "reading_groups": [{"heading": "Approval", "text": "..."}],
    "evidence_catalog": [
      {"ref": "PRM-0001", "text": "...", "primary_eligible": true}
    ]
  },
  "works": [{
    "work_id": "WRK-0001",
    "fixed_claim": "Payroll release requires two approvals.",
    "historical_excerpt": "...",
    "previous_state": {
      "support_witness_refs": [],
      "opposing_witness_refs": []
    },
    "carried_witness_catalog": []
  }],
  "is_last_context_in_phase": true
}
```

`historical_excerpt` is present exactly for `MODIFIED`, `REMOVED` and
`AMBIGUOUS`; it is absent for every other Evidence state. The application
rehydrates every carried current witness as `{ref, text, primary_eligible}` in
`carried_witness_catalog`; refs alone are not enough for the next call to reason
about their meaning. Digests, offsets, durable IDs, coverage proofs and
lifecycle history remain outside model input.

A non-final call returns only bounded current-revision witness additions:

```json
{
  "work_id": "WRK-0001",
  "witness_delta": {
    "support_witness_refs": ["PRM-0001"],
    "opposing_witness_refs": []
  }
}
```

Every returned ref must occur in the call's current catalog or carried current
witness catalog. Historical refs are never selectable. Application code
monotonically union-merges validated `witness_delta` refs into the prior
supporting/opposing sets; a later model call cannot delete an earlier decisive
witness by omission. The model does not emit a cumulative `status`; the
application knows whether the manifest is complete and rehydrates its owned
union into the next `carried_witness_catalog`.

After the Delta manifest completes, the Structured LLM returns one of:

```text
SUPPORTED(work_id, primary_ref, required_refs[])
NEEDS_FULL(work_id, witness_delta)
```

`NEEDS_FULL` is an internal execution transition, not a lifecycle or Support
status. Application code first merges its `witness_delta`, then the Full
continuation consumes the remaining current contexts and the accumulated
witnesses instead of restarting. After the Full manifest completes,
the only semantic results are:

```text
SUPPORTED(work_id, primary_ref, required_refs[])
UNSUPPORTED(work_id)
```

The application wraps execution separately:

```text
COMPLETED(SUPPORTED | UNSUPPORTED)
UNRESOLVED(reason)
```

`UNRESOLVED` covers partial provider coverage, incomplete manifest, capacity or
provider failure, invalid schema, and model abstention. It causes KEEP, blocks
destructive action and does not advance the Support baseline. It is execution
state, not a third semantic assessment result.

## 5. Current semantic-call inventory

The current `LiteLlmStructuredClient` mixes generation, classification and ranking. Target design migrates semantic responsibilities to the two executor interfaces rather than copying every historical wrapper.

| Responsibility | Shape | Target executor |
| --- | --- | --- |
| Claim Extraction / managed patch | open-vocabulary claim or patch generation | Structured LLM `GenerationExecutor` |
| Complete Support Assessment | dependent status + Primary/Required + carried witnesses | Structured LLM `GenerationExecutor` |
| Change Impact | fixed claim vs shared ChangeBundle; `AFFECTED/UNAFFECTED` | classifier model (Jev or small-parameter LLM) |
| Same-Unit Relation | complete exact-excluded `N × M` pair manifest; one relation label per pair | classifier model (Jev or small-parameter LLM) |
| Cross-document relation | bounded retrieved `K` pairs; one relation label per pair | classifier model (Jev or small-parameter LLM) |
| Candidate admission | dependent nonredundant subset over one candidate cohort | existing Structured LLM `GenerationWork`; deterministic normalization remains code |
| Entity adjudication | select a supplied candidate or no match | classifier model (Jev or small-parameter LLM) |
| Retrieval rerank | comparable relevance score | classifier model (Jev or small-parameter LLM) |
| Offline semantic judge / agent authority | fixed labels over complete supplied state | classifier model (Jev or small-parameter LLM) |
| Query entity detection | open-vocabulary extraction | Structured LLM unless code supplies a closed set |

Exact Fragment correspondence, CatalogDiff, coverage, selector validation, manifests and lifecycle actions remain code. `EvidenceFragment`, `ReadingGroup`, `AssessmentContext` and `AssessmentScope` are distinct: a ReadingGroup may contain several selectable fragments; one AssessmentContext contains one or more groups for one call; the AssessmentScope is DELTA or the complete effective current revision across all calls.

## 6. User-selectable execution profiles

Configuration separates generation from task-scoped classification:

```text
generation_executor = structured_llm
classifier_backend.change_impact = jev | small_llm
classifier_backend.same_unit_relation = jev | small_llm
classifier_backend.cross_document_relation = jev | small_llm
```

There is no `jev_with_llm_fallback` profile and no per-item confidence routing. Each registered classifier task has one configured backend, pinned model and contract version. A backend is production-eligible for that task only after the task's fixed evaluation suite passes; otherwise the task remains on its previous whole-task implementation. Provider failure produces typed failed/unresolved work and ordinary retry, never silent substitution.

Complete Support Assessment is always compound `GenerationWork`. Users cannot route it through a classifier backend. Executor, model, contract, complete pair/work manifest and ContextBundle digest participate in derivation identity; changing configuration does not reprocess unchanged Sources automatically.

## 7. Rollout and acceptance

Classifier backends begin with fixed, non-mutating evaluation cases. Acceptance is per task contract and model version, not per response confidence. Evaluation records exact label quality, especially `AFFECTED` recall; complete item/pair coverage; unknown-ID and truncation rejection; input/output tokens; concurrency and latency; and lifecycle simulation proving that labels alone cannot perform REMOVE, SUPERSEDE or RETIRE.

Same-Unit Relation acceptance includes exact-excluded full rectangles, `N × M` capacity partitioning, idempotent retries and equality of results across legal partitions. Change Impact acceptance includes several changed groups combined into one bundle, multiple bundles OR-reduced by code, distant revocation/exception examples, and source types represented by Markdown/Confluence, Jira and Teams. Complete Support Assessment is evaluated separately as Structured LLM generation/compound proposal work.

## 8. Non-goals

- no universal provider interface that pretends generation and classification have identical capabilities;
- no per-item confidence fallback or hidden model substitution;
- no classifier-owned lifecycle action, authority, selector membership or work completeness;
- no correctness dependency on prompt-cache retention;
- no undocumented Jev cross-request cache assumption;
- no human confirmation stage for ordinary source lifecycle;
- no classifier-only claim generation, image understanding or compound Support Assessment;
- no semantic retrieval pruning of mandatory same-Unit relation pairs;
- no second lifecycle state machine or provider-specific domain branch.

## 9. Research basis

The parser survey, TypeSafe primitive/API review and provider cache evidence are
captured in
[Structure-preserving parsers, Jev judgments, and repeated-context caching](../research/2026-09-21-structure-parsers-jev-prompt-cache.md).
The concurrency and cache-visibility comparison supporting the minimal batch
dispatcher is captured in
[Prompt-cache-aware batch scheduling](../research/2026-09-21-prompt-cache-aware-batch-scheduling.md).
The research note is supporting evidence; this document and the corresponding
ADRs remain the normative product contract.
