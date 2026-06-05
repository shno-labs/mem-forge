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


@pytest.mark.asyncio
async def test_graph_hides_other_users_private_memory(db):
    e1_id = await db.upsert_entity("argocd", "tool")
    await db.insert_memory(_mem("g-shared", "deploys via argocd"))
    await db.link_memory_entity("g-shared", e1_id)
    await db.insert_memory(_mem("g-priv", "deploys via argocd",
                                 visibility=PRIVATE, owner="u-2"))
    await db.link_memory_entity("g-priv", e1_id)
    adapters = build_sqlite_adapters(db, memory_collection=None)
    hits = await adapters.relational.graph_search(
        [e1_id], _scope(user_id="u-1", include_private=False),
        memory_types=None, limit=10,
    )
    assert {mid for mid, _ in hits} == {"g-shared"}


@pytest.mark.asyncio
async def test_temporal_hides_other_users_private_memory(db):
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    await db.insert_memory(_mem("t-shared", "x"))
    await db.insert_memory(_mem("t-priv", "x", visibility=PRIVATE, owner="u-2"))
    adapters = build_sqlite_adapters(db, memory_collection=None)
    hits = await adapters.relational.temporal_search(
        after=now - timedelta(days=1), before=None,
        scope=_scope(user_id="u-1", include_private=False),
        memory_types=None, limit=10,
    )
    assert {mid for mid, _ in hits} == {"t-shared"}


class _Coll:
    """Minimal Chroma fake: stores items with metadata, supports a where-filter."""

    def __init__(self):
        self.items: dict[str, dict] = {}

    def upsert(self, *, ids, embeddings, metadatas, **_):
        for i, mid in enumerate(ids):
            self.items[mid] = {"embedding": embeddings[i],
                                "metadata": dict(metadatas[i])}

    def query(self, *, query_embeddings, n_results, where=None, **_):
        # Trivial cosine-equal match: return all ids that satisfy where.
        def matches(meta, clause):
            if "$and" in clause:
                return all(matches(meta, c) for c in clause["$and"])
            if "$or" in clause:
                return any(matches(meta, c) for c in clause["$or"])
            for k, v in clause.items():
                if isinstance(v, dict) and "$in" in v:
                    if meta.get(k) not in v["$in"]:
                        return False
                else:
                    if meta.get(k) != v:
                        return False
            return True

        ids, dists = [], []
        for mid, rec in self.items.items():
            if where is None or matches(rec["metadata"], where):
                ids.append(mid)
                dists.append(0.1)  # any monotonic distance
        return {"ids": [ids[:n_results]], "distances": [dists[:n_results]]}


@pytest.mark.asyncio
async def test_vector_hides_other_users_private_memory(db):
    from memforge.storage.adapters.sqlite.vector import SqliteVectorStore
    coll = _Coll()
    coll.upsert(
        ids=["v-shared"], embeddings=[[0.1, 0.1, 0.1]],
        metadatas=[{"status": "active", "visibility": WORKSPACE,
                    "owner_user_id": "", "project_key": SHARED_PROJECT_KEY,
                    "memory_type": "fact"}],
    )
    coll.upsert(
        ids=["v-priv"], embeddings=[[0.1, 0.1, 0.1]],
        metadatas=[{"status": "active", "visibility": PRIVATE,
                    "owner_user_id": "u-2", "project_key": SHARED_PROJECT_KEY,
                    "memory_type": "fact"}],
    )
    vs = SqliteVectorStore(coll)
    hits = await vs.query([0.1, 0.1, 0.1],
                          _scope(user_id="u-1", include_private=False),
                          memory_types=None, limit=10)
    assert {mid for mid, _ in hits} == {"v-shared"}


@pytest.mark.asyncio
async def test_vector_pre_filter_does_not_drop_dangling_project_workspace_memory(db):
    # The vector tier intentionally does not narrow by project_key (Chroma cannot
    # express the dangling-project fail-safe). A workspace memory whose project
    # key has no row in the projects table must still be a vector candidate;
    # the relational post-fusion re-check is the authority on project openness.
    from memforge.storage.adapters.sqlite.vector import SqliteVectorStore
    coll = _Coll()
    coll.upsert(
        ids=["v-dangling"], embeddings=[[0.1, 0.1, 0.1]],
        metadatas=[{"status": "active", "visibility": WORKSPACE,
                    "owner_user_id": "", "project_key": "DANGLING-X",
                    "memory_type": "fact"}],
    )
    vs = SqliteVectorStore(coll)
    hits = await vs.query([0.1, 0.1, 0.1],
                          _scope(user_id="u-1", include_private=False),
                          memory_types=None, limit=10)
    assert {mid for mid, _ in hits} == {"v-dangling"}
