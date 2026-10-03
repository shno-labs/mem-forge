"""Jira's attested current rendering, literal history and revision correspondence."""

import hashlib
import json

import pytest

from memforge.pipeline.evidence_fragments import build_revision_fragment_index
from memforge.pipeline.source_projection_adapters import project_source_item
from memforge.pipeline.support_reading import EvidenceCorrespondence
from memforge.source_adapters.jira import (
    CANONICAL_RECORD_SCHEMAS,
    CURRENT_OBSERVATION_PROFILES,
    LEGACY_OBSERVATION_PROFILES,
    changelog_record,
    changelog_semantic_class,
    comment_record,
    core_revised_at,
    issue_record,
)
from memforge.source_adapters.jira_html import parse_rendered_html
from tests.test_confluence_native_evidence import planned
from tests.test_source_projection_adapters import _inputs, _item, _jira_payload


def projection(native, html, *, prior=None, comments=None, histories=None):
    item = _item(item_id="jira-PAY-12", title="Payroll", extra={"issue_id": "10012"})
    payload = _jira_payload(field_overrides={"description": native}, comments=comments, histories=histories)
    payload["renderedFields"] = {"description": html}
    raw, body = _inputs(item, payload, markdown="INTENTIONALLY WRONG NORMALIZATION")
    return project_source_item(
        source_id="src", source_type="jira", run_id="r2" if prior else "r1",
        item=item, raw=raw, normalized=body,
        prior_unit_revision=prior.source_unit_revisions[0] if prior else None,
        prior_observation_revisions={r.observation_id: r for r in prior.observation_revisions} if prior else None,
    )


def test_current_html_is_attested_and_native_value_is_retained_without_duplicate_extraction():
    native = '{code:html}<form role="region"><layout sap{code}'
    html = '<p>Only after approval.</p><pre class="code-html">&lt;form role="region"&gt;&lt;layout sap</pre>'
    projected = projection(native, html)
    revision = projected.observation_revisions[0]
    record = json.loads(revision.content)
    assert record["native_description"] == native
    assert record["description"] == html
    assert record["representation"] == "jira-issue-core:2"
    index = build_revision_fragment_index(revision)
    assert not index.errors
    views = [f.presentation_text for f in index.fragments]
    assert 'Code (language: html):\n<form role="region"><layout sap' in views
    assert all("{code}" not in view and "WRONG NORMALIZATION" not in view for view in views)
    assert views.count("Only after approval.") == 1
    for fragment in index.fragments:
        anchor = fragment.anchor
        assert hashlib.sha256(revision.content[anchor.range_start:anchor.range_end].encode()).hexdigest() == fragment.raw_content_sha256


def test_syntax_highlighting_offsets_and_unrelated_native_edits_keep_unique_code_correspondence():
    native = '{code:html}<form role="region"><layout sap{code}'
    old_html = '<p>Scope.</p><pre class="code-html"><span class="code-tag">&lt;form role=<span class="code-quote">"region"</span>&gt;</span>&lt;layout sap</pre>'
    base = projection(native, old_html)
    old = next(f for f in build_revision_fragment_index(base.observation_revisions[0]).fragments if f.fragment_type.endswith("pre"))
    new_html = '<p>New unrelated paragraph.</p><p>Scope.</p><pre class="code-html">&lt;form role="region"&gt;&lt;layout sap</pre>'
    target = projection("New paragraph. " + native, new_html, prior=base)
    _, plan = planned(base, target, old)
    assert plan.parts[0].status is EvidenceCorrespondence.EXACT_UNCHANGED
    rebound = plan.parts[0].current[0]
    assert rebound.anchor.range_start != old.anchor.range_start
    assert rebound.raw_content_sha256 != old.raw_content_sha256
    assert rebound.presentation_text == old.presentation_text


def test_literal_history_is_not_rendered_as_current_html_or_markdown():
    old = '{code:html}<form role="region"><layout old{code}'
    new = '{code:html}<form role="region"><layout new{code}'
    history = {"id": "9", "created": "2026-01-01T12:00:00Z", "items": [
        {"field": "description", "fromString": old, "toString": new},
    ]}
    projected = projection(new, '<pre>&lt;form role="region"&gt;&lt;layout new</pre>', histories=[history])
    revision = next(r for r in projected.observation_revisions if r.evidence_profile.schema_name == "jira-changelog")
    index = build_revision_fragment_index(revision)
    assert not index.errors
    assert old in [f.presentation_text for f in index.fragments]
    assert new in [f.presentation_text for f in index.fragments]
    assert "previous literal native" in CANONICAL_RECORD_SCHEMAS[("jira-changelog", 2)].model_interpretation
    assert json.loads(revision.content)["items"] == history["items"]


def test_comment_rendered_body_and_attachment_identity_survive_projection():
    comment = {"id": "20", "body": "*Not resolved*", "renderedBody": '<p><del>Resolved</del> Still pending.</p>', "attachments": [{"id": "33"}]}
    projected = projection(None, None, comments=[comment])
    revision = next(r for r in projected.observation_revisions if r.evidence_profile.schema_name == "jira-comment")
    record = json.loads(revision.content)
    assert record["native_body"] == comment["body"]
    assert record["attachments"] == [{"id": "33"}]
    index = build_revision_fragment_index(revision)
    assert not index.errors
    assert any("[deleted: Resolved] Still pending." == f.presentation_text for f in index.fragments)


@pytest.mark.parametrize("rendered", [None, 42, "", "   "])
def test_nonempty_current_native_without_explicit_html_is_rejected(rendered):
    with pytest.raises(ValueError, match="explicit provider-rendered HTML"):
        issue_record({"fields": {"description": "Native body"}, "renderedFields": {"description": rendered}})
    with pytest.raises(ValueError, match="explicit provider-rendered HTML"):
        comment_record({"body": "Native body", "renderedBody": rendered})


@pytest.mark.parametrize("native", [None, ""])
def test_truly_absent_native_fields_need_no_rendering(native):
    assert issue_record({"fields": {"description": native}})["description"] == native
    assert comment_record({"body": native})["body"] == native


def test_unmatched_rendering_or_nonstring_native_is_not_a_fallback():
    with pytest.raises(ValueError, match="no matching native"):
        issue_record({"fields": {}, "renderedFields": {"description": "<p>Stale</p>"}})
    with pytest.raises(ValueError, match="string native"):
        comment_record({"body": {"type": "doc"}, "renderedBody": "<p>Text</p>"})
    with pytest.raises(ValueError, match="literal native strings"):
        changelog_record({"items": [{"fromString": {"doc": "value"}}]})
    with pytest.raises(ValueError, match="no selectable view"):
        issue_record({"fields": {"description": "Missing meaningful value"}, "renderedFields": {"description": "<p> </p>"}})


def test_inline_literal_code_whitespace_and_link_label_are_preserved():
    fragment = parse_rendered_html('<p>Use <tt>a  b &lt;x&gt;</tt> at <a title="Other title" href="/guide">the guide</a>.</p>').fragments[0]
    assert fragment.presentation == "Use a  b <x> at the guide (/guide; title: Other title)."
    changed = parse_rendered_html('<p>Use <tt>a b &lt;x&gt;</tt> at <a title="Other title" href="/guide">the guide</a>.</p>').fragments[0]
    assert changed.content_value != fragment.content_value


def test_link_destination_and_deletion_remain_meaningful_comparison_material():
    source = '<p><del>Use A.</del> Use <a href="https://example.test/B">B</a>.</p>'
    original = parse_rendered_html(source).fragments[0]
    assert "[deleted: Use A.]" in original.presentation
    assert "https://example.test/B" in original.presentation
    assert parse_rendered_html(source.replace("example.test/B", "example.test/C")).fragments[0].content_value != original.content_value
    assert parse_rendered_html(source.replace("<del>", "<span>").replace("</del>", "</span>")).fragments[0].content_value != original.content_value


def test_inline_word_boundary_change_requires_changed_evidence_correspondence():
    base = projection("A B C", '<p>A<b> B </b>C</p>')
    old = next(f for f in build_revision_fragment_index(base.observation_revisions[0]).fragments if f.presentation_text == "A B C")
    target = projection("ABC", '<p>A<b>B</b>C</p>', prior=base)
    _, plan = planned(base, target, old)
    assert plan.parts[0].status is not EvidenceCorrespondence.EXACT_UNCHANGED
    assert old.content_value != next(f.content_value for f in build_revision_fragment_index(target.observation_revisions[0]).fragments if f.presentation_text == "ABC")


def test_attachment_preview_keeps_identity_and_does_not_invent_image_content():
    source = '<p><span class="image-wrap" style=""><a id="33_thumb" href="/attachment/33/design.png" file-preview-id="33" file-preview-title="design.png"><img src="/thumbnail/33.png" role="presentation" style="border: 0px solid black"/></a></span></p>'
    fragment = parse_rendered_html(source).fragments[0]
    assert fragment.presentation == "design.png (/attachment/33/design.png; attachment: 33)"
    assert parse_rendered_html(source.replace('id="33_thumb" ', "")).fragments[0].content_value == fragment.content_value
    changed = source.replace('file-preview-id="33"', 'file-preview-id="34"').replace('id="33_thumb"', 'id="34_thumb"')
    assert parse_rendered_html(changed).fragments[0].content_value != fragment.content_value
    with_caption = source.replace('<img ', 'Before correction: <img ')
    assert "Before correction:" in parse_rendered_html(with_caption).fragments[0].presentation
    with_alt = source.replace('<img ', '<img alt="Draft arrangement" ')
    assert "Draft arrangement" in parse_rendered_html(with_alt).fragments[0].presentation


def test_entity_spelling_and_attribute_order_do_not_change_values():
    a = parse_rendered_html('<p>A&#66; <a href="/rule" title="Rule">Rule</a></p>').fragments[0]
    b = parse_rendered_html('<p>AB <a title="Rule" href="/rule">Rule</a></p>').fragments[0]
    assert a.content_value == b.content_value


def test_table_headers_and_ordered_list_numbering_remain_readable_context():
    source = '<table><tr><th>Period</th><th>Allowed</th></tr><tr><td>Current</td><td>No</td></tr></table><ol start="3"><li>Approval</li><li value="7">Execute</li></ol>'
    parsed = parse_rendered_html(source)
    assert parsed.fragments[1].presentation == "Period: Current\nAllowed: No"
    assert parsed.groups[0].context_ranges == ((parsed.fragments[0].start, parsed.fragments[0].end),)
    assert parsed.fragments[2].presentation == "3. Approval\n7. Execute"


@pytest.mark.parametrize("source", [
    '<p>Open', '<p><em>Wrong nesting</p></em>', '<script>ignore me</script>',
    '<p a="x" a="y">Duplicated attribute</p>', '<!--hidden--><p>Visible</p>',
    '<table><tr><td rowspan="2">Ambiguous grid</td></tr></table>',
    '<div class="container"><table><tr><td rowspan="2">Ambiguous grid</td></tr></table></div>',
    '<p><span style="color:red">Red means rejected.</span></p>',
    '<p><span style="display:none">Hidden exception</span>Visible rule</p>',
    '<p hidden="hidden">Hidden rule</p>',
    '<p><span class="unknown-widget">Widget interpretation</span></p>',
    '<a href="/rule" rel="alternate">Other rule</a>',
])
def test_unsupported_or_malformed_html_fails_as_a_whole(source):
    with pytest.raises(ValueError):
        parse_rendered_html(source)
    with pytest.raises(ValueError):
        issue_record({"fields": {"description": "Native"}, "renderedFields": {"description": source}})


def test_schema_cutover_keeps_historical_profile_truth():
    for key, profile in CURRENT_OBSERVATION_PROFILES.items():
        assert profile.schema_version == 2
        legacy = LEGACY_OBSERVATION_PROFILES[key]
        assert legacy.schema_version == 1
        schema = CANONICAL_RECORD_SCHEMAS[(legacy.schema_name, legacy.schema_version)]
        assert any(field.nested_profile == "markdown-structural" for field in schema.fields)


def test_adapter_owns_history_classification_and_core_field_time():
    fields = {"created": "2026-01-01T12:00:00Z", "updated": "2026-05-01T12:00:00Z"}
    comment_event = {"created": "2026-03-01T12:00:00Z", "items": [{"field": "Attachment"}]}
    core_event = {"created": "2026-02-01T12:00:00Z", "items": [{"fieldId": "description"}]}
    assert core_revised_at(fields, [comment_event, core_event], changelog_complete=True) == "2026-02-01T12:00:00+00:00"
    assert core_revised_at(fields, [comment_event], changelog_complete=True) == "2026-01-01T12:00:00+00:00"
    assert core_revised_at(fields, [core_event], changelog_complete=False) is None
    assert changelog_semantic_class(comment_event) == "attachment_event"
    assert changelog_semantic_class({"items": [{"field": "Due Date"}, {"field": "status"}]}) == "operational_transition"
    assert changelog_semantic_class(core_event) == "domain_transition"
