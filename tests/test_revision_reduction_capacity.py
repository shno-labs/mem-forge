"""Complete scanning must not reject reducible current proof as over capacity."""

import json
from dataclasses import replace

import pytest

from memforge.pipeline.revision_work import RevisionWorkExecutor, SupportWorkItem
from memforge.pipeline.revision_assessment import RevisionAssessmentContext
from memforge.llm.structured import (
    RevisionScanResponse,
    RevisionScanResult,
    RevisionScanFinding,
    RevisionReductionResponse,
    RevisionFinalResponse,
    RevisionFinalResult,
)
from tests.test_revision_assessment import revisions, old_support, memory


class LocalClient:
    max_concurrent = 1

    def __init__(self, limit, case):
        self.limit = limit
        self.case = case
        self.calls = []
        self.reduced = []
        self.final_checks = []

    def request_tokens(self, prompt, **kwargs):
        return len(prompt)

    def input_policy_identity_for(self, model=None):
        return "local-char-budget"

    def request_fits(self, prompt, *, response_format, max_tokens, **kwargs):
        if response_format is RevisionFinalResponse:
            self.final_checks.append(len(prompt))
        return len(prompt) <= self.limit and max_tokens <= 32768

    async def evaluate_revision_work(self, prompt, *, response_format, **kwargs):
        tag = {RevisionScanResponse: "scan", RevisionReductionResponse: "reduce", RevisionFinalResponse: "final"}[
            response_format
        ]
        p = json.loads(prompt.split("<" + tag + ">")[1].split("</" + tag + ">")[0])
        self.calls.append(tag)
        assert self.request_fits(prompt, response_format=response_format, max_tokens=kwargs["max_tokens"])
        if tag == "final":
            self.final_history = p.get("historical_evidence", [])
        rows = p["current"]["primary_candidates"] + p["current"]["required_only_candidates"]
        if tag == "scan":
            return RevisionScanResponse(
                results=[
                    RevisionScanResult(
                        work_id=c["work_id"],
                        observations_found=[
                            RevisionScanFinding(
                                kind="support",
                                refs=[r[0]],
                                explanation=("Possible material. " * 10 if self.case != "progress" else ""),
                            )
                            for r in rows
                        ],
                    )
                    for c in p["claims"]
                ]
            )
        if tag == "reduce":
            useful = {r[0] for r in rows if "Two reviewers" in r[1] or "Country: US" in r[1]}
            if self.case == "retained":
                useful = set(sorted(r[0] for r in rows if "Two reviewers" in r[1])[:1])
            out = RevisionReductionResponse(
                dispositions=[
                    dict(
                        finding_id=f["finding_id"],
                        retained_refs=[r for r in f["refs"] if r in useful],
                        explanation="Keep the approval/scope rule; discard unrelated or duplicate text.",
                    )
                    for f in p["findings"]
                ],
                summary=(
                    "Dropped the unrelated background; keep the approval rule. " * 18
                    if self.case == "progress"
                    else "Retained exact rule and scope."
                ),
                needs_context=[],
            )
            self.reduced.append(out)
            return out
        return RevisionFinalResponse(
            results=[
                RevisionFinalResult(
                    work_id=c["work_id"],
                    status="supported",
                    primary_ref=next(r[0] for r in rows if "Two reviewers" in r[1]),
                    reason="Fixture only",
                )
                for c in p["claims"]
            ]
        )


def make(old, current):
    base, target = revisions(old, current)
    ctx = RevisionAssessmentContext(projection=target, base=base, access_context_hash="scope")
    return SupportWorkItem("w0", memory(), old_support(base), ctx)


@pytest.mark.asyncio
@pytest.mark.parametrize("case,limit", [("retained", 6500), ("progress", 6500), ("history", 8500)])
async def test_complete_current_proof_survives_capacity_preparation(case, limit):
    rule = "Two reviewers approve US releases."
    old = rule + "\n"
    if case == "retained":
        text = "\n\n".join([rule] * 300)
    elif case == "progress":
        text = rule + "\n\n" + "Unrelated background A. " * 180 + "\n\n" + "Unrelated background B. " * 180
    else:
        old = rule + " " + "Old explanatory background. " * 150
        text = (
            rule
            + " "
            + "Current rule explanation. " * 62
            + "\n\nCountry: US. "
            + "Current scope explanation. " * 62
            + "\n\n"
            + "\n\n".join("Routine unrelated note " + str(i) + ". " + "background. " * 15 for i in range(65))
        )
    item = make(old, text)
    client = LocalClient(limit, case)
    executor = RevisionWorkExecutor(client=client, model="openai/gpt-4o")
    scope = executor._full_range([item])
    result = await executor._scan(scope, [item])
    assert result["w0"].supported
    assert executor.covered_source_claim_pairs == len(scope.catalog.fragments)
    assert client.calls.count("scan") > 1
    assert client.calls.count("reduce") > 0
    assert client.calls.count("final") == 1
    assert client.final_checks[-1] <= limit


@pytest.mark.asyncio
async def test_delta_final_preserves_historical_explanation():
    item = make("Two reviewers approve US releases.\n", "Two reviewers approve US releases after the scope check.\n")
    client = LocalClient(12000, "history")
    executor = RevisionWorkExecutor(client=client, model="openai/gpt-4o")
    scope = replace(executor._full_range([item]), mode="delta")
    # A complete current range is also a valid over-approximation of this delta.
    await executor._scan(scope, [item])
    assert client.final_history


@pytest.mark.asyncio
async def test_aggregate_image_admission_can_reduce_before_final(monkeypatch):
    from memforge.pipeline.projection_images import ProjectionImageLoadError

    item = make(
        "Two reviewers approve US releases.\n",
        "Two reviewers approve US releases.\n\nUnrelated screenshot A.\n\nUnrelated screenshot B.\n",
    )
    client = LocalClient(12000, "progress")
    executor = RevisionWorkExecutor(client=client, model="openai/gpt-4o")
    scope = executor._full_range([item])
    rejected = []

    def limited_images(catalog):
        # Exercise the image loader's aggregate-admission boundary. Exact
        # Artifact bytes/ref propagation is covered by revision_work_acceptance.
        if len(catalog.fragments) > 2:
            rejected.append(len(catalog.fragments))
            raise ProjectionImageLoadError(error_code="image_batch_too_large")
        return ()

    monkeypatch.setattr(item.context, "images_for", limited_images)
    result = await executor._scan(scope, [item])
    assert rejected
    assert result["w0"].supported
    assert client.calls.count("reduce") > 0
    assert client.calls[-1] == "final"


@pytest.mark.asyncio
async def test_noncapacity_image_error_is_not_suppressed(monkeypatch):
    from memforge.pipeline.projection_images import ProjectionImageLoadError

    item = make("Two reviewers approve US releases.\n", "Two reviewers approve US releases.\n")
    executor = RevisionWorkExecutor(client=LocalClient(12000, "history"), model="openai/gpt-4o")
    scope = executor._full_range([item])

    def unavailable(catalog):
        raise ProjectionImageLoadError(error_code="artifact_unavailable")

    monkeypatch.setattr(item.context, "images_for", unavailable)
    with pytest.raises(ProjectionImageLoadError, match="artifact_unavailable"):
        await executor._scan(scope, [item])
