"""Tests for the agent-session source attribution repair script."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from memforge.agent_sessions import (
    agent_session_source_id,
    AGENT_SESSION_SOURCE_TYPE,
)
from memforge.models import AgentSessionReceipt, DocumentRecord
from memforge.storage.database import Database

from scripts.repair_agent_session_source_attribution import (
    repair_agent_session_source_attribution,
)


_LAST_MODIFIED = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def _doc_id(client: str, suffix: str) -> str:
    # Mirrors build_agent_session_doc_id: "agent-session-<client>-<sess>-<trigger>-<digest>".
    return f"agent-session-{client}-sess-{suffix}-stop-0123456789ab"


async def _seed_doc(db: Database, *, doc_id: str, source_id: str, client: str) -> None:
    await db.upsert_document(
        DocumentRecord(
            doc_id=doc_id,
            source=source_id,
            source_url=f"agent-session://{client}/sess/{doc_id}",
            title=f"Agent Session {doc_id}",
            space_or_project="mem-forge",
            author=client,
            last_modified=_LAST_MODIFIED,
            labels=[],
            version=f"v-{doc_id}",
            content_hash=f"hash-{doc_id}",
            token_count=100,
            raw_content_uri=None,
            raw_content_type="application/json",
            normalized_content_uri=None,
            pdf_content_uri=None,
            last_synced=_LAST_MODIFIED,
            client=client,
        )
    )


async def _seed_receipt(db: Database, *, doc_id: str, source_id: str, client: str) -> None:
    receipt = AgentSessionReceipt(
        doc_id=doc_id,
        source_id=source_id,
        client=client,
        session_id="sess",
        trigger="stop",
        workspace="/workspace/mem-forge",
        repo="mem-forge",
        branch="main",
        commit_sha="abc123",
        history_window_kind="session",
        history_window_start=None,
        history_window_end=None,
        submitted_at=_LAST_MODIFIED.isoformat(),
        document_hash=f"hash-{doc_id}",
        source_kind="generated_agent_summary",
        document_uri=f"/tmp/{doc_id}.json",
        metadata={},
        updated_at=_LAST_MODIFIED.isoformat(),
    )
    await db.upsert_agent_session_receipt(receipt)


async def _setup_seed(db: Database, tmp_path: Path) -> dict:
    """Seed a database with one correctly-attributed and one misfiled doc.

    Returns the source ids and doc ids for assertion lookups.
    """
    codex_source = agent_session_source_id("codex")
    claude_source = agent_session_source_id("claude-code")

    # Both per-client sources exist and start with bogus doc_count to verify
    # the repair recomputes from scratch.
    await db.upsert_source(
        id=codex_source,
        type=AGENT_SESSION_SOURCE_TYPE,
        name="Codex Session",
        config_json=json.dumps({"documents_dir": str(tmp_path), "client": "codex"}),
    )
    await db.upsert_source(
        id=claude_source,
        type=AGENT_SESSION_SOURCE_TYPE,
        name="Claude Code Session",
        config_json=json.dumps({"documents_dir": str(tmp_path), "client": "claude-code"}),
    )
    await db.update_source_doc_count(codex_source, 99)
    await db.update_source_doc_count(claude_source, 99)

    codex_doc = _doc_id("codex", "1")
    claude_doc = _doc_id("claude-code", "1")

    # The codex doc was misfiled under the claude-code source - this is the
    # "last writer wins" outcome of the original bug. The claude-code doc was
    # written correctly.
    await _seed_doc(db, doc_id=codex_doc, source_id=claude_source, client="codex")
    await _seed_receipt(db, doc_id=codex_doc, source_id=codex_source, client="codex")
    await _seed_doc(db, doc_id=claude_doc, source_id=claude_source, client="claude-code")
    await _seed_receipt(db, doc_id=claude_doc, source_id=claude_source, client="claude-code")

    return {
        "codex_source": codex_source,
        "claude_source": claude_source,
        "codex_doc": codex_doc,
        "claude_doc": claude_doc,
    }


async def _doc_source(db: Database, doc_id: str) -> str:
    async with db.db.execute(
        "SELECT source FROM documents WHERE doc_id = ?", (doc_id,)
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    return row[0]


async def _stored_doc_count(db: Database, source_id: str) -> int:
    async with db.db.execute(
        "SELECT doc_count FROM sources WHERE id = ?", (source_id,)
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


@pytest.mark.asyncio
async def test_repair_corrects_misfiled_source_and_recomputes_doc_counts(tmp_path: Path) -> None:
    db = Database(str(tmp_path / "repair.db"))
    await db.connect()
    try:
        seed = await _setup_seed(db, tmp_path)

        first = await repair_agent_session_source_attribution(db)

        assert first["corrected"] == 1
        assert first["misfiled_by_client"] == {"codex": 1}
        assert await _doc_source(db, seed["codex_doc"]) == seed["codex_source"]
        assert await _doc_source(db, seed["claude_doc"]) == seed["claude_source"]
        # Bogus seed counts get replaced by the recomputed values.
        assert await _stored_doc_count(db, seed["codex_source"]) == 1
        assert await _stored_doc_count(db, seed["claude_source"]) == 1
        assert first["after_counts"][seed["codex_source"]] == 1
        assert first["after_counts"][seed["claude_source"]] == 1

        second = await repair_agent_session_source_attribution(db)

        # Idempotency: nothing left to repair, counts stay where the first run
        # put them.
        assert second["corrected"] == 0
        assert second["misfiled_by_client"] == {}
        assert second["before_counts"] == second["after_counts"]
        assert await _doc_source(db, seed["codex_doc"]) == seed["codex_source"]
        assert await _stored_doc_count(db, seed["codex_source"]) == 1
        assert await _stored_doc_count(db, seed["claude_source"]) == 1
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_repair_leaves_non_agent_session_sources_untouched(tmp_path: Path) -> None:
    """A doc whose current source isn't an agent-session source is not rewritten.

    The repair only fixes the cross-pollination between per-client agent-session
    sources. Documents currently stamped with jira/confluence/etc. fall outside
    this bug and must be left alone.
    """
    db = Database(str(tmp_path / "repair-foreign.db"))
    await db.connect()
    try:
        codex_source = agent_session_source_id("codex")
        await db.upsert_source(
            id=codex_source,
            type=AGENT_SESSION_SOURCE_TYPE,
            name="Codex Session",
            config_json=json.dumps({"documents_dir": str(tmp_path), "client": "codex"}),
        )
        await db.upsert_source(
            id="src-jira-PROJ",
            type="jira",
            name="Jira PROJ",
            config_json=json.dumps({}),
        )

        codex_doc = _doc_id("codex", "1")
        # An agent-session-shaped doc whose current source is something
        # unrelated. Repair must leave the source value alone.
        await _seed_doc(db, doc_id=codex_doc, source_id="src-jira-PROJ", client="codex")
        await _seed_receipt(db, doc_id=codex_doc, source_id=codex_source, client="codex")

        report = await repair_agent_session_source_attribution(db)

        assert report["corrected"] == 0
        assert await _doc_source(db, codex_doc) == "src-jira-PROJ"
    finally:
        await db.close()
