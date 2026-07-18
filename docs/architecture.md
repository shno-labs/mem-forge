# MemForge: Architecture Design Document

> Auto-evolutionary agent memory layer for development teams.
> Sits between users/agents and knowledge sources, providing persistent team-wide memory
> that grows and refines as source documents change.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Design Principles](#2-design-principles)
3. [System Architecture](#3-system-architecture)
4. [Memory Data Model](#4-memory-data-model)
5. [Gene (Plugin) System](#5-gene-plugin-system)
6. [Memory Extraction Pipeline](#6-memory-extraction-pipeline)
7. [Memory Lifecycle](#7-memory-lifecycle)
8. [Entity Resolution & Alias System](#8-entity-resolution--alias-system)
9. [Storage Architecture](#9-storage-architecture)
10. [Retrieval Architecture](#10-retrieval-architecture)
11. [MCP Tool Interface](#11-mcp-tool-interface)
12. [Implementation Phases](#12-implementation-phases)
13. [Mem0 Patterns: What We Adopt vs Skip](#13-mem0-patterns-what-we-adopt-vs-skip)
14. [Feasibility Notes](#14-feasibility-notes)
15. [Admin UI Design](#15-admin-ui-design)
16. [Open Questions & Future Work](#16-open-questions--future-work)

---

## 1. Overview

### Problem

Development teams accumulate knowledge across many tools (Confluence, Jira, Microsoft Teams, Outlook, etc.). This knowledge is scattered, duplicated, and hard to retrieve. Current approaches either:

- Return full documents (too coarse, wastes tokens)
- Lose cross-source connections (same topic discussed in wiki, tickets, and chat)
- Don't evolve with the sources (stale after initial indexing)

### Solution

MemForge is a **memory layer** that:

- **Extracts** atomic knowledge units (memories) from documents synced via pluggable connectors (genes)
- **Deduplicates** across sources using semantic similarity
- **Evolves** automatically when source documents change (via scheduled sync)
- **Retrieves** precisely via hybrid search (vector + BM25 + entity graph) plus explicit source/date filters
- **Exposes** a unified MCP tool interface through agent-client proxies

### Key Metrics

| Metric | Target |
|--------|--------|
| Token efficiency vs doc-level search | 10-20x reduction (600 tokens vs 13,800 for equivalent knowledge) |
| Retrieval latency (no reranking) | < 150ms |
| Retrieval latency (with reranking) | < 500ms |
| Memory extraction per document | All durable atomic memories justified by the source; no fixed count |
| LLM calls per document sync (new) | 2 (enrichment + memory extraction), plus CandidateLedger when multiple semantic candidates remain |
| LLM calls per document sync (update) | 3 (enrichment + memory extraction + reconciliation), plus CandidateLedger and bounded support verification when needed |

---

## 1a. Technology Stack

| Component | Technology | Version / Notes |
|-----------|-----------|----------------|
| Language | Python 3.12+ | async/await throughout |
| Web framework | FastAPI | Admin REST API |
| Async DB | aiosqlite | SQLite with WAL mode |
| Vector store | ChromaDB | PersistentClient, cosine similarity |
| Embedding model | **OpenAI text-embedding-3-small** | 1536 dimensions, cosine distance. All similarity thresholds calibrated for this model. |
| LLM (enrichment) | **Claude Sonnet** (via Anthropic SDK) | XML-tag prompts, max_tokens=4000 |
| LLM (memory extraction) | **Claude Sonnet** (via Anthropic SDK) | Bounded source-unit extraction, max_tokens=32768 |
| LLM (reconciliation) | **Claude Sonnet** (via Anthropic SDK) | Third call on document updates only |
| Scheduler | APScheduler | Per-gene cron schedules |
| Auth (Atlassian) | Encrypted PAT + shared Jira browser sessions + httpx | HTTPS-only Confluence PAT access; Jira can use a shared per-origin browser session for instances that do not grant PAT REST quota. Source PATs and Jira browser-session cookies use `MEMFORGE_SECRET_KEY` when provided, otherwise an app-managed local Fernet key file |
| Auth (OAuth2) | httpx + MSAL | Microsoft Graph API for Teams/Outlook |
| Frontend | React 19 + TypeScript + Vite | Admin dashboard |

### Python Dependencies (Core)

```toml
[project]
name = "memforge"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn>=0.34",
    "aiosqlite>=0.20",
    "chromadb>=0.5",
    "anthropic>=0.40",
    "httpx>=0.27",
    "apscheduler>=3.10",
    "pydantic>=2.9",
    "tiktoken>=0.7",
    "markdownify>=0.13",
    "beautifulsoup4>=4.12",
    "bcrypt>=4.2",
    "cryptography>=42",
    "PyJWT>=2.9",
    "click>=8.1",
]
```

### Embedding Model Calibration

All distance thresholds are calibrated for **text-embedding-3-small** with cosine distance:

| Threshold | Value | Use |
|-----------|-------|-----|
| Dedup (near-duplicate) | cosine distance < 0.08 | Two memories are saying the same thing |
| Entity cluster (merge candidate) | cosine similarity > 0.85 | Two entities might be the same |
| Retrieval relevance floor | cosine distance < 0.40 | Below this, results are noise |

> **WARNING**: If you change the embedding model, ALL thresholds must be recalibrated
> using a held-out evaluation set. Different models have vastly different distance distributions.

---

## 2. Design Principles

| Principle | Implementation |
|-----------|---------------|
| **One extraction path** | The gene normalizes ALL data into comprehensive markdown. Two LLM calls extract metadata and memories (no separate "structural extraction" from gene code). |
| **Team-first, not user-first** | All memories are team-shared. No per-user scoping. Scope hierarchy: team > project/space > source. |
| **Steal patterns, not code** | Inspired by mem0's ADD/UPDATE/DELETE/NOOP operations, semantic deduplication, and confidence scoring. No mem0 dependency. |
| **SQLite + ChromaDB, no Neo4j** | Sufficient at team scale (up to 50K memories). Revisit graph DB only with data proving otherwise. |
| **Two-call extraction** | Enrichment (Call 1) produces metadata. Memory extraction (Call 2) receives Call 1's output + existing memories as context. Better quality, isolation, and independent iteration. |
| **Source-agnostic update extraction** | Every gene normalizes raw source data into stable markdown. Updates extract from changed hunks with the normalized full source item as context, then reconcile only current-document extracted memories. No persisted `KnowledgeBlock` layer or source-specific extraction strategy is required for the current lean design. |
| **Code-level entity resolution** | Entities are resolved in code (exact match → alias lookup → fuzzy match), not by LLM prompt instructions. The LLM assists by extracting explicit aliases from document text. |
| **Normalizer carries the weight** | Memory quality is proportional to normalizer quality. Each gene's normalizer must surface ALL meaningful structured data as readable markdown. |
| **Progressive disclosure** | Level 0 (memory cards, ~60 tokens each) > Level 1 (full detail + provenance) > Level 2 (backing source artifact via `get_resource`). Agents drill down only when needed. |
| **Unified search** | One `search` MCP tool that returns memory cards only. Agents use `get_memory` for provenance and `get_resource` for source artifacts. |

---

## 3. System Architecture

### Full Stack

```
+----------------------------------------------------------------------+
|                        AGENT / USER LAYER                            |
|  +----------------+  +--------------+  +---------------------------+ |
|  | Codex/Claude   |  |  Admin UI    |  |  Future Agent Clients     | |
|  | plugin+MCP     |  |  (REST API)  |  |  (plugin/proxy)           | |
|  +-------+--------+  +------+-------+  +-----------+---------------+ |
+----------|-------------------|------------------------|--------------+
           | MCP + hooks        | REST                   | MCP via proxy
           v                   v                        v
+----------------------------------------------------------------------+
|                     RETRIEVAL LAYER                                   |
|                                                                      |
|  MCP Proxy Tools:              Admin API:                            |
|  +---------------------+      +----------------------------+        |
|  | search              |      | POST /api/hooks/context    |        |
|  | get_memory          |      | POST /api/agent-sessions/  |        |
|  | submit_agent_session|      | POST /api/agent-sessions/  |        |
|  | _document           |      | documents (explicit only)  |        |
|  +---------+-----------+      +----------------------------+        |
|            v                                                         |
|  +----------------------------------------------------------+       |
|  |  Query Analyzer -> Strategy Router -> RRF Fusion          |       |
|  |  +---------+ +---------+ +-------+ +-----------+         |       |
|  |  | Vector  | |  BM25   | | Graph | | Temporal  |         |       |
|  |  | Search  | |  FTS5   | | Walk  | | Filter    |         |       |
|  |  +---------+ +---------+ +-------+ +-----------+         |       |
|  +----------------------------------------------------------+       |
+----------------------------------------------------------------------+
|                      MEMORY LAYER                                    |
|                                                                      |
|  +-----------------------------------------------------------+      |
|  |  memories        | memory_sources    | memory_entities     |      |
|  |  (SQLite)        | (provenance)      | (entity links)      |      |
|  |                  |                   |                      |      |
|  |  memories_fts    | entity_aliases    |                      |      |
|  |  (BM25 index)    | (alias registry)  |                      |      |
|  +-----------------------------------------------------------+      |
|  +-------------------+                                               |
|  | ChromaDB          |                                               |
|  | "memories"        | (separate from "documents" collection)        |
|  | collection        |                                               |
|  +-------------------+                                               |
+----------------------------------------------------------------------+
|                   EXTRACTION & LIFECYCLE                              |
|                                                                      |
|  +--------------------+ +-----------------+ +--------------------+   |
|  |  Memory Engine     | |  Deduplicator   | | Lifecycle Manager   |   |
|  |  (extract from     | |  (semantic      | |  (daily scheduler, |   |
|  |   enricher output) | |   similarity    | |   expiry/support   |   |
|  |                    | |   check before  | |   cleanup)         |   |
|  |  ADD / UPDATE /    | |   insert)       | |                    |   |
|  |  SUPERSEDE /       | |                 | |  Contradiction     |   |
|  |  DELETE / NOOP     | |  Corroboration  | |  Detector          |   |
|  +--------+-----------+ +-----------------+ +--------------------+   |
+-----------|----------------------------------------------------------+
            |        ENRICHMENT LAYER
            |
|  +--------v--------------------------------------------+             |
|  |  Enrichment (Call 1) + Memory Extraction (Call 2) |             |
|  |  -> summary, tags, entities, relationships          |             |
|  |  -> all durable atomic memories justified by source  |             |
|  |  -> entity_aliases                                  |             |
|  +--------+--------------------------------------------+             |
+-----------|----------------------------------------------------------+
            |          GENE LAYER (Sync)
            |
|  +--------v-------------------------------------------------+       |
|  |  Gene Sync Orchestrator                                   |       |
|  |  discover -> fetch -> normalize -> enrich+extract -> store|       |
|  +----+----------+----------+----------------+----------+----+       |
|       |          |          |                |                       |
|  +----v---+ +---v----+ +--v-----+  +-------v---+                    |
|  |Confluenc| |  Jira  | | Teams  |  | Outlook   |  ...more genes    |
|  |  Gene   | |  Gene  | |  Gene  |  |  Gene     |                   |
|  +----+----+ +---+----+ +--+-----+  +-----+-----+                   |
+-------|----------|----------|--------------|---------------------------+
        |          |          |              |
        v          v          v              v
   Confluence   Jira    MS Teams        Outlook
   REST API    REST API  Graph API     Graph API
```

Default agent-session hook capture is not the MCP
`submit_agent_session_document` path. The plugin keeps a local queue, uploads
bounded canonical evidence windows to `/api/agent-sessions/windows`, and
MemForge queues the `agent_session` source sync after package creation. A
queued request that arrives while the source is already syncing waits for that
active pass and then runs one coalesced follow-up pass.

---

## 4. Memory Data Model

### What Is a Memory?

A **memory** is an atomic, self-contained unit of extracted knowledge -- distilled from one or more source documents -- that can be retrieved and reasoned over without reading the source document.

**Examples:**

| Type | Example |
|------|---------|
| `fact` | "pay-api uses PostgreSQL 15 on port 5432" |
| `decision` | "Team chose gRPC over REST for inter-service calls, citing 40% p99 latency reduction" |
| `convention` | "All payment services must emit events to the payment.completed Kafka topic" |
| `procedure` | "To deploy pay-api: run make build-staging, kubectl apply, verify /health" |

### Memory Types

Four types. Chosen for clear LLM distinguishability — each answers a different question:

| Type | Description | Extraction Focus | Answers |
|------|-------------|-----------------|---------|
| `fact` | Declarative knowledge about systems, configs, ownership | Ports, URLs, versions, team ownership, dependencies | "What IS?" |
| `decision` | Time-bound choices with rationale | "We decided X because Y" | "Why?" |
| `convention` | Team standards and prescriptive norms | Naming conventions, required patterns, guidelines | "What SHOULD be?" |
| `procedure` | Step-by-step how-tos | Runbooks, deployment steps, debug workflows | "How?" |

> **Cut from earlier design:** `pattern` was removed because it overlaps with `fact`.
> "pay-api depends on auth-service" is a fact, not a separate type.
> Architectural relationships are facts about the system.

### Memory Scoping (Team-First)

```
TEAM (global) --- visible to everyone
  +-- PROJECT / SPACE --- filtered by Confluence space or Jira project key
        +-- SOURCE --- tied to specific gene instance
```

No per-user scoping. This is collective team memory.

### Memory Schema

```python
@dataclass
class Memory:
    id: str                          # "mem-{uuid8}"
    memory_type: str                 # fact | decision | convention | procedure
    content: str                     # Full natural-language statement
    content_hash: str                # SHA-256 for dedup

    # Scoping
    scope: str                       # "team" | "project:{key}" | "source:{id}"
    project_key: str | None          # e.g. "PAY", "DevOps"

    # Provenance chain
    source_doc_ids: list[str]        # Doc IDs that produced this memory
    source_types: list[str]          # ["confluence", "jira"]
    extraction_context: str          # Original text span (max 200 chars)

    # Entity linkage
    entity_refs: list[str]           # Canonical entity names referenced

    # Confidence and lifecycle
    confidence: float                # 0.0 - 1.0 (LLM extraction confidence)
    corroboration_count: int         # Independent sources confirming this
    contradiction_count: int         # Sources contradicting this (0 = no conflicts)
    valid_from: datetime | None      # When this fact became true
    valid_until: datetime | None     # When this fact expires
    created_at: datetime
    updated_at: datetime

    # Lifecycle
    superseded_by: str | None        # Points to newer memory
    status: str                      # active | superseded | retired | pending_review
```

### Provenance Chain

```
Source Document(s)  -->  memory_sources  -->  Memory  -->  memory_entities  -->  Entity
     (documents)         (join table)      (memories)      (join table)       (entities)
```

Provenance is bidirectional:
- From a memory: trace back to every source document that owns or corroborates it
- From a document: find memories extracted from it and memories it corroborates
- When a document changes: know which extracted memories need reconciliation and which corroborated supports need revalidation

`memory_sources.support_kind` separates ownership from additional evidence:
- `extracted`: the memory originated from this document, so the document can participate in same-document reconciliation.
- `corroborated`: the document directly supports an existing memory with a validated excerpt, but cannot update, supersede, retire, or review-queue that memory by itself.

Both kinds are valid source support for keeping a memory active. `extracted`
controls reconciliation ownership; it is not required for the memory to keep
existing while corroborated support remains.

---

## 5. Gene (Plugin) System

### What Is a Gene?

A gene is a self-contained plugin that syncs data from a specific source (Confluence, Jira, Teams, Outlook, etc.) and feeds it into the memory layer.

### Gene Interface

```python
class Gene(ABC):
    """Base class for all data source plugins."""

    # -- Static metadata (classmethod) --

    @classmethod
    @abstractmethod
    def metadata(cls) -> GeneMetadata: ...
        # name: str              -- unique identifier ("confluence", "jira", "teams")
        # display_name: str      -- human-readable ("Microsoft Teams")
        # description: str       -- one-line summary
        # default_sync_interval_minutes: int
        # auth_method: str       -- "pat" | "oauth2" | "api_key" | "browser_cookie"
        # data_shape: str        -- "document" | "ticket" | "message" | "email"

    @classmethod
    @abstractmethod
    def config_schema(cls) -> GeneConfigSchema: ...
        # Typed fields the UI renders dynamically
        # ConfigField(key, label, field_type, required, placeholder, help_text, group)

    # -- Instance methods (per-source) --

    @abstractmethod
    async def authenticate(self) -> None: ...

    @abstractmethod
    async def discover(self, since: datetime | None) -> AsyncIterator[ContentItem]: ...

    @abstractmethod
    async def fetch(self, item: ContentItem) -> RawContent: ...

    @abstractmethod
    async def normalize(self, raw: RawContent) -> NormalizedContent: ...
        # MUST produce comprehensive markdown that includes ALL structured data
        # Returns markdown_body + source_semantics dict

    # Optional
    async def health_check(self) -> dict:
        return {"healthy": True}
```

> **Simplified from earlier design:** `GeneCapabilities` (10 fields) was replaced by 3 fields
> on `GeneMetadata`. `on_webhook()` was removed (future work). Entrypoint discovery was removed.
> These can be reintroduced when gene count exceeds 5.

### Gene Metadata (Minimal)

```python
@dataclass
class GeneMetadata:
    name: str                            # "confluence", "jira", "teams", "outlook"
    display_name: str                    # "Microsoft Teams"
    description: str                     # One-line summary
    default_sync_interval_minutes: int   # e.g., 60 for Teams, 1440 for Confluence
    auth_method: str                     # "pat" | "oauth2" | "api_key" | "browser_cookie"
    data_shape: str                      # "document" | "ticket" | "message" | "email"
```

### Common Intermediate Representation

Every gene produces `NormalizedContent` with two parts:

| Part | Purpose | Used By |
|------|---------|---------|
| `markdown_body` | Clean markdown including ALL structured data | Enricher, ChromaDB, MCP |
| `source_semantics` | Structured dict for search filtering only | Faceted search, metadata filtering |

The normalizer is the critical quality gate. It MUST surface all meaningful structured data
as readable markdown so the enricher can extract memories from it.

### Gene Registry (Simple Dict)

```python
# Genes are registered explicitly. No auto-discovery, no entrypoints.
# Reintroduce entrypoint discovery when gene count exceeds 5.

GENE_REGISTRY: dict[str, type[Gene]] = {
    "agent_session": AgentSessionGene,
    "confluence": ConfluenceGene,
    "jira": JiraGene,
    "teams": TeamsGene,
}

def create_gene(name: str, config: dict, source_id: str) -> Gene:
    cls = GENE_REGISTRY[name]
    return cls(config=config, source_id=source_id)

def list_available_genes() -> list[GeneMetadata]:
    return [cls.metadata() for cls in GENE_REGISTRY.values()]
```

### Per-Gene Sync Schedules

| Gene | Default Interval | Min Interval | Rationale |
|------|-----------------|--------------|-----------|
| Confluence | Daily | 1h | Wiki pages change slowly |
| Jira | 6h | 30m | Tickets change moderately |
| Teams | 1h | 5m | Chat moves fast |
| Outlook | 2h | 15m | Email is moderate |
| Agent Session | Manual / service-queued | N/A | Generated packages arrive after accepted agent-session windows |

### Agent Session Gene Design

Agent-derived memory enters MemForge as generated session documents, not as
direct memory writes. The canonical flow is documented in
`docs/design/agent-session-saas-plugin-flow.md`.

**Content unit:** a MemForge-generated markdown package for one bounded
agent-session window. Codex and Claude Code plugins upload redacted canonical
evidence windows to `POST /api/agent-sessions/windows`; MemForge canonicalizes
again, runs the Stage 1 package LLM, and stores the package as an
`agent_session` source document. The explicit
`POST /api/agent-sessions/documents` path remains for already-generated manual or
MCP summaries, not the default hook flow.

**Receipt/lineage:** each processed window has a receipt recording client,
session id, trigger, workspace, repo, branch, commit, history window, document
hash, outcome (`package_created`, `no_output`, or `failed`), and reason when
needed. The receipt is not a conversation transcript; it exists for
deduplication, audit, deletion, and reprocessing.

**Authority:** agent session summaries are generated sources. They can provide
useful handoff context and candidate memories, including updates to stale docs,
but they should not bypass the normal source pipeline. When they conflict with
authored team sources, the conflict should become a human review decision rather
than an automatic win or loss.

**Admin ownership:** the `agent_session` source is service-managed. The Admin UI
may list it for sync status and repair actions, but users do not add, configure,
or delete it like Confluence, Jira, or Teams. Its storage path and sync requests
are owned by the agent-session API flow.

**Normalized markdown includes:** the generated session-window package after
operational sections such as validation logs, runtime notes, command evidence,
and receipt-only metadata are removed. Receipt provenance remains available in
`source_semantics`; it is not copied into LLM-visible extraction markdown.

### Agent Hook Integration

Codex, Claude Code, and similar coding agents use MemForge through two
separate paths:

- MCP is the model-visible read path. Agents call `search` and `get_memory`
  when they need memory evidence while reasoning. Recent-memory questions use
  `search` with a `time_range`, not a separate recent-changes memory tool.
- Hooks are lifecycle automation. Hooks call the Admin API for compact context
  injection, optional lifecycle receipt write-back, and agent-session window
  upload.

The hook context endpoint is `POST /api/hooks/context`. It accepts client,
hook, workspace, repo, branch, prompt, touched files, and a memory limit. It
returns `should_inject=false` for trivial prompts, or a compact markdown block
with relevant active memories, recent memory changes, and source warnings.

Installable hook packages live under `integrations/codex/memforge-memory` for Codex
and `integrations/claude-code/memforge-memory` for Claude Code. They share the
`memforge.hook_adapter` command adapter contract through a vendored plugin
script, so provider-specific plugins stay thin while the Admin API remains the
integration contract. Each package also includes `.mcp.json` so the same
installation exposes explicit memory tools through a plugin-local MCP proxy.
The packaged MCP config starts a stdlib-only local proxy. The proxy forwards
memory operations to `MEMFORGE_API_URL` and owns only client-local work such as
artifact cache files for `get_resource(mode="file")`.

Lifecycle receipt write-back is `POST /api/hooks/receipts`; receipts do not
enter the source pipeline. Automatic hook capture uses a local plugin queue and
uploads bounded, redacted canonical evidence windows to
`POST /api/agent-sessions/windows`. The plugin keeps native transcript rows as
local cursor units, but the package LLM sees filtered evidence rather than raw
JSONL prefixes when canonical events exist. MemForge generates packages and
queues the `agent_session` source sync internally, including a coalesced
follow-up when a package is created during an active sync. Hooks never write
canonical memories directly. See `docs/design/agent-hook-integration.md` for the
endpoint contract and query rules.

### Teams Gene Design (Detailed)

**Content unit:** conversational window. Threaded Teams conversations use one
root message plus replies as a window. Unthreaded group/direct chat messages
are projected into stable 60-minute time blocks using a local ledger, so a
late message can revise a window without changing its window id.

Teams sync uses the Teams chatsvc REST API, not Microsoft Graph. A live probe on
2026-07-08 against `/conversations` and `/conversations/{id}/messages` confirmed
the raw shape used by the implementation:

- conversation pages return `_metadata` plus `conversations[]`; each
  conversation carries `id`, `type`, `threadProperties`, `lastMessage`, and
  `version`.
- message pages return `_metadata`, `tenantId`, and `messages[]`; messages carry
  `conversationid`, `id`, `clientmessageid`, `rootMessageId`,
  `composetime`, `originalarrivaltime`, `messagetype`, `contenttype`,
  `content`, sender fields, and `version`.
- `lastmodifiedtime` was not present in the sampled message page, so edit/delete
  handling must not rely on that field being available.

The local agent audit log is compact JSONL at
`~/.memforge/teams-sync-audit.jsonl` by default. It records no message body,
participant display name, bearer token, or raw Teams id. Opaque ids and
pagination cursors are hashed by the audit writer. Each run writes:

- `teams_conversation_poll`: raw REST page count, raw message count, unique
  message-key count, duplicate raw-row count, filtered message count, coverage
  timestamps, pagination stop reason, and deterministic message receipt actions
  (`upsert_new`, `upsert_updated`, `upsert_unchanged`).
- `teams_window_projection`: selected window id hash, revision hash, and whether
  a prior receipt caused the window to be skipped.
- `teams_memory_patch`: push result for each new window revision.
- `teams_sync_run`: run-level selected/pushed/failed/skipped/poll totals.

For next-day incremental checks, `validate_teams_audit_run()` verifies that raw
message counts reconcile with unique plus duplicate rows, selected message
receipt actions reconcile with selected message keys, duplicate new window
projections are absent, and summary totals match projection/patch rows.

### Outlook Gene Design

- Two data shapes: email threads + calendar events
- Calendar events produce procedure/fact memories with attendee lists + timestamps
- Email: opt-in per shared mailbox/folder only (privacy-first)
- source_semantics carries: reply chains, importance flags, To/CC lists

---

## 6. Memory Extraction Pipeline

### Two-Call Extraction

Two separate LLM call families per document. Call 2 receives Call 1's output as
context. Better quality, failure isolation, and independent iteration vs. a
single combined call. Source items are first converted to readable normalized
markdown. Full-document extraction then uses shared deterministic structural
units derived from that markdown heading tree. The system does not persist a
source-specific `KnowledgeBlock` structure; unit ownership lives on the source
support edge.

```
Gene.normalize() --> comprehensive markdown
        |
   CALL 1: Enrichment (document --> metadata)
        | --> summary, tags, entities, relationships, doc_type, complexity, entity_aliases
        |
   CODE: Entity Resolution Pipeline (Section 8)
        | --> resolve extracted entities against DB (exact, alias, fuzzy)
        | --> auto-register new aliases from fuzzy matches
        | --> insert LLM-extracted aliases into entity_aliases table
        |
   CALL 2: Memory Extraction (unit + read-only document context + existing memories --> memories)
        | --> durable atomic memories justified by the owned unit
        | --> receives: entities from Call 1, existing memories for these entities
        |
   CODE: Dedup against existing DB memories --> store
        |
   CODE + LLM verifier: source-support detection
        | --> attach corroborated provenance to existing active memories
        | --> validate exact excerpts before persistence
```

**Why staged calls, not one prompt:**
- Each prompt is focused — better quality than a kitchen-sink prompt with 8 output fields
- If memory extraction fails, enrichment still succeeds (isolation)
- Memory extraction prompt can reference existing memories ("don't re-extract known facts")
- Source-support verification is isolated from extraction so it can add
  corroborated evidence without creating or rewriting memories.
- Each prompt can be iterated independently without risking regression on the other
- Separate token budgets — no competition for max_tokens
- A completed document lifecycle is also the process-memory ownership boundary:
  Python cycles are collected and Linux/glibc free pages are trimmed before the
  next document is admitted. Reclamation is best-effort and cannot change the
  already committed relational lifecycle result.

### Call 1: Enrichment Prompt

```
You are analyzing an internal document for a team knowledge system.

<source_type>{source_type}</source_type>
<document>{content}</document>

Return a JSON object with:

1. summary: 2-3 sentence summary
2. tags: 5-10 normalized lowercase topic tags (singular, no version numbers)
3. entities: [{name, type}] where type is: service, person, technology, api, team, feature
4. relationships: [{target_title, relation_type, confidence}]
5. doc_type: enum (design-doc, runbook, decision-record, how-to, reference,
   postmortem, meeting-notes, ticket, discussion, email, unknown)
6. complexity: enum (low, medium, high)
7. entity_aliases: if the document explicitly states two names refer to the same thing
   (e.g., "OnDemand Payroll, internally called Project Payroll"), return:
   [{canonical, aliases, evidence}]

Return ONLY valid JSON, no markdown fences or extra text.
```

### Between Calls: Code-Level Entity Resolution

After Call 1 returns entities, each entity passes through the resolution pipeline
(Section 8). This is **code, not LLM**:

```python
resolved_entities = []
for raw_entity in enrichment_result.entities:
    entity_id = await resolve_entity(
        extracted_name=raw_entity.name,
        extracted_type=raw_entity.type,
        db=self.db,
    )
    resolved_entities.append(entity_id)

# Also process LLM-extracted aliases
for alias_group in enrichment_result.entity_aliases:
    canonical_id = await resolve_entity(alias_group.canonical, ...)
    for alias_name in alias_group.aliases:
        await db.insert_alias(alias_name, canonicalize(alias_name), canonical_id, "llm_extracted")
```

### Call 2: Memory Extraction Prompt

```
You are extracting atomic knowledge from a document for a team memory system.

<source_type>{source_type}</source_type>
<doc_type>{doc_type_from_call_1}</doc_type>
<entities_found>{canonical_entity_names_from_call_1}</entities_found>
<existing_memories_for_these_entities>
{memories_already_in_DB_for_these_entities}
</existing_memories_for_these_entities>
<unit_markdown>{owned_unit_content}</unit_markdown>
<document_outline>{outline_context}</document_outline>
<glossary_appendix>{glossary_context}</glossary_appendix>

Extract all durable atomic knowledge units justified by `unit_markdown`. Return
[] if the unit contains no durable team memory. Each memory must have:
- content: self-contained factual sentence (understandable without the source document)
- memory_type: fact | decision | convention | procedure
- confidence: 0.0-1.0 (high only when the source directly states durable domain knowledge)
- entity_refs: key entity names (use the canonical names from <entities_found>)
- tags: 2-5 lowercase topic tags
- valid_from / valid_until: ISO dates if time-bound (null otherwise)
- extraction_context: short evidence quote for audit/provenance display
- evidence_quote: evidence text copied by the model when available
- evidence_anchor: "unit" to declare that the evidence belongs to the owned unit

Rules:
- Each memory must be SELF-CONTAINED
- Do NOT re-extract facts listed in <existing_memories_for_these_entities>
- Do not extract facts that appear only in the outline, glossary, title, URL, or source metadata
- Each memory must declare `evidence_anchor = "unit"` so code can reject context-only candidates
- Focus on NEW or UPDATED information
- Use entity names from <entities_found>, not your own variations
- Prefer specifics ("PostgreSQL 15" not "a database")
- For tickets: extract the decision/outcome, not the discussion
- For runbooks: each distinct step = separate procedural memory
- For design docs: extract decisions, dependencies, constraints
- For discussions: extract decisions and conventions that reached consensus;
  skip unresolved opinions, tentative suggestions, and unanswered questions
- For chat sources: skip transient status updates, review-in-progress notes, and
  temporary caveats; focus on decisions, persistent facts, and action items
- Do not extract document metadata: author, last modified, document status,
  revision-history rows, reviewer lists, and link list rows are provenance
- Preserve conditional language and do not turn open questions into decisions
- Do not extract formatting details, boilerplate, table-of-contents entries,
  passwords, credentials, tokens, API keys, or authentication secrets

Return ONLY a JSON array of memories, no markdown fences or extra text.
```

### Pre-Persistence Quality Gate

Call 2 output is still treated as candidate data. Before any candidate is
persisted, `MemoryEngine` runs a deterministic gate that skips:

- `metadata_only`: document headers such as author, last modified, document status, reviewers.
- `reference_only`: source link-list rows such as "Link to Concept".
- `attachment_event_only`: upload bookkeeping without a claim grounded in attachment content.
- `operational_history_only`: routing-field transitions such as assignee, due date, labels, priority, rank, sprint, resolution, or routine status.
- `open_question`: unresolved discussion prompts such as "discuss whether" or "to be discussed".

The gate is deliberately narrow. Conditional domain rules are kept when the
condition is part of the fact, for example "If regular pay date changes, repeat
the validation." The same gate applies to reconciliation-created ADD, UPDATE,
and SUPERSEDE candidates; a skipped replacement cannot supersede an incumbent
memory.

### CandidateLedger

Every extraction batch for one Source Unit revision is aggregated before
lifecycle planning. After the deterministic quality gate, exact content
duplicates collapse without an LLM call. Multiple remaining candidates pass
through one complete semantic uniqueness ledger:

- one `KEEP` or `DROP_REDUNDANT -> canonical_index` decision per candidate
- original candidate objects are retained; the ledger does not merge or rewrite content
- no full document, evidence text, incumbent list, or provider payload is included
- one corrective retry is allowed for an incomplete ledger
- more than 200 semantic candidates or 100,000 serialized input characters fails closed

A failed ledger writes no Memory and authorizes no incumbent mutation. The
failure is recorded as `candidate_ledger_failed`; successful multi-candidate
selection is recorded as `candidate_ledger_completed`.

### Token Budget

- Call 1 input: normalized document content truncated to 100,000 chars
- Call 1 output: max_tokens = 4000 (metadata is compact)
- Call 2 input: one deterministic unit plus read-only outline/glossary context
- Call 2 output: max_tokens = 32768 for structured memory candidates; the model supports
  64000, but regularly needing that ceiling indicates the Source Unit should be split smaller
- CandidateLedger input: at most 200 non-identical candidates and 100,000 serialized chars
- CandidateLedger output: max_tokens = 8192 for a complete decision ledger
- Call 3 output on updates: max_tokens = 4096 (reconciliation decisions)
- Call 2 receives additional context: entities + up to 30 existing memories for those entities
- Cost per document varies by source length; unchanged documents are skipped by content hash,
  new/changed documents pay enrichment + extraction, and changed documents pay reconciliation.

---

## 7. Memory Lifecycle

### Creation (During Sync)

Triggered inside the sync pipeline after normalization:

```python
# After enrichment returns combined output
for raw_memory in enrichment_result.memories:
    stored_id = await memory_engine.deduplicate_and_insert(
        raw_memory, doc_id, source_type, project_key
    )
```

### Update (When Source Items Change)

When a sync detects a content hash change, the update planner chooses
`diff_guided` when the previous and current normalized markdown can be compared,
or `full_document` when no reliable previous snapshot exists or the diff is too
large. This strategy is source-agnostic: Confluence pages, Jira tickets, Teams
blocks, agent-session summaries, future GitHub Pages, and local markdown repos
all share the same memory update path after normalization. Diff-guided
extraction uses the full updated source item as context, but asks the extractor
to produce only memories caused by changed hunks. The pipeline then enforces
that contract: each candidate's exact quote must overlap an inserted or replaced
current-revision range; unchanged-context candidates are audited and discarded.
Deletion-only diffs authorize no new candidate. Full-document fallback uses
the same deterministic structural units described above, so large pages are
processed by owned sections without adding source-specific extraction logic.

```python
async def update_memories_for_document(self, doc_id, new_content):
    existing = await self.db.get_memories_by_source_doc(doc_id, support_kind="extracted")
    existing_active = [m for m in existing if m.status == "active"]
    new_candidates = memory_extraction_result.memories  # from Call 2, scoped by update mode

    if not existing_active:
        for mem in new_candidates:
            await self.deduplicate_and_insert(mem)
        return

    # LLM-based reconciliation
    operations = await self.reconcile(
        existing_active,
        new_candidates,
        updated_document=new_content,
        changed_hunks=update_plan.changed_hunks,
        update_mode=update_plan.mode,
    )
    for op in operations:
        match op.action:
            case "ADD":      await self.add_memory(op.memory)
            case "UPDATE":   await self.update_memory(op.existing_id, op.memory)
            case "SUPERSEDE": await self.supersede_memory(op.existing_id, op.memory)
            case "DELETE":   await self.remove_source_support(op.existing_id, doc_id)
            case "NOOP":     pass
```

ADD, UPDATE, and SUPERSEDE candidates go through the same pre-persistence quality
gate used by initial extraction. If a proposed replacement is metadata-only,
reference-only, or an unresolved question, it is skipped and the old memory is
left unchanged.

DELETE is scoped to the updated source document. It removes that document's
support link from the memory; the memory is retired only when no usable source
support remains. This lets one document stop supporting a fact without hiding a
memory that is still supported by other documents.

Same-document reconciliation can mutate only memories where the current document
has `support_kind='extracted'`. If the model proposes UPDATE, SUPERSEDE, or
DELETE for a memory outside that authority, the decision is rejected and audited.
If a direct content mutation would affect another valid support edge, the system
stages a challenger for review instead of silently rewriting shared provenance.

The full state matrix for same-document and cross-document provenance conflicts
lives in `docs/design/document-memory-lifecycle.md`.

The source normalization boundary and reusable extraction contract are captured
in `docs/design/source-agnostic-memory-extraction.md`.

### Reconciliation Operations (Inspired by Mem0)

| Operation | When | Example |
|-----------|------|---------|
| **ADD** | New fact not in existing memories | New service dependency documented |
| **UPDATE** | Same fact, minor detail changed | Port changed from 8080 to 8443 |
| **SUPERSEDE** | Fundamentally replaced by a new fact | Migrated from REST to gRPC entirely |
| **DELETE** | Fact no longer supported by this source document | Section deleted; remove this document's support, retire only if support count becomes zero |
| **NOOP** | No change | Fact still accurately represented |

### Deduplication (Semantic Similarity)

Before inserting any memory, check for near-duplicates:

```python
async def deduplicate_and_insert(self, candidate, doc_id):
    embedding = await self.embed_memory(candidate)
    similar = self.memory_collection.query(
        query_embeddings=[embedding], n_results=3,
        where={"status": "active"}
    )
    if similar["ids"][0] and similar["distances"][0][0] < 0.08:
        # Near-duplicate extracted from this document: add extracted provenance
        # instead of creating a duplicate memory.
        existing_id = similar["ids"][0][0]
        await self.db.add_memory_source(existing_id, doc_id, support_kind="extracted")
        return existing_id

    # No duplicate: insert new memory
    await self.db.insert_memory(candidate)
    return candidate.id
```

### Source Support Detection

After extraction and reconciliation, the pipeline checks whether the current
document directly supports existing active memories for the same resolved
entities. This is evidence attachment, not memory extraction.

Candidate selection is deterministic and bounded:
- active memories only
- shared resolved entities with the current document
- no existing source link for the current document, except already-corroborated rows can be rechecked for a better excerpt
- same project/team preferred
- ranked by same project, entity overlap, corroboration count, confidence, and recency
- capped to a small batch for the verifier

The LLM acts only as a verifier. It returns a memory ID, `supported=true`, an
exact excerpt, and a short reason. The system persists support only when the
excerpt is contained in the normalized document and is not link-only,
metadata-only, or malformed. A persisted support row uses
`support_kind='corroborated'`.

Corroborated rows count toward `corroboration_count` and show in provenance,
but they do not participate in same-document reconciliation. If a document is
updated and an old corroborated excerpt is no longer present, the support row is
removed unless the verifier supplies a replacement excerpt from the updated
document.

### Lifecycle Cleanup

Memory state changes go through the lean lifecycle rules:

```python
async def retire_stale_memories(self):
    # 1. Memories from deleted source documents lose only that source support.
    orphaned = await self.db.get_memories_with_deleted_sources()
    for mem in orphaned:
        if await self.db.count_usable_sources(mem.id) > 1:
            await self.db.remove_source(mem.id, deleted_doc_id)
        else:
            await self.db.update_status(mem.id, "retired", reason="source_deleted")

    # 2. Expired episodic memories are retired by the daily scheduler job.
    expired = await self.db.get_expired_memories()
    for mem in expired:
        await self.db.update_status(mem.id, "retired", reason="expired")
```

`active` is the only default-searchable state. `pending_review` is quarantined,
`superseded` is historical replacement with `superseded_by`, and `retired` is
hidden because the memory has no current support or was explicitly hidden.
`decayed` is accepted only as a compatibility alias for `retired`.

Retired and pending-review memories are excluded from default search, but
queryable in explicit admin/history views.

### Contradiction Handling

When multiple sources produce conflicting memories, the system does not blindly
hide the incumbent. A better-supported active memory remains active, while an
ambiguous challenger or risky replacement is quarantined for review:

- Clear same-source replacement: old memory becomes `superseded`, new memory becomes `active`.
- Cross-document contradiction: challenger is stored as `pending_review` and hidden from default search, the incumbent stays active, and a Review workbench decision points to both rows.
- High-corroboration same-document replacement or delete: flagged for human review instead of automatic demotion.

> **Cut from earlier design:** Synthetic "meta-memories" that recorded conflicts were removed.
> The two original memories + `contradiction_count` + warning in search results is sufficient.
> Creating a third memory cluttered results and was hard to maintain when originals changed.

---

## 8. Entity Resolution & Alias System

### The Problem

The LLM extracts entity names from documents. Different documents use different names
for the same thing. Without resolution, memories fragment across duplicate entities:

```
Without resolution:
  entity #5  "postgresql"      → 4 memories linked
  entity #37 "postgresql 15"   → 2 memories linked
  entity #38 "postgres"        → 1 memory linked
  entity #39 "pg"              → 1 memory linked
  Total: 4 entities, 8 memories, no cross-linking.

With resolution:
  entity #5  "postgresql"      → 8 memories linked
  aliases: "postgresql 15", "postgres", "pg"
  Total: 1 entity, 8 memories, fully connected.
```

### Design Principle: Code Resolves, LLM Assists

Prompt-level guidance ("map to existing entities") is unreliable. The LLM is
non-deterministic, doesn't reliably scan long entity lists, and makes inconsistent
decisions about whether "PostgreSQL 15" is the same as "PostgreSQL".

**Entity resolution is a code-level pipeline, not a prompt instruction.** The LLM assists
by extracting explicit aliases from document text, but code is the safety net.

### Known Abbreviation Table

A static lookup of ~200 common tech abbreviations, applied during canonicalization.
Eliminates the single largest class of entity fragmentation (abbreviations/acronyms)
at zero runtime cost:

```python
KNOWN_ABBREVIATIONS: dict[str, str] = {
    # Databases
    "pg": "postgresql", "postgres": "postgresql", "psql": "postgresql",
    "mongo": "mongodb", "dynamo": "dynamodb", "rds": "amazon rds",
    # Infrastructure
    "k8s": "kubernetes", "k3s": "k3s",  # k3s is its own thing
    "tf": "terraform", "cdk": "aws cdk",
    # Languages / Runtimes
    "js": "javascript", "ts": "typescript", "py": "python",
    "rb": "ruby", "rs": "rust", "go": "golang",
    # Platforms
    "gh": "github", "gl": "gitlab", "aws": "amazon web services",
    "gcp": "google cloud platform", "az": "azure",
    # Auth / Identity
    "msal": "microsoft authentication library",
    "oidc": "openid connect", "saml": "saml",
    # Messaging
    "mq": "rabbitmq", "sns": "amazon sns", "sqs": "amazon sqs",
    # Monitoring
    "dd": "datadog", "otel": "opentelemetry",
    # ... ~200 entries total, curated per team domain
}

def canonicalize_entity_name(name: str) -> str:
    """Normalize entity name: lowercase, strip whitespace, expand abbreviations."""
    s = name.strip().lower()
    s = re.sub(r"\s+", " ", s)
    # Expand known abbreviations (exact match on full canonical form)
    if s in KNOWN_ABBREVIATIONS:
        s = KNOWN_ABBREVIATIONS[s]
    return s
```

This runs BEFORE any matching step. "PG" → "postgresql" → exact match on entity #5.
"K8s" → "kubernetes" → exact match. No fuzzy matching or alias table needed.

The table is **team-extensible**: admins can add domain-specific abbreviations
(e.g., "ODP" → "on-demand processing") via config or the admin API.

### Entity Alias Table

```sql
CREATE TABLE entity_aliases (
    alias            TEXT NOT NULL,
    alias_normalized TEXT NOT NULL,
    canonical_id     INTEGER NOT NULL REFERENCES entities(id),
    source           TEXT NOT NULL,    -- "exact" | "fuzzy_auto" | "llm_extracted" | "admin_manual"
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (alias_normalized, canonical_id)
);
CREATE INDEX IF NOT EXISTS idx_entity_aliases_normalized ON entity_aliases(alias_normalized);
```

### The Resolution Pipeline (4 Steps)

Every entity name extracted by the LLM passes through this pipeline before being
linked to a memory. The pipeline is deterministic (Steps 1-3) with LLM assistance
(Step 4) feeding future lookups.

```
LLM extracts: "PostgreSQL 15"
    |
    v
Step 1: Exact canonical match           "postgresql 15" ≠ "postgresql" → miss
    |
    v
Step 2: Alias table lookup              no alias "postgresql 15" → miss
    |
    v
Step 3: Fuzzy code match                "postgresql" is substring of "postgresql 15" → HIT!
    |   → link to entity #5 "postgresql"
    |   → auto-create alias: ("postgresql 15" → entity #5, source="fuzzy_auto")
    |   → next time "PostgreSQL 15" appears, Step 2 catches it instantly
    |
    v
Done. Memory linked to entity #5.
```

When no step matches → create new entity.

### Step-by-Step Implementation

```python
async def resolve_entity(
    extracted_name: str,
    extracted_type: str,
    db: Database,
) -> int:
    """Resolve an extracted entity name to a canonical entity ID.

    Returns the entity ID (existing or newly created).
    Deterministic: same input always produces same output.
    Self-improving: fuzzy matches auto-register aliases for faster future lookups.
    """
    canonical = canonicalize_entity_name(extracted_name)
    # After this: "PG" → "postgresql", "K8s" → "kubernetes", etc.

    # Step 1: Exact match on canonical_name (cross-type — LLM is inconsistent about types)
    entity = await db.get_entity_by_canonical(canonical)
    if entity:
        return entity.id

    # Step 2: Alias table lookup (cross-type)
    alias = await db.get_entity_by_alias(canonical)
    if alias:
        return alias.canonical_id

    # Step 3: Fuzzy match against existing entities of same type
    candidates = await db.get_entities_by_type(extracted_type)
    match = fuzzy_entity_match(canonical, candidates)
    if match:
        # Auto-register alias so Step 2 catches this next time
        await db.insert_alias(
            alias=extracted_name,
            alias_normalized=canonical,
            canonical_id=match.id,
            source="fuzzy_auto",
        )
        return match.id

    # Step 4: No match — create new entity
    new_id = await db.insert_entity(canonical, extracted_type, extracted_name)
    return new_id
```

> **Note:** Steps 1-2 are **cross-type** (no type filtering). This prevents duplicates when
> the LLM extracts "auth-service" as type `service` in one document and type `api` in another.
> Step 3 filters by type because fuzzy matching is less precise and type-filtering reduces
> false positives.

### Fuzzy Match Rules

Entity names are short (1-5 tokens). Simple deterministic rules outperform
embedding similarity for this use case:

```python
def fuzzy_entity_match(
    new_name: str,
    candidates: list[Entity],
) -> Entity | None:
    """Deterministic fuzzy match for short entity names.

    Rules applied in order, first match wins:
    1. Substring containment: "postgresql" in "postgresql 15"
    2. Token overlap: {"postgresql", "15"} ∩ {"postgresql"} ≥ 80% of shorter name
    3. Hyphen/space normalization: "pay-api" matches "pay api"
    """
    # Pre-normalize: remove hyphens, collapse spaces
    new_normalized = new_name.replace("-", " ").replace("_", " ")
    new_tokens = set(new_normalized.split())

    best_match = None
    best_score = 0.0

    for candidate in candidates:
        existing = candidate.canonical_name.replace("-", " ").replace("_", " ")
        existing_tokens = set(existing.split())

        score = 0.0

        # Rule 1: Substring containment
        # "postgresql" in "postgresql 15" → match
        # "pay" in "pay api" → match
        if existing in new_normalized or new_normalized in existing:
            longer = max(len(existing), len(new_normalized))
            shorter = min(len(existing), len(new_normalized))
            score = shorter / longer  # penalize large length differences

        # Rule 2: Token overlap
        # {"postgresql", "15"} ∩ {"postgresql"} = {"postgresql"}
        # overlap = 1, shorter name has 1 token → ratio = 1.0 → match
        elif new_tokens & existing_tokens:
            overlap = new_tokens & existing_tokens
            shorter_len = min(len(new_tokens), len(existing_tokens))
            score = len(overlap) / shorter_len

        if score > best_score:
            best_score = score
            best_match = candidate

    # Threshold: require ≥ 80% match confidence
    if best_score >= 0.8:
        return best_match
    return None
```

### What Each Step Catches

| Step | Input | Matches To | How |
|------|-------|-----------|-----|
| 0. Abbrev | "PG" | entity #5 "postgresql" | `KNOWN_ABBREVIATIONS["pg"]` → "postgresql" → exact match |
| 0. Abbrev | "K8s" | entity #7 "kubernetes" | `KNOWN_ABBREVIATIONS["k8s"]` → "kubernetes" → exact match |
| 0. Abbrev | "Postgres" | entity #5 "postgresql" | `KNOWN_ABBREVIATIONS["postgres"]` → "postgresql" → exact match |
| 1. Exact | "postgresql" | entity #5 "postgresql" | `canonical_name = canonical_name` |
| 1. Exact | "PostgreSQL" | entity #5 "postgresql" | canonicalize lowercases |
| 2. Alias | "adaptive scheduling" | entity #42 "on-demand processing" | alias table populated by LLM/admin |
| 3. Fuzzy | "postgresql 15" | entity #5 "postgresql" | "postgresql" is substring |
| 3. Fuzzy | "pay api" | entity #1 "pay-api" | hyphen/space normalization |
| 3. Fuzzy | "kafka broker" | entity #6 "kafka" | token "kafka" overlap = 1/1 |
| 3. Fuzzy | "auth service v2" | entity #2 "auth-service" | "auth service" ⊂ "auth service v2" |
| Miss | "MSAL" (if not in abbrev table) | → NEW entity | no overlap with "microsoft authentication library" |
| Miss | custom team acronyms | → NEW entity | add to KNOWN_ABBREVIATIONS or wait for LLM alias |

The abbreviation table eliminates the most common misses in software engineering
knowledge bases. Remaining misses are team-specific acronyms that get resolved via
LLM alias extraction or admin merge.

### LLM Alias Extraction (Feeds the Alias Table)

The enrichment prompt still asks the LLM to extract explicit aliases:

```
7. entity_aliases: if the document explicitly states that two names refer to the same
   thing (e.g., "OnDemand Payroll, internally called Project Payroll"), return:
   [{"canonical": "OnDemand Payroll", "aliases": ["Project Payroll"], "evidence": "..."}]
```

These populate the alias table, making Step 2 smarter over time.
But this is an **accelerator, not the primary defense**.

### Alias Validation Gate (Preventing Corruption)

LLM-extracted aliases are validated before insertion. This prevents the most dangerous
failure mode: a hallucinated alias that silently misroutes all future entity lookups.

```python
from difflib import SequenceMatcher

def validate_alias(alias_name: str, canonical_name: str) -> bool:
    """Check if an LLM-extracted alias has ANY resemblance to the canonical name.

    If the LLM says "pay-api" is an alias for "payment-service", that's likely
    wrong — they share no string similarity. Block it.

    If the LLM says "Project Payroll" is an alias for "OnDemand Payroll", that's
    plausible — they share word "Payroll". Allow it.

    For abbreviations that share no string similarity (e.g., "ODP" → "OnDemand Payroll"),
    the evidence field from the LLM must contain the explicit statement from the document.
    """
    a = canonicalize_entity_name(alias_name)
    c = canonicalize_entity_name(canonical_name)

    # Check 1: Any token overlap?
    a_tokens = set(a.replace("-", " ").split())
    c_tokens = set(c.replace("-", " ").split())
    if a_tokens & c_tokens:
        return True  # shared word = plausible alias

    # Check 2: Substring containment?
    if a in c or c in a:
        return True

    # Check 3: String similarity (SequenceMatcher, similar to Jaro-Winkler for short strings)
    ratio = SequenceMatcher(None, a, c).ratio()
    if ratio >= 0.5:
        return True

    # No resemblance — this alias is suspicious.
    return False


async def insert_llm_alias(alias_name: str, canonical_name: str, canonical_id: int, evidence: str, db: Database):
    """Insert an LLM-extracted alias, with validation."""
    if validate_alias(alias_name, canonical_name):
        await db.insert_alias(alias_name, canonicalize_entity_name(alias_name), canonical_id, "llm_extracted")
    else:
        # No string resemblance — could be a legitimate abbreviation OR a hallucination.
        # Queue for admin review instead of auto-inserting.
        await db.insert_pending_alias(
            alias=alias_name,
            canonical_id=canonical_id,
            evidence=evidence,
            reason="No string similarity between alias and canonical name",
        )
        logger.warning("LLM alias flagged for review", extra={
            "alias": alias_name, "canonical": canonical_name, "evidence": evidence
        })
```

**What this catches:**

| Alias | Canonical | Similarity | Result |
|-------|-----------|-----------|--------|
| "Project Payroll" | "OnDemand Payroll" | token overlap: "payroll" | ✅ Auto-insert |
| "ODP Runbook" | "ODP" | substring: "odp" ⊂ "odp runbook" | ✅ Auto-insert |
| "pay-api" | "payment-service" | no overlap, ratio=0.26 | ⚠️ Flagged for review |
| "auth-svc" | "billing-service" | token overlap: "service" — wait, false positive? | ✅ Auto-insert (false positive risk is low — admin can remove) |
| "ODP" | "OnDemand Payroll" | no overlap, ratio=0.15 | ⚠️ Flagged for review |

Note: "ODP" → "OnDemand Payroll" gets flagged because the abbreviation shares no string
similarity. This is a **correct flag** — the system can't verify that "ODP" truly means
"OnDemand Payroll" from string analysis alone. The admin reviews the evidence
("document says: ODP (OnDemand Payroll)") and approves it, promoting it to
`source = "admin_manual"`. After that, Step 2 catches "ODP" forever.

> **The principle:** Auto-insert when string similarity confirms the alias is plausible.
> Flag for human review when it doesn't. Never blindly trust the LLM.

### Self-Improving Behavior

The system gets better at entity resolution the more documents it processes:

```
Sync 1: "PG" extracted
  Abbreviation table: "pg" → "postgresql" → exact match entity #5. Done.

Sync 1: "PostgreSQL 15" extracted
  Step 3 fuzzy-matches to "postgresql"
  Auto-creates alias: "postgresql 15" → entity #5

Sync 2: "PostgreSQL 15" extracted again
  Step 2 finds alias immediately. No fuzzy match needed. Faster.

Sync 5: Document says "OnDemand Payroll (also known as ODP)"
  LLM extracts alias: "ODP" → "OnDemand Payroll"
  Validation gate: no string similarity → flagged for admin review
  Admin approves → alias inserted with source="admin_manual"
  Now Step 2 catches "ODP" forever.

Sync 10: "payment gateway svc" extracted
  Fuzzy match: "payment gateway" ⊂ "payment gateway svc" → entity #12
  Auto-alias registered. Step 2 catches it next time.
```

```
Resolution accuracy over time (with abbreviation table):

  Sync 1:    ~85% (abbreviation table + exact + fuzzy)
  Sync 10:   ~90% (alias table populated by LLM + auto-registration)
  Sync 50:   ~95% (alias table + admin merges)
  Sync 100+: ~97% (comprehensive alias table, most variants seen)
```

> Without the abbreviation table, initial accuracy drops to ~60-65%.
> The table is the single highest-ROI addition to entity resolution.

### Query Expansion (During Retrieval)

When searching, BM25 queries are expanded with known aliases:

```
User query: "Project Payroll weekly pay"

Step 1: "adaptive scheduling" → alias lookup → canonical entity #42 "on-demand processing"
Step 2: Get all aliases for entity #42 → ["adaptive scheduling", "odp"]
Step 3: Expand BM25 query:

  "Project Payroll weekly pay" ("on-demand processing" OR "adaptive scheduling" OR "odp")
```

This ensures keyword search finds memories regardless of which name was used in the
source document.

---

## 9. Storage Architecture

### Backend Decision

**SQLite + ChromaDB. No Neo4j.** Rationale:

- Sufficient at team scale (up to 50K memories)
- SQLite handles graph-like queries via recursive CTEs and indexed joins
- ChromaDB handles vector similarity search
- No additional deployment dependencies
- Revisit graph DB at 50K+ memories if traversal queries become bottleneck

### Database Schema (Migration #7)

```sql
-- Core entity table (referenced by memory_entities and entity_aliases)
CREATE TABLE IF NOT EXISTS entities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name  TEXT NOT NULL UNIQUE,
    entity_type     TEXT NOT NULL,        -- service, person, technology, api, team, feature
    display_name    TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(canonical_name);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);

-- Core memory table
CREATE TABLE IF NOT EXISTS memories (
    id                  TEXT PRIMARY KEY,
    memory_type         TEXT NOT NULL,          -- fact|decision|convention|procedure
    content             TEXT NOT NULL,
    content_hash        TEXT NOT NULL,           -- SHA-256 for dedup
    tags                TEXT NOT NULL DEFAULT '[]', -- JSON array of topic tags
    scope               TEXT NOT NULL DEFAULT 'team',
    project_key         TEXT,
    confidence          REAL NOT NULL DEFAULT 0.7,
    corroboration_count INTEGER NOT NULL DEFAULT 1,
    contradiction_count INTEGER NOT NULL DEFAULT 0,
    valid_from          TEXT,
    valid_until         TEXT,
    superseded_by       TEXT REFERENCES memories(id),
    status              TEXT NOT NULL DEFAULT 'active',
    extraction_context  TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Provenance: documents that own or corroborate this memory
CREATE TABLE IF NOT EXISTS memory_sources (
    memory_id   TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    doc_id      TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    excerpt     TEXT,                -- specific passage supporting this memory
    support_kind TEXT NOT NULL DEFAULT 'extracted',
    added_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (memory_id, doc_id)
);

-- Entity linkage
CREATE TABLE IF NOT EXISTS memory_entities (
    memory_id   TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    entity_id   INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    PRIMARY KEY (memory_id, entity_id)
);

-- Entity alias registry (populated by fuzzy_auto, llm_extracted, and admin_manual)
CREATE TABLE IF NOT EXISTS entity_aliases (
    alias            TEXT NOT NULL,
    alias_normalized TEXT NOT NULL,
    canonical_id     INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    source           TEXT NOT NULL,      -- "exact" | "fuzzy_auto" | "llm_extracted" | "admin_manual"
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (alias_normalized, canonical_id)
);

-- BM25 full-text search index
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    memory_id UNINDEXED,
    content,
    entities_text,    -- space-separated entity names
    tags_text,        -- space-separated tags
    tokenize='porter unicode61'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope);
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_key);
CREATE INDEX IF NOT EXISTS idx_memories_hash ON memories(content_hash);
CREATE INDEX IF NOT EXISTS idx_memory_sources_doc ON memory_sources(doc_id);
CREATE INDEX IF NOT EXISTS idx_memory_entities_entity ON memory_entities(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_aliases_normalized ON entity_aliases(alias_normalized);
```

### ChromaDB Collections

Two separate collections on the same PersistentClient:

| Collection | Content | Metadata |
|------------|---------|----------|
| `documents` | Summary + tags + document type + complexity | source, source_type, space, token_count, content_hash, version, embedding_text_hash, embedding_vector_hash |
| `memories` | Type-prefixed memory content + canonical entity names | memory_type, source_doc_id, space_or_project, confidence, status, content_hash, embedding_text_hash, embedding_vector_hash |

**Why separate?** Document embeddings (summary + tags) are semantically different from
memory embeddings (atomic facts). Mixing them degrades retrieval quality.

### Memory Embedding Text Construction

```python
def memory_embedding_text(memory: Memory, entity_names: list[str]) -> str:
    prefix = {
        "fact": "Fact", "decision": "Decision", "convention": "Convention",
        "procedure": "Procedure"
    }[memory.memory_type]
    entities = ", ".join(entity_names)
    return f"{prefix}: {memory.content}\nEntities: {entities}"
```

Memory embeddings use canonical entity names read from `memory_entities JOIN
entities`, not temporary LLM entity order. The type prefix causes memories of
the same type to cluster in embedding space, improving type-filtered retrieval.

Document embeddings are separate from memory embeddings and use the enrichment
metadata payload:

```python
def document_embedding_text(metadata: DocumentMetadata) -> str:
    return f"{metadata.summary}\n{' '.join(metadata.tags)}\n{metadata.doc_type}\n{metadata.complexity}"
```

Both Chroma collections store two freshness proofs:

- `embedding_text_hash`: hash of the exact text sent to the embedding model.
- `embedding_vector_hash`: hash of the exact vector payload stored in Chroma.

The text hash proves the vector was created from the current SQLite truth. The
vector hash catches payload drift where Chroma metadata says a row is fresh but
the stored vector payload no longer matches that metadata.
Vector writes stamp `embedding_vector_hash` only after Chroma persists the
embedding and returns it. This avoids false health failures from tiny numeric
differences between the Python vector passed to Chroma and the vector Chroma
stores.

### Deletion Consistency

SQLite foreign-key enforcement is enabled. Deletion paths still keep explicit
application-level cleanup where external indexes or lifecycle semantics are
involved:

- Source/document removal deletes source-support links and retires memories only
  when no usable source support remains. Usable support includes extracted and
  corroborated provenance rows whose documents still exist.
- Memory retirement removes the memory from FTS5 and ChromaDB default indexes.
- Privacy/compliance purge deletes memory rows, FTS5 rows, ChromaDB vectors,
  provenance links, and local document artifacts.

### FTS5 Sync

FTS5 virtual table requires manual sync. Every memory lifecycle write must route
through MemoryStore, which coordinates SQLite, FTS5, and ChromaDB. Do not write
`memories_fts` directly from LLM output.

Canonical memory insert and supersede both follow this derived-index sequence:

1. Insert or supersede the `memories` row in SQLite.
2. Link durable provenance in `memory_sources`.
3. Link canonical entities in `memory_entities`.
4. Rebuild `memories_fts` from `memories JOIN memory_entities JOIN entities`.
5. Build the memory embedding text from the same canonical entity names.
6. Upsert the Chroma memory vector with `content_hash`, `embedding_text_hash`,
   and `embedding_vector_hash`.

This order makes SQLite the source of truth and prevents FTS/Chroma from storing
temporary LLM entity ordering when canonical entity resolution produced a
different durable entity set.

---

## 10. Retrieval Architecture

### Two-Tier: Memories (Primary) + Documents (Backing)

```
Query + explicit filters -> [Query Analyzer] -> extracts entities
                |
    +-----------+-----------+
    |           |           |
    v           v           v
 Vector    BM25/FTS5    Entity-Graph
 Search    Keyword      Traversal
    |           |           |
    +-----------+-----------+
                |
    [Reciprocal Rank Fusion]
                |
    [Relational source/date/visibility checks]
                |
    [Optional Reranker (top-20, only for ambiguous results)]
                |
    Memory Cards (Level 0: ~60 tokens each)
         | source evidence needed
    Memory Detail (Level 1: 100-500 tokens)
         | agent needs backing evidence
    Source Artifact (Level 2: via get_resource on content_url/pdf_url)
```

### Query Analysis (Two-Tier Entity Detection)

Entity detection, not a 7-type classifier and not temporal-intent inference.
The agent explicitly passes `memory_types`, `source_filter`, and date-only
`time_range` via the tool schema — the analyzer doesn't need to guess intent.

**Entity mentions (regex → LLM fallback)**

*Tier 1 — Regex (< 5ms):* The query is canonicalized with `canonicalize_entity_name()`
(hyphens/underscores → spaces) to match the canonicalized entity names in the database.
Then matched against known entity canonical names **and aliases** (both loaded into the
detection dict at search startup). Word boundaries use `[^a-zA-Z0-9]` (any non-alphanumeric
character). Longest names matched first to prevent sub-matches. Matched character ranges are
tracked to prevent overlapping detections. Each entity ID appears at most once (deduplicated
across canonical name and aliases).

*Tier 2 — LLM fallback (~ 200ms):* When regex finds nothing, the full entity list (with
aliases grouped under canonical names) is sent to Claude Haiku along with the query. The LLM
identifies entities referenced directly, by abbreviation, or semantically (e.g., "the service
that handles payments" → payment-gateway). Returns a JSON array of entity IDs, validated
against the known entity set. Hard timeout of 1 second. Retry on transient API errors
(max 1 retry). Falls back silently to no entities on any failure.

Detected entity IDs feed two channels: **Entity Graph** (direct links + 1-hop expansion)
and **BM25** (alias expansion of the keyword query). This means entity detection runs
sequentially before channel launch — both channels depend on the result.

**All queries** run vector + BM25 in parallel. Graph traversal is additive (only when
entities are detected). Explicit source/date filters are applied after fusion by the
relational store so no retrieval channel can bypass visibility, source, or date semantics.
MemForge does not infer date ranges from query text; agents convert phrases such as
"last week" into explicit `start_date` / `end_date` values before calling the tool.

> **Simplified from earlier design:** A 7-type classifier with per-type strategy routing
> tables was removed. The `memory_types` filter from the tool schema handles type-specific
> retrieval directly — no need for the system to infer it from the query text.

### Ranking Formula

```
final_score = 0.85 * rrf_normalized + 0.15 * recency
```

Where `recency = exp(-0.693 * age_days / 90)` (half-life of 90 days).

> **Simplified from earlier design:** The original formula had 6 weighted parameters
> (confidence, source_authority, corroboration, access_frequency). These are deferred.
> Add one signal at a time with A/B evaluation only when retrieval tests show the need.

### Reciprocal Rank Fusion (RRF)

```
RRF_score(memory) = SUM over strategies S of: 1 / (k + rank_in_S(memory))
where k = 60 (standard constant)
```

**Known tradeoff:** Memories found by only one channel (especially graph-only discoveries
via 1-hop entity traversal) score ~3x lower than memories found by all channels. At small
memory counts (< 1K) this rarely matters because result sets are small enough. At scale,
cross-encoder reranking (below) addresses this.

### Cross-Encoder Reranking (Planned, Config-Gated)

After RRF fusion, optionally rerank the top-N candidates using a cross-encoder model.
This scores each (query, memory) pair independently, resolving the channel-count bias
in RRF by evaluating actual query-memory relevance regardless of which channel found it.

```
RRF top-30 candidates → Cross-encoder scores each (query, memory.content) → Final top-10
```

Implementation: Claude Haiku via existing Anthropic SDK (~200ms, ~$0.001/query).
Alternative: dedicated reranker API (Cohere, Jina) at ~50ms if query volume grows.
Config-gated via `retrieval.enable_reranking` (default: false). Enable at ~1K memories.

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Query analysis | < 5ms | Rule-based, no LLM |
| Vector search (ChromaDB) | < 50ms | Up to 100K memories |
| BM25 search (FTS5) | < 10ms | SQLite FTS5 |
| Graph traversal | < 30ms | 1-hop entity lookup + join |
| RRF fusion | < 2ms | In-memory merge |
| Total search (no reranking) | < 150ms | Parallel strategies + fusion |
| Total search (with reranking) | < 500ms | Cross-encoder for top-20 |
| get_memory | < 20ms | Single SQLite lookup + join |

### Caching

**Embedding cache only** (LRU, 256 entries). Saves the ~50-200ms OpenAI API round-trip
for repeated/similar queries within a session. Trivial to implement (dict + hash).

> **Deferred:** Entity name cache and result cache were removed. SQLite queries are fast
> enough at this scale (< 10ms). Add caching if latency profiling shows need.

### Memory-Only Unified Search

Memory search returns only memory cards. Direct document hits, document vectors,
and source artifacts remain part of sync, health, repair, and evidence access,
but they are not mixed into `search` results. Agents drill down through
`get_memory` before choosing a source artifact.

---

## 11. MCP Tool Interface

### Retrieval Tools + Intake Tool

```
search             "What do I need to know?"
                    -> memories (primary) + documents (fallback)
                    -> includes service artifact URLs for source documents
                    -> one call for any knowledge question

get_memory         "Tell me more about this specific memory"
                    -> full content + all source documents with artifact URLs
                    -> provenance chain + related memories
                    -> only called when agent needs to verify/deep-dive

get_resource       "Read this source artifact"
                    -> accepts content_url/pdf_url from get_memory
                    -> returns text, a local cache file path, or base64 bytes

submit_agent_session_document
                    -> stores an explicit already-generated markdown summary
                    -> writes a thin receipt for lineage and dedupe
                    -> feeds the generated source through normal sync when requested
```

MCP remains the model-visible memory interface. In Codex and Claude Code
plugins, MCP is implemented as a local thin proxy: `search`, `get_memory`,
and `submit_agent_session_document` are forwarded to the MemForge API, while
`get_resource(mode="file")` downloads artifacts into a client-local cache and
returns a real local path. Agent lifecycle hooks use the Admin API separately:
`POST /api/hooks/context` for compact prompt context and
`POST /api/hooks/receipts` for lifecycle receipt write-back. Automatic
agent-session capture uses `POST /api/agent-sessions/windows`; explicit
already-generated summaries still use `POST /api/agent-sessions/documents`.

### Local Proxy Request Path

```text
Codex / Claude Code
  -> MCP stdio
  -> plugin-local MemForge proxy
  -> HTTP(S) MemForge API
```

The local proxy is the transport bridge, not a memory engine. It owns MCP stdio,
service URL/token configuration, artifact URL validation, and agent-local cache
writes. The service owns search, memory detail, session intake, artifact bytes,
provenance, tenancy, and future SaaS auth. The non-MCP `/api/recent-changes`
endpoint remains an API surface for source-change views.

The CLI exposes the same read flow for humans and scripts:
`memforge search`, `memforge get-memory`, and `memforge get-resource`. These
commands call the Admin API and follow the same artifact-cache semantics as the
MCP proxy; they do not read the local SQLite store or container filesystem
directly.

| Agent call | Local proxy behavior | MemForge service call |
| --- | --- | --- |
| `search` | Normalize MCP args and forward | `POST /api/memories/search` |
| `get_memory` | Forward by memory ID | `GET /api/memories/{memory_id}` |
| `submit_agent_session_document` | Forward generated markdown summary | `POST /api/agent-sessions/documents` |
| `get_resource(mode="text")` | Fetch and return text inline | `GET` service artifact URL |
| `get_resource(mode="base64")` | Fetch and return encoded bytes | `GET` service artifact URL |
| `get_resource(mode="file")` | Fetch bytes, write local cache, return `local_path` | `GET` service artifact URL |

The MemForge service returns portable artifact URLs such as
`/api/documents/{document_id}/content` and `/api/documents/{document_id}/pdf`.
It does not return host-local, container-local, or SaaS-local file paths.

### Tool: `search`

```json
{
  "name": "search",
  "description": "Search visible MemForge memories. Returns memory cards only.",
  "inputSchema": {
    "query": "string (optional when source_filter or time_range is present)",
    "source_filter": {
      "source_ids": "array of exact IDs returned by list_sources (optional)",
      "clients": "array of exact client ids: codex|claude-code (optional)"
    },
    "time_range": {
      "date_type": "source_updated_at|memory_updated_at",
      "start_date": "YYYY-MM-DD (optional)",
      "end_date": "YYYY-MM-DD (optional)"
    },
    "top_k": "integer, default 10"
  }
}
```

`source_filter` is exact and optional. If an agent is unsure, it should omit the
facet and search all visible memories. The request boundary rejects unknown
source IDs or clients instead of guessing, normalizing, or returning an
accidentally empty result set. Repo-scoped MCP search is disabled until MCP
workspace roots are reliable across supported hosts. The schema does not expose
`current_repo_only`; if a stale caller still sends it, the proxy rejects the
request and tells the agent to omit the filter for a broader search.

**Output per result (Level 0 -- memory card):**

```json
{
  "memory_id": "mem-a7f3b2c1",
  "memory_type": "decision",
  "summary": "Team chose gRPC over REST for inter-service calls...",
  "confidence": 0.90,
  "relevance_score": 0.87,
  "tags": ["grpc", "architecture", "performance"],
  "corroborated_by": 2,
  "last_observed_at": "2026-03-15T10:30:00Z",
  "freshness": "current",
  "contradiction_warning": null
}
```

Search results intentionally omit top-level source and artifact fields. Agents
call `get_memory` when they need source titles, complete provenance,
contradiction context, corroborating sources, or artifact URLs before deciding
which artifact to read.

**`freshness` field values:**

| Value | Meaning |
|-------|---------|
| `current` | Memory's source document has not changed since last extraction |
| `stale` | Source document was updated but memory hasn't been re-extracted yet |
| `unverified` | Source document is no longer accessible (gene auth failed, etc.) |

**`pdf_url`**: Only available when MemForge has a service-readable PDF artifact
for the document. Null when a PDF rendition was not exported or is not readable
from service storage.

Admin API memory detail and MCP memory detail share the same artifact URL
contract. They expose service artifact URLs, not service-local storage paths.

### Tool: `get_memory`

```json
{
  "name": "get_memory",
  "inputSchema": {
    "memory_id": "string (required)"
  }
}
```

Returns: full content, context, all source documents with service artifact URLs,
related memories, entity links, confidence, and lifecycle metadata.

Use `get_memory` when an agent needs source documents for a memory,
corroboration, contradictions, entities, lifecycle metadata, or artifact URLs.

### Tool: `get_resource`

```json
{
  "name": "get_resource",
  "inputSchema": {
    "url": "string (required)",
    "mode": "text | file | base64",
    "max_chars": "integer",
    "max_bytes": "integer"
  }
}
```

`get_resource` reads a MemForge document artifact URL returned by `get_memory`
by fetching it through `MEMFORGE_API_URL` (default
`http://127.0.0.1:8765`). Text artifacts can be returned inline. PDFs and other
binary artifacts can be saved to a local cache file for agent runtimes that can
read files, or returned as base64 when that is more practical. The cache file is
created by the local plugin proxy, not by the MemForge service, so `local_path`
remains valid for Docker and future SaaS deployments.

### Agent Decision Tree

```
Agent receives a question
    |
    +-- Needs memory evidence -> search
          |
          +-- Recent window? -> include time_range on search
          |
          +-- Need source evidence? -> get_memory
                |
    |           +-- Need backing evidence? -> get_resource(content_url/pdf_url)
    |
    Done. No routing ambiguity.
```

---

## 12. Implementation Phases

### Phase 1: Foundation + Gene Core (Week 1-2)

**Week 1 focus: Data layer + Gene abstractions (no LLM yet)**

- Project setup (Python package, pyproject.toml, config system)
- Database schema (all tables: entities, memories, memory_sources, memory_entities, memory_relations, entity_aliases, memories_fts, documents, sources, agent_session_receipts, sync_state, sync_history, schedule_config, llm_config)
- Memory data models (dataclasses)
- Gene ABC, GeneMetadata, GeneCapabilities, NormalizedContent
- GeneRegistry with explicit built-in registration
- Agent session, Confluence, Jira, and Teams genes (normalizers that produce comprehensive markdown)
- GeneSyncOrchestrator (discover -> fetch -> normalize -> store)
- Basic document storage and sync WITHOUT enrichment (prove the pipeline works)

**Week 2 focus: Memory extraction layer**

- Enrichment prompt (Call 1) + Memory extraction prompt (Call 2)
- MemoryEngine: extract memories from enricher output
- MemoryStore: SQLite + ChromaDB operations, deduplication, FTS5 sync
- ChromaDB "memories" collection (parameterized get_chroma_collection)
- Hook memory extraction into GeneSyncOrchestrator after enrichment
- Full initial sync to populate memory corpus
- Basic CLI: `memforge init`, `memforge sync`, `memforge api`

### Phase 2: Retrieval (Week 3-4)

- SearchEngine: multi-channel (vector + BM25/FTS5 + entity-graph) plus authoritative relational filters
- Query analyzer (rule-based classification)
- RRF fusion implementation
- Ranking formula with all signals (recency, confidence, authority, corroboration, access)
- Progressive disclosure (Level 0/1/2)
- Unified `search` MCP tool
- `get_memory` MCP tool
- Recent-memory questions through `search` with `time_range`
- `submit_agent_session_document` MCP tool (explicit generated session-document intake)
- Document fallback in search results
- Query expansion with entity aliases
- Caching layer (entity cache, embedding cache, result cache)
- Admin API: memory endpoints, entity endpoints, health check

### Phase 3: Admin UI + Per-Gene Schedules (Week 5)

- Admin REST API: all endpoints from Section 14d
- Per-gene schedule support in APScheduler
- Dynamic config schema -> UI rendering for gene setup
- Source management UI (add/edit/delete/sync genes)
- Memory browser UI
- Entity management UI (merge, aliases)

### Phase 4: Teams + Outlook Genes (Week 6)

- OAuth2 auth provider for Microsoft Graph API (MSAL)
- Teams gene: Graph API, thread batching, significance filter
- Outlook gene: email threads + calendar events, privacy controls
- Comprehensive normalizers for both (all structured data in markdown)

### Phase 5: Lifecycle, Quality & Hardening (Week 7-8)

- Memory reconciliation on document updates (ADD/UPDATE/SUPERSEDE/DELETE)
- Reconciliation prompt (Section 14e)
- Contradiction detection and flagging
- Lifecycle cleanup: expiry retirement and zero-support retirement
- Staleness tracking (pending_review on extraction failure)
- Entity merge suggestion pipeline (embedding clustering)
- Memory-to-memory relations population (elaborates, supports)
- Retrieval quality evaluation set + metrics (Recall@k, MRR, NDCG)
- Observability: structured logging, health check, metrics dashboard
- Admin UI: quality dashboard, contradiction view, merge suggestions
- `memforge rebuild-vectors` CLI command

---

## 13. Mem0 Patterns: What We Adopt vs Skip

### Patterns We Adopt

| Mem0 Pattern | How We Adapt It |
|-------------|----------------|
| Atomic fact extraction via LLM | Two-call extraction: enrichment (Call 1) + memory extraction (Call 2) with existing memories as context |
| ADD/UPDATE/DELETE/NOOP operations | Plus SUPERSEDE (mem0 conflates with UPDATE) |
| Semantic dedup via embedding similarity | Cosine < 0.08 threshold before insert |
| Confidence scoring | Per-memory, from LLM + corroboration boosting |
| Separate vector collection for memories | "memories" collection in ChromaDB |

### What We Skip and Why

| Mem0 Feature | Why We Skip It |
|-------------|---------------|
| Mem0 as a pip dependency | Conversational vs. document-sourced mismatch too large |
| Mem0 MCP server | Duplicates the MemForge MCP tool contract and does not fit source-backed provenance |
| User/session/agent scoping | We need team/project/source scoping |
| Neo4j graph backend | SQLite sufficient at our scale |
| KV store (Redis) | SQLite indexed content_hash serves same purpose |
| Mem0's extraction prompts | Designed for chat messages, not structured documents |

### Why Not Use Mem0 Directly

The fundamental mismatch:

| Dimension | Mem0 | MemForge |
|-----------|------|-------------|
| Input | Short message pairs | Long-form documents (1K-100K tokens) |
| Who remembers | One user's personal facts | Entire team's collective knowledge |
| Update signal | User corrects in conversation | Source document is edited |
| Provenance | Optional | Critical (doc, version, passage) |
| Deduplication | Same user repeats | Same fact in 3+ source systems |
| Scoping | user/session/agent | team/project/source |

---

## 14. Feasibility Notes

### Confirmed Feasible

- **Enrichment prompt (Call 1)**: Free-text JSON parsing with permissive `.get()` defaults.
  No schema validation. max_tokens = 4000.
- **Memory extraction prompt (Call 2)**: Separate call with entities + existing memories as
  context. max_tokens = 8192.
- **Reconciliation prompt (Call 3)**: Runs only on changed documents and receives the
  updated normalized document plus same-document active memories. max_tokens = 4096.
- **FTS5**: SQLite 3.47.1 confirmed. FTS5 extension available.
- **Second ChromaDB collection**: PersistentClient supports multiple collections natively.
- **Database migration**: Fits as migration #7 in existing pattern.
- **MCP tool merge**: Declarative tool definitions, ~50-80 lines of changes.
- **FK enforcement**: Enabled; sync inserts documents before memories.
- **ChromaDB client management**: Shared singleton avoids local lock contention.
- **FTS5 sync**: Managed in the MemoryStore layer for memory insert/update/delete paths.
- **Document vector ownership**: `DocumentVectorIndex` owns document Chroma
  writes while `MemoryStore` owns memory lifecycle consistency. Sync uses
  document-index snapshots so DB/document-vector writes can roll back together.
- **Confluence PDF health**: Confluence sources require local PDF URI coverage;
  missing PDFs are reported by `/api/health` and fail sync instead of being
  hidden as success.
- **Agent hook integration**: Codex and Claude Code plugin packages call the
  Admin API for hook context/write-back and expose MCP tools through bundled
  `.mcp.json`.

### Requires Attention

- **Index repair automation**: The local CLI can repair FTS5 and Chroma metadata
  drift from SQLite. Scheduled/alerted repair is still future work if drift recurs.
- **Plugin beta hardening**: Install docs and project identity mapping are still
  needed before broad Codex/Claude rollout.
- **Agent session hardening**: Generated session summaries need provenance-aware
  extraction and prompt-injection hardening before they should be treated as a
  high-confidence source.
- **Outlook gene**: Still planned; requires Microsoft Graph OAuth2 and privacy controls.
- **Quality dashboard**: Staleness, contradiction, and extraction-quality metrics are
  not yet exposed in the Admin UI.
- **OAuth2 for Teams/Outlook**: Existing auth only handles browser-based SSO.
  Need OAuth2 provider for Microsoft Graph API.

---

## 14a. Error Handling Strategy

### LLM Extraction Failures

| Failure Mode | Detection | Response |
|-------------|-----------|----------|
| Malformed JSON (not parseable) | `json.loads()` raises | Strip markdown fences, retry parse. If still fails, use fallback (empty memories, basic metadata). Log warning. |
| JSON truncated (hit max_tokens) | JSON parse fails on incomplete structure | Increase max_tokens and retry once. If still truncated, parse what's available, log warning. |
| No memories extracted | `data.get("memories", [])` returns `[]` | Accept — some documents genuinely have no extractable atomic facts. Store document without memories. |
| Hallucinated entity names | Entity not in existing entity list | Create as new entity. The alias discovery pipeline will eventually merge if it's a duplicate. |
| Many memories extracted | `len(memories)` is high | Keep every durable, semantically distinct candidate. Exact duplicates collapse deterministically; a complete CandidateLedger removes fully redundant claims within the Source Unit revision. Explicit input budgets fail closed instead of truncating the ledger. |
| LLM timeout / API error | httpx timeout or 5xx response | Retry with exponential backoff (3 attempts). If all fail, store document without enrichment, mark for re-enrichment on next sync. |

### Fallback Metadata

When enrichment completely fails, store the document with:
```python
def fallback_metadata(doc_id: str) -> EnrichmentResult:
    return EnrichmentResult(
        summary="Enrichment failed. Document content remains available through source artifacts.",
        tags=[], entities=[], relationships=[],
        doc_type="unknown", complexity="unknown",
        memories=[], entity_aliases=[],
    )
```

### ChromaDB / SQLite Consistency

The system has two data stores that must stay in sync. Strategy:

1. **SQLite is the source of truth.** FTS5 and ChromaDB are derived indexes.
2. **Write ownership**: MemoryStore owns memory lifecycle writes across SQLite,
   FTS5, and ChromaDB. Memory FTS rows are rebuilt from canonical `memory_entities`
   after entity links are committed. Chroma memory vectors are embedded from that
   same canonical entity set.
3. **Repair command**: `memforge maintenance repair-indexes` rebuilds FTS5,
   removes non-search-visible memory vectors, and repairs memory/document Chroma
   freshness metadata from SQLite. It also prunes FTS orphans and repairs missing
   vector payload hashes without needing source documents.
4. **Health check**: `/api/health` runs deterministic SQLite, FTS5, memory Chroma,
   and document Chroma consistency checks. It detects active/non-active index
   visibility drift, FTS duplicates, FTS orphans, Chroma orphans, metadata hash
   drift, and vector payload hash drift. Any drift degrades health instead of
   being hidden.

### Gene Sync Failures

| Failure Mode | Response |
|-------------|----------|
| Authentication failure | Log error, mark source as `auth_failed`, skip sync, alert admin |
| API rate limit (429) | Exponential backoff with jitter, respect Retry-After header |
| Individual document fetch failure | Log, continue syncing other documents, record in sync_history.failed_docs |
| Entire source API down | Log, skip source, retry on next scheduled sync |
| Partial sync (some docs succeed, some fail) | Commit successful docs, log failures, report partial completion |

### Rate Limiting for LLM Calls

```python
# Semaphore limits concurrent LLM calls during sync
llm_semaphore = asyncio.Semaphore(3)  # max 3 concurrent enrichment calls

async with llm_semaphore:
    result = await enricher.enrich_document(doc_id, content, ...)
```

For initial backfill of 10K documents: ~3-4 hours at 3 concurrent calls with ~2s per call.
Estimated LLM cost: ~$300-400 (Claude Sonnet, ~5K avg input + ~1.5K avg output tokens per doc).

---

## 14b. Security & Data Governance

### Authentication

| Interface | Auth Method |
|-----------|------------|
| Agent MCP proxy | Optional bearer/API token forwarded to the Admin API; the proxy itself runs locally. |
| Admin REST API | JWT tokens (access + refresh). bcrypt password hashing. Admin and viewer roles. |
| Gene connections | Per-gene auth (SSO for Confluence/Jira, OAuth2 for Teams/Outlook) |

### Credential Storage

- Source config is stored in the `sources.config` JSON column.
- Secret fields such as PATs, API keys, client secrets, and browser-session
  cookies are moved into encrypted source-secret records and replaced with
  stable references in source config.
- The local encryption key is managed under `<base_dir>/secrets/` by default.
  `MEMFORGE_SECRET_KEY` or `MEMFORGE_SECRET_KEY_FILE` can override it
  for controlled deployments.

### Data Governance for Teams/Outlook

| Concern | Mitigation |
|---------|-----------|
| Private emails indexed without consent | Outlook gene is opt-in per shared mailbox/folder. Personal mailboxes require explicit admin opt-in with confirmation dialog. |
| PII in extracted memories | Enrichment prompt includes: "Do NOT extract personal information (phone numbers, home addresses, personal medical info). Extract only work-relevant technical and project knowledge." |
| GDPR right-to-deletion | `purge_source_data(source_id)` deletes all memories, documents, and entities from a source. Admin UI provides per-source purge button. |
| Sensitive content in Teams DMs | Teams gene only syncs **channel** messages, not 1:1 or group chats. Configurable channel include/exclude patterns. |
| Access control on memories | All memories are team-visible (by design). If per-team isolation is needed, run separate MemForge instances. |

---

## 14c. Configuration Management

### Configuration Sources (Priority Order)

1. **Environment variables** (highest priority for process config): `MEMFORGE_*` prefix
2. **Config file**: `~/.memforge/config.toml`
3. **Database**: `sources`, `schedule_config`, and admin-managed `llm_config`
4. **Defaults** (lowest priority): Hardcoded in code

For sync runtime, admin-managed `llm_config` values override process defaults
when present; missing DB values fall back to the environment/config-file
`AppConfig`.

The admin UI treats model configuration as explicit operator input. It does not
present fallback defaults as onboarding choices. The Settings screen calls
`POST /api/llm-config/probe` to test whether the API process can reach the
given endpoint and, when supported by the provider or proxy, fetch available
model IDs before saving. This keeps Docker and future hosted deployments on the
same path: the URL must be reachable from the MemForge service process, not
only from the user's browser.

For the current self-hosted admin API, the probe is an operator tool for the
local service owner. Before enabling the same endpoint in a multi-tenant SaaS
control plane, it must be tenant-authenticated and host-restricted so one
tenant cannot use MemForge to probe internal service networks or send API-key
headers to untrusted endpoints.

### Configurable Parameters

```toml
# ~/.memforge/config.toml

base_dir = "~/.memforge"          # Root data directory

[storage]
db_path = "db/memforge.db"        # SQLite path (relative to base_dir)
chroma_path = "vectors/chroma"        # ChromaDB path (relative to base_dir)
docs_path = "documents"               # Document content path (relative to base_dir)

[llm]
enrichment_model = "claude-sonnet-4-20250514"
enrichment_base_url = "https://api.anthropic.com"
enrichment_api_key = ""               # or MEMFORGE_ENRICHMENT_API_KEY env var
enrichment_max_tokens = 4000
enrichment_max_concurrent = 3         # Semaphore limit
embedding_model = "text-embedding-3-small"
embedding_base_url = "https://api.openai.com/v1"
embedding_api_key = ""               # or MEMFORGE_EMBEDDING_API_KEY env var

[memory]
dedup_cosine_threshold = 0.08         # Below this cosine distance = duplicate
# Lifecycle expiry is maintained by the Admin API scheduler.

[retrieval]
default_top_k = 10
rrf_k = 60                           # RRF constant
recency_half_life_days = 90
embedding_cache_size = 256

[server]
admin_api_port = 8765
jwt_secret = ""                       # or MEMFORGE_JWT_SECRET env var
```

Supported environment overrides include:

- `MEMFORGE_BASE_DIR`
- `MEMFORGE_STORAGE_DB_PATH`, `MEMFORGE_STORAGE_CHROMA_PATH`, `MEMFORGE_STORAGE_DOCS_PATH`
- `MEMFORGE_ENRICHMENT_MODEL`, `MEMFORGE_ENRICHMENT_BASE_URL`, `MEMFORGE_ENRICHMENT_API_KEY`
- `MEMFORGE_EMBEDDING_MODEL`, `MEMFORGE_EMBEDDING_BASE_URL`, `MEMFORGE_EMBEDDING_API_KEY`
- `MEMFORGE_ADMIN_API_PORT`, `MEMFORGE_CORS_ORIGINS`, `MEMFORGE_JWT_SECRET`
- `MEMFORGE_SECRET_KEY` optionally overrides the app-managed local key for encrypting stored source secrets and shared auth sessions, including Atlassian PATs and Jira browser-session cookies. This must be a 32-byte url-safe base64 Fernet key when set.
- `MEMFORGE_SECRET_KEY_FILE` optionally points to the local source-secret key file. When unset, MemForge uses `<base_dir>/secrets/source-secrets.key`.
- Confluence PDF rendering uses WeasyPrint. The Docker image includes the required WeasyPrint runtime libraries and does not bundle a browser.
- Docker build-only mirror variables include `MEMFORGE_DOCKERHUB_PREFIX`, `MEMFORGE_DEBIAN_MIRROR`, `MEMFORGE_DEBIAN_SECURITY_MIRROR`, `MEMFORGE_PYPI_INDEX_URL`, and `MEMFORGE_NPM_REGISTRY`. `.env.mirrors.example` sets these together for restricted or slow registry networks without changing runtime behavior.

### Source Authority Mapping

Complete doc_type to authority score mapping (used in ranking and review-risk
signals, not as an automatic truth hierarchy):

| doc_type | authority_score | Rationale |
|----------|----------------|-----------|
| decision-record | 1.0 | Authoritative decisions |
| design-doc | 0.9 | Architecture source of truth |
| runbook | 0.85 | Operational procedures |
| postmortem | 0.85 | Incident learnings |
| how-to | 0.8 | Practical guides |
| reference | 0.7 | API specs, schemas |
| ticket (Jira) | 0.6 | Work items, may be stale |
| discussion (Teams) | 0.5 | Conversational, context-dependent |
| meeting-notes | 0.5 | Often incomplete |
| email (Outlook) | 0.4 | Personal, may lack context |
| unknown | 0.3 | Unclassified documents |
| generated-agent-summary | 0.25 | Agent-created handoff context; useful, but generated claims need evidence review before replacing authored sources |

### Project Key Resolution

How `project_key` is determined per gene type:

| Gene | project_key source | Example |
|------|-------------------|---------|
| Confluence | `space_key` from Confluence space | "PAY" |
| Jira | `project_key` from Jira project | "PAY" |
| Teams | configured channel/team scope or conversation source grouping | "PAY Engineering" -> "PAY" |
| Outlook | Derived from folder name or configured mapping | "PAY Shared" -> "PAY" |

Current sync sets `project_key` from `ContentItem.space_or_project`. Genes
should populate that field with their best source-native scope, such as a
Confluence space, Jira project, Teams configured scope, or future Outlook
folder mapping. If the item has no scope, the memory is scoped to `"team"`
(global). Agent hooks derive `repo` from the local Git checkout by preferring
the normalized `origin` remote URL, for example `github.com/org/repo`, with the
Git root folder name only as a fallback for local-only repositories. Coding
session memories treat this repo identity as their primary context, while
project mapping remains optional relevance metadata rather than the source of
truth for the session.

---

## 14d. Admin REST API Specification

### Memory Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/memories` | List memories with pagination, filters (type, status, source, project, entity) |
| GET | `/api/memories/{id}` | Get memory detail with provenance |
| PUT | `/api/memories/{id}` | Update memory (admin edit content, confidence, status) |
| DELETE | `/api/memories/{id}` | Hide a memory (set status=retired) |
| GET | `/api/memories/stats` | Memory counts by type, source, status |
| GET | `/api/memories/contradictions` | List memories with contradiction_count > 0 |

### Review Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/memory-reviews` | List open or resolved review decisions |
| GET | `/api/memory-reviews/{id}` | Get incumbent and challenger details for one review |
| POST | `/api/memory-reviews/{id}/approve` | Promote the challenger through lifecycle-safe store paths |
| POST | `/api/memory-reviews/{id}/reject` | Retire the challenger through lifecycle-safe store paths |

### Entity Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/entities` | List entities with pagination, filters (type) |
| GET | `/api/entities/{id}` | Get entity with aliases and linked memories |
| POST | `/api/entities/merge` | Merge two entities (declare one as alias of other) |
| GET | `/api/entities/merge-suggestions` | Get auto-detected merge candidates |
| POST | `/api/entities/{id}/aliases` | Manually add an alias |
| DELETE | `/api/entities/{id}/aliases/{alias}` | Remove an alias |

### Gene/Source Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/genes` | List available genes (from registry) |
| GET | `/api/genes/{name}/config-schema` | Get config schema for UI rendering |
| GET | `/api/sources` | List configured sources |
| GET | `/api/sources/{id}/projects` | List project buckets observed for one source, with document and memory counts |
| POST | `/api/sources` | Add a new source (create gene instance) |
| PUT | `/api/sources/{id}` | Update source config |
| DELETE | `/api/sources/{id}` | Delete source and purge all its data |
| POST | `/api/sources/{id}/sync` | Trigger manual sync |
| GET | `/api/sources/{id}/sync/status` | Get current sync progress |

### Agent Session Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agent-sessions/windows` | Submit a versioned, redacted agent-session evidence window for service-owned canonicalization, package generation, and queued source sync |
| GET | `/api/agent-sessions/completeness` | Summarize processed window outcomes (`package_created`, `no_output`, `failed`) on demand; non-zero failures also surface a `latest_failure` summary (`count`, `reason`, `last_seen_at`) |
| POST | `/api/agent-sessions/documents` | Submit an explicit already-generated session summary document, store receipt lineage, and optionally start the `agent_session` source sync |
| POST | `/api/hooks/receipts` | Record a coding-agent lifecycle hook receipt without creating source material |

### System Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health (DB, ChromaDB, gene connectivity) |
| GET | `/api/stats` | Overall statistics (memory count, entity count, sync history) |
| GET | `/api/schedule` | Get sync schedule config |
| PUT | `/api/schedule` | Update sync schedule |
| GET | `/api/quality/dashboard` | Retrieval quality metrics, staleness rate, contradiction rate |

---

## 14e. Reconciliation Prompt

When a document is updated and existing memories need reconciliation, this is the
third LLM call (only on updates, not new documents). It compares new candidates
against existing active memories linked to the same source document and also
audits those existing memories against the updated document text:

```
You are reconciling team knowledge. A document was updated and new facts
were extracted. Compare them against existing memories from the same document
and the updated document content.

For each new extraction, decide ONE action:

- ADD: Genuinely new information not covered by any existing memory.
- UPDATE: An existing memory covers the same fact but needs minor refinement.
- SUPERSEDE: An existing memory covers the same topic but is now materially wrong.
- DELETE: An existing memory is demonstrably false or was extracted in error.
- NOOP: The new extraction adds nothing beyond what existing memories capture.

Also audit existing memories from this same document against the updated
document. If an existing memory is no longer supported by the updated document
and no new extraction supersedes it, return a DELETE action with its memory_id.
If an existing memory is still supported, you may omit it.

<new_extractions>
{json_list_of_new_candidates}
</new_extractions>

<existing_memories>
{json_list_of_existing_memories_with_ids}
</existing_memories>

<updated_document>
{new_normalized_content}
</updated_document>

Return a JSON array of operations:
[
  {"index": 0, "action": "ADD", "reason": "New fact about deployment"},
  {"index": 1, "action": "SUPERSEDE", "memory_id": "mem-abc123",
   "reason": "Database migrated from v14 to v16", "flag_for_review": false},
  {"index": 2, "action": "NOOP", "memory_id": "mem-ghi789",
   "reason": "Already captured"},
  {"action": "DELETE", "memory_id": "mem-old999",
   "reason": "The updated document no longer supports this memory"}
]
```

In the persistence layer, DELETE from reconciliation means "remove this source
document as support." It is not a hard purge and it does not retire the memory
while other source documents still support it.

---

## 14f. Observability & Monitoring

### Structured Logging

All log entries include: `timestamp`, `level`, `component`, `source_id` (if applicable),
`doc_id` (if applicable), `memory_id` (if applicable), `duration_ms`.

```python
logger.info("memory_extracted", extra={
    "component": "enricher", "doc_id": "confluence-12345",
    "memory_count": 7, "duration_ms": 1823
})
```

### Key Metrics to Track

| Metric | Source | Alert Threshold |
|--------|--------|----------------|
| Memory count (total, by type, by status) | SQLite | -- |
| Extraction success rate | enricher logs | < 90% |
| Average confidence | SQLite aggregate | < 0.6 |
| Dedup hit rate | MemoryStore logs | -- (informational) |
| Contradiction rate | SQLite (contradiction_count > 0) / total | > 10% |
| Search latency p50/p95/p99 | retrieval logs | p95 > 300ms |
| Sync duration per gene | sync_history table | > 2x average |
| Stale memory rate | SQLite (pending_review) / total | > 10% |
| ChromaDB vs SQLite count divergence | health check | Any divergence |

### Health Check Endpoint

`GET /api/health` returns:

```json
{
  "status": "healthy",
  "database": {"status": "ok", "detail": "962 memories"},
  "vector_store": {"status": "ok", "detail": "2 collection(s)"},
  "index_consistency": {"status": "ok", "detail": "No index consistency issues"},
  "genes": {
    "PAY Architecture": {"status": "success", "detail": "2026-05-25T14:38:16.163088+00:00"},
    "Delivery Board Jira Board": {"status": "success", "detail": "2026-05-25T03:49:06.272028+00:00"},
    "Teams - Project Payroll Dev Group": {"status": "failed", "detail": null}
  }
}
```

`index_consistency` checks SQLite, FTS5, memory Chroma, document Chroma, hash
drift, orphan rows, stale non-search-visible vectors, and required source
artifacts such as Confluence PDF URIs. A failed source can appear in `genes`
while the derived indexes remain clean.

---

## 14g. FTS5 Sync Implementation

The `memories_fts` virtual table must be kept in sync manually.

### What Gets Indexed

| FTS5 Column | Source |
|-------------|--------|
| `content` | `memories.content` |
| `entities_text` | Space-joined canonical names from `memory_entities` JOIN `entities` |
| `tags_text` | Space-joined values from `memories.tags` JSON array |

### Sync Points

```python
class MemoryStore:
    async def insert_memory(self, mem: Memory, entity_ids: list[int]):
        await db.insert_memory(mem)
        await db.add_memory_source(mem.id, doc_id, source_type, excerpt)
        for entity_id in entity_ids:
            await db.link_memory_entity(mem.id, entity_id)

        await db.rebuild_memory_fts(mem.id)
        embedding_text = await canonical_memory_embedding_text(mem.id)
        embedding = await embed(embedding_text)
        upsert_with_stored_vector_hash(
            collection,
            ids=[mem.id],
            embeddings=[embedding],
            metadatas=[{
                "status": mem.status,
                "content_hash": mem.content_hash,
                "embedding_text_hash": hash(embedding_text),
            }],
        )

    async def supersede_memory(self, old_id: str, replacement: Memory, entity_ids: list[int]):
        await db.supersede_memory(old_id, replacement)
        await remove_from_search_indexes(old_id)
        await db.add_memory_source(replacement.id, doc_id, source_type, excerpt)
        for entity_id in entity_ids:
            await db.link_memory_entity(replacement.id, entity_id)

        await db.rebuild_memory_fts(replacement.id)
        embedding_text = await canonical_memory_embedding_text(replacement.id)
        embedding = await embed(embedding_text)
        upsert_with_stored_vector_hash(..., metadatas=[{
            "embedding_text_hash": hash(embedding_text),
        }])

    async def update_memory(self, mem_id: str, new_content: str, ...):
        await db.update_memory_content(mem_id, new_content, ...)
        await db.rebuild_memory_fts(mem_id)
        await upsert_chroma_from_canonical_sqlite(mem_id)

    async def delete_memory(self, mem_id: str):
        await db.update_memory_status(mem_id, "retired")
        await remove_from_search_indexes(mem_id)
```

The database helper deletes and reinserts each FTS row during rebuild. Health
checks compare FTS5 and ChromaDB against SQLite because both are derived indexes.
Health checks also detect duplicate FTS rows because FTS5 itself does not enforce a
unique `memory_id`.

---

## 14h. Graph Traversal Retrieval Strategy

### Algorithm

When the query mentions known entities, the graph traversal strategy:

1. **Resolve entities**: Map query terms to canonical entity IDs (via entity_aliases)
2. **Find directly linked memories**: Query `memory_entities` for all memories linked to those entities
3. **Expand via co-entity**: For each found memory, find other entities linked to it,
   then find other memories linked to those entities (1-hop expansion)
4. **Score**: Memories directly linked to query entities score higher than co-entity expansions

```python
async def graph_retrieval(self, entity_ids: list[int], top_k: int) -> list[ScoredMemory]:
    # Direct links: memories that reference the query entities
    direct = await self.db.execute("""
        SELECT m.*, COUNT(me.entity_id) as entity_overlap
        FROM memories m
        JOIN memory_entities me ON m.id = me.memory_id
        WHERE me.entity_id IN ({placeholders}) AND m.status = 'active'
        GROUP BY m.id
        ORDER BY entity_overlap DESC
        LIMIT ?
    """, (*entity_ids, top_k * 2))

    # 1-hop expansion: memories sharing entities with direct results
    direct_ids = [r["id"] for r in direct]
    expanded = await self.db.execute("""
        SELECT m.*, COUNT(DISTINCT me2.entity_id) as shared_entities
        FROM memory_entities me1
        JOIN memory_entities me2 ON me1.entity_id = me2.entity_id
        JOIN memories m ON me2.memory_id = m.id
        WHERE me1.memory_id IN ({placeholders})
          AND m.id NOT IN ({placeholders})
          AND m.status = 'active'
        GROUP BY m.id
        HAVING shared_entities >= 2
        ORDER BY shared_entities DESC
        LIMIT ?
    """, (*direct_ids, *direct_ids, top_k))

    # Score: direct links get 1.0 * overlap, expanded get 0.5 * shared
    results = []
    for r in direct:
        results.append(ScoredMemory(r, score=r["entity_overlap"] / len(entity_ids)))
    for r in expanded:
        results.append(ScoredMemory(r, score=0.5 * r["shared_entities"] / len(entity_ids)))

    return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
```

> **Note:** Graph traversal uses only `memory_entities` (entity co-occurrence). A
> `memory_relations` table (for `supports`, `elaborates`, etc.) is deferred to Phase 5.
> The `superseded_by` field on the memory itself handles supersession without needing a
> separate relations table.

---

## 14i. Concurrent Sync & Race Conditions

### SQLite Write Serialization

SQLite with WAL mode supports concurrent reads but serializes writes.
The application uses an `asyncio.Lock` to prevent concurrent write transactions:

```python
class Database:
    def __init__(self):
        self._write_lock = asyncio.Lock()

    async def insert_memory(self, mem):
        async with self._write_lock:
            # All write operations serialized
            await self._db.execute("INSERT INTO memories ...", ...)
            await self._db.execute("INSERT INTO memories_fts ...", ...)
            await self._db.commit()
```

### ChromaDB Concurrent Access

ChromaDB PersistentClient uses its own internal locking. Concurrent upserts from
different genes are safe. However, the dedup check (query + conditional insert) is NOT
atomic. Mitigation: the dedup threshold (0.08) is conservative enough that near-miss
duplicates are acceptable — they'll be caught and merged on the next sync cycle.

### Partial Sync Visibility

During a large sync, memories are committed individually (not batched in a transaction).
This means search queries during sync see a gradually growing result set.
This is acceptable — partial results are better than blocking search for hours during backfill.

---

## 15. Admin UI Design

The current admin UI lives in `admin-ui/`. It uses React, Vite, Tailwind CSS, shadcn/ui-style primitives, TanStack Query, and lucide icons. The design goal is a quiet operational console: dense enough for repeat use, readable in long review sessions, and consistent with the service ownership model.

Current route summary:

```text
/memories               -> memory list
/memories/:id           -> memory detail
/review                 -> review queue
/review/:id             -> review detail
/entities               -> entity list
/entities/:id           -> entity detail
/sources                -> source list, configuration, and sync controls
/settings               -> LLM endpoint testing and model configuration
```

The UI is intentionally a client of the Admin API. It does not run extraction logic, mutate vector state directly, or own source lifecycle behavior. Those operations stay behind the service API so CLI, UI, scheduled sync, and future hosted deployments share the same runtime path.

Public implementation references:

- `admin-ui/src/App.tsx` for routes
- `admin-ui/src/components/layout/Sidebar.tsx` for navigation
- `admin-ui/src/api/client.ts` for API calls
- `admin-ui/src/views/sources/SourcesPage.tsx` for source configuration and sync controls

| Surface | Purpose | Primary API ownership |
| --- | --- | --- |
| Memories | Browse active memories and inspect provenance | `GET /api/memories`, `GET /api/memories/{id}` |
| Review | Resolve incumbent/challenger memory decisions | review endpoints |
| Entities | Inspect resolved entities and aliases | entity endpoints |
| Sources | Configure genes and start sync jobs | source endpoints |
| Settings | Test endpoints, fetch model IDs, and configure runtime LLM settings | `GET/PUT /api/llm-config`, `POST /api/llm-config/probe` |

## 16. Open Questions & Future Work

### Open Questions

1. **Retrieval quality baseline**: How do we measure if memory search is actually better than
   document search? Need A/B framework or at minimum a manual evaluation set.
2. **Memory compaction**: At scale, should closely related memories from the same source
   be merged to reduce count?
3. **Real-time sync**: Current design is poll-based. Should we add webhook support for
   Confluence/Jira change events?
4. **Multi-tenancy**: If multiple teams use separate instances, does the architecture change?

### Future Work

- **Graph database migration**: If memory count exceeds 50K and multi-hop traversal
  becomes a bottleneck, evaluate Neo4j/Kuzu as a replacement for SQLite graph queries.
- **Cross-encoder reranking**: Stubbed in search.py, config-gated. Uses Claude Haiku to
  rerank top-30 RRF candidates. Solves graph-only discovery ranking. Enable at ~1K memories.
- **Memory quality dashboard**: Surface extraction errors, stale memories, contradiction
  rates, retrieval-to-use ratios.
- **Agent feedback loop**: When an agent fetches Level 1 detail but doesn't use the memory,
  record as implicit negative signal for ranking tuning.
- **Webhook-based sync**: Real-time push from Confluence/Jira via webhooks.
- **GitHub/GitLab gene**: Code-aware memory extraction from PRs, issues, README changes.
- **Slack gene**: Similar to Teams gene with thread-based content units.
