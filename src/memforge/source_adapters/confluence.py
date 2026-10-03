"""Confluence-owned immutable page representation declarations."""

from __future__ import annotations

from memforge.source_adapters.contracts import CanonicalRecordField, CanonicalRecordSchema
from memforge.source_adapters.confluence_storage import STORAGE_FORMAT
from memforge.source_projection import EvidenceCoordinateSpace, EvidenceRepresentationProfile


PAGE_SCHEMA = CanonicalRecordSchema(
    name="confluence-page-storage", version=1,
    fields=(
        CanonicalRecordField("/title", contextual=True),
        CanonicalRecordField("/body", text_format=STORAGE_FORMAT),
    ),
)
CANONICAL_RECORD_SCHEMAS = {(PAGE_SCHEMA.name, PAGE_SCHEMA.version): PAGE_SCHEMA}
# The pre-profile writer persisted normalized Markdown. NULL-profile backfill
# may attest that historical contract, never the newly introduced native schema.
LEGACY_OBSERVATION_PROFILES = {
    ("confluence", "page_body"): EvidenceRepresentationProfile(
        "markdown-structural", 1, EvidenceCoordinateSpace.UNICODE_SCALAR,
    ),
}


def page_record(title: str, storage: object) -> dict[str, str]:
    """The actual fetched storage value; never reconstruct from normalized text."""
    if not isinstance(storage, str):
        raise ValueError("Confluence page projection requires its fetched storage value")
    return {
        "title": title, "body": storage,
        "representation": f"{PAGE_SCHEMA.name}:{PAGE_SCHEMA.version}",
    }
