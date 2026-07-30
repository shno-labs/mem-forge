# Settle MCP roots before workspace-routed tool calls

Status: Accepted (2026-07-30)

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

Repository Context supplied to `search` and `create_memory` is not a substitute
for this routing decision. It provides optional repository attribution and
retrieval affinity for that operation. Tools such as `list_sources` have no
per-call working-directory argument, and adding one to every tool would leak a
transport race into the tool contract.

## Decision

One resolved MCP root generation owns workspace routing for every HTTP-backed
tool call.

While a `roots/list` request is pending, the proxy defers incoming
`tools/call` requests instead of executing them against the fallback target.
The queue is bounded. If it is full, the proxy returns a retryable workspace
context error rather than guessing a target.

When the matching roots response arrives, the proxy first publishes either the
validated root paths or the established empty fallback for a roots error. It
then executes deferred tool calls in arrival order and emits their individual
JSON-RPC responses. A roots-change notification clears the previous root
generation and applies the same barrier until the replacement generation is
settled.

A client that does not advertise roots has no pending root generation, so tool
calls continue immediately through the documented process or user fallback.
Missing, invalid, ambiguous, or explicitly rejected roots also preserve that
fallback after the roots request completes.

The proxy does not infer a repository from its process working directory, add
workspace parameters to individual tools, send local paths to the service, or
change API-origin and token precedence.

## Consequences

`list_sources`, `search`, `get_memory`, `get_resource`, Memory lifecycle tools,
and review tools cannot observe different workspaces merely because they
arrived on opposite sides of a pending roots response.

The short initialization interval may delay a tool response until the client
answers its own roots request. The bounded queue prevents unbounded request
accumulation, while the MCP client's normal request timeout remains the
connection-level bound for a client that advertises roots but never responds.
Wrong-workspace execution is never used as timeout recovery.

Explicit per-call Repository Context remains preferred for repository
attribution as described by ADR 0016. MCP roots remain the compatibility input
that can select one repository workspace for tools whose contracts do not carry
per-call context.

## References

- [ADR 0016: Keep manual Memory creation independent of repository roots](0016-keep-manual-memory-creation-independent-of-repository-roots.md)
- [Cloud Issue #285](https://github.com/dodoman-sun/memforge-cloud/issues/285)
- [MCP roots](https://modelcontextprotocol.io/specification/2025-03-26/client/roots)
- [MCP lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)
