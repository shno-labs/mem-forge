# Memory Evaluation Mechanism

> Status: Final design for implementation planning
> Date: 2026-05-24
> Scope: Audit memory decisions, harden memory write paths, verify DB/search-index consistency, and create a recurring evaluation loop for extraction, lifecycle, and retrieval quality.

## Decision

MemForge will add a **Memory Evaluation Mechanism** made of four cooperating parts:

1. **Memory Audit Ledger**: an append-only operation log for memory decisions and outcomes.
2. **Safe Memory Write Path**: a refined write boundary so memory mutations cannot bypass SQLite, FTS5, ChromaDB, and audit coordination.
3. **Daily Deterministic Health Checks**: automated consistency checks across DB state, FTS5 rows, memory Chroma IDs, and document Chroma IDs.
4. **Periodic Evaluation Loop**: weekly agent review and monthly/release replay fixtures for semantic quality, lifecycle behavior, and retrieval impact.

The weekly evaluator does not mutate memories. It produces findings and recommendations. Memory changes still happen through normal sync, review, admin, or engineering workflows.

## Why This Exists

MemForge currently records useful but incomplete operational history:

- `sync_history` records source-level run outcomes.
- `changelog` records document-level changes.
- `memory_reviews` records human-gated lifecycle decisions.
- memory provenance records which documents extract or corroborate a memory.

Those records do not answer the full evaluation question:

```text
Why did this memory get created, skipped, updated, corroborated, superseded,
retired, quarantined, or left searchable?
```

They also do not prove that SQLite, FTS5, and ChromaDB stayed aligned after each lifecycle operation.

The evaluation mechanism gives the project a feedback loop while extraction, reconciliation, source support detection, entity resolution, and retrieval are still evolving.

## Goals

- Record each important memory operation with enough context to review the decision later.
- Separate semantic decisions from storage and index side effects.
- Detect DB/FTS5/Chroma divergence and source-artifact provenance gaps quickly, before weekly review.
- Make high-risk lifecycle and retrieval behavior visible to a human and to a reviewing agent.
- Turn real failures into replay fixtures and regression tests.
- Preserve purge and privacy expectations by avoiding unbounded raw evidence retention.

## Non-Goals

- No direct memory mutation by the weekly evaluation agent.
- No full source-document duplication inside audit rows.
- No per-turn agent transcript journal.
- No replacement for `memory_reviews`; evaluation findings are separate from review workbench decisions.
- No attempt to make SQLite and ChromaDB transactionally atomic. The design detects and repairs non-atomic side effects instead.

## Architecture

```text
Source sync / Admin action / Scheduler / Review action
        |
        v
Decision owner
  - MemoryEngine
  - SourceSupportDetector
  - ReviewService
  - Admin API
  - Scheduler
        |
        v
Safe mutation executor
  - MemoryStore for memory mutations
  - DocumentVectorIndex for document-vector mutations
        |
        +--> SQLite / FTS5 / ChromaDB
        |
        +--> Memory Audit Ledger
        |
        v
Daily deterministic health checks
        |
        v
Weekly evaluation bundle
        |
        v
Agent evaluation findings
        |
        v
Human triage -> prompt, threshold, lifecycle, normalizer, retrieval, or test changes
```

## Core Boundary

`MemoryStore` should be the single safe doorway for operations that change memory state, memory provenance, or memory search visibility.

It should own execution for:

- memory insert
- memory content, confidence, or tag update
- deduplication and corroboration
- source support add, update, and removal
- supersede
- retire
- mark pending review
- purge
- expired-memory retirement
- document or source deletion effects that can retire memories
- memory FTS5 and memory Chroma updates

`MemoryStore` should not own:

- source discovery
- source normalization
- LLM extraction prompts
- reconciliation policy
- review policy
- entity-resolution strategy
- weekly evaluation reports
- document-vector indexing

This keeps `MemoryStore` as the safe mutation executor, not the brain of the memory system.

## Document Vectors

Memory vectors and document vectors are separate retrieval surfaces.

Memory vectors represent extracted memories and should be protected by `MemoryStore`.

Document vectors represent source documents or document summaries and are written by sync as document fallback retrieval data. They should not be forced into `MemoryStore`, because they are not memories.

Current implementation:

- `DocumentVectorIndex` owns document Chroma writes, deletes, snapshots, and restores.
- `MemoryStore` owns memory lifecycle consistency and uses `DocumentVectorIndex` only for source/document cascade cleanup.
- Sync uses `DocumentVectorIndex` directly for document fallback vectors and stores/restores document-vector snapshots when later DB work fails.
- Memory and document vector writes both use stored-vector hashing, so health compares metadata against the vector payload Chroma actually persisted.

The daily health checker includes document Chroma consistency so deleted documents do not remain discoverable through document fallback. It also flags source-artifact provenance gaps for genes with required local renditions, such as Confluence documents with normalized content but no stored PDF URI.

## Audit Ledger

The append-only audit table is `memory_audit_events`.

Each row records one decision, attempt, result, failure, or repair marker. Rows are linked by `operation_id` and optionally `parent_event_id`.

Suggested fields:

| Field | Purpose |
| --- | --- |
| `event_id` | Unique event ID |
| `operation_id` | Groups related decision, DB, FTS5, Chroma, and review events |
| `parent_event_id` | Optional causal parent |
| `occurred_at` | Event timestamp |
| `actor_type` | `sync`, `admin`, `scheduler`, `review_service`, `evaluator`, `repair` |
| `actor_id` | User, job, service, or agent ID when available |
| `run_id` | Sync or evaluation run ID |
| `trace_id` | Cross-component trace ID |
| `source_id` | Source config ID |
| `doc_id` | Source document ID |
| `memory_id` | Memory ID when one exists |
| `candidate_id` | Run-local candidate ID before memory persistence |
| `review_id` | Review workbench row when relevant |
| `support_kind` | `extracted` or `corroborated` |
| `event_type` | Specific event name |
| `decision` | Compact decision label |
| `reason` | Human-readable reason |
| `payload_class` | Redaction and retention class |
| `before_snapshot` | Redacted JSON snapshot or hash reference |
| `after_snapshot` | Redacted JSON snapshot or hash reference |
| `evidence_refs` | Source pointers, hashes, short excerpts, or URI references |
| `model` | LLM model when relevant |
| `prompt_hash` | Prompt version hash when relevant |
| `config_hash` | Runtime config hash when relevant |
| `thresholds` | Dedup, confidence, quality, or retrieval thresholds |
| `status` | `attempted`, `committed`, `failed`, `repaired`, `skipped` |
| `error` | Redacted error details |

Audit rows should denormalize source, doc, run, and memory identity. They must not be deleted just because a source is removed. Privacy purge may redact or tombstone sensitive payloads while preserving operational metadata.

## Event Types

Decision events:

- `candidate_extracted`
- `candidate_skipped`
- `quality_gate_failed`
- `entity_resolved`
- `alias_registered`
- `reconciliation_proposed`
- `reconciliation_fallback_used`
- `source_support_verified`
- `source_support_rejected`
- `contradiction_detected`
- `review_required`

Memory mutation events:

- `memory_insert_attempted`
- `memory_insert_committed`
- `memory_update_attempted`
- `memory_update_committed`
- `memory_supersede_attempted`
- `memory_supersede_committed`
- `memory_retire_attempted`
- `memory_retire_committed`
- `memory_pending_review_committed`
- `memory_purge_attempted`
- `memory_purge_committed`

Provenance events:

- `source_support_add_attempted`
- `source_support_added`
- `source_support_updated`
- `source_support_remove_attempted`
- `source_support_removed`
- `source_support_removal_retired_memory`

Review events:

- `review_created`
- `review_approve_attempted`
- `review_approved`
- `review_reject_attempted`
- `review_rejected`
- `review_marked_stale`
- `review_refreshed`

Index events:

- `fts_upsert_attempted`
- `fts_upsert_committed`
- `fts_delete_attempted`
- `fts_delete_committed`
- `chroma_upsert_attempted`
- `chroma_upsert_committed`
- `chroma_delete_attempted`
- `chroma_delete_committed`
- `index_operation_failed`
- `index_repair_needed`
- `index_repair_committed`

Retrieval evaluation events:

- `retrieval_probe_recorded`
- `retrieval_probe_replayed`
- `retrieval_regression_detected`

## Safe Write Path

The implementation should refine current code so memory-affecting operations do not write directly to `Database` when they also affect FTS5, ChromaDB, audit state, or memory visibility.

Target shape:

```text
Admin API       -> MemoryStore for memory mutations
Scheduler       -> MemoryStore for expired-memory retirement
Sync pipeline   -> MemoryEngine for decisions, MemoryStore for mutations
ReviewService   -> MemoryStore for lifecycle and index effects
Support detector -> MemoryStore for source support mutations
```

The database layer remains the SQLite persistence layer. It should still own SQL, schema, row mapping, and transaction helpers. It should not be used directly by higher-level code for lifecycle operations that must also update search indexes.

### Dedup Guard

ChromaDB is part of the dedup path. A stale Chroma result can suppress creation of a correct new memory by corroborating an inactive one.

Before corroborating a near-duplicate returned by Chroma:

1. Load the memory from SQLite.
2. Confirm `status = active`.
3. Confirm the memory is still search-visible.
4. If not active, reject that Chroma candidate and emit `stale_chroma_candidate_detected`.
5. Continue checking candidates or insert a new memory.

### Non-Atomic Store Effects

SQLite and ChromaDB cannot be committed atomically together. The design therefore records separate events:

```text
memory_update_attempted
memory_update_committed
fts_upsert_attempted
fts_upsert_committed
chroma_upsert_attempted
chroma_upsert_failed
index_repair_needed
```

The daily health checker and repair flow consume these events.

## Audit Context

Introduce an `AuditContext` passed through sync, engine, store, review, scheduler, and admin entry points.

Suggested shape:

```python
AuditContext(
    run_id="sync-2026-05-24-a91f",
    trace_id="trace-...",
    operation_id="op-...",
    actor_type="sync",
    actor_id="scheduler",
    source_id="src-jira",
    doc_id="PAY-1234",
    model="claude-sonnet-4",
    prompt_hash="sha256:...",
    config_hash="sha256:...",
)
```

Components may derive child contexts with new `operation_id` values for independent memory operations.

## Daily Health Checks

Daily checks are deterministic and should not require an LLM.

They should compute:

- active memories missing from FTS5
- active memories missing from memory Chroma
- retired memories still present in FTS5
- retired memories still present in memory Chroma
- superseded memories still present in FTS5
- superseded memories still present in memory Chroma
- pending-review memories still present in FTS5
- pending-review memories still present in memory Chroma
- Chroma active metadata that disagrees with SQLite status
- memory rows with no provenance
- source support rows pointing to missing documents
- duplicate content hashes among active memories
- document Chroma IDs without SQLite document rows
- SQLite documents missing document Chroma fallback entries when expected
- stale review age
- pending review count by age band
- contradiction rate
- source sync failures and failed documents
- abnormal spikes in candidates, skips, deletions, retirements, or source support removals

Index divergence is an operational P0 because it can affect future write-time decisions, not only retrieval display.

## Weekly Evaluation Loop

The weekly evaluator receives a compact bundle, not the full database and not full source documents.

Bundle format:

```json
{
  "case_id": "case-2026w21-0007",
  "operation_id": "op-1911",
  "event_window": ["evt-1", "evt-9"],
  "source_id": "src-jira",
  "doc_id": "PAY-1234",
  "memory_ids": ["mem-old", "mem-new"],
  "operation": "SUPERSEDE",
  "decision_reason": "source document changed timeout from 30s to 60s",
  "snapshots": {
    "before": {"status": "active", "content_hash": "sha256:..."},
    "after": {"status": "superseded", "superseded_by": "mem-new"}
  },
  "evidence": [
    {"kind": "excerpt", "text": "timeout is now 60 seconds", "hash": "sha256:..."}
  ],
  "deterministic_checks": {
    "db_fts_chroma_consistent": true,
    "source_support_remaining": 1
  },
  "sampling_reason": "all_supersede_events"
}
```

The evaluator scores:

- groundedness
- atomicity
- durability
- source relevance
- dedup correctness
- corroboration correctness
- update vs supersede choice
- delete/source-support-removal correctness
- contradiction handling
- pending-review usefulness
- entity and alias quality
- retrieval impact
- staleness risk
- evidence quality

The evaluator output goes into a separate `memory_eval_findings` table or document package, not `memory_reviews`.

Finding shape:

```json
{
  "finding_id": "mef-2026w21-004",
  "severity": "P1",
  "category": "reconciliation",
  "title": "Jira status-only changes caused durable memories to lose support",
  "affected_operation_ids": ["op-1911", "op-1930"],
  "affected_memory_ids": ["mem-abc", "mem-def"],
  "evidence": "14 DELETE decisions came from issue workflow metadata changes.",
  "recommendation": "Adjust Jira normalizer or reconciliation prompt to separate issue metadata from source truth changes.",
  "owner_hint": "pipeline/reconciler",
  "replay_candidate": true
}
```

## Sampling Policy

Review exhaustively:

- deletion handling
- retirement
- supersede
- pending review
- contradiction cases
- stale support removal
- source config reset or full-sync reset
- sync failure
- generated agent-session source cases
- index divergence
- fallback mode events
- LLM parse failures

Sample normal events by:

- source
- memory type
- confidence band
- dedup distance band
- support kind
- retrieval frequency
- low and high extraction count per document
- new source type

This keeps the weekly evaluator focused on trust-risky behavior without ignoring high-volume normal flows.

## Retrieval Evaluation

Retrieval quality must be evaluated separately from memory quality because MemForge retrieval uses multiple channels.

The mechanism should maintain query probes with expected or observed useful results:

```json
{
  "query_id": "q-flex-payroll-od-lifecycle",
  "query": "how does on-demand payroll lifecycle affect task generation",
  "expected_memory_ids": ["mem-123", "mem-456"],
  "source_scope": "PAY",
  "metrics": ["hit_at_5", "mrr", "top_k_churn"]
}
```

Weekly and release evaluation should track:

- hit@k
- MRR
- top-k churn
- stale result rate
- missing expected result rate
- graph-only discovery visibility
- source-groundedness of top results

## Human Triage

Evaluation findings should feed a quality dashboard or admin report with triage categories:

- prompt change
- threshold recalibration
- lifecycle/index bug
- source normalizer fix
- entity or alias cleanup
- retrieval tuning
- manual memory review
- regression fixture
- no action

Memory-specific conflicts may link to `memory_reviews`, but systemic evaluation findings should become engineering tasks or design updates.

## Replay Fixtures

Monthly or before major prompt/model/lifecycle changes, selected findings become replay fixtures.

Fixture shape:

```yaml
case: jira-status-change-should-not-remove-support
input_doc_hash: sha256:...
old_memory_id: mem-abc
operation_under_test: reconciliation
expected_operation: NOOP
expected_search_visible: true
expected_provenance:
  support_kind: extracted
expected_retrieval:
  query: "what is the payroll lifecycle timeout"
  hit_at_5: true
```

Release gate:

- no unresolved P0 daily health failures
- no unresolved P1 evaluator findings that affect lifecycle or search visibility
- replay fixtures pass for lifecycle and retrieval cases touched by the change

## Example End-to-End Flow

### New Document

1. Sync starts and creates `run_id`.
2. The gene fetches and normalizes a document.
3. Enrichment resolves entities and emits entity audit events.
4. Extraction emits candidate events.
5. Quality gate emits keep/skip events.
6. `MemoryEngine` decides ADD.
7. `MemoryStore` inserts the memory in SQLite and FTS5, upserts Chroma, and emits separate DB/index events.
8. Daily health confirms the active memory exists in DB, FTS5, and Chroma.
9. Weekly evaluation samples the case and checks groundedness, atomicity, and retrieval impact.

### Updated Document

1. Sync detects content hash change.
2. Reconciliation proposes ADD, UPDATE, SUPERSEDE, DELETE, or NOOP.
3. Each proposal is audited before execution.
4. Human-review-required proposals create pending review events.
5. Executed lifecycle changes go through `MemoryStore`.
6. Search-index effects are audited separately.
7. Weekly evaluation reviews all supersede, delete, pending-review, and fallback cases.

### Expired Memory

1. Scheduler finds active memories past `valid_until`.
2. Scheduler calls `MemoryStore.retire_expired_memories`, not a DB-only helper.
3. `MemoryStore` marks each memory retired and removes it from FTS5 and Chroma.
4. Audit records each retirement and index side effect.
5. Daily health verifies no retired memory remains searchable.

### Deleted Source Document

1. Sync detects document deletion during a safe full-sync deletion pass.
2. Deletion flows through `MemoryStore.delete_document`.
3. SQLite determines which memories lost their last usable support.
4. `MemoryStore` removes only newly retired memories from FTS5 and Chroma.
5. Document-vector cleanup flows through `DocumentVectorIndex`.
6. Daily health verifies memory and document index consistency.

## Implementation Phases

### Phase 1: Audit Ledger and Context

Deliver:

- Implemented: `memory_audit_events` schema.
- Implemented: `AuditContext` model.
- Implemented: audit writer API.
- Implemented: events for memory mutations, support changes, review decisions, index effects, and repair markers.
- Remaining: broaden extraction, quality-skip, reconciliation-proposal, and LLM fallback event coverage where useful for weekly evaluation.

Why:

The evaluator needs a reliable factual record before it can judge behavior.

### Phase 2: Safe Write Path Refactor

Deliver:

- Implemented: route admin memory updates through `MemoryStore.update_memory`.
- Implemented: route expired-memory retirement through `MemoryStore`.
- Implemented: route source-support additions through `MemoryStore`.
- Implemented: DB-status guard before Chroma dedup/corroboration.
- Implemented: tests that lifecycle-affecting direct DB paths do not bypass search-index cleanup.

Why:

Audit logs are not enough if the system can still mutate memory state through unsafe side doors.

### Phase 3: Deterministic Health and Repair Markers

Deliver:

- Implemented: deterministic `/api/health` consistency checker.
- Implemented: DB/FTS5/memory-Chroma ID-set checks.
- Implemented: document-Chroma consistency checks.
- Implemented: anomaly summaries.
- Implemented: repair CLI that records repair marker events.
- Remaining: scheduled/alerted repair automation if drift recurs.

Why:

Index divergence can affect future writes immediately. It should not wait for weekly LLM review.

### Phase 4: Weekly Evaluation and Triage

Deliver:

- compact JSONL bundle generator.
- risk-stratified sampling.
- weekly evaluator prompt and output schema.
- `memory_eval_findings` storage.
- admin report or quality dashboard entry point.

Why:

Semantic issues require judgment: bad extraction, wrong replacement, noisy aliases, review overuse, or retrieval quality drift.

### Phase 5: Replay Fixtures

Deliver:

- fixture format.
- replay runner for selected cases.
- retrieval probe runner.
- release gate integration.

Why:

Real evaluator findings should become regression tests so the same memory mistake does not return.

## Acceptance Criteria

- Every memory lifecycle mutation has an audit event with `operation_id`.
- Every memory search-index mutation has an attempt and outcome event.
- Active, retired, superseded, and pending-review memory visibility can be checked across SQLite, FTS5, and Chroma.
- Chroma dedup candidates are verified against SQLite active status before corroboration.
- Admin, scheduler, sync, support detection, and review flows use safe mutation APIs for memory-affecting writes.
- Document-vector consistency is either managed by a dedicated index store or explicitly checked and reported.
- Weekly evaluator findings are stored separately from `memory_reviews`.
- Purge-sensitive payloads can be redacted without destroying operational audit metadata.
- At least one replay fixture can be generated from an evaluation finding.

## Open Design Choices For Implementation

- Resolved: document vectors use `DocumentVectorIndex`; memory lifecycle consistency remains in `MemoryStore`.
- Resolved for now: the audit writer uses direct table inserts. An outbox worker is not required for current Chroma repair coordination.
- Exact retention periods for redacted snapshots and evidence excerpts.
- Whether daily health should trigger alerts or repair suggestions in APScheduler beyond the current deterministic `/api/health` and repair CLI.
- Which retrieval probes should seed the first replay set.
