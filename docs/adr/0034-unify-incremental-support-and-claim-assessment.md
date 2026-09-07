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

1. Reuse one operation-scoped representation index and existing staged base/target
   snapshots. For document semantic assessment, provide the current full catalog
   when the complete request fits the configured input budget (initially about
   80% of available input capacity); otherwise provide the complete structural
   net delta plus necessary prior claim/Evidence and deterministic context. The
   baseline must apply to the evaluated Support. A contested older Support does
   not acquire the last sync's baseline automatically. Missing baseline selects
   current-full assessment. Oversized complete inputs use bounded Source × claim
   execution, never an empty or truncated successful input. Initial import
   retains complete Primary coverage within token-budgeted extraction requests.
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
Support capability; it is not the Evidence compiler version, currently 3.
Update the affected L3/L4 semantic work identities and any changed input-policy
identity through existing descriptors/hashes. Do not bump the compiler unless
fragment/coordinate semantics change, invent a Support migration, or rename an
unchanged L1 contract solely because downstream calls were combined. Already
committed history is not rewritten; incomplete work obeys existing invalidation
and recovery boundaries.

The input policy counts the prompt, response schema, actual supplied images and
requested output allowance. Conservative configurable input/context/output
operator caps are intersected with LiteLLM metadata; unknown aliases require
explicit route capacity rather than a silent universal limit. The default fraction is
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

## Bounded execution refinement (2026-09-07)

[Cloud #473](https://github.com/dodoman-sun/memforge-cloud/issues/473) supersedes
single-request capacity rejection with approved recoverable Source × claim
execution. Compact model catalogs preserve exact text, eligible roles and the
minimal representation/ancestry information needed for interpretation. Titles
remain selectable Evidence; navigation text does not replace a Required ref.

Scans produce potential evidence, counterexamples, scope or dependencies for each
fixed claim/Support; explicit no-local-effect is not a final validation. Complete
range coverage precedes final synthesis. Bounded reduction accounts for every
finding, preserves relevant exact refs and unresolved dependencies, and never
turns summaries into Evidence. Multiple claims may share scan and final requests.
Independent Support groups remain independent. Historical Support parts use integer
indices into a deduplicated explanation array, separate from selectable current
or removed-delta refs. This supersedes the shared `ref` namespace: a fixed-input
runtime replay returned supplied historical `e0`/`e1` IDs as scan findings despite
matching sender/validator catalogs. Scope correction alone did not remove this
input-contract ambiguity. The input policy changes to v3; previous stage results
are retained but cannot satisfy requests with the changed input identity. Large historical Evidence may be
omitted by selecting complete current-full revalidation; latest-sync delta cannot
stand in for an older Support baseline. Only an indivisible input/proof or genuine
representation failure is a capability error; ordinary length is a batching concern.

A frozen LiteLLM capacity snapshot and the actual model bind request/recovery
identity. Planning includes schema, images, output and correction space; actual
native-schema/fallback sends consume that reserve rather than reserving it twice.
The presentation/input policies change; compiler 3, Primary authority policy 5,
projection-extraction-v9 and Support v2 semantics do not.

Recoverable scan/reduce/final records belong to the existing derivation root
under [ADR 0017](0017-stage-recoverable-source-unit-derivation-before-lifecycle-commit.md).
No LLM runs in the lifecycle transaction, and no scan can commit partial Support. Independent claim batches within one Source range reuse the existing
bounded-work helper and structured-client concurrency limit; provider admission
alone is not a bound on queued prompt/image memory. An ordinary sibling failure
stops new admission and drains already started siblings so their successful stages
remain reusable. Aggregation follows planning order, and all required ranges must
still complete before final synthesis. External cancellation may interrupt active
calls; only already persisted successes are promised on resume.
Semantic recall remains imperfect; supplemental exploration is still #468.

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
