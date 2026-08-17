# Efficient offline agent evaluation scope for issue #258

Date: 2026-08-17

Status: Research recommendation. The official facts and the proposed MemForge
decisions are separated below. This note does not amend ADR 0025 by itself.

## Question

What is the smallest offline agent-evaluation system that can reliably catch
MemForge quality regressions without turning every pull request into an
expensive, slow, privacy-sensitive full Source sync?

The design must cover:

- immutable case and dataset lifecycle;
- representative and failure-driven sampling;
- deterministic checks, LLM judges, and human annotation;
- judge calibration and human agreement;
- exact replay boundaries;
- caching and incremental execution;
- statistically honest release gates;
- CI versus scheduled execution;
- content authorization and retention; and
- the role of Langfuse datasets, experiments, scores, and annotation queues.

## Executive recommendation

Implement one provider-neutral, task-level replay loop in the MemForge product
boundary:

```text
authorized online event
  -> immutable AgentEvaluationCase
  -> immutable cohort snapshot
  -> candidate task execution
  -> code / LLM / human AgentAssessments
  -> paired baseline comparison and release decision
  -> optional Langfuse experiment + score projection
```

Start with the existing Source Unit derivation and lifecycle-reconciliation
seam. Do not replay provider collection, the scheduler, an entire Source sync,
or external writes. The case must pin the exact inputs that reached the seam,
including the accepted source revision and the incumbent/gate manifest when
reconciliation is in scope.

Keep two cohorts separate in every report:

1. a **failure-regression cohort**, containing accepted historic failures and
   high-risk edge cases; and
2. a **representative control cohort**, sampled from ordinary traffic by stable
   source and workload strata.

The first answers “did a known bad behavior return?” The second answers “did
overall behavior shift?” Combining them into one pass rate would make neither
answer interpretable.

Use code for objective invariants, an LLM judge only for a named semantic
criterion that code cannot decide, and humans to create or adjudicate accepted
ground truth. Langfuse is the experiment and annotation workbench; the
authoritative case, accepted label, run, and gate remain in MemForge so offline
evaluation still works when Langfuse is disabled or cannot receive protected
content.

## Official and primary-source findings

### Evaluation scope should follow the nondeterministic task boundary

OpenAI's current evaluation guidance recommends task-specific tests that
reflect real-world distributions, mining logs for cases, automated scoring
where possible, continuous evaluation, and calibration of automated metrics
against human feedback. It calls out biased datasets that do not reproduce
production traffic and uncalibrated automated metrics as anti-patterns. It also
recommends typical, edge, and adversarial cases and expert human labellers.
([OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices))

For agents, OpenAI distinguishes trace inspection while behavior is still being
debugged from datasets and eval runs once repeatability is required. Trace
grading helps localize workflow failures; repeatable datasets are the unit for
benchmarking changes over time.
([OpenAI agent evaluation guidance](https://developers.openai.com/api/docs/guides/agent-evals),
[OpenAI trace grading](https://developers.openai.com/api/docs/guides/trace-grading))

These sources support evaluating the smallest meaningful workflow boundary,
not assuming that a black-box final answer or an operationally complete full
sync is the only useful evaluation unit.

### Deterministic checks, semantic judges, and humans have different jobs

Langfuse recommends code evaluators for objective checks such as schema,
parseability, exact match, tool calls, and business rules, and LLM-as-a-Judge
for semantic or subjective criteria. Both can score controlled experiments.
([Langfuse code evaluators](https://langfuse.com/docs/evaluation/evaluation-methods/code-evaluators),
[Langfuse LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge))

OpenAI recommends comparison, classification, or scoring against explicit
criteria rather than unconstrained generation when using models as evaluators.
Its grader guidance says grader prompts should be tested against model and
trusted-human answers with ground-truth grades, extended with discovered edge
cases, and checked against expert evaluation for grader hacking.
([OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices),
[OpenAI graders](https://developers.openai.com/api/docs/guides/graders))

The original MT-Bench/Chatbot Arena study found that a strong judge could reach
high human agreement, but also documented position, verbosity,
self-enhancement, and reasoning biases. It found relative comparisons more
stable than absolute scores in some settings and used order swapping to expose
position bias.
([Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*](https://arxiv.org/abs/2306.05685))

MLflow's current first-party guidance independently recommends deriving judges
from real failure modes, aligning them with human feedback, and versioning the
judge. It distinguishes code scorers from LLM judges and supports ordinary CI
regression tests over datasets.
([MLflow judges and scorers](https://mlflow.org/docs/latest/genai/eval-monitor/scorers/),
[MLflow regression testing](https://mlflow.org/docs/latest/genai/eval-monitor/regression-testing/))

### Datasets and experiment runs must be versioned independently

Langfuse dataset items carry inputs, optional expected outputs, and metadata.
Production traces or observations can be promoted into dataset items. Every
item add, update, delete, or archive creates a timestamped dataset version, and
the SDK can fetch a specific version. Dataset schema changes do **not** create a
dataset version.
([Langfuse datasets](https://langfuse.com/docs/evaluation/experiments/datasets))

A Langfuse dataset experiment links each dataset item to a generated trace;
item evaluators receive input, output, expected output, and metadata, while run
evaluators compute aggregate scores. Experiment SDKs support run metadata and
bounded concurrency. Local-data experiments create traces but do not currently
create Langfuse dataset-run objects, so a managed Langfuse dataset is required
for its full comparison experience.
([Langfuse experiment data model](https://langfuse.com/docs/evaluation/experiments/data-model),
[Langfuse experiments via SDK](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk))

Langfuse's official CI integration can pin a dataset version, attach commit and
job metadata, and fail a workflow when experiment code raises a
`RegressionError`. This is a useful projection and execution option, but it
does not define the product's authorization, ground truth, or statistical gate.
([Langfuse experiments in CI/CD](https://langfuse.com/docs/evaluation/experiments/experiments-ci-cd))

### Annotation tools do not establish accepted ground truth by themselves

Langfuse Annotation Queues let domain experts score, comment on, and provide
corrected outputs for traces, observations, or sessions. Queues can be managed
through an API and can help align an LLM judge with human annotations.
([Langfuse Annotation Queues](https://langfuse.com/docs/evaluation/evaluation-methods/annotation-queues))

The documented queue workflow is an annotation workflow, not a MemForge
authorization, dual-review, disagreement adjudication, or ground-truth
acceptance protocol. Those semantics must remain explicit in the product
domain.

### Telemetry and evaluation content require independent privacy decisions

OpenTelemetry warns that telemetry can inadvertently capture personal or other
sensitive data, cannot decide what is sensitive for an application, and should
follow data minimization. Its guidance prefers not collecting sensitive fields
and describes filtering, deletion, and redaction when collection is necessary.
([OpenTelemetry handling sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/))

This applies even more strongly to an offline case, which may intentionally need
source content. A metadata-only online trace policy does not authorize copying
that content into an external evaluation dataset.

## Proposed MemForge decisions

Everything below is a MemForge design recommendation inferred from those
sources and ADR 0025. It is not a claim that OpenAI, Langfuse, MLflow, or OTel
requires these exact records or thresholds.

### 1. Use five small domain records

Keep the model explicit, but do not create a workflow engine:

| Record | Responsibility |
|---|---|
| `AgentEvaluationCase` | Immutable, authorized replay input and lineage promoted from one runtime fact or curated source |
| `AcceptedGroundTruthRevision` | Versioned, explicitly accepted rubric labels or expected propositions for a case |
| `AgentEvaluationCohort` | Immutable snapshot of case IDs, ground-truth revisions, roles, selection policy, and weights |
| `AgentEvaluationRun` | Candidate, baseline, prompt/model/contract, runner, evaluator-suite, code, and environment fingerprints |
| `AgentEvaluationResult` | One immutable case/evaluator output, error state, cost/latency, and protected artifact handles |

Do not add mutable status to a case body. If a case is corrected, create a new
case revision or successor linked to the old one. If a label changes, create a
new ground-truth revision. Old run results retain the exact case, cohort, and
label revisions they used.

The minimal case identity is deterministic over:

```text
case schema
+ task family
+ exact operation/replay manifest
+ protected artifact digests
+ promotion-policy version
```

Promotion from the same event and policy is idempotent. A later correction is
not silently folded into that identity.

### 2. Pin replay inputs, not current product state

An offline run must not reconstruct a historic case from current Memories,
current Source content, a retained Langfuse trace, or a fresh provider fetch.
It resolves authorized, revision-pinned artifact handles and verifies their
digests before execution.

Use task families with narrow replay contracts:

| Task family | Pinned input | Candidate output |
|---|---|---|
| `source_unit_derivation` | Exact normalized Source Unit revision, block catalog, prompt/schema/model contract | Candidate memories, evidence coordinates, admission/drop decisions |
| `source_unit_reconciliation` | Candidate output plus exact incumbent versions, Support fingerprints, gate state, and reconciliation contract | Relations, reviews, and lifecycle plan |
| `retrieval` (later) | Query, caller visibility, source/time predicates, pinned index snapshot or corpus revision | Ranked current Memory IDs and evidence |

The first implementation should cover the first two families because issue
#258 already records their lineage. Retrieval is a later producer, not a reason
to generalize the first runner prematurely.

The replay runner must be side-effect free:

- no provider collection or network write;
- no mutation of the workspace's live Memories or lifecycle state;
- no scheduler, lease, retry, or full-Source-sync orchestration;
- model calls only through an explicitly selected evaluation provider policy;
- all generated outputs written as evaluation results, never product state.

This keeps replay cheap and makes a failure attributable to the prompt/model,
deriver, reconciler, or evaluator instead of to unrelated collection/runtime
machinery.

### 3. Maintain separate development, calibration, and release roles

An immutable cohort gives each case one role for that cohort revision:

- **development**: visible cases used to debug code, prompts, and rubrics;
- **calibration**: human-labelled cases used to tune and validate an LLM judge;
- **release holdout**: cases not used to tune the candidate or evaluator;
- **sentinel**: a very small set of safety/correctness invariants always run in
  CI.

Assign related cases as a group, not independently. The grouping key should be
the stable source-unit/operation family, so near-duplicate revisions or recovery
executions cannot leak across development and holdout roles. Use a stable hash
of that group key for repeatable assignment.

Do not expose holdout expected labels to prompt optimization or judge tuning.
When the holdout becomes familiar through repeated debugging, freeze the old
cohort for historical comparability and create a new time-blocked holdout from
later accepted traffic.

### 4. Build both failure-driven and representative cohorts

Promote:

- every stable, actionable terminal failure reason;
- recovered or degraded executions;
- user-reported quality failures;
- cases created by an accepted bug fix;
- a deterministic, stratified sample of ordinary successes; and
- bounded edge cases for source type, language, input size, formatting, and
  reconciliation action.

Initially stratify on existing bounded fields: task family, source type,
reason/outcome, prompt/schema/contract version, input-size bucket, language
bucket when already known, and lifecycle action class. Do not add embedding
clustering, an LLM novelty classifier, or adaptive sampling until duplicate
case cost is measured.

Report the failure-regression and representative-control cohorts separately.
If a production-weighted estimate is needed, preserve the sampling probability
or stratum weight. An intentionally failure-heavy golden set must never be
presented as the observed production failure rate.

### 5. Evaluate in layers

Run the cheapest, most objective layer first and stop expensive work for cases
whose required deterministic contract already failed.

#### Layer A: deterministic invariants

Examples:

- structured output parses against the pinned schema;
- every admitted memory has a resolvable block/evidence reference;
- evidence coordinates are in the pinned Source Unit revision;
- no result references an unknown candidate or incumbent;
- reconciliation covers every same-source destructive incumbent;
- the lifecycle plan is internally valid and contains no orphan pass state;
- output and action counts reconcile with the plan.

These are ordinary code checks. Any evaluator error is `unknown/error`, never a
pass.

#### Layer B: semantic rubric

Use a judge only for criteria such as:

- whether every accepted memory-worthy proposition was retained;
- whether an extracted memory is genuinely supported by its cited evidence;
- whether two differently worded memories express the same durable claim;
- whether a proposed refinement preserves material incumbent facts.

Each criterion has a separate categorical result and evidence explanation.
Avoid one overall “quality” score. For the first slice, prefer labels such as
`pass`, `partial`, `fail`, and `cannot_assess` over an uncalibrated 1–10 scale.

For candidate-versus-baseline regression, pairwise comparison is useful, but
run it in both A/B orders or randomize order and record it. A disagreement after
order swap is `cannot_assess`, not an arbitrary win.

#### Layer C: human acceptance and adjudication

Humans create proposed labels independently of model scores for the calibration
overlap. Reviewers see the exact authorized case and rubric, not merely the
Langfuse score explanation. Disagreement is adjudicated into a new accepted
ground-truth revision with provenance; it does not overwrite either annotation.

### 6. Calibrate judges before allowing them to gate

Start with a small stratified overlap set sufficient to expose every rubric
label and important failure family. Two qualified annotators label the same
overlap independently. Report:

- raw agreement;
- a per-label confusion matrix;
- the count of disagreements and adjudicated changes; and
- an agreement coefficient suitable for the label shape when the sample is
  large enough to interpret it.

Do not hard-code a universal agreement number into the architecture. Approve a
criterion-specific threshold only after seeing the label prevalence and error
cost. A rare catastrophic label needs per-label recall, not just high overall
agreement.

Then lock a judge version containing:

- rubric and prompt digest;
- judge provider, exact model identifier, and parameters;
- input mapping and visible-content policy;
- output schema and label meanings;
- calibration cohort and results; and
- known limitations.

Evaluate the locked version on a release holdout. A later prompt, model alias,
rubric, mapping, or content change creates a new evaluator version and returns
to shadow mode. An LLM judge score never becomes Accepted Ground Truth.

### 7. Cache by immutable fingerprints and rerun only affected work

Separate candidate generation from scoring:

```text
candidate_output_key = hash(case + candidate + runner + execution policy)
assessment_key       = hash(candidate_output + evaluator version)
```

This permits:

- reusing an unchanged candidate output while iterating on a judge;
- reusing deterministic assessments when neither output nor evaluator changed;
- rerunning only semantic assessments whose rubric/model changed; and
- comparing a new candidate with the exact stored baseline output.

Cache entries are immutable results, not mutable memoization rows. Bypass reuse
for an explicit nondeterminism study. An unpinned model alias may still be
recorded, but it is not a reproducible candidate fingerprint and must not back a
release claim.

Select incremental work from the declared change surface:

- prompt/model/schema change: affected derivation cases plus all sentinels;
- reconciliation/reducer change: reconciliation cases plus all sentinels;
- evaluator-only change: reuse outputs and rescore calibration/holdout cases;
- storage/UI/telemetry-only change: deterministic contract tests, not an
  expensive semantic replay unless the task boundary changed.

Always include the small sentinel set so an incorrect change-impact classifier
cannot suppress every signal.

### 8. Use paired gates and represent uncertainty honestly

Every candidate run declares a baseline run on the **same cohort revision**.
Report per-case paired transitions, not just two unrelated averages:

```text
pass -> pass
pass -> fail      regression
fail -> pass      improvement
fail -> fail
unknown/error     evaluation health failure
```

Recommended gates:

1. **Hard deterministic gate:** no newly violated safety, schema, evidence, or
   lifecycle invariant on sentinels or accepted regression cases.
2. **Known-case gate:** no previously passing, human-accepted critical case may
   regress without an explicit waiver.
3. **Semantic aggregate gate:** only after judge calibration, use paired deltas
   on the representative cohort and report a confidence interval, case count,
   and unknown/error rate. Do not block on a tiny unpaired mean.
4. **Evaluation-health gate:** missing artifacts, authorization failures,
   evaluator errors, or excessive `cannot_assess` results fail the evaluation
   run, not the product candidate as if it had received a semantic fail.

Use a paired bootstrap interval over case-level deltas for the first aggregate
implementation; it handles non-normal bounded scores without inventing a model
of their distribution. The exact tolerated regression, confidence level, and
minimum cohort size are release-policy inputs to approve with the first rubric,
not architectural constants.

### 9. Split fast CI from scheduled and release evaluation

| Lane | Scope | Purpose |
|---|---|---|
| Local/dry run | A few development cases, deterministic checks, optional cached outputs | Validate runner, mapping, and rubric quickly |
| Pull-request CI | Sentinels + affected accepted regression cases; deterministic checks first; small calibrated semantic slice when authorized | Catch obvious regressions with bounded cost and latency |
| Nightly/scheduled | Full development/regression cohort, broader representative controls, LLM judges, drift and unknown-rate report | Discover broader regressions and judge drift |
| Release holdout | Frozen holdout, pinned candidate/evaluator/provider, paired baseline, approved gates | Release evidence |

Protected production content must run in an authorized internal worker or
environment. Do not copy it to a public GitHub-hosted runner merely to obtain a
PR check. Sanitized OSS fixtures can run in ordinary GitHub CI.

The official Langfuse experiment action is an optional implementation for an
approved dataset. MemForge's provider-neutral runner and result records remain
the contract; a Langfuse outage must not erase historical evaluation evidence
or reinterpret an evaluation error as a product pass.

### 10. Integrate Langfuse as a workbench and projection

When content export is approved, mirror one MemForge case to one Langfuse
dataset item and record:

- `case_id` and case schema version;
- task family and safe strata;
- source runtime `trace_id`/`event_id` only when authorized;
- accepted-ground-truth revision ID;
- cohort ID and role; and
- protected content fields allowed by the specific export policy.

Pin and record the Langfuse dataset version timestamp for every experiment.
Use experiment metadata for candidate, baseline, code commit, prompt/model,
contract, runner, evaluator-suite, and environment versions. Project
per-evaluator results as Scores and run-level aggregates only as summaries; the
MemForge `AgentEvaluationResult` remains authoritative.

Use Annotation Queues for proposed human annotations and corrected outputs.
Import each annotation as a versioned proposed `AgentAssessment`; require the
MemForge acceptance/adjudication step before creating an
`AcceptedGroundTruthRevision`.

Default behavior remains metadata-only. Semantic cases that require source
text stay inside the authorized MemForge runner unless a separate policy
explicitly allows those exact fields, recipients, retention, and deletion
semantics in Langfuse.

## Initial semantic rubric for the missed-Teams-memory class

The first rubric should evaluate proposition sets rather than exact generated
wording. One case contains human-accepted memory-worthy propositions and, when
useful, explicitly accepted non-memory operational statements.

| Criterion | Evaluator | Question |
|---|---|---|
| `memory_worthy_recall` | calibrated LLM + human calibration | Did the candidate retain each accepted durable proposition? |
| `unsupported_memory` | calibrated LLM, preceded by deterministic evidence resolution | Is every candidate memory supported by the pinned source evidence? |
| `evidence_reference_valid` | deterministic | Does every evidence/block reference resolve inside the pinned revision? |
| `drop_disposition_valid` | deterministic + semantic only for disputed importance | Is every omitted candidate covered by an allowed, explained drop disposition? |
| `scope_and_specificity` | calibrated LLM | Does the memory preserve the durable claim without operational noise or unsupported generalization? |

Primary regression metrics are proposition recall, unsupported-memory count,
and evidence-reference validity. Do not begin with a single blended score; a
candidate that invents memories must not compensate for that by extracting more
true ones.

## Minimal implementation order

### Slice A: authoritative cases and deterministic replay

- persist immutable cases, ground-truth revisions, cohorts, runs, and results;
- authorize event-to-case promotion and artifact resolution;
- replay `source_unit_derivation` and `source_unit_reconciliation` without
  provider collection or product writes;
- implement deterministic evaluators and CLI/API result inspection; and
- prove SQLite/HANA contract parity.

### Slice B: human calibration

- approve the first proposition-level rubric and content visibility policy;
- create a stratified calibration overlap and release holdout;
- import annotations as proposed assessments and adjudicate accepted revisions;
- report agreement and per-label confusion.

### Slice C: judge shadowing and efficiency

- add one versioned semantic judge in non-gating shadow mode;
- add candidate-output and assessment fingerprints;
- run incremental PR and scheduled cohorts;
- compare judge results with the human calibration/holdout labels.

### Slice D: release gates and Langfuse workbench

- approve criterion-specific thresholds after observed calibration;
- enable paired release gates;
- mirror approved cases/runs/scores to Langfuse;
- round-trip Annotation Queue results through MemForge acceptance; and
- enable the Langfuse CI action only for datasets and runners whose content and
  availability policy make that appropriate.

## Acceptance criteria for the first offline slice

1. Promoting the same event under the same policy produces one case; a corrected
   manifest produces an explicit successor rather than mutation.
2. A replay succeeds after the live runtime event and Langfuse trace have been
   purged, using only authorized pinned artifacts.
3. Replaying a case performs no provider fetch and cannot mutate live Memory or
   lifecycle state.
4. The same case/candidate/evaluator fingerprints reuse the same immutable
   result; a changed evaluator reuses candidate output but creates a new
   assessment.
5. Failure-regression and representative-control results are reported
   separately.
6. Deterministic evaluator errors are unknown/error, not pass.
7. Human disagreement is retained and adjudication creates a new accepted
   ground-truth revision.
8. A judge remains non-gating until its locked version passes the approved
   calibration and holdout policy.
9. A release report identifies exact case, cohort, baseline, candidate,
   evaluator, prompt/model/contract, code, and environment versions.
10. Langfuse disabled or unavailable does not prevent canonical case replay,
    result persistence, or gate calculation.

## Explicit non-goals

- Full provider collection or full Source-sync replay for every case.
- Treating a sampled online Score, user reaction, or LLM judgment as ground
  truth automatically.
- One generic “agent quality” score.
- Embedding-based case clustering, adaptive novelty models, or judge ensembles
  before measured need.
- Copying ordinary source/prompt/Memory content into telemetry or Langfuse by
  default.
- Using CI success to claim production-representative quality without a
  separately reported representative cohort.
- Making Langfuse, OpenAI Evals, MLflow, Phoenix, or OTel part of the canonical
  persistence contract.

## Conclusion

The efficient scope is a task-level, immutable, paired replay system—not a
second ingestion platform. The design spends deterministic checks on every
affected case, semantic judges only where meaning is genuinely undecidable by
code, and human effort on calibration, hard failures, and adjudication. Stable
cohorts, exact fingerprints, and separate failure/control reporting make the
result reproducible and statistically interpretable. Langfuse adds a strong
experiment comparison and annotation experience, while MemForge retains the
authorization, ground truth, and durable audit needed for both Cloud and
self-hosted deployments.
