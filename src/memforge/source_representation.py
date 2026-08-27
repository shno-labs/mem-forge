"""Adapter-owned Evidence representation declarations for Source Projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from memforge.source_projection import (
    EvidenceCoordinateSpace,
    EvidenceRepresentationProfile,
)


MARKDOWN_STRUCTURAL_PROFILE = EvidenceRepresentationProfile(
    name="markdown-structural",
    version=1,
    coordinate_space=EvidenceCoordinateSpace.UNICODE_SCALAR,
)
BINARY_ARTIFACT_PROFILE = EvidenceRepresentationProfile(
    name="binary-artifact",
    version=1,
    coordinate_space=EvidenceCoordinateSpace.WHOLE_ARTIFACT,
)


@dataclass(frozen=True, slots=True)
class EvidenceProfileBackfillReport:
    """Exact result of classifying legacy Observation Revisions."""

    scanned_revision_count: int
    backfilled_revision_count: int
    unresolved_revision_ids: tuple[str, ...]


def _canonical_record_profile(schema_name: str) -> EvidenceRepresentationProfile:
    return EvidenceRepresentationProfile(
        name="canonical-record",
        version=1,
        coordinate_space=EvidenceCoordinateSpace.UNICODE_SCALAR,
        schema_name=schema_name,
        schema_version=1,
    )


_REPRESENTATION_CONTRACTS: Mapping[tuple[str, str], EvidenceRepresentationProfile] = {
    ("confluence", "page_body"): MARKDOWN_STRUCTURAL_PROFILE,
    ("jira", "issue_core"): _canonical_record_profile("jira-issue-core"),
    ("jira", "comment"): _canonical_record_profile("jira-comment"),
    ("jira", "changelog"): _canonical_record_profile("jira-changelog"),
    ("github_repo", "file_content"): MARKDOWN_STRUCTURAL_PROFILE,
    ("github_pages", "page_content"): MARKDOWN_STRUCTURAL_PROFILE,
    ("local_markdown", "file_content"): MARKDOWN_STRUCTURAL_PROFILE,
    ("teams", "message"): _canonical_record_profile("teams-message"),
    ("agent_session", "session_summary"): MARKDOWN_STRUCTURAL_PROFILE,
}


def representation_profile_for_observation_contract(
    *,
    source_type: str,
    observation_type: str,
) -> EvidenceRepresentationProfile | None:
    """Declare a stored adapter contract without inspecting content or MIME."""

    if observation_type == "binary_artifact":
        return BINARY_ARTIFACT_PROFILE
    if observation_type == "document_content":
        # The extension-safe projection fallback is explicitly normalized Markdown.
        return MARKDOWN_STRUCTURAL_PROFILE
    return _REPRESENTATION_CONTRACTS.get((source_type, observation_type))
