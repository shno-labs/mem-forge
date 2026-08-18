# Separate online assessment from offline evaluation execution

- Status: Accepted
- Date: 2026-08-18
- Coordinates: Issue #258 and ADR 0025

## Context

ADR 0025 owns the provider-neutral evaluation data model: unsampled
`AgentRuntimeEvent` facts, versioned `AgentAssessment` judgments, immutable
offline cases and cohorts, accepted ground-truth revisions, pinned runs and
results, calibration, and optional Langfuse projection. It deliberately did
not settle how a long-running service invokes those capabilities.

Calling every automatic check “online evaluation” and every operator command
“offline evaluation” is insufficient. A scheduled replay is still offline,
while a sampled semantic assessment of live traffic is still online. Treating
the CLI as the execution owner also fails for Cloud and Docker services: a
terminal disconnect must not abandon work, and UI, API, CI, and CLI must not
grow separate caching, authorization, or gate behavior.

## Decision

### Define online and offline by the evaluated boundary

| Boundary | Online Agent Evaluation | Offline Agent Evaluation |
| --- | --- | --- |
| Input | admitted facts from real product executions | an immutable case/reference cohort and pinned candidate manifest |
| Trigger | automatic at an admitted production seam | explicit API/UI/CLI/CI request, approved schedule, version change, incident curation, or calibration work |
| First evaluator | constant-time deterministic rules over the full admitted denominator | deterministic replay checks followed only by the semantic evaluators in the pinned suite |
| Product latency | no remote judge or human dependency; post-commit work cannot change the product outcome | asynchronous and outside Source Sync or request latency |
| Authority | detects and explains runtime behavior; it cannot approve a release or repair a Memory | may advise or gate a release under an approved policy; it cannot mutate live product state |
| Human role | bounded anomaly review or sampling that may propose an offline case | ground-truth curation, judge calibration, disagreement review, and assigned annotation |

An ordinary extraction or reconciliation operation automatically records its
eligible online facts and deterministic assessments. It does not call an LLM
judge for every production item. A separately approved sampler may select a
bounded committed event for asynchronous semantic assessment or promotion into
an offline case. Sampling never removes the unsampled runtime fact, and the
remote assessment never gates the Source transaction.

Offline execution occurs when a prompt, model, rubric, schema, contract,
replay harness, or supported execution variant changes; when CI or an operator
selects a stable `quick`, `scheduled`, or `release` profile; or when an online
incident is promoted into a regression case. A timer may trigger a scheduled
profile, but the pinned cohort replay remains offline evaluation.

The feedback loop is explicit:

```text
live operation -> online fact/assessment -> selected immutable case
              -> offline comparison/gate -> release -> new live monitoring
```

### Put execution behind one application service

The provider-neutral offline-evaluation application service owns manifest
validation, authorization, identity, exact cache reuse, evaluator ordering,
side-effect isolation, persistence, comparison, and gate calculation. HTTP,
Admin UI, CLI, schedulers, and CI are thin control-plane adapters to that
service. They never select tables, assemble evaluator outputs, or implement
their own verdict rules.

For a long-running service, run admission is durable before the caller receives
the `run_id`. A service-owned worker claims admitted work through a bounded
lease, executes the pinned run, and records one idempotent terminal state.
Lease, heartbeat, and recovery fields are execution metadata at the run
boundary, not another evaluation domain object or product lifecycle. A process
restart may resume the same run; it cannot create an unpinned replacement run
or silently remove an item from the denominator.

A CLI may submit, poll, wait, render a report, and translate an approved gate
verdict into a process exit status. It does not open a service database
directly, own the long-running evaluation process, schedule recurring work, or
contain cache and gate policy. A trusted in-process call remains useful for
tests and controlled operator smoke, but it is not the production service
execution contract.

### Keep release decisions separate from runtime monitoring

An `AgentEvaluationReleaseGate` is a pure, versioned policy over one complete,
pinned offline run and, when required, a paired baseline on the same cohort.
The policy records its exact inputs and verdict. It does not query current live
traffic or the latest external experiment at decision time.

Deterministic safety and authority failures may block immediately. Semantic
criteria remain advisory until the exact judge identity has an approved
calibration result. Missing results, evaluator errors, excessive unknowns, a
cohort mismatch, or unavailable ground truth remain explicit non-pass outcomes
according to the selected gate policy; they never collapse into success. HTTP
and UI present the recorded verdict, while a CLI or CI adapter maps it to its
native status or exit code.

### Use Langfuse for optional workbench experience, not execution authority

The normal human annotation experience is an authorized UI such as a MemForge
annotation view or an approved Langfuse Annotation Queue, not a CLI prompt.
Queue export and Score import are control-plane integrations. An imported
annotation remains a proposed immutable `AgentAssessment` until MemForge
rechecks current Source access, the content-policy receipt, reviewer mapping,
subject identity, and idempotency. SQLite/HANA remains authoritative for
accepted ground truth and release verdicts.

Langfuse may display online projections, offline experiment comparisons, and
human annotations. Its availability, retention, sampling, dataset version, or
evaluator lifecycle cannot determine whether an evaluation run completed or a
release passed.

### Keep deployment adapters small

The single-node OSS Docker profile may host the evaluation worker beside the
existing embedded Source Sync worker in the API container and use the same
SQLite store. Host CLI, `docker compose exec`, Admin UI, and HTTP clients call
the same application service. A third container is not required initially.

A separate self-hosted worker is justified only by measured isolation or
throughput needs. Adding one also requires a store/runtime topology that safely
supports the extra writer; it is not enabled by pointing multiple uncoordinated
processes at the single-node SQLite volume. A future Postgres adapter may use
the same store contract for multi-worker operation.

Cloud keeps the same service and store contracts. Its HANA, Cloud Foundry
worker, credential binding, and capacity consequences are recorded separately
in the Cloud repository rather than becoming OSS domain semantics.

## Current implementation boundary

At acceptance of this ADR, MemForge automatically records online runtime facts
and deterministic assessments, persists offline cases/cohorts/runs/results,
executes deterministic replay and a calibration-only semantic shadow judge,
and reads metadata-safe reports through the shared application service.

The deployed offline smoke calls that service in-process. Durable service
admission and lease recovery, public self-hosted/Cloud run endpoints, scheduled
profiles, Langfuse annotation import, and the release-gate policy/endpoint are
future Issue #258 implementation. This ADR is their contract, not evidence that
those entry points are already deployed.

## Consequences

- Product ingestion never waits for a remote semantic judge or human review.
- Online incidents become durable offline regressions only through explicit,
  authorized, deduplicated promotion.
- Cloud and self-hosted deployments share evaluation behavior while choosing
  different process and storage adapters.
- CLI remains useful for operators and CI without becoming a second execution
  engine.
- No Redis, Kafka, external scheduler, additional Docker container, or new
  managed Cloud service is required by the first execution-plane increment.
- Capacity is split only after measured queue delay, resource contention, or
  availability requirements justify the operational cost.

## Acceptance

1. A production extraction records eligible deterministic online assessments
   without waiting for a remote judge, Langfuse, or human input.
2. Submitting the same pinned offline specification through UI, API, CLI, or CI
   resolves to the same run identity, cache behavior, report, and gate policy.
3. Disconnecting the caller after admission does not cancel or duplicate the
   run; worker recovery preserves the pinned denominator.
4. Offline execution cannot mutate live Source, Memory, lifecycle, Review, or
   vector state.
5. Langfuse unavailable or disabled does not prevent run completion,
   annotation persistence already accepted by MemForge, or gate calculation.
6. The default OSS Docker topology completes one bounded run without requiring
   a third container or direct CLI access to SQLite.

## References

- [ADR 0025: Correlate agent runtime facts, telemetry, and evaluation](./0025-correlate-online-quality-events-with-source-derivation.md)
- [Langfuse Annotation Queues](https://langfuse.com/docs/evaluation/evaluation-methods/annotation-queues)
- [Langfuse experiments in CI/CD](https://langfuse.com/docs/evaluation/experiments/experiments-ci-cd)
