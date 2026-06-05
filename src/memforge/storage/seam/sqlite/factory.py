"""One construction point for the SQLite seam bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from memforge.storage.database import Database
from memforge.storage.seam.sqlite.keyword import SqliteKeywordSearch
from memforge.storage.seam.sqlite.relational import SqliteRelationalStore
from memforge.storage.seam.sqlite.vector import SqliteVectorStore

__all__ = ["SqliteSeam", "build_sqlite_seam"]


@dataclass(frozen=True)
class SqliteSeam:
    """The three seam handles bound to one datastore."""

    relational: SqliteRelationalStore
    keyword: SqliteKeywordSearch
    vector: SqliteVectorStore


def build_sqlite_seam(db: Database, memory_collection: Any) -> SqliteSeam:
    """Bind a Database plus its memories Chroma collection into the seam."""
    return SqliteSeam(
        relational=SqliteRelationalStore(db),
        keyword=SqliteKeywordSearch(db),
        vector=SqliteVectorStore(memory_collection),
    )
