# Source List organization design

Status: approved for implementation

## Goal

Make newly created and frequently used Sources easy to find without replacing Project grouping or adding another hierarchy. The Source List adds personal pinning, search, and stable sorting while preserving the existing Source rows and actions.

## Product rules

1. Project remains the only semantic grouping. A list preference never changes Project binding, retrieval scope, source configuration, or another user's view.
2. A Pinned Source stays in its Project group. Pinned rows form the first partition of that group; unpinned rows form the second partition. A Source is rendered once.
3. `Newest added` is the default sort. It uses the persisted Source `created_at`, never `last_sync`, list position, or client observation time.
4. Search matches normalized Source name, displayed source type, and Project name. It retains Project groups that have matches and reports `matching / total` Source counts.
5. Search text and `Pinned only` are ephemeral view state. Pin state and sort choice are personal preferences and survive new sessions.
6. After successful creation, the new Source is focused, scrolled into view, and highlighted once. The highlight is transient and is not domain state.

## Ordering contract

For each refresh:

1. Filter Sources by the search text and `Pinned only` state.
2. Resolve the existing Project groups.
3. Partition each group into pinned and unpinned rows.
4. Apply the selected comparator independently to both partitions.
5. Render pinned rows followed by unpinned rows.
6. Break equal sort keys with normalized Source name, then Source id, so refreshes cannot shuffle rows.

Initial sort modes:

- `newest`: `created_at` descending.
- `name`: normalized Source name ascending.
- `recently_synced`: successful `last_sync` descending, with never-synced Sources last.

`Needs attention` is not part of the first implementation. It requires one canonical attention signal spanning sync failure, incomplete setup, authentication, and local-daemon readiness; inferring it independently in the list would create another stale status model.

## Persistence model

The workspace datastore owns two small user-preference relations:

### Source list pins

`source_list_pins`

- `user_id`
- `source_id`
- `pinned_at`
- primary key: `(user_id, source_id)`
- foreign key: `source_id -> sources.id` with delete cascade

`pinned_at` supplies deterministic ordering and audit/debug evidence; it is not a shared Source priority.

### Source list preferences

`source_list_preferences`

- `user_id` primary key
- `sort_mode`
- `updated_at`

Workspace identity is already established by the selected workspace datastore. Neither relation accepts caller identity from a request body; the authenticated principal supplies `user_id`.

Search text and `Pinned only` are intentionally absent from persistence.

## API contract

- Source list responses expose `created_at` and `pinned_for_me` for the authenticated viewer.
- `PUT /api/sources/{source_id}/pin` idempotently pins the Source for the viewer.
- `DELETE /api/sources/{source_id}/pin` idempotently unpins it.
- `GET /api/source-list/preferences` returns the viewer's sort mode and the default when no row exists.
- `PUT /api/source-list/preferences` accepts only the closed sort-mode enum.

OSS SQLite and Cloud HANA implement the same protocol, identity semantics, delete behavior, and response fields. Source deletion removes pins through referential cleanup before object-artifact cleanup proceeds.

## UI contract

- Search is a real search input with an accessible label and clear action.
- Sort is a single select/menu labelled by the active mode.
- The Pinned control shows the current count and toggles `Pinned only`.
- Pin is available in the row overflow. A pinned row also exposes a visible, directly actionable pin icon; unpinned rows do not gain a permanent extra control.
- Desktop and mobile share the same order and semantics. No drag handle is introduced.
- Empty search results explain which fields are searchable and preserve a clear-reset action.

## Rejected alternatives

- **Collection:** duplicates Project grouping and makes semantic destination indistinguishable from personal organization.
- **Global pinned section plus normal Project rows:** duplicates Sources and makes counts/actions ambiguous.
- **Moving pinned Sources out of Projects:** hides their semantic destination.
- **Shared manual order:** creates team-wide contention, weak mobile behavior, and a write for every reorder.
- **Sorting by last sync to approximate creation:** makes a new Source move after its first sync and is not the requested meaning.

## Extensibility

The view pipeline accepts additional comparators without changing pin or Project semantics. A future Saved View may persist a named combination of search/filter/sort settings, but it remains a presentation concept and cannot become a memory destination. A future attention sort must consume one shared source-attention contract rather than reconstructing errors in the UI.

## Prototype evidence

The approved throwaway prototype is `source-list-organization-prototype.html`, variant A: project-local pins, newest-first default, search, sorting, and pinned-only filtering. The prototype is evidence for the decision and must not be promoted directly into production code.
