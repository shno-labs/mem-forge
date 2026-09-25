# Semantic judgment execution and context reuse

Date: 2026-09-24. This document is a target design. It does not claim
that TypeSafe/Jev, provider prompt caching, the LLM batch runner or the
described executor interfaces are implemented or deployed. The LLM batch runner
is the first step of
[Cloud issue #505](https://github.com/dodoman-sun/memforge-cloud/issues/505):
its first PR delivers the runner and moves the existing call sites onto it. #505
also tracks the Support, Relation and coordination semantics the runner carries.
[Cloud issue #506](https://github.com/dodoman-sun/memforge-cloud/issues/506)
builds on the runner with the executor interfaces, classifier backends, their
evaluation (Jev included) and prompt caching.

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
     -> LLM batch runner (capacity, partitioning, split on capacity failure,
        concurrency, coverage, correction, typed failures)
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

Both executors send every request through one LLM batch runner (section 4). No
call site checks context capacity, splits requests or handles timeouts on its
own.

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

`REVISION_FIRST` suits one Evidence Catalog or AssessmentContext evaluated
against several claim cohorts. `COHORT_FIRST` suits one cohort reading several
AssessmentContexts in order. The layout is chosen from the logical partition,
not by a cache-hit optimizer, and a retry keeps it. It is not a correctness
condition: when a Support item exits on complete Support or the LLM batch runner
splits a request, later requests carry a different cohort prefix and a cache miss
is acceptable. Serialization order changes, but named content,
digest, coverage and instructions do not.

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

Prompt caching does not introduce another batch planner or queue. The LLM batch
runner (section 4) creates capacity-safe requests and dependency lanes;
its bounded concurrency, built on the existing collector and Structured LLM
semaphore, is the only concurrency control.

- A stateful lane, such as one Support cohort reading several ReadingGroups,
  remains sequential inside the lane. Its first real request can create the
  cache entry and later requests reuse the cohort prefix until an item exits or
  the lane is split.
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

## 4. LLM batch runner

**Status: target design. The runner is the first step of Cloud issue #505: its
first PR delivers the runner and moves the existing call sites onto it, and
Support Assessment uses the ordered-chain form. Cloud issue #506 adds the
executor interfaces, classifier backends and prompt caching on top. Current code
checks capacity, partitions requests and validates coverage separately at each
call site.**

Batching is a transport detail. Every path that sends work to a model, whether
Structured LLM generation, Structured LLM judgment or a classifier model, goes
through one LLM batch runner. No call site handles input-context overflow or
timeouts on its own.

```python
class LlmBatchRunner:
    async def run_items(self, task: ItemTask) -> dict[ItemId, Result | ItemFailure]: ...
    async def run_chain(self, task: ChainTask) -> dict[ItemId, ChainEnd | ItemFailure]: ...

@dataclass(frozen=True)
class ItemFailure:
    category: Literal["capacity_exceeded", "deadline_exceeded",
                      "provider_error", "invalid_response"]
    error_code: str
```

**What the caller supplies**

- Fixed work items with stable application IDs. An item is the unit of coverage:
  a Claim, a Candidate, a ReadingGroup that holds authorized Claim Extraction
  work, or the whole rerank candidate list.
- Shared context from the `ContextBundle`, as an ordered list of separable parts,
  such as the changed ReadingGroups for Change Impact, the old Memory Claims for
  Sparse Relation or this round's Candidate claims for candidate admission. When
  the parts do not fit one request together with an item, the runner chunks them
  at part boundaries and returns one result per item and chunk. The caller merges
  those results: OR for Change Impact, the union of relations for Sparse
  Relation, and for candidate admission the reported duplicates are merged
  deterministically. The
  runner never receives merge rules.
- The prompt contract and response schema, and a decoder that applies task
  validation such as allowed refs. Adapters render shared context before items
  so the prefix stays stable.
- Optionally, the existing `DerivationWork` stage and record calls, for tasks
  that already persist per-request work.

**Two shapes**

- Independent items (`run_items`): Change Impact, candidate admission, Sparse
  Relation, entity adjudication, cross-document relation, rerank and Claim
  Extraction. Candidate admission's same-round dedup is a cohort-level output of
  the same request. Rerank is one indivisible listwise item: the runner never
  splits it, and the search caller passes its own deadline.
- Ordered chain (`run_chain`): Support Assessment. The caller supplies a cohort
  of Claims, AssessmentContexts in reading order and the compact carried state
  (the witness union) that is rehydrated in every request. The task carries a
  first-part boundary per item, because each Claim's first part is all changed
  ReadingGroups plus that Claim's own old-Evidence groups. Steps inside a lane run
  in order. Once its first part has been read, an item for which the step
  returned a validated `SUPPORTED` leaves the lane. Only an item that has read the whole
  order may end `UNSUPPORTED`. State merging stays in the caller's decoder.

**What the runner owns**

1. Capacity fit from LiteLLM metadata (`litellm.get_model_info`,
   `litellm.token_counter`) capped by the existing `MEMFORGE_LLM_MAX_*`
   overrides, with the existing correction reserve. There are no per-task item or
   character caps. The only other limits are ones a backend adapter declares, such
   as Jev's Choice option count.
2. Packing items, in order, into transport requests that fit.
3. Splitting on capacity failure. A request holding several items that ends in
   `deadline_exceeded`, `input_capacity_exceeded`, a provider 413
   `payload_too_large` or truncated output (`finish_reason=length`) is a capacity
   failure: the runner splits it into two halves and resends each half until they
   complete. Truncated output is not resent as JSON text at the same
   `max_tokens`. In the chain form a cohort splits into two lanes that continue
   from the same position with their own state, and a step holding a single Claim
   that spans several ReadingGroups first halves its ReadingGroups. A request
   holding one item, and in the chain form one ReadingGroup, that still fails
   returns a typed `ItemFailure` with diagnostics. The failure says whether that
   item alone exceeds the route's input capacity (from the capacity fit,
   `input_capacity_exceeded` or a provider 413) or failed otherwise, for example
   with a provider error, a timeout, or a schema or ID failure after the one
   correction.
4. Bounded concurrency through the existing collector and Structured LLM
   semaphore.
5. Complete coverage. Every submitted item ends with exactly one outcome, a
   result or an `ItemFailure`. Missing, unknown or duplicate IDs are rejected.
6. One bounded correction per request for correctable decoder errors, with the
   same input and allowed refs. JSON repair and transient provider retries stay
   inside the client.
7. Typed per-item failures. The runner never turns a failure into a label, never
   substitutes another model and never retries on a different backend.

**What the caller decides**

The business meaning of an `ItemFailure` belongs to the task:

| Task | Outcome of an item failure |
| --- | --- |
| Support Assessment and its targeted re-check | a ReadingGroup that alone exceeds capacity: `UNRESOLVED(capacity)`, KEEP, the Support baseline does not advance, and the diagnostic names the Source Unit and the ReadingGroup; any other failure: the Source Unit revision is not committed and the next sync retries it |
| Change Impact | the Claim enters Support Assessment; no `AFFECTED` label is recorded |
| Candidate admission | extraction-side failure: the Source Unit revision is not committed, so the Candidate is not added this round, and the next sync retries the revision |
| Sparse Relation | extraction-side failure: the Source Unit revision is not committed and the next sync retries it; never read as "no relation proposed" |
| Rerank | baseline order, also on timeout or invalid output; a fixed code rule, not configuration |
| Claim Extraction | the existing extraction failure for that Source Unit; no partial candidates |

**What it does not add**

No configuration beyond LiteLLM metadata, the existing `MEMFORGE_LLM_MAX_*`
overrides and `request_timeout_s`; no output budget or tokens-per-second
presizing; no business cache key; no lifecycle or business state; no per-item
model switching; no hidden provider fallback; no queue or leader barrier. Legal
partitions and split points never change coverage, work identity, the result
schema or lifecycle meaning; with a deterministic fixture client, results are
identical across legal partitions and split points. The runner does not choose
reading order, labels or lifecycle actions.

**Cloud impact.** Cloud reaches models through LiteLLM `sap/` routes with
environment-only configuration and `llm_config_writable = false`. The runner
reads capacity only from LiteLLM metadata and the existing environment
overrides, so Cloud needs no new settings. It wraps the existing
`LiteLlmStructuredClient` without changing its constructor. #505's first PR
deletes `SourceSupportDetector`, so Cloud's `proxy/external_runtime.py` must
drop its import (line 23), its construction (line 217) and the
`source_support_detector=` arguments to `SyncRuntime` (line 237) and
`CloudGeneSyncOrchestrator` (line 249) in the same wave as the pin upgrade. Optional `DerivationWork` journaling
reuses store methods that HANA already implements; no protocol in
`storage/adapters/protocols.py` changes. Cloud's pinned LiteLLM version must
expose `get_model_info` and `token_counter` for its configured routes, which the
client already uses today. Cloud upgrades the OSS pin.

## 5. Classifier-model execution

A classifier task has complete bounded input, application-defined labels and independent per-item answers. The runtime name is **classifier model (Jev or small-parameter LLM)**; Jev is one adapter, not a domain stage. A task is admitted to this interface only as a whole after a fixed evaluation set meets its label-quality and coverage criteria. Raw probabilities remain diagnostic telemetry and offline calibration data; they do not create per-item confidence fallback branches.

The Source-lifecycle judgment contracts (classifier or Structured LLM) are:

```text
ChangeImpact (JudgmentWork)
  fixed claim + capacity-safe ChangeBundle
  (added and modified ReadingGroups, plus the old text of removed ones)
  -> AFFECTED | UNAFFECTED

SparseRelation (JudgmentWork, Structured LLM)
  admitted Candidates + each Candidate's current Evidence
  + Claims of all Active same-Unit old Memories
  -> one row per Candidate listing only meaningful relations

CandidateAdmission (GenerationWork, Structured LLM)
  items: Candidates of one revision + their selected Primary/Required Evidence
  shared context: every Candidate claim of the revision (ID + claim text only)
  -> ADMITTED | REJECTED(reason) per Candidate, plus reported same-round duplicates
```

Change Impact runs on the existing Structured LLM until a classifier backend
(Jev or a small-parameter LLM) passes the #506 evaluation for that task. Its
instruction includes one fixed rule: a change containing a global statement with
unclear scope, such as "the process above", "this document" or "discontinued
from a given date", is `AFFECTED`. The rule has no dedicated evaluation cases;
the generic #506 classifier evaluation applies.

`REJECTED` has two reasons: the selected Evidence does not completely support
the Claim, or `low_value`, which replaces the current ledger's
`DROP_LOW_VALUE`. Every admission request carries all of this round's Candidate
claims as shared context, so the model can report a duplicate that sits in
another request; the program merges reported duplicates deterministically.

Sparse Relation never receives Support results or their reasons and does not
check whether Evidence supports the Candidate; candidate admission owns that
check. Omitting an old Memory means "no relation proposed". A pairwise
classifier backend that returns one label per Candidate/old Memory pair would
need its own contract and evaluation before it could replace the sparse
contract.

Cloud impact: Change Impact, Sparse Relation and candidate admission run on the
Structured LLM that Cloud already reaches through LiteLLM `sap/` routes and
`AICORE_*` environment variables, so Cloud needs no classifier route or new
setting until a classifier backend passes evaluation and is configured.

ChangeBundles contain all changed ReadingGroups that fit one shared state. Removed content counts as changed: a removed ReadingGroup enters the bundle as its old text, so a distant qualifier that was deleted is visible to Change Impact. Three groups plus 300 fixed claims therefore produce 300 questions, not 900. If they do not fit one request, the runner chunks them at ReadingGroup boundaries into several bundles and application code OR-reduces each claim's labels: any `AFFECTED` routes that claim to complete Support Assessment. When Change Impact execution fails for a claim, for example a single item that still fails after the runner's splitting, an indivisible bundle beyond the backend's capacity, or a bundle with images that a text-only backend cannot read, that claim enters Support Assessment. The failure is never recorded as an `AFFECTED` label.

Sparse Relation consumes deterministic exact matches first. Catalog bodies occur once per request; the LLM batch runner packs and splits requests, and when the old Memory catalog must be chunked the program takes the union of each Candidate's relations. Every admitted Candidate must return exactly one row. A missing row, an unknown ID or a duplicate or contradictory relation is rejected, and truncated output is a capacity failure that the runner splits; none of them is read as "no relation proposed". A failure that remains is an extraction-side failure: the Source Unit revision is not committed and the next sync retries it. Partitioning cannot weaken coverage, introduce lifecycle state or publish partial results. Whole-workspace relation discovery remains retrieve-then-classify over bounded `K` because its Cartesian product is unbounded and non-destructive discovery accepts recall loss.

TypeSafe/Jev evaluates independent Choice, Noul or Score questions over shared text state. A small-model LLM adapter emits the same application-owned result schema. Jev's current 64k request limit, text-only input and Choice option limit are adapter capabilities, not domain semantics. Jev has no documented cross-request prompt cache; its efficiency comes from many questions sharing one state. See [Models](https://docs.typesafe.ai/models), [System One](https://docs.typesafe.ai/concepts/system-one.md) and [Parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions.md).

Complete Support Assessment remains `GenerationWork`, even though its final semantic result is a small union. One Primary, zero or more Required refs, opposing witnesses and streamed previous state form one dependent Evidence-plan proposal. Splitting them into independent classifier questions would recreate a second Support engine in application code.

Missing answers, unknown IDs, incomplete manifests, unsupported modality, capacity failure or provider failure are technical work failures. The LLM batch runner first splits a multi-item request that hit a capacity failure in half; only a failure that remains for a single item is reported. Failures never become labels and do not trigger a hidden backend fallback. Retry uses the configured backend and exact work identity; changing backend is an explicit operation policy/configuration change.

### Support planning and execution contract

The boundary is task-shaped rather than confidence-shaped:

| Step | Owner | Input | Output |
| --- | --- | --- | --- |
| Exact Evidence correspondence | application code | prior Evidence metadata + current Fragment catalog + provider coverage | per part `EXACT_UNCHANGED / MODIFIED / REMOVED / AMBIGUOUS / UNKNOWN`; route per whole Support |
| Support reading order | application code | correspondence + CatalogDiff + ReadingGroups + complete current manifest | ordered context list (first part: changed groups, removed ones as old text, and prior-Evidence groups) + coverage receipt |
| Change Impact | existing Structured LLM until a classifier backend passes #506 evaluation | fixed claims + one shared capacity-safe ChangeBundle | exactly one `AFFECTED / UNAFFECTED` per claim, or an execution failure that routes the claim to Support Assessment |
| Ordered semantic scan | Structured LLM | fixed claims + current AssessmentContext catalog + rule-governed historical excerpt + carried current witnesses | per step next witness state, or `SUPPORTED` (item exits) once the first part is read; after the last context `SUPPORTED / UNSUPPORTED` |
| Final validation and lifecycle reduction | application code | model proposal + complete manifest + allowed refs + current Support set + stale guards | `COMPLETED` or `UNRESOLVED`; guarded KEEP/REBIND/REMOVE proposal |

The classifier is used only for an independent closed-label question whose full
input is already supplied: “can this changed bundle affect this fixed claim?” It
does not search for or compose Evidence. The Structured LLM is used where several
current fragments may jointly support a claim and one Primary plus Required refs
must be selected as a coherent unit.

Routing is per whole Support, not per part. Any `UNKNOWN` part yields
`UNRESOLVED` and KEEP without a model call. Any `MODIFIED`, `REMOVED` or
`AMBIGUOUS` part enters Support Assessment. When every part is
`EXACT_UNCHANGED`, a revision without changed content rebinds directly without a
model call; a revision with changed content, removed content included, goes
through Change Impact, where
`UNAFFECTED` rebinds and `AFFECTED` or an execution failure enters Support
Assessment. A unique exact match is `EXACT_UNCHANGED` whether or not its
surrounding ReadingGroup changed.

`RevisionContextPlanner` is deterministic application code. It uses exact
Fragment correspondence, CatalogDiff, provider coverage and the current-revision
manifest to produce this conceptual plan:

```json
{
  "work_manifest": ["WRK-0001"],
  "reading_order": ["CTX-0001", "CTX-0002", "CTX-0003"],
  "provider_coverage": "COMPLETE",
  "current_ref_catalog": ["PRM-0001", "REQ-0002"]
}
```

Support Assessment follows one rule: stream the complete current content in a
fixed order. The first part holds every changed ReadingGroup (added, modified,
and removed ones as read-only old text) and the ReadingGroups that hold that
Claim's own prior Evidence; the rest follows. The first part is therefore per
Claim. An item cannot exit while any
ReadingGroup of the first part is unread. After the first part, each item exits
as soon as it has complete Support, and only an item that read the whole order
without Support is `UNSUPPORTED`. The planner only orders reading. It compares no costs, makes no
start decision and never asks a model whether a negative result is conclusive.
This requires that the full read streams per ReadingGroup and allows early exit.
`UNSUPPORTED` also requires authoritative coverage of every affected object:
when a Jira description was fetched completely but comment pagination is
partial, a Support whose Evidence is in the description may become
`UNSUPPORTED` after the whole order is read, while a Support whose Evidence is in
an unreturned comment is `UNKNOWN`.

Each non-final Structured-LLM scan call receives only semantic material:

```json
{
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
  "is_last_context": false
}
```

`historical_excerpt` is present exactly for `MODIFIED`, `REMOVED` and
`AMBIGUOUS`; it is absent for every other Evidence state. The application
rehydrates every carried current witness as `{ref, text, primary_eligible}` in
`carried_witness_catalog`; refs alone are not enough for the next call to reason
about their meaning. Digests, offsets, durable IDs, coverage proofs and
lifecycle history remain outside model input.

While the first part of the order is being read, a call returns only bounded current-revision witness additions for each item. From the call that completes the first part onward, a non-final call returns, for an item that has not yet exited, either `SUPPORTED(work_id, primary_ref, required_refs[])`, after which the item leaves later requests, or witness additions:

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

After the last context of the order, the only semantic results for an item
still in the lane are:

```text
SUPPORTED(work_id, primary_ref, required_refs[])
UNSUPPORTED(work_id)
```

A `SUPPORTED` result also lists the omitted matched prior refs: each exact-matched
prior part whose current ref is not in the final Primary/Required set. The list
carries refs only, no explanation.

The application wraps execution separately:

```text
COMPLETED(SUPPORTED | UNSUPPORTED)
UNRESOLVED(reason)
```

`UNRESOLVED` is the third, application-owned Support result, not a model label.
It has two reasons: `partial_coverage`, an `UNKNOWN` exact correspondence under
partial coverage (no model call), and `capacity`, a single ReadingGroup that
alone exceeds the model's capacity for the work item. It causes KEEP, blocks
automatic destructive action, does not advance the Support baseline, and commits
with the revision. A provider error, a timeout, or a schema or ID failure that
remains after the runner's splitting and the one correction is not
`UNRESOLVED`: the Source Unit revision is not committed and the next sync
retries it.

## 6. Current semantic-call inventory

The current `LiteLlmStructuredClient` mixes generation, classification and ranking. Target design migrates semantic responsibilities to the two executor interfaces rather than copying every historical wrapper.

| Responsibility | Shape | Batch shape | Target executor |
| --- | --- | --- | --- |
| Claim Extraction / managed patch | open-vocabulary claim or patch generation; on an update only the changed structures with their ReadingGroups as context, on a first import every ReadingGroup | independent items | Structured LLM `GenerationExecutor` |
| Complete Support Assessment | dependent status + Primary/Required + carried witnesses | ordered chain | Structured LLM `GenerationExecutor` |
| Change Impact | fixed claim vs shared ChangeBundle; `AFFECTED/UNAFFECTED` | independent items | existing Structured LLM until a classifier backend (Jev or small-parameter LLM) passes #506 evaluation |
| Sparse Relation (same Unit) | one row per admitted Candidate; only meaningful relations to same-Unit old Memories | independent items | Structured LLM; a pairwise classifier needs its own contract and evaluation |
| Cross-document relation | bounded retrieved `K` pairs; one closed label per pair: `none`, `equivalent`, `updates`, `contradicts` ([ADR 0037](../adr/0037-record-cross-document-conflicts-as-relations.md)) | independent items | classifier model (Jev or small-parameter LLM) with an evaluated per-label threshold; the existing Structured LLM returns the same labels until a backend passes evaluation on the labeled pair set |
| Candidate admission | complete evidence support per Candidate + same-round dedup against all of the round's Candidate claims | independent items with a cohort-level duplicate output | Structured LLM `GenerationWork`; deterministic normalization and duplicate merging remain code |
| Entity adjudication | select a supplied candidate or no match | independent items | classifier model (Jev or small-parameter LLM) |
| Retrieval rerank | comparable relevance score | one indivisible listwise item, never split | classifier model (Jev or small-parameter LLM) |
| Offline semantic judge / agent authority | fixed labels over complete supplied state | independent items | classifier model (Jev or small-parameter LLM) |
| Query entity detection | open-vocabulary extraction | independent items | Structured LLM unless code supplies a closed set |

Every row sends its requests through the LLM batch runner (section 4).

Exact Fragment correspondence, CatalogDiff, coverage, selector validation, manifests and lifecycle actions remain code. `EvidenceFragment`, `ReadingGroup`, `AssessmentContext` and `AssessmentScope` are distinct: a ReadingGroup may contain several selectable fragments; one AssessmentContext contains one or more groups for one call; the AssessmentScope is the complete effective current revision, read in order across all calls.

## 7. User-selectable execution profiles

Configuration separates generation from task-scoped classification:

```text
generation_executor = structured_llm
classifier_backend.change_impact = jev | small_llm
classifier_backend.cross_document_relation = jev | small_llm
```

There is no `jev_with_llm_fallback` profile and no per-item confidence routing. Each registered classifier task has one configured backend, pinned model and contract version. A backend is production-eligible for that task only after the task's fixed evaluation suite passes; otherwise the task remains on its previous whole-task implementation, which for Change Impact is the existing Structured LLM. Same-Unit Relation has no classifier profile: it stays sparse Structured-LLM work. Provider failure produces typed failed/unresolved work and ordinary retry, never silent substitution.

Complete Support Assessment is always compound `GenerationWork`. Users cannot route it through a classifier backend. Executor, model, contract, complete work manifest and ContextBundle digest participate in derivation identity; changing configuration does not reprocess unchanged Sources automatically.

## 8. Rollout and acceptance

Classifier backends begin with fixed, non-mutating evaluation cases. Acceptance is per task contract and model version, not per response confidence. Evaluation records exact label quality, especially `AFFECTED` recall; complete item coverage; unknown-ID and truncation rejection; input/output tokens; concurrency and latency; and lifecycle simulation proving that labels alone cannot perform REMOVE, SUPERSEDE or RETIRE.

Sparse Relation acceptance includes one row per admitted Candidate, rejection of missing rows, unknown IDs and truncation, the rule that omission means "no relation proposed", idempotent retries and identical results across legal partitions with a deterministic fixture client. Change Impact acceptance includes several changed groups combined into one bundle, multiple bundles OR-reduced by code, distant revocation/exception examples, a deleted distant qualifier, execution failure routing to Support Assessment, and source types represented by Markdown/Confluence, Jira and Teams. The global-scope rule has no dedicated cases; the generic #506 classifier evaluation applies. Complete Support Assessment is evaluated separately as Structured LLM generation/compound proposal work.

LLM batch runner acceptance includes multi-item requests that hit each capacity failure (timeout, input capacity, provider 413, truncated output) and complete after halving with exactly one result per item, a single-item failure returned as a typed failure with diagnostics, a single-Claim chain step that halves its ReadingGroups first, shared context chunked into per-item-and-chunk results, identical results across legal partitions and split points with a deterministic fixture client, rejection of missing, unknown and duplicate IDs, and a Support chain in which an item that finds Support in the first part leaves only after the first part is read.

## 9. Non-goals

- no universal provider interface that pretends generation and classification have identical capabilities;
- no per-item confidence fallback or hidden model substitution;
- no classifier-owned lifecycle action, authority, selector membership or work completeness;
- no correctness dependency on prompt-cache retention;
- no undocumented Jev cross-request cache assumption;
- no human confirmation stage for ordinary source lifecycle;
- no classifier-only claim generation, image understanding or compound Support Assessment;
- no semantic retrieval pruning of the same-Unit Relation catalog;
- no per-call-site capacity checks, request splitting or timeout handling outside the LLM batch runner;
- no per-task item or character caps besides limits a backend adapter declares;
- no output-budget or tokens-per-second configuration;
- no second lifecycle state machine or provider-specific domain branch.

## 10. Research basis

The parser survey, TypeSafe primitive/API review and provider cache evidence are
captured in
[Structure-preserving parsers, Jev judgments, and repeated-context caching](../research/2026-09-21-structure-parsers-jev-prompt-cache.md).
The concurrency and cache-visibility comparison supporting the minimal batch
dispatcher is captured in
[Prompt-cache-aware batch scheduling](../research/2026-09-21-prompt-cache-aware-batch-scheduling.md).
The research note is supporting evidence; this document and the corresponding
ADRs remain the normative product contract. Where the parser/Jev note conflicts
with this document or ADR 0036, for example on classifier confidence thresholds
or Jev for Support Assessment, this document and ADR 0036 apply.
