# Agent Session Curator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the V1 repo-first agent-session Curator foundation: canonical repo identity, lineage schema/contracts, lineage-aware search metadata, and a non-destructive agent-session Curator runner for Codex and Claude Code memories.

**Architecture:** OSS owns canonical behavior: models, SQLite schema, storage-neutral protocol, Curator policy/runner, and search result shaping. Cloud implements the same storage contract in HANA; it does not fork API behavior. Session memories are grouped primarily by `repo_identifier`; `project_key` remains optional relevance metadata.

**Tech Stack:** Python, async SQLite via existing `Database`, storage adapter protocols, pytest/pytest-asyncio, existing MemForge search pipeline.

---

## File Structure

- Modify `src/memforge/models.py`: add memory level and curation dataclasses, extend `Memory` and `SearchResult` with optional curation fields.
- Modify `src/memforge/storage/database.py`: add SQLite schema/migrations for memory curation columns/tables and methods to persist/read lineage/runs.
- Modify `src/memforge/storage/adapters/protocols.py`: add curation protocol methods and ranking metadata fields.
- Modify `src/memforge/storage/adapters/sqlite/relational.py`: implement curation protocol and richer ranking metadata.
- Modify `src/memforge/storage/adapters/context.py`: add optional `active_repo_identifier` relevance context.
- Modify `src/memforge/retrieval/search.py`: add repo affinity to ranking metadata and lineage-aware result shaping.
- Modify `src/memforge/agent_sessions.py`: add repo identifier normalization and include `repo_identifier` in receipt metadata/package source semantics.
- Modify `src/memforge/genes/agent_session_gene.py`: normalize/pass through `repo_identifier`.
- Create `src/memforge/memory/curator.py`: source-type policy interfaces, agent-session policy, and non-destructive runner.
- Add tests:
  - `tests/test_agent_session_repo_identifier.py`
  - `tests/test_memory_curation_storage.py`
  - `tests/test_search_curation_lineage.py`
  - `tests/test_agent_session_curator.py`
- Cloud HANA contract coverage:
  - `packages/adapters/store/hana/src/memforge_cloud/adapters/store/hana/workspace.py`
  - `tests/unit/test_hana_workspace_store.py`

## Task 1: Canonical repo identity for agent sessions

**Files:**
- Modify: `src/memforge/agent_sessions.py`
- Modify: `src/memforge/genes/agent_session_gene.py`
- Test: `tests/test_agent_session_repo_identifier.py`

- [x] Step 1: Write failing tests for repo identifier normalization and package metadata.
- [x] Step 2: Run `uv run pytest tests/test_agent_session_repo_identifier.py -q`; expect failure because helpers/fields do not exist.
- [x] Step 3: Implement `normalize_repo_identifier()` and store/pass `repo_identifier` through receipt metadata and `source_semantics`.
- [x] Step 4: Run the test file again; expect pass.

## Task 2: Storage schema and protocol for curated lineage

**Files:**
- Modify: `src/memforge/models.py`
- Modify: `src/memforge/storage/database.py`
- Modify: `src/memforge/storage/adapters/protocols.py`
- Modify: `src/memforge/storage/adapters/sqlite/relational.py`
- Test: `tests/test_memory_curation_storage.py`

- [x] Step 1: Write failing storage tests for `memory_level`, `curation_cluster_id`, `repo_identifier`, derivation insert/read, and curation-run audit.
- [x] Step 2: Run `uv run pytest tests/test_memory_curation_storage.py -q`; expect schema/method failures.
- [x] Step 3: Add dataclasses, schema columns/tables, migrations, database methods, and SQLite relational protocol methods.
- [x] Step 4: Run storage tests; expect pass.

## Task 3: Repo-aware and lineage-aware search metadata

**Files:**
- Modify: `src/memforge/storage/adapters/context.py`
- Modify: `src/memforge/storage/adapters/protocols.py`
- Modify: `src/memforge/storage/adapters/sqlite/relational.py`
- Modify: `src/memforge/retrieval/search.py`
- Test: `tests/test_search_curation_lineage.py`

- [x] Step 1: Write failing search tests: same-repo candidate gets a small boost, consolidated+child results collapse by default, exact child can survive when it strongly outranks consolidated.
- [x] Step 2: Run `uv run pytest tests/test_search_curation_lineage.py -q`; expect failure.
- [x] Step 3: Add `active_repo_identifier`, richer ranking metadata, repo affinity, and result-family collapse.
- [x] Step 4: Run search curation tests; expect pass.

## Task 4: Non-destructive agent-session Curator V1

**Files:**
- Create: `src/memforge/memory/curator.py`
- Modify: `src/memforge/storage/adapters/protocols.py` if candidate reader needs a protocol hook
- Modify: `src/memforge/storage/adapters/sqlite/relational.py` if candidate reader lives in the adapter
- Test: `tests/test_agent_session_curator.py`

- [x] Step 1: Write failing Curator tests: only Codex/Claude Code agent-session memories are eligible, clusters are repo-first, private owners do not merge, and generated consolidated memories preserve lineage.
- [x] Step 2: Run `uv run pytest tests/test_agent_session_curator.py -q`; expect failure.
- [x] Step 3: Implement `MemoryCuratorPolicy`, `AgentSessionCuratorPolicy`, and `MemoryCuratorRunner` with a deterministic summarizer callback for tests.
- [x] Step 4: Run Curator tests; expect pass.

## Task 5: Focused regression and cleanup

**Files:**
- Relevant changed files above.

- [ ] Step 1: Run targeted existing tests around agent sessions, project resolver, project-first ranking, and storage adapters.
- [ ] Step 2: Run all new tests together.
- [ ] Step 3: Run `git diff --check`.
- [ ] Step 4: Review changed code for temporary bridges, source-type fallbacks, and cloud-only behavior.
- [ ] Step 5: Commit implementation with a clear message.

## Self-Review

- Spec coverage: V1 repo-first identity, curated searchable lineage, storage-neutral contracts, and non-destructive agent-session-only Curator are covered.
- Scope control: Jira/Confluence curation is intentionally deferred; Cloud HANA implements only the same storage-neutral contract.
- No placeholders: every task has concrete files and commands; code snippets are omitted here because implementation will be done directly with TDD against live files.
