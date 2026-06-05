import pytest
from memforge.models import Memory, Visibility, content_hash, SHARED_PROJECT_KEY
from memforge.storage.database import Database
from memforge.storage.adapters.sqlite import build_sqlite_adapters
from memforge.storage.adapters.context import AccessScope


WORKSPACE = Visibility.WORKSPACE.value
PRIVATE = Visibility.PRIVATE.value


def _mem(mid: str, content: str, *, visibility=WORKSPACE, owner=None,
         project_key=SHARED_PROJECT_KEY, status="active") -> Memory:
    return Memory(
        id=mid,
        memory_type="fact",
        content=content,
        content_hash=content_hash(content + mid),
        visibility=visibility,
        owner_user_id=owner,
        project_key=project_key,
        tags=[],
        status=status,
    )


def _scope(*, user_id="u-1", include_private=False) -> AccessScope:
    return AccessScope(
        user_id=user_id,
        open_projects=frozenset({SHARED_PROJECT_KEY}),
        member_projects=frozenset(),
        include_private=include_private,
        allowed_statuses=("active",),
        active_project=None,
        scope_mode="project-first",
    )


@pytest.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "p.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_bm25_hides_other_users_private_memory(db):
    # Two memories with the same FTS-matchable token, one workspace, one U2 private.
    await db.insert_memory(_mem("m-shared", "deploy via argocd", visibility=WORKSPACE))
    await db.insert_memory(_mem("m-priv", "deploy via argocd",
                                 visibility=PRIVATE, owner="u-2"))
    adapters = build_sqlite_adapters(db, memory_collection=None)
    # TEAM search by U1: must not return U2's private memory.
    team = await adapters.keyword.search("argocd", _scope(user_id="u-1",
                                                          include_private=False),
                                          memory_types=None, limit=10)
    assert {mid for mid, _ in team} == {"m-shared"}
    # PERSONALIZED search by U1: still must not return U2's private memory.
    personalized = await adapters.keyword.search(
        "argocd", _scope(user_id="u-1", include_private=True),
        memory_types=None, limit=10,
    )
    assert {mid for mid, _ in personalized} == {"m-shared"}
