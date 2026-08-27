from __future__ import annotations

import hashlib

import pytest

from memforge.memory.evidence import EvidenceRole
from memforge.pipeline.evidence_fragments import (
    EvidenceAuthorityRange,
    EvidenceFragmentKind,
    FragmentCompilationErrorCode,
    compile_fragments,
)
from memforge.source_projection import (
    AnchorKind,
    EvidenceCoordinateSpace,
    EvidenceRepresentationProfile,
    SourceAnchor,
    SourceObservationRevision,
)


MARKDOWN_PROFILE = EvidenceRepresentationProfile(
    name="markdown-structural",
    version=1,
    coordinate_space=EvidenceCoordinateSpace.UNICODE_SCALAR,
)
PLAIN_PROFILE = EvidenceRepresentationProfile(
    name="plain-text",
    version=1,
    coordinate_space=EvidenceCoordinateSpace.UNICODE_SCALAR,
)
BINARY_PROFILE = EvidenceRepresentationProfile(
    name="binary-artifact",
    version=1,
    coordinate_space=EvidenceCoordinateSpace.WHOLE_ARTIFACT,
)


def _canonical_profile(schema_name: str) -> EvidenceRepresentationProfile:
    return EvidenceRepresentationProfile(
        name="canonical-record",
        version=1,
        coordinate_space=EvidenceCoordinateSpace.UNICODE_SCALAR,
        schema_name=schema_name,
        schema_version=1,
    )


def _revision(
    content: str,
    profile: EvidenceRepresentationProfile,
    *,
    metadata: dict[str, object] | None = None,
) -> SourceObservationRevision:
    return SourceObservationRevision(
        id="obsrev-1",
        observation_id="obs-1",
        semantic_hash=hashlib.sha256(content.encode()).hexdigest(),
        content=content,
        metadata=metadata or {},
        evidence_profile=profile,
    )


def _authority(
    revision: SourceObservationRevision,
    *roles: EvidenceRole,
    start: int | None = None,
    end: int | None = None,
) -> EvidenceAuthorityRange:
    anchor = SourceAnchor(
        kind=AnchorKind.REVISION_RANGE if start is not None else AnchorKind.WHOLE_OBSERVATION,
        observation_id=revision.observation_id,
        observation_revision_id=revision.id,
        range_start=start,
        range_end=end,
    )
    return EvidenceAuthorityRange(anchor=anchor, eligible_roles=frozenset(roles))


def test_profile_name_and_version_are_separate_and_schema_is_typed() -> None:
    with pytest.raises(ValueError, match="must not embed"):
        EvidenceRepresentationProfile(
            name="markdown-structural-v1",
            version=1,
            coordinate_space=EvidenceCoordinateSpace.UNICODE_SCALAR,
        )
    with pytest.raises(ValueError, match="requires a representation schema"):
        EvidenceRepresentationProfile(
            name="canonical-record",
            version=1,
            coordinate_space=EvidenceCoordinateSpace.UNICODE_SCALAR,
        )


def test_markdown_compiles_non_overlapping_structural_fragments() -> None:
    content = """# Heading

Paragraph **one**.

- first item
- second item

| A | B |
| - | - |
| x | y |

> quoted rule

```python
print("safe")
```
"""
    revision = _revision(content, MARKDOWN_PROFILE)

    catalog = compile_fragments(
        revision,
        MARKDOWN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY, EvidenceRole.REQUIRED),),
    )

    assert catalog.usable is True
    assert [item.reference for item in catalog.fragments] == [
        f"f{index:06d}" for index in range(1, len(catalog.fragments) + 1)
    ]
    assert {item.fragment_type for item in catalog.fragments} == {
        "markdown-heading",
        "markdown-paragraph",
        "markdown-list-item",
        "markdown-table-row",
        "markdown-blockquote",
        "markdown-code-block",
    }
    ranges = [
        (item.anchor.range_start, item.anchor.range_end)
        for item in catalog.fragments
        if item.anchor.range_start is not None
    ]
    assert all(current_start >= previous_end for (_, previous_end), (current_start, _) in zip(ranges, ranges[1:]))
    for item in catalog.fragments:
        assert (
            item.raw_content_sha256
            == hashlib.sha256(content[item.anchor.range_start : item.anchor.range_end].encode()).hexdigest()
        )


def test_commonmark_raw_html_compiles_duplicate_list_items_by_exact_offset() -> None:
    content = "<ul><li>Same &amp; safe</li><li>Same &amp; safe</li></ul>"
    revision = _revision(content, MARKDOWN_PROFILE)

    catalog = compile_fragments(
        revision,
        MARKDOWN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY),),
    )

    assert catalog.errors == ()
    assert [item.fragment_type for item in catalog.fragments] == ["html-li", "html-li"]
    assert [item.presentation_text for item in catalog.fragments] == ["Same & safe", "Same & safe"]
    assert [content[item.anchor.range_start : item.anchor.range_end] for item in catalog.fragments] == [
        "<li>Same &amp; safe</li>",
        "<li>Same &amp; safe</li>",
    ]
    assert catalog.fragments[0].anchor.range_start != catalog.fragments[1].anchor.range_start


def test_nested_html_and_table_rows_remain_complete_and_non_overlapping() -> None:
    content = """<ul><li>Outer<ul><li>Inner</li></ul></li></ul>

<table><tr><td>A &amp; B</td><td>C</td></tr></table>"""
    revision = _revision(content, MARKDOWN_PROFILE)

    catalog = compile_fragments(
        revision,
        MARKDOWN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY),),
    )

    assert [item.fragment_type for item in catalog.fragments] == ["html-li", "html-tr"]
    assert [item.presentation_text for item in catalog.fragments] == ["Outer Inner", "A & B C"]
    first, second = catalog.fragments
    assert first.anchor.range_end <= second.anchor.range_start


def test_inline_html_uses_one_exact_paragraph_range_with_tag_free_presentation() -> None:
    content = "Keep <strong>A7</strong> enabled."
    revision = _revision(content, MARKDOWN_PROFILE)

    catalog = compile_fragments(
        revision,
        MARKDOWN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY),),
    )

    assert len(catalog.fragments) == 1
    assert catalog.fragments[0].fragment_type == "markdown-inline-html"
    assert catalog.fragments[0].presentation_text == "Keep A7 enabled."
    assert catalog.fragments[0].anchor.range_start == 0
    assert catalog.fragments[0].anchor.range_end == len(content)


def test_malformed_html_is_unselectable_without_parent_fallback() -> None:
    content = "<div><p>Unclosed</div>"
    revision = _revision(content, MARKDOWN_PROFILE)

    catalog = compile_fragments(
        revision,
        MARKDOWN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY),),
    )

    assert catalog.fragments == ()
    assert [error.code for error in catalog.errors] == [FragmentCompilationErrorCode.MALFORMED_HTML]
    assert catalog.errors[0].fatal is False


def test_unsafe_html_is_excluded_while_safe_sibling_remains_selectable() -> None:
    content = "<div><script>alert(1)</script><p>Safe rule</p></div>"
    revision = _revision(content, MARKDOWN_PROFILE)

    catalog = compile_fragments(
        revision,
        MARKDOWN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY),),
    )

    assert [item.presentation_text for item in catalog.fragments] == ["Safe rule"]
    assert any(error.code is FragmentCompilationErrorCode.UNSUPPORTED_HTML for error in catalog.errors)
    assert "alert" not in str(catalog.model_payload())


def test_html_comment_only_region_is_explicitly_unselectable() -> None:
    content = "<!-- operational note -->"
    revision = _revision(content, MARKDOWN_PROFILE)

    catalog = compile_fragments(
        revision,
        MARKDOWN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY),),
    )

    assert catalog.fragments == ()
    assert catalog.errors[0].code is FragmentCompilationErrorCode.UNSUPPORTED_HTML


def test_canonical_record_nested_markdown_maps_unicode_escape_to_raw_json() -> None:
    content = r'{"attachments":[],"body":"Rule \u4e2d and **bold**."}'
    profile = _canonical_profile("jira-comment")
    revision = _revision(content, profile)

    catalog = compile_fragments(
        revision,
        profile,
        (_authority(revision, EvidenceRole.PRIMARY, EvidenceRole.REQUIRED),),
    )

    assert catalog.errors == ()
    assert len(catalog.fragments) == 1
    fragment = catalog.fragments[0]
    assert fragment.fragment_type == "canonical-markdown-paragraph"
    assert fragment.presentation_text == "Rule 中 and **bold**."
    assert content[fragment.anchor.range_start : fragment.anchor.range_end] == r"Rule \u4e2d and **bold**."
    assert "attachments" not in fragment.presentation_text


def test_canonical_record_rejects_declared_text_with_wrong_runtime_type() -> None:
    content = '{"body":{"type":"doc"}}'
    profile = _canonical_profile("jira-comment")
    revision = _revision(content, profile)

    catalog = compile_fragments(
        revision,
        profile,
        (_authority(revision, EvidenceRole.PRIMARY),),
    )

    assert catalog.fragments == ()
    assert [error.code for error in catalog.errors] == [FragmentCompilationErrorCode.SCHEMA_MISMATCH]


def test_canonical_record_rejects_unpaired_unicode_escape() -> None:
    content = r'{"body":"bad \ud800 escape"}'
    profile = _canonical_profile("jira-comment")
    revision = _revision(content, profile)

    catalog = compile_fragments(
        revision,
        profile,
        (_authority(revision, EvidenceRole.PRIMARY),),
    )

    assert catalog.fragments == ()
    assert catalog.errors[0].code is FragmentCompilationErrorCode.MALFORMED_CANONICAL_RECORD
    assert catalog.errors[0].fatal is True


def test_required_only_authority_cannot_resolve_as_primary() -> None:
    revision = _revision("Dependency rule.", PLAIN_PROFILE)

    catalog = compile_fragments(
        revision,
        PLAIN_PROFILE,
        (_authority(revision, EvidenceRole.REQUIRED),),
    )

    reference = catalog.fragments[0].reference
    assert catalog.resolve(reference, EvidenceRole.PRIMARY) is None
    assert catalog.resolve(reference, EvidenceRole.REQUIRED) == catalog.fragments[0]
    assert catalog.resolve("f999999", EvidenceRole.REQUIRED) is None


def test_structural_fragment_crossing_authority_boundary_is_rejected_not_clipped() -> None:
    content = "Complete paragraph must remain atomic."
    revision = _revision(content, MARKDOWN_PROFILE)

    catalog = compile_fragments(
        revision,
        MARKDOWN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY, start=9, end=18),),
    )

    assert catalog.fragments == ()
    assert catalog.errors[0].code is FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE
    assert "not clipped" in catalog.errors[0].message
    assert catalog.errors[0].range_start == 0
    assert catalog.errors[0].range_end == len(content)


def test_separate_authority_ranges_assign_roles_without_cross_range_widening() -> None:
    content = "Primary claim.\n\nRequired condition."
    revision = _revision(content, PLAIN_PROFILE)
    required_start = content.index("Required")

    catalog = compile_fragments(
        revision,
        PLAIN_PROFILE,
        (
            _authority(
                revision,
                EvidenceRole.PRIMARY,
                start=0,
                end=len("Primary claim."),
            ),
            _authority(
                revision,
                EvidenceRole.REQUIRED,
                start=required_start,
                end=len(content),
            ),
        ),
    )

    primary, required = catalog.fragments
    assert catalog.resolve(primary.reference, EvidenceRole.PRIMARY) == primary
    assert catalog.resolve(primary.reference, EvidenceRole.REQUIRED) is None
    assert catalog.resolve(required.reference, EvidenceRole.PRIMARY) is None
    assert catalog.resolve(required.reference, EvidenceRole.REQUIRED) == required


def test_catalog_retry_reconstructs_identical_refs_hashes_and_digest() -> None:
    revision = _revision("One.\n\nTwo.", PLAIN_PROFILE)
    ranges = (_authority(revision, EvidenceRole.PRIMARY, EvidenceRole.REQUIRED),)

    first = compile_fragments(revision, PLAIN_PROFILE, ranges)
    retry = compile_fragments(revision, PLAIN_PROFILE, ranges)

    assert retry == first


def test_catalog_digest_changes_when_role_eligibility_or_limits_change() -> None:
    revision = _revision("One.", PLAIN_PROFILE)

    primary = compile_fragments(
        revision,
        PLAIN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY),),
    )
    required = compile_fragments(
        revision,
        PLAIN_PROFILE,
        (_authority(revision, EvidenceRole.REQUIRED),),
    )
    larger_limit = compile_fragments(
        revision,
        PLAIN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY),),
        max_fragments=4_096,
    )

    assert len({primary.digest, required.digest, larger_limit.digest}) == 3


def test_catalog_limits_fail_closed_without_truncating_or_merging() -> None:
    revision = _revision("One.\n\nTwo.", PLAIN_PROFILE)

    catalog = compile_fragments(
        revision,
        PLAIN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY),),
        max_fragments=1,
    )

    assert catalog.fragments == ()
    assert catalog.errors[-1].code is FragmentCompilationErrorCode.CATALOG_TOO_LARGE
    assert catalog.errors[-1].fatal is True


def test_binary_artifact_uses_whole_revision_byte_digest() -> None:
    digest = "a" * 64
    revision = _revision(
        "",
        BINARY_PROFILE,
        metadata={
            "source_artifact": {
                "sha256": digest,
                "inference_eligible": True,
                "filename": "diagram.png",
            }
        },
    )

    catalog = compile_fragments(
        revision,
        BINARY_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY),),
    )

    assert catalog.usable is True
    assert catalog.fragments[0].kind is EvidenceFragmentKind.ARTIFACT
    assert catalog.fragments[0].anchor.kind is AnchorKind.WHOLE_OBSERVATION
    assert catalog.fragments[0].raw_content_sha256 == digest
    assert "diagram.png" not in str(catalog.model_payload())


def test_out_of_bounds_authority_range_fails_closed() -> None:
    revision = _revision("short", PLAIN_PROFILE)

    catalog = compile_fragments(
        revision,
        PLAIN_PROFILE,
        (_authority(revision, EvidenceRole.PRIMARY, start=0, end=99),),
    )

    assert catalog.fragments == ()
    assert catalog.errors[0].code is FragmentCompilationErrorCode.INVALID_AUTHORITY_RANGE
    assert catalog.errors[0].fatal is True
