# Agent Session Curator Design

## Status

Draft for review. This document defines the desired architecture before
implementation. It intentionally does not prescribe a temporary migration
bridge or cloud-only route replacement.

## Problem

Agent coding sessions can produce far more memories than document sources. A
long-lived Codex or Claude Code setup can accumulate thousands of small
session-derived memories for the same repository. Flat search then becomes
noisy: old atomic memories compete with newer, more stable learnings, and the
UI becomes dominated by low-level session artifacts.

Document sources and session sources also have different natural ownership
models. Confluence and Jira content usually maps cleanly to a MemForge project.
Agent sessions are different: their most stable context is the code repository
where the session occurred. A repo may serve several MemForge projects, and a
MemForge project may contain several repos. Treating `project_key` as the
primary identity for session memories makes repo-level conventions harder to
retrieve and can mix unrelated repositories in the same business bucket.

## Goals

- Keep Codex and Claude Code agent-session memories useful over long periods.
- Make curated, consolidated memories searchable without losing access to the
  original atomic memories.
- Use repository identity as the primary grouping dimension for coding-session
  memories.
- Keep MemForge project relevance as an optional mapping for session memories,
  not the sole organizing key.
- Make the Curator source-type extensible, so Jira, Confluence, Teams, and
  future sources can add their own policies later.
- Preserve existing visibility and owner boundaries.
- Keep the first implementation small and non-destructive.

## Non-Goals

- Do not curate Jira, Confluence, or other document/work-tracking sources in
  the first implementation.
- Do not automatically delete or retire atomic memories in the first
  implementation.
- Do not replace project-aware search with repo-only search.
- Do not introduce a cloud-only API fork. OSS routes and services remain the
  canonical behavior; cloud provides storage implementations.
- Do not create a broad UI control panel for every curator knob in the first
  implementation.

## Current Baseline

The agent-session gene already exposes `repo` as its project binding field, and
normalization carries `client`, `session_id`, `workspace`, `repo`, `branch`, and
`commit_sha` through `source_semantics`.

The project resolver is intentionally conservative: if a binding is absent or a
repo is unmapped, the memory lands in `UNSORTED`; it does not mint project keys
from workspace path names.

Search already supports `project-first` behavior. In this mode, workspace
memories remain visible across projects, and cross-project candidates receive a
ranking penalty instead of being filtered out. That is a good base for adding
repo affinity without breaking existing project-aware behavior.

The memory model has lifecycle states such as `active`, `superseded`, and
`retired`, but it does not yet have a first-class representation for curated
lineage. Curated memories should not be encoded only as a lifecycle status.

## Design Principles

1. Source identity, context identity, and project relevance are different axes.
2. Coding-session memory is repo-first, project-second.
3. Curated memories are first-class searchable memories.
4. Search must be lineage-aware to avoid returning both a summary and all of
   its children by default.
5. Curator policies are source-type specific; the Curator runner is generic.
6. The first release is additive and reversible.

## Data Model

### Memory Identity Axes

Every memory should continue to carry existing source provenance and access
fields. The Curator adds a context layer instead of overloading `project_key`.

For agent sessions:

- `source_type`: `agent_session`
- `client`: `codex` or `claude-code`
- `repo_identifier`: canonical repository identity
- `project_key`: optional MemForge project relevance bucket
- `visibility` and `owner_user_id`: unchanged

For document sources:

- `source_type`: `confluence`, `jira`, etc.
- `context_identifier`: source-specific source context such as Confluence
  space/page tree or Jira project/filter
- `project_key`: primary project relevance bucket

### Repository Identity

`repo_identifier` is the canonical key for agent-session grouping. Prefer a
stable remote-derived identity, for example:

1. Normalized VCS remote URL such as `github.tools.sap/org/repo`.
2. Explicit repo slug supplied by the client.
3. Existing receipt `repo` value.
4. Workspace basename only as a last-resort display fallback, never as a project
   key.

This value should be stored as source semantics and copied into vector metadata
where search adapters need it for ranking or filtering.

### Curated Lineage

Add first-class lineage instead of hiding curated memories in a separate store.
The minimal schema is:

- `memories.memory_level`: `atomic` or `consolidated`
- `memories.curation_cluster_id`: nullable stable cluster key
- `memory_derivations`:
  - `parent_memory_id`
  - `child_memory_id`
  - `relation`, initially `summarizes`
  - `created_at`
- `memory_curation_runs`:
  - run id
  - policy id/version
  - source type
  - client
  - repo identifier
  - project key
  - candidate count
  - created memory count
  - skipped reason/error
  - timestamps

`memory_level` is not a lifecycle status. A consolidated memory may be active,
superseded, or retired just like an atomic memory.

## Curator Architecture

The Curator has a generic runner and source-specific policies.

```text
CuratorRunner
  -> loads candidate clusters
  -> picks a MemoryCuratorPolicy
  -> asks policy to select eligible memories
  -> generates consolidated memory candidates
  -> persists consolidated memories and lineage
  -> records curation run audit data
```

Policy contract:

```text
MemoryCuratorPolicy
  policy_id
  applies_to(source_type, source_semantics)
  cluster_key(memory, source_semantics)
  eligibility(memory, lineage, stats)
  prompt_overlay(cluster)
  parse_result(model_output)
  search_weighting_hint(memory)
```

First policies:

- `agent_session.codex.v1`
- `agent_session.claude_code.v1`

All other source types are unregistered in the first implementation. They are
not routed through a generic fallback policy; adding a new type requires an
explicit policy and tests.

## Agent-Session Clustering

Cluster key:

```text
workspace_or_tenant
owner_user_id or workspace-visible marker
repo_identifier
client_group
project_key or UNSORTED
topic signature
```

`client_group` should allow Codex and Claude Code memories for the same repo to
be consolidated together only when they share the same access boundary and repo.
The source id remains per client; the Curator cluster is allowed to span clients
because the durable repo facts may be shared by both agent tools.

Topic signature can be derived from tags/entities/memory type and then refined
by the Curator prompt. The first implementation should keep this deterministic
and conservative: do not use a broad LLM clustering pass over all memories.

## Search Behavior

Search should retrieve both atomic and consolidated memories. Consolidated
memories are not hidden.

After normal retrieval and ranking, add a lineage-aware result shaping step:

1. Fetch lineage metadata for top candidates.
2. Group candidates that belong to the same curation family.
3. If a consolidated memory and its children are both present, default to the
   consolidated memory.
4. Preserve exact-match behavior: if an atomic child has a clearly higher score
   for an exact error, symbol, issue id, or file-specific query, allow the child
   to appear above the consolidated memory.
5. Expose covered child count and lineage metadata for drill-down.

Ranking affinity should include both project and repo:

- `project_key` remains the relevance bucket used by existing project-first
  behavior.
- `repo_identifier` becomes an additional affinity signal when the request has
  repo context.
- In a coding-agent hook or MCP search with repo context, same-repo memories get
  priority.
- If no repo context is present, search falls back to existing project-first or
  workspace behavior.

This keeps UI search, project-scoped search, and coding-agent search aligned
without making project mapping mandatory for sessions.

## Request Context

Extend request/search context with optional repo identity:

```text
AccessScope
  user_id
  include_private
  allowed_statuses
  active_project
  scope_mode
  active_repo_identifier optional
```

This is not an access control dimension. It is a relevance signal. Access is
still governed by visibility, owner, workspace, and project mode semantics.

The explicit MCP/CLI search path should eventually send repo context, not only
the hook injection path. Without that, explicit searches remain flatter than
SessionStart-style hook context.

## Persistence and Adapter Contracts

Storage-neutral behavior belongs in OSS services and protocols:

- Curator candidate reads
- Curated memory insert
- Lineage insert/read
- Curation run audit
- Ranking metadata that includes `repo_identifier`, `memory_level`, and lineage
  family ids where needed

SQLite implements the contract in OSS. Cloud HANA implements the same contract
in cloud. Future Postgres should implement the same protocol without route
replacement.

## UI Behavior

First release UI can stay small:

- Search result indicates consolidated memories with a compact label.
- Search result can show "covers N memories".
- Memory detail can list lineage children.
- Source list does not need a Curator dashboard yet.

Admin-facing curation runs can be added later only if users need operational
visibility into scheduled curation.

## Triggering

Curator should not run on every UI load or every memory insert.

Initial trigger options:

- Scheduled background job.
- Manual admin/developer command.
- Threshold-based run when an owner/repo has more than N eligible active
  agent-session memories older than a minimum age.

Suggested first default:

- minimum age: 14 days
- minimum cluster size: 20 atomic memories
- source types: agent_session only
- clients: codex and claude-code
- destructive actions: disabled

## Privacy and Safety

- Never consolidate across owner boundaries for private memories.
- Never consolidate private and workspace-visible memories into one memory.
- Preserve source provenance and evidence ids.
- Do not store secrets in curated memories.
- Curated memories inherit the strictest visibility boundary of their cluster.
- Any future retire/supersede action must be auditable and reversible.

## Testing Strategy

### Unit

- Repo identifier normalization.
- Agent-session policy applies only to Codex and Claude Code.
- Cluster keys do not merge different repos.
- Cluster keys do not merge private memories from different owners.
- Project key remains optional for agent sessions.

### Storage Contract

- SQLite and HANA implementations expose the same lineage and curation-run
  behavior.
- Ranking metadata includes project key, repo identifier, memory level, and
  lineage family where required.

### Search

- Broad repo query prefers consolidated memory.
- Exact error or issue query can prefer atomic child.
- Consolidated memory and children collapse by default.
- No repo context preserves current project-first behavior.
- Repo context boosts same-repo memories without hiding cross-repo candidates.

### Integration

- Codex and Claude Code memories from the same repo can consolidate together
  only when access boundaries match.
- Memories from different repos under the same MemForge project do not
  consolidate together.
- Memories from the same repo under different project mappings remain connected
  by repo identity but do not bypass project relevance rules.

## Rollout Plan

1. Add source-semantics and metadata support for canonical `repo_identifier`.
2. Add storage-neutral Curator protocol and SQLite schema.
3. Add agent-session Curator policies.
4. Add lineage-aware search result shaping.
5. Add HANA implementation of the same storage contract.
6. Add focused UI labels/details for consolidated memories.
7. Enable manual or scheduled Curator run for agent_session only.

## Open Decisions

### Should project be primary for session memory?

No. For coding sessions, repo identity is primary and project key is optional
relevance metadata.

### Should consolidated memories be searchable?

Yes. They must be first-class searchable memories. The search layer should
collapse duplicate families instead of hiding the consolidated layer.

### Should originals be deleted or retired?

No for the first implementation. Original atomic memories remain active until a
separate reviewed lifecycle policy exists.

### Should Curator be source-type extensible?

Yes. V1 registers only agent-session policies, but the runner and storage model
must not assume agent sessions are the only possible curated source.

## References

- OpenAI Codex Memories: https://developers.openai.com/codex/memories
- Claude Code Memory: https://code.claude.com/docs/en/memory
- Claude Memory Tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- HiMem hierarchical long-term memory: https://arxiv.org/html/2601.06377v1
