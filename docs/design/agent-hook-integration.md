# Agent Hook Integration

Status: current summary, detailed flow moved to
`docs/design/agent-session-saas-plugin-flow.md`

Agent hooks have three narrow responsibilities:

1. Inject memory context through `POST /api/hooks/context` on read-path hooks
   such as `UserPromptSubmit`.
2. Record lightweight lifecycle receipts through `POST /api/hooks/receipts` when
   needed for audit. Receipts do not create source material.
3. Request agent-session capture by updating the plugin's local queue. The
   run-once worker uploads bounded, redacted windows to
   `POST /api/agent-sessions/windows`.

Hooks must return quickly, must not run memory extraction, and must not write
canonical memories directly.

Default automatic capture:

```text
native hook payload
  -> adapter parses identity and normalized capture policy
  -> local session_cursor bookmark/pending state
  -> run-once worker slices live event source
  -> /api/agent-sessions/windows
  -> MemForge-generated package
  -> service-owned source sync
```

Compatibility path:

```text
MCP submit_agent_session_document
POST /api/agent-sessions/documents
```

Use the compatibility path only for explicit, already-generated summaries.
Automatic hook capture should use window uploads.
