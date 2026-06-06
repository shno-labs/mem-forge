"""Repair misfiled agent-session source attribution.

Per-client agent-session sources used to share one documents_dir, so each
``AgentSessionGene`` rglobbed the entire shared directory and stamped foreign
clients' documents with its own source id. The gene now filters by
``receipt.client``, but documents written before that fix can still carry the
wrong source value. This one-shot script scans the documents table, detects
rows whose ``source`` does not match the canonical
``agent_session_source_id(client)`` for the doc's owning client, rewrites the
``source`` column, and recomputes ``sources.doc_count`` from the corrected
rows.

The script is idempotent: a second run finds no mismatches and leaves the
recomputed counts unchanged.

Owning client is taken from ``agent_session_receipts.client`` when present,
falling back to the doc_id prefix shape produced by
``build_agent_session_doc_id`` (``agent-session-<client_slug>-...``).
"""

from __future__ import annotations

import asyncio
import re
from typing import Iterable

from memforge.agent_sessions import (
    agent_session_client_for_source_id,
    agent_session_source_id,
)
from memforge.config import AppConfig
from memforge.storage.database import Database


# Documents whose owning client is recorded in agent_session_receipts use that
# value. For documents missing a receipt row we fall back to the doc_id, which
# build_agent_session_doc_id starts with "agent-session-<slugify(client)[:30]>".
_AGENT_SESSION_DOC_ID_PREFIX = "agent-session-"
_DOC_ID_CLIENT_PATTERN = re.compile(r"^agent-session-([a-z0-9-]+?)-[a-z0-9-]+-[a-z0-9-]+-[0-9a-f]{12}$")


async def _open_db(config: AppConfig) -> Database:
    db = Database(config.storage.db_path)
    await db.connect()
    return db


async def _load_doc_clients(db: Database) -> dict[str, str]:
    """Return {doc_id: client} for every agent-session document.

    Authoritative client lookup is the agent_session_receipts table. Documents
    that exist without a receipt row get their client inferred from the doc_id
    shape; rows whose doc_id does not match the expected pattern are skipped.
    """
    doc_clients: dict[str, str] = {}
    async with db.db.execute(
        "SELECT doc_id FROM documents WHERE doc_id LIKE ?",
        (f"{_AGENT_SESSION_DOC_ID_PREFIX}%",),
    ) as cursor:
        async for row in cursor:
            doc_id = row[0]
            doc_clients[doc_id] = ""

    async with db.db.execute(
        "SELECT doc_id, client FROM agent_session_receipts"
    ) as cursor:
        async for row in cursor:
            doc_id, client = row[0], row[1]
            if doc_id in doc_clients and client:
                doc_clients[doc_id] = client

    for doc_id, client in list(doc_clients.items()):
        if client:
            continue
        match = _DOC_ID_CLIENT_PATTERN.match(doc_id)
        if match:
            doc_clients[doc_id] = match.group(1)
        else:
            doc_clients.pop(doc_id, None)

    return doc_clients


async def _current_doc_sources(db: Database, doc_ids: Iterable[str]) -> dict[str, str]:
    """Return {doc_id: source} for the given doc_ids."""
    sources: dict[str, str] = {}
    doc_id_list = list(doc_ids)
    if not doc_id_list:
        return sources
    chunk_size = 500
    for start in range(0, len(doc_id_list), chunk_size):
        chunk = doc_id_list[start : start + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        async with db.db.execute(
            f"SELECT doc_id, source FROM documents WHERE doc_id IN ({placeholders})",
            chunk,
        ) as cursor:
            async for row in cursor:
                sources[row[0]] = row[1]
    return sources


async def _list_source_ids(db: Database) -> list[str]:
    ids: list[str] = []
    async with db.db.execute("SELECT id FROM sources") as cursor:
        async for row in cursor:
            ids.append(row[0])
    return ids


async def _count_documents_for_source(db: Database, source_id: str) -> int:
    async with db.db.execute(
        "SELECT COUNT(*) FROM documents WHERE source = ?", (source_id,)
    ) as cursor:
        row = await cursor.fetchone()
        return int(row[0]) if row else 0


async def _existing_source_doc_count(db: Database, source_id: str) -> int:
    async with db.db.execute(
        "SELECT doc_count FROM sources WHERE id = ?", (source_id,)
    ) as cursor:
        row = await cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0


async def repair_agent_session_source_attribution(db: Database) -> dict:
    """Run the repair against an open database; return a structured report."""
    doc_clients = await _load_doc_clients(db)
    current_sources = await _current_doc_sources(db, doc_clients.keys())

    misfiled: list[tuple[str, str, str, str]] = []  # (doc_id, client, current_source, expected_source)
    for doc_id, client in doc_clients.items():
        expected = agent_session_source_id(client)
        current = current_sources.get(doc_id)
        if current is None:
            continue
        if current != expected and agent_session_client_for_source_id(current) is not None:
            # Only rewrite when the current source is itself an agent-session
            # source. Documents stamped with a non-agent-session source (jira,
            # confluence, etc.) are left alone: they fall outside this bug.
            misfiled.append((doc_id, client, current, expected))

    misfiled_by_client: dict[str, int] = {}
    for _, client, _, _ in misfiled:
        misfiled_by_client[client] = misfiled_by_client.get(client, 0) + 1

    corrected = 0
    for doc_id, _client, _current, expected in misfiled:
        await db.db.execute(
            "UPDATE documents SET source = ? WHERE doc_id = ?",
            (expected, doc_id),
        )
        corrected += 1
    if corrected:
        await db.db.commit()

    source_ids = await _list_source_ids(db)
    before_counts: dict[str, int] = {}
    after_counts: dict[str, int] = {}
    for source_id in source_ids:
        before_counts[source_id] = await _existing_source_doc_count(db, source_id)
        real_count = await _count_documents_for_source(db, source_id)
        after_counts[source_id] = real_count
        if real_count != before_counts[source_id]:
            await db.update_source_doc_count(source_id, real_count)

    return {
        "misfiled_by_client": misfiled_by_client,
        "corrected": corrected,
        "before_counts": before_counts,
        "after_counts": after_counts,
        "agent_session_doc_total": len(doc_clients),
    }


def _format_report(report: dict) -> str:
    lines: list[str] = []
    lines.append("Agent-session source attribution repair")
    lines.append("=======================================")
    lines.append(f"Agent-session documents scanned: {report['agent_session_doc_total']}")
    if report["misfiled_by_client"]:
        lines.append("Misfiled documents detected (by owning client):")
        for client, count in sorted(report["misfiled_by_client"].items()):
            lines.append(f"  {client}: {count}")
    else:
        lines.append("Misfiled documents detected: 0")
    lines.append(f"Documents corrected this run: {report['corrected']}")
    lines.append("")
    lines.append("Per-source doc_count (before -> after):")
    for source_id in sorted(set(report["before_counts"]) | set(report["after_counts"])):
        before = report["before_counts"].get(source_id, 0)
        after = report["after_counts"].get(source_id, 0)
        marker = "" if before == after else "  *"
        lines.append(f"  {source_id}: {before} -> {after}{marker}")
    return "\n".join(lines)


async def _amain() -> None:
    config = AppConfig()
    db = await _open_db(config)
    try:
        report = await repair_agent_session_source_attribution(db)
    finally:
        await db.close()
    print(_format_report(report))


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
