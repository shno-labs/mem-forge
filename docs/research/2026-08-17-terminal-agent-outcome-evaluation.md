# Terminal agent outcomes and the online-to-offline evaluation loop

Date: 2026-08-17

Status: Research recommendation for GitHub issue #258. Official facts and
MemForge-specific recommendations are separated below. This note does not amend
the architecture by itself.

## Question

How should MemForge represent a terminal agent/runtime outcome so that:

- an actual reconciliation failure is visible to online evaluation;
- handled retries do not create false failures or duplicate evaluations;
- durable product audit remains exact even if a trace exporter is unavailable;
- Langfuse presents executions, retry families, and scores coherently; and
- selected live failures can become reproducible offline evaluation cases?

## Official facts

### OpenTelemetry operation and error semantics

An OpenTelemetry span represents an operation with duration. A span definition
should state its start/end boundary and, where retries are possible, whether it
represents the logical caller-visible operation or one physical attempt. A
point-in-time occurrence should be an event instead of another span. Span names
should be low-cardinality operation classes rather than instance identifiers.
([OTel semantic-convention authoring guidance](https://opentelemetry.io/docs/specs/semconv/how-to-write-conventions/))

OpenTelemetry does not impose one retry shape for every domain. Its stable HTTP
convention normally creates one client span per physical send attempt and adds
`http.request.resend_count` to repeated attempts. Its stable database
convention instead recommends that a database span represent the logical API
call and include internal retries in that span's duration. These examples show
that the instrumentation owner must choose and document the boundary that
matches the domain operation.
([OTel HTTP retries](https://opentelemetry.io/docs/specs/semconv/http/http-spans/#http-request-retries-and-redirects),
[OTel database client span duration](https://opentelemetry.io/docs/specs/semconv/db/database-spans/#database-client-span-duration))

Errors that were handled or retried so that the enclosing operation completed
successfully should not mark that enclosing operation as failed. When the
operation itself ends with an error, instrumentation should set span status to
`Error` and set a bounded `error.type`. On success, status should normally
remain `Unset`; instrumentation libraries generally should not set `Ok`.
([OTel recording errors](https://opentelemetry.io/docs/specs/semconv/general/recording-errors/),
[OTel tracing API status](https://opentelemetry.io/docs/specs/otel/trace/api/#set-status))

An exception event is for an exception that remains unhandled when the span
ends and causes the span status to be `Error`. Recording the same handled
exception at several layers is explicitly discouraged.
([OTel exception conventions](https://opentelemetry.io/docs/specs/otel/trace/exceptions/))

Span links can correlate causally related work in the same or different traces,
but trace/span IDs remain telemetry context. They do not define a product's
durable business identity.
([OTel tracing API links](https://opentelemetry.io/docs/specs/otel/trace/api/#link))

The current GenAI agent conventions define `invoke_agent` client and internal
spans, require/recommend operation and provider attributes, and follow the
general error rules. These agent conventions are still marked **Development**,
so a product-specific stable schema should not expose their evolving field set
as its persistence contract.
([OTel GenAI agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md))

### Langfuse identity, grouping, and immutability

Langfuse models observations as individual application steps, groups
observations into a trace by `trace_id`, and can optionally group multiple
traces into a session by `session_id`. Its own guidance describes a trace as a
single request or operation and sessions as a grouping for multi-turn
interactions or workflows.
([Langfuse data model](https://langfuse.com/docs/observability/data-model),
[Langfuse sessions](https://langfuse.com/docs/observability/features/sessions))

Langfuse can derive a deterministic, valid trace ID from an external seed. This
is a correlation facility, not an update mechanism.
([Langfuse trace IDs and distributed tracing](https://langfuse.com/docs/observability/features/trace-ids-and-distributed-tracing))

Current Langfuse v4 documentation says traces and observations are immutable.
Re-sending the same observation or trace ID must not be treated as an upsert:
the read path does not deduplicate those records and duplicates can inflate
metrics and produce inconsistent dashboards. Consequently, a retry/replay
design cannot depend on "same Langfuse ID means exactly once."
([Langfuse tracing-data updates](https://langfuse.com/faq/all/tracing-data-updates))

Langfuse scores are separate evaluation objects. A score targets exactly one
trace, observation, session, or dataset run and may be numeric, categorical,
boolean, or text. A stable score ID can participate in idempotent replacement,
but replacement also requires the same score name and date-granularity
timestamp. Langfuse recommends sending a complete score rather than a partial
update.
([Langfuse score model](https://langfuse.com/docs/evaluation/scores/data-model),
[Langfuse scores via SDK/API](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk))

### Langfuse online and offline evaluation

Current Langfuse live evaluators target observations. They can filter on the
observation and propagated trace attributes, then asynchronously attach scores.
The current LLM-as-a-Judge documentation says sampling is deterministic per
observation and evaluators using the same percentage select the same subset of
matching traffic. This is a change from older documentation that described
independent random samples, so the current behavior should be verified again
when configuring production rules.
([Langfuse LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge))

Langfuse code evaluators are intended for deterministic checks and can run on
live observations or controlled experiment data. Langfuse recommends semantic
LLM judgment only when deterministic code is not sufficient.
([Langfuse code evaluators](https://langfuse.com/docs/evaluation/evaluation-methods/code-evaluators))

Annotation queues let domain experts score and comment on traces,
observations, or sessions and add corrected outputs. They are an evaluation
workbench, not proof that an annotation has been accepted as MemForge ground
truth.
([Langfuse annotation queues](https://langfuse.com/docs/evaluation/evaluation-methods/annotation-queues))

Langfuse supports creating a dataset item from a production trace or a specific
observation. Dataset item changes create timestamped dataset versions, and an
experiment can run against a selected version. This supplies a useful offline
workbench, but the source trace link is optional and does not itself preserve
MemForge source authorization or artifact retention.
([Langfuse datasets and production promotion](https://langfuse.com/docs/evaluation/experiments/datasets#create-items-from-production-data),
[Langfuse dataset versioning](https://langfuse.com/docs/evaluation/experiments/datasets#versioning))

## MemForge design recommendations

The rest of this note is design inference from the official contracts above,
not a claim that OTel or Langfuse requires this exact model.

### 1. Define the domain boundary before the telemetry shape

Use three identities with different meanings:

| Identity | Meaning | Stable across |
|---|---|---|
| `operation_id` | One logical MemForge work item, such as reconciling one immutable source-unit projection | Automatic recovery executions for that same work item |
| `execution_id` | One durable execution that reaches a recorded terminal run state | Re-delivery/replay of telemetry for that execution |
| `event_id` | One immutable `AgentRuntimeEvent` for one named terminal fact of that execution | DB retry and adapter replay |

`trace_id`, `observation_id`, and `session_id` are projections/correlation IDs,
not substitutes for any of these product identities.

For relation-first reconciliation, the logical operation is the reconciliation
scope or source-unit projection. It is **not** each candidate-incumbent pair and
not each resulting lifecycle action. One authoritative reducer result can cover
many incumbents; telemetry should observe that result rather than recreate the
reducer's internal Cartesian product.

### 2. Emit one terminal outcome at the owner of the durable boundary

The coordinator that owns the durable run-state transition should emit the
terminal runtime fact. Lower-level catches may add diagnostic context, but they
must not each emit another product failure.

Apply this rule to retries:

- If an exception is handled inside one execution and the execution ultimately
  succeeds, record the final success/degraded terminal outcome with bounded
  `attempt_count` and `recovered=true`. Do not create a failed online assessment
  for every handled attempt.
- If a durable execution itself is committed as failed and a later scheduler
  creates a new recovery execution, record one failed terminal event for the
  failed execution and a later event for the recovery execution. Both carry the
  same `operation_id` but distinct `execution_id` values.
- A retry of the DB write or event delivery for the same execution resolves to
  the same deterministic `event_id` and must be an idempotent no-op in the
  canonical store.

This makes a user-visible/durable failed run observable without counting every
exception log line as a separate agent failure.

### 3. Persist the exact fact before exporting it

The canonical `AgentRuntimeEvent` remains content-free, bounded, and stored in
SQLite/HANA. Persist it atomically with the terminal run state when both records
share a transaction owner. For a successful lifecycle mutation, the terminal
event must not become visible if the lifecycle commit rolls back. For a failed
execution, the run's failed state and its failure event should commit together
after mutation rollback has completed.

Recommended terminal fields for this slice:

- `event_name = memforge.agent.reconciliation.result`;
- `operation_id`, `execution_id`, `event_id`, `schema_version`;
- source, source-unit, immutable revision/projection, derivation, and lifecycle
  plan lineage that is available at the boundary;
- `outcome`: `succeeded`, `degraded`, `failed`, or `cancelled`;
- bounded `reason_code`, never a raw exception message;
- `attempt_count`, `recovered`, start/end time, deployment and contract version;
- optional trace/span correlation populated by the projection layer;
- aggregate counts such as candidates, incumbents covered, actions, and reviews;
- no prompt, source text, quote, model response, stack trace, or unrestricted
  metadata object.

Online deterministic assessment derives from this persisted event. Missing
assessment means "not assessed," never "pass."

### 4. Map the model to Langfuse without inventing update semantics

Recommended projection:

```text
operation_id (logical retry family)
  execution_id A -> Langfuse trace A -> terminal failed observation -> score fail
  execution_id B -> Langfuse trace B -> terminal success observation -> score pass
```

- Use one Langfuse trace per durable execution and a stable low-cardinality
  root observation name such as `memforge.agent.reconcile_source_unit`.
- If attempts occur inside that execution, represent them as child observations
  only when their latency/provider detail is operationally useful. The root
  status reflects the final execution result.
- Put `operation_id`, `execution_id`, and `event_id` in metadata. A session may
  additionally group traces in the same operation/recovery family, but session
  identity remains optional presentation metadata.
- Do not resend an immutable Langfuse observation to "turn failure into
  success." A later recovery is a new execution trace.
- Project the deterministic `AgentAssessment` as an observation-level Langfuse
  score. Use a stable score ID, name, and timestamp if exporter retry must
  replace the same score.

An outbox can reduce duplicate export, but no network protocol can make an
ambiguous timeout exactly-once merely by reusing a Langfuse trace ID. The DB
event remains authoritative. If duplicate trace export is observed, diagnose
and bound it through `event_id` metadata rather than hiding it from product
audit counts.

### 5. Promote selected online facts, not raw traces, to offline cases

Create `AgentEvaluationCase` from an immutable runtime event and its authorized
artifact references. Promotion policy should include:

- all stable terminal failure reason codes;
- recovered/degraded outcomes;
- human-reported failures;
- a deterministic success/control sample; and
- bounded novelty triggers for a new prompt, model, schema, or deployment.

The case owns stable lineage, the selection reason, exact contract/deployment
versions, protected artifact handles/hashes, and accepted ground-truth revision.
Langfuse may mirror that case into a dataset and link it to its source
observation, but the dataset/trace is not the only copy of the case.

Human/LLM/code judgments remain versioned `AgentAssessment` records. A human
annotation becomes ground truth only after an explicit MemForge acceptance
step; an LLM score never becomes ground truth automatically.

## Consequences for issue #258 acceptance

A focused implementation should prove all of the following before adding more
producer types:

1. One reconciler execution that commits `failed` creates exactly one terminal
   runtime event and one deterministic failed assessment.
2. Five internal handled attempts followed by success create no terminal-fail
   assessment; the success event reports the bounded attempt count.
3. A separately scheduled recovery after a durable failed execution creates a
   second execution event under the same logical `operation_id`.
4. Retrying the canonical event write creates no duplicate in SQLite or HANA.
5. Cache hits and unchanged/no-op projections create only the explicitly
   documented terminal result, not extraction or model-call events that did not
   occur.
6. A lifecycle transaction rollback creates neither a success event nor an
   orphan assessment.
7. The Langfuse view groups the recovery family but preserves immutable traces
   per execution; no trace/observation upsert is attempted.
8. Online counts come from the canonical event/assessment store and reconcile
   with the durable run states even when Langfuse export is disabled.
9. A promoted failure can be replayed offline from its protected case manifest
   without relying on retained Langfuse content.

## Design conclusion

The small robust seam is not another matrix of error handlers. It is a single
terminal-outcome recorder owned by the durable operation boundary, backed by a
typed identity model and one provider-neutral persistence contract. OTel and
Langfuse are projections of that fact. Retries are modeled according to whether
they were handled inside the same execution or became a new durable execution,
which prevents both the current blind spot and false duplicate failures.
