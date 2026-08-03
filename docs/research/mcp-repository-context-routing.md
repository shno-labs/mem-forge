# MCP repository-context workspace routing

Research date: 2026-08-03. This note is a design input for repository-local
MemForge workspace routing. It is not an ADR. Source-code observations are
pinned to OpenAI Codex `d6407d735942c7cfc996aa2bc7d0f97fc8f0e4bf`, the
official MCP Python SDK `a4f4ccd091138771535e17191123f20b30fda68e`, and the
official MCP servers repository `76d64c822f5125032f89eb71dbdb94e42b434821`.

## Conclusion

An MCP server cannot require `roots/list` for correct workspace routing.
Roots have always been an optional client capability, current Codex source
does not opt in to that capability, and MCP 2026-07-28 deprecates Roots in
favor of tool parameters, resource URIs, or server configuration. When a
MemForge tool call already carries an exact
`repository_context.working_directory`, that request-local value should be
the primary input to the existing repository workspace resolver. Roots should
remain a compatibility fallback for calls that do not carry repository
context, not an authority that can override an explicit call context.

The resolver should produce one immutable workspace target per tool call and
use it for both repository attribution and every workspace-bound Cloud request.
Do not mutate `MEMFORGE_WORKSPACE_ID` or cache one unkeyed effective workspace
for the process: concurrent calls for different repositories must not affect
one another.

## Primary-source findings

### Roots are optional and clients may omit them

In the MCP 2025-11-25 specification, only clients *that support Roots* must
declare the `roots` capability during initialization. The lifecycle describes
Roots as one of the optional negotiated client capabilities and requires each
peer to use only successfully negotiated capabilities. The Roots error section
explicitly defines `-32601 Method not found` for a client that does not support
Roots. Therefore an MCP server must be prepared for a fully conforming client
that neither advertises Roots nor answers `roots/list`.

Sources:

- [MCP 2025-11-25 Roots: capability, listing, and unsupported-client error](https://modelcontextprotocol.io/specification/2025-11-25/client/roots)
- [MCP 2025-11-25 lifecycle: capability negotiation and operation](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)

The MCP 2026-07-28 specification makes the direction stronger: Roots is
deprecated, new implementations should not adopt it, and existing
implementations should migrate to passing directories or files through tool
parameters, resource URIs, or server configuration. While compatibility
remains, supporting clients advertise Roots in per-request metadata; absence
is still valid. Roots are also described as informational guidance, not an
access-control mechanism.

Source: [MCP 2026-07-28 Roots and deprecation guidance](https://modelcontextprotocol.io/specification/2026-07-28/client/roots).

The same revision defines tool inputs in `tools/call.params.arguments`, binds
them to each tool's `inputSchema`, and requires servers to validate them.
Together with the Roots migration guidance, this makes an explicit optional
repository-context argument the protocol-aligned carrier for routing state.

Source: [MCP 2026-07-28 Tools: schema and calling tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools#calling-tools).

### Current Codex does not advertise the Roots capability

Current OpenAI Codex constructs its MCP client capabilities from
`ClientCapabilities::default()`, sets elicitation, optionally adds the
`openai/form` extension, and does not set Roots. It currently pins the legacy
initialization request to MCP 2025-06-18. A MemForge server must therefore not
interpret a missing Codex Roots response as missing repository intent when the
tool call itself contains an exact working directory.

Source: [OpenAI Codex MCP initialization source, pinned](https://github.com/openai/codex/blob/d6407d735942c7cfc996aa2bc7d0f97fc8f0e4bf/codex-rs/codex-mcp/src/rmcp_client.rs#L936-L952).

Codex does preserve the active turn/session working directory when launching a
local stdio MCP process. That is useful process-launch configuration, but it
cannot provide per-call repository selection to a long-lived or HTTP MCP
server. The distinction reinforces why MemForge must consume the exact working
directory already attached to each tool call.

Sources:

- [Codex derives the local MCP fallback cwd, pinned](https://github.com/openai/codex/blob/d6407d735942c7cfc996aa2bc7d0f97fc8f0e4bf/codex-rs/core/src/session/mcp_runtime.rs#L23-L30)
- [Codex applies configured cwd or the session fallback, pinned](https://github.com/openai/codex/blob/d6407d735942c7cfc996aa2bc7d0f97fc8f0e4bf/codex-rs/codex-mcp/src/rmcp_client.rs#L1014-L1056)

### First-party SDKs favor explicit request-local context

The official MCP Python SDK v2 removed its ambient
`server.request_context`/module-level `ContextVar` and now passes
`ServerRequestContext` directly to every handler. That context carries the
request ID, metadata, method, raw parameters, protocol version, and request
object. The architectural pattern is to resolve request-dependent state from
the handler's explicit context, not from mutable process state.

Source: [MCP Python SDK v2 request-context migration, pinned](https://github.com/modelcontextprotocol/python-sdk/blob/a4f4ccd091138771535e17191123f20b30fda68e/docs/migration.md#L1630-L1658).

The official filesystem MCP server supplies the closest server-side fallback
example. It can combine explicit command-line allowed directories with Roots;
if the client does not support Roots, the server continues with the explicit
directories. It requires at least one valid source instead of assuming every
client supplies Roots. MemForge should likewise preserve its explicit/global
configuration fallback while allowing the more precise per-call repository
argument to win.

Source: [Official filesystem MCP server directory/Roots fallback, pinned](https://github.com/modelcontextprotocol/servers/blob/76d64c822f5125032f89eb71dbdb94e42b434821/src/filesystem/README.md#L54-L63).

## Design implications for MemForge

Use one request-local target-resolution path for every workspace-bound tool:

1. If `repository_context.working_directory` is present, normalize and
   validate the absolute path, then run the existing repository workspace
   resolver from that directory. A valid repository-local
   `.memforge/config.toml` wins according to the existing configuration
   precedence.
2. If repository context is absent, use a settled, unambiguous MCP root as the
   compatibility path for older callers that advertise Roots.
3. If neither per-call context nor a usable root exists, use the configured
   process/user default workspace.
4. Resolve once at the start of the tool call and pass the resulting target
   to repository attribution, source operations, memory operations, and the
   HTTP client. Do not resolve attribution and the HTTP workspace separately.

Every workspace-bound tool, including `list_sources`, needs the same optional
repository-context input or an equivalent SDK-injected request context. This
matches MCP 2026's explicit recommendation to carry directory context in tool
parameters and closes the current asymmetry where search can be attributed to
one repository while its HTTP request targets another workspace.

If an explicit repository context is present but malformed or unusable, fail
with a routing diagnostic rather than silently returning data from the global
workspace. Repository-override syntax remains the responsibility of the shared
configuration resolver and setup validation. Roots must not be treated as an
access-control allowlist: canonicalize and validate the supplied path through
the server's normal filesystem/security boundary, but do not reject a valid
explicit working directory merely because an optional Roots capability is
absent or stale.

## Acceptance cases

The implementation should prove the boundary with request-level tests:

| Call context | Roots state | Expected target |
| --- | --- | --- |
| Exact repo cwd with local override | Unsupported/absent | Repo override |
| Exact repo cwd with local override | Different global/root workspace | Repo override |
| Exact repo cwd, no local override | Unsupported/absent | Normal configured fallback |
| No repository context | One settled repo root with override | Root-derived repo override |
| No repository context | Unsupported/absent | Global default |
| Invalid explicit repository context | Any | Routing error; never silent cross-workspace data |

Run the same cases through `list_sources` and at least one memory operation.
Also issue two concurrent calls with different repository working directories
and assert their generated workspace URLs and repository attribution remain
independent. A test that only checks the reported effective workspace is not
sufficient; it must assert the actual workspace ID used by the outbound
adapter/client call.

## Non-goals

- Do not require an OpenAI Codex change or wait for Roots support.
- Do not remove Roots compatibility while older MCP clients still expose it.
- Do not mutate environment variables per call or add source-type-specific
  routing branches.
- Do not treat Roots as proof of filesystem authorization.
