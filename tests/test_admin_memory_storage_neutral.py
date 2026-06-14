from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from memforge.config import AppConfig
from memforge.models import Memory, SearchResult, content_hash
from memforge.server.admin_api import create_admin_app
from memforge.storage.adapters.context import AccessScope, LOCAL_DEV_USER_ID
from memforge.storage.admin_memory import (
    MemoryAdminListFilters,
    MemoryAdminQueryPage,
)


def _memory(memory_id: str) -> Memory:
    now = datetime.now(timezone.utc)
    return Memory(
        id=memory_id,
        memory_type="fact",
        content="Storage-neutral admin memory row.",
        content_hash=content_hash(memory_id),
        tags=["admin"],
        confidence=0.9,
        created_at=now,
        updated_at=now,
        status="active",
    )


def _config(tmp_path) -> AppConfig:
    cfg = AppConfig(base_dir=tmp_path / "memforge")
    cfg.llm.enrichment_api_key = ""
    cfg.llm.embedding_api_key = ""
    return cfg


def test_memory_list_route_uses_storage_neutral_admin_reader(tmp_path):
    class FakeAdminReader:
        def __init__(self) -> None:
            self.calls = []

        async def get_schedule_config(self) -> dict:
            return {"enabled": False}

        async def list_disabled_source_ids_for_user(self, user_id: str) -> list[str]:
            return []

        async def query_memory_admin_page(
            self,
            *,
            scope: AccessScope,
            filters: MemoryAdminListFilters,
            limit: int,
            offset: int,
        ) -> MemoryAdminQueryPage:
            self.calls.append((scope, filters, limit, offset))
            return MemoryAdminQueryPage(memories=[_memory("mem-neutral")], total=7)

        async def get_origin_source_pairs(self, memory_ids: list[str]):
            assert memory_ids == ["mem-neutral"]
            return {
                "mem-neutral": [
                    ("jira", "corroborated", None),
                    ("confluence", "extracted", None),
                ],
            }

    reader = FakeAdminReader()
    app = create_admin_app(db=reader, config=_config(tmp_path))

    with TestClient(app) as client:
        response = client.get(
            "/api/memories",
            params={
                "type": "fact",
                "status": "active",
                "source": "src-a",
                "project": "PAY",
                "search": "Payroll",
                "include_private": "true",
                "limit": 3,
                "offset": 2,
            },
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 7
    assert payload["limit"] == 3
    assert payload["offset"] == 2
    assert payload["data"][0]["id"] == "mem-neutral"
    assert payload["data"][0]["origin_source_type"] == "confluence"

    scope, filters, limit, offset = reader.calls[0]
    assert scope.user_id == LOCAL_DEV_USER_ID
    assert scope.include_private is True
    assert scope.allowed_statuses == ("active",)
    assert filters == MemoryAdminListFilters(
        memory_type="fact",
        status="active",
        source="src-a",
        disabled_source_ids=(),
        project="PAY",
        search="Payroll",
    )
    assert limit == 3
    assert offset == 2


def test_memory_list_route_uses_injected_principal_resolver(tmp_path):
    class FakeAdminReader:
        def __init__(self) -> None:
            self.scope: AccessScope | None = None

        async def get_schedule_config(self) -> dict:
            return {"enabled": False}

        async def list_disabled_source_ids_for_user(self, user_id: str) -> list[str]:
            return []

        async def query_memory_admin_page(
            self,
            *,
            scope: AccessScope,
            filters: MemoryAdminListFilters,
            limit: int,
            offset: int,
        ) -> MemoryAdminQueryPage:
            self.scope = scope
            return MemoryAdminQueryPage(memories=[], total=0)

        async def get_origin_source_pairs(self, memory_ids: list[str]):
            return {}

    reader = FakeAdminReader()
    app = create_admin_app(
        db=reader,
        config=_config(tmp_path),
        principal_resolver=lambda request: request.headers["x-cloud-user-id"],
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/memories",
            headers={"x-cloud-user-id": "cloud-user-1"},
            params={"include_private": "true"},
        )

    assert response.status_code == 200, response.text
    assert reader.scope is not None
    assert reader.scope.user_id == "cloud-user-1"


def test_memory_list_route_excludes_disabled_sources_for_principal(tmp_path):
    class FakeAdminReader:
        def __init__(self) -> None:
            self.filters: MemoryAdminListFilters | None = None

        async def get_schedule_config(self) -> dict:
            return {"enabled": False}

        async def list_disabled_source_ids_for_user(self, user_id: str) -> list[str]:
            assert user_id == "cloud-user-1"
            return ["src-b"]

        async def query_memory_admin_page(
            self,
            *,
            scope: AccessScope,
            filters: MemoryAdminListFilters,
            limit: int,
            offset: int,
        ) -> MemoryAdminQueryPage:
            self.filters = filters
            return MemoryAdminQueryPage(memories=[], total=0)

        async def get_origin_source_pairs(self, memory_ids: list[str]):
            return {}

    reader = FakeAdminReader()
    app = create_admin_app(
        db=reader,
        config=_config(tmp_path),
        principal_resolver=lambda request: request.headers["x-cloud-user-id"],
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/memories",
            headers={"x-cloud-user-id": "cloud-user-1"},
            params={"source": "src-b"},
        )

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0
    assert reader.filters is None

    with TestClient(app) as client:
        response = client.get(
            "/api/memories",
            headers={"x-cloud-user-id": "cloud-user-1"},
            params={"source": "src-a"},
        )

    assert response.status_code == 200, response.text
    assert reader.filters == MemoryAdminListFilters(source="src-a", disabled_source_ids=("src-b",))


def test_memory_search_route_excludes_disabled_sources_for_principal(tmp_path):
    class FakeAdminReader:
        async def get_schedule_config(self) -> dict:
            return {"enabled": False}

        async def list_disabled_source_ids_for_user(self, user_id: str) -> list[str]:
            assert user_id == "cloud-user-1"
            return ["src-b"]

        async def filter_ids_allowed_by_source_preferences(
            self,
            memory_ids: list[str],
            disabled_source_ids: tuple[str, ...],
        ) -> set[str]:
            assert memory_ids == ["mem-a", "mem-b"]
            assert disabled_source_ids == ("src-b",)
            return {"mem-a"}

    class FakeSearchEngine:
        def __init__(self) -> None:
            self.calls = []

        async def search(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "query_analysis": {
                    "is_temporal": False,
                    "detected_entities": [],
                    "strategies_used": [],
                },
                "results": [
                    SearchResult(
                        memory_id="mem-a",
                        memory_type="fact",
                        summary="Enabled source memory.",
                        confidence=0.9,
                        relevance_score=0.9,
                    ),
                    SearchResult(
                        memory_id="mem-b",
                        memory_type="fact",
                        summary="Disabled source memory.",
                        confidence=0.8,
                        relevance_score=0.8,
                    ),
                ],
                "total_candidates": 2,
                "retrieval_time_ms": 5,
            }

    class FakeRuntimeProvider:
        def __init__(self, engine: FakeSearchEngine) -> None:
            self.engine = engine

        async def build_search_engine(self, _db, _config, *, audit_logger=None):
            return self.engine

    reader = FakeAdminReader()
    search_engine = FakeSearchEngine()
    app = create_admin_app(
        db=reader,
        config=_config(tmp_path),
        principal_resolver=lambda request: request.headers["x-cloud-user-id"],
        runtime_provider=FakeRuntimeProvider(search_engine),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/memories/search",
            headers={"x-cloud-user-id": "cloud-user-1"},
            json={"query": "payroll"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [row["memory_id"] for row in payload["results"]] == ["mem-a"]
    assert payload["total_candidates"] == 1
    assert search_engine.calls[0]["sources"] is None

    with TestClient(app) as client:
        response = client.post(
            "/api/memories/search",
            headers={"x-cloud-user-id": "cloud-user-1"},
            json={"query": "payroll", "sources": ["src-b"]},
        )

    assert response.status_code == 200, response.text
    assert response.json()["results"] == []
    assert len(search_engine.calls) == 1


def test_stats_routes_exclude_disabled_sources_for_principal(tmp_path):
    class FakeAdminReader:
        def __init__(self) -> None:
            self.filters: list[MemoryAdminListFilters] = []

        async def get_schedule_config(self) -> dict:
            return {"enabled": False}

        async def list_disabled_source_ids_for_user(self, user_id: str) -> list[str]:
            assert user_id == "cloud-user-1"
            return ["src-b"]

        async def query_memory_admin_page(
            self,
            *,
            scope: AccessScope,
            filters: MemoryAdminListFilters,
            limit: int,
            offset: int,
        ) -> MemoryAdminQueryPage:
            assert scope.user_id == "cloud-user-1"
            assert scope.allowed_statuses == ("active", "superseded", "retired", "pending_review")
            assert limit == 0
            assert offset == 0
            self.filters.append(filters)
            if filters.memory_type == "fact":
                return MemoryAdminQueryPage(memories=[], total=2)
            if filters.memory_type:
                return MemoryAdminQueryPage(memories=[], total=0)
            if filters.status == "active":
                return MemoryAdminQueryPage(memories=[], total=2)
            if filters.status:
                return MemoryAdminQueryPage(memories=[], total=0)
            return MemoryAdminQueryPage(memories=[], total=2)

        async def get_all_entities(self):
            return [object()]

        async def list_sources_for_user(self, user_id: str) -> list[dict]:
            assert user_id == "cloud-user-1"
            return [
                {"id": "src-a", "enabled_for_me": True},
                {"id": "src-b", "enabled_for_me": False},
            ]

    reader = FakeAdminReader()
    app = create_admin_app(
        db=reader,
        config=_config(tmp_path),
        principal_resolver=lambda request: request.headers["x-cloud-user-id"],
    )

    with TestClient(app) as client:
        stats_response = client.get(
            "/api/stats",
            headers={"x-cloud-user-id": "cloud-user-1"},
        )
        memory_stats_response = client.get(
            "/api/memories/stats",
            headers={"x-cloud-user-id": "cloud-user-1"},
        )

    assert stats_response.status_code == 200, stats_response.text
    stats_payload = stats_response.json()
    assert stats_payload["total_memories"] == 2
    assert stats_payload["total_sources"] == 2
    assert stats_payload["total_entities"] == 1
    assert stats_payload["memories_by_type"][0] == {"key": "fact", "count": 2}
    assert stats_payload["memories_by_status"][0] == {"key": "active", "count": 2}

    assert memory_stats_response.status_code == 200, memory_stats_response.text
    assert memory_stats_response.json()["total"] == 2
    assert reader.filters
    assert all(filters.disabled_source_ids == ("src-b",) for filters in reader.filters)
