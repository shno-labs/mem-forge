# MemForge interactive CLI — clack redesign

Date: 2026-06-02
Status: implemented (pending review)
Scope: `cli/index.mjs`, `cli/tests/`, plus a small Python addition for end-to-end vault linking.

## Problem

`uv run memforge` with no subcommand spawns the clack menu in `cli/index.mjs`. The
menu is organized by plumbing, not by user intent, and three things hurt:

1. **"Configure local adapter" configures nothing.** Its handler only runs
   `adapter status` + `adapter kb list` and prints two notes, then loops back to
   the menu. The label promises configuration; the action is read-only. This is
   the reported "it did nothing."
2. **The markdown flow is split across three menu items.** "Configure markdown /
   Obsidian profile", "Preview local files", and "Push local files" are three
   sibling entries plus an abstract "Knowledge base" grouping. Setting up a vault
   and syncing it are the same concern presented as unrelated items.
3. **Push requires a hand-typed `--source-id`.** The local profile (folder +
   vault-id) and the server source (source-id) are joined manually by copying
   `src-abcd1234` out of the admin UI. This is the worst step in the flow.

The CLI also fights clack idiom: `spawnSync` wrapped in `spinner()` never
animates (the event loop is blocked), every prompt is individually wrapped in
`ensureNotCancelled` instead of using `group()`, and menu options carry no
`hint` text.

## Domain model (why the naming changes)

MemForge is a memory **service**. Most sources sync server-side. The local CLI
adapter exists only for sources the server cannot reach itself:

- **Markdown / Obsidian vault** — files on the user's disk. The CLI scans the
  folder and pushes each note into a `local_markdown` source's inbox.
- **Jira** — the server cannot log into Jira as the user, so the CLI hands over
  the user's local browser session.

Everything else (search, extraction, review) belongs to the server. The menu
should name these jobs, not the `adapter`/`kb`/`auth` command tree.

## Goals

- Each menu item has one clear responsibility a user can name.
- Setting up and syncing a markdown vault live in one area.
- A guided wizard sets up a vault end-to-end: pick folder, link to MemForge,
  first sync, with no hand-typed source-id.
- Apply clack idiom: `group()`, `tasks()`, option `hint`s, `maxItems`, async
  shell-out so spinners animate.

## Non-goals

- No change to extraction, review, or memory storage.
- No new source types beyond the two that already exist.
- The Node layer never reimplements scriptable behavior; it composes `memforge`
  subcommands. New behavior is added as Python subcommands the wizard calls.

## Menu structure (two-tier)

Top level, "Choose an area", every option carries a `hint`:

```
MemForge
  Connect a MemForge server      where your memories are stored        target add/use/check
  Markdown & Obsidian notes      sync a local folder into memory       adapter kb …
  Jira                           let the server sync Jira as you       adapter auth jira
  Search memory                  find stored facts and decisions       memory search
  Status & diagnostics           connection, capabilities, sources     adapter status, target check
  Quit
```

**Connect a MemForge server**
- Connect a server (wizard: name, API URL, token env, optional health check) — `target add` + `target use` + `target check`
- Switch active server — `target use`, options populated from `target list`
- Health check — `target check`
- ← Back

**Markdown & Obsidian notes**
- Set up a vault… — the guided wizard (below)
- Sync now — `adapter kb push <name>` with no source-id prompt (read from profile)
- Preview (dry run) — `adapter kb preview <name>`
- Manage vaults — list profiles (`adapter kb list`); edit = re-run setup (upsert via `adapter kb add`); remove = `adapter kb remove <name>`
- ← Back

**Jira**
- Authenticate browser session — `adapter auth jira` (keeps the principal-change confirm flow)
- ← Back

**Search memory**
- Search — `memory search`
- ← Back

**Status & diagnostics**
- Adapter capabilities & profiles — `adapter status` + `adapter kb list` (the old "Configure local adapter", renamed honestly)
- Run diagnostics — `adapter status` + `target check`
- ← Back

Navigation: the area loop and each action loop are `while (true)` around a
`select`; `← Back` returns to the area list. One shared `onCancel` handles
Ctrl-C everywhere.

## The "Set up a vault" wizard

Built with `group()` for the linear form and `tasks()` for shell-outs.

1. **Folder path** — `text`, placeholder `~/Obsidian/MyVault`. `validate`
   expands `~`, confirms the path exists, is a directory, and is readable;
   otherwise returns an inline error and re-asks. If `<folder>/.obsidian` exists,
   note "Detected Obsidian vault **<name>**" and pre-fill the vault name.
2. **Instant feedback** — run `adapter kb scan --root <folder>` (a profile-free
   scan, below) and report "Found N markdown files (k skipped)". Zero matches
   warns and loops back; never silently accept an empty folder.
3. **Vault name** — `text`, default = folder basename, slug-validated. One line:
   "the id MemForge uses to address this vault."
4. **What to sync** — defaults, not raw globs: include `**/*.md`, auto-exclude
   `.obsidian/`, `.trash/`, templates. A single `confirm` "Customize include /
   exclude patterns?" gates the advanced globs (progressive disclosure).
5. **Link to MemForge** — if a server target is connected: run
   `adapter kb add <name> --root … --vault-id … --create-source`. That command
   writes the profile, then creates **or reuses** a `local_markdown` source whose
   `vault_id` matches, and records the returned `source_id` into the profile. If
   no target is connected: write the profile only and show the exact `vault_id`
   to enter in the admin UI (graceful fallback).
6. **First sync** — `adapter kb preview` counts → `confirm` "Push N notes now?" →
   `adapter kb push <name>` (real animated spinner via async spawn) → result
   summary and any failures → optional `confirm` "trigger extraction now?"
   (`--process-now`).
7. **Done** — summary `note`: vault, folder, source-id, count pushed. "Run **Sync
   now** anytime."

After setup, **Sync now** needs zero typing: root, vault-id, globs, and
source-id all live in the profile.

## Python additions (end-to-end linking)

`tool_client.py`:
- `create_source(type, name, config) -> dict` → `POST /api/sources`.
- `list_sources() -> list[dict]` → `GET /api/sources` (returns `data`), used to
  find an existing `local_markdown` source by `config.vault_id` before creating
  a duplicate. `vault_id` survives config redaction (not a secret).

`main.py`:
- `adapter kb add` gains `--create-source/--no-create-source` (default
  `--no-create-source`, preserving current scriptable behavior) and
  `--display-label`. With `--create-source`, after writing the profile it
  reuses-or-creates the server source for the profile's `vault_id` and stores
  the returned `source_id` in the profile entry. JSON payload includes
  `source_id` and whether it was created or reused. Network failure reports a
  clear partial-success result (profile saved, source not linked).
- `adapter kb push` makes `--source-id` optional: fall back to the profile's
  stored `source_id`; if neither is present, raise a clear error pointing at
  "Set up a vault" / `--create-source`.
- `adapter kb scan --root <path> [--include … --exclude … --limit N]` — a
  profile-free dry scan returning the same counts/items shape as `preview`. Backs
  the wizard's instant-feedback step before any profile is saved.
- `adapter kb remove <name>` — delete a profile entry from `adapter.toml`.

Adapter config (`~/.memforge/adapter.toml`) `kb.<name>` entry gains an optional
`source_id` field.

## Clack patterns applied

- `runMemforge` becomes async: promise-wrapped `spawn` (not `spawnSync`) so
  `tasks()` / `spinner()` animate during the shell-out.
- `group({...}, { onCancel })` for every multi-field form; later steps read
  earlier answers via `({ results })`.
- `select` options carry `hint`; menus set `maxItems` so long lists scroll.
- One `onCancel` helper replaces the per-prompt `ensureNotCancelled` calls.
- `note` for summaries; `log.success` / `log.error` for outcomes (unchanged).

## Error handling

- Folder validation, empty-match, and unreadable paths are caught in the wizard
  with inline re-asks.
- `--create-source` network failure: profile is still saved; the wizard reports
  "vault saved, but couldn't reach the server to link it" and offers to retry or
  continue with the admin-UI fallback.
- Push failures list per-file `relative_path: error` as today.
- Ctrl-C anywhere: shared `onCancel` → `cancel()` + clean exit.

## Testing

- `cli/tests/menu-shape.test.mjs` — rewritten to assert the two-tier area →
  action structure, that each action routes to its `memforge` subcommand
  (`target add/use/check`, `adapter kb add/preview/push`, `adapter auth jira`,
  `memory search`, `adapter status`), the new `--create-source` wiring, and the
  preserved `MEMFORGE_NO_INTERACTIVE` / `MEMFORGE_CLI_BIN` guarantees.
- `cli/tests/dependency-check.test.mjs` — unchanged.
- Python `tests/test_local_adapter_api.py` / `tests/test_cli_agent_tools.py` —
  add coverage for `adapter kb add --create-source` (create and reuse paths) and
  `adapter kb push` reading `source_id` from the profile when `--source-id` is
  omitted. `create_source` / `list_sources` client methods get unit coverage.

## Files changed

- `cli/index.mjs` — rewritten around the area → action tree and clack idiom.
- `cli/tests/menu-shape.test.mjs` — rewritten for the new contract.
- `src/memforge/tool_client.py` — `create_source`, `list_sources`.
- `src/memforge/main.py` — `adapter kb add --create-source`, optional push
  source-id, profile `source_id`, new `adapter kb scan` and `adapter kb remove`.
- `tests/` — Python coverage for the above.

## Open questions

None blocking. The admin-UI deep-link fallback was deferred (chosen scope is
end-to-end without the deep link).
