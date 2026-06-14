"""Storage-neutral contract for admin source endpoints."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SourceAdminReader(Protocol):
    async def list_sources_for_user(self, user_id: str) -> list[dict[str, Any]]: ...

    async def count_source_memories(self, source_id: str) -> int: ...

    async def count_documents(self, source: str | None = None) -> int: ...

    async def get_sync_history(
        self, source: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]: ...

    async def get_source(self, source_id: str) -> dict[str, Any] | None: ...

    async def set_source_user_preference(
        self, source_id: str, user_id: str, enabled: bool
    ) -> None: ...

    async def list_disabled_source_ids_for_user(self, user_id: str) -> list[str]: ...

    async def list_source_projects(self, source_id: str) -> list[dict[str, Any]]: ...
