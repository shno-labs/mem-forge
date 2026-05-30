# Agent Client Integrations

MemInception supports Codex, Claude Code, and similar tools through thin client
adapters. The adapter boundary is deliberately small so different agent session
formats can be normalized without moving memory decisions into the client.

## Client-Side Responsibilities

The agent-client package owns:

- reading the hook payload supplied by the host tool
- requesting memory context from the service before the user prompt is handled
- keeping a local retry queue for failed lifecycle uploads
- translating native transcript rows into a bounded canonical evidence window
- redacting obvious client-visible secrets before upload
- uploading the window to `POST /api/agent-sessions/windows`

The client does not extract canonical memories, write memory rows, run source
sync, or read transcript files that belong to another tool.

## Service-Side Responsibilities

The MemInception service owns:

- validating the window schema and client metadata
- redacting again because client-side redaction is not a trust boundary
- canonicalizing evidence into a durable agent-session package
- deciding whether a gated turn contains enough signal to process
- queuing and running the `agent_session` source sync
- applying quality gates, reconciliation, review, storage, search, and lifecycle
  policies

This is the same boundary for local self-hosting and a future hosted service.
Only `MEMINCEPTION_API_URL` and authentication change.

## Window Shape

```json
{
  "schema_version": "agent-session-window/v1",
  "client": "codex",
  "session_id": "session-123",
  "workspace": "/workspace/mem-inception",
  "repo": "DoDoMan-TTT/mem-inception",
  "branch": "main",
  "trigger": "GATED_CAPTURE",
  "window": {
    "from": "line:120",
    "to": "line:180",
    "events": [
      {
        "role": "user",
        "kind": "message",
        "text": "Add tests for the adapter."
      },
      {
        "role": "assistant",
        "kind": "tool_call",
        "text": "uv run pytest tests/test_hook_adapter.py -q"
      }
    ]
  },
  "redaction": {
    "applied": true,
    "patterns": ["bearer", "json", "generic"]
  },
  "process_now": false
}
```

Automatic hook uploads use `process_now=false` so the API can acknowledge the
window quickly and let the service-owned queue process it. Explicit MCP
submissions can still use immediate processing when the caller already has a
small generated summary.

## Capture Triggers

`REQUIRED_CAPTURE` is used when context is about to be lost, such as compaction.
`GATED_CAPTURE` is used at ordinary turn boundaries and only captures when the
window contains durable work signals. `RECOVER` is used on resume to re-arm any
uncaptured tail.

These names describe capture policy rather than host-specific hook names. Codex,
Claude Code, and future clients can map their own hook events into the same
small vocabulary.
