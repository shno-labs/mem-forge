"""Origin-source selection for the leading source glyph in the admin UI.

`_pick_origin_source_type` decides which of a memory's sources represents it in
list and detail views: the extraction origin when present, else the first
attached source. Pairs are (source_type, support_kind), ordered oldest-first.
"""

from memforge.server.admin_api import _pick_origin_source_type


def test_no_sources_has_no_origin():
    assert _pick_origin_source_type([]) is None


def test_extracted_origin_wins_over_corroborated():
    pairs = [("jira", "corroborated"), ("confluence", "extracted")]
    assert _pick_origin_source_type(pairs) == "confluence"


def test_first_source_used_without_extracted():
    pairs = [("teams", "corroborated"), ("jira", "corroborated")]
    assert _pick_origin_source_type(pairs) == "teams"


def test_missing_support_kind_falls_back_to_first():
    assert _pick_origin_source_type([("github_pages", None)]) == "github_pages"


def test_first_extracted_wins_when_several():
    pairs = [("teams", "corroborated"), ("jira", "extracted"), ("confluence", "extracted")]
    assert _pick_origin_source_type(pairs) == "jira"
