"""Two uploaders submit agent-session documents; the gene -> sync chain must
carry the uploader through normalization into the persistence pipeline.

This guards the production write path: receipt metadata alone is not enough,
because the gene re-reads the package and feeds the sync pipeline. The
normalized source_semantics has to expose the uploader so the sync pipeline can
forward it to the memory engine, instead of falling back to LOCAL_DEV_USER_ID.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from memforge.agent_sessions import submit_agent_session_document
from memforge.config import AppConfig
from memforge.genes.agent_session_gene import AgentSessionGene
from memforge.memory.audit import MemoryAuditLogger
from memforge.memory.engine import MemoryEngine
from memforge.memory.store import MemoryStore
from memforge.models import (
    DocumentRecord,
    RawMemory,
    SHARED_PROJECT_KEY,
    UNSORTED_PROJECT_KEY,
    Visibility,
)
from memforge.storage.adapters.context import LOCAL_DEV_USER_ID, AccessScope
from memforge.storage.adapters.sqlite import build_sqlite_adapters
from memforge.storage.database import Database


U1_USER = "u-1"
U2_USER = "u-2"


class FakeCollection:
    def query(self, **kwargs):
        return {"ids": [[]], "distances": [[]]}

    def upsert(self, ids=None, embeddings=None, metadatas=None, **kwargs):
        pass

    def delete(self, ids=None, **kwargs):
        pass


def _config(tmp_path: Path) -> AppConfig:
    cfg = AppConfig(base_dir=tmp_path / "mem")
    cfg.llm.enrichment_api_key = ""
    cfg.llm.embedding_api_key = ""
    return cfg


def _personalized_scope(user_id: str) -> AccessScope:
    return AccessScope(
        user_id=user_id,
        open_projects=frozenset({SHARED_PROJECT_KEY, UNSORTED_PROJECT_KEY}),
        member_projects=frozenset(),
        include_private=True,
        allowed_statuses=("active",),
        active_project=None,
        scope_mode="project-first",
    )


async def _document_for(database: Database, doc_id: str, source_id: str, source_url: str) -> None:
    now = datetime.now(timezone.utc)
    await database.upsert_document(DocumentRecord(
        doc_id=doc_id,
        source=source_id,
        source_url=source_url,
        title="t",
        space_or_project="PROJ",
        author="codex",
        last_modified=now,
        labels=[],
        version="1",
        content_hash=f"h-{doc_id}",
        token_count=1,
        raw_content_uri=None,
        raw_content_type="application/json",
        normalized_content_uri=None,
        pdf_content_uri=None,
        last_synced=now,
    ))


@pytest.fixture
async def engine_fixture(tmp_path, monkeypatch):
    database = Database(str(tmp_path / "sync_uploader.db"))
    await database.connect()
    adapters = build_sqlite_adapters(database, FakeCollection())
    store = MemoryStore(
        relational=adapters.relational,
        keyword=adapters.keyword,
        vector=adapters.vector,
        embed_cfg={},
        audit_logger=MemoryAuditLogger(database),
    )

    async def _fake_embed(text: str) -> list[float]:
        return [0.0]

    monkeypatch.setattr(store, "_embed", _fake_embed)
    engine = MemoryEngine(
        relational=adapters.relational,
        vector=adapters.vector,
        db=database,
        memory_store=store,
        structured_llm_client=None,
    )
    yield engine, database, adapters
    await database.close()


async def _submit_and_normalize(
    *,
    db: Database,
    cfg: AppConfig,
    client: str,
    session_id: str,
    user_id: str,
    fact: str,
):
    """Run the production write path and return (item, normalized, fact)."""
    submitted = await submit_agent_session_document(
        db=db,
        config=cfg,
        client=client,
        session_id=session_id,
        trigger="Stop",
        document_markdown=f"## Durable Findings\n- {fact}\n",
        workspace="/workspace/mem-forge",
        repo="mem-forge",
        branch="main",
        commit_sha="abc",
        history_window_kind="session",
        user_id=user_id,
    )
    source = await db.get_source(submitted["source_id"])
    gene = AgentSessionGene(config=source["config"], source_id=source["id"])

    items = [item async for item in gene.discover()]
    item = next(it for it in items if it.item_id == submitted["doc_id"])
    raw = await gene.fetch(item)
    normalized = await gene.normalize(raw)
    return submitted, item, normalized


@pytest.mark.asyncio
async def test_sync_carries_uploader_from_gene_normalize_into_persistence(
    engine_fixture, tmp_path
):
    """Each uploader's row stamps its own owner; LOCAL_DEV_USER_ID is never used."""
    engine, database, adapters = engine_fixture
    cfg = _config(tmp_path)

    submitted_u1, item_u1, normalized_u1 = await _submit_and_normalize(
        db=database,
        cfg=cfg,
        client="codex",
        session_id="sess-u1",
        user_id=U1_USER,
        fact="u1 deploys via argo",
    )
    submitted_u2, item_u2, normalized_u2 = await _submit_and_normalize(
        db=database,
        cfg=cfg,
        client="claude-code",
        session_id="sess-u2",
        user_id=U2_USER,
        fact="u2 deploys via flux",
    )

    # The normalize step must surface the uploader hint. Without this, the sync
    # pipeline cannot forward user_id to the memory engine, and the memory
    # silently falls back to LOCAL_DEV_USER_ID for both rows.
    assert normalized_u1.source_semantics.get("uploader_user_id") == U1_USER
    assert normalized_u2.source_semantics.get("uploader_user_id") == U2_USER

    # Stand in for the sync pipeline's persistence step: it reads the uploader
    # hint from source_semantics and passes it as user_id to process_memories.
    await _document_for(
        database, item_u1.item_id, submitted_u1["source_id"], item_u1.source_url
    )
    await _document_for(
        database, item_u2.item_id, submitted_u2["source_id"], item_u2.source_url
    )

    raw_u1 = [RawMemory(
        memory_type="fact",
        content="u1 deploys via argo",
        entity_refs=[],
        tags=[],
        confidence=0.9,
    )]
    raw_u2 = [RawMemory(
        memory_type="fact",
        content="u2 deploys via flux",
        entity_refs=[],
        tags=[],
        confidence=0.9,
    )]

    await engine.process_memories(
        doc_id=item_u1.item_id,
        raw_memories=raw_u1,
        source_type="agent_session",
        user_id=normalized_u1.source_semantics.get("uploader_user_id"),
    )
    await engine.process_memories(
        doc_id=item_u2.item_id,
        raw_memories=raw_u2,
        source_type="agent_session",
        user_id=normalized_u2.source_semantics.get("uploader_user_id"),
    )

    rows = await database.list_memories()
    by_content = {row.content: row for row in rows}
    u1_row = by_content["u1 deploys via argo"]
    u2_row = by_content["u2 deploys via flux"]

    assert u1_row.visibility == Visibility.PRIVATE.value
    assert u1_row.owner_user_id == U1_USER
    assert u1_row.owner_user_id != LOCAL_DEV_USER_ID
    assert u2_row.visibility == Visibility.PRIVATE.value
    assert u2_row.owner_user_id == U2_USER
    assert u2_row.owner_user_id != LOCAL_DEV_USER_ID

    # PERSONALIZED keyword search by U1 sees its own row but never U2's private row.
    u1_hits = await adapters.keyword.search(
        "deploys", _personalized_scope(U1_USER), memory_types=None, limit=10,
    )
    u1_ids = {mid for mid, _ in u1_hits}
    assert u1_row.id in u1_ids
    assert u2_row.id not in u1_ids

    u2_hits = await adapters.keyword.search(
        "deploys", _personalized_scope(U2_USER), memory_types=None, limit=10,
    )
    u2_ids = {mid for mid, _ in u2_hits}
    assert u2_row.id in u2_ids
    assert u1_row.id not in u2_ids
