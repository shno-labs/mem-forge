# Agent Session Documents

Status: compatibility note, superseded as the automatic hook-capture design

The previous automatic hook design asked agent clients to submit generated
markdown summaries directly to:

```http
POST /api/agent-sessions/documents
```

That is no longer the default hook flow. The current design is documented in
`docs/design/agent-session-saas-plugin-flow.md`.

Current default:

```text
plugin hook -> local queue -> bounded transcript window
            -> POST /api/agent-sessions/windows
            -> MemForge-generated package
            -> queued agent_session source sync
```

The document endpoint and MCP tool remain valid for explicit, already-generated
session summaries:

```text
MCP submit_agent_session_document
POST /api/agent-sessions/documents
```

Example request shape:

```json
{
  "client": "codex",
  "session_id": "0193-example",
  "trigger": "manual",
  "workspace": "/Users/me/project",
  "document_markdown": "## Durable Findings\n- The summary is already generated.",
  "process_now": false
}
```

Use this path only when the caller already has a real summary document to store
as low-authority generated source material. Automatic Codex and Claude Code hook
capture should upload windows instead, so MemForge owns the package-generation
prompt, receipt outcome, and source-sync scheduling.
