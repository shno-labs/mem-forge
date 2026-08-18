# Langfuse Annotation Queue round trip for offline calibration

Date: 2026-08-18

Status: Research recommendation for the next bounded part of Issue #258. This note uses only current official Langfuse documentation, public API/OpenAPI, and repository source at commit [`7736acc`](https://github.com/langfuse/langfuse/tree/7736acc12bd97e382f3329e43ac3f0abd964a549). It does not change the MemForge ADR or product code.

## Executive recommendation

Use Langfuse as an optional human-review workbench, not as the task, authorization, or ground-truth authority:

```text
authorized MemForge annotation task
  -> durable provider-neutral export bridge in the MemForge DB
  -> one protected Langfuse root observation per reviewer task
  -> Langfuse Annotation Queue item
  -> Langfuse human ANNOTATION Score
  -> validated one-shot import
  -> immutable proposed AgentAssessment in the MemForge DB
  -> existing two-reviewer adjudication
  -> accepted ground truth
```

The next slice should implement exactly that round trip for an already-approved calibration result. It should not move cohort selection, source authorization, content-policy authority, assessment identity, or ground-truth acceptance into Langfuse.

The clean integration needs both channels:

- the Langfuse SDK/OTLP path creates the protected trace/observation that the reviewer can inspect;
- the Public REST API manages the queue workflow and reads completed human scores.

OTLP alone cannot create or assign queues, inspect queue completion, manage score configs, or retrieve human scores. Langfuse's compatibility matrix lists OTLP trace ingestion, score ingestion, and Scores API reads as separate capabilities. ([Compatibility matrix](https://langfuse.com/docs/compatibility), [OpenTelemetry integration](https://langfuse.com/integrations/native/opentelemetry))

## Official product and API constraints

| Area | Current official behavior | Consequence for MemForge |
|---|---|---|
| Queue subject | A queue item points to one `TRACE`, `OBSERVATION`, or `SESSION`. Its public representation contains identity, status, completion time, and timestamps, but no annotation value. ([Annotation Queue docs](https://langfuse.com/docs/evaluation/evaluation-methods/annotation-queues), [OpenAPI schemas](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/public/generated/api/openapi.yml)) | Import labels from Scores, not from Queue Items. Prefer an observation target because Langfuse v4 is observation-first. |
| Human result | Manual annotation creates a Score. Scores identify their subject and can expose `configId`, `queueId`, and `authorUserId` when `fields=details,subject,annotation` is requested. ([Scores API v3](https://langfuse.com/docs/api-and-data-platform/features/scores-api), [score data model](https://langfuse.com/docs/evaluation/scores/data-model)) | Join a completed item to exactly one expected Score by queue, subject, config, and author. Never infer the reviewer from the item alone. |
| Item completion | The current UI completion mutation only marks the item completed and records the annotator; it does not transactionally validate that all expected Scores exist. The public item schema does not expose the annotator. ([completion implementation](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/src/features/annotation-queues/server/annotationQueueItemsRouter.ts), [public schema](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/src/features/public-api/types/annotation-queues.ts)) | `COMPLETED` is necessary but not sufficient. Import must fail closed on a missing, extra, wrong-author, wrong-config, or wrong-subject Score. |
| Assignment | Queue assignments make relevant queues prominent and accept only project members, but the official release note explicitly says assignments do not restrict access to other project members. Assignment is queue-level, not item-level. ([assignment release note](https://langfuse.com/changelog/2025-08-07-annotation-queue-assignments)) | Treat assignment as workflow routing only. MemForge performs authorization before export and validates the expected `authorUserId` on import. |
| Assignment API | Public API exposes create/delete assignment but no list endpoint. The current implementation uses upsert for create and treats delete of an absent assignment as success. ([OpenAPI](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/public/generated/api/openapi.yml), [service implementation](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/src/features/annotation-queues/server/publicAnnotationQueueService.ts)) | Store the expected local-to-Langfuse reviewer binding in MemForge. Assignment writes may be retried, but assignment is not proof of authorization or completion. |
| Queue item idempotency | Queue Item POST accepts no client item ID. The service performs a direct create, and the Prisma schema has only a non-unique index over object/queue identity. Duplicate POSTs can therefore create duplicate tasks. ([create implementation](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/src/features/annotation-queues/server/publicAnnotationQueueService.ts), [Prisma schema](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/packages/shared/prisma/schema.prisma)) | MemForge needs a local unique bridge and single-writer lease. After an ambiguous POST, scan and adopt one exact match; multiple matches are a reconciliation conflict, not a reason to post again. |
| Score identity and edits | A Score ID may be used as an idempotency key. Current v4 update semantics also require the same name and timestamp date. Scores remain editable, while traces and observations are immutable after ingestion. ([score data model](https://langfuse.com/docs/evaluation/scores/data-model), [update semantics](https://langfuse.com/faq/all/tracing-data-updates)) | Snapshot and hash the imported Score version. Never re-ingest the annotation observation. After a successful one-shot import, a later remote Score change is drift requiring review, not an in-place AgentAssessment update. |
| Score config | Queue creation requires at least one Score Config. The conceptual data-model page calls configs immutable, but the current public API exposes PATCH and the management guide says existing configs may be changed. ([Score Config docs](https://langfuse.com/faq/all/manage-score-configs), [OpenAPI](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/public/generated/api/openapi.yml)) | Use versioned config names, pin `configId` plus a schema fingerprint, and refuse import if the config drifts. Do not patch a config already used by a MemForge rubric. |
| Pagination | Queue and Queue Item lists use page/limit metadata. Scores v3 uses a cursor, defaults to 50, caps at 100, and requires all filters to be repeated on every page because the cursor encodes position only. ([OpenAPI](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/public/generated/api/openapi.yml), [Scores API v3](https://langfuse.com/docs/api-and-data-platform/features/scores-api)) | Normal polling uses the known item ID. Full page scans are only for ambiguous-create recovery. Score import exhausts the cursor with unchanged filters and deduplicates by Score ID. |
| API lifecycle | Queue endpoints are currently unversioned and the generated OpenAPI `info.version` is empty. Scores v3 is the recommended read API; v1/v2 score reads are deprecated. Cloud moves continuously, while self-hosted deployments pin their server version. ([Public API](https://langfuse.com/docs/api-and-data-platform/features/public-api), [compatibility](https://langfuse.com/docs/compatibility), [versioning policy](https://langfuse.com/self-hosting/upgrade/versioning)) | Wrap only the endpoints used here, validate response schemas, and run contract tests against the configured Cloud or pinned self-hosted version. Do not use deprecated score reads. |

## Reviewer independence and blinding

A shared Langfuse subject is not suitable for MemForge's independent-review requirement. The current Annotation Form loads all `ANNOTATION` Scores attached to the subject and does not filter them by queue or author. A second reviewer can therefore see or edit the first reviewer's Score. ([annotation form](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/src/features/scores/lib/transformScores.ts), [queue drawer](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/src/features/annotation-queues/components/shared/AnnotationDrawerSection.tsx))

For the existing two-reviewer calibration contract:

1. Export a distinct root observation for each `(result, rubric, reviewer)` task. The approved case manifest and candidate output may be identical, but the Langfuse subject IDs are not shared.
2. Put reviewer tasks in reviewer-specific queues and assign exactly that reviewer to the queue. This is operational routing, not security.
3. Do not include the peer task ID, peer queue ID, peer reviewer, or peer Score in observation metadata or content.
4. Import only a Score whose `authorUserId` matches the durable reviewer binding for that task.
5. Preserve the existing MemForge rule that two different local reviewer principals are required before adjudication.

This gives practical queue-level blinding, not a security boundary: every project member can still navigate other project data. If security-grade blinding is required, use separate Langfuse projects per reviewer or keep review in a MemForge-owned UI. Queue assignments cannot provide that guarantee.

The current Langfuse source also enforces a maximum of one Annotation Queue on the Cloud Hobby plan. Two reviewer-specific queues therefore require a plan that permits them; otherwise the Langfuse queue UI is not a valid implementation of this two-reviewer workflow. ([queue creation implementation](https://github.com/langfuse/langfuse/blob/7736acc12bd97e382f3329e43ac3f0abd964a549/web/src/features/annotation-queues/server/publicAnnotationQueueService.ts))

## Minimal recommended contract

### Administrative bootstrap

Keep setup outside the per-task runtime:

- Create one versioned CATEGORICAL Score Config, for example `mf_calibration_v1`, with exact labels `pass`, `fail`, and `needs_review`.
- Create one bounded queue per reviewer and rubric version, using deterministic unique names.
- Assign the expected Langfuse project user to each queue.
- Persist an administrator-approved mapping from local reviewer principal to Langfuse `projectId`, `userId`, `queueId`, `scoreConfigId`, and a fingerprint of the config's name, type, categories, and description.

The first product slice should validate this configuration, not build a general Langfuse administration console.

### Durable provider-neutral bridge

Add one small provider-neutral record such as `ExternalAnnotationTask`; put Langfuse calls behind an adapter. Minimum fields:

| Class | Fields |
|---|---|
| MemForge authority | `task_id`, `result_id`, `content_policy_id`, `criterion`, `rubric_version`, local `reviewer_id` |
| Provider binding | `provider`, `provider_project_ref`, expected provider reviewer ID, `queue_id`, `score_config_id`, config fingerprint |
| External subject | deterministic `trace_id`, generated `observation_id`, `queue_item_id`, protected payload hash |
| Delivery | technical phase (`prepared`, `subject_ready`, `queued`, `imported`) plus bounded error/conflict code and timestamps |
| Imported version | provider Score ID, Score `updatedAt`, Score fingerprint, resulting `assessment_id` |

The row contains no case manifest, candidate output, source text, free-form comment, secret, or API key. Those remain in their existing authorities. Enforce local uniqueness for:

- `(provider, provider_project_ref, task_id)`;
- `(provider, provider_project_ref, queue_id, observation_id)`;
- `(provider, provider_project_ref, score_id)`.

`task_id` should be deterministic from `result_id + content_policy_id + criterion + rubric_version + reviewer_id`. This prevents duplicate reviewer work while allowing the same result to be reviewed by two independent people.

### Protected subject export

1. Re-run current Source authorization and materialize the existing `AgentEvaluationAnnotationTask` through the immutable content policy.
2. Require the approval to cover the configured external Langfuse project and intended reviewer. If the current policy does not authorize external persistence, create a new immutable export authorization receipt; do not silently broaden `human_calibration_v1`.
3. Create one root observation through the current GA Langfuse SDK. Put only the policy-approved case manifest in `input` and candidate output in `output`; do not copy them into metadata, tags, names, logs, or Scores.
4. Use `Langfuse.create_trace_id(seed=task_id)` for a deterministic W3C trace ID. The SDK cannot accept an arbitrary observation ID, so capture the generated observation ID in the bridge before ending/flushing the observation. Langfuse documents 32-hex trace IDs, 16-hex observation IDs, deterministic trace IDs, and direct access to the generated observation ID. ([instrumentation IDs](https://langfuse.com/docs/observability/sdk/instrumentation))
5. Never re-ingest a finished observation. Langfuse v4 explicitly warns that a second record with the same ID creates duplicates and inconsistent reads rather than a reliable update. ([immutable tracing data](https://langfuse.com/faq/all/tracing-data-updates))
6. After the observation is durable, POST one `OBSERVATION` Queue Item and store its returned item ID.

This path must remain separate from the existing metadata-only runtime trace sink. Enabling annotation export must not enable content capture for ordinary production traces.

### Retry and reconciliation rules

- A local single-writer lease owns each `task_id` while it performs external writes.
- Queue/config lookup and assignment writes are safe to retry after validating exact identity.
- Queue Item POST is not blindly retried. If the response is lost, page through that one controlled queue and match exact `objectType=OBSERVATION` plus `objectId=observation_id`.
  - zero matches: retry once under the same lease;
  - one match: adopt its item ID;
  - more than one: persist `duplicate_queue_item` and stop.
- Normal progress polling calls GET for the known item ID; it does not repeatedly scan every queue.

These phases are external-delivery recovery state, not a new evaluation or Memory business lifecycle.

### One-shot import

When the known Queue Item is `COMPLETED`, query Scores v3 with the narrow filters that Langfuse supports:

```text
source=ANNOTATION
queueId=<expected queue>
authorUserId=<expected Langfuse reviewer>
configId=<pinned label config>
traceId=<task trace>
observationId=<task observation>
fields=details,subject,annotation
limit=100
```

Repeat the same filters on every cursor page. Accept exactly one Score only when all of these hold:

- the item is still `COMPLETED` and has `completedAt`;
- Score source is `ANNOTATION`;
- queue, subject kind/ID, trace ID, config ID, score name/type, and author all equal the bridge;
- current Score Config fingerprint equals the pinned fingerprint;
- value is exactly one of `pass`, `fail`, or `needs_review`;
- no second matching Score exists.

Map the Score to the existing `record_human_annotation` operation using the local reviewer principal, pinned rubric version, expected criterion, imported label, content-policy ID, and a fixed bounded reason such as `langfuse_annotation`. In one MemForge DB transaction, append the immutable AgentAssessment and mark the bridge imported with the Score version/fingerprint and assessment ID.

The imported AgentAssessment is a proposal, not accepted ground truth. Existing adjudication still requires two completed human assessments from distinct local reviewer principals over the same result, policy, criterion, and rubric version.

Store `score.updatedAt` as part of the imported version fingerprint, but do not infer a cross-record ordering guarantee between Queue Item completion and Score ingestion. If a later reconciliation sees the same remote Score with a different fingerprint, record `external_annotation_changed` and require an explicit new task or human decision. Do not overwrite, delete, or automatically supersede the imported AgentAssessment.

## API and deployment notes

- Use project-level Basic Auth with the existing server-side Langfuse public/secret key binding. Never place the secret in a browser or bridge row. ([Public API authentication](https://langfuse.com/docs/api-and-data-platform/features/public-api))
- Call `GET /api/public/v3/scores`, not deprecated v1/v2 reads. Scores v3 is available on Langfuse Cloud and self-hosted `v3.179.0+`; pin and test the self-hosted server version. ([Scores API v3](https://langfuse.com/docs/api-and-data-platform/features/scores-api))
- Cloud is continuously upgraded. Contract-test the exact response fields used here, especially the unversioned Queue API. For self-hosting, test the pinned image before upgrade.
- The integration needs a bounded polling schedule in the existing offline-evaluation worker. It does not need a new service, OTel Collector, webhook platform, or export outbox for this first slice.
- Emit content-free counters/audit facts for `exported`, `queued`, `completed`, `imported`, `duplicate_queue_item`, `score_mismatch`, and `external_annotation_changed`; never put candidate content or free-form comments in telemetry.

## Acceptance checks for the bounded slice

1. One already-authorized calibration result is exported without changing ordinary metadata-only telemetry behavior.
2. Re-running export for the same task adopts the existing bridge/item and does not create another observation or Queue Item.
3. A reviewer completes one configured label in Langfuse; import creates exactly one immutable human AgentAssessment with the expected local reviewer and policy provenance.
4. Re-running import is a no-op returning the same assessment.
5. Wrong author, wrong config, missing/extra Score, duplicate Queue Item, config drift, and post-completion Score edits fail closed with self-contained, content-free audit records.
6. Two reviewer-specific subjects do not expose peer Scores in the normal queue UI; two imported assessments remain proposals until existing adjudication accepts them.
7. The same provider-neutral contract and adapter tests run with SQLite and HANA stores; only credential resolution and storage implementation differ.

## Explicit non-goals

- Langfuse as the authoritative task ledger, authorization engine, or ground-truth store.
- Replacing the existing MemForge human-annotation and adjudication invariants.
- Using queue assignment as a security or source-visibility boundary.
- Reusing one Langfuse subject for two supposedly blinded reviewers.
- Importing comments, corrected outputs, or arbitrary TEXT Scores into AgentAssessment in this slice.
- Automatically creating users, projects, plans, or a general queue administration UI.
- Automatically repairing or deleting duplicate remote objects.
- Re-ingesting or updating protected observations after they have been flushed.
- OTLP as a substitute for the Annotation Queue and Scores REST APIs.
- Release gating, baseline comparison, or automatic production repair.
