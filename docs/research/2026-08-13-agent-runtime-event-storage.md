# AgentRuntimeEvent storage: product database vs. SAP Cloud Logging

Date: 2026-08-13

## Recommendation

Persist every canonical `AgentRuntimeEvent` in the MemForge workspace database. For SAP BTP Cloud Foundry, that means HANA; for OSS/local it means SQLite, with PostgreSQL as the natural server/self-host adapter when concurrency or scale outgrows a single embedded database.

SAP Cloud Logging should be an **optional observability projection**, not a second source of truth. Do not synchronously dual-write HANA and Cloud Logging from the extraction transaction.

```text
Extraction transaction
  -> Memory / derivation state + AgentRuntimeEvent in one DB commit
  -> after commit: isolated metadata-only trace adapter
       -> current pilot: Langfuse Python SDK
       -> future interoperability: OTel/OTLP to Cloud Logging or other backends
```

This boundary is important because an `AgentRuntimeEvent` is a product fact used for exact audit/evaluation lineage, while SAP Cloud Logging is explicitly an observability service for logs, metrics, and traces built on OpenSearch ([SAP: What Is SAP Cloud Logging?](https://help.sap.com/docs/cloud-logging/cloud-logging/what-is-sap-cloud-logging)).

## Why HANA remains the Cloud source of truth

1. **Atomic correctness.** The event can commit in the same database transaction as its derivation/batch outcome. A remote logging write cannot participate in that transaction without a distributed-transaction problem. A synchronous dual-write can therefore create both split-brain outcomes: product state committed but telemetry missing, or telemetry visible for product state that later rolls back.
2. **Deterministic retention and retrieval.** Cloud Logging retention is configurable only from 1 to 90 days, defaults to 7 days, and is overridden by size-based curation when storage fills; retention changes also apply only to new indices ([SAP: Configuration Parameters](https://help.sap.com/docs/cloud-logging/cloud-logging/configuration-parameters), [SAP: Managing Your Instance](https://help.sap.com/docs/cloud-logging/cloud-logging/managing-your-instance)). SAP also documents automatic deletion of the oldest indices at the maximum storage watermark and possible quality degradation under excessive load ([SAP: Service Plans](https://help.sap.com/docs/cloud-logging/454331d80e3b42b1804d83a672cf098b/service-plans)). That is appropriate for operational telemetry, not for the only copy of an exact product fact.
3. **Workspace/source authorization.** HANA queries can enforce MemForge's existing workspace and source-visibility contract. Cloud Logging offers Identity Authentication and group-based dashboard access, but that is an observability access model, not MemForge's source-level read contract ([SAP: What Is SAP Cloud Logging?](https://help.sap.com/docs/cloud-logging/cloud-logging/what-is-sap-cloud-logging)). A Cloud Logging record should therefore contain only the minimum technical correlation needed to return to an authorized MemForge audit lookup.
4. **Data protection.** SAP states that Cloud Logging is not designed to collect, process, or store personal or business data and instructs customers to ensure such data is not sent ([SAP: Data Protection and Privacy](https://help.sap.com/docs/cloud-logging/cloud-logging/data-protection-and-privacy?version=Cloud)). Never project source text, prompts, quotes, memory content, owner/user identifiers, attachment data, or provider responses. Prefer `event_id`, event class, outcome/reason, deployment/prompt/schema version, source type, bounded counts/latency, and trace/span correlation. If source/unit correlation is needed externally, use a non-reversible scoped token and resolve it through the authorized DB API.
5. **Durability and recovery.** HANA Cloud encrypts data, redo logs, and backups at rest and automatically backs up database instances ([SAP HANA Cloud: Data Storage Security](https://help.sap.com/docs/hana-cloud-database/sap-hana-cloud-sap-hana-database-security-guide/data-storage-security), [SAP HANA Cloud: Backup and Recovery](https://help.sap.com/docs/r/9ae9104a46f74a6583ce5182e7fb20cb/latest/en-US/89d71f01daca4ecaaa069d6a060167f5.html)). This does not replace an application retention policy, but it is the right persistence tier for product-owned records.

## What SAP Cloud Logging should contain

Use Cloud Logging for fast operational exploration, dashboards, alerts, latency/error correlation, and trace-to-event navigation. SAP supports OTLP ingestion for logs, metrics, and traces over gRPC with mTLS; service-binding client certificates default to 90-day validity and must be rotated or ingestion stops ([SAP: Ingest via OpenTelemetry API Endpoint](https://help.sap.com/docs/cloud-logging/cloud-logging/ingest-via-opentelemetry-api-endpoint)).

Recommended projection policy:

- export all `failed`, `rejected`, and `degraded` outcomes when budget permits;
- sample ordinary successes at the telemetry layer, while retaining their canonical DB events according to the product retention policy;
- keep metric attributes low-cardinality; never use workspace/source/document/memory/event IDs as metric labels;
- correlate projected spans/events with `memforge.agent.event_id`, `trace_id`, and `span_id`;
- alert on exporter failures and certificate-expiry risk, but never fail or roll back extraction because Cloud Logging is unavailable.

OpenTelemetry defines telemetry as signals emitted to make a system observable ([OTel: Signals](https://opentelemetry.io/docs/concepts/signals/)). OTLP exporters retry transient failures with exponential backoff, but retry behavior is not a transaction or permanent delivery guarantee ([OTel: OTLP Exporter](https://opentelemetry.io/docs/specs/otel/protocol/exporter/)). An OTel Collector is useful in production because it can perform retries, batching, encryption, and sensitive-data filtering outside the application process ([OTel: Collector](https://opentelemetry.io/docs/collector/)).

## Dual-write and delivery semantics

Do **not** implement a synchronous application dual-write to HANA and Cloud Logging.

Use one of two explicitly named delivery levels:

1. **Best-effort observability (appropriate first increment):** after the DB commit, project the event through an isolated trace sink. The current pilot uses the Langfuse Python SDK; an explicit OTel/OTLP sink is optional future interoperability. Missing telemetry is acceptable because the DB remains complete and queryable.
2. **At-least-once telemetry delivery (only if a concrete acceptance criterion requires it):** write a transactional outbox row or durable projection checkpoint in the same DB transaction, then let a worker export and mark progress. Make the receiver projection idempotent by `event_id`. Even here, Cloud Logging still is not the source of truth because its configured/size-based retention can remove the record.

Do not add an outbox merely because an exporter exists. Add it when the product requirement says that a specific class of events must reliably reach an external backend within a measured SLA. This keeps the MVP small while preserving a clean upgrade path.

## OSS and self-hosted editions

The same architectural contract is reasonable outside SAP:

| Deployment | Canonical store | When it is appropriate | Optional observability |
|---|---|---|---|
| Local/single-node OSS | SQLite in the existing workspace database | Small-to-medium workloads and one application node. SQLite provides ACID, serializable transactions and crash-safe atomic commit ([SQLite: Transactional](https://www.sqlite.org/transactional.html), [SQLite: Isolation](https://www.sqlite.org/isolation.html)). | No backend by default; optional Langfuse SDK pilot or a future OTLP adapter. |
| Server/multi-worker self-host | PostgreSQL adapter implementing the same protocol | Multiple workers, higher concurrent write/query load, HA/backup requirements, or centralized operations. PostgreSQL WAL is the foundation for committed-transaction integrity and crash recovery ([PostgreSQL: WAL](https://www.postgresql.org/docs/current/wal-intro.html)); row-level security can enforce per-row policies when the deployment uses database-enforced tenancy ([PostgreSQL: Row Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)). | OTel Collector to any chosen backend, such as self-hosted Langfuse/Phoenix/Grafana or a managed service. |
| SAP BTP Cloud | HANA workspace database | Shared Cloud service with existing workspace/source visibility and transactional product state. | Optional Langfuse SDK pilot; future OTel/OTLP to Cloud Logging only when needed. |

Self-hosted MemForge must remain correct when no observability backend is installed. SQLite/PostgreSQL/HANA adapters should share the same event schema, idempotency, pagination, visibility, and retention semantics; only the storage implementation differs.

## Volume and cost controls

Keep the DB ledger compact rather than turning it into a second tracing backend:

- persist only bounded, high-value contract facts such as structured-output, evidence-localization, memory-admission, and batch outcomes;
- do not persist model token streams, every internal span, stack traces, arbitrary error strings, or copied source/model content;
- use fixed columns for common filters and bounded versioned metadata for rare fields;
- index from measured audit queries, chiefly workspace/time and workspace/event/outcome/time; avoid speculative indexes;
- define a configurable application retention job. Runtime-event, evaluation-case, assessment, source-content, and external telemetry retention are separate policies;
- before expiring a runtime event selected for long-lived regression use, promote the needed immutable identifiers/hashes into an `AgentEvaluationCase`; promotion must not extend raw source-content retention;
- monitor row rate, DB bytes, purge lag, trace-sink failures, and—if introduced—OTLP or Cloud Logging rejected/curated volume.

The correct cost split is therefore: **small unsampled correctness facts in the product DB; richer but lossy/sampled operational views in the observability backend.** If DB volume becomes unexpectedly high, first narrow what qualifies as a product fact or adjust explicit retention; do not silently sample away failures from the canonical ledger.

## Decision

- **Cloud:** persist in HANA; optionally project metadata-only Langfuse traces
  in the current pilot. Add OTel/OTLP to SAP Cloud Logging only for a later
  operational requirement.
- **OSS/self-host:** persist in SQLite by default; add PostgreSQL for multi-node/high-concurrency installations; keep external observability optional.
- **Never:** make SAP Cloud Logging/Langfuse the only copy, synchronously dual-write remote telemetry in the product transaction, or send customer/business content to Cloud Logging.
- **Later, if required:** add a DB-backed outbox/checkpoint for measured at-least-once export, not for product correctness.
