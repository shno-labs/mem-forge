# Local Agent Source Types Design

> Superseded by `docs/local-repo-sync.md` and the durable source-sync worker
> design. Local sources are configured in the UI, the daemon uploads raw data
> for server-issued jobs, and the server owns processing and schedules.

## Goal

Extend the local-agent Cloud job model beyond GitHub repository sync to cover two local-side source classes:

- `local_markdown`: Cloud cannot read a user's local folders, so preview and sync must run on the local daemon.
- `jira`: Cloud may not be able to reach internal Jira over VPN, so Jira content sync needs an optional local-daemon execution path in addition to the existing browser-session refresh daemon.

This design depends on the Cloud local-agent queue from Cloud PR #137 and the OSS daemon/GitHub local job flow from OSS PR #102.

## External Design References

- GitHub self-hosted runners use a runner-pulls-jobs model: jobs remain queued until a matching runner is online, and assigned jobs are re-queued if the runner does not pick them up promptly. This supports our no-inbound-network daemon design.
- Atlassian Jira REST search supports JQL-based issue search and pagination. The local daemon can reuse the existing Jira source config and JiraGene fetch/normalize behavior from the user's VPN/browser-capable environment.
- Local file connectors in ETL systems are commonly workstation/self-managed concerns. Local filesystem reads should happen in the local daemon, not in the SaaS Cloud container.

## Architecture

The Cloud job queue remains the generic control plane:

```text
Cloud UI/config -> POST /api/cloud/local-agent/jobs
local daemon -> lease job -> run source handler locally -> push package/documents to Cloud
local daemon -> complete job with result/error
Cloud UI -> poll job status
```

The daemon gets a small operation registry so source support is not implemented as an ever-growing `if operation == ...` chain. Each operation declares:

- accepted operation name;
- required payload fields;
- whether `source_id` is required;
- execution function;
- result shape.

Cloud keeps an explicit operation allowlist. New operations are only advertised after the daemon implements them.

## Operations

### Local Markdown

Add:

- `local_markdown_preview_tree`
- `local_markdown_sync`

Payload:

```json
{
  "root": "/Users/me/notes",
  "vault_id": "engineering-notes",
  "include": ["**/*.md", "**/*.txt", "**/*.json", "**/*.html"],
  "exclude": [".git/**", ".obsidian/**", ".trash/**"],
  "limit": 200,
  "process_now": true
}
```

Preview reuses existing `_preview_kb_profile`. Sync reuses existing `_push_kb_profile_payload` behavior, but from a Cloud job snapshot instead of a saved local CLI profile. Sync requires `source_id` and `workspace_id`, and it pushes through the workspace-scoped ToolClient so Cloud stores data in the source selected in the UI.

### Jira Local Content Sync

Add:

- `jira_sync`

Payload:

```json
{
  "base_url": "https://jira.example.corp",
  "auth_mode": "browser_cookie",
  "query_mode": "advanced",
  "jql": "project = PAY ORDER BY updated DESC",
  "projects": ["PAY"],
  "issue_types": ["Epic", "Story", "Bug", "Task"],
  "include_comments": true,
  "limit": 25,
  "process_now": true
}
```

Jira local content sync is not the same thing as the existing Jira auth refresh daemon:

- `jira_auth` task: captures and uploads browser session state so Cloud-side Jira sync can work when Cloud can reach Jira.
- `jira_sync` job: runs Jira issue discovery/fetch/normalize locally and pushes the resulting issue packages to Cloud when Cloud cannot reach Jira.

For `jira_sync`, the daemon instantiates the existing `JiraGene` locally from the job payload, authenticates from the local environment/session, fetches issues, normalizes them, then pushes each issue to Cloud through a Jira adapter document intake. Cloud must not re-fetch Jira after receiving a daemon-pushed issue; it should process a pushed Jira package from the source inbox.

In v1, Jira local content sync is browser-session only. PAT mode remains valid for Cloud-reachable Jira, but PAT secrets must not be passed through local-agent job payloads. The daemon must drop service-only inbox fields such as `local_agent_documents_dir` from the leased payload and run JiraGene in REST-fetch mode against the local browser/VPN environment.

Server intake adds Jira as a local adapter source type:

- validate the target source is `jira`;
- validate `base_url` and issue key/source URL match the saved source config;
- write a `jira_document` package to the same per-source local adapter inbox;
- refresh source config with `local_agent_documents_dir`;
- leave source processing to the daemon's batch-level sync trigger.

JiraGene learns an inbox mode:

- if `sync_mode=local_agent` and `local_agent_documents_dir` is set, discover/fetch local Jira packages from that inbox;
- otherwise keep the current REST API behavior.

This preserves the existing server-side Jira path for normal Cloud-reachable Jira sources while enabling local-daemon content sync for VPN-only Jira.

## UI Behavior

`local_markdown`:

- Creation/edit remains UI-owned.
- Preview button enqueues `local_markdown_preview_tree` instead of telling the user to run a CLI scan.
- Sync now enqueues `local_markdown_sync` and polls until the daemon completes.
- Sources must have a configured folder `root`. Pre-daemon local markdown rows without `root` should fail clearly and be edited in the UI; the old CLI-only setup panel and fallback sync path are intentionally removed.

`jira`:

- Existing browser-session refresh UI remains for auth state.
- Add a source config option for local content sync only when needed. In v1, the source action can enqueue `jira_sync` when config says the source uses local daemon sync.
- Hide server-side discovery preview when the source is configured for local daemon sync; no Jira local-agent preview operation exists in v1.
- Do not remove the server-side Jira sync path.

## Error Handling

- Preview jobs may omit `source_id`.
- Sync jobs require `source_id` and `workspace_id`.
- Local filesystem errors, invalid Jira auth/session, JQL errors, unsupported content, or adapter push failures complete the job as `failed` with a concise `last_error`.
- Partial push failures complete the job as `failed` with per-item failures in the result.
- If at least one Jira issue package is pushed successfully, the daemon starts source processing once through the source sync API after the push loop. It must not rely on re-pushing an issue with `process_now=true` as a processing side effect.
- The daemon continues later jobs after one job fails.

## Testing

Unit and integration coverage:

- Cloud route accepts the three new operations and still rejects unknown operations.
- Cloud route requires `source_id` for sync operations.
- Daemon operation registry dispatches GitHub, local markdown, and Jira operations.
- Local markdown preview/sync uses job payload, not a local profile.
- Jira sync uses job payload, local JiraGene behavior, workspace-scoped ToolClient, and adapter intake.
- JiraGene local inbox mode processes pushed Jira packages without making Jira REST calls.
- UI tests verify local markdown preview/sync and Jira local-sync enqueue/poll.

Live smoke:

- Deploy dependent Cloud branch to CF dev.
- Run local daemon against real Cloud.
- Smoke `local_markdown_preview_tree` and `local_markdown_sync` using a small temp local folder.
- Smoke Jira local sync with either a real reachable Jira source or a controlled failure path if no safe real Jira source is available.
