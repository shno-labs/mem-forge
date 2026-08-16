# Correlate agent runtime facts, telemetry, and evaluation

Status: Accepted (2026-08-13)

Amended:

- 2026-08-14 to retain one content-free diagnostic runtime fact for each
  provider attempt that fails transport or schema validation. Ordinary
  schema-conformant attempts remain represented only by the logical-call
  outcome.
- 2026-08-16 to define the stable Session, Trace, and observation hierarchy
  used by the Langfuse projection.

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
- `extraction_batch_outcome`.

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
could disclose content, or arbitrary errors. Langfuse annotations, scores, and
datasets remain separate future evaluation adapters rather than methods on the
runtime trace sink.

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
and batch facts; provides bounded reporting and retention; optionally projects
metadata-only traces through the isolated Langfuse adapter; and proves adapter
parity. Case persistence, assessor scheduling, human review, and regression
gating build on separate contracts rather than widening the runtime-event
object.

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
- [Phoenix annotations](https://arize.com/docs/phoenix/tracing/concepts-tracing/annotations-concepts)
