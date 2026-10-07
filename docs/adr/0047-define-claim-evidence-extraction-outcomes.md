# ADR 0047: Define claim and Evidence extraction outcomes before implementation

## Status

Proposed, 2026-10-04. The user approved the quality thresholds, not a claim of
implementation or release acceptance. The [complete design](../design/claim-evidence-extraction-contract.md)
and [validation](../research/2026-10-04-claim-evidence-design-validation.md)
define the contract and evidence. Existing accepted behavior is not silently
changed by this proposal.

Acceptance clarification, 2026-10-06: the user permits provisional acceptance
of nonideal Primary/Required selection when joint Evidence delivery and revision
Support correctness are verified. The [functional review](../research/2026-10-06-primary-required-functional-review.md)
passes the specific introductory-Primary/substantive-Required case. This accepts
that role-quality limitation; it does not declare every generated claim correct,
accept a source-authority violation, or establish product release completion.

Acceptance clarification, 2026-10-07: the user provisionally accepts the observed
composite-to-subset replacement error as residual model risk. This supersedes
treating that specific error as an outstanding release blocker; it does not
make the replacement semantically correct or remove whole-incumbent preservation
from the intended contract. The main model's boolean assessments are fallible
judgments, not program-verifiable entailment proofs. A subsequent real Sonnet
assessment of the complete claim pair and its original selected Evidence returned
`preserves_incumbent_truth=false`; the coordinator then kept the incumbent and
added the challenger. That assessment used a smaller catalog, so it does not
establish the original error's stochastic frequency. Retain both observations.
No extra self-review stage, semantic repair layer or restriction on all automatic
replacements is required by this disposition. Diagram/ADR failure-policy alignment
and the remaining implementation review are still required for completion.

The v19 source-framing and generic single-pass extraction hypothesis failed
independent coverage and Required-quality gates. Readable native binding and
deterministic correspondence are useful prerequisites, not proof that this
extraction strategy meets the quality contract. This supersedes the working
assumption that those representation improvements alone would suffice; it does
not establish that catalog binding is infeasible. No replacement architecture
or downstream repair stage is accepted. Preserve the failed outputs and provide
the requested handoff before further architectural iteration.

A subsequent complete-source counterfactual also failed the quality contract
when it replaced exact excerpts with generated support summaries bound to whole
immutable evaluation snapshots. It did not run ref-to-ref revision mapping.
This supersedes the hypothesis that removing exact-location and correspondence
constraints alone is sufficient for the tested extraction strategy. It does not
make precise excerpts universally mandatory or establish an intrinsic model
reasoning ceiling. Snapshot authenticity, support-summary faithfulness and
explicit Memory coverage remain independent duties. No summary-based storage
cutover or additional semantic repair stage is accepted by this finding; see the
[sealed comparison evidence](../research/2026-10-05-model-comparison-progress.md).

## Context

Exact source addressing is a valid reason to choose catalog-based Evidence
selection. It does not require raw markup in citations, repeated structural
Required references or conflating source-reading, reference-selection and
cross-revision comparison. Fixing model output after extraction can hide an
input or design defect and lose otherwise useful knowledge.

Current selected-Evidence entailment admission and mutable Unit Title facts
conflict with best-effort supplementary citations and immutable factual framing.
A single core range plus presentation hash does not establish the provenance of
additional factual labels or author/time fields used in a composite view.

## Proposed decision

Keep application-owned exact source binding and catalog selection as the feasible
implementation baseline. Arbitrary source-first quote selection is outside this implementation because
its native inverse mapping and historical reconstruction are unproven. The release has one chosen path, no quote/catalog
rescue switch or new semantic repair model. Equal accepted quality favors the
simpler reliable implementation.

Source adapters own native syntax, field semantics, factual framing and generated
controls. Shared compilation/planning consumes their declarations. Matching uses
source-owned canonical material and stable occurrence evidence independently
from readable rendering; whole-Support validity remains a separate assessment.

Primary directly supports the central conclusion. Required is best effort and
must add distinct relevant contribution when selected; it is not a complete
dependency graph. Claims retain their material conditions and modality even
when a supplementary citation is omitted. The user-approved cohort criteria are
no major claim/Primary errors, at least 95% useful knowledge coverage without
material branch omissions and at least 95% relevant nonredundant selected Required.
These were the original empirical acceptance gates, not a universal accuracy
guarantee. Preserve their historical measurements. Under the user's 2026-10-06
clarification, nonideal role selection alone is no longer a release blocker
when the authentic, authorized joint Evidence supports the claim and all its
selected parts remain available to consumers and revision assessment. Primary
remains the intended main citation; Required may supply substantive support,
conditions or relevant explanation. A Required sentence need not mirror the
claim literally or become an independent Memory automatically.

This clarification does not weaken exact source binding, Primary eligibility,
whole-part membership, visibility, partial-coverage preservation, complete
incumbent assessment or destructive lifecycle guards. Read and assess Support
as the complete Evidence Unit, rather than treating Primary strength as a
proxy for Unit validity. Primary also determines Evidence time in existing
relation rules: the reviewed same-Observation case has an identical time basis,
but acceptance must not generalize to arbitrary cross-Observation role swaps.
Static correspondence establishes source identity and change routing, not claim
truth. Model quality remains measurable and fallible without an added repair or
candidate-pruning stage.

Explicitly amend the following existing assumptions when implemented and
validated:

* ADR 0034 Candidate Admission no longer rejects for selected-Evidence
  `evidence_incomplete` or calibrates roles. Preserve independent value,
  same-round deduplication, relation and incumbent whole-Support duties.
* ADR 0034 Unit Title is display context. Claim-bearing framing must be retained
  in immutable source material and participate in revision/impact; a mutable
  display label cannot substantiate claim facts.
* Composite text Evidence carries one typed, versioned view descriptor with
  exact source-bound interpretation origins through existing reference records
  and both stores. It is provenance, not another domain graph or Required role.
* Value/deduplication decisions cover all candidates; unjudgeable work fails the
  derivation atomically. Citation reselection is removed and malformed selectors
  are technical failures, not normalized semantic success.
* Meaning-bearing reply/framing facts belong in immutable Observation records;
  their edits participate in revision and whole-Support impact.
* Canonical schemas declare field-role labels and exact sibling interpretation
  facts. Native historical old/new roles are visible in citations; actor framing
  uses declared human/identity leaves rather than whole transport objects.
  Schema versions preserve previous pinned presentations. A declared wildcard
  comparison role can survive array reordering while interpretation changes
  still require whole-Support assessment and duplicate matches stay ambiguous.
* Duplicate population changes have distinct reading and authority duties:
  Support reads every affected current occurrence and identifies historical
  copies as absent only when none remain. New-work authority cannot select an
  arbitrary added copy by position. Independent new material retains its
  authority: an ambiguous occurrence identity does not make the Unit's other
  extraction work unplannable. Shared native and standard text follow the same
  policy; complete Support coverage and atomic commit guards remain required.
  No repair stage or new lifecycle state is introduced.
* Source adapters declare native presentation containers, semantic controls and
  external-content constructs through their existing format interface. Layout
  and rendering decoration preserve authored children; links, task status,
  table interpretation and literal content preserve meaning. An uncollected
  external dependency cannot be silently erased and called complete Evidence.
  Compatible syntax extensions preserve registered fragment, comparison,
  presentation and reading contracts. Incompatible changes need new contracts
  with retained historical interpretation, independently of execution versions.
* Declared native-format structures receive the same narrow changed-work
  calculation as standard nested text. A changed JSON body field does not
  authorize all unchanged native structures.
* Incompatible historical claim-bearing representations cannot be silently
  dropped and called exact Support reuse. Preserve history and use the accepted
  bounded upgrade reprocess or explicit existing unresolved assessment.
* Support checks pinned raw/origin/presentation integrity and reconstructs
  supported descriptors before current membership/coverage routing. Unknown
  historical profiles/views preserve the whole Support as unresolved, including
  complete current absence. Binary raw integrity names Artifact bytes through
  their immutable metadata digest, not the Observation text envelope.
* Native input coverage is established independently of projected catalog
  planning coverage. Adapter field policy must retain material source facts;
  model quality cannot be inferred from knowledge the adapter omitted. Evaluate
  source metadata for useful-knowledge materiality rather than making every
  provider field mandatory Memory content. This supersedes treating a complete
  planned projected catalog as proof of complete native input.

No new durable Fragment catalog, lifecycle state or destructive authority is
introduced. Images remain deferred under [issue #497](https://github.com/shno-labs/mem-forge/issues/497).

## Focused presentation extension

The 2026-10-06 implementation uses existing catalog selectors with one generated
presentation per selected ref in the same extraction or supported-assessment
response. Source adapters still own source interpretation. Persist generated
`display_text` separately from full `excerpt`; carry it through derivation and
Lifecycle Plan payloads and both stores. It never participates in source identity,
part membership, correspondence, claim assessment or destructive authority.
API/UI retain full source inspection, while compact `get_memory` returns readable
`text` with pinned source locators and the complete Primary/Required group.

Core identity alone does not authorize carrying old presentation. Program rebind
and exact coordinator selection reuse display only when the complete source-view
presentation digest remains equal. If interpretation changes, clear old display
and expose the current source view; semantic reassessment generates new text in
its existing supported result. No extra model call, self-review, repair stage,
new business state or provider-specific shared parsing is introduced.

The [production-path integration verification](../research/2026-10-06-focused-display-integration.md)
confirms the separation through persistence, API/MCP, UI and online Sonnet
extraction/Assessment. A fresh blind review found no major claim or display
faithfulness defect in86 claims, but found useful omissions and did not establish
95% coverage. The subsequent user clarification treats useful coverage as a
quality metric for this provisional release rather than a deployment blocker.
The original95% cohort target remains a measured improvement objective in
[Issue500](https://github.com/shno-labs/mem-forge/issues/500). Source-integrity,
claim-faithfulness and complete joint Support lifecycle requirements remain
release gates; neither omitted knowledge nor role-quality acceptance proves
those gates. No frozen failed result is rescored. Product acceptance still
requires checked deployment and named live smoke.

## Consequences and acceptance

The shared Evidence reference/adapter contracts need a small versioned extension
and OSS/HANA parity. Claim-bearing framing must be collected and retained, not
guessed from an unpinned title. Registered historical view contracts preserve
old readability while source correspondence can explicitly remain unavailable.

A read-only native insertion probe already rejects the prior draft's broad
Primary authorization while preserving 73 unique canonical selections. That
failure belongs to shared implementation, not a Confluence-specific workaround.
Prior semantic outputs also remain failing evidence. None establishes that
catalog-first itself is invalid or that source-first would cure an LLM inference.

Acceptance proceeds from fixed design assumptions through deterministic seams,
complete real-source CF Sonnet comparison, fresh source-first blind evaluation,
adapter/store/tool verification and authorized product deployment. Design faults
change the design before code; sound contracts violated by code change the owning
module. Do not improve metrics by filtering candidates, truncating coverage,
adding unapproved batching or repeatedly patching document-specific prompts.

The canonical accepted ADRs are amended only after the corresponding behavior
has been validated. This proposal records the durable target and important
superseded assumptions; it is not a second execution backlog.

Changed source-declared governing reading context authorizes affected unchanged
cores for extraction. Core correspondence and whole-claim validity stay separate;
reading context does not become Required automatically. This supersedes planning
from changed core ranges alone, which could retire a scoped claim without
authorizing its replacement under a changed heading.

Reading-group membership does not establish governance. The representation
reading index distinguishes governing anchors from companions needed for
coherent reading, preventing a changed list item or section introduction from
authorizing every unchanged companion while retaining header/lead-in scope edits.
