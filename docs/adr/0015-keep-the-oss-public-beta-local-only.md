# Keep the OSS public beta local-only

Status: Accepted (2026-07-26; clarified 2026-08-30 by
[ADR 0031](0031-distribute-personal-local-oss-as-an-installed-tool.md))

## Context

The self-hosted OSS public beta has one operator, no tenancy boundary, and no
built-in request authentication. Publishing its Admin UI or API to a LAN would
therefore expose memory data, source configuration, provider credentials, and
mutation routes without an access-control boundary.

Adding an incomplete JWT/login layer would create a misleading sense of
protection without defining identity, session, recovery, secret, and
authorization lifecycles. Reusing the Cloud tenancy and authentication stack
would couple the local edition to hosted infrastructure and contradict its
small, self-contained deployment goal.

## Decision

The OSS Personal Local Profile is single-user, tenancy-unaware,
authentication-free, and same-host only. Every supported distribution binds
its Admin UI and API strictly to loopback. Host port numbers may remain
configurable for local conflict resolution, but an environment variable,
native launcher option, container port declaration, or persisted setting may
not widen the bind address.

The current Compose path publishes both services on `127.0.0.1`. A native Web
path must bind its one same-origin UI/API listener to `127.0.0.1` as well.
Distribution choice does not weaken or replace the host security boundary.

Same-host browser access, the Admin UI proxy, CLI, local-agent daemon, and
packaged Codex or Claude MCP clients continue to use the loopback endpoints. A
client inside another container has a different loopback namespace and must use
an explicitly supported host or container route; the default host binding is
not widened to accommodate it.

Shared and truly remote deployment are outside this beta contract. Operators
must not expose this profile through a LAN bind, port forward, or public reverse
proxy.

## Consequences

The local beta relies on the host boundary rather than application login.
[ADR 0031](0031-distribute-personal-local-oss-as-an-installed-tool.md) chooses
the target installation and fallback surfaces without changing this invariant.
Remote access becomes a supported profile only after a separate decision
defines end-to-end identity, authenticated sessions or service credentials,
authorization and tenancy semantics, TLS and origin protections, secret
management, recovery, migration, and compatibility for UI, CLI, daemon, and
MCP clients.
