# Correlate agent runtime facts, telemetry, and evaluation

Status: Accepted (2026-08-13)

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
2. OpenTelemetry is an optional observability projection. Spans represent
   duration-bearing work; bounded runtime facts become span events or
   EventRecords; metrics use low-cardinality aggregates; free-form diagnostics
   remain logs. OTLP is the interoperability boundary.
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
This required product audit is distinct from optional OTLP shipping. An OTLP
exporter, metric sink, or asynchronous evaluator may fail without changing the
committed extraction result; the outbox retries projection after commit.

### Use a bounded runtime taxonomy

Stable event names identify occurrence classes, initially:

- `structured_output_outcome`;
- `evidence_admission_outcome`;
- `evidence_localization_outcome`;
- `extraction_batch_outcome`.

Outcomes are `expected`, `degraded`, `rejected`, or `failed`; stable
low-cardinality reason codes explain the result. These values describe runtime
behavior, not semantic correctness labels.

The collector is capped. If it overflows, it preserves exact denominator
counts by coalescing excess occurrences by `(event_name, outcome, reason_code)`
instead of replacing them with an unrelated overflow event. Event and query
payloads are bounded and versioned.

### Map to OpenTelemetry without making it the ledger

Use stable span names for source sync, derivation batch, model call, Evidence
localization, lifecycle application, and asynchronous evaluator execution.
Sampling-relevant attributes such as operation, source type, provider/model,
contract version, and deployment revision are set when the span starts.

Each durable runtime event projects to the active span using its stable event
name and content-free attributes. A post-hoc evaluator creates a linked
`EVALUATOR` span and emits `gen_ai.evaluation.result`; that standard event is
used only for a real `AgentAssessment`, never for the underlying runtime fact.
OpenInference mappings may add evaluator/annotation compatibility without
changing the OSS domain object.

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

### Promote live facts into offline cases explicitly

Promotion records source/revision lineage, event IDs, artifact handles,
contract/prompt/schema/model/deployment versions, selection rule, observed
output/disposition, expected output, label provenance, and adjudication
revision. Cases are immutable and deduplicated.

Offline evaluation replays a fixed cohort against a candidate change and
compares deterministic, LLM, and human assessments on that same cohort.
Human-reviewed cases are reported separately from sampled controls. A model or
prompt change cannot silently replace the dataset.

## Consequences

All Source types—including Teams, Confluence, Jira, GitHub, Local Markdown,
Agent Session, and extensions—share one instrumentation seam. Connectors do not
need their own Block, trace, or evaluation mechanism.

SQLite and HANA implement the same append/query semantics, stable ordering,
idempotency, and filters. Cloud adds workspace partition, visibility checks,
deployment metadata, and a transactional outbox, but no Cloud-only taxonomy or
source-specific path.

The first increment persists structured-output, Evidence admission/localization,
and batch facts; provides a bounded content-free report and OTel projection;
and proves adapter parity. Case persistence, assessor scheduling, human review,
and regression gating build on the separate contracts rather than widening the
runtime-event object.

## References

- [OpenTelemetry GenAI agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)
- [OpenTelemetry GenAI evaluation event](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-events.md#event-gen_aievaluationresult)
- [OpenTelemetry sampling](https://opentelemetry.io/docs/concepts/sampling/)
- [OpenInference annotations](https://arize-ai.github.io/openinference/spec/annotations.html)
- [MLflow automatic evaluations](https://mlflow.org/docs/latest/genai/eval-monitor/automatic-evaluations/)
- [Langfuse LLM-as-a-judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)
- [Phoenix annotations](https://arize.com/docs/phoenix/tracing/concepts-tracing/annotations-concepts)
