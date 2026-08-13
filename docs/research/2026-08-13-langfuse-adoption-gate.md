# When MemForge should introduce Langfuse

Date: 2026-08-13

Status: Research recommendation based only on current official Langfuse documentation. Pricing and product/API maturity should be rechecked at the adoption date.

## Recommendation

Introduce the isolated Langfuse adapter in the same vertical slice as the
durable `AgentRuntimeEvent` contract, but keep it disabled until OSS/Cloud
adapter parity and database persistence have passed a deployed smoke test.
Do this **before** building a large custom evaluation UI or scheduler.

The approved first integration is a small, feature-flagged Langfuse Python SDK pilot. The SDK is isolated behind the provider-neutral runtime trace sink and is itself built on OpenTelemetry; MemForge does not require an explicit OTLP pipeline for this phase. Langfuse remains an optional observability and evaluation workbench, not MemForge's product ledger, authorization system, or only copy of evaluation evidence.

In practical terms:

1. Do not add Langfuse to the current runtime-event persistence transaction.
2. Finish and deploy the provider-neutral runtime-event storage contract first.
3. Then add a separate Langfuse Python SDK adapter and run a metadata-only pilot.
4. Add annotation queues next, once selected evaluation cases and accepted human labels can round-trip into the durable `AgentAssessment` model.
5. Enable Langfuse-managed live LLM judges only after a human-calibrated rubric and an approved policy for the exact evaluation input/output stored in Langfuse exist.

## Why not introduce it earlier?

### Langfuse traces are not a durable product audit

Langfuse sampling is client-side and trace-wide: when a trace is not sampled, none of its observations or associated scores is sent. Langfuse also respects the upstream OTel sampling decision. That is appropriate for telemetry cost control, but it cannot replace exact runtime facts needed to investigate an extraction omission. ([Langfuse sampling](https://langfuse.com/docs/observability/features/sampling))

Retention is also independent of references. Current Langfuse documentation says retained traces, observations, scores, and media are deleted by age, and a dataset may continue to reference a trace that has already been deleted. Self-hosted data is indefinite by default unless retention is configured; the built-in retention feature is currently Pro/Enterprise in Cloud and Enterprise Edition when self-hosted. ([Langfuse data retention](https://langfuse.com/docs/administration/data-retention))

Therefore MemForge must retain stable source revision, derivation, batch, candidate/memory, event, and assessment identity independently. Langfuse trace/observation IDs are correlation IDs and workbench targets, not the identity of the product fact.

### The current evaluator API is not a safe OSS dependency

Langfuse's evaluator and evaluation-rule APIs support versioned evaluator definitions, filters, mappings, and sampling, but the current official documentation explicitly calls those endpoints unstable while the evaluation data model is being redesigned. The documented direction is observation-level evaluation; legacy trace-level evaluators are being deprecated. ([Langfuse LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge))

MemForge should therefore integrate these APIs in a Cloud/deployment adapter, not expose Langfuse evaluator/rule objects in the canonical OSS protocols.

## What Langfuse is good at for MemForge

Langfuse is a strong fit once the boundary above exists:

- It is OTel-native and accepts spans from any OTel SDK through an OTLP endpoint. Current v4 ingestion requires `x-langfuse-ingestion-version: 4` for real-time visibility when exporting directly; otherwise current documentation warns of up to ten minutes of delay. ([Langfuse compatibility](https://langfuse.com/docs/compatibility), [OTel integration](https://langfuse.com/integrations/native/opentelemetry))
- Its trace/observation/session UI is useful for correlating an extraction workflow, model calls, evidence localization, admission, and downstream results. Langfuse recommends stable trace structure because evaluator rules, dashboards, experiments, and saved views depend on stable observation names and attributes. ([Langfuse trace best practices](https://langfuse.com/docs/observability/best-practices))
- Scores represent numeric, categorical, boolean, or text assessments and can be attached to a trace, observation, session, or dataset run. Scores can come from an API, an automated evaluator, or a human annotation. ([Langfuse score model](https://langfuse.com/docs/evaluation/scores/data-model))
- Annotation queues let domain experts score selected traces/observations, add comments and corrected outputs, and align an LLM judge with human annotation. Queues can also be managed through an API. ([Langfuse annotation queues](https://langfuse.com/docs/evaluation/evaluation-methods/annotation-queues))
- Live code and LLM evaluators run asynchronously on filtered observations and attach scores to those observations; controlled datasets/experiments support reproducible offline comparisons. ([Langfuse code evaluators](https://langfuse.com/docs/evaluation/evaluation-methods/code-evaluators), [Langfuse LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge))

This covers the workbench and scheduling layer that MemForge should avoid rebuilding prematurely.

## Important constraint: built-in live judges need evaluation content

A metadata-only Langfuse trace is useful for operational diagnosis, but it is not enough for most semantic judges. Langfuse observation-level evaluators only see the matched observation's input, output, and metadata; they do not automatically read sibling or child observations. For an end-to-end evaluation, the application must put the required context on the logical root observation. ([Langfuse observation-level evaluator context](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge))

Direct OTel ingestion maps attributes such as `langfuse.observation.input` and `langfuse.observation.output` into evaluator-visible content. ([Langfuse OTel attribute mapping](https://langfuse.com/integrations/native/opentelemetry), [empty input/output FAQ](https://langfuse.com/faq/all/empty-trace-input-and-output))

This creates a deliberate gate:

- **Tracing pilot:** export no source text, prompt, quote, model response, or Memory content. Use stable IDs, hashes, ranges, counts, event outcomes/reasons, source type, model/provider, prompt/contract version, deployment, and duration only.
- **External scorer:** if protected content must remain inside MemForge, run the scorer against authorized MemForge artifacts and send only the resulting score to Langfuse through its Scores API. Langfuse explicitly supports scores from external evaluation pipelines. ([Scores via API/SDK](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk))
- **Managed Langfuse judge:** enable only when the exact redacted evaluation payload is approved for storage in the selected Langfuse deployment. Create one explicit evaluator/root observation payload rather than copying an entire source document or trace.

Client-side redaction is the mandatory control when content must not leave the application. Langfuse's self-hosted server-side masking is an Enterprise feature and the official docs state that incoming events are written to blob storage before the worker invokes the masking callback, so it is a safety net rather than a substitute for client-side masking. ([Langfuse data masking](https://langfuse.com/self-hosting/security/data-masking))

## Staged adoption gates

### Gate 0 — canonical foundation (now)

Proceed only after all are true:

- `AgentRuntimeEvent` is immutable, bounded, content-free, and saved atomically with the derivation/batch result.
- `AgentAssessment` is a distinct append-only evaluator result; an event is not mislabeled as an evaluation.
- SQLite and HANA implement the same lineage, visibility, idempotency, filtering, and pagination contract.
- Runtime-event trace correlation and trace-sink mapping are deterministic and
  optional; exporter failure cannot alter extraction correctness. Explicit
  OTel/OTLP mapping is deferred until that adapter is needed.
- Deployed smoke proves a missing/rejected extraction can be reconstructed without a trace backend.

**Do not enable Langfuse before this gate.** Packaging the optional adapter is
safe because the no-op sink remains the default; sampled/exported data must
not become the accidental source of truth.

### Gate 1 — metadata-only Langfuse SDK pilot (introduce Langfuse here)

Use a separate runtime trace adapter, not calls in domain code. For the current Python runtime, the Langfuse SDK is the smaller first integration and already uses OpenTelemetry internally. Explicit OTLP remains a later adapter when multiple backends or cross-service traces justify it. ([Langfuse SDK overview](https://langfuse.com/docs/observability/sdk/overview))

Pilot acceptance:

- Feature flag and independent credentials/endpoint; disabling Langfuse changes no product behavior.
- Stable root and operation names for sync, derivation batch, model inference, evidence localization, and admission.
- Filterable, low-cardinality metadata includes source type, event outcome/reason, model/provider, prompt/contract version, release/deployment, and environment; no workspace/source/user IDs are metric labels.
- Automated adapter test proves forbidden content never reaches Langfuse observation metadata.
- Trace-to-`event_id` and `event_id`-to-trace navigation works for a small acceptance cohort.
- Measured ingestion volume, query usefulness, exporter failure behavior, and monthly cost are recorded before raising sampling or retention.

For a low-volume, metadata-only pilot, exporting the complete bounded acceptance cohort is simpler than tuning sampling. Later sampling may reduce ordinary-success traces, but exact anomaly counts continue to come from MemForge's durable ledger.

### Gate 2 — human annotation workbench

Introduce annotation queues after MemForge can promote selected runtime events into immutable evaluation cases. Start with:

- all deterministic schema/evidence/admission failures;
- a deterministic success/control sample;
- user-reported and investigator-selected cases.

Define stable score configs such as `memory_should_exist`, `evidence_correct`, and `admission_correct`. A queue annotation remains a Langfuse score until it is imported, validated, and accepted as a versioned MemForge `AgentAssessment`; only an explicitly accepted human result becomes offline ground truth.

Acceptance:

- every queue item maps to exactly one immutable MemForge case and narrow target observation;
- reviewer visibility is no broader than the underlying source authorization;
- accepted labels can be exported/imported without depending on a retained trace body;
- duplicate imports are idempotent and preserve evaluator/reviewer provenance.

### Gate 3 — live evaluators

Enable Langfuse-managed judges only after:

- a human-labeled calibration set exists and evaluator agreement/error modes are measured;
- evaluator name, rubric/prompt, score config, model, and version are pinned in the MemForge assessment record;
- the evaluation payload policy is approved and tested;
- asynchronous `pending`, `delayed`, `error`, and missing-score states are visible rather than interpreted as success;
- selection is reproducible.

Langfuse's current docs say each evaluator normally draws its own random sample, so multiple evaluators configured with the same percentage generally do not evaluate the same items. When cross-evaluator comparison matters, make the cohort decision in MemForge, tag it, and use identical filters (or 100% evaluation over that selected cohort). ([Langfuse LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge))

Begin with external deterministic scorers plus human queues. Add an LLM judge only for genuinely semantic criteria such as memory usefulness/completeness; schema validity, Block ID existence, quote localization, and admission invariants remain deterministic MemForge checks.

### Gate 4 — offline experiments and release gates

Only after Gate 2/3 results are trustworthy should selected cases become a stable Langfuse dataset/experiment cohort for prompt/model comparisons. Keep the immutable case manifest and accepted assessment in MemForge so trace retention, project migration, or Langfuse replacement does not alter the release evidence.

Do not make a deployment gate depend on a live sampled trend. A release gate runs the same pinned offline cohort and compares named, versioned assessments.

## Cloud or self-hosted?

### Recommended first pilot: Langfuse Cloud with metadata-only data

This is the fastest way to validate value because it avoids operating the Langfuse data plane. The current public pricing page lists a free Hobby tier for POCs, then Core at USD 29/month and Pro at USD 199/month before usage; the page currently lists 30/90-day Cloud access windows for Hobby/Core and three years plus retention controls for Pro. Prices and limits are changeable and must be rechecked before procurement. ([Langfuse pricing](https://langfuse.com/pricing))

Use Cloud only after the selected region, DPA/security posture, credentials, and exported metadata are approved. Do not use real Teams/Confluence/Jira text in the first pilot.

### Self-host only when data residency requires it and an owner accepts the operational cost

Self-hosting is appropriate if meaningful evaluation requires source/model content that cannot be sent to SaaS. It is not a lightweight sidecar: current Langfuse architecture includes web and worker containers plus Postgres, ClickHouse, Redis/Valkey, and S3/blob storage. Docker Compose is documented for testing/low scale and lacks HA, scaling, and backup; production guidance uses Kubernetes or cloud infrastructure. ([Langfuse self-hosting](https://langfuse.com/self-hosting))

The current scaling guide lists minimums of 4 GiB each for web, worker, and Postgres; 8 GiB for ClickHouse; and 1.5 GiB for Redis, plus blob storage. A production self-host should therefore be a separately operated service, not added to MemForge's constrained Cloud Foundry application footprint. ([Langfuse scaling](https://langfuse.com/self-hosting/configuration/scaling))

## Ownership boundary

| Concern | System of record |
|---|---|
| Exact source/derivation/batch/extraction outcome | MemForge `AgentRuntimeEvent` |
| Authorization and protected source/evidence content | MemForge source/artifact stores |
| Operational trace exploration and dashboards | Langfuse/OTel backend |
| Human/code/LLM workbench score | Langfuse, until accepted/imported |
| Accepted versioned assessment and ground-truth status | MemForge `AgentAssessment` / evaluation case |
| Offline release cohort | MemForge immutable case manifest; optionally mirrored to Langfuse datasets |

## Final decision

Package the metadata-only Langfuse SDK adapter with the provider-neutral
foundation, but enable the pilot **only after** durable DB persistence and
SQLite/HANA parity are merged, deployed, and smoke-tested. It remains behind
the trace sink, not a core domain dependency and not live LLM judging.

If that pilot proves faster investigation and useful trace correlation, add annotation queues as the first real evaluation feature. Managed live judges come later, because they require both a calibrated rubric and an explicit decision about what evaluator-visible content may be stored in Langfuse.
