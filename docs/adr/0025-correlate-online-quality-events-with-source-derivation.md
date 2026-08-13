# Correlate online quality events with Source Unit derivation

Status: Accepted (2026-08-13)

## Context

MemForge already records structured-model call metrics, durable Source
Projection and Derivation identity, and Memory lifecycle audit events. Those
records do not answer one important production question: why did a particular
source batch produce no Memory, especially when a candidate was rejected before
it received a Memory ID?

A raw log such as `quote mismatch` is insufficient. It may identify neither the
source revision nor the current Evidence authority, and copying the prompt,
quote, or source body into ordinary logs would violate private-source and
retention boundaries.

Online anomalies also are not ground-truth accuracy labels. A whole-Block
fallback can be valid but less precise; a zero-candidate batch can be expected.
Production observations need an explicit, authorized promotion step before
they become offline golden cases.

## Decision

### Producers emit content-free signals; derivation binds lineage

The canonical OSS module defines a small `QualitySignal` value and one
versioned `AgentEvaluationEvent` envelope. Structured-output, extraction, and
Evidence code emits signals through a request-local collector. A producer does
not know the database, workspace, provider route, or Source type.

The `SourceUnitDeriver` is the single binding seam. After a batch result has
been durably staged, it attaches current Source identity, document and Source
Unit identity, target Source Unit revision, Projection run, Derivation and
batch ID, extraction contract, and the matching Observation revision. This
makes rejected candidates traceable even when no Memory exists. Deterministic
event IDs make retry persistence idempotent.

SQLite and Cloud/HANA implement the same append and bounded-query protocol.
Cloud may fill deployment revision and workspace-scoped storage context, but it
must not define a different taxonomy or source-specific producer.

### Taxonomy separates occurrence from judgment

Each event has one outcome:

- `expected`: successful schema response, exact/canonical localization,
  candidates extracted, or an explicit zero-candidate result;
- `degraded`: work completed through a bounded fallback, such as whole-Block
  Evidence localization or structured-schema fallback recovery;
- `rejected`: model output could not enter the domain, such as an unknown
  Evidence Block or terminal invalid structured response;
- `failed`: provider, deadline, persistence, materialization, or lifecycle work
  failed.

Stable reason codes describe what happened. `degraded` and `rejected` do not
mean that the underlying semantic claim is incorrect. A deterministic invariant
or an adjudicated label is required for that conclusion.

The initial producers cover structured-output outcomes, Evidence Block
admission, quote/Block localization, and batch candidates/zero-candidates. The
same envelope is extended at projection materialization and lifecycle seams;
those modules must not create parallel event stores.

### Default records are content-free and bounded

Default events contain fixed identifiers, enums, counts, offsets, and SHA-256
digests. They never contain raw prompts, source bodies, quote text, Memory
content, provider response/error bodies, credentials, or raw provider URLs.
Model names and machine-readable error codes are bounded labels.

A request-local collector has a fixed maximum. Overflow becomes one aggregate
event instead of unbounded cardinality. Named invariant failures are persisted
exactly. Query APIs require a half-open time window and bounded page size.
Retention and source deletion follow the source-owned event ledger; optional
external metrics/log shipping may retain only the same safe envelope.

Event persistence is best-effort with respect to extraction correctness: a
telemetry-store failure is logged and cannot turn a valid extraction into a
failed derivation. Existing Memory lifecycle audit writes remain their own
required transactional contract and are not weakened by this decision.

### Online reports and offline cases remain separate

Online reports aggregate one bounded cohort with explicit denominators per
event type and breakdowns by source type, model, contract, deployment, outcome,
and reason. Authorized drill-down uses stored lineage to reach existing Source
Projection, Derivation, Evidence, Memory Review, and audit records; the event
does not embed their protected payloads.

Offline case materialization is a separate authorized operation. It pins an
immutable or protected source artifact reference, contract/model configuration,
observed disposition, originating event, label, label provenance, and
adjudication state. The exporter enforces the same workspace/private-source
access predicate as retrieval. A case is not created automatically from an
online event, and replay never reads mutable current-source state.

Confirmed cases may be promoted into the maintained regression suite. Online
rate thresholds detect distribution shifts; offline labels measure accuracy.
Neither substitutes for the other.

## Consequences

All supported Source types—including Confluence, Jira, GitHub, Local Markdown,
Teams, Agent Session, and extension sources—share one instrumentation path.
Adding a connector does not require a new Block or telemetry mechanism.

Operators can measure invalid Block IDs, Evidence localization modes, schema
fallback/failure, and empty extraction without exposing source content. A
dropped candidate remains attributable to the exact current projection and
batch.

This ledger does not replace infrastructure observability or Memory audit. It
provides the correlation contract that allows both to feed a controlled online
to offline evaluation loop.

## References

- [OpenTelemetry event semantic conventions](https://opentelemetry.io/docs/specs/semconv/general/events/)
- [OpenTelemetry log data model](https://opentelemetry.io/docs/specs/otel/logs/)
- [MLflow production trace evaluation](https://www.mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/traces/)
