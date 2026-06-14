from __future__ import annotations

from datetime import datetime, timezone

import pytest

from memforge.models import DocumentRecord, Memory, Visibility, content_hash
from memforge.storage.adapters.context import AccessScope
from memforge.storage.admin_memory import MemoryAdminListFilters
from memforge.storage.database import Database


def _memory(memory_id: str, content: str) -> Memory:
    now = datetime.now(timezone.utc)
    return Memory(
        id=memory_id,
        memory_type="fact",
        content=content,
        content_hash=content_hash(content),
        visibility=Visibility.WORKSPACE.value,
        owner_user_id=None,
        tags=[],
        created_at=now,
        updated_at=now,
        status="active",
    )


def _document(doc_id: str, source_id: str) -> DocumentRecord:
    now = datetime.now(timezone.utc)
    return DocumentRecord(
        doc_id=doc_id,
        source=source_id,
        source_url=f"https://example.test/{doc_id}",
        title=doc_id,
        space_or_project="PAY",
        author=None,
        last_modified=now,
        labels=[],
        version="1",
        content_hash=f"h-{doc_id}",
        token_count=None,
        raw_content_uri=None,
        raw_content_type=None,
        normalized_content_uri=None,
        pdf_content_uri=None,
        last_synced=now,
    )


@pytest.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "source-subscriptions.db"))
    await database.connect()
    yield database
    await database.close()


async def _seed_sources_and_memories(db: Database) -> None:
    for source_id in ("src-a", "src-b"):
        await db.upsert_source(
            id=source_id,
            type="confluence",
            name=source_id,
            config_json="{}",
        )
        await db.upsert_document(_document(f"doc-{source_id}", source_id))

    await db.insert_memory(_memory("mem-a", "A memory"))
    await db.insert_memory(_memory("mem-b", "B memory"))
    await db.add_memory_source("mem-a", "doc-src-a", "confluence")
    await db.add_memory_source("mem-b", "doc-src-b", "confluence")


@pytest.mark.asyncio
async def test_source_preferences_default_enabled_and_round_trip(db: Database):
    await db.upsert_source(
        id="src-a",
        type="confluence",
        name="A",
        config_json="{}",
    )

    assert await db.get_source_user_preference("src-a", "user-a") is None
    assert await db.list_disabled_source_ids_for_user("user-a") == []

    await db.set_source_user_preference("src-a", "user-a", False)
    assert await db.get_source_user_preference("src-a", "user-a") is False
    assert await db.list_disabled_source_ids_for_user("user-a") == ["src-a"]

    await db.set_source_user_preference("src-a", "user-a", True)
    assert await db.get_source_user_preference("src-a", "user-a") is True
    assert await db.list_disabled_source_ids_for_user("user-a") == []


@pytest.mark.asyncio
async def test_list_sources_for_user_marks_enabled_for_me(db: Database):
    await db.upsert_source("src-a", "confluence", "A", "{}")
    await db.upsert_source("src-b", "jira", "B", "{}")
    await db.set_source_user_preference("src-b", "user-a", False)

    rows = await db.list_sources_for_user("user-a")
    enabled_by_source = {row["id"]: row["enabled_for_me"] for row in rows}

    assert enabled_by_source == {"src-a": True, "src-b": False}


@pytest.mark.asyncio
async def test_memory_admin_page_filters_to_enabled_sources(db: Database):
    await _seed_sources_and_memories(db)
    await db.set_source_user_preference("src-b", "user-a", False)
    disabled_sources = await db.list_disabled_source_ids_for_user("user-a")

    page = await db.query_memory_admin_page(
        scope=AccessScope(
            user_id="user-a",
            include_private=False,
            allowed_statuses=("active",),
            active_project=None,
            scope_mode="project-first",
        ),
        filters=MemoryAdminListFilters(disabled_source_ids=tuple(disabled_sources)),
        limit=10,
        offset=0,
    )

    assert [memory.id for memory in page.memories] == ["mem-a"]
    assert page.total == 1


@pytest.mark.asyncio
async def test_source_preferences_removed_with_source(db: Database):
    await db.upsert_source("src-a", "confluence", "A", "{}")
    await db.set_source_user_preference("src-a", "user-a", False)

    await db.delete_source_cascade("src-a")

    assert await db.get_source_user_preference("src-a", "user-a") is None
