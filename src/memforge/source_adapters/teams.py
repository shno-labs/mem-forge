"""Teams-owned immutable record fields and comparison semantics."""

from __future__ import annotations

from typing import Mapping

from memforge.source_adapters.contracts import CanonicalRecordField, CanonicalRecordSchema


CANONICAL_RECORD_SCHEMAS: Mapping[tuple[str, int], CanonicalRecordSchema] = {
    ("teams-message", 1): CanonicalRecordSchema(
        name="teams-message",
        version=1,
        fields=(CanonicalRecordField("/content", nested_profile="markdown-structural"),),
        tombstone_pointer="/deleted",
    ),
}
