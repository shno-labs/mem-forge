"""Seed deterministic SQLite corpora from retrieval golden fixture manifests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from memforge.models import DocumentRecord, Memory, content_hash
from memforge.storage.database import Database


FIXED_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


async def seed_sqlite_fixture(
    *,
    db_path: Path,
    fixture: Mapping[str, Any],
) -> Database:
    """Create a SQLite database and seed one golden fixture."""

    db = Database(str(db_path))
    await db.connect()
    try:
        await _seed_sources(db, fixture)
        await _seed_documents(db, fixture)
        await _seed_memories(db, fixture)
        await _seed_memory_sources(db, fixture)
        await _seed_source_subscriptions(db, fixture)
    except Exception:
        await db.close()
        raise
    return db


async def _seed_sources(db: Database, fixture: Mapping[str, Any]) -> None:
    for source in fixture.get("sources") or ():
        await db.upsert_source(
            str(source["id"]),
            str(source.get("type") or "generic"),
            str(source.get("name") or source["id"]),
            json.dumps(source.get("config") or {}),
            status=str(source.get("status") or "active"),
        )


async def _seed_documents(db: Database, fixture: Mapping[str, Any]) -> None:
    for document in fixture.get("documents") or ():
        doc_id = str(document["doc_id"])
        await db.upsert_document(
            DocumentRecord(
                doc_id=doc_id,
                source=str(document["source_id"]),
                source_url=str(document.get("source_url") or f"https://eval.example/{doc_id}"),
                title=str(document.get("title") or doc_id),
                space_or_project=str(document.get("space_or_project") or ""),
                author=str(document.get("author") or "eval"),
                last_modified=FIXED_NOW,
                labels=list(document.get("labels") or ()),
                version=str(document.get("version") or "1"),
                content_hash=str(document.get("content_hash") or f"h-{doc_id}"),
                token_count=int(document.get("token_count") or 1),
                raw_content_uri=None,
                raw_content_type="text/plain",
                normalized_content_uri=None,
                pdf_content_uri=None,
                last_synced=FIXED_NOW,
                client=document.get("client"),
            )
        )


async def _seed_memories(db: Database, fixture: Mapping[str, Any]) -> None:
    for memory in fixture.get("memories") or ():
        memory_id = str(memory["id"]) if isinstance(memory, Mapping) else str(memory)
        content = str(
            memory.get("content")
            if isinstance(memory, Mapping) and memory.get("content") is not None
            else f"Evaluation memory {memory_id}."
        )
        await db.insert_memory(
            Memory(
                id=memory_id,
                memory_type=str(memory.get("memory_type") or "fact") if isinstance(memory, Mapping) else "fact",
                content=content,
                content_hash=content_hash(content),
                confidence=float(memory.get("confidence") or 0.9) if isinstance(memory, Mapping) else 0.9,
                project_key=memory.get("project_key") if isinstance(memory, Mapping) else None,
                status=str(memory.get("status") or "active") if isinstance(memory, Mapping) else "active",
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )


async def _seed_memory_sources(db: Database, fixture: Mapping[str, Any]) -> None:
    for support in fixture.get("memory_sources") or ():
        await db.add_memory_source(
            str(support["memory_id"]),
            str(support["doc_id"]),
            str(support.get("source_type") or "generic"),
            support.get("excerpt"),
            support_kind=str(support.get("support_kind") or "extracted"),
            source_updated_at=FIXED_NOW,
        )


async def _seed_source_subscriptions(db: Database, fixture: Mapping[str, Any]) -> None:
    for row in fixture.get("source_subscriptions") or ():
        await db.set_source_subscription(
            str(row["source_id"]),
            str(row["user_id"]),
            bool(row["enabled"]),
        )
