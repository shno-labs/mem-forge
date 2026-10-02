"""Replay a synthetic table against fixed historical compiler/normalizer sources.

Run from the repository root with its Python environment. Dependencies and
shared projection types come from the current checkout; this isolates the
historical source-code boundary, not historical deployments or environments.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

from memforge.source_projection import (
    AnchorKind,
    EvidenceCoordinateSpace,
    EvidenceRepresentationProfile,
    SourceAnchor,
    SourceObservationRevision,
)


COMMITS = ("a8302b5e^", "a8302b5e", "05f0f3c2", "57f8b006")
SOURCE = (
    "<table><tbody><tr><th>No.</th><th>Scenario</th><th>Status</th></tr>"
    "<tr><td>10</td><td><pre>command log\n\n1. First note\n2. Second note"
    "</pre></td><td>PASS</td></tr><tr><td>14</td><td>Late hire rejected</td><td></td></tr>"
    "<tr><td>20</td><td>Switch period then assignment is ok</td><td>"
    '<ac:structured-macro ac:name="status"><ac:parameter ac:name="title">Failed'
    "</ac:parameter></ac:structured-macro></td></tr></tbody></table>"
)


def historical_module(repo: Path, commit: str, filename: str):
    source = subprocess.check_output(
        ["git", "show", f"{commit}:src/memforge/pipeline/{filename}.py"],
        cwd=repo, text=True,
    )
    name = f"evidence_history_{filename}_{commit.replace('^', '_parent')}"
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(source, f"{commit}/{filename}.py", "exec"), module.__dict__)
    return module


def replay(repo: Path, commit: str):
    normalizer = historical_module(repo, commit, "normalizer_utils")
    compiler = historical_module(repo, commit, "evidence_fragments")
    normalized = normalizer.html_to_markdown(SOURCE)
    revision = SourceObservationRevision(
        id="synthetic-revision", observation_id="synthetic-observation",
        semantic_hash=hashlib.sha256(normalized.encode()).hexdigest(),
        content=normalized, metadata={},
        evidence_profile=EvidenceRepresentationProfile(
            name="markdown-structural", version=1,
            coordinate_space=EvidenceCoordinateSpace.UNICODE_SCALAR,
        ),
    )
    catalog = compiler.compile_fragments(revision, (compiler.EvidenceCandidateRange(
        anchor=SourceAnchor(
            kind=AnchorKind.WHOLE_OBSERVATION,
            observation_id=revision.observation_id,
            observation_revision_id=revision.id,
        ),
        primary_eligible=True,
    ),))
    return {
        "commit": commit,
        "compiler": compiler.COMPILER_CONTRACT_VERSION,
        "normalized_has_macro_tags": "<ac:structured-macro" in normalized,
        "fragment_kinds": [f.fragment_type for f in catalog.fragments],
        "swallowed_later_row": any(
            f.fragment_type == "markdown-ordered-list"
            and "Switch period then assignment is ok" in f.presentation_text
            for f in catalog.fragments
        ),
        "macro_in_evidence": any(
            "<ac:structured-macro" in f.presentation_text for f in catalog.fragments
        ),
        "errors": [e.code.value for e in catalog.errors],
    }


if __name__ == "__main__":
    repository = Path(__file__).resolve().parents[2]
    results = [replay(repository, commit) for commit in COMMITS]
    print(json.dumps(results, indent=2))
    assert not results[0]["swallowed_later_row"]
    assert not results[0]["macro_in_evidence"]
    assert all(r["swallowed_later_row"] and r["macro_in_evidence"] for r in results[1:])
    assert all(not r["errors"] for r in results)
