# Resolve request-scoped repository context before workspace-routed tool calls

Status: Superseded by ADR 0021 (2026-08-06)

ADR 0021 removes repository-derived workspace routing entirely. This record is
retained only as history for the request-scoped repository attribution barrier.

## Context

A repository-local `.memforge/config.toml` selects the Cloud workspace for
every HTTP-backed MCP tool. The shared target resolver gives a valid repository
override precedence over the process and user defaults, and MCP obtains the
repository roots from the optional client `roots/list` capability.

After MCP initialization enters the operation phase, the proxy may have sent a
`roots/list` request without receiving its response yet. JSON-RPC remains
full-duplex during that interval, so a client tool request can arrive before
the roots response. Treating the current empty root list as final routes that
request through the process or user fallback. A later request then uses the
repository workspace after roots resolve, allowing one MCP session to address
two workspaces unintentionally.

The original decision assumed that Roots should remain the sole repository
input for workspace routing and that per-tool Repository Context should remain
limited to attribution. Current Codex does not advertise the optional Roots
capability, however, while its MemForge calls can carry an exact working
directory. The result is internally inconsistent: a `search` call can be
attributed to one repository while the HTTP request still targets the global
workspace, and tools such as `list_sources` cannot express repository intent at
all.

This assumption also conflicts with the protocol direction adopted after the
original decision. MCP 2026-07-28 deprecates Roots and directs implementations
to migrate directory or file context to tool parameters, resource URIs, or
server configuration. Roots remain useful compatibility input, but cannot be a
required correctness dependency.

Codex `0.146.0` provides a more reliable request-local carrier than a model-
generated tool argument. An MCP server may advertise the experimental
`codex/sandbox-state-meta` server capability; Codex then attaches the owning
turn or execution environment's current working directory as `sandboxCwd` in
each `tools/call.params._meta`. The capability is negotiated once, but its cwd
value is computed for the individual call. It is therefore safe for one long-
lived proxy connection to serve tasks rooted in different repositories.

## Decision

Every HTTP-backed tool accepts the same optional
`repository_context.working_directory`. The proxy resolves one immutable call
context before validating or sending the operation. That context contains both
the effective Cloud target and the normalized repository identifier, so
workspace routing and attribution cannot diverge.

Target precedence is:

1. an exact explicit Repository Context supplied on the tool call;
2. an exact cwd supplied by a negotiated request-scoped host metadata adapter;
3. a settled, unambiguous compatible MCP Root when request context is absent;
4. the configured process or user workspace fallback.

An explicit context selects the repository root passed to the existing shared
workspace resolver. A valid repository-local `.memforge/config.toml` therefore
keeps its established precedence over process and user defaults. If the exact
repository has no override, the normal configured fallback applies; the proxy
does not borrow a different workspace from MCP Roots.

The Codex package advertises `codex/sandbox-state-meta` in the MCP initialize
response and consumes only its `sandboxCwd` field. Other sandbox fields do not
participate in MemForge authorization or routing. The adapter converts that cwd
into the same immutable Repository Context used by explicit tool input; it does
not add a Codex-specific branch to the service contract or forward the local
path. Other clients continue to use the portable tool argument or compatible
Roots.

Malformed, relative, non-local, or non-repository explicit or negotiated
context fails the call with a routing diagnostic. It never silently falls back
to Roots or the global workspace. Local paths are consumed only by the agent-
host resolver and are never included in the Cloud request.

While a `roots/list` request is pending, the proxy defers incoming
`tools/call` requests that contain neither explicit nor negotiated Repository
Context instead of executing them against the fallback target. A call with
request-local context is independent of that generation and proceeds
immediately. The queue is bounded. If it is full, the proxy returns a retryable
workspace context error rather than guessing a target.

When the matching roots response arrives, the proxy first publishes either the
validated root paths or the established empty fallback for a roots error. It
then executes deferred tool calls in arrival order and emits their individual
JSON-RPC responses. A roots-change notification clears the previous root
generation and applies the same barrier until the replacement generation is
settled.

A client that does not advertise Roots has no pending root generation. Calls
with explicit context use it; calls without context continue immediately
through the documented process or user fallback. Missing, invalid, ambiguous,
or explicitly rejected Roots also preserve that fallback after the Roots
request completes.

The proxy does not infer a repository from its process working directory,
mutate environment variables per call, cache one unkeyed task directory, send
local paths to the service, or change API-origin and token precedence. Roots
and negotiated cwd metadata remain informational context rather than access-
control boundaries.

## Consequences

`list_sources`, `search`, `list_recent_memories`, `get_memory`, `get_resource`,
Memory lifecycle tools, and review tools share one routing contract. Calls
cannot observe different workspaces merely because they arrived on opposite
sides of a pending Roots response, nor can concurrent calls for different
repositories overwrite process-wide routing state.

Codex calls no longer depend on the model remembering to reproduce the current
working directory in tool arguments. Because `sandboxCwd` remains call-scoped,
two tasks using the same installed plugin can resolve different repository
overrides without restarting or rewriting MCP configuration.

The short initialization interval may delay a tool response until the client
answers its own roots request. The bounded queue prevents unbounded request
accumulation, while the MCP client's normal request timeout remains the
connection-level bound for a client that advertises roots but never responds.
Wrong-workspace execution is never used as timeout recovery.

This amendment supersedes both the roots-only assumption and the later
assumption that model-generated tool input is the only safe call-scoped carrier.
Explicit per-call Repository Context remains authoritative, negotiated host
metadata is the automatic request-scoped adapter, and MCP Roots remain a
compatibility input only when a call omits both.

## References

- [ADR 0016: Keep manual Memory creation independent of repository roots](0016-keep-manual-memory-creation-independent-of-repository-roots.md)
- [Cloud Issue #285](https://github.com/dodoman-sun/memforge-cloud/issues/285)
- [Cloud Issue #297](https://github.com/dodoman-sun/memforge-cloud/issues/297)
- [MCP SEP-2577: Deprecate Roots, Sampling and Logging](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging)
- [MCP 2026-07-28 Roots](https://modelcontextprotocol.io/specification/2026-07-28/client/roots)
- [MCP 2026-07-28 Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [OpenAI Codex MCP client capabilities](https://github.com/openai/codex/blob/d6407d735942c7cfc996aa2bc7d0f97fc8f0e4bf/codex-rs/codex-mcp/src/rmcp_client.rs#L936-L952)
- [OpenAI Codex PR #17763: Send sandbox state through MCP tool metadata](https://github.com/openai/codex/pull/17763)
- [OpenAI Codex PR #28914: Scope MCP sandbox metadata to server environment](https://github.com/openai/codex/pull/28914)
- [OpenAI Codex 0.146.0 request metadata routing](https://github.com/openai/codex/blob/be449751a978f02e5bbba886999662956c7f38f5/codex-rs/core/src/mcp_tool_call.rs#L723-L789)
- [MCP roots](https://modelcontextprotocol.io/specification/2025-03-26/client/roots)
- [MCP lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)
