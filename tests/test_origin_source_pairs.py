"""Storage-layer batched lookup of each memory's source pairs, used to pick the
leading source glyph in the admin UI without an N+1 query."""

from datetime import datetime, timezone

import pytest

from memforge.models import Memory, content_hash
from memforge.server.admin_api import _pick_origin_source_type
from memforge.storage.database import Database


@pytest.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "origin-source.db"))
    await database.connect()
    yield database
    await database.close()


def _memory(mem_id: str) -> Memory:
    now = datetime.now(timezone.utc)
    return Memory(
        id=mem_id,
        memory_type="fact",
        content=f"content for {mem_id}",
        content_hash=content_hash(mem_id),
        scope="project:PAY",
        project_key="PAY",
        tags=[],
        confidence=0.9,
        created_at=now,
        updated_at=now,
        status="active",
    )


async def _insert_doc(db: Database, doc_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.db.execute(
        """INSERT INTO documents
           (doc_id, source, source_url, title, space_or_project, last_modified, version, content_hash, last_synced)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (doc_id, "src", f"http://test/{doc_id}", doc_id, "PAY", now, "1", f"hash-{doc_id}", now),
    )
    await db.db.commit()


async def _add_source(
    db: Database, memory_id: str, doc_id: str, source_type: str, support_kind: str, added_at: str
) -> None:
    await _insert_doc(db, doc_id)
    await db.add_memory_source(memory_id, doc_id, source_type, "excerpt", support_kind=support_kind)
    # add_memory_source stamps added_at to now(); override it so ordering is testable.
    await db.db.execute(
        "UPDATE memory_sources SET added_at = ? WHERE memory_id = ? AND doc_id = ?",
        (added_at, memory_id, doc_id),
    )
    await db.db.commit()


async def test_empty_input_returns_empty_map(db: Database):
    assert await db.get_origin_source_pairs([]) == {}


async def test_groups_pairs_oldest_first_and_omits_sourceless(db: Database):
    for mem_id in ("mem-a", "mem-b", "mem-c"):
        await db.insert_memory(_memory(mem_id))
    # mem-a's corroborated jira source is added before its extracted confluence one.
    await _add_source(db, "mem-a", "doc-jira", "jira", "corroborated", "2026-01-01T00:00:00")
    await _add_source(db, "mem-a", "doc-conf", "confluence", "extracted", "2026-01-02T00:00:00")
    # mem-b has one source; mem-c has none.
    await _add_source(db, "mem-b", "doc-teams", "teams", "corroborated", "2026-01-01T00:00:00")

    pairs = await db.get_origin_source_pairs(["mem-a", "mem-b", "mem-c"])

    assert pairs["mem-a"] == [("jira", "corroborated"), ("confluence", "extracted")]
    assert pairs["mem-b"] == [("teams", "corroborated")]
    assert "mem-c" not in pairs

    # The extracted origin wins even though it was attached later.
    assert _pick_origin_source_type(pairs["mem-a"]) == "confluence"
    assert _pick_origin_source_type(pairs["mem-b"]) == "teams"
