"""build_sqlite_seam wires a Database plus collection into the three impls."""

from __future__ import annotations

import pytest

from memforge.storage.database import Database
from memforge.storage.seam.protocols import (
    KeywordSearch,
    RelationalStore,
    VectorStore,
)
from memforge.storage.seam.sqlite.factory import build_sqlite_seam


class FakeCollection:
    def query(self, **kwargs):
        return {"ids": [[]], "distances": [[]]}

    def upsert(self, **kwargs):
        pass

    def delete(self, **kwargs):
        pass

    def get(self, **kwargs):
        return {"ids": []}


@pytest.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "factory.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_build_sqlite_seam_returns_protocol_conforming_impls(db):
    seam = build_sqlite_seam(db, FakeCollection())
    assert isinstance(seam.relational, RelationalStore)
    assert isinstance(seam.keyword, KeywordSearch)
    assert isinstance(seam.vector, VectorStore)


@pytest.mark.asyncio
async def test_vector_handle_wraps_the_passed_collection(db):
    collection = FakeCollection()
    seam = build_sqlite_seam(db, collection)
    assert seam.vector.collection is collection
