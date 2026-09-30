"""ADR 0013 (2026-10-01): the upgrade leaves every stored input naming only objects its Document owns."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest

from memforge.models import ContentItem, slugify
from memforge.storage.database import Database
from memforge.storage.document_store import LocalDocumentStore
from memforge.storage.source_cleanup import SourceArtifactCleanupService

OWNERSHIP_MIGRATION = 109
REPOSITORY = "src-repository"
JIRA = "src-jira"
RECORDED_AT = "2026-09-01T00:00:00+00:00"
GITHUB_PACKAGE_KIND = "github_repo_document"


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def package(doc_id: str) -> bytes:
    return json.dumps({"package_kind": GITHUB_PACKAGE_KIND, "doc_id": doc_id, "markdown": f"# {doc_id}"}).encode()


class Workspace:
    def __init__(self, tmp_path: Path) -> None:
        self.path = str(tmp_path / "ownership.db")
        self.root = tmp_path / "documents"
        self.store = LocalDocumentStore(str(self.root))
        self.db: Database | None = None

    async def open(self, store: LocalDocumentStore | None = None) -> Database:
        self.db = Database(self.path, document_store=store or self.store)
        await self.db.connect()
        return self.db

    async def upgrade_again(self, store: LocalDocumentStore | None = None) -> Database:
        """Reopen the database with the ownership migration not yet recorded."""

        assert self.db is not None
        await self.db.db.execute("DELETE FROM schema_migrations WHERE version = ?", (OWNERSHIP_MIGRATION,))
        await self.db.db.commit()
        await self.db.close()
        return await self.open(store)

    def title_keyed(self, source_id: str, name: str, body: bytes) -> str:
        """An object keyed by title only, as same-titled Documents of one Source once shared."""

        path = self.root / slugify(source_id) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return str(path)

    async def add_source(self, source_id: str, source_type: str) -> None:
        assert self.db is not None
        await self.db.upsert_source(
            id=source_id, type=source_type, name=source_id, config_json="{}",
            access_policy="workspace", owner_user_id="dev",
        )

    async def add_input(
        self,
        unit_id: str,
        *,
        source_id: str,
        document_id: str,
        raw_content_uri: str | None,
        raw_content_type: str = "text/markdown",
        raw_content_sha256: str | None = None,
        normalized_content_uri: str | None = None,
        normalized_content_hash: str | None = None,
        pdf_content_uri: str | None = None,
    ) -> None:
        assert self.db is not None
        revision_id = f"{unit_id}-revision"
        await self.db.db.execute(
            """INSERT INTO source_units (id, source_id, unit_type, provider_key, locator_json,
                   current_revision_id, updated_at)
               VALUES (?, ?, 'document', ?, ?, ?, ?)""",
            (unit_id, source_id, unit_id, json.dumps({"document_id": document_id}), revision_id, RECORDED_AT),
        )
        item = ContentItem(
            item_id=document_id,
            title="User Guide",
            source_url=f"https://example.test/{document_id}",
            last_modified=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        await self.db.db.execute(
            """INSERT INTO source_unit_inputs (
                   source_unit_id, source_id, document_id, unit_revision_id, item_json,
                   raw_content_uri, raw_content_type, raw_content_sha256,
                   normalized_content_uri, normalized_content_hash, pdf_content_uri, recorded_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                unit_id, source_id, document_id, revision_id, json.dumps(item.to_payload()),
                raw_content_uri, raw_content_type, raw_content_sha256,
                normalized_content_uri, normalized_content_hash, pdf_content_uri, RECORDED_AT,
            ),
        )
        await self.db.db.commit()

    async def recorded(self, unit_id: str) -> dict:
        assert self.db is not None
        async with self.db.db.execute(
            """SELECT raw_content_uri, raw_content_sha256, normalized_content_uri, normalized_content_hash,
                      pdf_content_uri
                 FROM source_unit_inputs WHERE source_unit_id = ?""",
            (unit_id,),
        ) as cursor:
            return dict(await cursor.fetchone())

    def owns(self, uri: str | None, *, source_id: str, doc_id: str) -> bool:
        return self.store.belongs_to_document(uri, source_id=source_id, doc_id=doc_id)


@pytest.fixture
async def workspace(tmp_path):
    workspace = Workspace(tmp_path)
    await workspace.open()
    await workspace.add_source(REPOSITORY, "github_repo")
    await workspace.add_source(JIRA, "jira")
    try:
        yield workspace
    finally:
        if workspace.db is not None:
            await workspace.db.close()


def ownership_counts(caplog: pytest.LogCaptureFixture) -> dict[str, int]:
    *_, message = [record.getMessage() for record in caplog.records if record.getMessage().startswith("Stored object")]
    return json.loads(message.split(": ", 1)[1])


@pytest.mark.asyncio
async def test_proven_objects_are_copied_under_the_documents_keys_and_the_rest_are_no_longer_named(
    workspace: Workspace, caplog: pytest.LogCaptureFixture
) -> None:
    own_package = package("guide")
    other_package = package("examples/guide")
    jira_body = b'{"key": "PAY-1"}'
    normalized = "# PAY-1\n\nBody"
    own_normalized = workspace.store.store_normalized(JIRA, "jira-PAY-3", "PAY-3", "# PAY-3")
    own_raw = workspace.store.store_raw(JIRA, "jira-PAY-3", "PAY-3", b'{"key": "PAY-3"}', "application/json")
    await workspace.add_input(
        "unit-package",
        source_id=REPOSITORY,
        document_id="guide",
        raw_content_uri=workspace.title_keyed(REPOSITORY, "user-guide.json", own_package),
    )
    await workspace.add_input(
        "unit-other-package",
        source_id=REPOSITORY,
        document_id="docs/guide",
        raw_content_uri=workspace.title_keyed(REPOSITORY, "guide.json", other_package),
    )
    await workspace.add_input(
        "unit-hash",
        source_id=JIRA,
        document_id="jira-PAY-1",
        raw_content_uri=workspace.title_keyed(JIRA, "pay-1.raw.json", jira_body),
        raw_content_type="application/json",
        raw_content_sha256=sha256(jira_body),
        normalized_content_uri=workspace.title_keyed(JIRA, "pay-1.md", normalized.encode()),
        normalized_content_hash=sha256(normalized.encode()),
    )
    await workspace.add_input(
        "unit-plain",
        source_id=JIRA,
        document_id="jira-PAY-2",
        raw_content_uri=workspace.title_keyed(JIRA, "pay-2.raw.json", b'{"key": "PAY-9"}'),
        raw_content_type="application/json",
        normalized_content_uri=workspace.title_keyed(JIRA, "pay-2.md", b"# PAY-9"),
        normalized_content_hash=sha256(b"# PAY-2"),
        pdf_content_uri=workspace.title_keyed(JIRA, "pay-2.pdf", b"%PDF-PAY-9"),
    )
    await workspace.add_input(
        "unit-missing",
        source_id=JIRA,
        document_id="jira-PAY-4",
        raw_content_uri=str(workspace.root / "src-jira" / "pay-4.raw.json"),
        raw_content_type="application/json",
    )
    await workspace.add_input(
        "unit-owned",
        source_id=JIRA,
        document_id="jira-PAY-3",
        raw_content_uri=own_raw,
        raw_content_type="application/json",
        normalized_content_uri=own_normalized,
        normalized_content_hash=sha256(b"# PAY-3"),
    )
    released = {
        (await workspace.recorded(unit))[column]
        for unit in ("unit-package", "unit-other-package", "unit-hash", "unit-plain", "unit-missing")
        for column in ("raw_content_uri", "normalized_content_uri", "pdf_content_uri")
    } - {None}

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="memforge.storage.database"):
        await workspace.upgrade_again()

    copied_package = await workspace.recorded("unit-package")
    assert workspace.owns(copied_package["raw_content_uri"], source_id=REPOSITORY, doc_id="guide")
    assert workspace.store.read_artifact(copied_package["raw_content_uri"]) == own_package
    assert copied_package["raw_content_sha256"] == sha256(own_package)
    assert await workspace.recorded("unit-other-package") == {
        "raw_content_uri": None,
        "raw_content_sha256": None,
        "normalized_content_uri": None,
        "normalized_content_hash": None,
        "pdf_content_uri": None,
    }
    copied = await workspace.recorded("unit-hash")
    assert workspace.owns(copied["raw_content_uri"], source_id=JIRA, doc_id="jira-PAY-1")
    assert workspace.owns(copied["normalized_content_uri"], source_id=JIRA, doc_id="jira-PAY-1")
    assert workspace.store.read_artifact(copied["raw_content_uri"]) == jira_body
    assert workspace.store.read_normalized(copied["normalized_content_uri"]) == normalized
    assert (copied["raw_content_sha256"], copied["normalized_content_hash"]) == (
        sha256(jira_body),
        sha256(normalized.encode()),
    )
    # The normalized hash still describes the committed revision's content.
    assert await workspace.recorded("unit-plain") == {
        "raw_content_uri": None,
        "raw_content_sha256": None,
        "normalized_content_uri": None,
        "normalized_content_hash": sha256(b"# PAY-2"),
        "pdf_content_uri": None,
    }
    assert (await workspace.recorded("unit-missing"))["raw_content_uri"] is None
    assert await workspace.recorded("unit-owned") == {
        "raw_content_uri": own_raw,
        "raw_content_sha256": None,
        "normalized_content_uri": own_normalized,
        "normalized_content_hash": sha256(b"# PAY-3"),
        "pdf_content_uri": None,
    }
    assert ownership_counts(caplog) == {
        "inputs": 6,
        "inputs_changed": 5,
        "normalized.recorded_hash_matches": 1,
        "normalized.unproven": 1,
        "pdf.unproven": 1,
        "raw.missing": 1,
        "raw.package_of_document": 1,
        "raw.package_of_other_document": 1,
        "raw.recorded_hash_matches": 1,
        "raw.unproven": 1,
        "derivations_superseded": 0,
    }

    # The ordinary cleanup of released stored input deletes the replaced
    # objects once nothing names them, and keeps the copies.
    assert {task.artifact_uri for task in await workspace.db.list_source_artifact_cleanup_tasks()} == released
    await SourceArtifactCleanupService(workspace.db, workspace.store).run_pending(limit=100)
    assert not any(Path(uri).exists() for uri in released)
    assert workspace.store.read_artifact(copied_package["raw_content_uri"]) == own_package
    assert workspace.store.read_normalized(copied["normalized_content_uri"]) == normalized


@pytest.mark.asyncio
async def test_the_upgrade_run_again_changes_nothing(workspace: Workspace, caplog: pytest.LogCaptureFixture) -> None:
    body = package("guide")
    await workspace.add_input(
        "unit-package",
        source_id=REPOSITORY,
        document_id="guide",
        raw_content_uri=workspace.title_keyed(REPOSITORY, "user-guide.json", body),
    )
    await workspace.upgrade_again()
    upgraded = await workspace.recorded("unit-package")
    objects = sorted(path for path in workspace.root.rglob("*") if path.is_file())

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="memforge.storage.database"):
        await workspace.upgrade_again()

    assert await workspace.recorded("unit-package") == upgraded
    assert sorted(path for path in workspace.root.rglob("*") if path.is_file()) == objects
    assert ownership_counts(caplog) == {"inputs": 1, "inputs_changed": 0, "derivations_superseded": 0}


class FailingCopyStore(LocalDocumentStore):
    def store_raw(self, *args, **kwargs) -> str:
        raise OSError("object store unavailable")


@pytest.mark.asyncio
async def test_an_upgrade_that_cannot_copy_leaves_every_input_as_recorded(workspace: Workspace) -> None:
    body = package("guide")
    title_keyed = workspace.title_keyed(REPOSITORY, "user-guide.json", body)
    await workspace.add_input("unit-package", source_id=REPOSITORY, document_id="guide", raw_content_uri=title_keyed)
    await workspace.add_input(
        "unit-other-package",
        source_id=REPOSITORY,
        document_id="docs/guide",
        raw_content_uri=workspace.title_keyed(REPOSITORY, "guide.json", package("examples/guide")),
    )
    await workspace.db.db.execute("DELETE FROM schema_migrations WHERE version = ?", (OWNERSHIP_MIGRATION,))
    await workspace.db.db.commit()
    await workspace.db.close()

    with pytest.raises(OSError, match="object store unavailable"):
        await workspace.open(FailingCopyStore(str(workspace.root)))
    await workspace.db.close()
    workspace.db = Database(workspace.path)
    await workspace.db.connect(run_migrations=False)
    assert (await workspace.recorded("unit-package"))["raw_content_uri"] == title_keyed
    assert (await workspace.recorded("unit-other-package"))["raw_content_uri"] is not None
    async with workspace.db.db.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ?", (OWNERSHIP_MIGRATION,)
    ) as cursor:
        assert await cursor.fetchone() is None
    assert await workspace.db.list_source_artifact_cleanup_tasks() == []
    await workspace.db.close()

    await workspace.open()

    assert workspace.owns(
        (await workspace.recorded("unit-package"))["raw_content_uri"], source_id=REPOSITORY, doc_id="guide"
    )
    assert (await workspace.recorded("unit-other-package"))["raw_content_uri"] is None


@pytest.mark.asyncio
async def test_an_unapplied_derivation_naming_an_object_outside_its_documents_keys_is_superseded(
    workspace: Workspace,
) -> None:
    own = workspace.store.store_raw(JIRA, "jira-PAY-1", "PAY-1", b'{"key": "PAY-1"}', "application/json")
    title_keyed = workspace.title_keyed(JIRA, "pay-1.raw.json", b'{"key": "PAY-9"}')
    for derivation_id, raw_uri in (("derivation-own", own), ("derivation-title-keyed", title_keyed)):
        payload = {
            "unit_input": {
                "source_unit_id": "unit-1",
                "unit_revision_id": "unit-1-revision-2",
                "source_id": JIRA,
                "document_id": "jira-PAY-1",
                "raw_content_uri": raw_uri,
                "normalized_content_uri": None,
                "pdf_content_uri": None,
            }
        }
        await workspace.db.db.execute(
            """INSERT INTO source_derivation_attempts (
                   id, source_id, source_unit_id, base_unit_revision_id, target_unit_revision_id,
                   projection_payload_json, projection_payload_hash, projection_identity_hash,
                   context_payload_json, context_payload_hash, context_identity_hash,
                   extraction_contract_version, status, created_at, updated_at
               ) VALUES (?, ?, 'unit-1', 'unit-1-revision-1', 'unit-1-revision-2', '{}', 'p', 'p', ?, 'c', 'c',
                         'v1', 'pending', ?, ?)""",
            (derivation_id, JIRA, json.dumps(payload), RECORDED_AT, RECORDED_AT),
        )
    await workspace.db.db.commit()

    await workspace.upgrade_again()

    async with workspace.db.db.execute(
        "SELECT id, status FROM source_derivation_attempts ORDER BY id"
    ) as cursor:
        assert [tuple(row) for row in await cursor.fetchall()] == [
            ("derivation-own", "pending"),
            ("derivation-title-keyed", "superseded"),
        ]


@pytest.mark.asyncio
async def test_a_database_with_recorded_input_is_upgraded_only_with_its_document_store(
    workspace: Workspace,
) -> None:
    await workspace.add_input(
        "unit-package",
        source_id=REPOSITORY,
        document_id="guide",
        raw_content_uri=workspace.title_keyed(REPOSITORY, "user-guide.json", package("guide")),
    )
    await workspace.db.db.execute("DELETE FROM schema_migrations WHERE version = ?", (OWNERSHIP_MIGRATION,))
    await workspace.db.db.commit()
    await workspace.db.close()
    workspace.db = Database(workspace.path)

    with pytest.raises(RuntimeError, match="needs the workspace's document store"):
        await workspace.db.connect()
