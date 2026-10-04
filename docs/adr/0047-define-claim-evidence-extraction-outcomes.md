# ADR 0047: Define claim and Evidence extraction outcomes before implementation

## Status

Proposed, 2026-10-04. The user approved the quality thresholds, not a claim of
implementation or release acceptance. The [complete design](../design/claim-evidence-extraction-contract.md)
and [initial validation](../research/2026-10-04-claim-evidence-design-validation.md)
define the contract and evidence. Existing accepted behavior is not silently
changed by this proposal.

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
implementation baseline. A source-first exact-quote alternative must demonstrate
bounded native mapping, authority, historical selection reconstruction and output
capacity before replacing it. The release has one chosen path, no quote/catalog
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
These are empirical acceptance gates, not a universal accuracy guarantee.

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
* Declared native-format structures receive the same narrow changed-work
  calculation as standard nested text. A changed JSON body field does not
  authorize all unchanged native structures.
* Incompatible historical claim-bearing representations cannot be silently
  dropped and called exact Support reuse. Preserve history and use the accepted
  bounded upgrade reprocess or explicit existing unresolved assessment.

No new durable Fragment catalog, lifecycle state or destructive authority is
introduced. Images remain deferred under [issue #497](https://github.com/shno-labs/mem-forge/issues/497).

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
