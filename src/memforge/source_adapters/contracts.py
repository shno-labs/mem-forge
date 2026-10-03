"""Source-neutral declarations consumed by the representation compiler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from memforge.source_projection import EvidenceRepresentationProfile


@dataclass(frozen=True, slots=True)
class DeclaredTextFragment:
    """One complete native selection in decoded-field Unicode coordinates.

    ``content_value`` is the format-owned comparison value, never model text.
    The compiler independently binds the range to the immutable record.
    """

    start: int
    end: int
    kind: str
    presentation: str
    content_value: str


@dataclass(frozen=True, slots=True)
class DeclaredTextGroup:
    start: int
    end: int
    context_ranges: tuple[tuple[int, int], ...] = ()
    together: bool = False


@dataclass(frozen=True, slots=True)
class ParsedDeclaredText:
    fragments: tuple[DeclaredTextFragment, ...]
    groups: tuple[DeclaredTextGroup, ...] = ()


@dataclass(frozen=True, slots=True)
class DeclaredTextFormat:
    """An adapter-owned format; invalid or unsupported source raises ValueError."""

    name: str
    version: int
    parse: Callable[[str], ParsedDeclaredText]

    def __post_init__(self) -> None:
        if not self.name or self.version <= 0:
            raise ValueError("declared text format requires a versioned name")


@dataclass(frozen=True, slots=True)
class CanonicalRecordField:
    json_pointer: str
    nested_profile: str | None = None
    comparison_keys: tuple[str, ...] = ()
    contextual: bool = False
    text_format: DeclaredTextFormat | None = None

    def __post_init__(self) -> None:
        if self.nested_profile not in {None, "markdown-structural", "plain-text"}:
            raise ValueError("unsupported nested canonical-record text profile")
        if self.text_format is not None and self.nested_profile is not None:
            raise ValueError("canonical text field must declare exactly one format")


@dataclass(frozen=True, slots=True)
class CanonicalRecordSchema:
    name: str
    version: int
    fields: tuple[CanonicalRecordField, ...]
    tombstone_pointer: str | None = None
    model_interpretation: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceRepresentationContract:
    profile: EvidenceRepresentationProfile
    canonical_schema: CanonicalRecordSchema | None = None

    def __post_init__(self) -> None:
        if (self.profile.name == "canonical-record") != (self.canonical_schema is not None):
            raise ValueError("canonical schema ownership must match the representation profile")
