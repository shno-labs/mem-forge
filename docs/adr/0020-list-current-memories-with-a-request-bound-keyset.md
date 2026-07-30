# List current Memories with a request-bound keyset

Status: Accepted (2026-07-31)

MemForge exposes deterministic recent-Memory enumeration separately from
semantic search. `list_recent_memories` lists current active Memories whose
selected timestamp falls in one caller-resolved, timezone-qualified half-open
`[start_at, end_at)` UTC window. It never accepts or synthesizes a semantic
query, and it must not be described as a create/update/delete changelog.

## Runtime flow

1. The agent resolves the user's calendar intent into two RFC 3339 timestamps
   with explicit offsets and, when needed, resolves exact configured Source IDs
   through `list_sources`.
2. The service normalizes the window to UTC and applies visibility, active
   Memory status, optional Memory types, exact Source IDs, and the selected time
   field before pagination.
3. `source_updated_at` matches the Source ID and timestamp on the same active
   Support Provenance Projection row. A broad `source_updated_at` listing
   therefore includes only current Memories backed by active configured
   Sources. `memory_updated_at` reads the current Memory row and may include
   current direct/manual Memories without a Source row; an explicit Source
   filter still requires matching active Source support.
4. The relational adapter orders by the selected timestamp descending and then
   by Memory ID descending. The response returns an opaque cursor bound to the
   normalized filters, caller scope, first-page listing watermark, and last
   ordering key. Each result exposes that selected `matched_at` timestamp and
   does not invent a semantic relevance score for a deterministic listing.

The cursor is keyset pagination with a fixed upper watermark, not a database
MVCC snapshot. It prevents offset drift and gives non-overlapping continuation
pages while the matched read model is unchanged. `total_candidates` is exact
for each page read, not an immutable snapshot count. Concurrent in-place or
late-arriving Support Projection changes can change later membership; callers
that require convergence start a new listing after the current pass. We do not
add a version ledger or a server-side snapshot subsystem solely for this read.

An audit-grade change feed is a different product contract. It must derive
creates, updates, removals, and historical states from authoritative Source
Projection or provider delta lineage. Microsoft Graph similarly distinguishes
delta/change tracking from reading the currently existing collection:
<https://learn.microsoft.com/en-us/graph/delta-query-overview>.

The opaque cursor and explicit input schema follow the MCP tool contract:
<https://modelcontextprotocol.io/specification/2025-11-25/server/tools>.
The keyset-plus-point-in-time distinction follows Elasticsearch's pagination
guidance: `search_after` supplies the last sort values, while a true preserved
index snapshot requires a separate point-in-time resource:
<https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results>.

The existing queryless `search` path remains compatibility-only for this
release. It now honors Memory types and the same active-source semantics, but
retains its legacy offset pagination. Its description directs active-source
time listings to `list_recent_memories` and forbids filler queries such as
`updates` or `recent changes`.
