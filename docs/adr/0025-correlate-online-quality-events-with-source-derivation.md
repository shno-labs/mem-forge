# Correlate agent runtime facts, telemetry, and evaluation

Status: Accepted (2026-08-13)

Issue #258 terminal-outcome amendment: Proposed (2026-08-17)

Amended:

- 2026-08-14 to retain one content-free diagnostic runtime fact for each
  provider attempt that fails transport or schema validation. Ordinary
  schema-conformant attempts remain represented only by the logical-call
  outcome.
- 2026-08-16 to define the stable Session, Trace, and observation hierarchy
  used by the Langfuse projection.
- 2026-08-16 to add the first DB-authoritative deterministic
  `AgentAssessment` contract and optional Langfuse Score projection.
- Proposed 2026-08-17 to separate logical Agent Operation, durable Agent
  Execution, and terminal Event identity and to add the first Source lifecycle
  reconciliation producer without turning internal retries into failed
  evaluations.

## Context

MemForge records structured-model metrics, Source Projection/Derivation
lineage, and Memory lifecycle audit. Those records do not explain why a
source batch produced no Memory when a candidate was rejected before it
received a Memory ID. A log such as `quote mismatch` is not self-contained if
it cannot identify the exact source revision, derivation batch, Evidence
decision, prompt contract, and deployed build.

This information cannot live only in traces. Production traces may be sampled
or unavailable, and OpenTelemetry trace/span IDs describe one telemetry
execution rather than stable product identity. Nor is a runtime anomaly an
evaluation result: a whole-Block fallback can be valid, and an LLM judge is
not ground truth merely because it returned a score.

## Decision

### Keep three distinct planes

1. `AgentRuntimeEvent` is an immutable fact about what the product did. It is
   recorded without sampling and carries stable MemForge lineage.
2. Trace/evaluation backends are optional projections. The first supported
   projection uses an isolated Langfuse Python SDK adapter because Python is
   the current runtime and Langfuse already implements its tracing on
   OpenTelemetry. MemForge does not require applications to configure an OTel
   SDK, OTLP exporter, Collector, or SAP Cloud Logging for product correctness.
   Explicit OTel/OTLP remains the future interoperability adapter when a
   deployment needs multiple telemetry backends or cross-service tracing.
3. `AgentAssessment` is a versioned code, LLM, or human judgment targeting a
   runtime event or evaluation case. An explicitly accepted human or
   deterministic reference may become ground truth; an LLM score alone does
   not.

`AgentEvaluationCase` is the explicit bridge from live traffic into an
immutable offline cohort. It pins protected artifact handles and versioned
expected output instead of reading mutable current source state during replay.

The canonical vocabulary is provider-neutral OSS. MLflow, Langfuse, Phoenix,
OpenInference, OpenLLMetry, and other backends are optional exporters or
evaluation workers; none owns MemForge identity or storage semantics.

### Bind runtime facts at the Source Derivation seam

Extraction, structured-output, and Evidence code emits small content-free
`QualitySignal` values into one bounded request-local collector. Producers do
not know a database, workspace, connector, or telemetry provider.

`SourceUnitDeriver` binds each signal to source, document, Source Unit, current
Source Unit revision, Projection run, Derivation, batch, batch attempt,
extraction contract, Observation revision when known, prompt hash, provider,
model, and deployment revision. The resulting `AgentRuntimeEvent` remains
actionable when no Memory exists. Its deterministic product ID is based on
stable execution lineage and signal sequence; trace/span IDs are optional
correlation and never participate in identity.

The batch outcome and its runtime events commit in one SQLite/HANA transaction.
This required product audit is distinct from optional trace shipping. After
commit, one injected `RuntimeEventTraceSink` may publish the bounded events.
The default sink is no-op. The first concrete sink uses the Langfuse Python SDK
and contains no source, prompt, quote, Memory, or model-response content. Sink
failure is logged and cannot change the committed extraction result. A
dedicated transactional export outbox is introduced only if a configured
external sink requires at-least-once delivery; the durable runtime ledger
remains replayable meanwhile.

Langfuse enablement is explicit and fail-safe: the feature flag, exact base
URL, and both SDK credentials must be present before the adapter is
constructed. Requiring the base URL avoids silently exporting to the SDK's
default region. Missing or invalid configuration selects the no-op sink and
records an operational warning; it never weakens the durable database event.

The first deterministic evaluator is a pure, provider-neutral function over
the just-bound runtime events. Its completed `AgentAssessment` rows commit in
the same transaction, after their target events, so a successful extraction
cannot leave an eligible deterministic check missing because a process exited
between commits. This narrow exception to asynchronous evaluation is limited
to local constant-time rules with no network, model, or content access.
Semantic, LLM, and human evaluators remain post-commit asynchronous workers.

### Separate logical work, durable executions, and terminal facts

The Source Derivation identity used by the first increment is not sufficient
for lifecycle reconciliation. A reconciliation may fail after extraction has
already committed, may retry several times inside one document execution, and
may later run again under durable worker recovery. Treating every caught
exception as an event would overcount failures; treating the eventual success
as an update of an earlier failure would erase real production evidence.

The shared runtime domain therefore uses three product identities:

| Identity | Meaning | Reuse rule |
| --- | --- | --- |
| `operation_id` | one exact logical work item and its versioned input manifest | shared by recovery executions only while the complete logical input remains identical |
| `execution_id` | one durable execution owned by a run/lease boundary | shared by internal retries, changed by a later durable recovery execution |
| `event_id` | one named immutable terminal fact for that execution | deterministic from schema, execution, and event name; a conflicting payload is an invariant violation |

Trace, observation, and Session IDs remain optional projection identities.
They never replace these product IDs.

`operation_id` and `execution_id` are identity fields on the runtime event, not
new Agent Operation/Execution tables, statuses, queues, or schedulers. Durable
work ownership remains in Source Sync, Source Derivation, Source Projection,
and Lifecycle Plan records that already own those transitions.

For `source_unit_lifecycle_outcome`, the operation manifest pins:

- operation kind and reconciliation contract version;
- Source, Source Unit, base and target Source Unit revisions;
- the Source Derivation identity and candidate-output hash when extraction ran;
- the complete incumbent version and active-Support-set fingerprints;
- Lifecycle Gate state and other inputs that can change the reducer result.

The `operation_id` is a versioned digest of that content-free manifest. The
manifest must be complete enough that a changed incumbent, Support set, gate,
candidate output, or contract creates a different operation instead of being
mis-grouped as a retry.

The `execution_id` is a versioned digest of `operation_id` plus the explicit
durable execution owner and attempt: normally the durable Source Sync run ID,
its lease-attempt ordinal, and the Source Unit. Direct execution supplies its
own explicit run identity. Code must not parse these values from a composite
Projection run ID or synthesize them inside a telemetry adapter. The sync
coordinator passes the durable execution identity and current bounded document
attempt ordinal explicitly into the Source Unit lifecycle call.

One execution can contain provider retries and the existing bounded document
retry loop. Those attempts increment `attempt_count`; if a later attempt
succeeds, the execution records one expected terminal outcome with
`recovered=true` and no failed assessment. If the owner durably ends that
execution as failed or partial, it records one failed terminal outcome. A
later scheduler recovery is a new execution and therefore a second immutable
outcome under the same operation:

```text
operation O (same pinned reconciliation input)
  execution E1: internal attempts 1..3 -> durable failed -> event F -> fail
  execution E2: internal attempts 1..2 -> committed success -> event S -> pass
```

Database delivery retry for F or S uses the same `event_id` and is an
idempotent no-op only when the full canonical payload hash matches. The store
must not use an unconditional insert-ignore that could silently accept two
different terminal claims for the same event identity.

### Add one Source lifecycle terminal producer at the durable owners

The first Phase 2 producer observes the complete Source Unit lifecycle
operation: relation classification, deterministic relation reduction,
Lifecycle Plan construction, stale validation, and atomic application. It does
not emit one event per candidate/incumbent relation or lifecycle mutation.

The implementation has one typed, provider-neutral `AgentRuntimeBundle`
containing the bound terminal event and its deterministic assessments. A
central binder validates safe labels, constructs the three identities, hashes
the canonical payload, and applies the deterministic evaluator. It has no
database or Langfuse dependency.

Domain layers have narrow responsibilities:

- the relation classifier and static reducer return typed failure codes and
  metrics but never persist telemetry;
- the projected lifecycle boundary wraps an unhandled failure in one
  content-free terminal descriptor; it never persists the raw exception;
- a successful `apply_source_projection_lifecycle` stores the expected event
  and assessment in the same transaction as the Projection and Lifecycle Plan;
- the sync coordinator retains only the last bounded failure descriptor while
  its internal document retries continue;
- after retries are exhausted, the durable worker transition to pending,
  partial, or failed stores the failed bundle in the same transaction. The
  direct-sync terminal result does the equivalent through its existing
  terminal-history transaction;
- post-commit sinks receive complete bundles. A heterogeneous batch is grouped
  by `execution_id`; the first event in a tuple never determines another
  execution's trace identity.

This split is necessary because the success and failure facts have different
transaction owners. It is not a second lifecycle: all durable mutation remains
owned by the Source Projection and Lifecycle Plan, while the runtime ledger
only observes the terminal outcome.

The initial lifecycle event is:

- `event_name = source_unit_lifecycle_outcome`;
- `outcome = expected` with `reason_code = lifecycle_plan_applied` after a
  successful atomic application;
- `outcome = failed` with a typed low-cardinality reason such as
  `non_unique_contradiction_proposal`, `relation_ledger_incomplete`,
  `stale_guard_rejected`, or `lifecycle_commit_failed` after the execution
  owner accepts the failure;
- criterion `source_unit_lifecycle_completion`, assessed pass for the applied
  outcome and fail for the failed outcome.

A safely created Review is not a failed lifecycle execution and pending vector
delivery does not undo an applied relational plan. The event may report bounded
aggregate counts such as candidates, incumbents, relation pairs, mutations,
Reviews, model calls, attempts, and elapsed milliseconds, but never individual
relation text, prompt/source/Memory/model content, exception text, or an
unrestricted metadata object.

An unchanged Projection, Source Derivation cache reuse, framework/HTTP success,
and a handled internal retry do not create this event. A deterministic
lifecycle operation that actually builds and applies a semantic plan may emit
the same terminal event with `model_call_count=0`; the denominator is the
product operation, not LLM usage.

### Evolve the source-bound envelope without anticipating retrieval

Schema v3 adds `operation_id`, `execution_id`, generic `contract_version`,
canonical `payload_hash`, `duration_ms`, and `recovered` to the source-bound
runtime envelope. Source, document, Source Unit, target revision, and
Projection lineage remain required for this producer. Extraction-only
Derivation, batch, and extraction-contract fields become optional extensions;
new extraction events also populate the common operation/execution/contract
fields. Existing schema-v2 rows remain readable and are not rewritten merely
to manufacture identities they did not originally store.

This amendment does not make source identity nullable or add a generic JSON
subject in anticipation of retrieval evaluation. A future retrieval producer
must first define its workspace-scoped authorization, logical operation, and
replay manifest, then extend the shared envelope deliberately. It must not use
fake Source, document, Derivation, or batch identifiers to fit this slice.

The initial rules judge only contracts that the runtime fact proves:

- final structured-output conformance is pass/fail;
- rejected Evidence references are fail;
- exact or canonical Evidence localization is pass, while whole-Block fallback
  is `needs_review`, not fail;
- completed extraction with candidates and terminal batch failure are
  pass/fail respectively;
- applied Source Unit lifecycle and a terminal Source Unit lifecycle failure
  are pass/fail respectively.

`zero_candidates` is not judged because the runtime event cannot prove that a
Memory should have existed. Failed provider attempts are not scored separately
because the logical structured-output event is the denominator authority.
An assessment inherits the immutable target event's `occurrence_count`, so a
collector overflow that coalesces equivalent facts does not undercount the
evaluation denominator. Absence of an assessment remains unknown.

The product stores a stable trace correlation ID when a trace sink supplies or
derives one, but the trace ID is not part of `AgentRuntimeEvent` identity. The
Langfuse adapter uses the same trace ID and puts `event_id` on each child
observation so an investigator can move in either direction through an
authorized MemForge lookup. The shared bounded cohort query supports exact
`event_id` and `trace_id` filters with normal source-visibility enforcement.
The adapter constructs one process-level Langfuse client with an isolated OTel
`TracerProvider` and exports only Langfuse-owned spans. Environment changes
therefore require a process restart. SDK batching remains asynchronous and one
graceful process-exit shutdown drains its queue; a source batch never performs
a synchronous flush.

### Use a bounded runtime taxonomy

Stable event names identify occurrence classes, initially:

- `structured_output_outcome`;
- `structured_llm_attempt_outcome` for non-conformant provider attempts;
- `evidence_admission_outcome`;
- `evidence_localization_outcome`;
- `extraction_batch_outcome`;
- `source_unit_lifecycle_outcome`.

Outcomes are `expected`, `degraded`, `rejected`, or `failed`; stable
low-cardinality reason codes explain the result. These values describe runtime
behavior, not semantic correctness labels.

The collector is capped. If it overflows, it preserves exact denominator
counts by coalescing excess occurrences by `(event_name, outcome, reason_code)`
instead of replacing them with an unrelated overflow event. Event and query
payloads are bounded and versioned.

The logical structured-output event remains the denominator authority for
call, retry, fallback, and terminal rates. A non-conformant provider attempt
additionally records its one-based attempt index, native-schema or JSON-text
mode, selected schema transport, requested output-token cap, optional
finish/stop reason, provider response/request identifier, reported token usage,
response character count and SHA-256, bounded validation rule/path and JSON
line/column when available. Provider errors without a response record the same
attempt identity and stable error category with response fields absent.

The implementation may transiently inspect a provider response to calculate
these allowlisted fields, but it never persists the response, prompt, provider
headers, validation message, or exception body. Only an allowlisted request ID
header or bounded response ID may cross the seam. This preserves enough
evidence to distinguish output truncation, refusal, schema-transport drift, and
malformed complete output without creating a content-bearing debug path.

### Keep the trace adapter isolated

`RuntimeEventTraceSink` is the only interface the Source Derivation caller
learns. Langfuse configuration, SDK construction, buffering, flushing,
attribute mapping, and backend failure stay inside its adapter. The core and
every storage adapter compile and run when the optional dependency is absent.

The first Langfuse projection creates one metadata-only root span per
derivation batch attempt and discrete child events for its runtime facts.
Every event carries the durable `event_id` and is explicitly parented to the
root with the durable trace correlation ID. It does not export
source/workspace/document/user identifiers, protected handles, raw hashes that
could disclose content, or arbitrary errors. Langfuse annotations and datasets
remain separate future evaluation adapters. The optional Score projection
reuses the process-level client owned by the runtime trace adapter but
implements a separately typed `AgentAssessmentSink`. It attaches one
categorical Score to the deterministic batch Trace, uses the durable assessment
ID as Score identity, and carries the target runtime-event ID in allowlisted
metadata. Score export is post-commit and best-effort; the DB row remains
authoritative.

### Group Langfuse telemetry by product execution boundaries

Langfuse identity follows the existing MemForge execution hierarchy rather
than introducing another durable lifecycle:

| Langfuse level | MemForge boundary | Stable correlation |
| --- | --- | --- |
| Session | one Source Projection execution | opaque hash of `projection_run_id` |
| Trace | one executed Source Derivation batch attempt | `derivation_id`, `batch_id`, and `batch_attempt` |
| Root observation | that batch attempt's metadata-only projection | stable name `memforge.agent.extraction_batch` |
| Child observation | one durable `AgentRuntimeEvent` occurrence | `event_id` in metadata |

The Session is deliberately narrower than a whole source sync and broader than
one Derivation. Diff-guided extraction and its structural fallback may create
different Derivations, but they remain one Projection workflow and therefore
one Session. `derivation_id` would split that workflow; `source_id` or the
source-sync run would create large, mixed-purpose Sessions.

The Langfuse adapter derives, but does not persist, the Session ID as
`mfs1-<sha256("memforge-agent-runtime-session-v1:" + projection_run_id)[:32]>`.
The prefix versions the export mapping, the digest keeps raw lineage out of the
external backend, and the result satisfies Langfuse's ASCII/200-character
limit. `projection_run_id` remains the authoritative DB key; no Session column,
table, migration, or source-specific mechanism is added.

The Trace ID remains a deterministic 32-lowercase-hex digest of the versioned
`(derivation_id, batch_id, batch_attempt)` seed, with a guard against W3C's
invalid all-zero value. The attempt ordinal separates real retries. This ID is
correlation, not export idempotency; an at-least-once exporter would still need
its own outbox and observation-deduplication contract.

Langfuse requires an arbitrary valid parent span ID when a predetermined Trace
ID is injected. It only makes the root inherit that Trace ID; it is not a
missing MemForge operation and does not justify a global OTel ID generator.

The adapter sets first-class Langfuse attributes early enough that the root and
all child observations agree on:

- `session_id`: the derived Source Projection Session ID;
- `trace_name`: `memforge.agent.extraction_batch`;
- `version`: the extraction contract version;
- `release`: the deployment revision already configured on the client;
- `environment`: the deployment environment already configured on the client;
- `tags`: only the low-cardinality values `memforge-agent-eval`,
  `memory-extraction`, and `source-type:<source_type>`.

`user_id` remains unset. Dynamic IDs never enter names, tags, metric labels,
input, or output. Ordinary logs do not repeat runtime events; only an export
failure warning adds the opaque Session ID, Trace ID, event count, and bounded
error type needed to correlate with the durable ledger.

Lifecycle projection follows the same hierarchy without pretending that a
recovery rewrites an earlier trace:

| Langfuse level | Source lifecycle boundary | Stable correlation |
| --- | --- | --- |
| Session | one logical reconciliation operation/recovery family | opaque versioned hash of `operation_id` |
| Trace | one durable reconciliation execution | deterministic hash of `execution_id` |
| Root observation | that complete execution | `memforge.agent.reconcile_source_unit` |
| Child event | its durable terminal runtime fact | `event_id` in metadata |
| Score | deterministic lifecycle-completion assessment | durable `assessment_id`; Trace score with target `event_id` metadata |

The failure trace remains failed. A later recovery success creates another
Trace in the same Session. Langfuse trace and observation records are immutable
and are not an upsert or exactly-once mechanism, so exporter retry never decides
the canonical denominator. The MemForge DB deduplicates by `event_id` and
payload hash; Langfuse remains a best-effort view unless a measured delivery
SLO later justifies an outbox.

The corresponding OpenTelemetry root span, when an OTel projection is later
enabled, represents the complete execution rather than each handled retry. A
failed terminal execution sets bounded `error.type` and Error status; an
execution that recovers internally remains successful and does not repeat the
same handled exception at multiple layers.

Deployment target, environment label, sampling policy, and the disabled-first
feature flag are non-secret deployment configuration. Public and secret SDK
keys remain outside Git and rendered deployment files. A deploy first starts
with the adapter disabled, runs the SDK's blocking authentication check as an
operator smoke, and only then enables the flag and restarts the process. The
authentication call never runs in an application request or extraction path.

### Preserve OpenTelemetry interoperability without requiring OTLP

Use stable span names for source sync, derivation batch, model call, Evidence
localization, lifecycle application, and asynchronous evaluator execution.
Sampling-relevant attributes such as operation, source type, provider/model,
contract version, and deployment revision are set when the span starts.

The runtime-event trace ID is derived from durable derivation, batch, and
attempt identity so DB-to-Langfuse correlation remains stable across process
topology and replay. It deliberately does not reuse an ambient OTel trace as
product identity. A future explicit OTel sink can map each durable event to a
span event using the same stable names and content-free attributes. A post-hoc
evaluator may create a linked `EVALUATOR` span and emit
`gen_ai.evaluation.result`; that standard event is used only for a real
`AgentAssessment`, never for the underlying runtime fact. OpenInference
mappings may add evaluator/annotation compatibility without changing the OSS
domain object.

Metrics include counts, rates, latency, queue delay, and score distributions.
Workspace, source, document, unit, Memory, event, trace, span, request, and user
IDs are forbidden metric labels. Detailed dashboards link to an authorized
runtime-event query instead.

### Keep content and authorization out of ordinary telemetry

Default runtime events, traces, metrics, and logs never contain source text,
prompt text, quote text, Memory content, model responses, tool arguments,
provider exception bodies, credentials, or raw provider URLs. They carry
stable IDs, hashes, ranges, counts, modes, versions, and an optional protected
artifact handle.

Artifact lookup, event/case query, and case materialization enforce the same
workspace, owner, visibility, and source-retention boundaries as retrieval.
Content capture requires a separately authorized workflow with its own access,
encryption, retention, and audit policy.

### Separate three sampling policies

- Product audit records every bounded high-value runtime fact; it is not trace
  sampling.
- Telemetry tail-samples rejected, failed, degraded, or high-latency traces and
  probabilistically samples ordinary success traces.
- Evaluation selection retains all deterministic failures plus risk-triggered
  cases and a small unbiased success/control cohort. Expensive LLM judges run
  asynchronously and record evaluator version and execution failure explicitly.

Exact rates are computed from the durable event ledger, never from sampled
traces. A missing assessment is unknown, not success.

### Retain runtime facts by explicit product policy

Runtime facts are not retained forever merely because they are stored in the
product database. The shared storage interface provides a bounded, idempotent
purge by `occurred_at`; SQLite and HANA implement the same cutoff and batch
semantics. The default policy retains 90 days and the existing daily scheduler
performs one bounded cleanup batch. Operators can run the same cleanup
explicitly when scheduling is disabled.

An event selected for durable regression work must first be promoted into an
immutable `AgentEvaluationCase`. Runtime-event retention, case/assessment
retention, source-content retention, and Langfuse retention remain separate.
Purging a runtime event never extends or shortens protected source retention.

### Promote live facts into offline cases explicitly

Promotion records source/revision lineage, event IDs, artifact handles,
contract/prompt/schema/model/deployment versions, selection rule, observed
output/disposition, expected output, label provenance, and adjudication
revision. Cases are immutable and deduplicated.

Offline evaluation replays a fixed cohort against a candidate change and
compares deterministic, LLM, and human assessments on that same cohort.
Human-reviewed cases are reported separately from sampled controls. A model or
prompt change cannot silently replace the dataset.

For Source lifecycle reconciliation, the protected case manifest additionally
pins the exact operation manifest used to derive `operation_id`: Source Unit
revisions, candidate derivation/output hashes, incumbent versions and Support
fingerprints, gate state, reconciliation contract, and the terminal event. An
offline replay must resolve those protected handles under current authorization
and retention policy; it must not reconstruct the incumbent set from mutable
current Memories or from Langfuse metadata.

Promotion initially selects all stable lifecycle failures and recovered
executions, plus a bounded deterministic success/control sample. Promotion is
idempotent for `(event_id, promotion_policy_version)`. Human, code, and LLM
assessments remain separate versioned rows. A Langfuse annotation or dataset
item is imported as a proposed assessment/case revision and becomes Accepted
Ground Truth only through an explicit authorized MemForge acceptance step.

Offline runs execute an immutable case cohort against one candidate contract
and store a separate run result; they never mutate the case or its accepted
reference. CI or release gating begins only after the cohort, rubric, allowed
regression thresholds, and evaluator version are explicitly approved.

## Consequences

All Source types—including Teams, Confluence, Jira, GitHub, Local Markdown,
Agent Session, and extensions—share one instrumentation seam. Connectors do not
need their own Block, trace, or evaluation mechanism.

SQLite and HANA implement the same append/query/purge semantics, stable
ordering, idempotency, filters, cutoff, and bounded cleanup. Cloud adds
workspace partition, visibility checks, and deployment metadata, but no
Cloud-only taxonomy or source-specific path. Cloud does not add an export
outbox until an external delivery SLA actually requires at-least-once delivery.

The first increment persists structured-output, Evidence admission/localization,
and batch facts plus the narrow deterministic assessments above; provides a
bounded authorized Source view and retention through the target-event cascade;
optionally projects metadata-only traces and categorical Scores through the
isolated Langfuse adapters; and proves SQLite/HANA parity. Case persistence,
semantic assessor scheduling, human review, and regression gating build on
separate contracts rather than widening the runtime-event object.

The first Phase 2 increment adds the source-bound schema-v3 identity envelope
and `source_unit_lifecycle_outcome`, proves atomic success and failed-run
persistence in SQLite and HANA, and projects immutable recovery traces and
Scores to Langfuse. It does not yet implement retrieval events, managed judges,
annotation import, case materialization, alert thresholds, or an export outbox.

Acceptance includes these falsifiable cases:

1. Three handled document attempts followed by success produce one expected
   terminal event and one pass assessment with `attempt_count=3`.
2. One durable failed execution followed by a later recovery success produces
   two events with one `operation_id`, two `execution_id` values, and immutable
   fail/pass traces.
3. A lifecycle transaction rollback produces no success event or orphan pass;
   the accepted failed-run transition records exactly one failure bundle.
4. Replaying the same event payload is a no-op, while reusing its `event_id`
   with a different payload hash fails closed in SQLite and HANA.
5. Unchanged projections and extraction cache reuse do not mint lifecycle or
   extraction events for work that did not execute.
6. Online DB event/assessment counts reconcile with durable execution outcomes
   while Langfuse is disabled or unavailable.
7. All supported configured Source types reach the same Source Unit lifecycle
   producer through shared Projection and Memory Engine seams; connectors add
   no telemetry branch.

## References

- [OpenTelemetry GenAI agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)
- [OpenTelemetry GenAI evaluation event](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-events.md#event-gen_aievaluationresult)
- [OpenTelemetry sampling](https://opentelemetry.io/docs/concepts/sampling/)
- [Langfuse Python SDK overview](https://langfuse.com/docs/observability/sdk/overview)
- [Langfuse SDK instrumentation](https://langfuse.com/docs/observability/sdk/instrumentation)
- [Langfuse trace IDs and distributed tracing](https://langfuse.com/docs/observability/features/trace-ids-and-distributed-tracing)
- [Langfuse Sessions](https://langfuse.com/docs/observability/features/sessions)
- [Langfuse tracing best practices](https://langfuse.com/docs/observability/best-practices)
- [Langfuse releases and versioning](https://langfuse.com/docs/observability/features/releases-and-versioning)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [OpenTelemetry Tracing API](https://opentelemetry.io/docs/specs/otel/trace/api/)
- [OpenInference annotations](https://arize-ai.github.io/openinference/spec/annotations.html)
- [MLflow automatic evaluations](https://mlflow.org/docs/latest/genai/eval-monitor/automatic-evaluations/)
- [Langfuse LLM-as-a-judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)
- [Langfuse Scores via SDK](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk)
- [Phoenix annotations](https://arize.com/docs/phoenix/tracing/concepts-tracing/annotations-concepts)
- [OpenTelemetry semantic-convention authoring guidance](https://opentelemetry.io/docs/specs/semconv/how-to-write-conventions/)
- [OpenTelemetry recording errors](https://opentelemetry.io/docs/specs/semconv/general/recording-errors/)
- [Langfuse tracing-data immutability](https://langfuse.com/faq/all/tracing-data-updates)
- [Langfuse data model](https://langfuse.com/docs/observability/data-model)
- [Langfuse dataset versioning](https://langfuse.com/docs/evaluation/experiments/datasets#versioning)
- [Issue #258 terminal-outcome research](../research/2026-08-17-terminal-agent-outcome-evaluation.md)
