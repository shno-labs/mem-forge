# Select workspaces at the v1 request boundary

Status: Accepted (2026-08-06)

## Context

MemForge previously exposed different data-plane targets: self-hosted used
`/api/...`, while Cloud embedded the workspace in
`/api/workspaces/{workspace_id}/api/...`. Coding-agent clients selected Cloud
workspaces through process, user, or repository configuration. That made
correct routing depend on how each host loaded environment and repository
state, and it coupled repository attribution to tenancy.

Most callers have one accessible workspace and should not have to discover or
send an identifier. Multi-workspace callers need a deliberate way to query a
different workspace with the same API key. A directory call is useful for
discovery, but cannot be a prerequisite for every session or tool call.

## Decision

OSS and Cloud expose one breaking v1 data plane at `/api/v1/...`. Every
workspace-scoped HTTP operation accepts an optional `workspace_id` query
parameter. The MCP server exposes `list_workspaces` and
`set_default_workspace`; every data-plane MCP tool has the same optional
`workspace_id` input. Repository Context is provenance and retrieval
attribution only. It never selects a workspace.

The server resolves exactly one Authorized Workspace Context for each data-
plane request in this order:

1. a requested `workspace_id`, after access and active-routing validation;
2. the caller's valid Default Workspace preference;
3. the caller's only accessible active workspace.

If none is available, the server returns the same non-enumerating 404 used for
an inaccessible explicit selector. If multiple candidates remain, it returns
`workspace_selection_required` with the caller's accessible candidate IDs.
The response identifies the effective workspace through
`MemForge-Workspace`.

`GET /api/v1/workspaces` is principal-scoped discovery and does not itself
require a workspace. `PUT /api/v1/me/default-workspace` stores an optional
user preference only after current access validation. Revoking membership or
retiring routing makes that preference ineffective; membership revocation
also clears a matching preference.

The MCP `set_default_workspace` tool is an explicit control-plane operation.
Its description requires user confirmation, and its only input is the selected
workspace ID. Calling another tool with `workspace_id` is a one-request
override and never changes the default. A workspace-selection conflict in an
automatic hook reports an actionable instruction to discover and confirm a
default; hooks do not open an interactive MCP flow or maintain hidden session
selection state.

Self-hosted OSS implements the same contract as a singleton directory. Its
stable readable workspace ID is `local`, its role is `owner`, and it is always
the default. Explicit values other than `local` fail with the same workspace
404 contract.

After resolution, the selected workspace is immutable for that request. Any
durable job or run admitted by the request persists the effective workspace
ID; workers use the persisted value rather than resolving defaults again.

## Consequences

Cloud and self-hosted clients share one URL and tool schema. Single-workspace
users can omit `workspace_id`; multi-workspace users may set a default or pass
an explicit selector without changing agent environment or repository files.
Calling `list_workspaces` first remains optional.

Automatic hooks and omitted data-plane selectors converge on the same
server-side Default Workspace. Existing bounded hook retries may succeed after
the preference is set; the hook transport does not invent a separate queue,
workspace cache, or agent-environment override.

The old path-shaped Cloud surface, unversioned OSS data plane,
`MEMFORGE_WORKSPACE_ID`, repository `.memforge/config.toml` workspace
overrides, and the workspace setup skill are removed rather than retained as
compatibility branches.

Workspace authorization, selection, store binding, and selection diagnostics
belong to one server module. Adapters implement the same directory/default
persistence contract, while route handlers consume only the already authorized
request context.

## References

- [ADR 0018](0018-settle-mcp-roots-before-workspace-routed-tool-calls.md)
- [MCP 2026-07-28 Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
