# Agent Hook Integration

Status: current summary. The durable-memory write path is documented in
`docs/design/agent-knowledge-bundle.md`; the client SaaS/plugin packaging flow
is documented in `docs/design/agent-session-saas-plugin-flow.md`.

Agent hooks have two narrow responsibilities:

1. Record lightweight lifecycle receipts through `POST /api/hooks/receipts` when
   needed for audit. Receipts do not create source material.
2. Request agent-session capture by updating the plugin's local queue. The
   run-once worker uploads bounded, redacted windows to
   `POST /api/agent-sessions/windows`.

Per-prompt memory retrieval is delegated to the MCP `search` tool, which the
agent calls on demand with a query-aware prompt. MCP is the read/consumption
path, not the automatic ingestion trigger. The plugin no longer ships a
`UserPromptSubmit` hook; `POST /api/hooks/context` remains in the API surface
for future read-path integrations.

Hooks must return quickly, must not run memory extraction, and must not write
canonical memories directly.

Default automatic capture:

```text
native hook payload
  -> adapter parses identity and normalized capture policy
  -> local session_cursor bookmark/pending state
  -> run-once worker slices live event source
  -> /api/agent-sessions/windows
  -> server-side Agent Knowledge Bundle patch
  -> private concept/claim/citation + searchable memory row
```

The local adapter is a low-authority evidence uploader. It can normalize native
client events, attach repository metadata, and retry upload windows, but it must
not decide durable memory semantics. MemForge owns concept placement, claim
updates, privacy scope, idempotency, and search-surface reconciliation.

Compatibility path:

```text
MCP submit_agent_session_document
POST /api/agent-sessions/documents
```

Use the compatibility path only for explicit, already-generated summaries.
Automatic hook capture should use window uploads.

## Decision Boundary

The intended split is:

- hooks/local adapter: deterministic capture and delivery;
- `/api/agent-sessions/windows`: authenticated evidence intake;
- Agent Knowledge Bundle service: structured patch proposal, validation, and
  DB-authoritative write;
- MCP/search: retrieval and agent consumption after memory exists.

This is why automatic sync should not be replaced by an MCP-only `save memory`
tool. MCP calls depend on the agent choosing to call a tool, while lifecycle
hooks are the reliable capture trigger when session context is about to move or
be compacted.
