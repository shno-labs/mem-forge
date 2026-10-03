"""Source-neutral declarations consumed by the representation compiler."""

from __future__ import annotations

from dataclasses import dataclass

from memforge.source_projection import EvidenceRepresentationProfile


@dataclass(frozen=True, slots=True)
class CanonicalRecordField:
    json_pointer: str
    nested_profile: str | None = None
    comparison_keys: tuple[str, ...] = ()
    contextual: bool = False

    def __post_init__(self) -> None:
        if self.nested_profile not in {None, "markdown-structural", "plain-text"}:
            raise ValueError("unsupported nested canonical-record text profile")


@dataclass(frozen=True, slots=True)
class CanonicalRecordSchema:
    name: str
    version: int
    fields: tuple[CanonicalRecordField, ...]
    tombstone_pointer: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceRepresentationContract:
    profile: EvidenceRepresentationProfile
    canonical_schema: CanonicalRecordSchema | None = None

    def __post_init__(self) -> None:
        if (self.profile.name == "canonical-record") != (self.canonical_schema is not None):
            raise ValueError("canonical schema ownership must match the representation profile")
