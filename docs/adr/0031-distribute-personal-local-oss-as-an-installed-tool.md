# ADR 0031: Distribute personal-local OSS as an installed tool

## Status

Accepted (2026-08-30)

## Context

The OSS edition is a Personal Local Profile: one owner, one local machine, one
`local` workspace, one writable service instance, and light but durable use.
Team access, remote servers, replicas, multi-user authorization, and high write
concurrency belong to MemForge Cloud. Treating OSS as a smaller community
server would duplicate the Cloud boundary and add operational complexity that
the intended user does not need.

Docker currently gives MemForge a reproducible userspace for Python, Pango,
fonts, the Admin UI, and other native dependencies. It also adds a container
engine or desktop VM, Docker-managed volumes, port translation, and special
host routing for local model APIs. Those costs are material for a personal
application that must reach local files, browser sessions, the operating-system
keyring, Ollama, LM Studio, and other same-host OpenAI-compatible endpoints.

SQLite is an in-process, disk-backed database suited to one local writer.
Chroma `PersistentClient` is a persistent embedded topology that Chroma itself
documents for personal use and long-term memory. Neither store requires a
separate user-managed database process for this bounded profile. Their local
fit does not extend the profile to team or server-grade operation.

## Decision

The target durable OSS installation is a version-pinned isolated tool:

```bash
uv tool install --python 3.12 'memforge-ai==X.Y.Z'
memforge web
```

`memforge web` owns one foreground or user-service application process, one
worker, one data root, embedded SQLite, one Chroma `PersistentClient`, the
version-matched Admin UI, and one same-origin loopback listener. A data-root
lock rejects a second server, migration writer, restore, or reindex owner.
SQLite and Chroma files stay on a local filesystem; network-file sharing and
replicated writers are outside the profile.

`uvx` is a trial surface only:

```bash
uvx --python 3.12 --from 'memforge-ai==X.Y.Z' memforge web
```

Its executable environment is disposable cache. Durable MemForge data never
lives under that cache, and documentation prints the resolved application
version so a trial can be reproduced exactly. An unpinned moving version is
discovery UX, not a durable-instance contract.

Docker remains a supported fallback for an unsupported native platform, a
failed native dependency preflight, users who explicitly prefer container
isolation, CI, and maintainer reproduction. It remains the documented default
until the native acceptance gates below pass. Docker uses the same Personal
Local Profile, loopback security boundary, data formats, migrations, backup,
and recovery contracts; it is not a distinct product or a larger OSS server
mode.

The published Python release must own the complete ordinary Web experience:

- build the Admin UI in release CI and package its hashed assets with the
  matching server version;
- serve UI and API on one origin without an end-user Node or npm build;
- publish and clean-install-test a reproducible application dependency set;
- keep Pango/WeasyPrint PDF export and Playwright/browser collection out of
  core boot behind explicit optional-feature preflights or packaged extras;
- let the first-run UI configure and probe enrichment and embedding provider,
  model, base URL, and credential;
- store provider credentials through one operating-system keyring abstraction,
  with only an explicit encrypted-file fallback and no plaintext downgrade;
- resolve data, config, state, logs, cache, and runtime files through one path
  registry with a `MEMFORGE_HOME` portability override and `memforge paths`;
- expose vector count and dimension, SQLite/WAL and Chroma sizes, process RSS,
  available RAM, and free-disk guardrails before admitting more ingestion.

Local collection remains a separate consented operating-system user service
under [ADR 0029](0029-manage-local-collection-as-a-user-service.md). Installing
or starting the Web service does not silently install the collection daemon,
move its target, or copy its credentials.

The native path becomes the front-page OSS default only after clean-machine
macOS, Linux, and each declared Windows/architecture combination proves install,
first boot, provider configuration, first Memory, search, graceful shutdown,
restart persistence, resource guards, backup, restore, supported upgrade,
downgrade refusal, service lifecycle, and keep-data uninstall from the
published artifact. Until then, Docker is the honest supported default.

## Considered options

- **Keep Docker as the permanent primary UX.** Rejected for the target profile
  because it makes a container engine, host routing, and volume operations
  permanent prerequisites without changing SQLite or HNSW capacity.
- **Use `uvx` as the durable installation.** Rejected because its tool
  environment is cache and it does not own login startup, stable executable
  lifecycle, upgrade, or uninstall.
- **Publish a signed desktop or single-binary application first.** Deferred.
  It may later improve nontechnical UX, but it creates a larger per-platform
  signing, notarization, update, native-library, and rollback product before
  the installed-tool contract is proven.
- **Run a separate SQL or vector server locally.** Rejected for the Personal
  Local Profile. It adds processes, ports, configuration, and failure modes for
  concurrency that belongs to Cloud.

## Consequences

The OSS release is intentionally not an unqualified production server. Its
embedded topology is accepted only with the single-owner, single-instance,
local-filesystem, loopback-only boundary. Resource pressure must pause writes
while preserving read/export and present Cloud as the team/high-concurrency
path rather than silently widening OSS.

Docker remains tested and recoverable, but no implementation may use Docker to
create different lifecycle semantics or to compensate for an unsafe canonical
OSS contract. Cloud continues to implement shared behavior through the OSS
protocols and its own storage adapters; this decision adds no Cloud-only
runtime branch.

Executable delivery does not own durable data compatibility. Both native and
Docker upgrades follow
[ADR 0032](0032-guard-local-data-upgrades-with-recoverable-migrations.md).

## References

- [Issue 341: Ship Personal Local OSS installation and recoverable upgrades](https://github.com/shno-labs/mem-forge/issues/341)
- [ADR 0015: Keep the OSS public beta local-only](0015-keep-the-oss-public-beta-local-only.md)
- [ADR 0029: Manage local collection as an operating-system user service](0029-manage-local-collection-as-a-user-service.md)
- [SQLite: Appropriate Uses For SQLite](https://www.sqlite.org/whentouse.html)
- [Chroma: Anthropic MCP client types](https://docs.trychroma.com/integrations/frameworks/anthropic-mcp)
- [uv: Tools](https://docs.astral.sh/uv/concepts/tools/)
- [Apple: Using the file system effectively](https://developer.apple.com/documentation/foundation/using-the-file-system-effectively)
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir/latest/)
