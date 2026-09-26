# Unify incremental Support and claim assessment within the existing lifecycle

## Status

Accepted. The original unified assessment contract was implemented on
2026-09-06. The sections labelled "target" are the accepted shared contract
tracked by
[Cloud issue #505](https://github.com/dodoman-sun/memforge-cloud/issues/505),
whose first step delivers the LLM batch runner of
[ADR 0036](0036-separate-semantic-work-from-inference-executors.md) and moves
the existing model call sites onto it; the Support reading order, extraction
scope, Relation, Support and Relation coordination, candidate admission and
lifecycle consequences follow on that runner. Classifier backends, their
evaluation and cache-aware context are tracked by
[Cloud issue #506](https://github.com/dodoman-sun/memforge-cloud/issues/506).
Release and deployment evidence remains external to this ADR, and a source
change alone does not prove a deployed Cloud runtime.

Current implemented contract: Support Assessment uses exact correspondence,
Change Impact and the [ordered read](#ordered-current-revision-reading) with
cumulative witnesses. Claim Extraction reads as described in
[Unified revision input planning](#unified-revision-input-planning-and-bounded-execution)
under `revision-input-v7`: changed structures with their ReadingGroups on an
update, every ReadingGroup on a first import, one runner item per ReadingGroup,
with no cost comparison and no truncation. Every reading carries the Unit Title
([One deep context-planning module](#one-deep-context-planning-module)).
[Candidate admission](#candidate-admission) is implemented as
`candidate-admission-v2`, and the [Sparse same-Unit Relation](#sparse-same-unit-relation)
request is implemented as `claim-revision-v8-sparse-catalog`, described in
[Sparse claim catalog](../design/sparse-claim-catalog.md). Relation runs
concurrently with Support Assessment over every same-Unit old Memory, and
[Support and Relation coordination](#support-and-relation-coordination) with its
[Pending coordinator Review](#pending-coordinator-review) joins the two lines. The
[Same-Unit identity backstop](#same-unit-identity-backstop),
[Automated destructive validation](#automated-destructive-validation) and the
commit order of a [Source Unit identity](#source-unit-identity-and-convergence)
change are implemented. With them every section labelled "target" is
implemented in OSS. Cloud implements the HANA side with its pin upgrade, and the
read-only shadow cohort and deployment evidence that Cloud issue #505 requires
are recorded outside this ADR.

Amended 2026-09-26 by [ADR 0039](0039-create-memories-within-the-source-unit.md): the
[Same-Unit identity backstop](#same-unit-identity-backstop) and pre-creation
identity reuse are removed. Every admitted ADD Candidate creates its own Memory;
same-Unit duplicates are decided by candidate admission and Sparse Relation, and
sameness across Source Units is an asynchronous `equivalent` relation. The
statements about identity below describe the removed step.

## Context

The preceding reconciliation classified claim pairs, audits incumbent support, and
conditionally makes a separate revision-composition call. The subsequent NOOP
path independently selects and validates current Evidence. Repeating support
judgments and limiting current candidates through old-location correspondence
can lose valid rewritten or split Evidence. Full-document context also needs to
remain distinct from authority to extract new claims.

The end-to-end explanation and implementation comparison live in
[Source sync to Memory](../design/source-sync-to-memory.md). This ADR records
only the decision; it does not replace the representation compiler, storage
protocol, or the complete lifecycle description.

## Target contract (tracked by Cloud issue #505)

This section is the target contract for context planning, Support assessment and
relationship discovery. Incremental Support assessment does not repeatedly
transport all prior Support text, cumulative state is not reduced to the latest
status, current-full extraction may span several model requests, and
relationship discovery does not need one explicit result per
candidate/incumbent pair. The contract adds no lifecycle state, semantic
Evidence search, human confirmation step, separate candidate-to-candidate
deduplication pass, or cross-Source-Unit destructive rebind.

### Classifier and Support contract

A **classifier model** is an executor role implemented by TypeSafe/Jev or a small-parameter LLM. Eligibility is decided for a complete task contract from a fixed evaluation set; runtime confidence is telemetry, not a per-item route to another model.

Cross-document discovery retains bounded retrieval followed by classification over `K` pairs.

Exact prior Evidence is classified as `EXACT_UNCHANGED`, `MODIFIED`, `REMOVED`, `AMBIGUOUS` or `UNKNOWN`. Old exact excerpt is supplied only for `MODIFIED`, `REMOVED` and `AMBIGUOUS`; `UNKNOWN` is application-owned `UNRESOLVED(partial_coverage)` and KEEP with no model call. When every part of a Support is `EXACT_UNCHANGED` and the revision has changed content, the Change Impact judgment checks the claim against capacity-safe ChangeBundles and returns `AFFECTED` or `UNAFFECTED`; affected claims, claims whose Change Impact execution failed, and Supports with directly changed Evidence enter complete Structured-LLM Support Assessment.

`AssessmentScope` is the complete effective current revision. `AssessmentContext` is one call's one-or-more ReadingGroups. A ReadingGroup may contain several selectable EvidenceFragments. Support Assessment reads the scope in one fixed order with per-work-item early exit after the first part ([Ordered current-revision reading](#ordered-current-revision-reading)). The semantic result is `SUPPORTED(primary_ref, required_refs[]) | UNSUPPORTED`, and `UNSUPPORTED` exists only after the whole order has been read. Partial coverage, a single ReadingGroup beyond the model's capacity and output that stays invalid for the work item alone are separately `UNRESOLVED(partial_coverage)`, `UNRESOLVED(capacity)` and `UNRESOLVED(invalid_response)`, which keep the Support; an execution error leaves the Source Unit revision uncommitted. `REBIND_SUPPORT` atomically attaches target-Revision Support and marks the replaced assertion inactive without altering Memory identity or rewriting historical rows.

### Target contract overview

Target contract, tracked by Cloud issue #505. Each item points to the section
that owns the detail.

- Support reads the complete current revision in one fixed order. The first
  part is per Claim: every changed ReadingGroup (added, modified and removed)
  and the ReadingGroups that contain that Claim's own old Evidence; a Claim
  cannot exit while any of them is unread. After the first part, a Claim exits
  as soon as it has complete Support. Delta names only the first part of that
  order; it is not a mode, and there is no Delta/Full cost comparison or start
  decision
  ([Ordered current-revision reading](#ordered-current-revision-reading)).
- The exact status set has no container state: a unique exact match is
  `EXACT_UNCHANGED` whether or not its surrounding ReadingGroup changed, and
  routing is decided for the whole Support, not per part
  ([Exact current Evidence correspondence](#exact-current-evidence-correspondence)).
- Support has a third, application-owned result `UNRESOLVED` with three reasons:
  `partial_coverage` (an `UNKNOWN` part under partial projection, with no model
  call), `capacity` (one ReadingGroup that alone exceeds the model's capacity
  for the Claim) and `invalid_response` (the model's output for the Claim alone
  stays invalid after the one correction, for example a schema, ID or selection
  failure). All three keep the Support unchanged, and the revision commits.
  `UNKNOWN` takes priority: a Support with any `UNKNOWN` part is `UNRESOLVED`
  with no model call. A Support Assessment or targeted re-check request that
  ends in an execution error (a provider error, a timeout, a rejected request or
  an unexpected exception) after the LLM
  batch runner split it down to one work item and one ReadingGroup is not
  `UNRESOLVED`: the Source Unit revision is not committed and the next sync
  retries it.
- Change Impact runs on the existing Structured LLM until a classifier backend
  passes the #506 evaluation for that task. Its ChangeBundles carry the old text
  of removed ReadingGroups as removed content, so a deleted distant qualifier is
  visible to it. Its execution failure sends the claim to Support Assessment and
  is never recorded as an `AFFECTED` label. A change that contains a global
  statement with unclear scope is `AFFECTED`.
- On an update, Claim Extraction reads only the changed structures, with their
  ReadingGroups as context; a first import streams per ReadingGroup. Extraction
  makes no Delta/current-full cost comparison
  ([Unified revision input planning](#unified-revision-input-planning-and-bounded-execution)).
  Implemented as `revision-input-v7`.
- Every Source adapter supplies the Unit Title, the Unit's human-facing name, as
  the Unit's first Observation. It is never Primary, can be selected as Required,
  and is read with every model reading of the Unit
  ([One deep context-planning module](#one-deep-context-planning-module)).
- Candidate admission is an independent step between Claim Extraction and
  Relation. Low-value Candidates are `REJECTED` with reason `low_value`, and
  every admission request carries the round's Candidate claims so duplicates are
  found across requests ([Candidate admission](#candidate-admission)).
- Same-Unit Relation stays sparse: one completion row per admitted Candidate,
  listing only meaningful relations to same-Unit old Memories. A pairwise
  classifier backend for this task would be a separate contract with its own
  evaluation. Relation input excludes Support results, so Support Assessment and
  Relation run in parallel ([Sparse same-Unit Relation](#sparse-same-unit-relation)).
- An execution error in candidate admission or Relation leaves the
  Source Unit revision uncommitted, and the next sync retries it, with no
  partial publish. A Candidate that stays unjudgeable in isolation is recorded
  instead: candidate admission rejects it for this round. In Relation the
  Candidate is consumed without ADD, and because its row would cover every old
  Memory of the Unit, the Relation line is incomplete: no DELETE, SUPERSEDE or
  UPDATE of the Unit is executed this round.
- `SupportRelationCoordinator` combines both results by one fixed table, with at
  most one targeted re-check per Claim per revision
  ([Support and Relation coordination](#support-and-relation-coordination)).
  `UNRESOLVED(partial_coverage)` takes part in the table like any other result;
  only a Claim that could not be judged, `UNRESOLVED(capacity)` or
  `UNRESOLVED(invalid_response)`, keeps the Memory and consumes its related
  Candidates without a decision.
  A coordinator Review is the Lifecycle Plan's existing `CREATE_REVIEW`
  record in `lifecycle_reviews`, with the Candidate in its staged evidence and a
  deterministic ID, so one conflict has exactly one Review
  ([Pending coordinator Review](#pending-coordinator-review)).
- Amended by [ADR 0039](0039-create-memories-within-the-source-unit.md): every admitted ADD Candidate creates its own Memory,
  and no identity step follows the coordinator. The next statement describes the
  removed step.
  Identity deduplication covers this Unit's kept old Memories and excludes those
  this round deletes, supersedes, updates or sends to Review
  ([Same-Unit identity backstop](#same-unit-identity-backstop)).
- DestructiveValidation also requires complete Relation work for any SUPERSEDE
  or UPDATE ([Automated destructive validation](#automated-destructive-validation)).
- When a Source Unit's identity changes, the new Unit's creation and identity
  attach commit before the old Unit is removed
  ([Source Unit identity and convergence](#source-unit-identity-and-convergence)).
  Amended by [ADR 0039](0039-create-memories-within-the-source-unit.md): there is no identity attach; the new Unit creates its
  own Memories and still commits before the old Unit is removed.
- A RepresentationCompiler change to segmentation or text representation is
  absorbed by ordinary Support Assessment; a Unit that no longer changes is
  reprocessed at its current revision by an operator
  ([Validation and version boundaries](#validation-and-version-boundaries)).
- Every model call goes through the LLM batch runner of
  [ADR 0036](0036-separate-semantic-work-from-inference-executors.md) (decision
  13). Response models check only the JSON shape of a row, and each task checks
  every row's meaning on that row alone: valid rows are accepted at once, and
  the rejected rows are re-asked once, together, naming each item's error. A row
  that names an ID the request did not supply voids the whole response. A
  request with several work items that fails for capacity, or whose output
  cannot be read into rows even after one correction, is split in half and
  resent; a Support chain step for a single Claim over several ReadingGroups
  halves its ReadingGroups first on a capacity failure. An item that still
  fails is a typed failure that each task maps to its own
  outcome, by one rule: an execution error (a provider error, a timeout, a
  rejected request or an unexpected exception) leaves the Source Unit revision
  uncommitted, and an item that stays
  unjudgeable in isolation (capacity or invalid output) is recorded by its stage
  and the revision commits. Support records `UNRESOLVED(capacity)` or
  `UNRESOLVED(invalid_response)` and KEEP. Change Impact sends the claim to
  Support Assessment. Candidate admission rejects the Candidate for this round.
  Relation consumes the Candidate without ADD and withholds every destructive
  action of the Unit this round. Claim Extraction skips the ReadingGroup with a diagnostic and extracts the other
  groups ([Capacity and non-goals](#capacity-and-non-goals)).

Cloud impact: these are shared OSS contracts that Cloud consumes by upgrading its
OSS pin. They add no configuration, no lifecycle state, no Review field and no
SQLite or HANA migration. The one store change is Plan apply for coordinator
Reviews, which Cloud's HANA adapter makes together with the pin upgrade
([Pending coordinator Review](#pending-coordinator-review)).

### Domain vocabulary

The durable design uses responsibility names rather than model-stage numbers:

| Responsibility | Meaning |
| --- | --- |
| Claim Extraction | extract new claims from authorized current change |
| Candidate Admission | check that each Candidate's selected Evidence completely supports it and merge same-round duplicates |
| Support Assessment | test one fixed existing claim and rebuild its complete current Evidence Unit |
| Sparse Relation (same-Unit Claim Reconciliation) | propose relations between admitted Candidates and same-Unit Active Memories: one row per Candidate, only meaningful relations |
| Support and Relation coordination | combine Support and Relation results by one fixed table before Lifecycle Reconciliation |
| Lifecycle Reconciliation | reduce coordinated Support and relation results into guarded domain mutations |

Historical implementation notes may retain L1/L3/L4 labels, but public types,
methods, result states and new documentation must use the domain names above.

### Complete support

Support Assessment and Candidate Admission judge the same relation: whether
selected Evidence completely supports a claim. It has one definition, and both
model requests carry the same text of it (`pipeline/complete_support.py`).

Selected Evidence completely supports a claim only when every specific the claim
states appears in that Evidence or follows directly from it. Specifics include
names of people, systems and things, identifiers, quantities, dates and times,
statuses, conditions and scope. A claim that states any specific the Evidence
contradicts or does not contain is not supported, even when the rest of the
claim matches, and no knowledge outside the Evidence counts.

Matching the topic, the action or most of the wording is therefore not enough:
a claim that names a different identifier than the Unit Title it selects as
Required Evidence, or a different person, number or date than its Primary
Evidence, is `UNSUPPORTED` in Support Assessment and `REJECTED` with
`evidence_incomplete` in Candidate Admission. Change Impact does not judge
support and does not use this definition.

A change to the definition changes the meaning of both results, so it raises
`REVISION_SUPPORT_CONTRACT`, the Support Assessment work contract and the
candidate admission contract together; completed work under an earlier
definition is never reused. The current contracts are `revision-support-v7`,
`support-ordered-reading-v5` and `candidate-admission-v2`.

Cloud impact: the definition is shared OSS prompt text. Cloud receives it by
upgrading the pin; its HANA derivation work and reconciliation manifests carry
the new contract identities without a schema change, and completed work under
the earlier identities is recomputed rather than reused.

### Backend-neutral context and judgment execution

`RevisionContextPlanner` returns application-owned context, authority and work
manifests rather than a provider prompt. The selected plan is rendered as a
backend-neutral `ContextBundle` whose stable contract and revision-shared
material precede cohort, carried-state and attempt-only material. This permits a
Structured LLM adapter to use provider prompt-prefix caching without making
cache retention part of correctness, and permits an eligible classifier adapter
to evaluate the same state without reconstructing revision context.

Open-vocabulary Claim Extraction remains `GenerationWork`. Closed-set semantic decisions are `JudgmentWork`; a classifier model backed by
TypeSafe/Jev or a small-parameter LLM implements the judgment interface only where
its task-specific evaluation satisfies the complete contract. Runtime confidence
does not switch individual items to another backend. Classifier models do not
generate claims, discover arbitrary Evidence or reproduce compound Support
Assessment. Executor,
model, contract and context digest participate in work identity. Exact selector
validation, complete manifests, lifecycle reduction and destructive validation
remain application-owned for every executor.

Claim Extraction, Support Assessment, Change Impact, candidate admission and
Relation send model work only through the LLM batch runner (ADR 0036, decision
13; target, delivered as the first step of #505). The caller supplies fixed work
items, shared context and the prompt and schema. The runner owns capacity fit
from LiteLLM metadata, partitioning into transport requests, per-row acceptance
with one re-ask of the rejected rows, the split in half of a multi-item request
that fails for capacity or whose output cannot be read into rows after one
correction, bounded concurrency, coverage and ID validation, and typed failures. A truncated response is split, not
resent as JSON text at the same `max_tokens`. When shared context itself must be
chunked, the runner returns one result per item and chunk and the caller merges
them; the runner never receives merge rules. Support Assessment uses its
ordered form: ReadingGroups in reading order, carried compact state and per-item
early exit after the first part of the order. The other tasks send independent
items. None of these transport steps changes coverage or a lifecycle outcome.
Cloud impact: the runner wraps the existing structured client, adds no
configuration and leaves Cloud's client construction unchanged.

The complete decision, operation inventory, cache layout and evaluation gate are
in [ADR 0036](0036-separate-semantic-work-from-inference-executors.md) and
[Semantic judgment execution](../design/semantic-judgment-execution.md).

### One deep context-planning module

Callers use one source-neutral interface:

```python
plan_revision_context(
    base_projection,
    target_projection,
    change_set,
    existing_supports,
    coverage,
) -> RevisionContextPlan | TypedPlanningFailure
```

`RevisionContextPlanner` owns exact Evidence correspondence, removed-anchor
context, representation reading groups, the Support reading order, historical
excerpt selection and work-coverage manifests. Those are private collaborators,
not additional public orchestration stages. Representation adapters for
Markdown/HTML structure, plain text, canonical records such as Jira, and message
graphs such as Teams all emit the same `ReadingGroup` contract:

```text
scope + container + before + target + after
+ authority/selectability metadata + exact fragment references
```

The change target is a sum type: either a current Fragment or a removed Anchor.
A pure deletion therefore has a valid reading group even though no current
target Fragment exists. Historical content is explicitly non-selectable.

Implemented reading groups and reading context: Support and Claim Extraction
share one partition of a revision into ReadingGroups, one outermost list or one
Fragment. Every model reading, whether a Claim Extraction request, a Support
Assessment step or a Change Impact bundle, reads its Fragments with one reading
context: the representation's heading, intro and list lead-in; the Observation
its provider declares it replies to, or else follows (`REPLIES_TO`, else
`PRECEDES`), never inferred from order or similarity; and the Unit Title.
Reading context is Required-only and has no character cap.

The Unit Title is the provider's human-facing name of the Unit, such as a Jira
key, type and summary, a Confluence space and page title, or a repository and
path. The Source adapter contract requires every adapter to supply it from the
values present in the provider payload, without guessing and without
source-specific prompt instructions. It is projected as the first Observation of
every live Unit (`unit_identity`, representation `unit-identity`), so a partial
projection always returns it. It compiles to one Fragment that is never Primary:
it scopes and identifies claims but states none. A claim that names the Unit
selects it as Required, which is what candidate admission checks identifying
details against. It forms its own ReadingGroup, so a changed Unit Title is
ordinary changed content.

### Exact current Evidence correspondence

The planner deterministically classifies every part of prior Support Evidence:

| Status | Meaning | Input consequence |
| --- | --- | --- |
| `EXACT_UNCHANGED` | one compatible exact fragment | current ref |
| `MODIFIED` | object/structure remains but fragment text changed | old exact excerpt + current corresponding ReadingGroup |
| `REMOVED` | authoritative complete coverage proves the old fragment absent | old exact excerpt + the whole reading order |
| `AMBIGUOUS` | exact/structural correspondence is not unique | old exact excerpt + all candidate ReadingGroups |
| `UNKNOWN` | partial coverage cannot prove presence or absence | no model input |

The classification is recomputed for each base/target revision pair; it is not
a remembered `unchanged` flag or a model judgment. The old side comes from the
applied Support's resolved Evidence part (Source Unit and Observation identity,
revision-pinned Anchor, exact excerpt/raw-slice or Artifact digest, and role).
The new side comes from the target Projection's authoritative membership and
one operation-scoped compiled current Fragment catalog. A carried Observation
Revision may retain its exact Anchor. Across Observation Revisions, an old
offset or derived Fragment ID is only a locator hint: the planner must find
exactly one compatible current Fragment in the same Source Unit and provider
Observation, and compare the persisted exact content/presentation digest with
the compiler's current exact representation. The comparison does not ignore
punctuation or paraphrases. Provider `FragmentMapping` does not enter this comparison:
it cannot prove text equality, make an old ref current or choose among exact
candidates, so repeated exact text is `AMBIGUOUS`. A unique
exact match is `EXACT_UNCHANGED` whether or not the ReadingGroup around it
changed; changed surrounding content reaches the claim through the ChangeBundle.
A cross-Source-Unit match is never an automatic rebind.

Routing is decided for the whole Support, not for each part, and the first
matching route applies:

- any part is `UNKNOWN` (a partial projection cannot prove presence or
  removal): `UNRESOLVED(partial_coverage)`, the Support stays unchanged, no model
  call. This route takes priority even when other parts are `MODIFIED`,
  `REMOVED` or `AMBIGUOUS`, because an `UNKNOWN` part never reaches the model;
- any part is `MODIFIED`, `REMOVED` or `AMBIGUOUS`: Support Assessment;
- every part is `EXACT_UNCHANGED` and the revision has no changed content:
  direct `REBIND_SUPPORT`, no model call;
- every part is `EXACT_UNCHANGED` and the revision has changed content: Change
  Impact. `UNAFFECTED` leads to `REBIND_SUPPORT`; `AFFECTED` or a Change Impact
  execution failure sends the claim to Support Assessment.

Each status is a per-part result, not proof that a multi-part Evidence Unit survived.
All Primary and Required parts must have valid current refs before deterministic
REBIND can be proposed. If one part is modified, removed or ambiguous, retain
the uniquely matched current parts as candidates and assess the fixed entire
claim with a complete current Evidence Unit. The matched parts are offered to
the model as selectable current refs, like any other current ref. Whether the
selected Primary/Required set is complete is judged by the
[Complete support](#complete-support) definition; the program does not require
the model to account for a matched part it does not select. Never copy a missing
old ref or promote one matching part to `SUPPORTED`. Missing legacy provenance cannot be
treated as `EXACT_UNCHANGED` and follows the existing limited-Evidence gate.
The status and current-ref map are operation-local derived data; the committed
Support/Evidence and target Projection retain the durable proof and provenance.

`EXACT_UNCHANGED` proves survival of the original fragment, not absence of a distant exception. All added and modified ReadingGroups, together with the old text of every removed ReadingGroup as removed content, are grouped into capacity-safe ChangeBundles, so a deleted distant qualifier reaches the judgment; this uses the removed Anchors the planner already holds and adds no state. The Change Impact executor, which is the existing Structured LLM until a classifier backend passes the #506 evaluation, evaluates every exact-rebound fixed claim against each bundle as `AFFECTED` or `UNAFFECTED`; code OR-reduces multiple bundles. Only all-`UNAFFECTED` work completes KEEP+REBIND. The instruction states one scope rule: a change that contains a global statement with unclear scope, such as "以上流程", "本文档" or "自某日起停用", is `AFFECTED`. This rule has no dedicated evaluation case; the generic #506 classifier-backend evaluation covers it. An execution failure for a claim (after the LLM batch runner's split, if any) sends that claim to Support Assessment; the application never records it as an `AFFECTED` label. There is no per-item confidence fallback. Cloud impact: Change Impact runs on Cloud's configured Structured LLM `sap/` route until a classifier backend is admitted; no configuration is added.

The application retains Memory, Support and Evidence IDs, Observation/Revision identity, exact digests, coverage and provenance outside model input. Historical excerpt transfer is exhaustive and exclusive: `MODIFIED`, `REMOVED` and `AMBIGUOUS` receive it once; no other status does. The excerpt is immutable, non-selectable historical material.

Cloud impact: exact correspondence and whole-Support routing are shared OSS code
over the stored Projection and Evidence that HANA already persists; the status
set needs no HANA field or migration.

### Ordered current-revision reading

Target contract, tracked by Cloud issue #505.

`ReadingGroup` is a coherent current structure containing one or more selectable EvidenceFragments. `AssessmentContext` is one call's one-or-more ReadingGroups and prompt-local Evidence Catalog. `AssessmentScope` is the complete effective current revision.

Support Assessment follows one rule. It streams the complete current content in a fixed order: first every changed ReadingGroup (added, modified and removed) and the ReadingGroups that contain that work item's own prior Evidence, then every remaining ReadingGroup. The first part is therefore per work item, and the LLM batch runner's chain task carries each item's first-part boundary. The first part carries the fixed claims, compact Support metadata and historical excerpts exactly for `MODIFIED`, `REMOVED` and `AMBIGUOUS`; "Delta" names only this first part of the order, not a mode. A work item cannot exit while any ReadingGroup of the first part is unread, because a later changed group may revoke or qualify the Support. After the first part has been read, each work item leaves the read as soon as it has complete Support, as defined in [Complete support](#complete-support). A work item becomes `UNSUPPORTED` only after the whole order has been read without complete Support. The planner derives the order deterministically from exact correspondence, CatalogDiff, coverage and manifest. It makes no Delta/Full cost comparison and no start decision, and it never asks a model whether a partial read is conclusive. The rule requires that the read streams per ReadingGroup (an AssessmentContext holds whole ReadingGroups) and permits a work item to exit between contexts once the first part is read.

Reading the whole order means all eligible effective-current Catalog contexts are processed. A small document may fit one AssessmentContext; a large one streams several contexts under one manifest and grounded previous state. `UNSUPPORTED` additionally requires authoritative coverage of every object the Support's Evidence belongs to; the read never upgrades a partial Projection. For example, when a Jira issue's description was fetched completely and rewritten while its comment pagination is partial, a Support whose Evidence is in the description can reach `UNSUPPORTED`, because that object's coverage is authoritative and the carried-forward comments are still read. A Support whose Evidence is in a comment the provider did not return is `UNKNOWN`.

`REVISION_FIRST` evidence-fixed batching and `COHORT_FIRST` cohort-fixed streaming are separate deterministic cache layouts. The first puts current Catalog before changing claim cohorts; the second puts fixed unresolved claims before changing AssessmentContexts. Previous state remains in the changing suffix. A work item that has exited is removed from later requests even though this changes the cohort prefix; cache behavior cannot alter scope, work identity or result.

Cloud impact: the reading order is shared OSS planning code. Cloud needs no
configuration or storage change and receives it by upgrading the OSS pin.

### Cumulative Support witness state

Support Assessment works at `(memory_id, independent_support_id)` granularity. An Evidence Unit remains one Primary plus zero or more Required refs, possibly selected from several fragments or ReadingGroups in the current AssessmentContext.

The final semantic wire result is `SUPPORTED(work_id, primary_ref, required_refs[]) | UNSUPPORTED(work_id)`. Only `SUPPORTED` admits selectors. Its selectable current pool is the current AssessmentContext catalog plus current refs grounded by earlier contexts and rehydrated with exact current text in `carried_witness_catalog`; historical refs are never selectable. Streamed model output carries only `witness_delta` additions. Application code validates and monotonically union-merges them into grounded supporting/opposing sets, so omission cannot erase an earlier witness; no cumulative status is model-owned. Steps inside the first part of the order return only `witness_delta`. The step that completes the first part, and any later step, may return `SUPPORTED` for a work item, which then exits; otherwise the step returns only its `witness_delta`. A work item exits only on a model-returned `SUPPORTED` that passes program validation. A non-empty opposing-witness set does not block that exit, because the opposing text is carried in the request through `carried_witness_catalog` and the model judged with it. The step that reads the last ReadingGroup of the order returns `SUPPORTED` or `UNSUPPORTED`. Partial coverage (an `UNKNOWN` part, which never reaches the model) becomes application-owned `UNRESOLVED(partial_coverage)`; a single ReadingGroup that alone exceeds the model's capacity for the work item becomes `UNRESOLVED(capacity)`; and a work item whose output alone stays invalid after the one correction (a schema, ID or selection failure) becomes `UNRESOLVED(invalid_response)`. All three KEEP, and the revision commits. A provider error or a timeout that remains after the LLM batch runner split the request down to that one item leaves the Source Unit revision uncommitted, and the next sync retries it.

Prior Evidence reaches the model as selectable candidates: each exactly matched prior part appears by its current ref in `prior_evidence`, and those refs stay in `carried_witness_catalog` for later requests. Whether the selected set is complete is judged only by [Complete support](#complete-support), and the program validates that every selected ref was supplied by the request.

### Sparse same-Unit Relation

Implemented as `claim-revision-v8-sparse-catalog`, described in
[Sparse claim catalog](../design/sparse-claim-catalog.md).

Relation (the claim revision judgment) receives only `ADMITTED` Candidates, each
with its current Evidence, and the Claims of every same-Unit Active old Memory
left after deterministic exact consumption. It runs in parallel with Support
Assessment, so its catalog includes every same-Unit old Memory, including those
whose Support later becomes `UNRESOLVED`. The model input contains no Support
result or reason, and Relation does not judge whether Evidence supports the
Candidate; candidate admission owns that check. Only `SupportRelationCoordinator`
uses Support results, in program code.

The output is one completion row per Candidate that lists only meaningful
relations: equivalent, directional refines, contradicts or uncertain. Omitting an
old Memory means "no relation proposed". A missing Candidate row, a duplicate row
or edge, an unknown ID and a truncated response are execution failures, never
"no relation" and cannot fall back to independent ADD. Each Candidate's row is
validated on its own; the rejected rows are re-asked once, together, each with
its exact error (for example "NEW-0003 names MEM-0037, which is not in its
allowed list"). A Candidate whose row is still rejected after its re-ask is consumed without ADD and without a Review, with a
diagnostic. Its row would have covered it against every old Memory of the Unit,
so the gap cannot be localized: any old Memory may be the one it restates,
refines or contradicts. The Relation line of the revision is therefore
incomplete, and DestructiveValidation withholds every DELETE, SUPERSEDE and
UPDATE of the Unit this round: each such old Memory is kept with its Support and
validation baseline, and a Candidate whose only effect was a withheld SUPERSEDE
or UPDATE is not added. Non-destructive work still commits: rebinds, ADD of the
other Candidates and Reviews. A Relation execution error (a provider error, a timeout, a rejected request or an unexpected exception) leaves
the Source Unit revision uncommitted, and the next sync retries it. The LLM batch runner partitions a large catalog; when the catalog is
chunked as shared context, the caller unions the relations returned for each
chunk. Partitions create no lifecycle state and publish no partial mutation.
Relation labels are proposals and cannot authorize REMOVE or RETIRE. Cross-document
discovery keeps bounded hybrid retrieval followed by classification over K pairs,
where non-destructive recall loss remains accepted. Same-round Candidate
deduplication belongs to candidate admission; deduplication against other Units
and sources belongs to identity.
Amended by [ADR 0039](0039-create-memories-within-the-source-unit.md): sameness with Memories of other Units and sources is
recorded only by the asynchronous `equivalent` relation of ADR 0037, which never
merges Memories.

Cloud impact: the request loses the old Memory's `current_support` field and the
response loses its evidence entailment status. Both are shared OSS prompt and
schema changes; Cloud upgrades the pin with no HANA or configuration change.

### Candidate admission

Implemented as `candidate-admission-v2`; execution through the LLM batch runner.

Candidate admission runs between Claim Extraction and Sparse Relation, for
every Candidate, whether or not the Unit has old Memories. One admission request
covers both duties, with no additional call round:

1. Complete evidence support: the Candidate's selected Primary and Required
   Evidence completely support its Claim, including scope, exceptions and
   table-header qualifiers, as defined in [Complete support](#complete-support):
   every specific the Claim states needs that Evidence.
2. Same-round deduplication: the Candidate states the same knowledge as another
   Candidate of this round. Every admission request carries all of this round's
   Candidate claims (Candidate ID and claim text, no Evidence) as shared context,
   so a duplicate is found even when the two Candidates are judged in different
   requests. Candidates with the same normalized Claim, type and validity are
   duplicates without the model saying so, but each is still judged on its own
   Evidence. The program merges duplicates deterministically into one: only
   admitted Candidates merge, by connected groups of duplicates, and each group
   keeps its most specific (longest normalized) Candidate, the earliest
   extracted among equals. If that
   list does not fit, the LLM batch runner chunks it as shared context and
   returns one result per Candidate and chunk; a Candidate rejected in any chunk
   is rejected, and the reported duplicates of all chunks are united.

| Result | Handling |
| --- | --- |
| `ADMITTED` | enters Sparse Relation |
| `REJECTED` (Evidence insufficient, or reason `low_value`) | not added this round; no Review |
| same-round duplicate | merged; one Candidate continues to Sparse Relation |
| Candidate that stays unjudgeable in isolation (it alone exceeds capacity, or its output stays invalid after the one correction) | `REJECTED` for this round with reason `capacity_exceeded` or `invalid_response`, recorded like any rejection; no ADD, no Review |
| execution error (provider error, timeout, rejected request, unexpected exception) | the Source Unit revision is not committed and the next sync retries it |

An admission execution error adds no Candidate this round and publishes
nothing for that revision; it follows the existing extraction-failure contract.
Each admission request is recorded as `candidate_admission` derivation work, so a
retried sync reuses completed requests and the atomic commit requires them
complete.

A `REJECTED` Candidate emits one structured event with the Source Unit, revision,
Candidate Claim, selected Evidence refs and reject reason, without full source
text, once the revision commits. Each revision counts admitted, rejected and merged Candidates, so an
extraction quality regression becomes visible, for example a rising reject ratio
for one Source or after one deployment. Execution failures use the existing
failure trace. Merges are only counted, not recorded as anomalies.

Sparse Relation receives only `ADMITTED` Candidates. Deduplication against
Memories of other Units and other sources is identity's job
([Same-Unit identity backstop](#same-unit-identity-backstop)), not admission's.
Amended by [ADR 0039](0039-create-memories-within-the-source-unit.md): no step deduplicates against other Units or Sources; an
admitted Candidate that the coordinator keeps as an ADD creates its own
Memory.

Cloud impact: admission is a shared OSS prompt and contract. The event uses the
existing Memory audit events and the counts use sync statistics, so Cloud needs
no HANA schema or configuration change. The HANA commit gate must accept
`candidate_admission` as a required derivation work kind, as SQLite does.

### Support and Relation coordination

Implemented for Cloud issue #505 in `pipeline/support_relation_coordinator.py`.
Support Assessment and Relation run concurrently; a failure raised on either line
cancels the other, and the revision is not committed. A Relation
execution error or a contract failure is returned as the line's result rather
than raised, so the Support line finishes its reads; the revision is still not
committed, and the retry reuses that Support work from its journal. A Candidate
that Relation could not judge even alone is part of the Relation result, listed
as unjudged, and makes the Relation line incomplete.

`SupportRelationCoordinator` is program code that runs after both lines finish and
before Lifecycle Reconciliation. For each same-Unit old Memory it combines the
Support result with the Relation edges that point at that Memory. The rows are
evaluated in this order and the first match wins: the row of a Claim that could
not be judged, `UNRESOLVED(capacity)` or `UNRESOLVED(invalid_response)` (keep),
then the row for an old Memory with both an equivalent and a contradicts edge
(Review, with the contradicting Candidate staged and supersession proposed),
then all other rows, including the `UNRESOLVED(partial_coverage)` rows. A
Support Assessment or re-check execution error never reaches the coordinator,
because the revision is not committed. A Candidate that Relation could not judge
has no edges; the coordinator consumes it without ADD and without a Review and
counts it with the unresolved Candidates, and DestructiveValidation then
withholds every destructive decision of the Unit, because the Relation line is
incomplete.

| Support result | Relation result | Action |
| --- | --- | --- |
| `SUPPORTED` | none or equivalent | keep the old Memory; an equivalent Candidate is consumed, no ADD |
| `SUPPORTED` | contradicts | the current source supports two mutually exclusive statements: the old Memory's verified Support is rebound to its current Evidence, and a coordinator Review is created |
| `UNSUPPORTED` (whole order read) | equivalent | targeted re-check with the Candidate's current Evidence: supported keeps the old Memory and rebinds it to that Evidence; still unsupported creates a coordinator Review |
| `UNSUPPORTED` (whole order read) | contradicts | normal SUPERSEDE |
| `UNSUPPORTED` (whole order read) | none | remove this source's Support; retire the Memory only if no other source has Active Support |
| `UNAFFECTED` (rebound) | contradicts | Change Impact miss: run Support Assessment for this Claim once, in the normal reading order |
| `UNRESOLVED(capacity)` or `UNRESOLVED(invalid_response)` | any | keep unchanged; related Candidates are consumed this round, with no ADD and no destructive action |
| `UNRESOLVED(partial_coverage)` | equivalent | targeted re-check with the Candidate's current Evidence: supported keeps the old Memory, rebinds it to that Evidence and consumes the Candidate, with no ADD; still unsupported creates a coordinator Review |
| `UNRESOLVED(partial_coverage)` | contradicts | coordinator Review that proposes superseding the old Memory with the contradicting Candidate; there is no automatic supersession, because the old Evidence state is unknown |
| `UNRESOLVED(partial_coverage)` | none | keep unchanged |
| any | both an equivalent and a contradicts edge on the same old Memory | coordinator Review |

Re-check rules:

- Each Claim in a conflict group gets at most one re-check per revision. The
  re-check reuses the Support Assessment contract; there is no new prompt.
- A Claim whose Support read already covered the whole order, or whose Support
  is `UNRESOLVED(partial_coverage)`, re-checks only the Candidate's new Evidence.
  A supported re-check on the `UNRESOLVED(partial_coverage)` row replaces the
  Support that had an `UNKNOWN` part, so later revisions no longer find it
  `UNKNOWN`.
- A Claim that has no Support result this revision (the `UNAFFECTED` row) runs one
  Support Assessment in the normal reading order, which may continue to the end of
  the document. Its result then enters the table again; this run is its one
  re-check.
- A conflict that remains after the re-check goes to Review; there is no second
  re-check.
- A re-check execution error leaves the Source Unit revision uncommitted, and
  the next sync retries it; it does not create a Review. A re-check whose
  ReadingGroup alone exceeds capacity, or whose output alone stays invalid, is
  `UNRESOLVED(capacity)` or `UNRESOLVED(invalid_response)` and follows that row.

A supported re-check result is accepted even though the first read found nothing,
because a supported result names concrete current refs that the program validates,
while "not found" only reports absence over a long read. Relation never sees
Support results, and the coordinator never lets one line decide the other's truth.
A rebound `UNAFFECTED` Support with no contradicts edge follows the `SUPPORTED`
rows. REFINES and uncertain Relation results follow the revision-proof and local
unresolved rules in [Local unresolved claim relationships](#local-unresolved-claim-relationships).
When one Candidate receives different treatments across several old Memories,
or is staged in the Reviews of more than one old Memory, the same local
unresolved component rule applies: the whole related component is consumed this
round, with no ADD and no destructive action. The treatments are consumed as an
equivalent, staged in a Review, and replacing an old Memory; a Candidate that
only refines without revising has none. A Candidate staged twice has no single
decision: each approval would apply it again, creating it a second time or
rebinding a second Memory to the same claim.

An old Memory can have several Supports in one Source Unit. Their results combine
by the table's precedence into one Memory-level result: any `UNRESOLVED(capacity)`
Support, then any `UNRESOLVED(invalid_response)` one, then any
`UNRESOLVED(partial_coverage)` one; otherwise a read that found
Support makes the Memory `SUPPORTED`, Supports that were only rebound make it
`UNAFFECTED`, and only a Memory whose every Support was read without complete
Support is `UNSUPPORTED`. The `UNAFFECTED` re-check reads only the rebound
Supports, and one Candidate-Evidence re-check of a Claim reads the Evidence of all
its equivalent Candidates, carrying every prior part the Claim has in the Unit.
A Candidate-Evidence re-check that does not find Support is not a complete read:
the Claim keeps its result and never loses Support because of it.

Several contradicting Candidates on one old Memory name no single successor. When
the whole order was read without Support, the old Memory loses this source's
Support and each Candidate stands on its own; otherwise each contradicting
Candidate gets its own coordinator Review and the old Memory is kept.

Known limitation: a Support is `UNRESOLVED(capacity)` when one ReadingGroup
alone exceeds the model's capacity for its Claim, and `UNRESOLVED(invalid_response)`
when the model's output for the Claim alone stays invalid after the one
correction. The Memory stays unchanged, a diagnostic names the Source Unit and
the ReadingGroup, and the revision commits. Its related Candidates are consumed
this round with no ADD and no destructive action; because an update extracts
only changed structures, their knowledge returns only when that structure
changes again. A Candidate that Relation could not judge alone is consumed the
same way, and while it lacks its row the Unit's old Memories are kept rather
than deleted, superseded or updated. Apart from the local unresolved relationship rule, these are the only
cases in which a Candidate is consumed without a decision.

Cloud impact: the coordinator is shared OSS code. It needs no HANA schema
change. Reviews from the `UNRESOLVED(partial_coverage)` rows use the same Plan
apply as the other coordinator Reviews, and an uncommitted revision is reported
through the existing sync failure status and LLM failure trace, which HANA
deployments already record. `reconcile_memories` takes Memory-level Support
results (`supports`) instead of `support_audits`; Cloud's HANA unit test that
calls it changes with the pin.

### Pending coordinator Review

Implemented for Cloud issue #505. The first version stays minimal.
It applies only to Reviews created by the coordinator table; Source Authority
Reviews keep their existing rules.

- Storage: a coordinator Review is the Lifecycle Plan's existing `CREATE_REVIEW`
  mutation, written to `lifecycle_reviews`. The Candidate that raised it (the
  contradicting Candidate; for the `UNSUPPORTED` x equivalent and
  `UNRESOLVED(partial_coverage)` x equivalent rows, the equivalent Candidate)
  stays in the Review's staged evidence together with the
  proposed action; no Memory is created for it. Approval applies the proposed
  action recorded in the Review, and rejection keeps the status quo. For
  `UNSUPPORTED` x equivalent or `UNRESOLVED(partial_coverage)` x equivalent that
  is still unsupported after the re-check, the proposed action keeps the old
  Memory and rebinds it to the Candidate's Evidence. For `SUPPORTED` x
  contradicts and `UNRESOLVED(partial_coverage)` x contradicts, the proposed
  action supersedes the old Memory with a Memory created from the staged
  contradicting Candidate.
  For an old Memory with both an equivalent and a contradicts edge, the staged
  Candidate is the contradicting one and the proposed action is the same
  supersession; rejection keeps the old Memory and rebinds it to the equivalent
  Candidate's Evidence.
- Stale guard: the Review carries its own stale guard in its staged evidence,
  taken after the creating Plan's own mutations. A Support rebound in the same
  Plan (the `SUPPORTED` x contradicts row) is therefore already part of the
  guard, and approval checks this guard rather than the creating Plan's
  pre-apply guard. Plan apply records it after the Plan's last mutation, and
  the planner places new coordinator Reviews last. Rejection that rebinds the
  old Memory to an equivalent Candidate's Evidence is a Plan too:
  `RESOLVE_REVIEW(rejected)` with that rebind, under the same guard.
- Identity: the Review ID is deterministic, derived from the Source Unit, the
  old Memory, the proposal (supersede or rebind) and a hash of the normalized
  Candidate claim. It does not include the per-run scope, so the same conflict
  always names the same Review, and a rejected rebind of a claim never silences
  a later proposal to supersede with it.
- Recurrence: when a new revision raises the same conflict, the existing Review
  is reused according to its status, and a second record is never created:
  - `pending`: reused; this revision's `CREATE_REVIEW` for the same ID refreshes
    its staged evidence and stale guard to this revision's Support set,
    including a Support rebound this round;
  - `rejected`: the same conflict is not raised again, respecting the human
    decision;
  - `stale`: reopened as `pending` with refreshed staged evidence and stale
    guard;
  - `approved`: the action already ran, so the conflict no longer exists.
  A decided conflict raised again keeps the status quo: the old Memory keeps its
  decision without a Review, and the Candidate is consumed.
- Visibility: while the Review is pending, the old Memory stays Active,
  retrievable and unchanged. There is no "conflicted" marker. Under the lifecycle
  gate, a rebind that removes Support waits with the Review, which then proposes
  against the current Support; the old Memory has one Review decision.
- New revision: it is processed normally and the coordinator judges again. An
  update extracts only changed structures, so Relation cannot raise again a
  conflict whose Candidate was not extracted again. A pending Review whose staged
  Candidate Evidence is still exactly current therefore enters the coordinator
  again with its Candidate and edge, is not re-checked again, and follows the
  table like a new edge: it is refreshed, or resolved by the rows, for example
  superseded normally once the old Memory is read without Support. If the
  revision decides the old Memory and no longer raises the conflict, the
  conflict is gone and the revision's Plan closes the Review with the existing
  `stale` status, before any destructive mutation of the Plan. An old Memory the
  revision keeps unchanged without a decision (an unresolved component,
  `UNRESOLVED(capacity)` or `UNRESOLVED(invalid_response)`, or a destructive
  decision DestructiveValidation kept)
  keeps its pending Reviews as they are; a later revision that decides it
  refreshes or closes them. A different conflict has a different Candidate claim
  hash or proposal and therefore its own Review. A reviewer cannot refresh a
  stale coordinator Review by hand; the next revision that raises its conflict
  reopens it.
- A review decision applies only while the related Memory, its Support and its
  Source Unit revision are unchanged, through the existing stale guards. A
  decision whose guard no longer holds is refused (409) and leaves a coordinator
  Review pending, because `stale` means only that its conflict is gone; the next
  revision of its Source Unit raises the conflict again against the current state.
- Lifecycle gate: approval and a rejection that rebinds are Plans, so both need
  the source's lifecycle gate enabled and are refused (409) under the gate. A
  rejection without a rebind only resolves the Review and works under the gate.

Cloud impact: the ID derivation, the Review's own stale guard and the
recurrence decision live in the OSS planner and review code. Reuse, reopen and
close change an existing `lifecycle_reviews` row, so both stores' Plan apply
treats `CREATE_REVIEW` as an upsert on the Review ID that writes an existing
`pending` or `stale` row back to `pending` with the new Plan ID and staged
evidence and refuses any other status (the planner never emits it for a
`rejected` or `approved` Review), and `RESOLVE_REVIEW` also accepts `stale`. The call sites are
the `CREATE_REVIEW` and `RESOLVE_REVIEW` branches of
`_apply_lifecycle_mutation_unlocked` in OSS `storage/database.py` and of
`_apply_lifecycle_mutation_on_connection` in Cloud's HANA adapter
`packages/adapters/store/hana/.../workspace.py`. Plan apply also records each
created Review's own guard after the Plan's mutations (the incumbent's Unit
Support-set hash and its Memory version, the digest of `status`, `content_hash`
and `updated_at` that the Plan stale guard uses), `RESOLVE_REVIEW` accepts
`rejected` for the rejection Plan, and `list_lifecycle_reviews` takes
`incumbent_memory_ids` so a revision reads the Reviews of its own old Memories.
No field, status, migration or mutation type is added, but Cloud changes the
HANA adapter together with the pin upgrade.

### Same-Unit identity backstop

Superseded by [ADR 0039](0039-create-memories-within-the-source-unit.md) (2026-09-26): the identity step, its exclusion set, the
attach path and the Plan rule against an identity attach are removed. A Relation
omission within the Unit is not repaired; Sparse Relation over every active old
Memory of the Unit and candidate admission's same-round deduplication are the
only same-Unit duplicate checks. The mechanism below is kept for context.

Implemented for Cloud issue #505 (`identity_excluded_incumbent_ids` in
`memory/lifecycle_planner.py`).

Identity deduplication for this Unit's ADD Candidates excludes only the old
Memories that this round's Plan will DELETE, SUPERSEDE or UPDATE (a revision
UPDATE emits `SUPERSEDE_MEMORY`), and the old Memories whose decision this round
is REVIEW. Old Memories kept this round, including rebound and `UNRESOLVED` ones,
are eligible identity targets. A hit uses the existing non-destructive attach and
creates no Memory. It does not pass through the coordinator and adds no prompt,
configuration or state. Relation omission still means "no relation proposed";
identity decides equivalence on its own, so the two do not conflict. One
Lifecycle Plan can already rebind an old Memory's own Support and attach an
identity-matched new Support to the same Memory: Plan validation, mutation order
and stale guards accept both on one Memory in SQLite and HANA.

The exclusion set is computed by the planner's own rules from this round's
operations, after the round's Evidence Units are built: a DELETE, SUPERSEDE or
UPDATE; a coordinator Review that is raised (a conflict a human already decided
keeps the old Memory and is not raised); and, under the lifecycle gate, a rebind
that removes Support. The Plan rejects an identity attach to an old Memory whose
decision is not KEEP, so a disagreement fails the revision instead of committing.

Identity judges each Candidate/Memory pair through the LLM batch runner, and the
catalog request lists each Candidate's allowed Memory IDs next to that Candidate
(`memory-relation-v5-sparse`). Unlike the per-row stages, the identity catalog
is validated as one answer, so an invalid catalog gets one whole-request
correction and is then split. A proven equivalent attaches even when another
pair of the same Candidate could not be judged. A Candidate without a proven
equivalent and with a pair that stays unjudgeable in isolation (capacity, or
output still invalid after the one correction) may duplicate an old Memory: it
is consumed without ADD, with a diagnostic, like a local unresolved
relationship, and the revision commits. An identity execution error leaves the
Source Unit revision uncommitted.

Known residue: when the old Memory is deleted this round and Relation also missed
the equivalence, the Candidate becomes a Memory with a new ID. No duplicate
results, and this is accepted.

Acceptance: in a fixture where Relation omits an equivalent, the Unit ends with no
duplicate Active Memory; within one Plan no Memory is both deleted, superseded or
updated and the target of an attach, and the planner rejects a Plan that would
do so.

Cloud impact: only the exclusion set that OSS passes to identity changes. HANA
already implements `excluded_memory_ids`, so Cloud upgrades the pin.

### Automated destructive validation

Implemented for Cloud issue #505 in `memory/destructive_validation.py`.

There is no human confirmation step. Before applying a proposed
`REMOVE_SUPPORT`, `SUPERSEDE` or `RETIRE_MEMORY`, Lifecycle Reconciliation runs
an automatic `DestructiveValidation` over the affected fixed claims. It verifies:

1. authoritative coverage or an explicit tombstone for every affected object;
2. complete Claim Extraction and Support Assessment manifests with no technical
   failure or unresolved independent Support (an extraction ReadingGroup skipped
   because it could not be read alone, for capacity or invalid output, is a
   recorded coverage fact, not a technical failure);
3. resolvable decisive current witnesses and non-stale Support-set hashes;
4. every `UNSUPPORTED` proposal binds a completed receipt for the whole ordered
   read;
5. the aggregate active-Support count after simulating source-scoped removals;
6. for every DELETE, SUPERSEDE or UPDATE (a revision UPDATE emits
   `SUPERSEDE_MEMORY`), complete Relation work: every admitted Candidate has its
   completion row over the complete same-Unit old-Memory catalog.

The validator does not run another semantic scan. Support Assessment owns the
single ordered read; DestructiveValidation verifies its receipt, manifests,
witnesses, Support count, Relation completeness and stale guards. Unknown
coverage, `UNRESOLVED` Support or stale input yields KEEP and leaves the
validation baseline unchanged; an execution error leaves the Source
Unit revision uncommitted. Only zero remaining
active Supports may retire a Memory. Another source's active Support always
prevents retirement by the current source.

The validator runs on the coordinator's operations before identity and the
Plan, and checks what the earlier steps recorded (amended by [ADR 0039](0039-create-memories-within-the-source-unit.md): there
is no identity step, so it runs directly before the Plan):

- Checks 1 and 2: every Support the old Memory has in this Unit has a result and
  none is `UNRESOLVED`. Exact correspondence already makes a part `REMOVED` only
  under an explicit tombstone or coverage that proves absence, and routes any
  `UNKNOWN` part to `UNRESOLVED(partial_coverage)` before a model call.
- Check 4: a DELETE or SUPERSEDE rests on Supports that each read the whole
  reading order and recorded the completion receipt. A Candidate-Evidence
  re-check never counts. A Support read whose order is empty records a program
  receipt for it; a revision whose content became empty is decided by coverage
  without a read, as described below.
- Check 6: every destructive decision rests on a Relation line whose completion
  rows cover every admitted Candidate over the catalog of every old Memory
  decided by Support and Relation. A missing row may be the Candidate that
  restates an old Memory the table would delete, so an incomplete Relation line
  withholds every destructive action of the Unit, a DELETE included. A Candidate carried by a pending Review was not
  extracted again, so its completion row is the one from the revision that
  raised the Review; the table may still supersede with it once the old Memory
  is read without Support.
- Checks 3 and 5 stay where their facts are: the Plan's stale guard rejects a
  commit whose Support sets, Memory versions or Observation revisions moved, and
  the planner retires a Memory only when the removed Support was its last.

A kept decision leaves the old Memory with its Support and validation baseline
and consumes a replacing Candidate without an ADD, like a local unresolved
relationship; statistics count each reason. Decisions held for Review are
proposals, protected by their stale guard at approval. A revision whose content
became empty is decided without a read: its claims lose their Support only where
every Observation they rest on was returned or the coverage proves absence, and
the others are `UNRESOLVED(partial_coverage)`. Partial coverage needs no guard of
its own: a claim whose Evidence was returned and read completely can lose its
Support, and a claim with an Evidence part that was not returned cannot.

Cloud impact: the validator checks results the Support and Relation lines already
hold in the OSS process and reads no store; Cloud upgrades the pin with no HANA
change. Removing a Support under partial coverage now depends on the read of the
returned Observations rather than on an affected-anchor proof, which changes
Jira and Teams outcomes after the pin upgrade.

### Source Unit identity and convergence

Amended by [ADR 0039](0039-create-memories-within-the-source-unit.md) (2026-09-26): no identity matching attaches the new Unit's
Candidates to the old Unit's Memories. The new Unit creates its own Memories,
and the old Unit's Memories retire once their last Support is removed. The
commit order stays, because deletions are detected only after every document of
the run committed, which is what makes absence authoritative.

Provider identity changes are Source Projection facts. If a Confluence Page,
Teams window or other Unit loses its provider identity, authoritative inventory
represents the event as old Unit deletion plus new Unit creation. The lifecycle
may remove the old Unit's Supports and extract candidates from the new Unit; it
does not promise Memory-ID continuity or perform cross-Unit destructive semantic
rebind. Ordinary non-destructive identity matching may still attach a new
equivalent Support to an active access-compatible Memory.

Under `COMPLETE_SNAPSHOT`, disappearance may remove old Supports. Under
`PARTIAL_PROJECTION`, absence is unknown and old Supports remain. Implemented
for #505: when a Source Unit's identity changes, the new Unit's creation and its
identity attach commit before the old Unit is removed. Identity matching finds
only Active Memories, so this order lets an equivalent Memory be reattached
instead of retired with the old Unit and recreated under a new ID. This is an
ordering constraint only; it adds no state, and Memory-ID continuity is still
not promised. The operations must be idempotent and converge. A sync commits
this run's Units first, including a deferred commit that waits only on another
Unit of the run, and detects deletions after that; a deferred commit that fails
for good counts as a failed document, so absence stays unproven for that run. A
deferred commit that still waits after that convergence has failed for good
unless it waits, directly or through another deferred commit, on a Unit outside
the run: only the removal of such a Unit can still unblock it. It is retried
after the removal, and one that waits on a Unit outside the run that this run
does not remove is not retried. A crash
between the two steps leaves the old Unit, which the next complete sync removes.
A provider-declared stable move,
reply, quote or correction mapping may enlarge an explicit comparison scope,
but text similarity alone never does so. Cloud impact: the ordering is shared
OSS sync code; Cloud upgrades the pin with no HANA change.

### Capacity and non-goals

Representation adapters may split one large Observation only into exact,
claim-coherent authority ranges with a complete coverage manifest: for example,
table header plus row, list lead-in plus item subtree, or heading plus paragraph.
Cross-range claims use one Primary and the necessary Required references.
Target (#505): the LLM batch runner measures capacity fit. When an indivisible ReadingGroup
still exceeds route capability, the outcome depends on the work: a Support work
item that cannot fit is `UNRESOLVED(capacity)` and KEEP, with a diagnostic naming
the Source Unit and the ReadingGroup, while other work continues and the Source
revision may commit. A Claim Extraction ReadingGroup that cannot fit is skipped
with a diagnostic naming the Source Unit, the ReadingGroup and
`input_capacity_exceeded`; the other groups are extracted and the revision
commits. Planning skips a group the capacity fit rejects, and execution skips a
group the provider still rejects alone, so recovering a derivation plans the
same skip; the skipped count is reported in the extraction statistics. A
ReadingGroup whose extraction output stays invalid when read alone, after the
one correction, is skipped the same way with the reason `invalid_response`. Because an
update extracts only its changed structures, the skipped group's knowledge is
extracted again only when that structure changes again. A skipped group is a
recorded coverage fact, not a technical failure of the extraction manifest, so it
does not block a destructive action that
[DestructiveValidation](#automated-destructive-validation) otherwise admits.
Cloud impact: capacity is measured from LiteLLM metadata and the existing
`MEMFORGE_LLM_MAX_*` caps for Cloud's `sap/` routes; no configuration is added,
and the skip is shared OSS extraction code with no HANA change.

This amendment deliberately does not add semantic Evidence retrieval, manual
confirmation, a separate candidate-to-candidate deduplication pass, permanent Fragment
rows, a MemoryRevision entity, a second lifecycle state machine, cross-Unit
identity continuity, or partial lifecycle commits.

## Decision

Decisions 1, 2, 3, 4, 5 and 6 state the target contract (Cloud #505); the
implemented contract is summarized in [Status](#status).

1. Reuse one operation-scoped representation index and staged base/target
   snapshots. A source-neutral revision-input planner builds one reading order
   for Support Assessment over the complete current input without non-current
   history: first every changed ReadingGroup (added, modified and removed) and
   the ReadingGroups holding prior Evidence, with compact Support metadata and
   bounded exact history only for `MODIFIED`, `REMOVED` and `AMBIGUOUS`; then
   every remaining ReadingGroup. After that first part has been read, a work item
   exits once it has complete Support. There is no cost comparison between plans
   and no changed-content percentage threshold. The baseline belongs to the
   evaluated Support, not its Evidence birth revision or the latest Source sync.
   Initial import streams its full authorized Primary work per ReadingGroup
   through the LLM batch runner. Support Assessment streams exact ReadingGroups
   under one complete work manifest. Oversized work never silently truncates
   coverage: a ReadingGroup is read whole or, when it alone exceeds capacity,
   reported with a diagnostic.
2. Keep read scope separate from new-claim Primary authority. On an update,
   Claim Extraction reads only the changed structures, with their ReadingGroups
   as context, and Primary is limited to authorized added/changed complete
   structures or canonical fields. Extraction makes no cost comparison between a
   Delta read and a current-full read. Existing-claim validation can use current
   unchanged Evidence without authorizing duplicate extraction.
3. One completed Support Assessment returns a discriminated semantic result for
   the fixed claim. `SUPPORTED` carries one current Primary and zero or more
   Required refs; `UNSUPPORTED` carries no selectors. `SUPPORTED` may be
   finalized at any point of the ordered read after its first part; `UNSUPPORTED`
   only after the whole order. Partial coverage, a single ReadingGroup that
   alone exceeds capacity and output that stays invalid for the one item return
   application-owned `UNRESOLVED(partial_coverage)`, `UNRESOLVED(capacity)` and
   `UNRESOLVED(invalid_response)` and KEEP; an execution error that
   remains after the request was split down to one item leaves the Source Unit
   revision uncommitted. The
   application resolves
   complete current Evidence Units, and Required membership may split, merge,
   grow or shrink. An old offset locates only its own revision. Semantic selection
   of supplied current fragments does not reconstruct the author's edit history.
   Stored provenance remains exact and immutable.
4. Same-Unit Claim Reconciliation consumes deterministic exact matches, then runs
   sparse Relation: one completion row per `ADMITTED` Candidate, listing only
   meaningful relations to same-Unit old Memories. Omitting an old Memory means
   no relation proposed; a missing Candidate row, duplicate output, unknown IDs
   and truncation are technical failures, not relationship labels. `REFINES`
   denotes the same knowledge item with a compatible directional change; the
   label alone still cannot replace a broader incumbent with a narrower rule.
   Relation never receives Support results. `SupportRelationCoordinator` combines
   Relation with Support by the fixed table, and the Lifecycle Planner then
   applies source authority and scope facts before proposing actions. Relation labels never
   directly authorize destructive mutation.
5. Keep existing Lifecycle Plan, complete incumbent coverage, Source Authority,
   Review, causal stale guards, and atomic commit. Model output never directly
   creates or retires Memory. Unknown selectors and malformed or incomplete
   results remain execution failures with the existing bounded correction/retry
   contract; they cannot fall back to independent ADD. Review arises from the
   Source Authority contract and from the coordinator table in
   [Support and Relation coordination](#support-and-relation-coordination), under
   the [pending coordinator Review](#pending-coordinator-review) rules; there is
   no human confirmation step for ordinary revisions.
   Competing incompatible refiners retain the existing fail-closed boundary;
   this decision does not introduce multi-option Review, all-candidate conflict
   scanning, or a separate Memory lifecycle state.
6. Retain pre-creation identity reuse and post-commit bounded relation discovery
   from ADRs 0006/0009. New supported Memory may be visible before cross-document
   conflicts are discovered. This temporary window is accepted; no conflict-free
   publication guarantee or fixed completion deadline is implied. Persist work
   with the lifecycle transaction, retain auditable failure/retry, and never give
   discovery authority to retire another source's knowledge. Discovery records
   relations, not Reviews ([ADR 0037](0037-record-cross-document-conflicts-as-relations.md)). Pre-creation
   identity reuse also covers this Unit's kept old Memories, as described in
   [Same-Unit identity backstop](#same-unit-identity-backstop).
   Amended by [ADR 0039](0039-create-memories-within-the-source-unit.md): pre-creation identity reuse is removed; post-commit
   relation discovery is the only comparison with other Source Units.

Bounded structural reading groups deliberately accept occasional semantic false
acceptance when a dependency outside the supplied group is missing and the model
does not recognize the gap. Reading the whole order eliminates that particular omission for
a fitting current snapshot, but does not claim semantic recall. A work item that
has not found Support in the first part of the reading order simply continues
reading; it is not an error. Illegal provenance, incomplete planned execution or provider
coverage, visibility errors, model abstention and destructive-authority
violations instead produce typed fail-closed outcomes.
Supplemental agentic reads remain the separate beta in
[Cloud issue #468](https://github.com/dodoman-sun/memforge-cloud/issues/468).

## Relationship to existing decisions

### Support validation baseline ownership (2026-09-07)

This ADR is the canonical owner of the following baseline contract. ADR 0030
owns immutable Evidence representation; ADR 0009 owns asynchronous discovery.

- Evidence References identify immutable Observation Revisions and exact ranges.
  An Evidence Unit's original document revision and extraction run describe its
  provenance, never the progress of later Support validation. Reusing an
  unchanged Evidence Unit must not update its original extraction run. New
  Evidence metadata must not duplicate these typed revision/run columns; existing
  historical metadata is preserved as audit data.
- A Support Assertion links to the last applied Lifecycle Plan that actually
  established or successfully revalidated that exact Memory/Evidence Unit pair.
  Its effective baseline is that Plan's target Source Unit revision. Do not
  duplicate that revision or run on Support, or infer it from the latest Source
  sync, Memory timestamp, Evidence creation version, or another Support's Plan.
- Publish this association with the corresponding ATTACH_SUPPORT mutation in
  the same transaction as the Plan and Source projection. Rollback and rejected
  or stale Plans publish no progress. A removal, KEEP without a validation,
  pending proposed mutation, or unrelated successful validation does not advance
  this association. Existing causal and complete-coverage guards remain required.
- A protected old Support retained pending a destructive lifecycle Review keeps
  its last proven baseline. A cross-document relation does not freeze
  independently validated Support on either Memory, and Review presence is not
  itself a validation result or a new baseline state.
- Supports established at v3, v10 and v15 but each validated through v19 can
  share v19-to-v20 assessment context. A Support still validated only through v3
  requires v3-to-v20 context or a complete current-catalog proof. Unchanged
  Observation Revisions may retain their exact References; changed Observations
  require newly resolved current References, not edited historical anchors.

Schema upgrade adds only the nullable successful-Plan association. Existing
NULL associations mean that no verified validation baseline is recorded, not
current validation. L3 may establish one through a new complete-current
assessment and normal Plan when the current target provides complete authorized
coverage. This absent-baseline case is distinct from a recorded baseline whose
named snapshot is missing, mismatched, corrupt, inaccessible, or incomplete.
Such a Support has no usable baseline, so the planner cannot tell what changed
for it. It is not rebound by the program and does not go through Change Impact.
It enters Support Assessment, and the whole current revision is read without
assuming old Support validity, exactly as when no baseline is recorded. The
outcome is an ordinary `SUPPORTED` or `UNSUPPORTED` under the usual coverage
rules, and a successful result establishes a new baseline. A diagnostic names the
Support and the unusable snapshot so the data defect can be investigated;
processing does not wait for a repair. Claim Extraction keeps its own rule: an
incremental request whose required base is unavailable must not turn into an
initial full extraction.

Optional historical backfill requires an applied Plan's exact Support mutation,
matching source/unit, complete target membership and authoritative stored
Evidence; a Source-wide success or timestamp is insufficient. Backfill is a
separately authorized, bounded recovery operation with exact-count dry-run and
stale guards. It never rewrites Evidence, Plans, Reviews, or failed jobs and
does not require source re-ingestion. When no verified baseline exists and the
task contract permits current-full proof, assess the complete current catalog
through the same LLM batch runner
([ADR 0036](0036-separate-semantic-work-from-inference-executors.md), decision
13). In this L3 path, full input means
complete current coverage, not one model request and not access to unrecorded
historical content.
Only necessary indivisible work that still exceeds the configured capability
fails through the existing capacity contract; never borrow a newer delta,
silently truncate, or fabricate validation.

Implementation and adapter acceptance of this amendment must be verified
separately from the previously implemented L3/L4 assessment contract.

This amends ADR 0030's one-selector-per-old-Required
revalidation mechanics and the separate support/proof orchestration described
in ADR 0012. Their immutable Evidence, authority, storage, and retry invariants
remain. ADR 0008's pruning is semantic-conservative: unchanged old Evidence or
cross-revision position non-overlap alone cannot rule out an exception elsewhere.
ADRs 0009, 0017, 0019 and 0023 remain the owners of asynchronous discovery,
recoverable derivation, vector delivery and Review orchestration.

The shared Source sync engine now consumes unified L3 and L4 results. Historical
ADRs retain the superseded mechanics for context; no historical Evidence is
rewritten. Cloud implements the same
shared contracts; only HANA/hosting consequences belong in Cloud ADRs.

## Validation and version boundaries

Preserve existing deterministic admission normalization and fixed-slot binding
before strict resolution. Unambiguous redundant extraction refs and the current
first-decision pair normalization must not become whole-document failures.
Validate only fields applicable to the selected result; derive mechanical
eligibility in application code rather than requiring redundant model agreement.
Existing one-workset selector correction and typed non-retryable exhaustion
remain. Semantic disagreement is not a transport retry signal. These allowances
never repair an unknown identity by guessing, omit required coverage, or grant
out-of-scope authority.

`projection-extraction-v9` is an extraction contract selected by current v2
Support capability; it is not the Evidence compiler version, currently 4.
Update the affected L3/L4 semantic work identities and any changed input-policy
identity through existing descriptors/hashes. Do not bump the compiler unless
fragment/coordinate semantics change, invent a Support migration, or rename an
unchanged L1 contract solely because downstream calls were combined. Already
committed history is not rewritten; incomplete work obeys existing invalidation
and recovery boundaries.

Target contract, tracked by Cloud issue #505. A RepresentationCompiler change to
fragment segmentation or text representation can make existing Evidence stop matching exactly. The affected Supports then
enter Support Assessment as a whole the next time their Unit gets a new
revision. This is a one-time cost that document updates spread out naturally;
a large batch is handled by the LLM batch runner's split on capacity failure. A compiler
change that alters segmentation or text representation must state this impact
in its PR. There is no version migration or rollout mechanism for it. Cloud impact: the same re-assessment load
reaches Cloud when it upgrades to a pin that contains such a compiler change, so
the PR statement also covers Cloud.

A Source adapter that adds model-visible Unit content, such as the Unit Title,
is absorbed the same way: the next revision of each Unit carries the new
Observation as added content. It authorizes no extraction, and exact Supports go
through Change Impact. Such a change states the one-time load in its PR. Cloud
impact: Cloud reaches the same load as its Units are next fetched after the pin
upgrade; the new Observation needs no HANA schema change.

Both rules wait for a Unit's next revision, and a Unit that no longer changes (a
closed Jira issue, an archived page) never gets one. An operator reprocesses such
Units at their current revision: a `REPROCESS` Source sync run reprojects each
named Document from its stored input (the item metadata its Gene discovered,
kept with the Document, the raw content, and the Artifacts of its committed
revision) with the current adapter and compiler, without contacting the provider.
The Unit then goes through the ordinary revision flow in one atomic commit, with
two differences: extraction reads every ReadingGroup, under the run's reprocess
authorization, and every Support is read over the whole Unit as if it had no
usable baseline, so no Support is rebound or sent to Change Impact. The run
keeps the sync cursor and infers no removal, and a stored input that no longer
places the Unit where its committed revision does fails that Unit with
`stored_input_incomplete`. A Document stored before its item metadata was kept
can fail this way when the adapter places the Unit from that metadata (a
Confluence child page, a GitHub file); an ordinary sync that stores the Document
again makes it reprocessable. The run reads the latest stored input: raw content
that a sync stored but whose revision never committed is projected and committed
as the next ordinary sync would. Like every run that holds the Source lease, a
reprocess run first finishes derivations an earlier run left interrupted. A
compiler or adapter change states in its PR the OSS and Cloud load and which
Units, if any, should be reprocessed; `dry_run` reports each Unit's stored input
and an estimate of its model calls before the run (extraction items, one
admission request, one Relation request when the Unit has Supports, one
whole-Unit reading per Support), leaving out requests split for capacity,
Support readings that take several steps, selector corrections, entity
resolution, cross-document relation classification and the interrupted
derivations the run finishes first. Cloud impact: the reprocess runs on the
Source sync run queue, which gains one HANA column for its Documents and the
reprocess enqueue rules; the Document row gains one HANA column for the item
metadata; and `run_source_sync` passes `execution_mode` again.

The input policy counts the exact fallback prompt with its response schema,
actual supplied images and requested output allowance. Configured input,
context-window and output caps are intersected with LiteLLM metadata. Known route
aliases resolve to their corresponding SDK model (SAP Sonnet 4.6 uses Bedrock
Sonnet 4.6 metadata and tokenizer); capacity numbers are not duplicated in an
application registry. Unknown aliases require all three explicit route caps rather
than a silent universal limit. The default input fraction is 0.8; the shared
request budget also applies its versioned output and bounded-correction reserves.
These are transport-capacity limits, not an edit-percentage mode threshold or an
accuracy guarantee. Actual extractor model, output allowance and policy
configuration participate in derivation identity. In the target contract (#505)
the LLM batch runner applies this capacity policy to every model call.
A request with several work items that fails for capacity is split in half and
resent (ADR 0036, decision 13). No output budget, tokens-per-second estimate or other
setting beyond LiteLLM metadata, the `MEMFORGE_LLM_MAX_*` overrides and
`request_timeout_s` is added.
L4 shares one candidate/Evidence payload across its comparison group and sizes
output to the existing workload. It does not change coverage; oversized
requests subdivide within that complete workload. Image-capable context
reserves existing multimodal admission before loading bytes; image integrity
errors are terminal, while unavailable storage remains a recoverable read failure.

## Consequences

Same-Unit sparse claim assessment (`claim-revision-v8-sparse-catalog`) uses the
shared request catalog and completion validator described in ADR 0009.
Challenger/incumbent references are `NEW`/`MEM`; Evidence catalog references are
`PRM`/`REQ`, and admission's Candidate references are `CND`, each followed by
four digits. The claim work identity includes the changed contract and schema,
so older completed work cannot be reused against a different catalog. Relation
input carries no incumbent Support result, and Evidence entailment belongs to
candidate admission ([Sparse same-Unit Relation](#sparse-same-unit-relation),
[Candidate admission](#candidate-admission)). Complete incumbent support
auditing, conditional exact comparisons between competing refiners and
destructive revision proof are unchanged.

The material changes concentrate in input preparation, L3, L4, and coordinator/Plan
integration. Entity resolution stays a bounded retrieval helper, not a truth or
identity authority. No new scheduler, persistent Fragment model, MemoryRevision
entity, or historical-document browser is required.

Reading groups and request partitions are transient presentation boundaries.
They do not merge list-item Evidence, combine independent Evidence Units or
Supports, regroup incumbents, create intermediate lifecycle states, or change
the complete atomic Lifecycle Plan. Resolver and lifecycle identity continue to
use exact Fragment and Evidence-Unit membership.

Fewer logical calls do not prove lower total cost: L4 now receives complete
candidate Evidence, and Sparse Relation over all same-Unit old Memories remains
required. Validate
accuracy, input/call cost, unresolved outcomes and latency on a fixed cohort;
record request coverage and capability failures rather than silently truncating.

## Unified revision input planning and bounded execution

Target contract, tracked by Cloud issue #505; the current implemented contract
is summarized in [Status](#status).

The revision-input planner never draws a negative Support conclusion from part
of the document. It is source-neutral: representation profiles supply exact
structures and reading groups; the planner does not branch on Confluence, Jira,
Teams, GitHub, local files, or agent clients. Support Assessment has one model responsibility:
assess the fixed claim and update its current Support evidence in light of the
selected complete input. A rule remaining in force is distinct from execution
compliance; missing results or unfinished examples do not by themselves revoke a
normative obligation. Deletion, rewrite, heading/scope change, and Required
split/merge use that same contract rather than source-specific classifiers.

For a valid base/target pair, the planner constructs one reading order over the
complete eligible effective current snapshot. Its first part (Delta) holds the
changed current structures and the ReadingGroups that contain prior Evidence,
with compact prior-Support metadata, current candidates for exact unchanged
Evidence, and bounded exact historical excerpts only for `MODIFIED`, `REMOVED` or
`AMBIGUOUS` Evidence. Every remaining current ReadingGroup follows. The order does
not repeatedly transport unchanged historical Support bodies or semantically
search for current Evidence after exact correspondence fails.
The order omits non-current `oldhistory`. Reading the whole order means coverage of that current Source Projection,
not provider version
history, deleted upstream data, a repair for incomplete collection, or a grant of
new extraction authority. Partial Projection carry-forward remains current input;
an upstream omission without authoritative coverage still cannot prove deletion.

The plan receives a deterministic request-format forecast across all requests,
including prompt/schema transport, repeated material, initial/carried-state
reserve, output reserve and images. Every emitted request still passes actual
capacity admission. An indivisible ReadingGroup that exceeds the route makes
each work item still reading at that point `UNRESOLVED(capacity)` and KEEP, with
a diagnostic naming the Source Unit and the ReadingGroup; other work continues. After the first part of the order has been read, a work item
leaves the read as soon as it has complete Support; only a work item that has
read the whole order may become `UNSUPPORTED`. Support Assessment streams exact
ReadingGroups under complete manifests. Claim Extraction reads only the changed
structures on an update and streams per ReadingGroup on a first import, and it
limits Primary to authorized current work. The planner does not use edit ratio, document-size percentage,
Fragment-count percentage or source-type preference, and it never asks a model
whether a partial read is conclusive.

A fitting reading order and claim group uses one model request. A larger order
uses the same cumulative assessment contract over stable Source batches. Each request receives
the fixed claims, compact Support metadata, current exact catalog, the affected
bounded historical excerpts and processed-group metadata. Cumulative state is
application-owned: code validates and monotonically union-merges each model
`witness_delta` into supporting/opposing current refs; the next request rehydrates
that union with exact current text and Primary eligibility. It does not
carry an unbounded prose narrative or cumulative Support status. `UNSUPPORTED`
is derived only after the complete group manifest is satisfied; an
unrelated later group cannot erase an earlier revocation or exception.
Batches describe one base/target pair, not intermediate Source revisions. When
Support Assessment has no recorded verified baseline and complete-current proof is permitted,
the whole order is read with the same executor without assuming old Support validity. A
named baseline whose snapshot is unavailable or mismatched is handled the same way,
with a diagnostic (see Support validation baseline ownership).
Here “old” means Evidence from the historical Source revision. Earlier batches
of this same target revision remain valid assessment context;
their selected current refs remain grounded because the next batch supplies the
corresponding exact text through `carried_witness_catalog`.

Current selectors are limited to the current catalog and grounded current refs in
the cumulative witness state supplied in that request. These refs form one shared
candidate pool: a claim may select Evidence another claim previously selected.
Candidate availability is a request property, while judgments and complete
Evidence Units remain independent per claim/Support.
Refs omitted from the request, including other claim batches, are not selectable.
Historical material never becomes selectable current Evidence.
The application validates the final complete Evidence Unit from exact original
refs; it does not require a final model request to reread all retained raw text.
Cumulative witnesses are inference state, not stored Evidence. Bounded execution
still accepts model semantic misses, but complete range coverage, decisive-witness
retention and the union merge of witness sets, which yields the same set in any
merge order, prevent transport partitioning from silently forgetting an earlier
judgment. A Support Assessment that ends `UNRESOLVED(partial_coverage)`,
`UNRESOLVED(capacity)` or `UNRESOLVED(invalid_response)` preserves its existing Support and Evidence and does not
advance its validation baseline; the program emits a bare NOOP / KEEP unless an
`UNRESOLVED(partial_coverage)` row of the coordinator table applies. If any
independent Support is unresolved, the incumbent takes no destructive action
this round. Other incumbents and extraction candidates continue, and the Source
revision may commit. The unresolved result itself needs no Review or hidden
model substitution. A Support execution error that remains after the
runner split its request down to one item is not `UNRESOLVED`: the Source Unit
revision is not committed, and the next sync retries it. The existing Plan
records the exact preserved Support IDs on its KEEP decision under the usual
Support-set stale guard. This exception cannot validate a new attachment or
authorize destructive mutation.
Unresolved incumbents remain in the Sparse Relation catalog, but their preserved
Support prevents those relation labels from authorizing an automatic destructive
action; the coordinator table decides their re-check or Review.
They also remain eligible for ordinary candidate identity matching and
independent corroboration (amended by [ADR 0039](0039-create-memories-within-the-source-unit.md): identity matching is removed).
A later assessment still uses each
Support's actual validation baseline, not the last Source sync revision.

SQLite and HANA apply the same support-preserving invariant in both Support
representations: a structurally valid unrelated Unit's historical Support cannot
block a non-destructive write; destructive decisions still require complete current
Support. Technical failures, invalid selectors and incomplete execution coverage
remain errors. Supplemental exploration stays #468.

Claim batches may share Source input. The LLM batch runner performs the
partitioning. When cumulative state grows, it repartitions only the unfinished
claim work, retaining its processed prefix and parent results; work items that
have exited are not carried further. When a chain step with several work items
fails for capacity (`deadline_exceeded`, `input_capacity_exceeded`, provider 413
`payload_too_large` or output truncation with `finish_reason=length`), the runner
splits the unfinished cohort in half and continues each half from the same
position with its own state. When the step holds a single Claim over several
ReadingGroups, the runner halves the ReadingGroups first. Every row of a step
is validated on its own: a valid row advances its Claim, and the rejected Claims
re-read the same step, from the same position with their unchanged state, in one
re-ask that names each error, then rejoin the cohort. A step whose output cannot
be read into rows even after one correction is split by Claims. A Claim that
still fails is a typed failure. When that Claim's ReadingGroup alone exceeds capacity, Support
maps it to `UNRESOLVED(capacity)`, and when its output alone stays invalid, to
`UNRESOLVED(invalid_response)`, both KEEP; an execution error leaves the Source
Unit revision uncommitted and the next sync retries it. A
frozen LiteLLM capacity snapshot budgets the actual transport, schema, images,
per-claim output references, cumulative state and correction reserve. Neither
output truncation nor smaller business scopes substitutes for execution coverage.
An indivisible representation or cumulative state beyond available capability
remains an explicit execution limitation, not a successful or semantic judgment.

Cloud impact: the ordered read and its partitioning are shared OSS code driven by
LiteLLM metadata, `MEMFORGE_LLM_MAX_*` and `request_timeout_s`, which Cloud
already supplies from its environment for `sap/` routes. Durable work records use
the existing derivation store methods that HANA implements.

`support_assess` records persist exact model inputs/results under the existing
Source derivation. `support_finalize` is a program-generated completion receipt
binding complete coverage and all assessment dependencies; it is not another LLM
call. Existing atomic lifecycle/stale guards consume that receipt. Changed model
work contracts invalidate their own reuse, without changing authority 5, extraction v9 or Support v2 merely for execution.
Compiler 4 independently changes structural boundaries as described in ADR 0030.
Legacy stage records remain immutable history. See ADR 0017 for storage ownership.

Claim Extraction scope is defined in [Decision](#decision) item 2 and implemented
as `revision-input-v7`: `plan_projection_evidence_work` computes Primary authority
only, and each ReadingGroup that holds authorized Primary is one LLM batch runner
item, read with its reading context demoted to Required-only. The runner packs
items into requests by actual capacity; each planned request is staged as one
derivation batch and, when executed, is still split in half on a capacity or
deadline failure, or on output the client cannot read even after its one
repair. An item that alone exceeds capacity, or whose output alone stays
invalid, is skipped with a diagnostic ([Capacity and non-goals](#capacity-and-non-goals)). Claim Extraction and Support Assessment share
catalog, budget and durable execution primitives, while retaining distinct
semantic duties. Cloud impact: extraction scope is shared OSS
planning code; Cloud upgrades the pin with no configuration or HANA change.

## Local unresolved claim relationships

Implemented for Cloud issue #505 in `pipeline/support_relation_coordinator.py`.

Claim Reconciliation returns one completion row per admitted Candidate and does
not repeat Support or Evidence selectors. Equivalent and contradicts edges are
combined with Support by the coordinator table in
[Support and Relation coordination](#support-and-relation-coordination). A
refinement relation that conflicts with the Support result, or uncertain relation
material, is unresolved locally. Candidate admission
already owns whether supplied current Evidence entails the challenger, including
table column associations; relation classification cannot repair candidate text.

For an unresolved pair, the coordinator consumes the candidate and emits a bare skipped
NOOP for the incumbent, preserving Support, Evidence and validation baseline.
If either participates in other related pairs, preserve the related component
together so a shared candidate cannot escape as ADD or drive another destructive
operation. An old Memory without an edge never spreads this uncertainty. Exclude that component
from conditional refinement work; independent candidates and incumbents continue.
The existing skipped-Support proof and stale guards remain the only Plan mechanism.
The coordinator's single re-check and the pending coordinator Review rules are the
only additions; there is no new Review state and atomic commit ownership is
unchanged. Cloud impact: shared OSS coordinator code; Cloud upgrades the pin.


## References

- [Existing fragment and lifecycle contract](0030-compile-revision-pinned-evidence-fragments.md)
- [Existing asynchronous relation contract](0009-bound-cross-document-relation-discovery.md)
- [Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html): durable follow-up work and idempotent delivery, not conflict-free publication.
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents): start with bounded workflows and justify additional agentic complexity through evaluation.

## Directional support and overlapping scope

The deployed fixed-fixture evaluation exposed a distinction the original prompt
left ambiguous: L3 asks whether current evidence entails the old proposition,
not whether the new and old rules are equivalent or enumerate the same complete
set of requirements. A stronger necessary obligation over the same population
can preserve a weaker necessary obligation. Do not infer sufficiency or
exclusivity absent from the old claim; explicit sufficiency, scope, time and
modality remain material. Restricting the population cannot establish a prior
universal claim.

Likewise, an exception can contradict a universal rule on their overlapping
scope; narrower scope alone does not make incompatible assertions a refinement.
The shared relation definition uses this intersection, while cross-source
mutation still requires the existing Review/Source Authority gates. Target
(#505): Relation does not see Support results, so `SupportRelationCoordinator`,
not the Relation model, detects an entailment chain that contradicts L3 (current
evidence supports the new claim and the new claim preserves the old claim, but
L3 rejected old support). For an equivalent edge it applies the table's targeted
re-check; a REFINES edge that conflicts with the Support result is unresolved
locally. It never manufactures a supported verdict or falls back to delete/add.

This clarification advances only the Support/claim semantic contracts and the
shared relation-classifier identity. Compiler, extraction, representation,
Support storage and historical Evidence formats remain unchanged. Frozen
failures are retained alongside new necessary/sufficient and scope holdouts;
prompt improvement does not establish population accuracy.


### Revision identity is continuity, not equivalence

L4's same-item condition means continuity of an independently maintained fact,
rule or decision about its subject and concern across a revision. It is distinct
from L6 equivalence, which requires identical truth conditions. A compatible added
requirement can preserve the knowledge item's identity while making the current
proposition stronger. Complete replacement text must already state the old meaning
and the refinement; adding information does not itself make that text incomplete.

The target relation contract names the newly admitted claim `challenger` and the
active Memory `incumbent`; it does not reuse the former ambiguous `candidate_*`
revision-proof fields. `REFINES(challenger, incumbent)` means the same knowledge
item is stated more specifically in that direction. Lifecycle policy still rejects
whole-incumbent replacement when the challenger narrows population, time or scope
and therefore cannot preserve the incumbent's complete truth conditions.
Unsupported old claims need not be negated: loss of universal coverage alone does
not establish contradiction with a compatible subset rule.

Acceptance must evaluate the complete revision conjunction and the resulting
coordinator action. Correct Support, relation and preservation fields alone do not
prove an eligible UPDATE. Frozen failed results remain evidence even when a later
prompt/schema version corrects them.

## Same-Unit Relation execution

Target contract, tracked by Cloud issue #505. The request and output are
implemented as `claim-revision-v8-sparse-catalog`, described in
[Sparse claim catalog](../design/sparse-claim-catalog.md).

Same-Unit Relation keeps the sparse output shape: one completion row per
`ADMITTED` Candidate, listing only meaningful relations; omitting an old Memory
means "no relation proposed", while a missing Candidate row is a technical
failure. The model input holds the Candidate, its current Evidence and the Claims
of same-Unit old Memories. It holds no Support result or reason and asks for no
evidence entailment judgment. Catalog text is encoded as shared state, so model
input does not repeat claim bodies per request. A pairwise classifier backend for
this task would be a separate contract that needs its own evaluation.

Batching remains a computation detail of the LLM batch runner. It cannot
cap the catalog, change atomicity, add business states or weaken same-source
incumbent coverage. Existing Source Authority, Support Assessment,
DestructiveValidation, stale guards and atomic commit remain mandatory; even
`CONTRADICTS` is not a lifecycle action.

Cross-document relation discovery remains a different contract: existing
access-filtered hybrid retrieval generates bounded K pairs and a classifier labels
them. Full-workspace N × M is not required, and a missed cross-document relation
cannot authorize destructive mutation.

Completed Relation work binds the Candidate and catalog manifest, context digests,
executor/model/contract identity and budget. Retries compute unfinished transport
partitions but cannot reuse judgments under changed input. SQLite and HANA still
require complete work before applying the Source projection/Lifecycle Plan.

Cloud impact: removing `current_support` and the entailment status changes the
shared prompt and schema and requires a successor claim revision contract
identity. Cloud upgrades the pin; HANA needs no change because work records use
the existing derivation store.

## Complete Support requests and model-facing identifiers

Target contract, tracked by Cloud issue #505; execution through the LLM batch
runner.

Support Assessment reads the reading order for the complete fixed-claim cohort
under one validation baseline. Only a measured input, image, mandatory
response-row, or cumulative-state capacity failure invokes transport
partitioning. Rows are accepted one by one and the rejected ones re-asked once
together; a request with several work items that fails for capacity, or whose
output cannot be read into rows after one correction, is split in half and
resent, and a step for a single Claim over several ReadingGroups halves its
ReadingGroups first on a capacity failure (ADR 0036, decision 13). A work item
whose single ReadingGroup alone exceeds capacity is `UNRESOLVED(capacity)`, and
one whose output alone stays invalid is `UNRESOLVED(invalid_response)`, with
diagnostics and KEEP; an execution error at one item leaves the Source Unit
revision uncommitted. There is no packing score and no
mode selection. The order itself is defined in
[Ordered current-revision reading](#ordered-current-revision-reading).

A step inside the first part of the order returns only `witness_delta`. From the
step that completes the first part onward, a step's response is `SUPPORTED(...)`
for a work item that has found complete Support, which then exits, or
`witness_delta` otherwise; the step that reads the
last ReadingGroup returns final `SUPPORTED(...) | UNSUPPORTED`. The response remains one
independent judgment per work item with only its selected
Primary/Required refs. A hypothetical claim-by-every-fragment response is an output
allowance estimate, not a required output shape. That allowance saturates at the
route's generation capacity; the minimum serialized row coverage must also fit.
No Evidence list is silently shortened to satisfy this budget. Provider truncation
(which the runner treats as a capacity failure and splits), refusal, invalid refs
and incomplete task coverage cannot complete work, even when
the response text is syntactically valid JSON. Successful parsing alone is not
successful execution. The existing bounded correction and fail-closed lifecycle
boundary remain authoritative; no new semantic states or scheduler are introduced.

Support requests expose stable typed aliases: WRK for assessment tasks, PRM for
Primary-eligible current Evidence, REQ for Required-only current Evidence and HIS
for historical material. PRM Evidence may also be selected as Required. Prefixes
identify namespaces, not relationships between matching numeric suffixes. Numbers
use a minimum four digits and expand without truncation. Aliases remain stable
across every partition and cumulative state in the same assessment. Encoding and
decoding affect only identifier fields; source text and reasons are never rewritten.
Canonical Evidence coordinates and stored work results retain their internal IDs.
Implementation must allocate successor Support-work and revision-input contract
identities for the ordered read and witness schemas; old completed work
is never reinterpreted as new-wire output. Evidence compiler and lifecycle
semantics are unchanged.


### Compact Support judgments

Final Support judgments use discriminated variants. `SUPPORTED` carries work ID,
status and complete Primary/Required refs; `UNSUPPORTED` carries only work ID and
status and cannot carry selectors. The final model wire result does not carry
generated prose. During streamed assessment, the model returns only current
`witness_delta` additions; application code validates and monotonically unions
them into supporting/opposing sets. Each next call rehydrates that union with exact
current text and Primary eligibility. Partial coverage, a single ReadingGroup beyond capacity and output that
stays invalid for one item are application-owned `UNRESOLVED(reason)`, not a
semantic model status; an execution error leaves the Source Unit
revision uncommitted. Application diagnostics may retain
a bounded decisive basis outside the final wire result. This supersedes the
assumption that every successful item needs a
generated reason. The canonical stored result retains a deterministic success explanation; downstream
lifecycle decisions continue to use status and resolved Evidence, never that sentence
as additional authority. Cumulative assessment carries grounded Evidence witnesses,
not an unbounded narrative of unrelated facts. Final status cannot overwrite or forget
an unresolved earlier opposing witness.

Every requested work item must still be returned. Omission is not approval, unchanged
Support or coverage. Reference lists are never truncated to meet an output target.
The wire schema is distinct from the canonical stored result; cached canonical results
are validated without decoding aliases again. `support-delta-assessment-v3` and
`revision-input-v5` isolate the changed prompt/schema semantics from historical work.
Validation diagnostics identify the work, attempt, rule and expected item count without
logging source text or provider response bodies. A correction remains bounded and
complete; partial-result repair is not introduced by this decision.

Anthropic's [latency guidance](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-latency)
recommends reducing unnecessary output. Output reduction is measured separately from
end-to-end latency; input processing and provider waiting prevent proportional latency
claims from output token counts alone.

The earlier source-neutral reading and cost-selection amendment uses
`revision-input-v6`. That identity is included directly in the inference
capability hash and the Source derivation's `semantic_input_policy`; completed
v4/v5 work is not reinterpreted. The extraction contract remains
`projection-extraction-v9`, Support remains `revision-support-v2`, compiler
contract remains 4, authority policy remains 5, and the model presentation policy
is 4. The planner amendment changes request scope and presentation identity only;
it does not migrate stored Evidence or create a lifecycle version.

Implementing the target contract must allocate
successor semantic-work and input-policy identities for exact correspondence,
witness state, the ordered Support read, changed-structure and first-import
streaming extraction, candidate admission (`candidate-admission-v1`, and
`candidate-admission-v2` under [Complete support](#complete-support)), the Relation
input change (`claim-revision-v8-sparse-catalog`), the coordinator and
DestructiveValidation. Reading per ReadingGroup with the shared reading context
and the Unit Title uses `revision-input-v7`, `revision-support-v5`,
`support-ordered-reading-v3`, `change-impact-v2`, authority policy 6 and model
presentation policy 5; the extraction contract stays `projection-extraction-v9`
and the compiler stays 4. [Complete support](#complete-support), with prior
Evidence offered only as selectable candidates, gives the current contracts
`revision-support-v7` and `support-ordered-reading-v5`. Completed work under an
earlier contract is never reinterpreted under a later one. Exact successor numbers
are assigned with the implementation so they cannot collide with independently
released work; no stored Evidence or lifecycle schema migration follows merely
from this contract change.
