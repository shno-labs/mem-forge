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

`GenerationWork` may create open-vocabulary text such as a new claim.
`JudgmentWork` chooses, scores or verifies values already defined by application
code. A Structured LLM may implement both interfaces. Jev implements only the
second. This prevents a provider abstraction from hiding a real capability
difference.

The model never owns Source authority, exact offsets, allowed selectors,
complete work coverage, lifecycle verbs, stale guards or atomic commit. Those
remain application facts and validators regardless of executor.

## 2. Context is a domain plan, not a prompt string

Each domain planner produces one immutable, backend-neutral `ContextBundle`:

```python
ContextBundle(
    contract=ContextSegment(...),
    revision_shared=ContextSegment(...),
    cohort=ContextSegment(...),
    carried_state=ContextSegment(...),
    attempt=ContextSegment(...),
    manifest=WorkManifest(...),
)
```

Every segment has:

- a semantic role, exact content and content digest;
- revision, access and work identity where applicable;
- selectable versus read-only material;
- one stability class: `CONTRACT`, `REVISION_SHARED`, `COHORT`, or `ATTEMPT`;
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
For repeated calls over one revision, the Structured LLM adapter renders:

```text
1. CONTRACT
   stable instructions + static output contract

2. REVISION_SHARED
   current ReadingGroup/catalog content shared by the request cohort

3. COHORT
   fixed claims, candidate pairs, per-work allowed references

4. CARRIED_STATE
   compact support/opposition witnesses or completed slots

5. ATTEMPT
   bounded repair diagnostics; absent on the first attempt
```

Stable material must precede variable material. A provider cache breakpoint, if
supported, is placed after the largest reusable `REVISION_SHARED` prefix. A
batch planner should keep calls for the same contract and revision prefix
adjacent, while still respecting complete coverage, latency and concurrency
limits. It must not enlarge semantic batches solely to chase a cache hit.

For Anthropic-compatible routes, exact-prefix order is `tools`, then `system`,
then `messages`. Stable tool/response definitions therefore come before the
stable system contract and revision-shared message content; cohort work,
carried state and repair diagnostics follow the final reusable breakpoint.
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
| Memory relation discovery | `classify_memory_relations` | equivalent/refines/contradicts/unrelated choice for supplied pairs | strong candidate |
| Revision proof | `prove_revision_compositions` | several fixed boolean conditions | candidate as independent Nouls composed by code |
| Claim Reconciliation | `assess_claim_revisions` | sparse relation plus conditional revision proof | candidate after decomposition; no full pair product |
| Retrieval rerank | `rerank_memories` | comparable relevance degree | strong Score candidate |
| Offline semantic judge | `judge_offline_semantics` | fixed evaluation labels | strong candidate |
| Agent-session authority | `classify_agent_session_evidence_authority` | per-candidate authority decision | strong candidate |
| Selector correction | `correct_projection_fragment_selectors` | bounded closed-set selection | possible for small text-only catalogs; not first rollout |
| Support Assessment | `evaluate_revision_work`, `assess_revision_support`, `validate_memory_support` | status plus complete Primary/Required Evidence Unit across streamed context | shadow/evaluation first; compound state and multi-select Evidence make direct replacement high risk |
| Incumbent audit legacy path | `audit_incumbent_support` | fixed support judgment | classifier-shaped, but remove/delegate if ADR 0034 supersedes the call |

Support Assessment illustrates why “LLM and Jev are both calls” is true only
below the domain interface. Jev can ask a status Choice, one Primary Choice and
independent Required-candidate Nouls, but code must still prove complete catalog
coverage and a coherent Evidence Unit. Because the questions are independent,
the design does not assume Jev has reproduced the current multi-step Support
semantics until a representative evaluation demonstrates it.

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
question contract and risk class. Relation/rerank/entity work may qualify before
Support Assessment. A destructive lifecycle proposal still passes the same
automatic `DestructiveValidation`; confidence alone can never authorize REMOVE,
SUPERSEDE or RETIRE.

## 8. Non-goals

- no universal provider interface that pretends generation and classification
  have identical capabilities;
- no model-owned lifecycle action, authority, offset, selector membership or
  work completeness;
- no dependency on provider cache retention for correctness or recovery;
- no undocumented Jev prompt-cache assumption;
- no human confirmation stage added to ordinary source lifecycle;
- no Jev-only claim generation, image understanding or semantic Evidence search;
- no second lifecycle state machine or provider-specific domain branch.

## 9. Research basis

The parser survey, TypeSafe primitive/API review and provider cache evidence are
captured in
[Structure-preserving parsers, Jev judgments, and repeated-context caching](../research/2026-09-21-structure-parsers-jev-prompt-cache.md).
The research note is supporting evidence; this document and the corresponding
ADRs remain the normative product contract.
