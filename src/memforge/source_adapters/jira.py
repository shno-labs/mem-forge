"""Jira-owned immutable record fields and comparison semantics."""

from __future__ import annotations

from typing import Mapping

from memforge.source_adapters.contracts import CanonicalRecordField, CanonicalRecordSchema


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
        fields=(
            CanonicalRecordField("/created", contextual=True),
            CanonicalRecordField("/items/*/field", contextual=True),
            CanonicalRecordField("/items/*/fromString", nested_profile="markdown-structural"),
            CanonicalRecordField("/items/*/toString", nested_profile="markdown-structural"),
        ),
    ),
}
