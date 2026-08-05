# Keep the OSS public beta local-only

Status: Accepted (2026-07-26)

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

The OSS public-beta Compose profile is single-user, tenancy-unaware,
authentication-free, and same-host only. Docker publishes both the Admin UI and
API strictly on `127.0.0.1`. Host port numbers remain configurable for local
conflict resolution, but the bind address is not an environment override.

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
Remote access becomes a supported profile only after a separate decision
defines end-to-end identity, authenticated sessions or service credentials,
authorization and tenancy semantics, TLS and origin protections, secret
management, recovery, migration, and compatibility for UI, CLI, daemon, and
MCP clients.
