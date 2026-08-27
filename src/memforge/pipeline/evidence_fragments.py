"""Deterministic, revision-pinned Evidence Fragment compilation.

The compiler owns representation parsing and transient catalog references.  It
does not create durable Evidence, call a model, or make lifecycle decisions.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass, field, replace
from enum import Enum
from html.parser import HTMLParser
from typing import Callable, Mapping, Sequence

from markdown_it import MarkdownIt

from memforge.memory.evidence import EvidenceRole
from memforge.source_projection import (
    AnchorKind,
    EvidenceCoordinateSpace,
    EvidenceRepresentationProfile,
    SourceAnchor,
    SourceObservationRevision,
)


COMPILER_CONTRACT_VERSION = 1
DEFAULT_MAX_FRAGMENTS = 2_048
DEFAULT_MAX_PRESENTATION_CHARS = 120_000
_SUPPORTING_ROLES = frozenset({EvidenceRole.PRIMARY, EvidenceRole.REQUIRED})


class EvidenceFragmentKind(str, Enum):
    TEXT = "text"
    ARTIFACT = "artifact"


class FragmentCompilationErrorCode(str, Enum):
    UNSUPPORTED_PROFILE = "unsupported_profile"
    INVALID_AUTHORITY_RANGE = "invalid_authority_range"
    MALFORMED_MARKDOWN = "malformed_markdown"
    MALFORMED_HTML = "malformed_html"
    UNSUPPORTED_HTML = "unsupported_html"
    MALFORMED_CANONICAL_RECORD = "malformed_canonical_record"
    SCHEMA_MISMATCH = "schema_mismatch"
    ARTIFACT_INELIGIBLE = "artifact_ineligible"
    NO_SELECTABLE_CONTENT = "no_selectable_content"
    CATALOG_TOO_LARGE = "catalog_too_large"


@dataclass(frozen=True, slots=True)
class FragmentCompilationError:
    code: FragmentCompilationErrorCode
    observation_revision_id: str
    message: str
    range_start: int | None = None
    range_end: int | None = None
    fatal: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceAuthorityRange:
    """One application-owned Anchor and the roles selectable from it."""

    anchor: SourceAnchor
    eligible_roles: frozenset[EvidenceRole]

    def __post_init__(self) -> None:
        allowed = {EvidenceRole.PRIMARY, EvidenceRole.REQUIRED}
        if not self.eligible_roles or not self.eligible_roles.issubset(allowed):
            raise ValueError("Evidence Authority Range requires Primary and/or Required eligibility")


@dataclass(frozen=True, slots=True)
class EvidenceFragment:
    reference: str
    kind: EvidenceFragmentKind
    fragment_type: str
    anchor: SourceAnchor
    eligible_roles: frozenset[EvidenceRole]
    raw_content_sha256: str
    presentation_text: str
    presentation_sha256: str


@dataclass(frozen=True, slots=True)
class EvidenceFragmentCatalog:
    observation_revision_id: str
    profile: EvidenceRepresentationProfile
    fragments: tuple[EvidenceFragment, ...]
    errors: tuple[FragmentCompilationError, ...]
    digest: str
    max_fragments: int
    max_presentation_chars: int

    @property
    def usable(self) -> bool:
        return bool(self.fragments) and not any(error.fatal for error in self.errors)

    def resolve(self, reference: str, role: EvidenceRole) -> EvidenceFragment | None:
        """Resolve one catalog-local selector without widening its authority."""

        if role not in {EvidenceRole.PRIMARY, EvidenceRole.REQUIRED}:
            return None
        for fragment in self.fragments:
            if fragment.reference == reference:
                return fragment if role in fragment.eligible_roles else None
        return None

    def model_payload(self) -> tuple[Mapping[str, object], ...]:
        """Return the bounded selector view; authoritative raw text stays in the Revision."""

        return tuple(
            {
                "ref": fragment.reference,
                "kind": fragment.kind.value,
                "type": fragment.fragment_type,
                "text": fragment.presentation_text,
                "eligible_roles": sorted(role.value for role in fragment.eligible_roles),
            }
            for fragment in self.fragments
        )


@dataclass(frozen=True, slots=True)
class CanonicalRecordField:
    json_pointer: str
    nested_profile: str | None = None

    def __post_init__(self) -> None:
        if self.nested_profile not in {None, "markdown-structural", "plain-text"}:
            raise ValueError("unsupported nested canonical-record text profile")


@dataclass(frozen=True, slots=True)
class CanonicalRecordSchema:
    name: str
    version: int
    fields: tuple[CanonicalRecordField, ...]


CANONICAL_RECORD_SCHEMAS: Mapping[tuple[str, int], CanonicalRecordSchema] = {
    ("jira-issue-core", 1): CanonicalRecordSchema(
        name="jira-issue-core",
        version=1,
        fields=(
            CanonicalRecordField("/summary"),
            CanonicalRecordField("/description", nested_profile="markdown-structural"),
            CanonicalRecordField("/status"),
            CanonicalRecordField("/priority"),
            CanonicalRecordField("/assignee"),
            CanonicalRecordField("/labels"),
            CanonicalRecordField("/resolution"),
        ),
    ),
    ("jira-comment", 1): CanonicalRecordSchema(
        name="jira-comment",
        version=1,
        fields=(CanonicalRecordField("/body", nested_profile="markdown-structural"),),
    ),
    ("jira-changelog", 1): CanonicalRecordSchema(
        name="jira-changelog",
        version=1,
        fields=(CanonicalRecordField(""),),
    ),
    ("teams-message", 1): CanonicalRecordSchema(
        name="teams-message",
        version=1,
        fields=(CanonicalRecordField("/content", nested_profile="markdown-structural"),),
    ),
}


@dataclass(frozen=True, slots=True)
class _FragmentCandidate:
    kind: EvidenceFragmentKind
    fragment_type: str
    start: int | None
    end: int | None
    eligible_roles: frozenset[EvidenceRole]
    presentation_text: str
    raw_content_sha256: str | None = None


def compile_fragments(
    revision: SourceObservationRevision,
    profile: EvidenceRepresentationProfile,
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
    *,
    max_fragments: int = DEFAULT_MAX_FRAGMENTS,
    max_presentation_chars: int = DEFAULT_MAX_PRESENTATION_CHARS,
) -> EvidenceFragmentCatalog:
    """Compile one immutable Observation Revision under its declared profile."""

    if revision.evidence_profile is not None and revision.evidence_profile != profile:
        return _fatal_catalog(
            revision,
            profile,
            authority_ranges,
            FragmentCompilationErrorCode.UNSUPPORTED_PROFILE,
            "compiler profile does not match the immutable Observation Revision",
            max_fragments=max_fragments,
            max_presentation_chars=max_presentation_chars,
        )
    if max_fragments <= 0 or max_presentation_chars <= 0:
        raise ValueError("Fragment catalog limits must be positive")

    range_error = _validate_authority_ranges(revision, profile, authority_ranges)
    if range_error is not None:
        return _catalog_from_candidates(
            revision,
            profile,
            authority_ranges,
            (),
            (range_error,),
            max_fragments=max_fragments,
            max_presentation_chars=max_presentation_chars,
        )

    compiler = _PROFILE_COMPILERS.get((profile.name, profile.version))
    if compiler is None:
        return _fatal_catalog(
            revision,
            profile,
            authority_ranges,
            FragmentCompilationErrorCode.UNSUPPORTED_PROFILE,
            f"unsupported Evidence Representation Profile: {profile.name}/{profile.version}",
            max_fragments=max_fragments,
            max_presentation_chars=max_presentation_chars,
        )

    candidates, errors = compiler(revision, profile, authority_ranges)
    return _catalog_from_candidates(
        revision,
        profile,
        authority_ranges,
        candidates,
        errors,
        max_fragments=max_fragments,
        max_presentation_chars=max_presentation_chars,
    )


def _validate_authority_ranges(
    revision: SourceObservationRevision,
    profile: EvidenceRepresentationProfile,
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
) -> FragmentCompilationError | None:
    expected_coordinate_space = (
        EvidenceCoordinateSpace.WHOLE_ARTIFACT
        if profile.name == "binary-artifact"
        else EvidenceCoordinateSpace.UNICODE_SCALAR
    )
    if profile.coordinate_space is not expected_coordinate_space:
        return _error(
            revision,
            FragmentCompilationErrorCode.UNSUPPORTED_PROFILE,
            "Evidence Representation Profile declares an incompatible coordinate space",
            fatal=True,
        )
    if not authority_ranges:
        return _error(
            revision,
            FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE,
            "Fragment compilation requires at least one authority range",
            fatal=True,
        )
    if profile.name == "binary-artifact" and len(authority_ranges) != 1:
        return _error(
            revision,
            FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE,
            "binary Artifact compilation requires exactly one authority range",
            fatal=True,
        )
    spans: list[tuple[int, int]] = []
    for item in authority_ranges:
        anchor = item.anchor
        if anchor.observation_id != revision.observation_id or anchor.observation_revision_id != revision.id:
            return _error(
                revision,
                FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE,
                "authority range belongs to another Observation Revision",
                fatal=True,
            )
        if profile.coordinate_space is EvidenceCoordinateSpace.WHOLE_ARTIFACT:
            if anchor.kind is not AnchorKind.WHOLE_OBSERVATION:
                return _error(
                    revision,
                    FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE,
                    "binary Artifact authority must cover the whole Observation",
                    fatal=True,
                )
            continue
        if anchor.kind is AnchorKind.WHOLE_OBSERVATION:
            spans.append((0, len(revision.content)))
            continue
        if anchor.kind is not AnchorKind.REVISION_RANGE:
            return _error(
                revision,
                FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE,
                "derived Fragment compilation accepts only whole or revision-range Anchors",
                fatal=True,
            )
        assert anchor.range_start is not None and anchor.range_end is not None
        if anchor.range_end > len(revision.content):
            return _error(
                revision,
                FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE,
                "authority range exceeds immutable Revision content",
                start=anchor.range_start,
                end=anchor.range_end,
                fatal=True,
            )
        spans.append((anchor.range_start, anchor.range_end))
    spans.sort()
    if any(current_start < previous_end for (_, previous_end), (current_start, _) in zip(spans, spans[1:])):
        return _error(
            revision,
            FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE,
            "authority ranges must not overlap",
            fatal=True,
        )
    return None


def _compile_markdown_profile(
    revision: SourceObservationRevision,
    profile: EvidenceRepresentationProfile,
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
) -> tuple[tuple[_FragmentCandidate, ...], tuple[FragmentCompilationError, ...]]:
    del profile
    candidates, errors = _markdown_candidates(
        revision,
        revision.content,
        base=0,
        roles=_SUPPORTING_ROLES,
    )
    bound, authority_errors = _bind_candidates_to_authority(
        revision,
        candidates,
        authority_ranges,
    )
    return bound, (*_errors_inside_authority(errors, authority_ranges, revision.content), *authority_errors)


def _compile_plain_text_profile(
    revision: SourceObservationRevision,
    profile: EvidenceRepresentationProfile,
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
) -> tuple[tuple[_FragmentCandidate, ...], tuple[FragmentCompilationError, ...]]:
    del profile
    candidates: list[_FragmentCandidate] = []
    for start, end in _paragraph_ranges(revision.content):
        candidates.append(
            _text_candidate(
                revision.content,
                "plain-paragraph",
                start,
                end,
                _SUPPORTING_ROLES,
                revision.content[start:end],
            )
        )
    return _bind_candidates_to_authority(revision, tuple(candidates), authority_ranges)


def _compile_binary_artifact_profile(
    revision: SourceObservationRevision,
    profile: EvidenceRepresentationProfile,
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
) -> tuple[tuple[_FragmentCandidate, ...], tuple[FragmentCompilationError, ...]]:
    del profile
    raw_artifact = revision.metadata.get("source_artifact")
    if not isinstance(raw_artifact, Mapping):
        return (), (
            _error(
                revision,
                FragmentCompilationErrorCode.ARTIFACT_INELIGIBLE,
                "binary Artifact Revision lacks authoritative metadata",
                fatal=True,
            ),
        )
    if raw_artifact.get("inference_eligible") is not True:
        return (), (
            _error(
                revision,
                FragmentCompilationErrorCode.ARTIFACT_INELIGIBLE,
                "binary Artifact is not inference eligible",
                fatal=True,
            ),
        )
    digest = str(raw_artifact.get("sha256") or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        return (), (
            _error(
                revision,
                FragmentCompilationErrorCode.ARTIFACT_INELIGIBLE,
                "binary Artifact lacks a valid byte digest",
                fatal=True,
            ),
        )
    return (
        tuple(
            _FragmentCandidate(
                kind=EvidenceFragmentKind.ARTIFACT,
                fragment_type="binary-artifact",
                start=None,
                end=None,
                eligible_roles=item.eligible_roles,
                presentation_text="",
                raw_content_sha256=digest,
            )
            for item in authority_ranges
        ),
        (),
    )


def _compile_canonical_record_profile(
    revision: SourceObservationRevision,
    profile: EvidenceRepresentationProfile,
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
) -> tuple[tuple[_FragmentCandidate, ...], tuple[FragmentCompilationError, ...]]:
    if any(item.anchor.kind is not AnchorKind.WHOLE_OBSERVATION for item in authority_ranges):
        return (), (
            _error(
                revision,
                FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE,
                "canonical records require whole-Observation authority before field compilation",
                fatal=True,
            ),
        )
    assert profile.schema_name is not None and profile.schema_version is not None
    schema = CANONICAL_RECORD_SCHEMAS.get((profile.schema_name, profile.schema_version))
    if schema is None:
        return (), (
            _error(
                revision,
                FragmentCompilationErrorCode.SCHEMA_MISMATCH,
                f"unknown canonical-record schema: {profile.schema_name}/{profile.schema_version}",
                fatal=True,
            ),
        )
    try:
        document = _JsonDocument.parse(revision.content)
    except ValueError as exc:
        return (), (
            _error(
                revision,
                FragmentCompilationErrorCode.MALFORMED_CANONICAL_RECORD,
                str(exc),
                fatal=True,
            ),
        )

    candidates: list[_FragmentCandidate] = []
    errors: list[FragmentCompilationError] = []
    for authority in authority_ranges:
        for descriptor in schema.fields:
            node = document.nodes.get(descriptor.json_pointer)
            if node is None or node.value is None:
                continue
            if descriptor.nested_profile is None:
                candidates.append(
                    _text_candidate(
                        revision.content,
                        "canonical-field",
                        node.start,
                        node.end,
                        authority.eligible_roles,
                        _canonical_value_presentation(node.value),
                    )
                )
                continue
            if not isinstance(node.value, str) or node.string_boundaries is None:
                errors.append(
                    _error(
                        revision,
                        FragmentCompilationErrorCode.SCHEMA_MISMATCH,
                        f"canonical field {descriptor.json_pointer or '/'} is not declared text",
                        start=node.start,
                        end=node.end,
                    )
                )
                continue
            if descriptor.nested_profile == "plain-text":
                nested = tuple(
                    _FragmentCandidate(
                        kind=EvidenceFragmentKind.TEXT,
                        fragment_type="plain-paragraph",
                        start=start,
                        end=end,
                        eligible_roles=authority.eligible_roles,
                        presentation_text=node.value[start:end],
                    )
                    for start, end in _paragraph_ranges(node.value)
                )
                nested_errors: tuple[FragmentCompilationError, ...] = ()
            else:
                nested, nested_errors = _markdown_candidates(
                    revision,
                    node.value,
                    base=0,
                    roles=authority.eligible_roles,
                )
            for candidate in nested:
                assert candidate.start is not None and candidate.end is not None
                raw_start = node.string_boundaries[candidate.start]
                raw_end = node.string_boundaries[candidate.end]
                candidates.append(
                    _text_candidate(
                        revision.content,
                        f"canonical-{candidate.fragment_type}",
                        raw_start,
                        raw_end,
                        candidate.eligible_roles,
                        candidate.presentation_text,
                    )
                )
            for nested_error in nested_errors:
                raw_start = (
                    node.string_boundaries[nested_error.range_start]
                    if nested_error.range_start is not None
                    else node.start
                )
                raw_end = (
                    node.string_boundaries[nested_error.range_end] if nested_error.range_end is not None else node.end
                )
                errors.append(
                    _error(
                        revision,
                        nested_error.code,
                        nested_error.message,
                        start=raw_start,
                        end=raw_end,
                        fatal=nested_error.fatal,
                    )
                )
    return tuple(candidates), tuple(errors)


_ProfileCompiler = Callable[
    [SourceObservationRevision, EvidenceRepresentationProfile, tuple[EvidenceAuthorityRange, ...]],
    tuple[tuple[_FragmentCandidate, ...], tuple[FragmentCompilationError, ...]],
]

_PROFILE_COMPILERS: Mapping[tuple[str, int], _ProfileCompiler] = {
    ("markdown-structural", 1): _compile_markdown_profile,
    ("canonical-record", 1): _compile_canonical_record_profile,
    ("plain-text", 1): _compile_plain_text_profile,
    ("binary-artifact", 1): _compile_binary_artifact_profile,
}


def _markdown_candidates(
    revision: SourceObservationRevision,
    text: str,
    *,
    base: int,
    roles: frozenset[EvidenceRole],
) -> tuple[tuple[_FragmentCandidate, ...], tuple[FragmentCompilationError, ...]]:
    try:
        tokens = MarkdownIt("commonmark").enable("table").parse(text)
    except Exception as exc:
        return (), (
            _error(
                revision,
                FragmentCompilationErrorCode.MALFORMED_MARKDOWN,
                f"Markdown parser rejected the authority range: {type(exc).__name__}",
                start=base,
                end=base + len(text),
            ),
        )
    line_starts = _line_starts(text)
    structural: list[tuple[int, int, int, str, bool]] = []
    token_specs = {
        "html_block": (0, "html-block", True),
        "list_item_open": (1, "markdown-list-item", False),
        "tr_open": (1, "markdown-table-row", False),
        "blockquote_open": (1, "markdown-blockquote", False),
        "heading_open": (2, "markdown-heading", False),
        "fence": (2, "markdown-code-block", False),
        "code_block": (2, "markdown-code-block", False),
        "paragraph_open": (3, "markdown-paragraph", False),
    }
    for token in tokens:
        spec = token_specs.get(token.type)
        if spec is None or token.map is None:
            continue
        start, end = _token_range(text, line_starts, token.map[0], token.map[1])
        if start >= end:
            continue
        priority, fragment_type, is_html = spec
        structural.append((priority, start, end, fragment_type, is_html))

    selected: list[tuple[int, int, str, bool]] = []
    for _, start, end, fragment_type, is_html in sorted(structural):
        if any(start < chosen_end and chosen_start < end for chosen_start, chosen_end, _, _ in selected):
            continue
        selected.append((start, end, fragment_type, is_html))

    candidates: list[_FragmentCandidate] = []
    errors: list[FragmentCompilationError] = []
    for start, end, fragment_type, is_html in sorted(selected):
        raw = text[start:end]
        if is_html:
            html_candidates, html_errors = _html_candidates(
                revision,
                raw,
                base=base + start,
                roles=roles,
            )
            candidates.extend(html_candidates)
            errors.extend(html_errors)
            continue
        presentation = raw
        if fragment_type == "markdown-paragraph" and _HTML_TAG_RE.search(raw):
            presentation = _html_presentation(raw)
            fragment_type = "markdown-inline-html"
        candidates.append(
            _text_candidate(
                revision.content,
                fragment_type,
                base + start,
                base + end,
                roles,
                presentation,
            )
        )
    return tuple(candidates), tuple(errors)


@dataclass(slots=True)
class _HtmlNode:
    tag: str
    start: int
    start_tag_end: int
    end: int | None = None
    children: list[_HtmlNode] = field(default_factory=list)
    unsafe: bool = False


class _OffsetHTMLParser(HTMLParser):
    _VOID_TAGS = frozenset(
        {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    )

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_starts = _line_starts(source)
        self.roots: list[_HtmlNode] = []
        self.stack: list[_HtmlNode] = []
        self.failure: str | None = None

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        start = self._offset()
        raw = self.get_starttag_text() or ""
        node = _HtmlNode(
            tag=tag.lower(),
            start=start,
            start_tag_end=start + len(raw),
            unsafe=tag.lower() in {"script", "style"},
        )
        (self.stack[-1].children if self.stack else self.roots).append(node)
        if tag.lower() in self._VOID_TAGS:
            node.end = node.start_tag_end
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1].tag == tag.lower():
            self.stack[-1].end = self.stack[-1].start_tag_end
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1].tag != tag.lower():
            self.failure = f"mismatched HTML end tag: {tag}"
            return
        start = self._offset()
        end = self.source.find(">", start)
        if end < 0:
            self.failure = f"unterminated HTML end tag: {tag}"
            return
        node = self.stack.pop()
        node.end = end + 1

    def close_checked(self) -> None:
        try:
            self.feed(self.source)
            self.close()
        except Exception as exc:
            self.failure = f"HTML parser failure: {type(exc).__name__}"
        if self.stack and self.failure is None:
            self.failure = f"unclosed HTML element: {self.stack[-1].tag}"


class _HTMLTextCollector(HTMLParser):
    _SEPARATOR_TAGS = frozenset(
        {"br", "p", "li", "tr", "td", "th", "blockquote", "pre", "div", "section", "article", "dt", "dd"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self.unsafe_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() in {"script", "style"}:
            self.unsafe_depth += 1
        elif not self.unsafe_depth and tag.lower() in self._SEPARATOR_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self.unsafe_depth:
            self.unsafe_depth -= 1
        elif not self.unsafe_depth and tag.lower() in self._SEPARATOR_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.unsafe_depth:
            self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if not self.unsafe_depth:
            self.parts.append(html.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        if not self.unsafe_depth:
            self.parts.append(html.unescape(f"&#{name};"))


_HTML_SEMANTIC_TAGS = frozenset(
    {"p", "li", "tr", "blockquote", "pre", "figcaption", "dt", "dd", "h1", "h2", "h3", "h4", "h5", "h6"}
)
_HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")


def _html_candidates(
    revision: SourceObservationRevision,
    source: str,
    *,
    base: int,
    roles: frozenset[EvidenceRole],
) -> tuple[tuple[_FragmentCandidate, ...], tuple[FragmentCompilationError, ...]]:
    parser = _OffsetHTMLParser(source)
    parser.close_checked()
    if parser.failure is not None:
        return (), (
            _error(
                revision,
                FragmentCompilationErrorCode.MALFORMED_HTML,
                parser.failure,
                start=base,
                end=base + len(source),
            ),
        )

    all_nodes = tuple(_walk_html_nodes(parser.roots))
    unsafe_nodes = tuple(node for node in all_nodes if _html_node_has_unsafe_content(node))
    safe_nodes = tuple(
        node
        for node in all_nodes
        if node.end is not None
        and not _html_node_has_unsafe_content(node)
        and _html_presentation(source[node.start : node.end])
    )
    semantic = tuple(node for node in safe_nodes if node.tag in _HTML_SEMANTIC_TAGS)
    selected = tuple(
        node
        for node in semantic
        if not any(
            parent is not node
            and parent.end is not None
            and node.end is not None
            and parent.start <= node.start
            and node.end <= parent.end
            for parent in semantic
        )
    )
    if not selected:
        selected = tuple(
            node
            for node in safe_nodes
            if not any(
                parent is not node
                and parent.end is not None
                and node.end is not None
                and parent.start <= node.start
                and node.end <= parent.end
                for parent in safe_nodes
            )
        )

    candidates = tuple(
        _text_candidate(
            revision.content,
            f"html-{node.tag}",
            base + node.start,
            base + (node.end or node.start),
            roles,
            _html_presentation(source[node.start : node.end]),
        )
        for node in sorted(selected, key=lambda value: (value.start, value.end or value.start, value.tag))
    )
    errors = tuple(
        _error(
            revision,
            FragmentCompilationErrorCode.UNSUPPORTED_HTML,
            f"unsafe HTML element is unselectable: {node.tag}",
            start=base + node.start,
            end=base + (node.end or node.start_tag_end),
        )
        for node in unsafe_nodes
    )
    if not candidates and not errors:
        errors = (
            _error(
                revision,
                FragmentCompilationErrorCode.UNSUPPORTED_HTML,
                "HTML region contains no selectable claim text",
                start=base,
                end=base + len(source),
            ),
        )
    return candidates, errors


def _walk_html_nodes(nodes: Sequence[_HtmlNode]):
    for node in nodes:
        yield node
        yield from _walk_html_nodes(node.children)


def _html_node_has_unsafe_content(node: _HtmlNode) -> bool:
    return node.unsafe or any(_html_node_has_unsafe_content(child) for child in node.children)


def _html_presentation(source: str) -> str:
    collector = _HTMLTextCollector()
    try:
        collector.feed(source)
        collector.close()
    except Exception:
        return ""
    return " ".join("".join(collector.parts).split())


@dataclass(frozen=True, slots=True)
class _JsonNode:
    start: int
    end: int
    value: object
    string_boundaries: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class _JsonDocument:
    value: object
    nodes: Mapping[str, _JsonNode]

    @classmethod
    def parse(cls, source: str) -> _JsonDocument:
        scanner = _JsonScanner(source)
        value, end = scanner.parse_value(0, "")
        end = scanner.skip_space(end)
        if end != len(source):
            raise ValueError("canonical record contains trailing data")
        return cls(value=value, nodes=dict(scanner.nodes))


class _JsonScanner:
    def __init__(self, source: str) -> None:
        self.source = source
        self.nodes: dict[str, _JsonNode] = {}

    def skip_space(self, cursor: int) -> int:
        while cursor < len(self.source) and self.source[cursor].isspace():
            cursor += 1
        return cursor

    def parse_value(self, cursor: int, pointer: str) -> tuple[object, int]:
        cursor = self.skip_space(cursor)
        if cursor >= len(self.source):
            raise ValueError("canonical record ended before a value")
        start = cursor
        char = self.source[cursor]
        if char == '"':
            value, end, boundaries = _parse_json_string(self.source, cursor)
            self.nodes[pointer] = _JsonNode(start=start, end=end, value=value, string_boundaries=boundaries)
            return value, end
        if char == "{":
            value, end = self._parse_object(cursor, pointer)
            self.nodes[pointer] = _JsonNode(start=start, end=end, value=value)
            return value, end
        if char == "[":
            value, end = self._parse_array(cursor, pointer)
            self.nodes[pointer] = _JsonNode(start=start, end=end, value=value)
            return value, end
        try:
            value, end = json.JSONDecoder().raw_decode(self.source, cursor)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid canonical JSON at character {exc.pos}") from exc
        self.nodes[pointer] = _JsonNode(start=start, end=end, value=value)
        return value, end

    def _parse_object(self, cursor: int, pointer: str) -> tuple[dict[str, object], int]:
        result: dict[str, object] = {}
        cursor = self.skip_space(cursor + 1)
        if cursor < len(self.source) and self.source[cursor] == "}":
            return result, cursor + 1
        while True:
            if cursor >= len(self.source) or self.source[cursor] != '"':
                raise ValueError("canonical record object key must be a JSON string")
            key, cursor, _ = _parse_json_string(self.source, cursor)
            if key in result:
                raise ValueError(f"canonical record contains duplicate key: {key}")
            cursor = self.skip_space(cursor)
            if cursor >= len(self.source) or self.source[cursor] != ":":
                raise ValueError("canonical record object key lacks a value")
            child_pointer = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
            value, cursor = self.parse_value(cursor + 1, child_pointer)
            result[key] = value
            cursor = self.skip_space(cursor)
            if cursor < len(self.source) and self.source[cursor] == "}":
                return result, cursor + 1
            if cursor >= len(self.source) or self.source[cursor] != ",":
                raise ValueError("canonical record object is not comma-delimited")
            cursor = self.skip_space(cursor + 1)

    def _parse_array(self, cursor: int, pointer: str) -> tuple[list[object], int]:
        result: list[object] = []
        cursor = self.skip_space(cursor + 1)
        if cursor < len(self.source) and self.source[cursor] == "]":
            return result, cursor + 1
        index = 0
        while True:
            value, cursor = self.parse_value(cursor, f"{pointer}/{index}")
            result.append(value)
            index += 1
            cursor = self.skip_space(cursor)
            if cursor < len(self.source) and self.source[cursor] == "]":
                return result, cursor + 1
            if cursor >= len(self.source) or self.source[cursor] != ",":
                raise ValueError("canonical record array is not comma-delimited")
            cursor = self.skip_space(cursor + 1)


_SIMPLE_JSON_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def _parse_json_string(source: str, start: int) -> tuple[str, int, tuple[int, ...]]:
    cursor = start + 1
    output: list[str] = []
    boundaries = [cursor]
    while cursor < len(source):
        char = source[cursor]
        if char == '"':
            return "".join(output), cursor + 1, tuple(boundaries)
        if char == "\\":
            if cursor + 1 >= len(source):
                raise ValueError("unterminated JSON escape")
            escape = source[cursor + 1]
            if escape in _SIMPLE_JSON_ESCAPES:
                output.append(_SIMPLE_JSON_ESCAPES[escape])
                cursor += 2
                boundaries.append(cursor)
                continue
            if escape != "u" or cursor + 6 > len(source):
                raise ValueError("unsupported JSON escape")
            try:
                codepoint = int(source[cursor + 2 : cursor + 6], 16)
            except ValueError as exc:
                raise ValueError("invalid Unicode JSON escape") from exc
            cursor += 6
            if 0xD800 <= codepoint <= 0xDBFF:
                if cursor + 6 > len(source) or source[cursor : cursor + 2] != "\\u":
                    raise ValueError("unpaired high-surrogate JSON escape")
                low = int(source[cursor + 2 : cursor + 6], 16)
                if not 0xDC00 <= low <= 0xDFFF:
                    raise ValueError("invalid low-surrogate JSON escape")
                cursor += 6
                codepoint = 0x10000 + ((codepoint - 0xD800) << 10) + (low - 0xDC00)
            elif 0xDC00 <= codepoint <= 0xDFFF:
                raise ValueError("unpaired low-surrogate JSON escape")
            output.append(chr(codepoint))
            boundaries.append(cursor)
            continue
        if ord(char) < 0x20:
            raise ValueError("unescaped control character in JSON string")
        output.append(char)
        cursor += 1
        boundaries.append(cursor)
    raise ValueError("unterminated JSON string")


def _catalog_from_candidates(
    revision: SourceObservationRevision,
    profile: EvidenceRepresentationProfile,
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
    candidates: tuple[_FragmentCandidate, ...],
    errors: tuple[FragmentCompilationError, ...],
    *,
    max_fragments: int,
    max_presentation_chars: int,
) -> EvidenceFragmentCatalog:
    ordered = tuple(sorted(candidates, key=_candidate_sort_key))
    if not ordered and not errors:
        errors = (
            _error(
                revision,
                FragmentCompilationErrorCode.NO_SELECTABLE_CONTENT,
                "authority ranges contain no selectable Evidence Fragment",
            ),
        )
    overlap_error = _candidate_overlap_error(revision, ordered)
    if overlap_error is not None:
        errors = (*errors, overlap_error)
        ordered = ()
    presentation_chars = sum(len(candidate.presentation_text) for candidate in ordered)
    if len(ordered) > max_fragments or presentation_chars > max_presentation_chars:
        errors = (
            *errors,
            _error(
                revision,
                FragmentCompilationErrorCode.CATALOG_TOO_LARGE,
                "compiled Fragment catalog exceeds its explicit limits",
                fatal=True,
            ),
        )
        exposed: tuple[_FragmentCandidate, ...] = ()
    elif any(error.fatal for error in errors):
        exposed = ()
    else:
        exposed = ordered

    fragments = tuple(
        _materialize_fragment(revision, candidate, index) for index, candidate in enumerate(exposed, start=1)
    )
    digest = _catalog_digest(
        revision,
        profile,
        authority_ranges,
        ordered,
        errors,
        max_fragments=max_fragments,
        max_presentation_chars=max_presentation_chars,
    )
    return EvidenceFragmentCatalog(
        observation_revision_id=revision.id,
        profile=profile,
        fragments=fragments,
        errors=tuple(sorted(errors, key=_error_sort_key)),
        digest=digest,
        max_fragments=max_fragments,
        max_presentation_chars=max_presentation_chars,
    )


def _fatal_catalog(
    revision: SourceObservationRevision,
    profile: EvidenceRepresentationProfile,
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
    code: FragmentCompilationErrorCode,
    message: str,
    *,
    max_fragments: int,
    max_presentation_chars: int,
) -> EvidenceFragmentCatalog:
    return _catalog_from_candidates(
        revision,
        profile,
        authority_ranges,
        (),
        (_error(revision, code, message, fatal=True),),
        max_fragments=max_fragments,
        max_presentation_chars=max_presentation_chars,
    )


def _materialize_fragment(
    revision: SourceObservationRevision,
    candidate: _FragmentCandidate,
    index: int,
) -> EvidenceFragment:
    if candidate.kind is EvidenceFragmentKind.ARTIFACT:
        anchor = SourceAnchor(
            kind=AnchorKind.WHOLE_OBSERVATION,
            observation_id=revision.observation_id,
            observation_revision_id=revision.id,
        )
        raw_digest = candidate.raw_content_sha256 or ""
    else:
        assert candidate.start is not None and candidate.end is not None
        anchor = SourceAnchor(
            kind=AnchorKind.REVISION_RANGE,
            observation_id=revision.observation_id,
            observation_revision_id=revision.id,
            range_start=candidate.start,
            range_end=candidate.end,
        )
        raw_digest = hashlib.sha256(revision.content[candidate.start : candidate.end].encode("utf-8")).hexdigest()
    return EvidenceFragment(
        reference=f"f{index:06d}",
        kind=candidate.kind,
        fragment_type=candidate.fragment_type,
        anchor=anchor,
        eligible_roles=candidate.eligible_roles,
        raw_content_sha256=raw_digest,
        presentation_text=candidate.presentation_text,
        presentation_sha256=hashlib.sha256(candidate.presentation_text.encode("utf-8")).hexdigest(),
    )


def _catalog_digest(
    revision: SourceObservationRevision,
    profile: EvidenceRepresentationProfile,
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
    candidates: tuple[_FragmentCandidate, ...],
    errors: tuple[FragmentCompilationError, ...],
    *,
    max_fragments: int,
    max_presentation_chars: int,
) -> str:
    payload = {
        "compiler_contract_version": COMPILER_CONTRACT_VERSION,
        "observation_id": revision.observation_id,
        "observation_revision_id": revision.id,
        "profile": {
            "name": profile.name,
            "version": profile.version,
            "coordinate_space": profile.coordinate_space.value,
            "schema_name": profile.schema_name,
            "schema_version": profile.schema_version,
        },
        "authority_ranges": [
            {
                "kind": item.anchor.kind.value,
                "range_start": item.anchor.range_start,
                "range_end": item.anchor.range_end,
                "eligible_roles": sorted(role.value for role in item.eligible_roles),
            }
            for item in sorted(authority_ranges, key=_authority_sort_key)
        ],
        "limits": {
            "max_fragments": max_fragments,
            "max_presentation_chars": max_presentation_chars,
        },
        "fragments": [
            {
                "kind": item.kind.value,
                "fragment_type": item.fragment_type,
                "start": item.start,
                "end": item.end,
                "eligible_roles": sorted(role.value for role in item.eligible_roles),
                "raw_content_sha256": (
                    item.raw_content_sha256
                    if item.raw_content_sha256 is not None
                    else hashlib.sha256(revision.content[item.start : item.end].encode("utf-8")).hexdigest()
                ),
                "presentation_sha256": hashlib.sha256(item.presentation_text.encode("utf-8")).hexdigest(),
            }
            for item in candidates
        ],
        "errors": [
            {
                "code": item.code.value,
                "range_start": item.range_start,
                "range_end": item.range_end,
                "fatal": item.fatal,
            }
            for item in sorted(errors, key=_error_sort_key)
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _candidate_overlap_error(
    revision: SourceObservationRevision,
    candidates: tuple[_FragmentCandidate, ...],
) -> FragmentCompilationError | None:
    text_candidates = tuple(item for item in candidates if item.start is not None and item.end is not None)
    for previous, current in zip(text_candidates, text_candidates[1:]):
        assert previous.end is not None and current.start is not None
        if current.start < previous.end:
            return _error(
                revision,
                FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE,
                "compiled Fragments overlap",
                start=current.start,
                end=previous.end,
                fatal=True,
            )
    return None


def _candidate_sort_key(item: _FragmentCandidate) -> tuple[int, int, str, str, tuple[str, ...]]:
    start = item.start if item.start is not None else -1
    end = item.end if item.end is not None else -1
    raw_digest = item.raw_content_sha256 or ""
    presentation_digest = hashlib.sha256(item.presentation_text.encode("utf-8")).hexdigest()
    return (
        start,
        end,
        item.fragment_type,
        raw_digest + presentation_digest,
        tuple(sorted(role.value for role in item.eligible_roles)),
    )


def _authority_sort_key(item: EvidenceAuthorityRange) -> tuple[int, int, tuple[str, ...]]:
    return (
        item.anchor.range_start if item.anchor.range_start is not None else -1,
        item.anchor.range_end if item.anchor.range_end is not None else -1,
        tuple(sorted(role.value for role in item.eligible_roles)),
    )


def _error_sort_key(item: FragmentCompilationError) -> tuple[int, int, str, str]:
    return (
        item.range_start if item.range_start is not None else -1,
        item.range_end if item.range_end is not None else -1,
        item.code.value,
        item.message,
    )


def _text_candidate(
    authority_text: str,
    fragment_type: str,
    start: int,
    end: int,
    roles: frozenset[EvidenceRole],
    presentation: str,
) -> _FragmentCandidate:
    return _FragmentCandidate(
        kind=EvidenceFragmentKind.TEXT,
        fragment_type=fragment_type,
        start=start,
        end=end,
        eligible_roles=roles,
        presentation_text=presentation,
        raw_content_sha256=hashlib.sha256(authority_text[start:end].encode("utf-8")).hexdigest(),
    )


def _error(
    revision: SourceObservationRevision,
    code: FragmentCompilationErrorCode,
    message: str,
    *,
    start: int | None = None,
    end: int | None = None,
    fatal: bool = False,
) -> FragmentCompilationError:
    return FragmentCompilationError(
        code=code,
        observation_revision_id=revision.id,
        message=message,
        range_start=start,
        range_end=end,
        fatal=fatal,
    )


def _anchor_span(anchor: SourceAnchor, content: str) -> tuple[int, int]:
    if anchor.kind is AnchorKind.WHOLE_OBSERVATION:
        return 0, len(content)
    assert anchor.range_start is not None and anchor.range_end is not None
    return anchor.range_start, anchor.range_end


def _bind_candidates_to_authority(
    revision: SourceObservationRevision,
    candidates: tuple[_FragmentCandidate, ...],
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
) -> tuple[tuple[_FragmentCandidate, ...], tuple[FragmentCompilationError, ...]]:
    bound: list[_FragmentCandidate] = []
    errors: list[FragmentCompilationError] = []
    spans = tuple((*_anchor_span(item.anchor, revision.content), item) for item in authority_ranges)
    for candidate in candidates:
        assert candidate.start is not None and candidate.end is not None
        containing = tuple(item for start, end, item in spans if start <= candidate.start and candidate.end <= end)
        if len(containing) == 1:
            bound.append(replace(candidate, eligible_roles=containing[0].eligible_roles))
            continue
        overlapping = any(candidate.start < end and start < candidate.end for start, end, _ in spans)
        if overlapping:
            errors.append(
                _error(
                    revision,
                    FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE,
                    "structural Fragment crosses an authority boundary and was not clipped",
                    start=candidate.start,
                    end=candidate.end,
                )
            )
    return tuple(bound), tuple(errors)


def _errors_inside_authority(
    errors: tuple[FragmentCompilationError, ...],
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
    content: str,
) -> tuple[FragmentCompilationError, ...]:
    spans = tuple(_anchor_span(item.anchor, content) for item in authority_ranges)
    return tuple(
        error
        for error in errors
        if error.fatal
        or error.range_start is None
        or error.range_end is None
        or any(error.range_start < end and start < error.range_end for start, end in spans)
    )


def _line_starts(text: str) -> tuple[int, ...]:
    starts = [0]
    starts.extend(match.end() for match in re.finditer(r"\n", text))
    return tuple(starts)


def _token_range(text: str, line_starts: tuple[int, ...], start_line: int, end_line: int) -> tuple[int, int]:
    start = line_starts[start_line]
    end = line_starts[end_line] if end_line < len(line_starts) else len(text)
    return _trim_range(text, start, end)


def _trim_range(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _paragraph_ranges(text: str) -> tuple[tuple[int, int], ...]:
    ranges: list[tuple[int, int]] = []
    cursor = 0
    for separator in re.finditer(r"\n[ \t]*\n+", text):
        start, end = _trim_range(text, cursor, separator.start())
        if start < end:
            ranges.append((start, end))
        cursor = separator.end()
    start, end = _trim_range(text, cursor, len(text))
    if start < end:
        ranges.append((start, end))
    return tuple(ranges)


def _canonical_value_presentation(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
