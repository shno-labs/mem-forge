# Semantic judgment execution and context reuse

Date: 2026-09-21. This document is a target design. It does not claim that
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
     -> TypeSafe/Jev adapter, only for eligible judgment work
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
by application code. A Structured LLM may implement both interfaces. Jev
implements only the second. This prevents a provider abstraction from hiding a
real capability difference.

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
    reading_group=ContextSegment(...),
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
  `READING_GROUP`, `CARRIED_STATE`, or `ATTEMPT`;
- a deterministic order within its stability class.

The bundle contains structured application state, not provider messages,
TypeSafe questions or a serialized prompt. Executor adapters render it:

- the Structured LLM adapter creates system/user content, response schema,
  images and provider cache breakpoints;
- the Jev adapter creates one `state` object plus independent Choice, Noul or
  Score questions;
- tests can inspect the same canonical bundle without parsing either wire
  format.

The domain planner, not either executor, decides which ReadingGroups, fixed
claims, candidates, Evidence catalogs, historical excerpts and cumulative
witnesses are logically required. Switching executor cannot silently widen or
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

`REVISION_FIRST` is used when one ReadingGroup is evaluated against several
claim or candidate cohorts. `COHORT_FIRST` is used when one fixed cohort scans
several ReadingGroups, as in streamed Support Assessment. Each work contract
declares one layout; Support Assessment declares `COHORT_FIRST`. There is no
runtime cache-layout optimizer. Retries preserve the declared layout. This
changes serialization order only. Named segment content, the context digest,
logical coverage and instructions remain the same.

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

## 4. Jev execution model

TypeSafe describes Jev as a System One model: it evaluates text or structured
text state and returns typed decisions and probabilities rather than generated
text. It currently accepts no image, audio or video input. Its primitives are:

| Primitive | Domain shape |
| --- | --- |
| Choice | exactly one value from an application-defined option set |
| Noul | probability that one clearly defined condition is true |
| Score | position over application-defined ordered levels |

Questions in one request share the same state and are evaluated independently;
one question cannot consume another question's answer. Dependent work therefore
requires another bounded request. Choice supports at most 255 options. These are
current provider capabilities, not MemForge lifecycle semantics. See
[System One](https://docs.typesafe.ai/concepts/system-one.md),
[Primitives](https://docs.typesafe.ai/primitives.md), and the
[HTTP API](https://docs.typesafe.ai/api.md).

The Jev adapter maps only an eligible `JudgmentSpec`:

```python
JudgmentSpec(
    judgment_id=...,
    kind=CHOICE | BOOLEAN | SCORE,
    instructions=...,
    options_or_levels=...,
    risk=NON_DESTRUCTIVE | DESTRUCTIVE_INPUT,
)
```

It returns the application-owned result shape plus engine evidence:

```python
JudgmentResult(
    judgments=...,
    complete_manifest=...,
    engine_id="typesafe",
    model_id="jev-...",
    contract_id=...,
    context_digest=...,
    raw_probabilities=...,
)
```

Raw probabilities and Jev confidence are diagnostic inputs to an
application-owned threshold policy. They are never lifecycle authority. Low
confidence, missing answers, unsupported modalities, too many Choice options or
provider failure yield a typed unresolved result. The configured policy may
then use a Structured LLM fallback or preserve current state; it may not invent
an answer.

No TypeSafe document reviewed for this design promises reusable prompt/KV
caching. Jev efficiency should therefore come from asking independent questions
over one shared state in one call, not from assuming undocumented cache behavior.
The current public API exposes the System One request rather than an offline
batch/job service. Its documented request/model limits are capability-admission
inputs and must be version-pinned and rechecked; they are never a reason to
truncate a logical work manifest.

## 5. Current semantic-call inventory

The current `LiteLlmStructuredClient` exposes both generation and judgment
methods. New design should target semantic responsibilities and remove or
delegate superseded wrappers instead of implementing a second adapter for every
historical method name.

| Responsibility | Current examples | Shape | Jev target |
| --- | --- | --- | --- |
| Claim Extraction | `extract_memories`, `extract_projection_memories`, `extract_projection_fragment_memories` | generate claim text/type and select Evidence | no; requires `GenerationExecutor` |
| Managed agent patch | `generate_agent_knowledge_patch` | generate a new patch/claim | no |
| Query entity detection | `detect_query_entities` | open-vocabulary entity extraction | no unless code first supplies a closed candidate set |
| Candidate admission ledger | `select_memory_candidates` | KEEP/DROP choice over fixed candidates | strong candidate |
| Source support | `verify_source_support` | supported/unsupported/insufficient judgment | strong candidate |
| Entity adjudication | `validate_entity_match`, `validate_entity_batch` | choose candidate or no match | strong candidate within Choice limit |
| Relation adjudication | `classify_memory_relations` | equivalent/refines/contradicts/unrelated choice for an already bounded pair set | Jev candidate only for supplied `K` pairs; it does not discover pairs from `N × M` |
| Revision proof | `prove_revision_compositions` | several fixed boolean conditions | candidate as independent Nouls composed by code |
| Claim Reconciliation | `assess_claim_revisions` | discover sparse material edges from Candidate and Memory catalogs plus conditional revision proof | no direct Jev replacement; keep Structured LLM unless an upstream contract already supplies bounded pairs |
| Retrieval rerank | `rerank_memories` | comparable relevance degree | strong Score candidate |
| Offline semantic judge | `judge_offline_semantics` | fixed evaluation labels | strong candidate |
| Agent-session authority | `classify_agent_session_evidence_authority` | per-candidate authority decision | strong candidate |
| Selector correction | `correct_projection_fragment_selectors` | bounded closed-set selection | possible for small text-only catalogs; not first rollout |
| Complete Support Assessment | `evaluate_revision_work`, `assess_revision_support`, `validate_memory_support` | one dependent proposal containing status, Primary, zero or more Required refs and carried witnesses across streamed context | no; keep on `GenerationExecutor` with Structured LLM |
| Incumbent audit legacy path | `audit_incumbent_support` | fixed support judgment | classifier-shaped, but remove/delegate if ADR 0034 supersedes the call |

Complete Support Assessment illustrates why “LLM and Jev are both calls” is true
only below the domain interface. Its status, Primary, Required refs and carried
witnesses constrain one another. Splitting them into independent Jev questions
can produce an internally inconsistent result such as `supported` without the
Required Evidence that entails the complete claim. Recombining those answers
would recreate a second Support-assessment engine in application code.

Therefore complete Support Assessment is outside Jev capability admission. It
does not enter Jev shadow evaluation, fallback or production routing. A smaller,
independently useful judgment such as whether one supplied excerpt supports one
proposition may be registered separately, but it cannot stand in for the complete
Evidence Unit assessment.

Relation work has a second boundary. A Structured LLM can receive one Candidate
catalog of size `N` and one Memory catalog of size `M`, encode each item once,
and return `N` rows containing only `K` material edges. Its transport is roughly
`N + M + K`; this does not prove that the model's internal semantic work is
linear. Jev must not replace that sparse discovery by asking one question for
every possible pair, which would create `N × M` questions. It may adjudicate the
`K` pairs only when deterministic rules, bounded retrieval or a prior semantic
stage already supplied them. If no safe bounded pair set exists, sparse Claim
Reconciliation remains Structured LLM work.

A single Jev Choice with all Memory IDs is not a general substitute: it selects
only one result, cannot express multiple material edges, multiplies Memory IDs by
relation types, and is subject to the provider's Choice-option limit. It remains
appropriate for domains such as entity resolution where exactly one candidate or
`no_match` is the declared contract.

## 6. User-selectable execution profiles

Configuration separates generation from judgment:

```text
generation_executor = structured_llm
judgment_profile = structured_llm | jev_with_llm_fallback | jev_only_eligible
```

`structured_llm` uses the configured LLM for all work.
`jev_with_llm_fallback` uses Jev only for operations whose registered capability
and calibrated acceptance policy permit it, then falls back on an unresolved
result. `jev_only_eligible` never silently routes an eligible judgment to an LLM;
unsupported generation work still uses the separately configured generation
executor.

Complete Support Assessment is always registered as generation/compound-proposal
work and therefore always uses the configured Structured LLM executor. A user
judgment profile cannot route it through Jev.

The UI may present these as execution profiles, but the persisted contract is
an operation-to-executor policy with explicit model and contract versions. A
single “use Jev for everything” Boolean would be misleading because Jev cannot
generate claims or consume images.

Executor selection participates in derivation/work identity. Completed output
from one model, question contract or ContextBundle digest cannot be reused under
another. Switching profile does not reprocess unchanged Sources by itself.

## 7. Rollout and acceptance

Jev begins in sampled shadow mode on fixed, non-mutating inputs. The existing
executor remains authoritative while evaluation records:

- exact label agreement and material disagreements;
- probability calibration on adjudicated outcomes;
- unresolved/fallback rate;
- selector and complete-coverage validity;
- input/output tokens, prompt-cache reads/writes where applicable;
- provider and end-to-end latency;
- lifecycle simulation, including false destructive proposals.

Production eligibility is granted per semantic responsibility, model version,
question contract and risk class. Relation, rerank and entity work can qualify;
complete Support Assessment is not part of this rollout. A destructive lifecycle
proposal still passes the same automatic `DestructiveValidation`; confidence
alone can never authorize REMOVE, SUPERSEDE or RETIRE.

## 8. Non-goals

- no universal provider interface that pretends generation and classification
  have identical capabilities;
- no model-owned lifecycle action, authority, offset, selector membership or
  work completeness;
- no dependency on provider cache retention for correctness or recovery;
- no undocumented Jev prompt-cache assumption;
- no human confirmation stage added to ordinary source lifecycle;
- no Jev-only claim generation, image understanding or semantic Evidence search;
- no Jev shadow, fallback or production path for complete Support Assessment;
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
