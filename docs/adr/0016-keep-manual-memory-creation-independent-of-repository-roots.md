# Keep manual Memory creation independent of repository roots

Status: Accepted (2026-07-26)

## Context

The MCP `create_memory` tool records user-confirmed durable knowledge as a
private `user_memory`. Repository identity improves attribution and retrieval
affinity, but the MemForge service cannot discover a coding client's local
working directory. That context must cross the agent-host seam before the local
proxy can resolve it to a normalized Git remote.

MCP filesystem roots are optional, have uneven client support, and are
deprecated by MCP SEP-2577. Environment-variable fallbacks are client-specific,
static for the lifetime of the proxy process, and require users to duplicate
context their coding host already owns. The proxy process working directory is
also not authoritative because packaged servers commonly start from an
installation or plugin directory.

The shared OSS request and lifecycle contracts already model
`repo_identifier` as optional. Requiring the proxy to resolve exactly one Git
remote made the packaged tool reject otherwise valid manual memories before
they reached those contracts. It also made repository metadata behave like
authorization even though the authenticated principal and private visibility
own that boundary.

## Decision

The packaged MCP proxy owns one host-neutral Repository Context module. Its
interface resolves an optional per-call working directory and compatible
client-provided roots into one of three results: exact, absent, or ambiguous.
It derives repository identity locally with the Git `origin` remote and the
shared repository-identifier normalization contract.

`search` and `create_memory` expose the same optional
`repository_context.working_directory` tool argument. Coding clients pass the
exact current working directory when it is available and omit the object when
it is not. The proxy consumes this object locally; raw filesystem paths are
never sent to OSS or Cloud.

Existing MCP `roots/list` support remains a compatibility adapter during the
protocol deprecation period. Explicit per-call context takes precedence because
it identifies the repository active for that operation. The proxy does not read
`CODEX_WORKSPACE_ROOT`, another client-specific workspace variable, or its own
process working directory as a fallback.

Manual `create_memory` still requires durable content, provenance, a
server-resolved principal, and the existing memory-type and confidence
validation. Repository identity remains optional attribution:

- when per-call context or compatible roots resolve exactly one Git remote, the
  proxy sends its normalized `repo_identifier`;
- when context is unsupported, unavailable, ambiguous, invalid, or not a Git
  repository, the proxy omits `repo_identifier` and creates an unscoped private
  Memory;
- the server remains responsible for principal, visibility, lifecycle,
  idempotency, provenance, and storage validation.

Search follows the same rule. Exact context becomes
`active_repo_identifier`, which is a ranking affinity rather than an access
predicate. Absent or ambiguous context leaves search broad. Exact repository
filtering remains a separate explicit search capability.

The provenance documents created by direct user lifecycle operations remain
virtual: `user_memory` and `user_correction` do not correspond to configured
Source rows. Their Memories stay readable under the normal owner/visibility
predicate. Configured-source access checks continue to apply to configured
Source support, and a dangling non-virtual source edge does not widen access.

Memory provenance exposes one derived Origin Kind rather than persisting a
parallel classification: `user_memory` and `user_correction` are
`direct_user`, `agent_session` is `managed_capture`, and other source types are
`configured_source`. Client and Repository Context remain independent
dimensions. Storage adapters derive this classification from the canonical
source type, so no schema migration or historical backfill is required and the
classification cannot drift from the provenance edge that owns it.

## Consequences

Codex, Claude Code, Cursor, and future MCP clients share one tool contract.
Repository Context resolution has no MemForge client-name branches. Clients
that expose MCP roots receive automatic compatibility behavior; other clients
can supply the per-call working directory through the standard tool interface.
No user-managed workspace environment variable is required.

The Repository Context module is the only place that understands local path
validation, Git remote lookup, exact/absent/ambiguous resolution, and transport
precedence. Tool handlers consume only its normalized result.

This decision does not change automatic Agent Session reconciliation.
Agent-session windows still carry repository identity for same-repository
candidate selection and claim projection. It also does not weaken
source-backed lifecycle validation or make repository roots an authorization
boundary.

SQLite and Cloud adapters must implement the same optional `repo_identifier`
and virtual-provenance visibility contract for manual `user_memory` creation.
Cloud receives the normalized identifier only and never receives a client-local
path.

This decision does not add a Cursor distribution package or expand the bounded
agent-session producer/client taxonomy. Those are separate integration and
source-lifecycle decisions.

## References

- [Agent Knowledge Bundle](../design/agent-knowledge-bundle.md)
- [Agent Hook Integration](../design/agent-hook-integration.md)
- [MCP SEP-2577: Deprecate Roots, Sampling, and Logging](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging)
