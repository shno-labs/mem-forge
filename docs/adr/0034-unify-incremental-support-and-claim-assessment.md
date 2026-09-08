# Unify incremental Support and claim assessment within the existing lifecycle

## Status

Accepted and implemented (2026-09-06). Release and deployment acceptance are
tracked in [Cloud issue #470](https://github.com/dodoman-sun/memforge-cloud/issues/470);
a source change alone does not prove a deployed Cloud runtime.

## Context

The preceding reconciliation classified claim pairs, audits incumbent support, and
conditionally makes a separate revision-composition call. The subsequent NOOP
path independently selects and validates current Evidence. Repeating support
judgments and limiting current candidates through old-location correspondence
can lose valid rewritten or split Evidence. Full-document context also needs to
remain distinct from authority to extract new claims.

The end-to-end explanation and implementation comparison live in
[Source sync to Memory](../design/source-sync-to-memory.md). This ADR records
only the decision; it does not replace the representation compiler, storage
protocol, or the complete lifecycle description.

## Decision

1. Reuse one operation-scoped representation index and staged base/target
   snapshots. Normal updates assess the complete structural net delta, necessary
   prior claim/Evidence and deterministic context, even when the full document
   fits. The baseline belongs to the evaluated Support, not its Evidence birth
   revision or the latest Source sync. Only an unavailable reliable baseline
   requires current-full assessment. Initial import uses the full authorized
   catalog for extraction. Oversized requests batch Source and claims under
   one complete request budget; they never silently truncate coverage.
2. Keep read scope separate from new-claim Primary authority. Ordinary extraction
   still requires authorized added/changed complete structures or canonical
   fields, even when unchanged context is readable. Existing-claim validation
   can use current unchanged Evidence without authorizing duplicate extraction.
3. One L3 assessment returns the fixed claim's support result and necessary
   current Evidence reconstruction. The application can retain proven unchanged
   parts and resolves a complete Evidence Unit; Required membership can split,
   merge, grow, or shrink. An old offset locates only its own revision. Semantic
   selection of current supplied fragments does not require reconstructing the
   author's unique edit history. Stored provenance remains exact and immutable.
4. One L4 call combines claim relation classification and conditional revision
   assessment. Its relationship vocabulary is EQUIVALENT, directional REFINES,
   CONTRADICTS, and UNRELATED. Insufficient input is an unresolved assessment,
   not an unrelated pair or a new persisted relationship. Only a new-to-old
   refinement with the same knowledge identity, all old meaning and scope
   preserved, a self-contained new claim, and complete current supporting
   Evidence may propose revision. Non-applicable revision assessment is explicit
   in a fixed result contract. The reducer validates completeness and consistency
   with the same-input L3 result before proposing actions.
5. Keep existing Lifecycle Plan, complete incumbent coverage, Source Authority,
   Review, causal stale guards, and atomic commit. Model output never directly
   creates or retires Memory. Unknown selectors and malformed or incomplete
   results remain execution failures with the existing bounded correction/retry
   contract; they cannot fall back to independent ADD. A semantic uncertainty
   becomes Review only when an existing single proposal can express its complete
   protected postcondition. Otherwise reject the Unit without a partial commit.
   Competing incompatible refiners retain the existing fail-closed boundary;
   this decision does not introduce multi-option Review, all-candidate conflict
   scanning, or a separate Memory lifecycle state.
6. Retain pre-creation identity reuse and post-commit bounded relation discovery
   from ADRs 0006/0009. New supported Memory may be visible before cross-document
   conflicts are discovered. This temporary window is accepted; no conflict-free
   publication guarantee or fixed completion deadline is implied. Persist work
   with the lifecycle transaction, retain auditable failure/retry, and never give
   discovery authority to retire another source's knowledge.

The delta mode deliberately accepts occasional semantic false acceptance when
unchanged remote context is missing and the model does not recognize the gap.
Recognized uncertainty, illegal provenance, incomplete delta, visibility errors,
and destructive authority violations are not covered by that tradeoff.
Supplemental agentic reads remain the separate beta in
[Cloud issue #468](https://github.com/dodoman-sun/memforge-cloud/issues/468).

## Relationship to existing decisions

### Support validation baseline ownership (2026-09-07)

This ADR is the canonical owner of the following baseline contract. ADR 0030
owns immutable Evidence representation; ADR 0009 owns asynchronous discovery.

- Evidence References identify immutable Observation Revisions and exact ranges.
  An Evidence Unit's original document revision and extraction run describe its
  provenance, never the progress of later Support validation. Reusing an
  unchanged Evidence Unit must not update its original extraction run. New
  Evidence metadata must not duplicate these typed revision/run columns; existing
  historical metadata is preserved as audit data.
- A Support Assertion links to the last applied Lifecycle Plan that actually
  established or successfully revalidated that exact Memory/Evidence Unit pair.
  Its effective baseline is that Plan's target Source Unit revision. Do not
  duplicate that revision or run on Support, or infer it from the latest Source
  sync, Memory timestamp, Evidence creation version, or another Support's Plan.
- Publish this association with the corresponding ATTACH_SUPPORT mutation in
  the same transaction as the Plan and Source projection. Rollback and rejected
  or stale Plans publish no progress. A removal, KEEP without a validation,
  pending proposed mutation, or unrelated successful validation does not advance
  this association. Existing causal and complete-coverage guards remain required.
- A protected old Support retained pending a destructive lifecycle Review keeps
  its last proven baseline. An asynchronous cross-source conflict Review does
  not freeze independently validated Support on either Memory. Review presence
  is not itself a validation result or a new baseline state.
- Supports established at v3, v10 and v15 but each validated through v19 can
  share v19-to-v20 assessment context. A Support still validated only through v3
  requires v3-to-v20 context or a complete current-catalog proof. Unchanged
  Observation Revisions may retain their exact References; changed Observations
  require newly resolved current References, not edited historical anchors.

Schema upgrade adds only the nullable successful-Plan association. Existing
NULL associations mean unknown validation progress, not current validation.
They can be established by a new complete-current assessment and normal Plan.
Optional historical backfill requires an applied Plan's exact Support mutation,
matching source/unit, complete target membership and authoritative stored
Evidence; a Source-wide success or timestamp is insufficient. Backfill is a
separately authorized, bounded recovery operation with exact-count dry-run and
stale guards. It never rewrites Evidence, Plans, Reviews, or failed jobs and
does not require source re-ingestion. If no reliable baseline exists and full
current input does not fit, fail through the existing capacity contract rather
than borrow a newer delta, silently truncate, or fabricate validation.

Implementation and adapter acceptance of this amendment must be verified
separately from the previously implemented L3/L4 assessment contract.

This amends ADR 0030's one-selector-per-old-Required
revalidation mechanics and the separate support/proof orchestration described
in ADR 0012. Their immutable Evidence, authority, storage, and retry invariants
remain. ADR 0008's pruning is semantic-conservative: unchanged old Evidence or
cross-revision position non-overlap alone cannot rule out an exception elsewhere.
ADRs 0009, 0017, 0019 and 0023 remain the owners of asynchronous discovery,
recoverable derivation, vector delivery and Review orchestration.

The shared Source sync engine now consumes unified L3 and L4 results. Historical
ADRs retain the superseded mechanics for context; no historical Evidence is
rewritten. Cloud implements the same
shared contracts; only HANA/hosting consequences belong in Cloud ADRs.

## Validation and version boundaries

Preserve existing deterministic admission normalization and fixed-slot binding
before strict resolution. Unambiguous redundant extraction refs and the current
first-decision pair normalization must not become whole-document failures.
Validate only fields applicable to the selected result; derive mechanical
eligibility in application code rather than requiring redundant model agreement.
Existing one-workset selector correction and typed non-retryable exhaustion
remain. Semantic disagreement is not a transport retry signal. These allowances
never repair an unknown identity by guessing, omit required coverage, or grant
out-of-scope authority.

`projection-extraction-v9` is an extraction contract selected by current v2
Support capability; it is not the Evidence compiler version, currently 4.
Update the affected L3/L4 semantic work identities and any changed input-policy
identity through existing descriptors/hashes. Do not bump the compiler unless
fragment/coordinate semantics change, invent a Support migration, or rename an
unchanged L1 contract solely because downstream calls were combined. Already
committed history is not rewritten; incomplete work obeys existing invalidation
and recovery boundaries.

The input policy counts the prompt, response schema, actual supplied images and
requested output allowance. Conservative configurable input/context/output
operator caps are intersected with LiteLLM metadata. Known route aliases resolve
to their corresponding SDK model (SAP Sonnet 4.6 uses Bedrock Sonnet 4.6 metadata
and tokenizer); capacity numbers are not duplicated in an application registry.
Unknown aliases still require explicit route capacity rather than a silent universal limit. The default fraction is
0.8. Actual extractor model/output allowance and policy configuration participate
in derivation identity. L4 shares one candidate/Evidence payload across its
comparison group and sizes output to the existing pair workload. It does not
change pair coverage; oversized pair requests subdivide within that complete
workload. Image-capable context reserves
existing multimodal admission before loading bytes; image integrity errors are
terminal, while unavailable storage remains a recoverable read failure.

## Consequences

The material changes concentrate in input preparation, L3, L4, and reducer/Plan
integration. Entity resolution stays a bounded retrieval helper, not a truth or
identity authority. No new scheduler, persistent Fragment model, MemoryRevision
entity, or historical-document browser is required.

Fewer logical calls do not prove lower total cost: L4 now receives complete
candidate Evidence, and complete same-Unit comparisons remain required. Validate
accuracy, input/call cost, unresolved outcomes and latency on a fixed cohort;
record request coverage and capability failures rather than silently truncating.

## Direct delta assessment and bounded execution

The delta-first decision supersedes full-first cost selection and the large-input
scan/reduce/final inference chain. L3 has one model responsibility: assess the
fixed claim and update its current Support evidence in light of the supplied
changes. A rule remaining in force is distinct from execution compliance; missing
results or unfinished examples do not by themselves revoke a normative obligation.
Deletion, rewrite, heading/scope change, and Required split/merge use that same
contract rather than source-specific classifiers.

A fitting delta and claim group uses one model request. Larger deltas use the same
cumulative assessment contract over stable Source batches. Each request receives
the fixed claims, necessary prior Evidence, previous brief judgments,
current exact catalog, removed historical text and processed-range metadata.
The carried result contains only status, a short reason and selected Primary/Required
refs. It does not maintain a fact inventory, context-reference collection or missing-
context checklist. This supersedes the requirement to accumulate unresolved semantic
dependencies: simplicity and efficiency take priority over lossless cross-batch context.
Batches describe one base/target pair, not intermediate
Source revisions. Unknown-baseline current-full assessment uses the same executor
without assuming old Support validity.
Here “old” means Evidence from the historical Source revision. Earlier batches
of this same target revision remain valid assessment context in both modes;
their selected refs do not expire when the next batch omits their raw text.

Current selectors are limited to the current catalog and the grounded refs in all
previous states supplied in that same request. These refs form one shared candidate
pool: a claim may select Evidence another claim previously selected. This supersedes
the per-claim selector restriction; candidate availability is a request property,
while judgments and complete Evidence Units remain independent per claim/Support.
Refs omitted from the request, including other claim batches, are not selectable.
Historical material never becomes selectable current Evidence.
The application validates the final complete Evidence Unit from exact original
refs; it does not require a final model request to reread all retained raw text.
Cumulative explanations are inference state, not stored Evidence. This deliberately
trades some joint-reading accuracy for bounded execution: complete range coverage
cannot guarantee all cross-batch semantic relationships are preserved. The final
status remains the sole semantic result; removing a context checklist does not turn
an explicit insufficient judgment into supported. An L3 `insufficient` result skips
that incumbent for this revision: the program emits a bare NOOP / KEEP, preserves
its existing Support and Evidence, and does not advance its validation baseline.
If any independent Support is insufficient, the whole incumbent is skipped for
this round. Other incumbents and extraction candidates continue, and the Source
revision may commit; this supersedes stopping the Unit on L3 insufficiency. No
Review or additional model call is required. The existing Plan records the exact
preserved Support IDs on its KEEP decision under the usual Support-set stale guard.
This exception cannot validate a new attachment or authorize destructive mutation.
Skipped incumbents bypass L4 but remain eligible for ordinary candidate identity
matching and independent corroboration. A later assessment still uses each
Support's actual validation baseline, not the last Source sync revision.

SQLite and HANA apply the same support-preserving invariant in both Support
representations: a structurally valid unrelated Unit's historical Support cannot
block a non-destructive write; destructive decisions still require complete current
Support. Technical failures, invalid selectors and incomplete execution coverage
remain errors. Supplemental exploration stays #468.

Claim batches may share Source input. When cumulative state grows, repartition only
the unfinished claim work, retaining its processed prefix and parent results. A
frozen LiteLLM capacity snapshot budgets the actual transport, schema, images,
per-claim output references, cumulative state and correction reserve. Neither
output truncation nor smaller business scopes substitutes for execution coverage.
An indivisible representation or cumulative state beyond available capability
remains an explicit execution limitation, not a successful or semantic judgment.

`support_assess` records persist exact model inputs/results under the existing
Source derivation. `support_finalize` is a program-generated completion receipt
binding complete coverage and all assessment dependencies; it is not another LLM
call. Existing atomic lifecycle/stale guards consume that receipt. Changed model
work contracts invalidate their own reuse, without changing authority 5, extraction v9 or Support v2 merely for execution.
Compiler 4 independently changes structural boundaries as described in ADR 0030.
Legacy stage records remain immutable history. See ADR 0017 for storage ownership.

First-import extraction separately batches its full authorized catalog. Incremental
L1 uses authorized changed structures and required context; neither path widens
Primary authority or requires a final full-document reread. L1 and L3 share catalog,
budget and durable execution primitives, while retaining distinct semantic duties.

## Local unresolved claim relationships

L4 returns a relationship and conditional refinement proof, without a redundant
`consistent_with_support` Boolean. UNRELATED is valid whether L3 supported the old
claim or not. CONTRADICTS proceeds through the existing authority/Review action
table; old support does not invalidate a contradictory relationship by itself.
An equivalent supported challenger paired with an unsupported incumbent, a
refinement entailment chain conflicting with L3, or insufficient applicable material
is unresolved locally. L4 must also check its supplied accurate Evidence against
the challenger, including table column associations; it cannot repair candidate text.

For an unresolved pair, the reducer consumes the candidate and emits a bare skipped
NOOP for the incumbent, preserving Support, Evidence and validation baseline.
If either participates in other related pairs, preserve the related component
together so a shared candidate cannot escape as ADD or drive another destructive
operation. UNRELATED edges never spread this uncertainty. Exclude that component
from conditional refinement work; independent candidates and incumbents continue.
The existing skipped-Support proof and stale guards remain the only Plan mechanism,
with no new Review state, semantic retry loop, or change to atomic commit ownership.


## References

- [Existing fragment and lifecycle contract](0030-compile-revision-pinned-evidence-fragments.md)
- [Existing asynchronous relation contract](0009-bound-cross-document-relation-discovery.md)
- [Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html): durable follow-up work and idempotent delivery, not conflict-free publication.
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents): start with bounded workflows and justify additional agentic complexity through evaluation.

## Directional support and overlapping scope

The deployed fixed-fixture evaluation exposed a distinction the original prompt
left ambiguous: L3 asks whether current evidence entails the old proposition,
not whether the new and old rules are equivalent or enumerate the same complete
set of requirements. A stronger necessary obligation over the same population
can preserve a weaker necessary obligation. Do not infer sufficiency or
exclusivity absent from the old claim; explicit sufficiency, scope, time and
modality remain material. Restricting the population cannot establish a prior
universal claim.

Likewise, an exception can contradict a universal rule on their overlapping
scope; narrower scope alone does not make incompatible assertions a refinement.
The shared relation definition uses this intersection, while cross-source
mutation still requires the existing Review/Source Authority gates. L4 must
reject an entailment chain that contradicts L3 (current evidence supports the
new claim and the new claim preserves the old claim, but L3 rejected old support).
It must not manufacture a supported verdict or fall back to delete/add.

This clarification advances only the Support/claim semantic contracts and the
shared relation-classifier identity. Compiler, extraction, representation,
Support storage and historical Evidence formats remain unchanged. Frozen
failures are retained alongside new necessary/sufficient and scope holdouts;
prompt improvement does not establish population accuracy.


### Revision identity is continuity, not equivalence

L4's same-item condition means continuity of an independently maintained fact,
rule or decision about its subject and concern across a revision. It is distinct
from L6 equivalence, which requires identical truth conditions. A compatible added
requirement can preserve the knowledge item's identity while making the current
proposition stronger. Complete replacement text must already state the old meaning
and the refinement; adding information does not itself make that text incomplete.

The former L4 fields named `candidate_*` were ambiguous because the shared pair
input calls the incumbent “candidate,” while the lifecycle reducer calls new
extractions candidates. The model-facing revision response now names the current
challenger explicitly and describes each condition in its schema. This changes the
L4 work contract to v3, with an explicit mapping into the existing reducer proof;
compiler, storage, L3 and historical Evidence contracts are unaffected. Unsupported
old claims need not be negated: loss of universal coverage alone does not establish
contradiction with a compatible subset rule.

Acceptance must evaluate the complete revision conjunction and the resulting
reducer action. Correct Support, relation and preservation fields alone do not
prove an eligible UPDATE. Frozen failed results remain evidence even when a later
prompt/schema version corrects them.
