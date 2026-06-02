# Jira Client-Side Session Capture and Proactive Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Jira browser-session capture to the client CLI (with a proactive watch daemon) and make the remote server store/validate/use the cookie it receives over an authenticated upload endpoint, never scraping a browser itself.

**Architecture:** The browser-scraping helpers move from `jira_auth.py` into a new client-only module `jira_capture.py`, so the server stops importing `browser_cookie3`. The server's `JiraAuthSessionService` keeps storage and authoritative validation, exposed through new `/api/auth/jira-session*` endpoints. The client CLI (`adapter auth jira`) talks to those endpoints via `ToolClient`: `refresh` captures + pre-validates + uploads, and a new `watch` command loops that on an interval, marking the session expired and auto-healing when the browser session dies. PAT mode is untouched.

**Tech Stack:** Python 3.12, Click (CLI), FastAPI (admin API), httpx (Jira probe), urllib-based `ToolClient` (CLI to server), pytest + pytest-asyncio (`asyncio_mode=auto`), Node.js + `@clack/prompts` (interactive CLI), node:test.

**Spec:** `docs/superpowers/specs/2026-06-03-jira-client-side-session-refresh-design.md`

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `src/memforge/auth/jira_capture.py` | create | Client-only: browser cookie scraping + `capture_and_prevalidate`. Imports `browser_cookie3`. |
| `src/memforge/auth/jira_auth.py` | modify | Server: drop scraping + `browser_cookie3` import; harden `validate_jira_cookie_session`; replace `refresh_from_browser` with `store_uploaded_session`; drop server re-scrape in `cookie_header_for_sync`. |
| `src/memforge/auth/browser_session.py` | modify | Replace `refresh_from_browser` in the service Protocol + ops with `store_uploaded`. |
| `src/memforge/tool_client.py` | modify | Add Jira-session auth methods (status/list/upload/forget/expire). |
| `src/memforge/server/admin_api.py` | modify | Replace server-scrape `/jira-session/refresh` with `POST /jira-session` (upload); add list-origins, forget, expire; secure-or-loopback gate. |
| `src/memforge/main.py` | modify | Repoint `adapter auth jira {status,list,forget}` to `ToolClient`; `refresh` = capture+upload; add `watch` (tick + loop). |
| `cli/index.mjs` | modify | Add "Start background refresh (watch)" action in the Jira area. |
| `tests/test_jira_auth_sessions.py` | modify | Update imports for moved scraping fns; cover hardened validate + `store_uploaded_session`. |
| `tests/test_jira_capture.py` | create | Cover `capture_and_prevalidate` (good / no-session). |
| `tests/test_browser_session.py` | modify | Update fake service: `store_uploaded_session` replaces `refresh_from_browser`. |
| `tests/test_tool_client_jira_session.py` | create | Cover the new `ToolClient` auth methods against a stub server. |
| `tests/test_jira_session_api.py` | create | Cover the new endpoints via `TestClient`. |
| `tests/test_jira_watch_tick.py` | create | Cover the watch tick state machine with injected collaborators. |
| `cli/tests/menu-shape.test.mjs` | modify | Assert the new watch action exists. |
| `CHANGELOG.md` | modify | Note the behavior change. |

**Decision (lighter split than the spec's three-file ideal):** only the scraping helpers move to `jira_capture.py`. `validate_jira_cookie_session`, `canonical_jira_origin`, the status constants, and the error classes stay in `jira_auth.py`. The client may import those from `jira_auth.py`; only the *server* import of `browser_cookie3` is what must disappear, and it does because scraping leaves `jira_auth.py`.

---

## Task 1: Harden `validate_jira_cookie_session` against SSO login-page responses

A redirect-to-login expiry returns `200 + HTML`, which today surfaces as an opaque JSON parse error instead of a clean "session not accepted". Treat a non-JSON body (or a landed-on-login URL) as expiry.

**Files:**
- Modify: `src/memforge/auth/jira_auth.py:442-466`
- Test: `tests/test_jira_auth_sessions.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_jira_auth_sessions.py`:

```python
import httpx


def _transport(handler):
    return httpx.MockTransport(handler)


async def test_validate_treats_html_login_page_as_not_accepted(monkeypatch):
    from memforge.auth import jira_auth
    from memforge.auth.jira_auth import JiraAuthSessionMissingError, validate_jira_cookie_session

    def handler(request: httpx.Request) -> httpx.Response:
        # SSO often answers an expired session with a 200 HTML login page.
        return httpx.Response(200, text="<html><body>Log in</body></html>")

    real_async_client = httpx.AsyncClient

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = _transport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(jira_auth.httpx, "AsyncClient", patched_async_client)

    with pytest.raises(JiraAuthSessionMissingError):
        await validate_jira_cookie_session("https://jira.example.test", "SESSION=dead")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_jira_auth_sessions.py::test_validate_treats_html_login_page_as_not_accepted -v`
Expected: FAIL (currently raises `json.JSONDecodeError`, not `JiraAuthSessionMissingError`).

- [ ] **Step 3: Implement the hardening**

Replace the body of `validate_jira_cookie_session` (jira_auth.py:442-466) with:

```python
async def validate_jira_cookie_session(
    origin: str,
    cookie_header: str,
    tls_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a browser Cookie header against Jira and return the principal.

    A live session returns a JSON principal from ``/rest/api/2/myself``. An
    expired SSO session typically answers with a 200 HTML login page or a
    redirect to the IdP, so a non-JSON body is treated as "session not accepted"
    rather than surfacing as an opaque parse error.
    """
    headers = {
        "Accept": "application/json",
        "Cookie": cookie_header,
    }
    async with httpx.AsyncClient(
        base_url=canonical_jira_origin(origin),
        headers=headers,
        timeout=30.0,
        follow_redirects=True,
        verify=tls_verify(tls_config or {}),
    ) as client:
        response = await client.get("/rest/api/2/myself")
        if response.status_code == 401:
            raise JiraAuthSessionMissingError("Jira browser session is expired or not accepted")
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            raise JiraAuthSessionMissingError(
                "Jira returned a non-JSON response (likely a login page); the browser session is not accepted"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise JiraAuthSessionMissingError(
                "Jira /myself did not return JSON; the browser session is not accepted"
            ) from exc
        if not isinstance(data, dict) or not _principal_id(data):
            raise JiraAuthSessionError("Jira /myself response did not contain a stable principal")
        return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_jira_auth_sessions.py::test_validate_treats_html_login_page_as_not_accepted -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/memforge/auth/jira_auth.py tests/test_jira_auth_sessions.py
git commit -m "fix: treat Jira non-JSON /myself response as session-not-accepted"
```

---

## Task 2: Extract browser scraping into a client-only `jira_capture.py`

Move the scraping helpers out of `jira_auth.py` so the server stops importing `browser_cookie3`.

**Files:**
- Create: `src/memforge/auth/jira_capture.py`
- Modify: `src/memforge/auth/jira_auth.py` (remove scraping fns + `browser_cookie3` import + default `browser_extractor`)
- Modify: `tests/test_jira_auth_sessions.py` (import moved fns from `jira_capture`)

- [ ] **Step 1: Create `jira_capture.py` with the moved functions**

Create `src/memforge/auth/jira_capture.py` and move these verbatim from `jira_auth.py`: `extract_browser_cookie_header`, `_browser_loaders`, `_cookie_header_from_jar`, `_cookie_domain_matches`, `_cookie_path_matches`. Header:

```python
"""Client-side Jira browser-session capture.

This module runs on the user's machine (the CLI), where the signed-in browser
lives. It reads the local browser cookie store and produces a Cookie header for
exactly one Jira origin. The server never imports this module, so it never
depends on ``browser_cookie3``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from typing import Any
from urllib.parse import urlsplit

from memforge.auth.jira_auth import (
    JiraAuthSessionMissingError,
    canonical_jira_origin,
)

# (paste extract_browser_cookie_header, _browser_loaders, _cookie_header_from_jar,
#  _cookie_domain_matches, _cookie_path_matches here, unchanged)
```

- [ ] **Step 2: Remove the moved functions and the dependency from `jira_auth.py`**

In `jira_auth.py`: delete `extract_browser_cookie_header`, `_browser_loaders`, `_cookie_header_from_jar`, `_cookie_domain_matches`, `_cookie_path_matches`. Remove the now-unused imports (`from http.cookiejar import CookieJar`). In `JiraAuthSessionService.__init__`, drop the `browser_extractor` parameter and its default `extract_browser_cookie_header`:

```python
    def __init__(
        self,
        db: Database,
        *,
        session_validator: SessionValidator | None = None,
    ) -> None:
        self.db = db
        self._session_validator = session_validator or validate_jira_cookie_session
```

Leave `register_provider(...)` but change `service_factory=lambda db: JiraAuthSessionService(db)` (already matches the new signature). Keep `BrowserExtractor` type alias deletion for later if unused.

- [ ] **Step 3: Update the moved-function tests' imports**

In `tests/test_jira_auth_sessions.py`, change every `from memforge.auth.jira_auth import _cookie_header_from_jar` (and `extract_browser_cookie_header`, `_browser_loaders`) to import from `memforge.auth.jira_capture`. For example:

```python
def test_cookie_header_post_filters_domain_path_and_secure_scope():
    from memforge.auth.jira_capture import _cookie_header_from_jar
    ...
```

- [ ] **Step 4: Run tests to verify the move is clean**

Run: `uv run pytest tests/test_jira_auth_sessions.py -q`
Expected: PASS (all previously-passing scraping tests still pass via the new import path).

- [ ] **Step 5: Verify the server no longer imports browser_cookie3 transitively**

Run:

```bash
uv run python -c "import memforge.server.admin_api, sys; assert 'browser_cookie3' not in sys.modules, 'server still imports browser_cookie3'; print('server clean')"
```

Expected: prints `server clean`.

- [ ] **Step 6: Commit**

```bash
git add src/memforge/auth/jira_capture.py src/memforge/auth/jira_auth.py tests/test_jira_auth_sessions.py
git commit -m "refactor: move Jira browser scraping to client-only jira_capture module"
```

---

## Task 3: Add `capture_and_prevalidate` to `jira_capture.py`

The client's one-shot capture: scrape, then run a lightweight `/myself` pre-check so a dead cookie is never uploaded.

**Files:**
- Modify: `src/memforge/auth/jira_capture.py`
- Test: `tests/test_jira_capture.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_jira_capture.py`:

```python
from __future__ import annotations

import pytest

from memforge.auth.jira_auth import JiraAuthSessionMissingError


async def test_capture_and_prevalidate_returns_cookie_and_principal():
    from memforge.auth import jira_capture

    result = await jira_capture.capture_and_prevalidate(
        "https://jira.example.test",
        browser=None,
        extractor=lambda origin, browser: ("SESSION=good", "Chrome"),
        validator=lambda origin, cookie, tls_config=None: {"accountId": "user-1", "displayName": "Ann"},
    )
    assert result.cookie_header == "SESSION=good"
    assert result.browser == "Chrome"
    assert result.principal["accountId"] == "user-1"


async def test_capture_and_prevalidate_raises_when_session_dead():
    from memforge.auth import jira_capture

    async def dead_validator(origin, cookie, tls_config=None):
        raise JiraAuthSessionMissingError("not accepted")

    with pytest.raises(JiraAuthSessionMissingError):
        await jira_capture.capture_and_prevalidate(
            "https://jira.example.test",
            browser=None,
            extractor=lambda origin, browser: ("SESSION=dead", "Chrome"),
            validator=dead_validator,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_jira_capture.py -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'capture_and_prevalidate'`.

- [ ] **Step 3: Implement `capture_and_prevalidate`**

Add to `src/memforge/auth/jira_capture.py`:

```python
import inspect
from dataclasses import dataclass

from memforge.auth.jira_auth import validate_jira_cookie_session


@dataclass(frozen=True)
class JiraCaptureResult:
    origin: str
    cookie_header: str
    browser: str | None
    principal: dict[str, Any]


async def capture_and_prevalidate(
    base_url: str,
    *,
    browser: str | None = None,
    tls_config: dict[str, Any] | None = None,
    extractor: Callable[[str, str | None], tuple[str, str]] | None = None,
    validator: Callable[..., Any] | None = None,
) -> JiraCaptureResult:
    """Scrape the local browser cookie for one Jira origin and pre-validate it.

    Raises ``JiraAuthSessionMissingError`` when no live session can be captured,
    so the caller never uploads a dead cookie.
    """
    origin = canonical_jira_origin(base_url)
    extract = extractor or extract_browser_cookie_header
    validate = validator or validate_jira_cookie_session

    cookie_header, browser_name = extract(origin, browser)
    result = validate(origin, cookie_header, tls_config)
    principal = await result if inspect.isawaitable(result) else result
    return JiraCaptureResult(
        origin=origin,
        cookie_header=cookie_header,
        browser=browser_name,
        principal=principal,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_jira_capture.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/memforge/auth/jira_capture.py tests/test_jira_capture.py
git commit -m "feat: add client-side capture_and_prevalidate for Jira sessions"
```

---

## Task 4: Replace `refresh_from_browser` with `store_uploaded_session` and drop the server re-scrape

The service validates an uploaded cookie authoritatively and stores it. It no longer scrapes a browser, and sync no longer tries to.

**Files:**
- Modify: `src/memforge/auth/jira_auth.py` (`JiraAuthSessionService`)
- Test: `tests/test_jira_auth_sessions.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_jira_auth_sessions.py`:

```python
async def test_store_uploaded_session_validates_and_stores(db):
    from memforge.auth.jira_auth import JiraAuthSessionService

    service = JiraAuthSessionService(
        db,
        session_validator=lambda origin, cookie, tls_config=None: {"accountId": "user-123", "displayName": "Ann"},
    )
    status = await service.store_uploaded_session(
        base_url="https://jira.example.test",
        cookie_header="SESSION=good",
        browser="Chrome",
    )
    assert status["status"] == "active"
    assert status["principal_id"] == "user-123"


async def test_cookie_header_for_sync_marks_expired_without_rescrape(db):
    from memforge.auth.jira_auth import JiraAuthSessionMissingError, JiraAuthSessionService

    good = JiraAuthSessionService(
        db,
        session_validator=lambda origin, cookie, tls_config=None: {"accountId": "user-123"},
    )
    await good.store_uploaded_session(base_url="https://jira.example.test", cookie_header="SESSION=good", browser=None)

    def dead_validator(origin, cookie, tls_config=None):
        raise JiraAuthSessionMissingError("expired")

    expiring = JiraAuthSessionService(db, session_validator=dead_validator)
    with pytest.raises(JiraAuthSessionMissingError):
        await expiring.cookie_header_for_sync("https://jira.example.test")
    status = await expiring.get_status("https://jira.example.test")
    assert status["status"] == "expired"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_jira_auth_sessions.py::test_store_uploaded_session_validates_and_stores tests/test_jira_auth_sessions.py::test_cookie_header_for_sync_marks_expired_without_rescrape -v`
Expected: FAIL (`store_uploaded_session` undefined; `cookie_header_for_sync` still attempts a browser refresh).

- [ ] **Step 3: Replace `refresh_from_browser` and trim `cookie_header_for_sync`**

In `jira_auth.py`, delete `refresh_from_browser` (lines 188-211) and add:

```python
    async def store_uploaded_session(
        self,
        *,
        base_url: str,
        cookie_header: str,
        browser: str | None = None,
        tls_config: dict[str, Any] | None = None,
        confirm_principal_change: bool = False,
    ) -> dict[str, Any]:
        """Validate a client-uploaded cookie authoritatively, then store it."""
        origin = canonical_jira_origin(base_url)
        try:
            principal = await _maybe_await(self._session_validator(origin, cookie_header, tls_config))
        except JiraPrincipalChangedError:
            raise
        except Exception as exc:
            await self._record_failure(origin, str(exc), status=JIRA_SESSION_EXPIRED)
            raise JiraAuthSessionError(str(exc)) from exc
        return await self.store_validated_session(
            base_url=origin,
            cookie_header=cookie_header,
            principal=principal,
            browser=browser,
            confirm_principal_change=confirm_principal_change,
        )
```

In `cookie_header_for_sync`, change the signature default and remove the re-scrape branches. Replace the method body (jira_auth.py:213-267) with:

```python
    async def cookie_header_for_sync(
        self,
        base_url: str,
        *,
        tls_config: dict[str, Any] | None = None,
    ) -> str:
        origin = canonical_jira_origin(base_url)
        stored = await self.db.get_auth_session(JIRA_AUTH_PROVIDER, origin)
        if not stored:
            raise JiraAuthSessionMissingError(
                f"No Jira browser session is available for {origin}. "
                "Sign in to Jira in your browser, then run `memforge adapter auth jira refresh`."
            )

        try:
            cookie_header = decrypt_secret(stored["secret_encrypted"])
            principal = await _maybe_await(self._session_validator(origin, cookie_header, tls_config))
        except Exception as exc:
            await self.db.mark_auth_session_status(
                provider=JIRA_AUTH_PROVIDER,
                origin=origin,
                status=JIRA_SESSION_EXPIRED,
                last_error=str(exc),
            )
            raise JiraAuthSessionMissingError(
                f"Jira browser session expired for {origin}. "
                "Sign in to Jira in your browser, then run `memforge adapter auth jira refresh`."
            ) from exc

        if stored.get("principal_id") and _principal_id(principal) != stored.get("principal_id"):
            await self.db.mark_auth_session_status(
                provider=JIRA_AUTH_PROVIDER,
                origin=origin,
                status=JIRA_SESSION_FAILED,
                last_error="Validated Jira principal changed during sync",
            )
            raise JiraPrincipalChangedError(origin, stored.get("principal_id"), _principal_id(principal))

        await self.db.mark_auth_session_status(
            provider=JIRA_AUTH_PROVIDER,
            origin=origin,
            status=JIRA_SESSION_ACTIVE,
            last_error=None,
        )
        return cookie_header
```

Then update the one caller in `browser_session.inject_cookie_for_source` (browser_session.py:182-186) to drop `allow_browser_refresh`:

```python
    config[descriptor.cookie_config_key] = await service.cookie_header_for_sync(
        str(config.get("base_url") or ""),
        tls_config=config,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_jira_auth_sessions.py -q`
Expected: PASS. (Delete or rewrite any old test that called `refresh_from_browser` with a `browser_extractor`; e.g. the `fail_extractor` tests at lines ~138-156 become `store_uploaded_session` failure tests: pass a `session_validator` that raises and assert `JiraAuthSessionError`.)

- [ ] **Step 5: Commit**

```bash
git add src/memforge/auth/jira_auth.py src/memforge/auth/browser_session.py tests/test_jira_auth_sessions.py
git commit -m "feat: server stores uploaded Jira cookie; sync marks expired without re-scrape"
```

---

## Task 5: Update the `browser_session` provider Protocol and ops

The generic ops surface `store_uploaded` (cookie in) instead of `refresh` (scrape).

**Files:**
- Modify: `src/memforge/auth/browser_session.py`
- Test: `tests/test_browser_session.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_browser_session.py`, update the fake service and add an ops test. Replace the fake's `refresh_from_browser` (line ~23) with:

```python
    async def store_uploaded_session(self, *, base_url, cookie_header, browser=None,
                                     tls_config=None, confirm_principal_change=False):
        self.uploaded = {"base_url": base_url, "cookie_header": cookie_header, "browser": browser}
        return {"provider": "jira", "origin": base_url, "status": "active"}
```

Add:

```python
async def test_store_uploaded_dispatches_to_service(db):
    from memforge.auth import browser_session
    # FakeProvider/registration as already set up in this file's fixtures.
    result = await browser_session.store_uploaded(
        db, "jira", base_url="https://jira.example.test", cookie_header="SESSION=x", browser="Chrome",
    )
    assert result["status"] == "active"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_browser_session.py::test_store_uploaded_dispatches_to_service -v`
Expected: FAIL (`browser_session.store_uploaded` undefined).

- [ ] **Step 3: Implement the Protocol + ops change**

In `browser_session.py`, in the `BrowserSessionService` Protocol replace the `refresh_from_browser` method with:

```python
    async def store_uploaded_session(
        self, *, base_url: str, cookie_header: str, browser: str | None = None,
        tls_config: dict | None = None, confirm_principal_change: bool = False,
    ) -> dict[str, Any]: ...
```

Replace the module-level `refresh(...)` function (lines 156-169) with:

```python
async def store_uploaded(
    db: Database,
    provider: str,
    *,
    base_url: str,
    cookie_header: str,
    browser: str | None = None,
    confirm_principal_change: bool = False,
) -> dict[str, Any]:
    descriptor = get_provider(provider)
    return await descriptor.service_factory(db).store_uploaded_session(
        base_url=base_url,
        cookie_header=cookie_header,
        browser=browser,
        confirm_principal_change=confirm_principal_change,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_browser_session.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/memforge/auth/browser_session.py tests/test_browser_session.py
git commit -m "refactor: browser_session ops expose store_uploaded instead of refresh"
```

---

## Task 6: Add Jira-session methods to `ToolClient`

The client reaches the remote server's auth endpoints over the configured target.

**Files:**
- Modify: `src/memforge/tool_client.py` (after `create_source`, around line 136)
- Test: `tests/test_tool_client_jira_session.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tool_client_jira_session.py`:

```python
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from memforge.tool_client import ToolClient


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence
        pass

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/auth/jira-session"):
            self._send(200, {"provider": "jira", "origin": "https://jira.example.test", "status": "active"})
        elif self.path == "/api/auth/jira-origins":
            self._send(200, {"origins": [{"origin": "https://jira.example.test", "status": "active"}]})
        else:
            self._send(404, {"error": "nope"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/auth/jira-session":
            self._send(200, {"provider": "jira", "origin": body["base_url"], "status": "active"})
        elif self.path == "/api/auth/jira-session/expire":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "nope"})


@pytest.fixture
def server():
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_tool_client_jira_session_round_trip(server):
    client = ToolClient(api_url=server, api_token=None)
    assert client.get_jira_session("https://jira.example.test")["status"] == "active"
    assert client.list_jira_origins()["origins"][0]["origin"] == "https://jira.example.test"
    up = client.upload_jira_session(base_url="https://jira.example.test", cookie_header="SESSION=x", browser="Chrome")
    assert up["status"] == "active"
    assert client.mark_jira_session_expired(base_url="https://jira.example.test", error="dead")["ok"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tool_client_jira_session.py -v`
Expected: FAIL (`ToolClient` has no `get_jira_session`).

- [ ] **Step 3: Implement the methods**

Add to `ToolClient` (tool_client.py, after `create_source`):

```python
    def get_jira_session(self, base_url: str) -> dict[str, Any]:
        return self._http_json("GET", f"/api/auth/jira-session?base_url={quote(base_url, safe='')}", None)

    def list_jira_origins(self) -> dict[str, Any]:
        return self._http_json("GET", "/api/auth/jira-origins", None)

    def upload_jira_session(
        self, *, base_url: str, cookie_header: str, browser: str | None = None,
        confirm_principal_change: bool = False,
    ) -> dict[str, Any]:
        return self._http_json(
            "POST",
            "/api/auth/jira-session",
            {
                "base_url": base_url,
                "cookie_header": cookie_header,
                "browser": browser,
                "confirm_principal_change": confirm_principal_change,
            },
        )

    def forget_jira_session(self, base_url: str) -> dict[str, Any]:
        return self._http_json("DELETE", f"/api/auth/jira-session?base_url={quote(base_url, safe='')}", None)

    def mark_jira_session_expired(self, *, base_url: str, error: str) -> dict[str, Any]:
        return self._http_json("POST", "/api/auth/jira-session/expire", {"base_url": base_url, "error": error})
```

`quote` is already imported in `tool_client.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tool_client_jira_session.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/memforge/tool_client.py tests/test_tool_client_jira_session.py
git commit -m "feat: ToolClient methods for remote Jira-session status/list/upload/forget/expire"
```

---

## Task 7: Server endpoints: upload (replace scrape), list-origins, forget, expire

**Files:**
- Modify: `src/memforge/server/admin_api.py` (models near 382; gate near 1239; routes near 1656-1699)
- Test: `tests/test_jira_session_api.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_jira_session_api.py`:

```python
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from memforge.auth import jira_auth
from memforge.config import AppConfig


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Force the authoritative validator to accept a fixed principal (no network).
    async def fake_validate(origin, cookie_header, tls_config=None):
        if cookie_header == "SESSION=good":
            return {"accountId": "user-123", "displayName": "Ann"}
        raise jira_auth.JiraAuthSessionMissingError("not accepted")

    monkeypatch.setattr(jira_auth, "validate_jira_cookie_session", fake_validate)

    from memforge.server.admin_api import create_admin_app

    cfg = AppConfig(base_dir=tmp_path / "mem")
    cfg.server.jwt_secret = "test-secret"
    app = create_admin_app(cfg)
    with TestClient(app) as c:
        yield c


def test_upload_then_status_then_forget(client):
    up = client.post(
        "/api/auth/jira-session",
        json={"base_url": "https://jira.example.test", "cookie_header": "SESSION=good", "browser": "Chrome"},
    )
    assert up.status_code == 200, up.text
    assert up.json()["status"] == "active"

    st = client.get("/api/auth/jira-session", params={"base_url": "https://jira.example.test"})
    assert st.json()["status"] == "active"

    origins = client.get("/api/auth/jira-origins")
    assert any(o["origin"] == "https://jira.example.test" for o in origins.json()["origins"])

    gone = client.request("DELETE", "/api/auth/jira-session", params={"base_url": "https://jira.example.test"})
    assert gone.json()["forgotten"] is True


def test_upload_rejects_dead_cookie(client):
    resp = client.post(
        "/api/auth/jira-session",
        json={"base_url": "https://jira.example.test", "cookie_header": "SESSION=dead"},
    )
    assert resp.status_code == 400


def test_expire_marks_status(client):
    client.post(
        "/api/auth/jira-session",
        json={"base_url": "https://jira.example.test", "cookie_header": "SESSION=good"},
    )
    client.post("/api/auth/jira-session/expire", json={"base_url": "https://jira.example.test", "error": "logged out"})
    st = client.get("/api/auth/jira-session", params={"base_url": "https://jira.example.test"})
    assert st.json()["status"] == "expired"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_jira_session_api.py -v`
Expected: FAIL (no `POST /api/auth/jira-session` route; old route is `/jira-session/refresh`).

- [ ] **Step 3: Add models and the secure-or-loopback gate**

Near the existing models (admin_api.py:382), add:

```python
class JiraSessionUploadRequest(BaseModel):
    base_url: str
    cookie_header: str
    browser: str | None = None
    confirm_principal_change: bool = False


class JiraSessionExpireRequest(BaseModel):
    base_url: str
    error: str = "client reported the session expired"
```

Add a gate near `_require_local_admin_request` (admin_api.py:1239):

```python
def _require_secure_or_loopback(request: Request) -> None:
    """A Jira session cookie is a live credential: only accept it over HTTPS or from loopback."""
    host = request.client.host if request.client else ""
    if host in {"127.0.0.1", "::1", "localhost", "testclient"}:
        return
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    if proto == "https":
        return
    raise HTTPException(status_code=400, detail="Upload a Jira session only over HTTPS or from localhost")
```

- [ ] **Step 4: Replace the refresh route and add the new routes**

Replace `refresh_jira_session` (admin_api.py:1665-1698) with the upload route, and add list/forget/expire. Keep imports `browser_session`, `JiraAuthSessionService`, `JiraAuthSessionError`, `JiraPrincipalChangedError`:

```python
    @auth_router.post("/jira-session", response_model=JiraSessionStatusResponse)
    async def upload_jira_session(
        req: JiraSessionUploadRequest,
        request: Request,
        db: Database = Depends(get_db),
        sync_service: SyncService = Depends(get_sync_service),
    ):
        """Store a client-captured Jira session cookie. The server validates it."""
        _require_secure_or_loopback(request)
        try:
            if req.confirm_principal_change:
                await _cancel_running_jira_browser_sources_for_origin(
                    db=db, sync_service=sync_service, base_url=req.base_url,
                )
            result = await JiraAuthSessionService(db).store_uploaded_session(
                base_url=req.base_url,
                cookie_header=req.cookie_header,
                browser=req.browser,
                confirm_principal_change=req.confirm_principal_change,
            )
        except JiraPrincipalChangedError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": str(exc),
                    "origin": exc.origin,
                    "old_principal_id": exc.old_principal_id,
                    "new_principal_id": exc.new_principal_id,
                },
            ) from exc
        except (JiraAuthSessionError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JiraSessionStatusResponse(**result)

    @auth_router.get("/jira-origins")
    async def list_jira_origins(db: Database = Depends(get_db)):
        """Known Jira origins: authenticated sessions plus configured sources."""
        origins = await browser_session.list_origins(db, "jira")
        return {"origins": origins}

    @auth_router.delete("/jira-session")
    async def forget_jira_session(base_url: str, db: Database = Depends(get_db)):
        """Delete the stored Jira session for an origin."""
        try:
            return await browser_session.forget(db, "jira", base_url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @auth_router.post("/jira-session/expire")
    async def expire_jira_session(req: JiraSessionExpireRequest, db: Database = Depends(get_db)):
        """Mark a Jira session expired (the client found the browser session dead)."""
        try:
            await JiraAuthSessionService(db).mark_expired(req.base_url, req.error)
            return {"ok": True}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
```

Remove the now-unused `JiraSessionRefreshRequest` model and the `_require_local_admin_request` helper if no other route uses them (grep first; see Task 10).

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_jira_session_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/memforge/server/admin_api.py tests/test_jira_session_api.py
git commit -m "feat: server endpoints to upload/list/forget/expire Jira sessions; drop server-side scrape"
```

---

## Task 8: Repoint `adapter auth jira` to the server and add `watch`

`status`/`list`/`forget` become `ToolClient` calls; `refresh` captures + uploads; `watch` loops a testable tick.

**Files:**
- Modify: `src/memforge/main.py` (`_make_browser_session_group`, lines 1454-1530; remove `_run_session_op` use here)
- Test: `tests/test_jira_watch_tick.py`

- [ ] **Step 1: Write the failing test for the watch tick**

Create `tests/test_jira_watch_tick.py`:

```python
from __future__ import annotations

import pytest

from memforge.auth.jira_auth import JiraAuthSessionMissingError


class _Client:
    def __init__(self, upload_result=None):
        self.uploaded = []
        self.expired = []
        self._upload_result = upload_result or {"status": "active"}

    def upload_jira_session(self, *, base_url, cookie_header, browser=None, confirm_principal_change=False):
        self.uploaded.append(cookie_header)
        return self._upload_result

    def mark_jira_session_expired(self, *, base_url, error):
        self.expired.append(error)
        return {"ok": True}


async def _capture_good(base_url, *, browser=None):
    from memforge.auth.jira_capture import JiraCaptureResult
    return JiraCaptureResult(origin=base_url, cookie_header="SESSION=good", browser="Chrome",
                             principal={"accountId": "u1"})


async def _capture_dead(base_url, *, browser=None):
    raise JiraAuthSessionMissingError("dead")


async def test_tick_uploads_changed_cookie():
    from memforge.main import run_watch_tick
    client = _Client()
    action, new_hash = await run_watch_tick(
        base_url="https://jira.example.test", browser=None, client=client,
        last_hash=None, capture=_capture_good, log=lambda m: None,
    )
    assert action == "uploaded"
    assert client.uploaded == ["SESSION=good"]
    assert new_hash is not None


async def test_tick_skips_unchanged_cookie():
    from memforge.main import run_watch_tick, _cookie_hash
    client = _Client()
    same = _cookie_hash("SESSION=good")
    action, new_hash = await run_watch_tick(
        base_url="https://jira.example.test", browser=None, client=client,
        last_hash=same, capture=_capture_good, log=lambda m: None,
    )
    assert action == "unchanged"
    assert client.uploaded == []
    assert new_hash == same


async def test_tick_marks_expired_when_session_dead():
    from memforge.main import run_watch_tick
    client = _Client()
    action, new_hash = await run_watch_tick(
        base_url="https://jira.example.test", browser=None, client=client,
        last_hash="abc", capture=_capture_dead, log=lambda m: None,
    )
    assert action == "expired"
    assert client.expired and new_hash is None


async def test_tick_flags_principal_conflict():
    from memforge.main import run_watch_tick
    client = _Client(upload_result={"error": "MemForge API request failed", "status_code": 409, "detail": "{}"})
    action, _ = await run_watch_tick(
        base_url="https://jira.example.test", browser=None, client=client,
        last_hash=None, capture=_capture_good, log=lambda m: None,
    )
    assert action == "principal_conflict"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_jira_watch_tick.py -v`
Expected: FAIL (`run_watch_tick` / `_cookie_hash` undefined).

- [ ] **Step 3: Implement the tick and the watch/command wiring**

In `main.py`, add near the auth group helpers:

```python
import hashlib

# Watch defaults. The tick interval is deliberately shorter than a typical Jira
# idle-session timeout so the stored copy is renewed while it is still valid.
WATCH_DEFAULT_INTERVAL_SECONDS = 1800  # 30 minutes
WATCH_BACKOFF_BASE_SECONDS = 5
WATCH_BACKOFF_MAX_SECONDS = 300  # 5 minutes


def _cookie_hash(cookie_header: str) -> str:
    return hashlib.sha256(cookie_header.encode("utf-8")).hexdigest()


async def run_watch_tick(*, base_url, browser, client, last_hash, capture, log):
    """One watch iteration. Returns (action, new_last_hash).

    action is one of: uploaded, unchanged, expired, principal_conflict, transport_error.
    Pure over its injected collaborators (capture, client, log) so it is unit-testable.
    """
    from memforge.auth.jira_auth import JiraAuthSessionMissingError

    try:
        result = await capture(base_url, browser=browser)
    except JiraAuthSessionMissingError as exc:
        client.mark_jira_session_expired(base_url=base_url, error=str(exc))
        log(f"Jira session for {base_url} is not active; sign back into Jira in your browser. ({exc})")
        return "expired", None

    new_hash = _cookie_hash(result.cookie_header)
    if new_hash == last_hash:
        return "unchanged", last_hash

    uploaded = client.upload_jira_session(
        base_url=base_url, cookie_header=result.cookie_header, browser=result.browser,
    )
    if uploaded.get("status_code") == 409:
        log(f"A different Jira user is signed in for {base_url}; re-run refresh with --confirm-principal-change.")
        return "principal_conflict", last_hash
    if uploaded.get("error"):
        log(f"Upload to MemForge failed: {uploaded.get('detail') or uploaded['error']}")
        return "transport_error", last_hash
    log(f"Refreshed Jira session for {base_url} (cookie {new_hash[:8]}).")
    return "uploaded", new_hash
```

Now rewrite `_make_browser_session_group` so `status`/`list`/`forget` use `_tool_client(ctx)` and add `refresh`/`watch` for Jira. Replace the body of the four existing subcommands and add `watch`:

```python
    @group.command("status")
    @click.option("--base-url", required=True)
    @click.pass_context
    def status_cmd(ctx, base_url):
        _emit_tool_payload(ctx, _tool_client(ctx).get_jira_session(base_url))

    @group.command("list")
    @click.pass_context
    def list_cmd(ctx):
        _emit_tool_payload(ctx, _tool_client(ctx).list_jira_origins())

    @group.command("forget")
    @click.option("--base-url", required=True)
    @click.pass_context
    def forget_cmd(ctx, base_url):
        _emit_tool_payload(ctx, _tool_client(ctx).forget_jira_session(base_url))

    @group.command("refresh")
    @click.option("--base-url", required=True)
    @click.option("--browser", default=None)
    @click.option("--confirm-principal-change", is_flag=True)
    @click.pass_context
    def refresh_cmd(ctx, base_url, browser, confirm_principal_change):
        """Capture the local browser session and upload it to the server."""
        from memforge.auth import jira_capture
        from memforge.auth.jira_auth import JiraAuthSessionMissingError

        async def _capture():
            return await jira_capture.capture_and_prevalidate(base_url, browser=browser)

        try:
            result = asyncio.run(_capture())
        except JiraAuthSessionMissingError as exc:
            _emit_tool_payload(ctx, {"error": "no_session", "detail": str(exc)})
            return
        payload = _tool_client(ctx).upload_jira_session(
            base_url=result.origin, cookie_header=result.cookie_header,
            browser=result.browser, confirm_principal_change=confirm_principal_change,
        )
        _emit_tool_payload(ctx, payload)

    @group.command("watch")
    @click.option("--base-url", required=True)
    @click.option("--browser", default=None)
    @click.option("--interval-seconds", type=int, default=WATCH_DEFAULT_INTERVAL_SECONDS, show_default=True)
    @click.pass_context
    def watch_cmd(ctx, base_url, browser, interval_seconds):
        """Keep the server's Jira session fresh by re-capturing on an interval."""
        from memforge.auth import jira_capture

        client = _tool_client(ctx)

        async def _capture(url, *, browser=None):
            return await jira_capture.capture_and_prevalidate(url, browser=browser)

        async def _loop():
            last_hash = None
            backoff = WATCH_BACKOFF_BASE_SECONDS
            while True:
                action, last_hash = await run_watch_tick(
                    base_url=base_url, browser=browser, client=client,
                    last_hash=last_hash, capture=_capture, log=click.echo,
                )
                if action == "transport_error":
                    await asyncio.sleep(min(backoff, WATCH_BACKOFF_MAX_SECONDS))
                    backoff = min(backoff * 2, WATCH_BACKOFF_MAX_SECONDS)
                    continue
                backoff = WATCH_BACKOFF_BASE_SECONDS
                await asyncio.sleep(interval_seconds)

        try:
            asyncio.run(_loop())
        except KeyboardInterrupt:
            click.echo("Stopped Jira session watch.")
```

Note: `refresh`/`watch` are Jira-specific (they import `jira_capture`). Since Jira is the only browser-session provider, build those two commands only when `descriptor.provider == "jira"`. Wrap the `refresh`/`watch` definitions in `if descriptor.provider == "jira":`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_jira_watch_tick.py -v`
Expected: PASS

- [ ] **Step 5: Verify the CLI wires up without error**

Run: `uv run memforge adapter auth jira --help`
Expected: lists `status`, `list`, `forget`, `refresh`, `watch`.

- [ ] **Step 6: Commit**

```bash
git add src/memforge/main.py tests/test_jira_watch_tick.py
git commit -m "feat: adapter auth jira talks to remote server; add capture refresh and watch daemon"
```

---

## Task 9: Add the "Start background refresh (watch)" action to the Node CLI

**Files:**
- Modify: `cli/index.mjs` (Jira area, around lines 583-620 and 703-712)
- Test: `cli/tests/menu-shape.test.mjs`

- [ ] **Step 1: Write the failing test**

In `cli/tests/menu-shape.test.mjs`, add an assertion that the Jira area exposes a `watch` action (match the file's existing assertion style). For example:

```javascript
test("jira area offers a background watch action", () => {
  const source = readFileSync(new URL("../index.mjs", import.meta.url), "utf8");
  assert.match(source, /value:\s*"watch"/);
  assert.match(source, /adapter auth jira watch/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cli && node --test tests/menu-shape.test.mjs`
Expected: FAIL (no `watch` value yet).

- [ ] **Step 3: Implement the action and menu entry**

In `cli/index.mjs`, add an action function near `actionAuthJira`:

```javascript
async function actionJiraWatch() {
  const baseUrl = await pickBrowserOrigin("jira", "Keep which Jira origin fresh?");
  if (!baseUrl) return;
  note(
    "The watch daemon runs in the foreground and re-captures your Jira session on a timer.\n" +
      "Run it in its own terminal (or under launchd/systemd) so it keeps the server's session fresh:\n\n" +
      `  memforge adapter auth jira watch --base-url ${baseUrl}`,
    "Background refresh",
  );
  const startNow = ensureNotCancelled(
    await confirm({ message: "Start it here now? (blocks this menu until you stop it)", initialValue: false }),
  );
  if (startNow) {
    log.info("Starting watch. Press Ctrl-C to stop and return to the menu.");
    await runMemforge(["adapter", "auth", "jira", "watch", "--base-url", baseUrl]);
  }
}
```

Add to the Jira area `actions` array (cli/index.mjs:707-711):

```javascript
      { value: "watch", label: "Start background refresh", hint: "keep the session fresh on a timer", run: actionJiraWatch },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cli && node --test tests/menu-shape.test.mjs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cli/index.mjs cli/tests/menu-shape.test.mjs
git commit -m "feat: interactive CLI can start the Jira session watch daemon"
```

---

## Task 10: Remove dead code, update CHANGELOG, full verification

**Files:**
- Modify: `src/memforge/main.py` (remove `_run_session_op` if now unused), `src/memforge/server/admin_api.py` (remove `_require_local_admin_request` / `JiraSessionRefreshRequest` if unused), `src/memforge/auth/jira_auth.py` (remove unused `BrowserExtractor` alias), `CHANGELOG.md`

- [ ] **Step 1: Find now-dead symbols**

Run:

```bash
cd /Users/i551096/Dev/mem-inception/.claude/worktrees/elastic-satoshi-af37e7
grep -rn "_run_session_op\|_require_local_admin_request\|JiraSessionRefreshRequest\|refresh_from_browser\|browser_session.refresh\b\|BrowserExtractor" src tests
```

Expected: only definitions remain, no live callers. Delete each symbol that has no remaining caller. If `_require_local_admin_request` still guards another route, leave it.

- [ ] **Step 2: Update CHANGELOG**

Add a line under the current unreleased section of `CHANGELOG.md`:

```markdown
- Jira browser-session capture now runs in the client CLI and uploads to the server over `POST /api/auth/jira-session`; the server no longer scrapes a browser. New `memforge adapter auth jira watch` keeps the session fresh proactively. PAT mode is unchanged.
```

- [ ] **Step 3: Run lint**

Run: `make lint`
Expected: clean (fix any unused-import warnings from the moves).

- [ ] **Step 4: Run the full Python suite**

Run: `make test`
Expected: PASS (no failures, no errors).

- [ ] **Step 5: Run the Node CLI tests**

Run: `cd cli && node --test tests/`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove server-side Jira scrape remnants; changelog for client-side capture"
```

---

## Self-Review

**Spec coverage:**
- Client-side capture -> Tasks 2, 3, 8 (`jira_capture.py`, `refresh`, `watch`).
- Watch daemon -> Task 8 (`run_watch_tick`, `watch_cmd`).
- Server-authoritative validation + client pre-check -> Task 1 (hardened validate, shared), Task 3 (client pre-check), Task 7 (server validates on upload).
- Dead-session report + keep running + auto-heal -> Task 8 tick (`expired` action marks server, loop continues; next good capture uploads).
- Cookie stays server-side + sync injection unchanged except no re-scrape -> Task 4 (`cookie_header_for_sync`), Task 5 (`inject_cookie_for_source` caller).
- Upload endpoint replaces scrape; list/forget/expire; secure-or-loopback -> Task 7.
- ToolClient transport reuse -> Task 6.
- PAT untouched -> no task touches `bearer_headers` / PAT config (verified by scope).
- HTTPS / loopback security -> Task 7 gate.
- Named constants (no magic numbers) -> Task 8 (`WATCH_*` with reasons).
- Teams out of scope -> not in any task.

**Placeholder scan:** every code step contains real code; commands have expected output. The only intentionally descriptive step is Task 2 Step 1's "paste ... unchanged", which refers to a verbatim move of named functions, not new logic.

**Type/name consistency:** `JiraCaptureResult` (fields `origin/cookie_header/browser/principal`) used in Tasks 3 and 8; `capture_and_prevalidate(base_url, *, browser, tls_config, extractor, validator)` used in Tasks 3 and 8; `store_uploaded_session(*, base_url, cookie_header, browser, tls_config, confirm_principal_change)` used in Tasks 4, 5, 7; `run_watch_tick(*, base_url, browser, client, last_hash, capture, log) -> (action, hash)` used in Task 8 tests and impl; endpoint paths `/api/auth/jira-session`, `/api/auth/jira-origins`, `/api/auth/jira-session/expire` consistent across Tasks 6 and 7; `ToolClient` method names consistent across Tasks 6 and 8.
