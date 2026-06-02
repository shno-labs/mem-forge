# Jira browser-session: client-side capture and proactive refresh

Date: 2026-06-03
Status: designed (pending implementation)
Scope: `src/memforge/auth/` (split), `src/memforge/main.py` (`adapter auth jira` commands + new `watch`), `src/memforge/tool_client.py` (auth methods), `src/memforge/server/admin_api.py` (upload endpoint replaces server-side scrape), `cli/index.mjs` + `cli/tests/`, plus tests under `tests/`.

## Problem

Jira `browser_cookie` auth lets the server sync Jira as the user by presenting the user's browser session cookie. The capture path was built for a co-located deployment and breaks when the MemForge server is remote, because of two assumptions:

1. **The CLI writes to a local DB.** `memforge adapter auth jira refresh` runs `browser_session.refresh(db, ...)` against a DB opened locally via `_run_session_op` ([main.py:1442](../../../src/memforge/main.py)). On a remote deployment that DB is not the server's, so the captured cookie never reaches the server.
2. **The server scrapes the browser itself.** `POST /auth/jira-session/refresh` calls `JiraAuthSessionService.refresh_from_browser`, which runs `browser_cookie3` server-side and is gated by `_require_local_admin_request` ([admin_api.py:1665](../../../src/memforge/server/admin_api.py)). A remote server has no user browser to read, so the whole flow is unusable off-box.

On top of that, the session is detected as expired only reactively (at sync time), and the server-side "auto refresh from browser" fallback in `cookie_header_for_sync` cannot work remotely. The user wants expiry handled proactively, with capture driven from the client.

## Domain reality (what can and cannot be done)

In `browser_cookie` mode there is no token to refresh. MemForge stores a scraped copy of the user's Jira session cookie; the session lifetime is owned by Jira and, for SSO, by the IdP. The backend cannot extend or renew it. The only proactive lever is **re-capture**: keep the server's stored copy fresh from the live browser before it goes stale.

Two consequences shape the design:

- **Re-capture must run where the browser is.** For a remote server that is the client machine. The server can never reach back to scrape.
- **The cookie must still live on the server.** Sync is server-initiated (the scheduler fires; the client is not in the loop at that moment), so the server must hold the latest cookie to use whenever it next syncs. The client's job is to keep that stored copy fresh.

## Decisions (settled in brainstorming)

1. **Capture is client-side.** The CLI on the user's machine owns browser access. The server stores and validates only; it never scrapes.
2. **Proactive mechanism is a persistent watch daemon.** `memforge adapter auth jira watch` re-captures on an interval and uploads.
3. **Validation is server-authoritative with a client pre-check.** The client runs a quick local `/myself` probe to avoid uploading an obviously-dead cookie; the server re-validates on store and owns the principal-identity / principal-change decision (it holds the stored history).
4. **Dead session: report expired, keep running, auto-heal.** When re-capture cannot produce a valid cookie, the daemon tells the server to mark the session expired (so sync stops hammering and status reflects reality), logs a "sign back into Jira" line, and keeps ticking. The next tick with a valid browser session re-captures and uploads. Notification is CLI/log only.

## Goals

- Capture, pre-validate, and proactive re-capture run entirely on the client CLI and work against a remote server.
- The server stores the cookie encrypted, validates authoritatively, and uses it at sync time, exactly as today, but receives it over an authenticated upload instead of scraping.
- The server no longer imports `browser_cookie3`.
- A clean module boundary: browser scraping (client) is separated from storage and validation (server), with a small shared core (origin canonicalization, provider/status constants, the validation probe).

## Non-goals

- **PAT mode is unchanged.** It never used the browser-session machinery. The token lives in the source config (`pat_encrypted`), the gene sends it as a bearer header ([jira_gene.py:134](../../../src/memforge/genes/jira_gene.py)), and `inject_cookie_for_source` is a no-op for it. This design does not touch it.
- **Teams is out of scope.** `teams_auth.py` has the same co-location shape; generalizing the split at the provider layer (so Teams benefits) is a follow-up (see Approach C in Follow-ups).
- **No OAuth / 3LO.** A real refresh-token flow is a separate, Cloud-oriented effort.

## Chosen approach (A): split capture from store/validate, joined by an upload endpoint

`jira_auth.py` today mixes four concerns: browser scraping, Jira validation, encrypted storage, and provider registration. The remote topology wants them on different sides of the wire. The split:

- **Client-only (scraping):** `extract_browser_cookie_header`, `_browser_loaders`, `_cookie_header_from_jar`, `_cookie_domain_matches`, `_cookie_path_matches`. Moves off the server; the server drops the `browser_cookie3` dependency.
- **Server-only (storage):** `JiraAuthSessionService`, `_redacted_status`, principal helpers, provider registration, the `auth_sessions` table, `encrypt_secret`.
- **Shared core:** `canonical_jira_origin`, the provider/status constants (`JIRA_AUTH_PROVIDER`, `JIRA_SESSION_*`), and `validate_jira_cookie_session` (server runs it authoritatively; client runs the same probe as a pre-check).
- **New seam:** `POST /auth/jira-session` (upload) replaces the server-side scrape. It accepts a cookie blob, validates, and stores.

### Module layout

| File | Responsibility | Side |
|---|---|---|
| `src/memforge/auth/jira_origin.py` (new) | `canonical_jira_origin`, provider + status constants, principal helpers | shared |
| `src/memforge/auth/jira_validate.py` (new) | `validate_jira_cookie_session` (the `/myself` probe) | shared |
| `src/memforge/auth/jira_auth.py` | `JiraAuthSessionService`, storage, `_redacted_status`, `register_provider` | server |
| `src/memforge/adapter/jira_capture.py` (new) | browser scraping helpers + `capture_jira_cookie(origin, browser)` + `pre_validate(origin, cookie)` + the watch-loop body | client |
| `src/memforge/auth/browser_session.py` | provider-agnostic ops, unchanged in shape | server |

The exact filenames are a detail for the plan; the boundary is the contract.

## Components and data flow

### 1. Client capture (one shot)

`capture_jira_cookie(origin, browser)`:

1. Scrape the browser cookie store for the origin (`extract_browser_cookie_header`).
2. Pre-validate with a lightweight `/myself` probe. On 401 / non-JSON / login-redirect, treat as "no valid session" and return a typed `no-session` result (do not upload).
3. Return `{cookie_header, browser_name, principal_preview}`.

### 2. Upload to the remote server

`ToolClient` gains auth methods that call the server over the already-configured target (`api_url` + bearer token, the same transport `kb push` uses):

- `get_jira_session(base_url)` -> `GET /auth/jira-session`
- `list_jira_origins()` -> `GET /auth/jira-origins`
- `upload_jira_session(base_url, cookie_header, browser, confirm_principal_change)` -> `POST /auth/jira-session`
- `forget_jira_session(base_url)` -> `DELETE /auth/jira-session`
- `mark_jira_session_expired(base_url, error)` -> `POST /auth/jira-session/expire`

### 3. Server endpoint (authoritative validate + store)

`POST /auth/jira-session`:

1. Enforce transport safety: reject if the request did not arrive over HTTPS and the client is not loopback (the cookie is a live credential).
2. `validate_jira_cookie_session(origin, cookie_header)` to get the authoritative principal. On failure, return 400 with a clear "session not accepted" message and mark the stored row expired.
3. Detect principal change against the stored row. If changed and `confirm_principal_change` is false, return 409 with `{origin, old_principal_id, new_principal_id}` (existing shape). If confirmed, reset affected sources, as `store_validated_session` already does.
4. `store_validated_session(...)` writes the encrypted cookie and active status.

`GET /auth/jira-session` (status) stays a passive read of the stored row. `GET /auth/jira-origins` returns `browser_session.list_origins(db, "jira")`. `DELETE /auth/jira-session` forgets. `POST /auth/jira-session/expire` marks the stored row expired (used by the daemon's dead-session path).

The old `POST /auth/jira-session/refresh` (server-side scrape) and `_require_local_admin_request` gating for it are removed.

### 4. Sync-time use (server, essentially unchanged)

`run_source_sync` -> `inject_cookie_for_source` -> `cookie_header_for_sync` -> gene reads `jira_cookie`. One change: `cookie_header_for_sync` no longer attempts a server-side browser re-capture on validation failure (it cannot, remotely). On failure it marks the row expired and raises; recovery now comes from the client daemon's next upload. `allow_browser_refresh` is dropped from that path.

### 5. Watch daemon (client)

`memforge adapter auth jira watch --base-url ... [--browser ...] [--interval-seconds N] [--confirm-principal-change]`:

Loop every `interval_seconds` (default `WATCH_DEFAULT_INTERVAL_SECONDS`, overridable via `--interval-seconds`, chosen shorter than a typical Jira idle timeout so the stored copy is renewed while still valid):

1. `capture_jira_cookie(origin, browser)`.
2. If a valid cookie is captured and its content hash differs from the last successful upload, `upload_jira_session(...)`. The server re-validates and stores. Cache the hash to avoid redundant uploads of an unchanged cookie.
3. If capture returns `no-session` (dead/expired/logged out): `mark_jira_session_expired(...)`, log "sign back into Jira in your browser", keep looping. A later tick with a valid session auto-heals.
4. On a 409 principal change: by default do not auto-confirm. Log the conflict and skip uploads for that origin until the operator re-runs `refresh`/`watch` with `--confirm-principal-change`.
5. On transport failure (server unreachable): exponential backoff up to a cap, then resume the normal interval. Never crash the loop on a transient error.

### 6. CLI commands (Python) repoint to the server

`adapter auth jira {status,list,forget}` switch from `_run_session_op` (local DB) to `_tool_client(ctx)` calls, because the server DB is the source of truth on a remote deployment. `refresh` becomes capture + pre-check + upload (one tick of the daemon). `watch` is the long-running loop.

### 7. Node CLI (`cli/index.mjs`)

The Jira area keeps `status` / `authenticate` / `forget` (now reflecting server state) and adds a "Start background refresh (watch)" action that launches the daemon, plus a short note on running it under a supervisor for persistence. `menu-shape.test.mjs` is updated for the new action.

## Error handling

- **Dead / expired session:** typed `no-session` from capture -> daemon marks expired, logs, keeps running, auto-heals. Sync sees `expired` and stops hammering.
- **Principal change:** server 409 with both principal ids; daemon does not auto-confirm; operator confirms explicitly.
- **Invalid cookie at upload:** server 400, stored row marked expired, clear message.
- **SSO redirect masking expiry:** `validate_jira_cookie_session` treats a non-JSON / login-page response as "not accepted" rather than letting it surface as an opaque JSON parse error, so both the client pre-check and the server probe report expiry cleanly. (This also fixes a gap found in the prior review.)
- **Transport failure:** daemon backs off and retries; one-shot `refresh` returns the `ToolClient` error payload, consistent with other adapter commands.

## Security

- The cookie is a live session credential. Upload only over the authenticated target channel (bearer token). Refuse to upload over plaintext HTTP to a non-loopback host.
- Never log the cookie value (log the principal and a content hash prefix only).
- The server continues to store the cookie encrypted (`encrypt_secret`) and to return only redacted status.

## Constants (no magic numbers)

Named constants, each with a clear reason:

- `WATCH_DEFAULT_INTERVAL_SECONDS` (daemon tick; chosen below a typical Jira idle timeout so the stored copy is renewed while still valid).
- `WATCH_BACKOFF_BASE_SECONDS` and `WATCH_BACKOFF_MAX_SECONDS` (transport-failure backoff bounds).
- `PRE_VALIDATE_TIMEOUT_SECONDS` (client `/myself` probe timeout).

## Testing strategy

- **Client capture:** unit tests for cookie filtering (expiry, domain, path, secure) and for `capture_jira_cookie` returning `no-session` on 401 / HTML-login responses, using a fake browser extractor and a fake HTTP probe.
- **Watch loop:** drive the loop body with a fake `ToolClient` and fake capture to assert: upload-on-change-only (hash cache), dead-session marks expired and continues, 409 pauses uploads, transport failure backs off. The loop body is a pure function of injected collaborators (no real sleeping in tests).
- **Server endpoint:** upload validates and stores; invalid cookie -> 400 + expired; principal change -> 409; HTTPS / loopback enforcement; status is a passive read; expire endpoint flips status.
- **Gene / sync:** `cookie_header_for_sync` marks expired and raises on validation failure without attempting a browser refresh.
- **Node CLI:** `menu-shape.test.mjs` covers the new watch action; `dependency-check.test.mjs` unchanged.
- Remove tests tied to the server-side scrape endpoint and `_require_local_admin_request` for jira-session.

## Migration and backward compatibility

- **Co-located installs still work.** Point the target at `http://127.0.0.1:<port>`; upload travels over loopback (allowed without HTTPS). Behavior is the same, now via the server API instead of a direct DB write. This makes auth ops consistent with the rest of `adapter`, which already requires a reachable target.
- **Removed:** server-side scrape (`refresh_from_browser` on the service and its endpoint), the `_require_local_admin_request` gate for jira-session, and the local-DB `_run_session_op` path for the auth group.
- No DB schema change: `auth_sessions` is reused as-is.

## Follow-ups (out of scope here)

- **Approach C:** push the client/server split into the provider-agnostic `browser_session` layer so Teams (`teams_auth.py`) gets client-side capture for free.
- **Supervisor integration:** document running `watch` under launchd / systemd; do not build it.
- **OAuth / 3LO:** a true refresh-token flow for Atlassian Cloud.
