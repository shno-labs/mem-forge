# Semantic judgment execution and context reuse

Date: 2026-09-24. The LLM batch runner (section 4) is implemented and every
model call goes through it
([Cloud issue #505](https://github.com/dodoman-sun/memforge-cloud/issues/505)).
The rest of this document is a target design: it does not claim that
TypeSafe/Jev, provider prompt caching, the decision contract or the decision
model are implemented or deployed.
[Cloud issue #506](https://github.com/dodoman-sun/memforge-cloud/issues/506)
builds on the runner with the decision contract, the per-task decision-model
evaluation and prompt caching. The assignment of model steps to kinds, the
decision contract and the decision model are decided in
[ADR 0043](../adr/0043-assign-model-judgments-by-task-shape-and-share-one-decision-contract.md).

The complete Source lifecycle remains defined by
[Source sync to Memory](source-sync-to-memory.md). Exact Fragment and
ReadingGroup compilation remain governed by
[ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md), and
incremental Support and claim reconciliation remain governed by
[ADR 0034](../adr/0034-unify-incremental-support-and-claim-assessment.md).

## 1. Decision summary

MemForge separates application-owned semantic work from provider-specific
inference transport, and gives every model step one of three kinds, decided by
what the model must do rather than by the shape of its output:

```text
domain planner
  -> ContextBundle + task (Generation, Reasoning or Decision)
  -> model: the main model, or the decision model for a registered Decision task
     -> LLM batch runner (capacity, partitioning, per-row acceptance, one re-ask
        of rejected rows, split when the failing item cannot be named,
        concurrency, coverage, typed failures)
        -> LLM adapter (main model or decision model, through LiteLLM)
        -> Jev adapter (optional OSS adapter, Decision tasks only)
  -> application-owned validation and reducer
  -> existing Lifecycle Plan / retrieval / evaluation consumer
```

| Kind | The model must | Runs on |
| --- | --- | --- |
| Generation | write text that does not exist in the input | the main model |
| Reasoning | choose, but find the relevant items in a list the program cannot narrow, carry state or dependent answers across items, or decide whether several Evidence parts together entail a claim | the main model |
| Decision | answer one fixed question about one item the program supplied in full, with closed options, independently of every other item | the decision model once the task passes its evaluation, otherwise the main model |

Candidate admission and Support Assessment return only choices, yet they are
Reasoning: complete support over several Evidence parts is one entailment
judgment, and they share one definition of it (`COMPLETE_SUPPORT_DEFINITION`).
They therefore run on the same model, so a Candidate admitted under one reading
of complete support is not retired by a different reading at the next revision.
The step-by-step assignment is in section 6.

Model outputs are the knowledge or the choice, nothing else. A Generation
contract returns text only in the fields that are the generated knowledge (the
claim, its validity dates, entity names). A Reasoning or Decision contract
returns only values the program defined: labels, booleans, and refs or IDs from
lists the request supplied. No contract returns an explanation or a
model-reported confidence. Records that show a reason carry program-owned text;
people read the Memories and the Evidence.

Every Decision task implements one decision contract (section 5), whatever model
answers it. A task moves to the decision model as a whole, after it passes its
evaluation; a probability a backend reports is diagnostic telemetry, never
changes the answer and never switches an item to another model.

Every task sends its requests through one LLM batch runner (section 4). No
call site checks context capacity, splits requests or handles timeouts on its
own.

The model never owns Source authority, exact offsets, allowed selectors,
complete work coverage, lifecycle verbs, stale guards or atomic commit. Those
remain application facts and validators regardless of model.

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
TypeSafe questions or a serialized prompt. Adapters render it:

- the LLM adapter creates system/user content, response schema,
  images and provider cache breakpoints, for the main model and the decision
  model alike;
- the optional Jev adapter renders a Decision task as shared state plus one
  Choice/Noul/Score question per item and returns the same application-owned
  answers;
- tests can inspect the same canonical bundle without parsing either wire
  format.

The domain planner, not the adapter, decides which AssessmentScope, AssessmentContexts, ReadingGroups, fixed claims,
candidates, Evidence catalogs, historical excerpts and cumulative witnesses are
logically required. Switching model or adapter cannot silently widen or
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

**Status: implemented. Support Assessment uses the ordered-chain form. Cloud
issue #506 adds the decision contract, the decision-model evaluation and prompt
caching on top.**

Batching is a transport detail. Every path that sends work to a model, whether
Generation, Reasoning or Decision and whether on the main model or the decision
model, goes through one LLM batch runner. No call site handles input-context overflow or
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
3. Per-row acceptance. The model returns one row per item. The response model
   checks only the JSON shape of a row (types, required fields, enums); every
   rule about one row's meaning is a row rule that the task's decoder checks on
   that row alone, yielding either the item's result or a rejected row whose
   message names the item by the ID the model sees and states its exact error.
   The runner rejects an item with no row or with more than one row. A row that
   names an ID the request did not supply means the response's IDs cannot be
   trusted to match their rows (an answer may sit under its neighbour's ID), so
   the whole response is treated as unreadable (step 5). Valid rows are accepted
   at once and never sent again. Candidate admission, Change Impact, Support
   Assessment, Sparse Relation (`claim_revision`), the refinement comparison,
   cross-document relation, entity resolution and agent-session authority work
   this way. Claim Extraction has no per-item rows, because one response serves
   all ReadingGroups of the request: a response that cannot be read is split down
   to single ReadingGroups, and a ReadingGroup still unreadable alone is skipped;
   an invalid selector gets one correction and then only that claim is dropped.
4. One re-ask. The rejected items are re-asked once, together, in one request
   that holds only them and lists each item's error, packed by capacity when
   they do not fit one request. In the chain form a re-asked item reads the same
   step, from the same position, with its unchanged carried state, and rejoins
   its lane when accepted. An item still rejected after its re-ask is an
   `invalid_response` failure. A request with k rejected rows costs one extra
   call, whatever k and the request size.
5. Splitting only where the failing item cannot be named. A request holding
   several items that ends in `deadline_exceeded`, `input_capacity_exceeded`, a
   provider 413 `payload_too_large` or truncated output (`finish_reason=length`)
   is a capacity failure: the runner splits it into two halves and resends each
   half until they complete. Truncated output is not resent as JSON text at the
   same `max_tokens`. A response that cannot be read into rows at all (malformed
   or ambiguous JSON, or a schema failure) first gets one correction of the whole
   request; the client repairs a schema failure once itself. If it still cannot
   be read, the request is split the same way. In the chain form a cohort splits
   into two lanes that continue from the same position with their own state; a
   step holding a single Claim that spans several ReadingGroups first halves its
   ReadingGroups on a capacity failure.
6. Typed per-item failures. An item that still fails returns a typed
   `ItemFailure` with diagnostics. Its category says whether the item alone
   exceeds the route's input capacity (`capacity_exceeded`: from the capacity
   fit, `input_capacity_exceeded` or a provider 413), a model response for it was
   received and still fails validation after its re-ask or correction
   (`invalid_response`, malformed or ambiguous JSON included), the failure is
   transient (`deadline_exceeded` or `provider_error`), or the request failed
   without a response to validate (`request_error`: a provider rejection such as
   400, or an unexpected exception). Only the first two make the item
   unjudgeable in isolation; they are defined positively, and every other
   error, a code defect included, is not. The runner never turns a failure into
   a label, never substitutes another model and never retries on a different
   backend.
7. Bounded concurrency through the existing collector and Structured LLM
   semaphore, and a journal: a response that reads into rows is journaled even
   when some rows are rejected, and each re-ask is its own journaled request, so
   a retried run reuses accepted rows and re-asks without a call.

**What the caller decides**

One rule governs every Source Unit task: an item that stays unjudgeable in
isolation (capacity or invalid output) is recorded by its task, and the revision
commits; every other failure leaves the Source Unit revision uncommitted and the
next sync retries it. One item the model cannot judge never blocks the rest of
its Unit. The business meaning of an `ItemFailure` belongs to the task:

| Task | Item unjudgeable in isolation (capacity or invalid output) | Any other failure |
| --- | --- | --- |
| Support Assessment and its targeted re-check | `UNRESOLVED(capacity)` or `UNRESOLVED(invalid_response)`, KEEP, the Support baseline does not advance, and the diagnostic names the Source Unit and the ReadingGroup | the Source Unit revision is not committed and the next sync retries it |
| Change Impact | the Claim enters Support Assessment; no `AFFECTED` label is recorded | the same |
| Candidate admission | the Candidate is `REJECTED` for this round with reason `capacity_exceeded` or `invalid_response`, recorded like any rejection; no ADD | the Source Unit revision is not committed and the next sync retries it |
| Sparse Relation | the Candidate is consumed without ADD and without a Review, with a diagnostic; never read as "no relation proposed". The Relation line is incomplete, so no DELETE, SUPERSEDE or UPDATE of the Unit is executed this round | the Source Unit revision is not committed and the next sync retries it |
| Claim Extraction | the ReadingGroup is skipped with a diagnostic naming the Source Unit, the ReadingGroup and the reason (`input_capacity_exceeded` or `invalid_response`); the other groups are extracted | the existing extraction failure for that Source Unit, with no partial candidates |
| Rerank | baseline order, also on timeout or invalid output; a fixed code rule, not configuration | the same |

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

## 5. Decision-model execution

A Decision task answers one fixed question about one item the program supplied
in full, with closed options, independently of every other item. Every Decision
task implements one decision contract, whatever model answers it:

- **Task.** A task has a name, a contract version that is part of its work
  identity, one fixed question and a closed list of options. One option is the
  task's safe answer, which is also the answer for an uncertain case.
- **Item.** One item is the complete input the program supplies for one
  question. Items are independent. When an item's input is too large for one
  request and the task allows it, the program splits the input and combines the
  answers by the task's rule.
- **Answer.** Exactly one option per item, nothing else: no explanation and no
  confidence. An ID outside the supplied candidates is a rejected row, not the
  safe answer.
- **Meaning.** What each option means and what the program does with it belong
  to the task. Relation direction (`updates` needs known Evidence dates that
  order the pair) stays a program rule
  ([ADR 0037](../adr/0037-record-cross-document-conflicts-as-relations.md)).
- **Execution.** Requests go through the LLM batch runner. How items are packed
  is the adapter's concern: the LLM adapter asks for many items per request; the
  Jev adapter sends one state with one question per item. A probability a
  backend reports is diagnostic telemetry and offline calibration data; it never
  changes the answer.
- **Failure.** An item without a valid answer after the runner's re-ask is an
  execution failure that the task routes as section 4 describes. A failure is
  never an option, not even the safe answer.

| Task | Question | Options | Safe answer | Split and combine |
| --- | --- | --- | --- | --- |
| Change Impact | can this ChangeBundle affect this fixed claim | `AFFECTED`, `UNAFFECTED` | `AFFECTED`: it sends the claim to Support Assessment | ChangeBundles chunked at ReadingGroup boundaries; any `AFFECTED` wins |
| Same-Unit pair review | do these two refinements of the same old Memory contradict | a memory relation label; only `contradicts` is acted on | `contradicts`: it blocks the refinement | not split |
| Cross-document relation | how do these two Memories from different Source Units relate | `none`, `equivalent`, `updates`, `contradicts` | `none` | not split |
| Entity adjudication | which supplied candidate, if any, is this mention | one supplied candidate ID, or no candidate | no candidate | not split |
| Agent-session authority | which authority kind does this user message carry, read in its window | the closed list of authority kinds | `not_authoritative` | not split |

The Source-lifecycle contracts of the Support and Relation lines are:

```text
ChangeImpact (Decision, safe answer AFFECTED)
  fixed claim + capacity-safe ChangeBundle
  (added and modified ReadingGroups, plus the old text of removed ones)
  -> AFFECTED | UNAFFECTED

PairReview (Decision, safe answer contradicts)
  two supported refinements of the same old Memory
  -> one memory relation label; contradicts blocks the refinement

SparseRelation (Reasoning, main model)
  admitted Candidates + each Candidate's current Evidence
  + Claims of all Active same-Unit old Memories
  -> one row per Candidate listing only meaningful relations, and for a
     refinement its entailment booleans (`revision_assessment`)

CandidateAdmission (Reasoning, main model)
  items: Candidates of one revision + their selected Primary/Required Evidence
  shared context: every Candidate claim of the revision (ID + claim text only)
  -> ADMITTED | REJECTED(reject reason) per Candidate, plus reported same-round duplicates
```

Change Impact runs on the main model until it passes its decision evaluation
and is registered (section 7). Its safe answer is `AFFECTED`, because
`UNAFFECTED` rebinds the claim without Support Assessment while `AFFECTED` sends
it there; an uncertain case is therefore `AFFECTED`. Its instruction includes
one fixed rule: a change containing a global statement with unclear scope, such
as "the process above", "this document" or "discontinued from a given date", is
`AFFECTED`. The rule has no dedicated evaluation cases; the Change Impact
decision evaluation applies.

Candidate admission is Reasoning and always runs on the main model, the same
model as Support Assessment: it judges complete support over the selected
Evidence parts with the same definition (`COMPLETE_SUPPORT_DEFINITION`), and it
finds same-round duplicates by scanning every Candidate of the round. Its row
holds the verdict, a program-defined reject reason and a reported duplicate,
and no text. `REJECTED` has two reasons: `evidence_incomplete`, when the
selected Evidence does not completely support the Claim, including identifying
details such as a name or key that the Claim states, or `low_value`. Every
admission request carries all of this round's Candidate claims as shared
context, so the model can report a duplicate that sits in another request.
Candidates with the same normalized claim, type and validity are duplicates
without the model saying so, but each is judged on its own Evidence. The program
merges duplicates deterministically, only among admitted Candidates, and keeps
the most specific Candidate of each group; a Candidate rejected in any context
chunk is rejected.

Sparse Relation is Reasoning and always runs on the main model: it finds the few
related old Memories among all of the Unit's, which similarity cannot narrow
inside one document, and a refinement is decided by entailment. It never
receives Support results and does not check whether Evidence supports the
Candidate; candidate admission owns that check. Omitting an old Memory means
"no relation proposed". A row returns only relation labels, old Memory IDs and
the refinement booleans, with no explanation and no written proof of a
contradiction. A pending Review and a replaced Memory show the Memories, the
label, the Evidence and program-owned reason text. A pairwise form that returns
one label per Candidate/old Memory pair would be a separate task that needs its
own contract and evaluation before it could replace the sparse contract.

The pair review runs when two or more supported Candidates refine the same old
Memory. The program supplies each pair of those refinements in full, so the
question is a Decision. `contradicts`, the safe answer, turns the refinement
uncertain and blocks the UPDATE; any other label lets it proceed. Its contract
version is part of its work identity.

Cloud impact: every task runs on the main model that Cloud reaches through
LiteLLM `sap/` routes and `AICORE_*` environment variables. The decision model
is one deployment variable next to `MEMFORGE_AICORE_ENRICHMENT_MODEL`, empty by
default and needing no database row. Nothing runs on a second model until a
task passes evaluation on Cloud's own labeled cases and the variable is set.
Cloud's decision model is a small model on a `sap/` route, for example Claude
Haiku 4.5 once SAP AI Core offers it; Cloud does not send Source content to Jev.

ChangeBundles contain all changed ReadingGroups that fit one shared state. Removed content counts as changed: a removed ReadingGroup enters the bundle as its old text, so a distant qualifier that was deleted is visible to Change Impact. Three groups plus 300 fixed claims therefore produce 300 questions, not 900. If they do not fit one request, the runner chunks them at ReadingGroup boundaries into several bundles and application code OR-reduces each claim's labels: any `AFFECTED` routes that claim to complete Support Assessment. When Change Impact execution fails for a claim, for example a single item that still fails after the runner's splitting, an indivisible bundle beyond the model's capacity, or a bundle with images that a text-only adapter cannot read, that claim enters Support Assessment. The failure is never recorded as an `AFFECTED` label.

Sparse Relation sends every admitted Candidate to the model, including one whose text equals an old Memory. Catalog bodies occur once per request; the LLM batch runner packs and splits requests, and when the old Memory catalog must be chunked the program takes the union of each Candidate's relations. Every admitted Candidate must return exactly one row. A missing row, an unknown ID or a duplicate or contradictory relation is rejected, and truncated output is a capacity failure that the runner splits; none of them is read as "no relation proposed". Each Candidate's row is validated on its own, and the rejected rows are re-asked once, together, naming each Candidate's error. A Candidate whose row is still rejected after its re-ask is consumed without ADD and without a Review. Its row would cover it against every old Memory of the Unit, so the gap cannot be localized: while any row is missing, DestructiveValidation withholds every DELETE, SUPERSEDE and UPDATE of the Unit, and the non-destructive work of the revision commits. Any other failure leaves the Source Unit revision uncommitted, and the next sync retries it. Partitioning cannot weaken coverage, introduce lifecycle state or publish partial results. Whole-workspace relation discovery remains retrieve-then-classify over bounded `K` because its Cartesian product is unbounded and non-destructive discovery accepts recall loss.

TypeSafe/Jev is an optional OSS adapter behind the same decision contract. It evaluates independent Choice, Noul or Score questions over shared text state and returns the same one-option-per-item answers as the LLM adapter. Jev's current 64k request limit, text-only input and Choice option limit are adapter capabilities, not domain semantics. Jev has no documented cross-request prompt cache; its efficiency comes from many questions sharing one state. See [Models](https://docs.typesafe.ai/models), [System One](https://docs.typesafe.ai/concepts/system-one.md) and [Parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions.md).

Complete Support Assessment is Reasoning, even though its final semantic result is a small union. One Primary, zero or more Required refs, opposing witnesses and streamed previous state form one dependent Evidence-plan proposal read in order with carried witnesses. Splitting them into independent Decision questions would recreate a second Support engine in application code.

Missing answers, unknown IDs, incomplete manifests, unsupported modality, capacity failure or provider failure are technical work failures. The LLM batch runner accepts every valid row, re-asks the rejected rows once and splits a multi-item request only on a capacity failure or output it cannot read into rows; only a failure that remains for a single item is reported. Failures never become labels and do not trigger a fallback to another model. Retry uses the same model and exact work identity; moving a task to the decision model is an explicit registration and configuration change (section 7).

### Support planning and execution contract

The boundary is task-shaped rather than confidence-shaped:

| Step | Owner | Input | Output |
| --- | --- | --- | --- |
| Exact Evidence correspondence | application code | prior Evidence metadata + current Fragment catalog + provider coverage | per part `EXACT_UNCHANGED / MODIFIED / REMOVED / AMBIGUOUS / UNKNOWN`; route per whole Support |
| Support reading order | application code | correspondence + CatalogDiff + ReadingGroups + complete current manifest | ordered context list (first part: changed groups, removed ones as old text, and prior-Evidence groups) + coverage receipt |
| Change Impact (Decision) | the decision model once the task passes its evaluation, otherwise the main model | fixed claims + one shared capacity-safe ChangeBundle | exactly one `AFFECTED / UNAFFECTED` per claim, or an execution failure that routes the claim to Support Assessment |
| Ordered semantic scan (Reasoning) | the main model | fixed claims + current AssessmentContext catalog + rule-governed historical excerpt + carried current witnesses | per step next witness state, or `SUPPORTED` (item exits) once the first part is read; after the last context `SUPPORTED / UNSUPPORTED` |
| Final validation and lifecycle reduction | application code | model proposal + complete manifest + allowed refs + current Support set + stale guards | `COMPLETED` or `UNRESOLVED`; guarded KEEP/REBIND/REMOVE proposal |

The decision model answers only an independent closed question whose full
input is already supplied: “can this changed bundle affect this fixed claim?” It
does not search for or compose Evidence. The main model is used where several
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

The exactly matched prior parts are offered as selectable current refs. The
complete support definition judges whether the selected set is complete; no
field accounts for prior parts the selection leaves out.

The application wraps execution separately:

```text
COMPLETED(SUPPORTED | UNSUPPORTED)
UNRESOLVED(reason)
```

`UNRESOLVED` is the third, application-owned Support result, not a model label.
It has three reasons: `partial_coverage`, an `UNKNOWN` exact correspondence under
partial coverage (no model call); `capacity`, a single ReadingGroup that alone
exceeds the model's capacity for the work item; and `invalid_response`, output
for the work item alone that stays invalid after the one correction. It causes
KEEP, blocks automatic destructive action, does not advance the Support
baseline, and commits with the revision. A provider error or a timeout that
remains after the runner's splitting is not `UNRESOLVED`: the Source Unit
revision is not committed and the next sync retries it.

## 6. Current semantic-call inventory

The current `LiteLlmStructuredClient` serves every model step through one interface. The target design gives each step one kind (section 1), and the kind decides which model may run it.

| Responsibility | Kind | Shape | Batch shape | Runs on |
| --- | --- | --- | --- | --- |
| Claim Extraction (with selector correction) | Generation | writes the claim, its validity dates and entity names; on an update only the changed structures with their ReadingGroups as context, on a first import every ReadingGroup; each request reads its items with their reading context and the Unit Title | independent items, one per ReadingGroup that holds authorized Primary | main model |
| Managed agent patch | Generation | writes the replacement claim for one agent-session window | one item per window | main model |
| Candidate admission | Reasoning | complete support over the selected Evidence parts per Candidate + same-round dedup against all of the round's Candidate claims | independent items with a cohort-level duplicate output | main model, the same as Support Assessment; deterministic normalization and duplicate merging remain code |
| Complete Support Assessment | Reasoning | ordered reading with carried witnesses; Primary and Required are one dependent choice | ordered chain | main model |
| Sparse Relation (same Unit) | Reasoning | one row per admitted Candidate; only meaningful relations to same-Unit old Memories, found among all of the Unit's; refinement decided by entailment | independent items | main model |
| Same-Unit pair review | Decision, safe answer `contradicts` | two supported refinements of the same old Memory; one memory relation label per pair | independent items | decision model once the task passes its evaluation, otherwise main model |
| Change Impact | Decision, safe answer `AFFECTED` | one fixed claim vs one shared ChangeBundle; `AFFECTED/UNAFFECTED` | independent items; chunked bundles OR-reduced by code | decision model once the task passes its evaluation, otherwise main model |
| Cross-document relation | Decision, safe answer `none` | bounded retrieved `K` pairs; one closed label per pair: `none`, `equivalent`, `updates`, `contradicts` ([ADR 0037](../adr/0037-record-cross-document-conflicts-as-relations.md)); the classifier returns only the label and has no per-label confidence threshold | independent items | decision model once the task passes its evaluation on the labeled pair set, otherwise main model; contract version `cross-document-relation-v3` |
| Entity adjudication | Decision, safe answer no candidate | one mention and its supplied candidates; pick one or none | independent items | decision model once the task passes its evaluation, otherwise main model |
| Agent-session authority | Decision, safe answer `not_authoritative` | one user message with its window as context; one `authority_kind` | independent items | decision model once the task passes its evaluation, otherwise main model |

Every row sends its requests through the LLM batch runner (section 4).

Two model calls are outside this assignment. Retrieval rerank is a ranking task for a dedicated reranker; it stays disabled by default, Cloud does not use it, and [Query-time Memory reranking](query-time-memory-reranking.md) owns its contract. The offline semantic judge is evaluation tooling, not a product step, and uses the model its evaluation spec names.

Exact Fragment correspondence, CatalogDiff, coverage, selector validation, manifests and lifecycle actions remain code. `EvidenceFragment`, `ReadingGroup`, `AssessmentContext` and `AssessmentScope` are distinct: a ReadingGroup may contain several selectable fragments; one AssessmentContext contains one or more groups for one call; the AssessmentScope is the complete effective current revision, read in order across all calls.

## 7. Model settings and task registration

There are two model settings:

```text
main model       every Generation and Reasoning task, and every Decision task
                 that is not registered
decision model   one setting, empty by default, applied to every registered
                 Decision task
```

A Decision task moves to the decision model only after it passes its evaluation
(section 8). The passed tasks are registered in code with their contract
versions; a new contract version is not registered until it passes on its own.
When the decision model is not set, every task runs on the main model. There is
no per-task backend setting, no per-item routing, no `jev_with_llm_fallback`
profile and no fallback between models. Provider failure produces typed
failed or unresolved work and ordinary retry, never substitution.

Generation and Reasoning tasks always run on the main model; no setting routes
Claim Extraction, candidate admission, Support Assessment or Sparse Relation
elsewhere. Model, contract version, complete work manifest and ContextBundle
digest participate in work identity. Changing the decision model or a
registration does not reprocess unchanged Sources automatically: derivations use
the new version at their next processing, and existing cross-document relations
are re-run by an operator.

Cloud impact: the decision model is one deployment variable next to
`MEMFORGE_AICORE_ENRICHMENT_MODEL`, read by `prepare-deploy.sh` and the
`sap-internal` profile, exported by `cf_env_aicore.py` and passed through
`proxy/external_runtime.py`. It is empty by default and needs no database row,
so it works with Cloud's environment-only configuration and
`llm_config_writable = false`. The `sap/` transport choice applies to it as it
does to the main model. It is the one configuration addition beyond LiteLLM
metadata, `MEMFORGE_LLM_MAX_*` and `request_timeout_s`.

## 8. Rollout and acceptance

A Decision task is evaluated on held-out labeled cases before it is registered.
It passes when, against the main model on the same cases, its safe-answer recall
and its precision on every other option are no lower. For Change Impact that is
`AFFECTED` recall and `UNAFFECTED` precision.
Acceptance is per task contract version and model, not per response confidence.
Evaluation also records complete item coverage; unknown-ID and truncation
rejection; input/output tokens; concurrency and latency; and lifecycle simulation
proving that labels alone cannot perform REMOVE, SUPERSEDE or RETIRE.

A contract change that alters behaviour on any model needs its own evaluation
before it ships, whether or not the task moves to the decision model. Removing
entity adjudication's confidence cutoff turns every returned candidate into a
persistent alias, and removing Sparse Relation's explanation removes text the
model wrote before its refinement booleans; both are compared with the previous
contract on labeled cases before the new version replaces it.

Sparse Relation acceptance includes one row per admitted Candidate, rejection of missing rows, unknown IDs and truncation, a Candidate whose row stays invalid alone left unresolved while the revision commits, the rule that omission means "no relation proposed", idempotent retries and identical results across legal partitions with a deterministic fixture client. Change Impact acceptance includes several changed groups combined into one bundle, multiple bundles OR-reduced by code, distant revocation/exception examples, a deleted distant qualifier, execution failure routing to Support Assessment, and source types represented by Markdown/Confluence, Jira and Teams. The global-scope rule has no dedicated cases; the Change Impact decision evaluation applies. Complete Support Assessment and candidate admission are evaluated separately as Reasoning work on the main model.

LLM batch runner acceptance includes multi-item requests that hit each capacity failure (timeout, input capacity, provider 413, truncated output) and complete after halving with exactly one result per item, valid rows accepted once and never resent, rejected or missing rows re-asked once together with each item's error (item and chain form, the chain re-ask reading the same step and state), a 53-item request with two rejected rows completing in two calls and one with a persistently rejected row ending in two calls with one unjudgeable item, output that cannot be read into rows corrected once and then split (malformed output included), a retried run reusing accepted rows and re-asks without a call, a single-item failure returned as a typed failure with diagnostics, a single-Claim chain step that halves its ReadingGroups first, shared context chunked into per-item-and-chunk results, identical results across legal partitions and split points with a deterministic fixture client, rejection of missing and duplicate rows, a row for an unrequested ID voiding the whole response (an answer shifted onto its neighbour's ID is never accepted), one semantically invalid row costing one re-ask through the real client parse path, and a Support chain in which an item that finds Support in the first part leaves only after the first part is read.

## 9. Non-goals

- no universal provider interface that pretends every model and adapter has identical capabilities;
- no per-item confidence fallback or hidden model substitution;
- no per-task backend setting, per-item routing or fallback between the main model and the decision model;
- no model-written explanation or model-reported confidence in any Generation, Reasoning or Decision contract, and no per-label confidence threshold;
- no model-owned lifecycle action, authority, selector membership or work completeness;
- no correctness dependency on prompt-cache retention;
- no undocumented Jev cross-request cache assumption;
- no human confirmation stage for ordinary source lifecycle;
- no Generation or Reasoning task on the decision model, and no image understanding by a text-only adapter;
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
with this document, ADR 0036 or ADR 0043, for example on confidence thresholds,
Jev for Support Assessment or Jev on Cloud, this document and those ADRs apply.
