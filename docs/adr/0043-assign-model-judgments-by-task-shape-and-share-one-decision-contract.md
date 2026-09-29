# Assign model judgments by task shape and share one decision contract

Status: Accepted

Date: 2026-09-28

Amended: 2026-09-29, see [Amendment: shared context and equivalent results](#amendment-2026-09-29-shared-context-and-equivalent-results).

## Context

Every model step in the Source lifecycle runs on one Structured LLM. The
[semantic judgment design](../design/semantic-judgment-execution.md) and
[ADR 0036](0036-separate-semantic-work-from-inference-executors.md) separate
`GenerationWork` from `JudgmentWork` and allow a classifier adapter
(TypeSafe/Jev or a small-parameter LLM) for closed-label judgments. They sort
steps by output shape, which files candidate admission and Support Assessment
as generation although both return only choices, and several contracts still
ask the model for text or a self-reported confidence:

- candidate admission returns a `reason` that nothing reads;
- same-Unit Sparse Relation returns a `reason`, stored as the Lifecycle Review
  planner reason and a Memory's replacement reason, and
  `incompatible_assertions`, checked only for being non-empty;
- the same-Unit pair review returns a direction, a proof text and a `reason`,
  and only its `contradicts` label is used;
- cross-document relations return a `reason` stored with the relation and shown
  in the admin UI, the API and MCP `relations[]`;
- entity adjudication returns a `reason` and a `confidence` that must reach 0.9;
  the prompt never asks for the confidence, so a match without one is dropped;
- agent-session authority returns a required `reason` that nothing reads, and an
  `is_authoritative` flag that repeats its `authority_kind`;
- Claim Extraction and managed agent patches return a `confidence`, and patches
  a `reason` stored as the replacement reason.

`Memory.confidence` is read only for display, hashing and one unused query
(`get_source_support_candidates`); no lifecycle, ranking, filtering or hook
decision reads it. Admission reserves about 250 output tokens per Candidate for
its unread reason.

Evaluating the cross-document relation classifier on EU12 dev showed that the
definition in `CROSS_DOCUMENT_RELATION_RULES` is already general and that the
errors come from the model not applying it. Two points the definition leaves
open (partial overlap and inferred conflict) are settled here.

## Decision

### Three kinds of model work

Every model step is one kind, decided by what the model must do, not by the
shape of its output.

| Kind | The model must | Runs on |
|---|---|---|
| Generation | write text that does not exist in the input | the main model |
| Reasoning | choose, but find the relevant items in a list the program cannot narrow, carry state or dependent answers across items, or decide whether several Evidence parts together entail a claim | the main model |
| Decision | answer one fixed question about one item the program supplied in full, with closed options, independently of every other item | the decision model once the task passes its evaluation, otherwise the main model |

| Step | Kind | Why |
|---|---|---|
| Claim Extraction (with selector correction) | Generation | writes the claim, its dates and entity names |
| Managed agent patch | Generation | writes the replacement claim |
| Candidate admission | Reasoning | complete support over the selected Evidence parts uses the same definition as Support Assessment (`COMPLETE_SUPPORT_DEFINITION`), and same-round duplicates are found by scanning every Candidate of the round |
| Support Assessment | Reasoning | ordered reading with carried witnesses; Primary and Required are one dependent choice |
| Same-Unit Sparse Relation | Reasoning | finds the few related old Memories among all of the Unit's, which similarity cannot narrow inside one document; refinement is decided by entailment and drives SUPERSEDE, DELETE and UPDATE |
| Same-Unit pair review | Decision | the program supplies two refinements of the same old Memory; do they contradict |
| Change Impact | Decision | one ChangeBundle and one fixed claim; `affected` or `unaffected` |
| Cross-document relation | Decision | the program retrieves each pair; one label per pair |
| Entity adjudication | Decision | one mention and its supplied candidates; pick one or none |
| Agent-session authority | Decision | one user message with its context; one authority kind |

Admission and Support Assessment run on the same model: a Candidate admitted
under one reading of complete support must not be retired by a different
reading at the next revision.

Out of scope: retrieval rerank, a ranking task for a dedicated reranker that
stays disabled by default and unused by Cloud, and the offline semantic judge,
which is evaluation tooling rather than a product step.

### Model outputs are the knowledge or the choice, nothing else

A Generation contract returns text only in the fields that are the generated
knowledge (the claim, its validity dates, entity names). A Reasoning or
Decision contract returns only values the program defined: labels, booleans,
and refs or IDs from lists the request supplied. No contract returns an
explanation or a model-reported confidence. Records that used a model reason
keep their program-owned text (for example the fallback replacement reason);
people read the Memories and the Evidence.

`Memory.confidence` is removed with its API, MCP, admin UI and storage fields,
and with the unused `get_source_support_candidates`.

### One decision contract

Every Decision step implements the same contract, whatever model answers it:

- **Task.** A task has a name, a contract version that is part of its work
  identity, one fixed question and a closed list of options. One option is the
  task's safe answer, which is also the answer for an uncertain case: `none`
  for cross-document relations, no candidate for entity adjudication,
  `not_authoritative` for agent-session authority, `contradicts` for the pair
  review (it blocks the refinement) and `affected` for Change Impact (it sends
  the claim to Support Assessment).
- **Item.** One item is the complete input the program supplies for one
  question. Items are independent. When an item's input is too large for one
  request and the task allows it, the program splits the input and combines the
  answers by the task's rule (Change Impact: any `affected` wins).
- **Answer.** Exactly one option per item, nothing else. An ID outside the
  supplied candidates is a rejected row, not the safe answer.
- **Meaning.** What each option means and what the program does with it belong
  to the task. Relation direction (`updates` needs known Evidence dates that
  order the pair) stays a program rule
  ([ADR 0037](0037-record-cross-document-conflicts-as-relations.md)).
- **Execution.** Requests go through the LLM batch runner. How items are packed
  is the adapter's concern, within the shared context rule of the amendment
  below: an LLM adapter asks for many items per request; a Jev adapter sends
  one state with one question per item. A backend without calibrated
  probabilities answers with its option as returned. A backend that reports
  calibrated probabilities applies the calibrated cutoffs of the amendment
  below and otherwise returns its highest-probability option.
- **Failure.** An item without a valid answer after the runner's re-ask is an
  execution failure that the task routes as today. A failure is never an
  option.

### Cross-document relation rules

`CROSS_DOCUMENT_RELATION_RULES` keeps its four same-situation conditions and
adds:

- decide whether the statements are about the same situation before deciding
  whether both can hold;
- when statements overlap only in part, they conflict if the part they share
  cannot hold for both, and a shared part never makes them equivalent;
- compare only what the statements state; a conflict that has to be inferred
  from either statement is not a relation;
- the kind of a statement (what should be, what happened, what was planned or
  decided) is read from what it says, not from its memory type.

The classifier returns only the label. There is no per-label confidence
threshold.

### Decision model

A Decision task moves to the decision model only after it passes its
evaluation; the passed tasks are registered with their contract versions in
code. The decision model is one setting, applied to every registered task; when
it is not set, every task runs on the main model. There is no per-task backend
setting, no per-item routing and no fallback between models.

A task is evaluated on held-out labeled cases and passes when, against the main
model on the same cases, its safe-answer recall and its precision on every
other option are no lower. A contract change that alters behaviour on any model
needs its own evaluation before it ships: removing the entity confidence
cutoff turns every returned candidate into a persistent alias, and removing
Sparse Relation's reason removes text written before `revision_assessment`.

On Cloud the decision model is a small model on a `sap/` route, for example
Claude Haiku 4.5 once SAP AI Core offers it. TypeSafe/Jev is an optional OSS
adapter behind the same contract; Cloud does not send Source content to it.

## Consequences

- Admission, Sparse Relation, the pair review, cross-document relations, entity
  adjudication, agent-session authority and managed patches lose their text and
  confidence fields, and each bumps its contract version. Entity adjudication
  and agent-session authority gain a version; the pair review's version joins
  its work identity. Derivations use a new version at their next processing;
  existing cross-document relations are re-run by an operator.
- Admission's output shrinks from about 320 to about 70 tokens per Candidate.
- Agent-session authority returns only `authority_kind`.
- A pending Review and a replaced Memory no longer show a model reason; they
  show the Memories, the label and the Evidence.
- Unused per-task model settings (`RetrievalConfig.entity_model`,
  `entity_timeout_s`, the unused `rerank_model` default) and `entity_filter.py`
  are deleted, and no per-task backend setting is introduced.

## Cloud impact

- HANA drops `CROSS_DOCUMENT_RELATIONS.REASON` (it also holds reasons converted
  from human Reviews, which are dropped with it), `MEMORIES.CONFIDENCE` and
  `AGENT_CLAIMS.CONFIDENCE` through migrations, and the column lists, MERGE,
  join-back queries and row mappings that name them. The storage protocol
  method `apply_agent_claim_source_projection_lifecycle` loses its `confidence`
  argument, and Cloud's `get_source_support_candidates` is deleted. Columns that
  also hold program text (`LIFECYCLE_REVIEWS.REASON`,
  `MEMORIES.REPLACEMENT_REASON`) stay and stop receiving model text.
- The decision model is one deployment variable next to
  `MEMFORGE_AICORE_ENRICHMENT_MODEL`, read by `prepare-deploy.sh` and the
  `sap-internal` profile, exported by `cf_env_aicore.py` and passed through
  `proxy/external_runtime.py`. It is empty by default and needs no database
  row. The `sap/` transport choice applies to it as it does to the main model.
  It is the one configuration addition this ADR allows beyond LiteLLM metadata,
  `MEMFORGE_LLM_MAX_*` and `request_timeout_s`.
- Nothing runs on a second model until a task passes evaluation on Cloud's own
  labeled cases and the variable is set.
- The admin UI relation card and MCP relation output drop `reason`; search and
  Memory output drop `confidence`. An older plugin ignores the missing fields.

## Amendment 2026-09-29: shared context and equivalent results

### Shared context

A Decision task may declare a shared context: input that every item of one
request is judged against. For cross-document relations the shared context is
the subject, the challenger Memory, and each item is one candidate.

- A request holds exactly one shared context, stated once, and one question per
  item. Items with different shared contexts never share a request; the batch
  runner still packs and splits one context's items by capacity, and every
  split request states the context again.
- Every question asks only for the relation between its own item and the
  shared context, with one fixed wording.
- The instruction states that items repeating one another say nothing about
  the shared context: two candidates that state the same thing tell nothing
  about the subject, and a candidate is `equivalent` only when it and the
  subject state the same knowledge.

This is the TypeSafe/Jev shape (one state, one question per item), and the LLM
adapter renders the same shape. A model that sees several statements side by
side without this rule reads similarity among the candidates as similarity to
the subject.

Measured on EU12 dev with Claude Sonnet 4.6 (3,537 pairs of 60 challengers in
two workspaces; 282 pairs labeled the same by two reviewers, 8 of them true
relations):

| Rendering | False relations among 274 `none` pairs | True relations found (of 8) | Input tokens vs grouped |
|---|---|---|---|
| Grouped: each challenger with its candidates listed under it (v3 rules) | 149 | 6 | 1.00 |
| One self-contained pair per item, many items per request (a draft of the v4 rules without the illustrated kinds and occurrences and with the v3 `contradicts` wording) | 16 | 6 | 1.54 |
| Subject stated once, one question per candidate (v4 rules) | 2 | 4 | 1.01 |

The subject rendering removes nearly all false relations at the grouped token
cost. It finds fewer of the 8 reviewed relations; the contract prefers `none`
when unsure because a false relation warns every reader of both Memories, while
a missed one only omits a hint.

### Relation rules

Contract `cross-document-relation-v4` renders the subject and questions above
and sharpens `CROSS_DOCUMENT_RELATION_RULES`:

- the kinds of statement are illustrated (what should be: a requirement,
  design, rule or expected behaviour; what happened: a reported defect, test
  result, incident or observed behaviour);
- different events, tickets, incidents, test runs or cases are different
  occurrences. They illustrate what an occurrence is; they are not scope
  dimensions, and the contract still lists none;
- partial overlap follows the rule above;
- `none` includes a statement that adds a fact, condition, step or outcome the
  other does not state; `equivalent` requires each statement as a whole to state
  everything the other states, differing only in wording; `contradicts` requires
  the two statements to directly state incompatible things.

The input is unchanged, so evaluation cases pinned under `v2` and `v3` are
replayed under `v4` (`CROSS_DOCUMENT_RELATION_INPUT_VERSIONS`).

### Relation evaluation replays production packing

A relation evaluation shows the classifier what discovery shows it. The
measured false relations came from candidates judged against one another inside
one request, which a case holding one pair cannot reproduce. Relation group
cases (`cross_document_relation_group_v1`) pin one challenger with every
candidate discovery asked about for it, in discovery's order, and labels for
some of them; replay sends the whole group through the production classifier
and batch runner and scores the labelled candidates, while relations given to
unlabelled candidates are counted for labelling. The group set is the gate for
a change of the relation prompt, rendering, packing or model: its false
relation count and `none` recall must not get worse.

### Search annotates an equivalent pair

Search returns both Memories of an `equivalent` pair, and each carries the
relation that names the other; neither is left out of the results. A false
`equivalent` would remove a different Memory from the results, which costs far
more than showing a repeated statement. Hiding one of the pair waits until the
measured precision of `equivalent` justifies it. `updates` ordering and the
relation notices stay as ADR 0037 specifies.

### Re-running discovery

A completed discovery run replaces every relation the classifier recorded for
its discovery work: pairs it judges receive its labels, and a relation the work
recorded for a pair it no longer judges, because the pair is no longer a
candidate, is removed. A run that finds its work obsolete, because the
challenger or its evidence in the work's Source Unit is no longer current,
removes the work's classifier relations the same way. Relations a person
confirmed for the current contents, relations another challenger's work
recorded, and dismissals stay. Re-running all completed work
(`POST /api/v1/relation-discovery/work/rerun` with `{"state": "completed"}`,
and `{"state": "exhausted"}` for exhausted work) therefore leaves exactly the
relations `v4` decides.

### Cloud impact

Cloud reads this contract through its pinned OSS version; the prompt, rules
and search change arrive with the pin. The HANA
`complete_relation_discovery_work` must remove the classifier relations of the
completing work before it applies the run's labels, and
`obsolete_relation_discovery_work` must remove them in the same transaction
that marks the work obsolete, as SQLite does, or a re-run leaves relations from
pairs it no longer judges; an index on
`CROSS_DOCUMENT_RELATIONS.DISCOVERY_WORK_ID` keeps that removal cheap. No
storage protocol signature, configuration or `proxy/external_runtime.py` call
site changes. Existing relations are re-run by an operator. Relation group
cases are stored in each workspace's HANA evaluation store like other cases,
are seeded through the proxied admin route and run on the Cloud evaluation
worker through the pinned OSS version.

## Amendment 2026-09-29: calibrated probabilities

A backend that reports calibrated option probabilities, such as TypeSafe Jev
(trained for calibration; TypeSafe asks for thresholds calibrated on the
user's own domain and a pinned model version), may apply a cutoff per task and
option: when the probability of the highest option is below that option's
cutoff, the answer is the task's safe answer. The contract output is unchanged,
one option per item, and a backend without calibrated probabilities (the LLM
adapter) answers as before.

- A cutoff is a named contract constant bound to the task, its contract
  version and the backend model version. It is set on a calibration set and
  verified on a held-out set that took no part in setting it; a change of any of
  the three means calibrating again.
- A cutoff never routes an item to another model and never turns a failure
  into an option.
- No cutoff is set yet. On EU12 dev, Jev with the v4 rules answered 13
  relations on 282 labelled pairs with 6 correct; a cutoff of 0.7 on the same
  pairs kept 6 with 5 correct. Eight true relations are too few to both set and
  verify a cutoff, so cutoffs wait for a Jev adapter and a larger labelled set.

Cloud impact: none. Cloud's Decision tasks run on `sap/` LLM routes, which
report no calibrated probabilities.

## Amendment 2026-09-29: model input changes are replayed before release

### What happened

Commit `87e665f5` put the Unit Title into Unit revisions as each Unit's first
Observation. Every existing Unit met it as added content at its next revision,
and Change Impact read it as a change. On EU12 dev, 356 of payroll_agent's 369
Change Impact requests since 2026-09-26 showed only the added Unit Title; 2,294
of their 2,648 claims were judged `affected` and read again in full by Support
Assessment. A line in the Change Impact prompt saying what the Unit Title is
fixed 10 of 47 replayed requests. The Unit Title is now reading context carried
by the projection and no part of a Unit revision, and revisions are compared in
the current representation only
([ADR 0034, The Unit Title](0034-unify-incremental-support-and-claim-assessment.md#the-unit-title)).

The unit tests of that change passed: they checked that each step behaved as
designed, not how much model work existing Units would send, or what the
model would answer.

### The rule

A change that alters what a model reading shows for existing Units (a new
Observation or representation, a compiler or rendering change, reading context
or a prompt change), or how revisions are compared, is replayed on stored
production requests before release. For every task the change reaches, its PR
states:

- the requests and items the next revisions of existing Units will send,
  counted from the stored revisions the change reaches;
- the changed answers on a replayed sample, next to the answers of the current
  contract and against labelled items where they exist.

This measured load is the one-time load ADR 0034 asks such a change to state.
For the Unit Title as reading context, the replay covers the Change Impact
requests that showed only the added Unit Title (their Units must now rebind
with no model call), a sample of Units that stored a Unit Title Observation
(each a pure rebind), Claim Extraction and Candidate Admission requests on Jira
Units (claims that state the Unit's key are kept) and a Support Assessment
sample (answers about names do not change); the relation group baselines are
re-run after release. Payloads recorded before this change have no Unit Title,
and those since 2026-09-26 hold it as an Observation, so a replay of the stored
payload would show neither what the change shows nor compare as it does. The
replay therefore projects each sampled Unit again from its stored input
(`SourceUnitInput`) through `project_source_item`, with the Unit revision the
recorded request read as the prior revision, and runs the production planner and
prompts on that projection.

### Cloud impact

The replay runs against a Cloud workspace from its worker process in a
read-only HANA transaction, with a journal store that refuses writes. The rule
changes no storage protocol, HANA schema, configuration or
`proxy/external_runtime.py` call site. Contract identities raised by a replayed
change arrive with the pin, and work completed under earlier identities is
never reinterpreted. Derivation attempts staged before the upgrade are never
resumed: `_resume_source_derivations` supersedes pending and retryable attempts
under another extraction contract and skips completed ones. For the Unit Title,
no staged target revision that holds a Unit Title Observation is applied after
the upgrade.

## Alternatives considered

- **Per-question answers for relations** (same object, same scope, same kind,
  same occurrence, both can hold). Rejected: more output per pair and a second
  place that restates the rules.
- **Keep a reason for readers.** Rejected: no program rule reads it, a decision
  model cannot produce it, and readers see both Memories and the Evidence.
- **Per-task backend settings.** Rejected: settings grow with every task, while
  eligibility is a property of the evaluated contract.
- **Jev as Cloud's decision model.** Rejected for Cloud: it is not reachable
  through SAP AI Core and would send SAP Source content to an external service
  hosted in the US.
