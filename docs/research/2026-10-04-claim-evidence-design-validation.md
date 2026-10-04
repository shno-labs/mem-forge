# Claim/Evidence design review and initial contract validation

Date: 2026-10-04. Proposed contract:
[claim-evidence-extraction-contract.md](../design/claim-evidence-extraction-contract.md),
v3. Baseline main: `57f8b006`; inspected previous draft: `879ddd9d`.

## Result and limit

The design is coherent for a bounded implementation audit. It is **not** runtime,
online semantic, native-source-matrix or release acceptance. This iteration
produced the complete proposed design first, reviewed its responsibilities, and
ran one named deterministic counterexample. No production implementation was
changed, no source/workspace data written, and no CF deployment performed.

The user explicitly approved the cohort criteria: no major claim/Primary errors;
at least 95% distinct relevant selected Required, without a recall target; at
least 95% independently useful knowledge coverage without material branch/guard
omission. These are not claims of a perfect extraction model.

Catalog-first is a concrete implementation baseline, not an assumed universal
optimum. Source-first is an alternative whose native mapping and correspondence
must first earn their additional implementation cost. A prose proposal, an exact
quote found in rendered text, or a plaintext-only demo cannot meet that gate.

## Design review: changed assumptions before code

One independent Codex reviewer read the complete design and focused canonical
code/contracts. Architecture review is not blinded candidate/source evaluation.
V1 review found the following missing decisions; v3 closes them:

| Finding | Prior assumption | Design correction |
|---|---|---|
| D1, P1 | Preserve existing admission while prohibiting semantic admission repair | Explicitly remove `evidence_incomplete` entailment/reselection from candidate admission; retain value/same-round deduplication and relation work. Evaluate untreated extraction. |
| D2, P1 | Mutable Unit Title can supply claim facts without creating revision work | Unit Title is display-only. Claim-bearing framing is retained as immutable source material and participates in revision/impact. |
| D3, P2 | A central raw range and presentation hash suffice for a composite view | Choose a compact typed, versioned `text_view` descriptor with source-bound interpretation origins, round-tripped through existing Evidence records and both stores. |

The reviewer read v3 again and found no unresolved blocking architecture
contradiction for bounded A implementation/audit. The review explicitly did not
approve collection, model quality, storage, correspondence or deployment.

A separate Claude Code CLI design-review attempt, with tools/hooks disabled,
was unavailable; no review was produced. Its diagnostic is retained privately.
This is recorded as unavailable external design review, not a CF Sonnet authentication
result and does not excuse semantic acceptance. No CF Sonnet extraction call was
made in this iteration.

### Architecture feasibility decision

The user asked whether catalog-first itself might be wrong, then stressed its
original implementation rationale. The design now considers both:

* A binds IDs to existing exact compiled views; native ranges, raw digests,
  canonical values and historical whole-selection indexing are reusable.
* B returns claim-specific exact quote selectors in native record/body regions.
  It needs reversible visible-to-native mapping, partial-selection interpretation
  and historical selection reconstruction outside existing Fragment anchors.

Inspected draft code proves B is not a prompt replacement: native parsers export
complete selections, not a general inverse visible-character source map;
`support_reading._correspond` first finds an old compiled Fragment by anchor.
Mapping arbitrary quote spans to that interface needs new shared work. Expanding
every quote back into the same existing Fragment would not demonstrate finer
citations. ADR 0030 also documents HTML/table-sensitive quote copying and the
rejected whole-Block fallback as reasons for catalog selection.

Disposition: keep A as the implementation baseline and test its outcome contracts.
Only advance B after bounded real-native feasibility, without a new parser
framework, substring catalog, semantic graph or fallback. Equivalent accepted
quality favors the simpler, reliable implementation. This rejects speculative
infrastructure, not the user's architectural question.

## New deterministic test: native insertion and incremental authority

Hypothesis fixed before execution: adding one unrelated paragraph to a complete
native document authorizes that paragraph as new Primary work, while old
unchanged structures retain their comparison values and receive no unrelated
new Primary authorization.

Input: frozen authentic complete native Confluence source, 71,051 UTF-8 bytes,
SHA-256 `38eda4ad6e0563c6a759881d1f35817d2ab3a4112a22363600d270d5a2a0789b`.
Target is a **controlled prefix insertion**, not an authentic provider revision.
The read-only probe uses draft `879ddd9d`, the canonical adapter/compiler,
`CommittedSourceUnitSnapshot`, and `plan_projection_evidence_work` with
`reprocess_all_current_observations=False`. No model or store is used.

| Observation | Count / result |
|---|---|
| Original compiled fragments | 79 |
| Target fragments after one paragraph insertion | 80 |
| Added fragments | 1 |
| Unchanged fragments | 79 |
| Added fragments authorized | 1 |
| Unchanged fragments authorized as new Primary work | **78** |
| Old unique canonical selections | 73 |
| Those selections still present once in target | **73/73** |
| A4 narrow incremental authority | **FAIL** |
| Canonical-material equality/cardinality subcheck | **PASS**, not whole A9 acceptance |

Cause confirmed by static path: canonical-field planning descends into structural
diff only when the descriptor has `nested_profile`. A declared native
`text_format` falls into whole-field authorization. One changed body field is
therefore treated as broad new claim authority despite its unchanged native
structures. This is a shared planner contract violation introduced by the new
format interface, not a reason to put a Confluence-specific branch in the planner.

Disposition: the design explicitly requires structural comparison for declared
native formats and meaning-bearing interpretation, separate from whole JSON
field changes. No quick fix was applied. The eventual implementation must satisfy
the same contract for every adapter using declared native text, including actual
framing and duplicate cases. The 73/73 comparison result does not prove Support
validity or composite-view origins.

Probe artifacts are retained outside Git as `/tmp/memforge-design-native-authority-probe.py`
and `.json`; private provider source bytes are not committed.

## Prior evidence classified against the new contract

These are existing frozen artifacts, not new model calls or new acceptance runs.
The latest prior Sonnet Confluence candidate file was rehashed in this iteration:
SHA-256 `9a62af91c16d401ade082f4b5366236a7ddd18186fa1b602f55fe42083e54c1f`.
It contains 56 candidates, 56 Primary parts and 4 Required parts.

Both prior reviews identify 3 redundant Required table headers. Accordingly,
this small regression cohort has 1/4 relevant nonredundant supplementary parts,
or **25%**, below the approved A8 target. This is not a global false-positive
rate or a newly blinded evaluation. A completed-fix interpretation remains
contested/unaccepted under A5; no external resolution was supplied. Structural
span/hash checks passing cannot turn these semantic results into acceptance.

The old handoff reports complete native correspondence probes and 355 OSS/496
HANA engineering tests. Those named results remain useful evidence for their
old seams. They were not rerun here and do not certify the new descriptor,
framing, authority or admission contracts.

## Initial A1–A15 audit

| Contract | Evidence / current result | Remaining named proof |
|---|---|---|
| A1 Native collection | Native Confluence/Jira frozen sources exist; Jira fixture has no comments | Real complete comments, Teams framing, managed input and held-out families |
| A2 Locality | Draft owns native grammar; main generic boilerplate stripping still contains Confluence/Jira-specific patterns | Adapter-owned native recognition; no deletion of authored lookalike headings |
| A3 Source binding | Old exact core ranges/hashes verified; composite factual origins not persisted | `text_view` reconstruction/round-trip and every displayed value's origin |
| A4 Reading/authority | **Failed controlled native insertion test above** | Shared native structural/interpretation diff; no unrelated old Primary work |
| A5 Faithfulness | Prior completed-remedy inference unaccepted | Frozen new extraction and independent source-first review |
| A6 Useful coverage | Prior Confluence accounts for its 45 scenarios; not a full source-family acceptance | Untreated and delivered coverage on common complete held-out cohort |
| A7 Primary | Eligibility and binding are not evidence of central entailment | Independent claim/Primary judgments under fixed criteria |
| A8 Required | Prior cohort 1/4 distinct relevant parts | Meet approved quality without pruning or admission repair |
| A9 Correspondence | 73/73 unique values survive controlled insertion; duplicate limits retained | Whole view reconstruction, origins and native/source-family perturbations |
| A10 Outside-ref changes | Existing whole-Support path available; mutable Title/framing exemption conflicts | Header/frame/exception changes affect claims despite matching core text |
| A11 Lifecycle/stores | Prior parity suites do not cover proposed descriptor/admission/framing | Shared SQLite/HANA protocol and user-facing enforcement tests |
| A12 Delivery | Existing historical/resource work reusable | New composite view origins/versions round-trip with exact visibility |
| A13 Large/capacity | Prior large-document structural evidence exists | Complete current request path, compact output and capacity evidence |
| A14 Cutover | One upgrade reprocess acceptable to user | Bounded exact dry-run/impact and explicit authorized apply |
| A15 Product | No new deployment | Checked CF deploy and named smoke after accepted implementation |

The table is an evidence audit, not an execution backlog or a claim that all rows
must produce more canaries. Implementation scope follows the proposed contract;
material deferred features remain in the issue tracker.

## Frozen experiment interpretation

Catalog-first uses an enumerable set of safe compiler views. A conditional
source-first feasibility manifest must specify its supported selection grammar
and representative structural cases; it must not enumerate every substring.
The generic ref-returning instruction in section 5 is explicitly A's wire
contract; B would share its semantic rules and return verbatim selectors.

Report three separate coverage values: raw semantic claim coverage, exact
binding coverage and delivered knowledge coverage. An invalid/ambiguous selector
is a technical work failure; if its atomic revision cannot publish, that source's
work counts as unavailable delivered knowledge. Publishing nothing cannot win
through perfect citation precision. A selected invalid Required is different
from an omitted optional Required.

Baseline/candidate comparison must freeze exact source/profile/work/model limits
and preserve untreated output. When a result fails, classify the violated
contract before changing anything. False design assumptions change the design;
sound contracts violated in implementation change the owning shared module or
adapter. No per-sample generic prompt additions, rejected-candidate cleanup or
source-type compensation in Cloud constitutes acceptance.

## References

* [Complete proposed design](../design/claim-evidence-extraction-contract.md).
* [Official primary-source constraints](2026-10-04-extraction-design-primary-sources.md).
* Existing OSS draft PR [#495](https://github.com/shno-labs/mem-forge/pull/495),
  Cloud draft [#545](https://github.com/dodoman-sun/memforge-cloud/pull/545):
  reusable implementation and preserved negative evidence, not release approval.
* Image-capability deferral [#497](https://github.com/shno-labs/mem-forge/issues/497).
