# Local Agent Folder Picker Long Poll Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a UI-triggered local folder picker for `local_markdown` sources and make Cloud local-agent job delivery interactive through bounded long polling.

**Architecture:** Cloud keeps the local-agent job queue as the control plane. The daemon runs a dedicated Cloud-job long-poll loop separate from scheduled local sync checks, executes `local_markdown_pick_root` locally, and returns the selected absolute path to the UI. The UI remains Cloud-owned: it creates a job, polls its result, and writes the returned path into the source form.

**Tech Stack:** FastAPI/Pydantic service route, MemForge OSS Click daemon, existing ToolClient HTTP client, React admin UI, pytest, Vitest.

## Global Constraints

- Do not expose a localhost daemon HTTP server from the browser.
- Do not use browser directory handles as the daemon sync root; daemon sync needs a real local absolute path.
- Cloud long polling must be bounded (`wait_seconds` capped) and must not hold DB transactions while waiting.
- The daemon must issue only one Cloud-job lease request at a time.
- Keep scheduled source/profile checks separate from interactive Cloud job leasing.
- `local_markdown_pick_root` does not move file content; it returns a selected folder path only.
- Non-macOS folder picker support may return a clear unsupported-platform error in v1.

---

### Task 1: Cloud Bounded Long-Poll Lease

**Files:**
- Modify: `/Users/i551096/Dev/memforge-cloud/packages/cloud-service/src/memforge_cloud/cloud_service/routes/local_agent_jobs.py`
- Test: `/Users/i551096/Dev/memforge-cloud/tests/integration/test_local_agent_jobs_api.py`

**Interfaces:**
- Consumes: existing `LocalAgentJobLeaseRequest(limit, lease_seconds)`.
- Produces: `LocalAgentJobLeaseRequest.wait_seconds: int`, async `/jobs/lease`, and allowlisted `local_markdown_pick_root`.

- [ ] Add tests that `wait_seconds` is accepted, bounded, and a no-job lease returns empty after a short wait.
- [ ] Add tests that `local_markdown_pick_root` can be created without `source_id` for `local_markdown`.
- [ ] Implement `wait_seconds` with capped async waiting and per-iteration short DB lease attempts.
- [ ] Keep sync operations requiring `source_id`; `local_markdown_pick_root` must not be a sync operation.
- [ ] Run Cloud focused tests.

### Task 2: ToolClient Lease Parameters

**Files:**
- Modify: `/Users/i551096/Dev/mem-inception/src/memforge/tool_client.py`
- Test: `/Users/i551096/Dev/mem-inception/tests/test_tool_client_sources.py`

**Interfaces:**
- Consumes: existing `ToolClient.lease_local_agent_jobs`.
- Produces: `lease_local_agent_jobs(limit=5, lease_seconds=60, wait_seconds=0)` sending `wait_seconds` only when provided.

- [ ] Add test that `wait_seconds` is included in the lease payload.
- [ ] Implement optional `wait_seconds` parameter and ensure request timeout exceeds it.
- [ ] Run focused ToolClient tests.

### Task 3: Daemon Dedicated Cloud-Job Loop

**Files:**
- Modify: `/Users/i551096/Dev/mem-inception/src/memforge/local_agent/runner.py`
- Modify: `/Users/i551096/Dev/mem-inception/src/memforge/main.py`
- Test: `/Users/i551096/Dev/mem-inception/tests/test_local_agent_daemon.py`
- Test: `/Users/i551096/Dev/mem-inception/tests/test_cli_agent_tools.py`

**Interfaces:**
- Consumes: existing `LocalAgentRunner.run_forever` and `_lease_cloud_jobs`.
- Produces: a runner path that can long-poll Cloud jobs separately from scheduled due-task checks.

- [ ] Add runner test proving cloud job lease can run without waiting for scheduled source intervals.
- [ ] Add CLI option defaults for `--cloud-job-wait-seconds 25` and `--cloud-job-idle-jitter-seconds`.
- [ ] Implement a dedicated Cloud-job loop path that leases one job at a time with `wait_seconds`.
- [ ] Preserve `run_once` behavior for tests and one-shot commands.
- [ ] Run daemon focused tests.

### Task 4: Local Markdown Pick Root Operation

**Files:**
- Modify: `/Users/i551096/Dev/mem-inception/src/memforge/main.py`
- Create: `/Users/i551096/Dev/mem-inception/src/memforge/local_agent/folder_picker.py`
- Test: `/Users/i551096/Dev/mem-inception/tests/test_cli_agent_tools.py`

**Interfaces:**
- Produces: `pick_folder(title: str | None = None, initial_directory: str | None = None) -> str`.
- Produces: Cloud job handler operation `local_markdown_pick_root`.

- [ ] Add tests that `local_markdown_pick_root` returns `{"root": path}` when picker succeeds.
- [ ] Add tests that cancellation or unsupported platform returns a concise error.
- [ ] Implement macOS native picker via `osascript` or another dependency-free native path.
- [ ] Wire operation registry to call picker.
- [ ] Run focused handler tests.

### Task 5: Admin UI Choose Folder

**Files:**
- Modify: `/Users/i551096/Dev/mem-inception/admin-ui/src/views/sources/SourceConfigDialog.tsx`
- Test: `/Users/i551096/Dev/mem-inception/admin-ui/tests/local-markdown-config.test.ts`

**Interfaces:**
- Consumes: existing local-agent job create/status polling helpers.
- Produces: a `Choose folder` button beside the `root` field for `local_markdown`.

- [ ] Add UI test that clicking `Choose folder` creates `local_markdown_pick_root`, polls status, and writes `result.root` into the path field.
- [ ] Implement the button, loading state, success path, cancellation/error message.
- [ ] Do not show this control for non-local-markdown source types.
- [ ] Run admin UI focused tests.

### Task 6: Verification, Deploy, Smoke

**Files:**
- Modify: `/Users/i551096/.codex/tmp/local-agent-source-types-handoff.md`
- Modify: `/Users/i551096/Dev/memforge-cloud/requirements.txt` if OSS commit pin changes.

**Interfaces:**
- Produces: committed/pushed OSS and Cloud branches, deployed CF dev app, smoke evidence.

- [ ] Run OSS focused backend and admin UI tests.
- [ ] Run Cloud focused tests.
- [ ] Commit/push OSS changes, update Cloud pin, commit/push Cloud changes.
- [ ] Deploy Cloud to CF dev.
- [ ] Smoke `/healthz`.
- [ ] Smoke `local_markdown_pick_root` with a controlled picker path test when possible, and at least smoke `local_markdown_preview_tree` after path selection plumbing.
