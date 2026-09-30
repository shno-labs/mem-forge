"""Upgrade recorded stored input so that it names only objects its Document owns.

A Document uses only the objects stored under its own keys
(``{source}/{document identity}/``, ``DocumentStore.belongs_to_document``).
Stored inputs recorded before that rule can name other objects: title-keyed
objects that same-titled Documents of one Source shared, and objects of
another Source. Such an object may hold another Document's content, so the
upgrade proves each one before the Document keeps it (ADR 0013, amendment of
2026-10-01):

| Recorded object | Proven by | Proven | Not proven |
| --- | --- | --- | --- |
| raw | its bytes match the recorded SHA-256, or it is a local-agent package of the Source's own kind that names this Document | copied under the Document's keys | URI and SHA-256 cleared: the input has no stored raw content |
| normalized | its bytes match the recorded normalized content hash | copied under the Document's keys | URI cleared; the hash stays, because it describes the committed revision's content |
| PDF | nothing is recorded that could prove it | | URI cleared |

A missing object is cleared as well. An unapplied derivation whose stored
input names an object outside its Document's keys is superseded, because
applying it would record that object again.

The upgrade has two steps. ``plan_stored_object_ownership`` only reads: it
classifies every recorded object and names what the upgrade will do.
``copy_owned_objects`` writes the proven copies and returns the stored inputs
to record; the relational store then records them, releases every replaced
object to the ordinary cleanup of released stored input and supersedes the
derivations, in one transaction with its migration record. A copy is named by
the SHA-256 of its bytes, so writing it again writes the same object, and a
run that stops before the transaction commits leaves every recorded input as
it was. The next run plans again from the recorded inputs.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from memforge.genes.local_adapter_packages import decode_package
from memforge.local_agent.replay_adapter import get_local_source_replay_adapter, registered_local_source_types
from memforge.storage.document_store import DocumentStore

__all__ = [
    "ForeignObject",
    "ObjectKind",
    "OwnedStoredInput",
    "OwnershipFinding",
    "RecordedStoredInput",
    "StoredInputOwnership",
    "StoredObjectOwnershipPlan",
    "UnappliedDerivationInput",
    "copy_owned_objects",
    "plan_stored_object_ownership",
    "unapplied_derivation_input",
]


class ObjectKind(str, Enum):
    RAW = "raw"
    NORMALIZED = "normalized"
    PDF = "pdf"


class OwnershipFinding(str, Enum):
    """What the upgrade found in one recorded object outside the Document's keys."""

    # Proven, so the Document keeps a copy under its own keys.
    RECORDED_HASH_MATCHES = "recorded_hash_matches"
    PACKAGE_OF_DOCUMENT = "package_of_document"
    # Not proven, so the input no longer names it.
    PACKAGE_OF_OTHER_DOCUMENT = "package_of_other_document"
    UNPROVEN = "unproven"
    MISSING = "missing"

    @property
    def copies(self) -> bool:
        return self in (OwnershipFinding.RECORDED_HASH_MATCHES, OwnershipFinding.PACKAGE_OF_DOCUMENT)


@dataclass(frozen=True, slots=True)
class RecordedStoredInput:
    """One recorded stored input row, with its Source's type."""

    source_unit_id: str
    unit_revision_id: str
    source_id: str
    source_type: str
    document_id: str
    raw_content_uri: str | None
    raw_content_type: str
    raw_content_sha256: str | None
    normalized_content_uri: str | None
    normalized_content_hash: str | None
    pdf_content_uri: str | None
    # Every recording of an input sets it, so it identifies the planned row.
    recorded_at: str

    @property
    def names_objects(self) -> bool:
        return any((self.raw_content_uri, self.normalized_content_uri, self.pdf_content_uri))


@dataclass(frozen=True, slots=True)
class ForeignObject:
    """A recorded object outside the Document's keys and what the upgrade found in it."""

    kind: ObjectKind
    uri: str
    finding: OwnershipFinding
    # The SHA-256 of the bytes a proven object is copied with.
    sha256: str | None = None


@dataclass(frozen=True, slots=True)
class StoredInputOwnership:
    recorded: RecordedStoredInput
    foreign_objects: tuple[ForeignObject, ...]


@dataclass(frozen=True, slots=True)
class UnappliedDerivationInput:
    """The objects named by the stored input of one unapplied derivation."""

    derivation_id: str
    source_id: str
    document_id: str
    uris: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StoredObjectOwnershipPlan:
    """Everything the upgrade does, computed without writing anything."""

    inspected_input_count: int
    inputs: tuple[StoredInputOwnership, ...]
    superseded_derivation_ids: tuple[str, ...]

    def counts(self) -> dict[str, int]:
        """The number of recorded objects in each ``{kind}.{finding}`` class, and the totals."""

        classes = Counter(
            f"{foreign.kind.value}.{foreign.finding.value}"
            for ownership in self.inputs
            for foreign in ownership.foreign_objects
        )
        return {
            "inputs": self.inspected_input_count,
            "inputs_changed": len(self.inputs),
            **dict(sorted(classes.items())),
            "derivations_superseded": len(self.superseded_derivation_ids),
        }


@dataclass(frozen=True, slots=True)
class OwnedStoredInput:
    """The stored input to record in place of a planned row, and the objects it releases."""

    source_unit_id: str
    unit_revision_id: str
    source_id: str
    recorded_at: str
    raw_content_uri: str | None
    raw_content_sha256: str | None
    normalized_content_uri: str | None
    pdf_content_uri: str | None
    released_uris: tuple[str, ...]


def unapplied_derivation_input(derivation_id: str, context_payload_json: str | None) -> UnappliedDerivationInput | None:
    """The objects the stored input of an unapplied derivation names, or ``None`` when it carries none."""

    payload = json.loads(context_payload_json or "{}")
    unit_input = payload.get("unit_input")
    if not isinstance(unit_input, Mapping):
        return None
    uris = tuple(
        str(unit_input[key])
        for key in ("raw_content_uri", "normalized_content_uri", "pdf_content_uri")
        if unit_input.get(key)
    )
    return UnappliedDerivationInput(
        derivation_id=derivation_id,
        source_id=str(unit_input["source_id"]),
        document_id=str(unit_input["document_id"]),
        uris=uris,
    )


def plan_stored_object_ownership(
    recorded_inputs: Iterable[RecordedStoredInput],
    unapplied_derivations: Iterable[UnappliedDerivationInput],
    document_store: DocumentStore,
) -> StoredObjectOwnershipPlan:
    """Classify every recorded object outside its Document's keys; reads only."""

    inspected = 0
    inputs: list[StoredInputOwnership] = []
    for recorded in recorded_inputs:
        inspected += 1
        foreign_objects = _foreign_objects(recorded, document_store)
        if foreign_objects:
            inputs.append(StoredInputOwnership(recorded=recorded, foreign_objects=foreign_objects))
    superseded = tuple(
        derivation.derivation_id
        for derivation in unapplied_derivations
        if any(
            not document_store.belongs_to_document(
                uri, source_id=derivation.source_id, doc_id=derivation.document_id
            )
            for uri in derivation.uris
        )
    )
    return StoredObjectOwnershipPlan(
        inspected_input_count=inspected,
        inputs=tuple(inputs),
        superseded_derivation_ids=superseded,
    )


def copy_owned_objects(
    plan: StoredObjectOwnershipPlan,
    document_store: DocumentStore,
) -> tuple[OwnedStoredInput, ...]:
    """Write each proven object under its Document's keys; returns the inputs to record.

    Every copy is written before any input names it. A proven object whose
    bytes changed after planning fails the upgrade, and the next run plans
    again.
    """

    return tuple(_owned_input(ownership, document_store) for ownership in plan.inputs)


def _foreign_objects(recorded: RecordedStoredInput, document_store: DocumentStore) -> tuple[ForeignObject, ...]:
    def foreign(uri: str | None) -> bool:
        return bool(uri) and not document_store.belongs_to_document(
            uri, source_id=recorded.source_id, doc_id=recorded.document_id
        )

    found: list[ForeignObject] = []
    if foreign(recorded.raw_content_uri):
        found.append(_raw_object(recorded, str(recorded.raw_content_uri), document_store))
    if foreign(recorded.normalized_content_uri):
        found.append(_normalized_object(recorded, str(recorded.normalized_content_uri), document_store))
    if foreign(recorded.pdf_content_uri):
        uri = str(recorded.pdf_content_uri)
        present = document_store.get_artifact(uri, "application/pdf") is not None
        found.append(
            ForeignObject(
                kind=ObjectKind.PDF,
                uri=uri,
                finding=OwnershipFinding.UNPROVEN if present else OwnershipFinding.MISSING,
            )
        )
    return tuple(found)


def _raw_object(recorded: RecordedStoredInput, uri: str, document_store: DocumentStore) -> ForeignObject:
    body = _read(document_store, uri, recorded.raw_content_type)
    if body is None:
        return ForeignObject(kind=ObjectKind.RAW, uri=uri, finding=OwnershipFinding.MISSING)
    sha256 = hashlib.sha256(body).hexdigest()
    if recorded.raw_content_sha256 is not None and sha256 == recorded.raw_content_sha256:
        finding = OwnershipFinding.RECORDED_HASH_MATCHES
    else:
        package = _source_package(recorded.source_type, body)
        if package is None:
            finding = OwnershipFinding.UNPROVEN
        elif package.get("doc_id") == recorded.document_id:
            finding = OwnershipFinding.PACKAGE_OF_DOCUMENT
        else:
            finding = OwnershipFinding.PACKAGE_OF_OTHER_DOCUMENT
    return ForeignObject(kind=ObjectKind.RAW, uri=uri, finding=finding, sha256=sha256)


def _normalized_object(recorded: RecordedStoredInput, uri: str, document_store: DocumentStore) -> ForeignObject:
    body = _read(document_store, uri, "text/markdown")
    if body is None:
        return ForeignObject(kind=ObjectKind.NORMALIZED, uri=uri, finding=OwnershipFinding.MISSING)
    sha256 = hashlib.sha256(body).hexdigest()
    # The normalized content hash is the SHA-256 of the markdown's UTF-8 bytes.
    finding = (
        OwnershipFinding.RECORDED_HASH_MATCHES
        if sha256 == recorded.normalized_content_hash
        else OwnershipFinding.UNPROVEN
    )
    return ForeignObject(kind=ObjectKind.NORMALIZED, uri=uri, finding=finding, sha256=sha256)


def _source_package(source_type: str, body: bytes) -> dict[str, Any] | None:
    """The local-agent package of the Source's own kind that ``body`` holds, if any."""

    if source_type not in registered_local_source_types():
        return None
    return decode_package(body, get_local_source_replay_adapter(source_type).package_kind)


def _read(document_store: DocumentStore, uri: str, media_type: str) -> bytes | None:
    if document_store.get_artifact(uri, media_type) is None:
        return None
    return document_store.read_artifact(uri)


def _owned_input(ownership: StoredInputOwnership, document_store: DocumentStore) -> OwnedStoredInput:
    recorded = ownership.recorded
    owned = OwnedStoredInput(
        source_unit_id=recorded.source_unit_id,
        unit_revision_id=recorded.unit_revision_id,
        source_id=recorded.source_id,
        recorded_at=recorded.recorded_at,
        raw_content_uri=recorded.raw_content_uri,
        raw_content_sha256=recorded.raw_content_sha256,
        normalized_content_uri=recorded.normalized_content_uri,
        pdf_content_uri=recorded.pdf_content_uri,
        released_uris=tuple(foreign.uri for foreign in ownership.foreign_objects),
    )
    for foreign in ownership.foreign_objects:
        copy_uri = _copy(recorded, foreign, document_store) if foreign.finding.copies else None
        if foreign.kind is ObjectKind.RAW:
            owned = replace(
                owned,
                raw_content_uri=copy_uri,
                raw_content_sha256=foreign.sha256 if copy_uri else None,
            )
        elif foreign.kind is ObjectKind.NORMALIZED:
            owned = replace(owned, normalized_content_uri=copy_uri)
        else:
            owned = replace(owned, pdf_content_uri=copy_uri)
    return owned


def _copy(recorded: RecordedStoredInput, foreign: ForeignObject, document_store: DocumentStore) -> str:
    body = document_store.read_artifact(foreign.uri)
    if hashlib.sha256(body).hexdigest() != foreign.sha256:
        raise RuntimeError(f"stored object changed after the ownership upgrade planned it: {foreign.uri}")
    # Named by its SHA-256, so the copy never replaces an object that a sync
    # of this Document wrote under its title.
    name = str(foreign.sha256)
    if foreign.kind is ObjectKind.NORMALIZED:
        return document_store.store_normalized(
            source_id=recorded.source_id,
            doc_id=recorded.document_id,
            title=name,
            markdown=body.decode("utf-8"),
        )
    return document_store.store_raw(
        source_id=recorded.source_id,
        doc_id=recorded.document_id,
        title=name,
        content=body,
        content_type=recorded.raw_content_type,
    )
