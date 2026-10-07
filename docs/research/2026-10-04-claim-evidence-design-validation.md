# Claim/Evidence design validation

Date: 2026-10-04. Status: **not accepted for release**.

This report separates source binding, semantic quality and deployed-product
acceptance. Passing a deterministic suite or receiving valid structured output
does not establish the other gates. The completion contract is
[the extraction design](../design/claim-evidence-extraction-contract.md).

The later [causal audit](2026-10-04-claim-evidence-causal-audit.md) isolates the
historical representation regression and native facts absent from the exact v19
prompt. It changes failure attribution, not the frozen scores or acceptance.
Design v7 clarifies native-to-prompt input integrity; no new online trial or
replacement architecture is implied.

The subsequent [local delivery probe](2026-10-04-claim-evidence-delivery-validation.md)
passed all 61 frozen-candidate SQLite lifecycle/group reads and 64 selected
reference comparisons, actual HTTP detail/resource reads, tool compaction and
private-Memory access checks. The current Cloud seam suite passed 520 tests.
HANA grouped-read parity used a local SQLite bridge, not physical HANA. This
closes named local delivery gaps without changing semantic scores or completing
all A11/A12 acceptance variants.

The [Support audit](2026-10-04-claim-evidence-support-audit.md) subsequently
confirmed real native same-pinned-revision program rebind for the 61 Memories
and 64 parts with no model calls. It also reproduced two existing shared
implementation/contract differences: silent duplicate-selector normalization
and supported-view integrity failures classified as incomplete coverage. Online
Support/Change Impact semantic acceptance remains unverified; extraction-only
Sonnet telemetry cannot establish it.

## Frozen online experiment: projection-extraction-v18

Later [Support implementation correction](2026-10-04-claim-evidence-support-correction.md)
records 868 OSS/524 Cloud seam passes and real same-pinned-revision 61-Memory/
64-part reuse under corrected duplicate/integrity handling. It changes current
code, not the frozen v19 executable or semantic scores. Full acceptance remains
open.

The local canonical extractor called the deployed application's verified SAP
AI Core Sonnet transport. Model: `sap/anthropic--claude-4.6-sonnet`.
Target: CF EU12, org `GSHCM_AI_Innovation_hcmgcn-wo4dz1tb`, space `dev`.
The deployed OSS version was `57f8b006`; the proposed extractor was local,
uncommitted code. This was a read-only extraction replay, **not deployment or
lifecycle acceptance**. No product data was reprocessed.

One complete planned request was sent per source. There was no schema split,
limit increase, introduced batching, semantic repair, admission pruning or
model self-review. Native source, profiles, catalog, prompt, transport response,
bound candidates, telemetry and a source-tree manifest were frozen.

| Native source family | UTF-8 bytes | Catalog refs | Calls | Emitted candidates | Model execution |
|---|---:|---:|---:|---:|---|
| Confluence retained storage | 71,051 | 79 | 1 | 56 | Complete, 73.261 s |
| Jira issue and ten history events | 50,807 | 85 | 1 | 7 | Complete, 13.818 s |

Source SHA-256 values:

* Confluence: `38eda4ad6e0563c6a759881d1f35817d2ab3a4112a22363600d270d5a2a0789b`.
* Jira: `828b504feef809f8d9d9c19e551b70989fdb6f751fe7efe7a0f9c433db52dae3`.
* Frozen source-tree aggregate: `2ada8d7aaa84427a42fa7ac1ff1e6f02454c48fd56aac4c58e76cf8af1821aa3`.
* Candidate review packet: `feb7bb5ebad64b887d7d76c14aeca6e77cb130c69dc6873888978ada0db72402`.

Private evidence resides in the local `contract-v18-20261004` validation
directory, including full source-only packets and independent review files.
These hashes identify that experiment; later code changes do not retroactively
replace its manifest. A fresh main-versus-proposal online comparison has not
been completed in this iteration.

## Independent source-first review

Two agents first received only native source and the approved criteria. Each
froze a useful-knowledge inventory before receiving every raw candidate and
selected reference. Both examined all 63 candidates, 63 Primary refs and ten
Required refs. Neither was instructed to repair outputs or ignore failures.

Inventory A hash:
`9d3977e7bfeea6c5ca4fc206955f6b6adbd1bec7ecf864d3d3f56aea436f4f0b`.
Inventory B hash:
`e23d844b34cda79451dfa3f6a7871930e4dcb9d18722af035a97d31f0ac49e9e`.

| Gate | Review A | Review B | Conclusion |
|---|---|---|---|
| Confluence useful coverage | 50/52, 96.15% | 52/52, 100% | Both reach numeric threshold; material-qualifier interpretation still needs consistent adjudication. |
| Jira useful coverage | 6/8, 75% | 7/8, 87.5% | Neither reaches 95%. |
| Confluence distinct relevant Required | 3/4, 75% | 3/4, 75% | Fails 95%. |
| Jira distinct relevant Required | 2/6, 33.33% | 2/6, 33.33% | Fails 95%. |
| Major claim/Primary errors | Two Confluence findings | No major findings; same items considered debatable | Preserve disagreement; it cannot reverse the other failed gates. |

The agreed failures are concrete: a table header repeats labels already shown
in its selected row; historical copies and labels repeat current-body support;
the exact reproduction navigation/range is incompletely covered. A valid
selector and authentic text did not guarantee a useful, distinct citation.

The reviewers disagree about a list lead-in used as Primary and whether
“Fix by” plus a PASS cell permits “Fixed by”. The safe design cannot require
an undocumented interpretation of either: the central assertion needs direct
support, and ambiguous source modality must remain ambiguous. Do not report
the favorable review alone or upgrade uncertainty into a completed remedy.

## Falsified assumptions and owning boundaries

| Observation | Classification and design consequence |
|---|---|
| Repeated selected Required despite generic distinctness instruction | Extraction quality assumption failed. This is not an admission/store problem; filtering candidates afterward would conceal the failure. |
| Unlabelled historical old/new passages and whole author JSON in readable citations | Representation design gap. Jira owns native field/event boundaries and meaningful human framing; the shared compiler must consume explicit declarations rather than Jira key heuristics. |
| Source lead-in and list are separate selectable units | Granularity risk. The existing reading context is complete, but central-support selection can be weak. Any grouping change must follow declared syntax, preserve precise matching, and be assessed against held-out formats. No grouping fix is yet accepted. |
| Procedural setup omitted | Coverage failure on available source, not a missing image/provider failure. An independent useful-knowledge inventory is necessary. |
| “Fix by” strengthened to “Fixed by” | Ambiguous source plus claim-faithfulness risk. Preserve modality; do not invent resolution from an issue key. |

These observations require design changes before another paid semantic trial.
No proposed contribution-output schema or source-unit grouping is validated by
this experiment. The v18 output remains negative evidence.

## Deterministic evidence and limits

Named seam suites recorded 214 OSS contract passes, 182 native/boundary passes
and 520 HANA/Cloud parity passes at their recorded code states. The latest
governing-scope/capacity suite recorded 25 passes. These runs overlap; their
counts are not an aggregate unique-test count or full acceptance audit.
The broader changed-test run exposed obsolete fixture/admission expectations
and the missing typed capacity code and excessive governing-context authority.
The latter two were implementation violations and were fixed after the frozen
online experiment. The full changed suite still requires convergence; do not
claim all tests pass from selected seam results.

A controlled insertion into the actual large native Confluence source preserved
73 unique exact correspondences and reported six ambiguous repeated selections.
It authorized the inserted selection and no unchanged selections. This proves a
bounded transformation seam; it is not authentic consecutive provider history
or a guarantee for indistinguishable duplicate occurrences. Bilateral uniqueness
and stable native identity remain explicit matching requirements. Readable text
and display aliases do not determine correspondence. Canonical field comparison
also binds the declared JSON pointer and format, so moving a value into another
field does not establish an exact match.

## Frozen online experiment: projection-extraction-v19

The same actual native sources were replayed through the local proposed
canonical extractor and the CF application's SAP AI Core Sonnet transport.
The source-owned Jira schema4 provides field/old/new roles and human actor
framing; a generic substantive-Primary instruction retains the existing output
schema. No self-review, admission, pruning, selection repair, added batching or
provider-limit increase was applied. Compiler contract8 and extraction-v19 were
frozen before inference. Both complete planned requests succeeded with zero
transport retries.

| Native source | Bytes | Catalog refs | Calls | Candidates | Selected Required | Time |
|---|---:|---:|---:|---:|---:|---:|
| Confluence | 71,051 | 79 | 1 | 56 | 1 | 79.965 s |
| Jira issue/history | 50,807 | 95 | 1 | 5 | 2 | 16.307 s |

The two requests used the deployed 32,768 output-token limit, unchanged.
Model: `sap/anthropic--claude-4.6-sonnet`. The combined OSS/Cloud/helper source
freeze hash is `934ec430f2c0faf60d4ee1babefa7c340481f535dee087fb6df00fb3ebcaeded`.
The complete candidate packet hash is
`416632a6a19667b9f03ec6bfada7cdad519c87133c7c8594087a7071ca253ae4`.
Full private evidence is preserved in `contract-v19-20261004` alongside v18.
The design-file copies were captured after inference; their original file
mtimes precede the frozen run. The source/prompt/configuration guard is stronger
evidence than that late design-file capture and the distinction is recorded.

Both independent agents froze fresh source-only inventories before receiving
the candidate packet. They audited all 61 candidates and 64 selected references.
Their denominators differ; neither was adjusted after candidates were exposed.

| Gate | Review A | Review B | Release consequence |
|---|---|---|---|
| Confluence useful coverage | 48/53, 90.57%; favorable modality interpretation 49/53 | 39/55, 70.91%; even crediting 12 omitted named setup environments gives 51/55, 92.73% | Neither reaches 95%; materiality/equivalence adjudication remains explicit. |
| Jira useful coverage | 7/8, 87.5% | 7/10, 70% | Neither reaches 95% under its frozen inventory. |
| Confluence Required | 1/1 relevant, distinct | 1/1 relevant, distinct | Passes sampled selection quality. |
| Jira Required | 1/2 relevant, distinct | 1/2 relevant, distinct | Fails; combined cohort 2/3 also fails 95%. |
| Major claim error | No established major; one unresolved potential major | One Confluence modality error | Do not claim zero-major acceptance from the favorable review alone. |
| Major Primary error | None established | None established | Does not override other failed gates. |

Both reviewers identify the same redundant citation: Jira WCAG labels repeat
the classification already directly supported by its selected Primary. Both
flag the Confluence `Fix by` to `fixed by` change, with different severity because
an adjacent PASS status makes completion plausible without explicitly proving
the named issue was completed. Preserve the uncertainty rather than resolving
it through another model call. Missing refinement qualifications and procedural
setup knowledge remain coverage findings; exact inventory mappings/excerpts
are preserved privately. Primary role and source knowledge are evaluated
semantically by reviewers; raw Observation-range integrity is established by
the deterministic pre-inference compiler checks, not inferred from blind scores.

Current deterministic evidence: 23 affected OSS test files, **781 passed**;
focused correspondence/lifecycle suite **104 passed**; Ruff passed and
`git diff --check` clean. Counts overlap. This iteration closed field-reorder
authority drift, scalar transport/comparison disagreement, native list scope,
and duplicate-population reading/authority responsibilities. Every surviving
current copy is readable; no particular old duplicate is falsely labelled
removed, and new-work authority still cannot choose an added duplicate by
position. Static re-probes confirm the shared native/standard policy.

V19 is **not accepted**. Readability and binding improvements do not establish
faithfulness/coverage/Required quality. The hypothesis that the current source
framing plus generic single-pass extraction rule suffices for the approved
quality criteria failed this cohort. This result does not prove catalog-based
binding impossible. In accordance with the user's conditional handoff request,
produce a complete handoff before selecting another architecture; do not append
case-specific prompt prohibitions or filter these outputs to make them pass.

## Remaining full-contract acceptance limitations

* The Jira native cohort contains no comments. Collection fixtures prove the
  rendered-comment boundary, not real-comment semantic acceptance.
* Real Teams, held-out document families and large consecutive provider
  revisions have not completed this iteration's online/blind acceptance.
* Managed uploads retain concept documents and content-free receipts, not
  original dialogues. Concept-source and dialogue-source acceptance must not
  be conflated. Transcript-retention changes are not authorized.
* Full new-view store-write/lifecycle/pinned-resource delivery needs its final
  parity audit at the current code state.
* No proposed revision has been committed, deployed or smoke-tested in CF.

Release remains gated on the complete A1–A15 audit, converged deterministic
contracts, accepted online/source-first blind quality, bounded upgrade evidence,
PRs for both repositories, checked deployment and named product smoke evidence.
