# MCP Memory Search Facets

## Goal

MemForge MCP search should let agents ask flexible natural-language questions while using explicit, validated facets when the agent knows the scope. A missing facet means "search all visible memories"; a provided facet narrows results. Facet values are exact; the system does not silently guess or normalize them.

## User Contract

The ordinary MCP tool exposes one memory query path: `search`.

Agents may provide:

- `query`: required natural-language question.
- `memory_types`: optional memory-type enum filter.
- `time_range`: optional date-only range. `start_date` and `end_date` are
  individually optional, but at least one is required when `time_range` is sent.
  Agents convert phrases such as "last week" into explicit `YYYY-MM-DD` bounds
  before calling. `date_type` is either `source_updated_at` (default) or
  `memory_updated_at`.
- `include_private`: optional flag. The server still decides whose private memories are visible from the authenticated principal.
- `include_superseded`: optional lifecycle broadening.
- `status`: optional lifecycle status.
- `active_project` / `scope_mode`: optional project ranking context.
- `source_filter`: optional source facets:
  - `source_types`: registered source types such as `agent_session`, `jira`, or `confluence`.
  - `clients`: bounded agent-session clients such as `codex` or `claude-code`.
  - `current_repo_only`: restrict to the current git repository. The local MCP
    proxy resolves the exact repository identifier.

Agents should omit a facet when unsure. They must not invent source ids, user ids, or fuzzy labels. Invalid enum values are request errors.

## Non-Goals

- No fuzzy normalization for source types, clients, repositories, or source names.
- No MCP-facing exact source-instance or arbitrary repository-id filter for
  normal search. Source ids and exact repo ids remain internal or advanced API
  concerns.
- No MCP-facing `active_repo_identifier`. The local proxy may derive it as an
  internal ranking signal, but the model cannot provide or override it.
- No `list_recent_changes` MCP memory tool. Recent-memory questions should use `search` with `time_range`.

## Architecture

```text
MCP search tool
  -> ToolClient / plugin proxy forwards structured request
  -> POST /api/memories/search validates bounded facets
  -> server derives AccessScope.user_id from auth principal
  -> SearchEngine retrieves candidates through vector/BM25/graph
  -> RelationalStore applies authoritative post-fusion facet checks
  -> SQLite, HANA, and future stores implement the same source/date-facet contract
```

Search channels may over-retrieve, but no channel can bypass visibility or facet rules. The final relational check is authoritative because a memory can have multiple supporting sources and one vector row cannot encode that relationship safely.

## Validation Rules

- `source_filter` is optional.
- Empty lists are treated like omitted facets.
- `source_types` must match registered source types exactly.
- `clients` must match known client ids exactly.
- The local proxy may auto-detect an active repo identifier for ranking
  affinity, but auto-detection never populates `source_filter.repo_identifiers`
  unless the MCP caller explicitly asks for `current_repo_only`.
- Request bodies cannot provide `user_id` or `owner_user_id`; private memory access is always server-principal-derived.
- `source_updated_at` filters provenance rows. It only matches memories with a
  source/provenance row whose source facet and date window both match that same
  row. Memories without provenance rows do not match this mode.
- `memory_updated_at` filters the MemForge memory lifecycle row. It does not
  require a provenance row.
- MemForge does not infer temporal intent from the query string. If the user
  says "from last week", the agent must convert that phrase to explicit dates.

## Examples

Search all visible memory:

```json
{"query": "how did we fix the scheduler issue"}
```

Search recent agent-session memory from the current repo:

```json
{
  "query": "scheduler fix decisions from the last week",
  "time_range": {
    "date_type": "memory_updated_at",
    "start_date": "2026-06-11",
    "end_date": "2026-06-17"
  },
  "include_private": true,
  "source_filter": {
    "source_types": ["agent_session"],
    "current_repo_only": true
  }
}
```

Search Claude Code session memories only:

```json
{
  "query": "UI review feedback",
  "source_filter": {
    "source_types": ["agent_session"],
    "clients": ["claude-code"]
  }
}
```
