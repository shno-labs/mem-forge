# MemForge Local Agent Daemon V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local MemForge daemon that can run local-folder/GitHub local-push syncs and keep Jira browser sessions fresh through one extensible runtime.

**Architecture:** The daemon lives in the OSS CLI package and reuses the existing adapter profiles, ToolClient transport, GitHub/local folder push helpers, and Jira watch tick. V1 is local-first: it does not add cloud job relay endpoints yet, but it creates adapter/job/state seams that can later poll cloud jobs. Jira V1 only refreshes browser sessions; it does not fetch Jira issues locally.

**Tech Stack:** Python Click CLI, existing `ToolClient`, existing adapter profile TOML, SQLite-backed JSON state file, pytest, no new runtime dependency.

## Global Constraints

- Do not add a second source-ingestion protocol. GitHub and local folder daemon jobs must call the same push paths as `adapter github push` and `adapter kb push`.
- Do not implement Jira full local fetch in V1. Jira daemon support is browser-session refresh only.
- Keep the daemon extensible through source-specific task functions, not hard-coded command strings.
- Daemon loops must survive one profile failure and continue processing other profiles.
- The daemon must be observable through a status command that reports last run, counts, and last error per task.
- Do not require inbound network access to the user's machine.

---

## File Structure

- Create `src/memforge/local_agent/__init__.py`: package marker.
- Create `src/memforge/local_agent/state.py`: JSON state load/save with atomic writes.
- Create `src/memforge/local_agent/tasks.py`: reusable task functions for KB sync, GitHub sync, and Jira browser-session refresh.
- Create `src/memforge/local_agent/runner.py`: daemon loop, once mode, schedule interval checks, per-task error isolation.
- Modify `src/memforge/main.py`: expose `memforge adapter daemon {run,once,status}` and add thin reusable wrappers around existing push logic.
- Test `tests/test_local_agent_daemon.py`: pure tests for task discovery, failure isolation, state, and CLI status.

### Task 1: State Store

**Files:**
- Create: `src/memforge/local_agent/__init__.py`
- Create: `src/memforge/local_agent/state.py`
- Test: `tests/test_local_agent_daemon.py`

**Interfaces:**
- Produces: `LocalAgentStateStore(path: Path)`, `.load() -> dict`, `.record_result(task_id: str, result: dict) -> dict`.

- [x] **Step 1: Write failing tests for atomic state persistence**
- [x] **Step 2: Run `uv run pytest tests/test_local_agent_daemon.py -q` and verify failure**
- [x] **Step 3: Implement state store with temp-file replace and mode `0600`**
- [x] **Step 4: Re-run the test and verify pass**

### Task 2: Task Discovery

**Files:**
- Create: `src/memforge/local_agent/tasks.py`
- Modify: `src/memforge/main.py`
- Test: `tests/test_local_agent_daemon.py`

**Interfaces:**
- Produces: `LocalAgentTask(task_id, kind, profile_name, interval_seconds, run_once)`.
- Produces: `discover_local_agent_tasks(adapter_config: dict) -> list[LocalAgentTask]`.

- [x] **Step 1: Write failing tests that KB/GitHub linked profiles become sync tasks and Jira watch config becomes auth task**
- [x] **Step 2: Run targeted tests and verify failure**
- [x] **Step 3: Implement discovery over existing adapter config**
- [x] **Step 4: Re-run tests**

### Task 3: Reusable Task Executors

**Files:**
- Modify: `src/memforge/local_agent/tasks.py`
- Modify: `src/memforge/main.py`
- Test: `tests/test_local_agent_daemon.py`

**Interfaces:**
- Produces: `run_local_agent_task(task, adapter_config, ctx_obj, now) -> dict`.
- Consumes existing `_preview_kb_profile`, `_preview_github_profile`, `ToolClient.push_*`, and `run_watch_tick`.

- [x] **Step 1: Write failing tests with fake push/auth functions**
- [x] **Step 2: Run targeted tests and verify failure**
- [x] **Step 3: Extract reusable KB/GitHub push helpers from CLI command bodies without changing CLI behavior**
- [x] **Step 4: Implement task executor using the reusable helpers**
- [x] **Step 5: Re-run CLI and daemon tests**

### Task 4: Daemon Runner and CLI

**Files:**
- Create: `src/memforge/local_agent/runner.py`
- Modify: `src/memforge/main.py`
- Test: `tests/test_local_agent_daemon.py`
- Test: `tests/test_cli_interactive.py` if menu shape changes.

**Interfaces:**
- Produces: `run_local_agent_once(...) -> dict`.
- Produces CLI commands:
  - `memforge adapter daemon once`
  - `memforge adapter daemon run --interval-seconds N`
  - `memforge adapter daemon status`

- [x] **Step 1: Write failing tests for once-mode failure isolation and status output**
- [x] **Step 2: Run targeted tests and verify failure**
- [x] **Step 3: Implement runner and CLI commands**
- [x] **Step 4: Re-run targeted tests**

### Task 5: Verification and Review

**Files:**
- Existing tests only unless review finds a real gap.

- [x] **Step 1: Run `uv run pytest tests/test_local_agent_daemon.py tests/test_cli_interactive.py tests/test_cli_agent_tools.py -q`**
- [x] **Step 2: Run `uv run ruff check src/memforge/local_agent src/memforge/main.py tests/test_local_agent_daemon.py`**
- [x] **Step 3: Run one manual smoke command: `uv run memforge adapter daemon status`**
- [x] **Step 4: Request reviewer feedback and fix accepted findings**

## V1 Follow-Ups

- Support only one local daemon writer per state file in V1. Add a PID file or advisory lock before recommending launchd/systemd-style supervised deployment.
- Add SIGTERM-aware graceful shutdown when supervised deployment is supported.
- Add a compact status view if the task map grows beyond the current per-task state summary.
