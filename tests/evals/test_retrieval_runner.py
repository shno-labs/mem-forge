from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_sqlite_runner_executes_core_hard_cases(tmp_path) -> None:
    from memforge.evals.retrieval import load_case_set
    from memforge.evals.retrieval.runner import run_sqlite_case_set

    report = await run_sqlite_case_set(
        load_case_set("retrieval-core-v1"),
        db_path=tmp_path / "retrieval-eval.db",
    )

    assert report.case_count == 4
    assert report.hard_failures == ()

    assert report.case_results["exact_external_id_lookup"].ranked_ids[0] == "mem-blocker-hint"
    assert report.case_results["metadata_title_exact"].rank("mem-access-review") <= 3
    assert report.case_results["compact_trigram_metadata_recall"].rank("mem-blocker-hint") <= 10
    assert report.case_results["queryless_source_listing"].total_candidates == 17

    assert report.qrels["metadata_title_exact"] == {"mem-access-review": 3}
    assert report.run["exact_external_id_lookup"]["mem-blocker-hint"] > 0
    assert report.to_json()["summary"] == {
        "case_count": 4,
        "hard_failures": 0,
    }


@pytest.mark.asyncio
async def test_sqlite_runner_reports_required_channel_failure(tmp_path) -> None:
    from memforge.evals.retrieval import load_case_set
    from memforge.evals.retrieval.runner import run_sqlite_case_set

    case_set = load_case_set("retrieval-core-v1").replace_case(
        "metadata_title_exact",
        expected=load_case_set("retrieval-core-v1")
        .get_case("metadata_title_exact")
        .expected.with_required_channels(
            "mem-access-review",
            ("graph",),
        ),
    )

    report = await run_sqlite_case_set(case_set, db_path=tmp_path / "retrieval-eval.db")

    assert len(report.hard_failures) == 1
    assert report.hard_failures[0].case_id == "metadata_title_exact"
    assert "graph" in report.hard_failures[0].message
