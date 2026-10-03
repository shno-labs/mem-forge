"""Jira-owned immutable record fields and comparison semantics."""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from memforge.source_adapters.contracts import CanonicalRecordField, CanonicalRecordSchema
from memforge.source_adapters.jira_html import RENDERED_HTML_FORMAT
from memforge.source_projection import EvidenceCoordinateSpace, EvidenceRepresentationProfile
from memforge.source_time import latest_source_time, reported_source_time


CANONICAL_RECORD_SCHEMAS: Mapping[tuple[str, int], CanonicalRecordSchema] = {
    ("jira-issue-core", 1): CanonicalRecordSchema(
        name="jira-issue-core",
        version=1,
        fields=(
            CanonicalRecordField("/summary"),
            CanonicalRecordField("/description", nested_profile="markdown-structural"),
            CanonicalRecordField(
                "/status",
                comparison_keys=("id", "key", "name", "value"),
            ),
            CanonicalRecordField(
                "/priority",
                comparison_keys=("id", "key", "name", "value"),
            ),
            CanonicalRecordField(
                "/assignee",
                comparison_keys=(
                    "accountId",
                    "id",
                    "key",
                    "name",
                    "displayName",
                ),
            ),
            CanonicalRecordField("/labels"),
            CanonicalRecordField(
                "/resolution",
                comparison_keys=("id", "key", "name", "value"),
            ),
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
        model_interpretation=(
            "fromString is the previous field value; toString is the new value. "
            "field identifies the changed field and created records the change event. "
            "The event time alone does not establish when a business rule becomes effective."
        ),
        fields=(
            CanonicalRecordField("/created", contextual=True),
            CanonicalRecordField("/items/*/field", contextual=True),
            CanonicalRecordField("/items/*/fromString", nested_profile="markdown-structural"),
            CanonicalRecordField("/items/*/toString", nested_profile="markdown-structural"),
        ),
    ),
}


CORE_FIELDS = ("summary", "description", "status", "priority", "assignee", "labels", "resolution")
OPERATIONAL_HISTORY_FIELDS = frozenset({
    "assignee", "due date", "duedate", "fix version", "fix version/s", "fixversion",
    "labels", "priority", "rank", "resolution", "sprint", "status",
})

ISSUE_SCHEMA = replace(
    CANONICAL_RECORD_SCHEMAS[("jira-issue-core", 1)],
    version=2,
    fields=tuple(
        CanonicalRecordField("/description", text_format=RENDERED_HTML_FORMAT)
        if field.json_pointer == "/description" else field
        for field in CANONICAL_RECORD_SCHEMAS[("jira-issue-core", 1)].fields
    ),
)
COMMENT_SCHEMA = CanonicalRecordSchema(
    name="jira-comment", version=2,
    fields=(CanonicalRecordField("/body", text_format=RENDERED_HTML_FORMAT),),
)
CHANGELOG_SCHEMA = replace(
    CANONICAL_RECORD_SCHEMAS[("jira-changelog", 1)],
    version=2,
    fields=tuple(
        replace(field, nested_profile="plain-text") if field.nested_profile else field
        for field in CANONICAL_RECORD_SCHEMAS[("jira-changelog", 1)].fields
    ),
    model_interpretation=(
        "fromString is the previous literal native field value; toString is the new value. "
        "These historical strings have no provider-rendered HTML view and are not declared Markdown. "
        "field identifies the changed field and created records the change event. "
        "The event time alone does not establish when a business rule becomes effective."
    ),
)
CANONICAL_RECORD_SCHEMAS = {
    **CANONICAL_RECORD_SCHEMAS,
    **{(schema.name, schema.version): schema for schema in (ISSUE_SCHEMA, COMMENT_SCHEMA, CHANGELOG_SCHEMA)},
}


def _profile(schema_name: str, version: int) -> EvidenceRepresentationProfile:
    return EvidenceRepresentationProfile(
        "canonical-record", 1, EvidenceCoordinateSpace.UNICODE_SCALAR,
        schema_name=schema_name, schema_version=version,
    )


CURRENT_OBSERVATION_PROFILES = {
    ("jira", observation_type): _profile(schema_name, 2)
    for observation_type, schema_name in (
        ("issue_core", ISSUE_SCHEMA.name), ("comment", COMMENT_SCHEMA.name),
        ("changelog", CHANGELOG_SCHEMA.name),
    )
}
LEGACY_OBSERVATION_PROFILES = {
    key: replace(profile, schema_version=1) for key, profile in CURRENT_OBSERVATION_PROFILES.items()
}


def _current_rendering(native: object, rendered: object, field_name: str) -> str | None:
    if native is None or native == "":
        if rendered is not None and rendered != "":
            raise ValueError(f"Jira {field_name} rendering has no matching native value")
        return native
    if not isinstance(native, str):
        raise ValueError(f"Jira {field_name} requires a string native value")
    if not isinstance(rendered, str) or not rendered.strip():
        raise ValueError(f"Jira {field_name} requires its snapshot's explicit provider-rendered HTML")
    # Validate before persistence: unsupported syntax cannot become an apparently
    # complete revision whose meaningful field is silently omitted downstream.
    parsed = RENDERED_HTML_FORMAT.parse(rendered)
    if native.strip() and not parsed.fragments:
        raise ValueError(f"Jira {field_name} rendering has no selectable view of its native value")
    return rendered


def issue_record(data: Mapping[str, object]) -> dict[str, object]:
    """Keep native and rendered values from the same returned issue snapshot."""
    fields = data.get("fields")
    if not isinstance(fields, Mapping):
        raise ValueError("Jira issue record requires its fetched fields")
    rendered = data.get("renderedFields")
    native = fields.get("description")
    description = rendered.get("description") if isinstance(rendered, Mapping) else None
    return {
        **{name: fields.get(name) for name in CORE_FIELDS},
        "description": _current_rendering(native, description, "description"),
        "native_description": native,
        "representation": f"{ISSUE_SCHEMA.name}:{ISSUE_SCHEMA.version}",
    }


def comment_record(comment: Mapping[str, object]) -> dict[str, object]:
    """The comment body's explicit renderedBody expansion and original value."""
    native = comment.get("body")
    return {
        "body": _current_rendering(native, comment.get("renderedBody"), "comment body"),
        "native_body": native,
        "attachments": comment.get("attachments"),
        "representation": f"{COMMENT_SCHEMA.name}:{COMMENT_SCHEMA.version}",
    }


def changelog_record(history: Mapping[str, object]) -> dict[str, object]:
    """Retain prior/new strings as recorded, without borrowing current rendering."""
    items = history.get("items")
    if not isinstance(items, list):
        raise ValueError("Jira changelog record requires its fetched change items")
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("Jira changelog has a malformed change item")
        if any(item.get(name) is not None and not isinstance(item[name], str) for name in ("fromString", "toString")):
            raise ValueError("Jira changelog values require literal native strings")
    return {**history, "representation": f"{CHANGELOG_SCHEMA.name}:{CHANGELOG_SCHEMA.version}"}


def core_revised_at(
    fields: Mapping[str, object], histories: list[object], *, changelog_complete: bool,
) -> str | None:
    """Latest core-field change, or creation when complete history has none.

    A truncated changelog cannot attest this time. The issue updated timestamp
    also moves for comments and other fields and is not a core-field timestamp.
    """
    if not changelog_complete:
        return None
    core_change_times = [
        history.get("created") for history in histories
        if isinstance(history, Mapping) and any(
            isinstance(entry, Mapping)
            and str(entry.get("fieldId") or entry.get("field") or "").strip().lower() in CORE_FIELDS
            for entry in (history.get("items") if isinstance(history.get("items"), list) else [])
        )
    ]
    return latest_source_time(core_change_times) if core_change_times else reported_source_time(fields.get("created"))


def changelog_semantic_class(history: Mapping[str, object]) -> str:
    """Jira field ownership distinguishes attachments, operations and domain changes."""
    items = history.get("items")
    fields = {
        " ".join(str(item.get("field") or "").strip().lower().split())
        for item in (items if isinstance(items, list) else []) if isinstance(item, Mapping)
    } - {""}
    if fields and fields <= {"attachment"}:
        return "attachment_event"
    if fields and fields <= OPERATIONAL_HISTORY_FIELDS:
        return "operational_transition"
    return "domain_transition"
