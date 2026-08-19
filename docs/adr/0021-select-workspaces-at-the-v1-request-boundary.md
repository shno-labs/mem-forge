# Select workspaces at the v1 request boundary

Status: Accepted (2026-08-06; amended 2026-08-10)

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
parameter. The MCP server exposes `list_workspaces`; every data-plane MCP tool
has the same optional `workspace_id` input. A user-confirmed local binding may
turn exact host context into that explicit request selector. The local path is
never sent to the service and does not grant authority.

Interactive data-plane requests resolve exactly one Authorized Workspace
Context in this order:

1. a requested `workspace_id`, after access and active-routing validation;
2. the caller's only accessible active workspace.

The server stores no default workspace preference. Automatic hook and
agent-session clients resolve a project binding, pinned session selection, or
client-local hook fallback and send that workspace as an explicit request
selector. When the client cannot resolve one, the same server selection rules
apply and the hook remains fail-open rather than risking capture in another
workspace.

If none is available, the server returns the same non-enumerating 404 used for
an inaccessible explicit selector. If multiple candidates remain, it returns
`workspace_selection_required` with the caller's accessible candidate IDs.
The response identifies the effective workspace through
`MemForge-Workspace`.

`GET /api/v1/workspaces` is principal-scoped discovery and does not itself
require a workspace. It reports accessible and selectable workspaces without a
server-side default. There is no default-workspace mutation route or MCP tool.

Installable agent clients read optional user intent from
`~/.memforge/workspace-bindings.json`. Bindings are scoped by canonical
MemForge origin. A normalized Git `origin` may map through
`repository_bindings`; an absolute ordinary directory may map through
`directory_bindings`, whose most-specific ancestor wins. A directory binding
is more specific than a repository binding. `hook_workspace_id` is considered
only by hooks. Missing configuration means no local selection; malformed,
ambiguous, or conflicting configuration fails closed.

The `memforge-setup` skill owns guided inspection and mutation of that file.
It discovers currently accessible workspaces, previews the exact mutation,
requires confirmation, writes atomically without credentials, and reuses the
same local resolver as MCP and hooks. An explicit MCP `workspace_id` overrides
a local binding for only that call and never mutates configuration.

Hook capture pins the resolved workspace with the local session cursor before
asynchronous upload. Later configuration changes cannot split one admitted
session across workspaces. Hooks remain fail-open for the coding client and
retain bounded retry state when no selection is available.

Self-hosted OSS implements the same contract as a singleton directory. Its
stable readable workspace ID is `local`, its role is `owner`, and it is always
selected when the request omits `workspace_id`. Explicit values other than
`local` fail with the same workspace 404 contract.

The self-hosted request principal and source-management resolver use that same
`owner` role. They do not translate it to the Cloud-only `workspace_admin`
membership role. Shared modules consume resolved management capabilities;
Cloud remains responsible for mapping Workspace Membership Roles into those
capabilities when it constructs the OSS application.

After resolution, the selected workspace is immutable for that request. Any
durable job or run admitted by the request persists the effective workspace
ID; workers use the persisted value rather than resolving defaults again.

## Consequences

Cloud and self-hosted clients share one URL and tool schema. Single-workspace
users can omit `workspace_id`; multi-workspace interactive calls require an
explicit selector, either supplied by the tool call or resolved from a
user-confirmed local binding. Calling `list_workspaces` first remains optional
after configuration.

Automatic hooks may use a repository binding, directory binding, pinned
session selection, or local hook fallback. None of those selections silently
scopes an interactive search.

The old path-shaped Cloud surface, unversioned OSS data plane,
`MEMFORGE_WORKSPACE_ID`, and repository `.memforge/config.toml` workspace
overrides remain removed rather than retained as compatibility branches.

Workspace authorization, selection, store binding, and selection diagnostics
belong to one server module. Route handlers consume only the already authorized
request context; workspace preferences do not belong to a storage adapter
contract.

## References

- [ADR 0018](0018-settle-mcp-roots-before-workspace-routed-tool-calls.md)
- [MCP 2026-07-28 Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
