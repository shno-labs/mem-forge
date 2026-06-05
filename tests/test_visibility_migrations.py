# tests/test_visibility_migrations.py
import pytest
from memforge.storage.database import Database


async def _columns(db, table):
    cols = []
    async with db.db.execute(f"PRAGMA table_info({table})") as cur:
        async for row in cur:
            cols.append(row[1])
    return cols


async def _indexes(db):
    names = []
    async with db.db.execute("PRAGMA index_list(memories)") as cur:
        async for row in cur:
            names.append(row[1])
    return names


@pytest.mark.asyncio
async def test_fresh_schema_has_visibility_columns_and_no_scope(tmp_path):
    db = Database(str(tmp_path / "m.db"))
    await db.connect()
    try:
        cols = await _columns(db, "memories")
        assert "visibility" in cols
        assert "owner_user_id" in cols
        assert "scope" not in cols
        idx = await _indexes(db)
        assert "idx_memories_access" in idx
        assert "idx_memories_owner" in idx
        assert "idx_memories_scope" not in idx
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_backfill_maps_legacy_scope_to_project_key(tmp_path):
    from memforge.models import SHARED_PROJECT_KEY, UNSORTED_PROJECT_KEY

    db = Database(str(tmp_path / "legacy.db"))
    await db.connect()  # fresh schema + all migrations already applied
    try:
        # Reconstruct the legacy condition the backfill targets: a dormant scope
        # column carrying project-style values, project_key not yet derived. Then
        # replay Migration 15 by clearing its schema_migrations row and re-running.
        await db.db.execute("ALTER TABLE memories ADD COLUMN scope TEXT")
        await db.db.execute(
            "INSERT INTO memories (id, memory_type, content, content_hash, visibility, project_key, scope) "
            "VALUES ('a','fact','x','h1','workspace',NULL,'project:ACME'),"
            "       ('b','fact','y','h2','workspace',NULL,'team'),"
            "       ('c','fact','z','h3','workspace',NULL,'source:42')"
        )
        await db.db.execute("DELETE FROM schema_migrations WHERE version = 15")
        await db.db.commit()

        await db._run_migrations()  # re-applies Migration 15 against the legacy rows

        rows = {}
        async with db.db.execute("SELECT id, project_key FROM memories") as cur:
            async for row in cur:
                rows[row[0]] = row[1]
        assert rows["a"] == "ACME"
        assert rows["b"] == SHARED_PROJECT_KEY
        assert rows["c"] == UNSORTED_PROJECT_KEY
    finally:
        await db.close()
