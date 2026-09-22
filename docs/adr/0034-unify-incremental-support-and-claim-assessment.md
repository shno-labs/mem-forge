# Unify incremental Support and claim assessment within the existing lifecycle

## Status

Accepted. The original unified assessment contract was implemented on
2026-09-06. The context-planning optimization accepted on 2026-09-21 is the
target shared contract; its implementation and deployment require separate
acceptance tracked by [Cloud issue #505](https://github.com/dodoman-sun/memforge-cloud/issues/505).
Release and deployment evidence remains external to this ADR, and a source
change alone does not prove a deployed Cloud runtime.

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

## Context-planning optimization amendment (2026-09-21)

This amendment supersedes the earlier assumptions that incremental Support
assessment should repeatedly transport all prior Support text, that cumulative
state can be reduced to the latest status, that current-full extraction must be
one model request, and that relationship discovery needs one explicit result per
candidate/incumbent pair. It does not add a lifecycle state, semantic Evidence
search, human confirmation step, candidate-to-candidate deduplication pass, or
cross-Source-Unit destructive rebind.

### Domain vocabulary

The durable design uses responsibility names rather than model-stage numbers:

| Responsibility | Meaning |
| --- | --- |
| Claim Extraction | extract new claims from authorized current change |
| Support Assessment | test one fixed existing claim and rebuild its complete current Evidence Unit |
| Claim Reconciliation | discover material relations between admitted candidates and existing Memories |
| Lifecycle Reconciliation | reduce current Support and relation results into guarded domain mutations |

Historical implementation notes may retain L1/L3/L4 labels, but public types,
methods, result states and new documentation must use the domain names above.

### One deep context-planning module

Callers use one source-neutral interface:

```python
plan_revision_context(
    base_projection,
    target_projection,
    change_set,
    existing_supports,
    coverage,
) -> RevisionContextPlan | TypedPlanningFailure
```

`RevisionContextPlanner` owns exact Evidence correspondence, removed-anchor
context, representation reading groups, Delta/Full cost planning, historical
excerpt selection and work-coverage manifests. Those are private collaborators,
not additional public orchestration stages. Representation adapters for
Markdown/HTML structure, plain text, canonical records such as Jira, and message
graphs such as Teams all emit the same `ReadingGroup` contract:

```text
scope + container + before + target + after
+ authority/selectability metadata + exact fragment references
```

The change target is a sum type: either a current Fragment or a removed Anchor.
A pure deletion therefore has a valid reading group even though no current
target Fragment exists. Historical content is explicitly non-selectable.

### Exact current Evidence correspondence

The planner deterministically classifies every part of prior Support Evidence:

| Status | Meaning | Input consequence |
| --- | --- | --- |
| `EXACT_UNIQUE` | same Observation, one exact digest match, compatible role and structural authority | supply the current Evidence candidate and compact metadata |
| `CHANGED` | the provider object remains but text, digest, role or governing structure changed | supply current reading context and one bounded exact historical excerpt |
| `REMOVED` | authoritative coverage proves the old object or Fragment absent | supply a removed Anchor and one bounded exact historical excerpt |
| `AMBIGUOUS` | multiple exact matches or structural correspondence is not unique | supply the exact candidates and one bounded exact historical excerpt |
| `UNKNOWN` | partial coverage cannot prove presence or absence | preserve the existing Support and forbid destructive action |

Provider identity locates an Observation; it does not establish semantic
equivalence or stable Fragment coordinates. `EXACT_UNIQUE` is a current Evidence
candidate, not a semantic KEEP decision. Support Assessment still reads every
changed ReadingGroup in scope because a distant changed structure may add an
exception or revoke a rule whose original wording remains unchanged. The
planner never performs semantic Evidence search after exact correspondence
fails.

The application always retains Memory, Support and Evidence IDs, Observation and
Revision identity, exact digests, coverage and source provenance. It does not
send all historical Evidence text by default. Only `CHANGED`, `REMOVED` and
`AMBIGUOUS` work receives the relevant historical body, as a bounded immutable
excerpt with revision, digest and historical reference. This excerpt is supplied
once per independent work stream and can never be selected as current Evidence.

### Delta and current-full input

Delta cost is:

```text
all changed ReadingGroups
+ fixed claims and compact Support metadata
+ current context for affected or ambiguous Evidence
+ necessary bounded historical excerpts
```

Evidence merely being distributed throughout a large document does not make
Delta approach Full. Unchanged, exactly corresponding Evidence contributes a
current reference and compact state rather than repeated body text. Delta
approaches Full only when changed/removed/ambiguous Evidence and the deduplicated
union of its ReadingGroups cover most of the effective current Projection.

Claim Extraction and Support Assessment choose Delta or current-full
independently. Mode selection is performed over the complete logical work before
transport partitioning. Current-full means that the model work reads the complete
effective current Source Projection; it never upgrades provider `PARTIAL`
coverage or grants destructive authority. Both modes may stream representation-
safe ReadingGroups and persist execution receipts. Partitioning is a transport
detail: no partial group may publish a Memory, Support or lifecycle mutation.

### Cumulative Support witness state

Support Assessment works at `(memory_id, independent_support_id)` granularity.
Every independent Evidence Unit remains exactly one Primary plus zero or more
Required references; different Supports and sources are never combined to make
one Support appear sufficient.

Cumulative state records semantic witnesses rather than only the most recent
status:

```json
{
  "work_id": "WRK-0001",
  "support_refs": ["PRM-0012"],
  "opposing_refs": ["PRM-0041"],
  "uncertain": false
}
```

Each ReadingGroup adds grounded supporting, opposing or uncertain witnesses.
The final status is derived only after the work manifest proves that all changed
ReadingGroups were processed. A later unrelated group cannot erase an earlier
global revocation or exception. Different legal ReadingGroup orders and
partitions must reduce to the same lifecycle proposal; disagreement yields
`insufficient`, preserves the Support and does not advance its validation
baseline. Witness state is execution data within the existing recoverable work,
not a new business or lifecycle state.

### Sparse Claim Reconciliation

Claim Reconciliation receives complete candidate, existing-Memory and current
Evidence catalogs, with each claim and Evidence body encoded once per request.
It returns one row per requested candidate and only material discovered
equivalent, refining or contradictory relations. Omitted candidate/incumbent
pairs are not persisted or reconstructed as proven `UNRELATED`. A missed
relation may temporarily retain duplicate or conflicting Memory, which is an
accepted false-negative tradeoff; it cannot authorize removal or retirement.

The design does not add candidate-to-candidate semantic deduplication. Exact
admission normalization remains deterministic, and rare same-run semantic
duplicates are accepted rather than adding another model pass or state system.

### Automated destructive validation

There is no human confirmation step. Before applying a proposed
`REMOVE_SUPPORT`, `SUPERSEDE` or `RETIRE_MEMORY`, Lifecycle Reconciliation runs
an automatic `DestructiveValidation` over the affected fixed claims. It verifies:

1. authoritative coverage or an explicit tombstone for every affected object;
2. complete Claim Extraction and Support Assessment manifests with no technical
   failure or unresolved independent Support;
3. resolvable decisive current witnesses and non-stale Support-set hashes;
4. whether the complete effective current Projection still supports the fixed
   claim when Delta alone cannot establish absence; and
5. the aggregate active-Support count after simulating source-scoped removals.

The validator may stream the complete effective current Projection for only the
at-risk fixed claims. This is fixed-claim validation, not semantic Evidence
retrieval. Finding current Support changes the proposal to KEEP or Evidence
replacement. Unknown coverage, model uncertainty, capacity failure or stale
input also yields KEEP and leaves the validation baseline unchanged. Only zero
remaining active Supports may retire a Memory. Another source's active Support
always prevents retirement by the current source.

### Source Unit identity and convergence

Provider identity changes are Source Projection facts. If a Confluence Page,
Teams window or other Unit loses its provider identity, authoritative inventory
represents the event as old Unit deletion plus new Unit creation. The lifecycle
may remove the old Unit's Supports and extract candidates from the new Unit; it
does not promise Memory-ID continuity or perform cross-Unit destructive semantic
rebind. Ordinary non-destructive identity matching may still attach a new
equivalent Support to an active access-compatible Memory.

Under `COMPLETE_SNAPSHOT`, disappearance may remove old Supports. Under
`PARTIAL_PROJECTION`, absence is unknown and old Supports remain. Delete and
create may commit in either order and temporarily expose a gap or overlap; the
operations must be idempotent and converge. A provider-declared stable move,
reply, quote or correction mapping may enlarge an explicit comparison scope,
but text similarity alone never does so.

### Capacity and non-goals

Representation adapters may split one large Observation only into exact,
claim-coherent authority ranges with a complete coverage manifest: for example,
table header plus row, list lead-in plus item subtree, or heading plus paragraph.
Cross-range claims use one Primary and the necessary Required references. An
indivisible ReadingGroup that still exceeds route capability produces a typed
capacity failure, preserves affected Supports and publishes no partial candidate
or lifecycle mutation.

This amendment deliberately does not add semantic Evidence retrieval, manual
confirmation, candidate-to-candidate semantic deduplication, permanent Fragment
rows, a MemoryRevision entity, a second lifecycle state machine, cross-Unit
identity continuity, or partial lifecycle commits.

## Decision

1. Reuse one operation-scoped representation index and staged base/target
   snapshots. A source-neutral revision-input planner constructs both feasible
   reading plans for normal updates: complete changed ReadingGroups with compact
   Support metadata, current context for affected/ambiguous Evidence and bounded
   exact history only for changed, removed or ambiguous Evidence; and complete
   current input without non-current history. It forecasts both in the actual
   request format and chooses the lower forecast token cost; delta wins an exact
   tie.
   There is no changed-content percentage threshold. The baseline belongs to the
   evaluated Support, not its Evidence birth revision or the latest Source sync.
   Initial import partitions its full authorized Primary work with local reading
   context. Claim Extraction and Support Assessment may stream exact ReadingGroups
   under one complete work manifest. Oversized work never silently truncates
   coverage or publishes a partial business result.
2. Keep read scope separate from new-claim Primary authority. Ordinary extraction
   still requires authorized added/changed complete structures or canonical
   fields, even when unchanged context is readable. Existing-claim validation
   can use current unchanged Evidence without authorizing duplicate extraction.
3. One Support Assessment returns the fixed claim's support result and necessary
   current Evidence reconstruction. The application can retain proven unchanged
   parts and resolves a complete Evidence Unit; Required membership can split,
   merge, grow, or shrink. An old offset locates only its own revision. Semantic
   selection of current supplied fragments does not require reconstructing the
   author's unique edit history. Stored provenance remains exact and immutable.
4. Claim Reconciliation combines relation classification and conditional revision
   assessment over complete candidate, incumbent and current-Evidence catalogs.
   Its relationship vocabulary is EQUIVALENT, directional REFINES and
   CONTRADICTS. Only material discovered edges are returned; omission is accepted
   as a semantic false negative and is never reconstructed as proven UNRELATED or
   used to authorize a destructive action. Insufficient input is an unresolved
   assessment, not a relationship or a new persisted state. Only a new-to-old
   refinement with the same knowledge identity, all old meaning and scope
   preserved, a self-contained new claim, and complete current supporting
   Evidence may propose revision. Non-applicable revision assessment is explicit
   in a fixed result contract. The reducer validates completeness and consistency
   with the same-input Support Assessment result before proposing actions.
5. Keep existing Lifecycle Plan, complete incumbent coverage, Source Authority,
   Review, causal stale guards, and atomic commit. Model output never directly
   creates or retires Memory. Unknown selectors and malformed or incomplete
   results remain execution failures with the existing bounded correction/retry
   contract; they cannot fall back to independent ADD. A semantic uncertainty
   becomes Review only where an existing Source Authority contract already
   requires it; Review is not an extra confirmation step for ordinary revision
   processing. Otherwise reject the Unit without a partial commit.
   Competing incompatible refiners retain the existing fail-closed boundary;
   this decision does not introduce multi-option Review, all-candidate conflict
   scanning, or a separate Memory lifecycle state.
6. Retain pre-creation identity reuse and post-commit bounded relation discovery
   from ADRs 0006/0009. New supported Memory may be visible before cross-document
   conflicts are discovered. This temporary window is accepted; no conflict-free
   publication guarantee or fixed completion deadline is implied. Persist work
   with the lifecycle transaction, retain auditable failure/retry, and never give
   discovery authority to retire another source's knowledge.

Bounded structural reading groups deliberately accept occasional semantic false
acceptance when a dependency outside the supplied group is missing and the model
does not recognize the gap. Choosing current-full eliminates that particular
omission for a fitting current snapshot, but does not claim semantic recall.
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
NULL associations mean that no verified validation baseline is recorded, not
current validation. L3 may establish one through a new complete-current
assessment and normal Plan when the current target provides complete authorized
coverage. This absent-baseline case is distinct from a recorded baseline whose
named snapshot is missing, mismatched, corrupt, inaccessible, or incomplete.
The latter is a technical contract failure and must not be converted into
current-full, semantic `insufficient`, or a successful empty result. L1 likewise
must not turn an incremental request with an unavailable required base into an
initial full extraction.

Optional historical backfill requires an applied Plan's exact Support mutation,
matching source/unit, complete target membership and authoritative stored
Evidence; a Source-wide success or timestamp is insufficient. Backfill is a
separately authorized, bounded recovery operation with exact-count dry-run and
stale guards. It never rewrites Evidence, Plans, Reviews, or failed jobs and
does not require source re-ingestion. When no verified baseline exists and the
task contract permits current-full proof, assess the complete current catalog
through the same budgeted batch executor. In this L3 path, full input means
complete current coverage, not one model request and not access to unrecorded
historical content.
Only necessary indivisible work that still exceeds the configured capability
fails through the existing capacity contract; never borrow a newer delta,
silently truncate, or fabricate validation.

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

The input policy counts the exact fallback prompt with its response schema,
actual supplied images and requested output allowance. Configured input,
context-window and output caps are intersected with LiteLLM metadata. Known route
aliases resolve to their corresponding SDK model (SAP Sonnet 4.6 uses Bedrock
Sonnet 4.6 metadata and tokenizer); capacity numbers are not duplicated in an
application registry. Unknown aliases require all three explicit route caps rather
than a silent universal limit. The default input fraction is 0.8; the shared
request budget also applies its versioned output and bounded-correction reserves.
These are transport-capacity limits, not an edit-percentage mode threshold or an
accuracy guarantee. Actual extractor model, output allowance and policy
configuration participate in derivation identity.
L4 shares one candidate/Evidence payload across its comparison group and sizes
output to the existing pair workload. It does not change pair coverage; oversized
pair requests subdivide within that complete workload. Image-capable context
reserves existing multimodal admission before loading bytes; image integrity
errors are terminal, while unavailable storage remains a recoverable read failure.

## Consequences

The material changes concentrate in input preparation, L3, L4, and reducer/Plan
integration. Entity resolution stays a bounded retrieval helper, not a truth or
identity authority. No new scheduler, persistent Fragment model, MemoryRevision
entity, or historical-document browser is required.

Reading groups and request partitions are transient presentation boundaries.
They do not merge list-item Evidence, combine independent Evidence Units or
Supports, regroup incumbents, create intermediate lifecycle states, or change
the complete atomic Lifecycle Plan. Resolver and lifecycle identity continue to
use exact Fragment and Evidence-Unit membership.

Fewer logical calls do not prove lower total cost: L4 now receives complete
candidate Evidence, and complete same-Unit comparisons remain required. Validate
accuracy, input/call cost, unresolved outcomes and latency on a fixed cohort;
record request coverage and capability failures rather than silently truncating.

## Unified revision input planning and bounded execution

The revision-input planner supersedes both full-first fallback and unconditional
delta-first selection. It is source-neutral: representation profiles supply exact
structures and reading groups; the planner does not branch on Confluence, Jira,
Teams, GitHub, local files, or agent clients. Support Assessment has one model responsibility:
assess the fixed claim and update its current Support evidence in light of the
selected complete input. A rule remaining in force is distinct from execution
compliance; missing results or unfinished examples do not by themselves revoke a
normative obligation. Deletion, rewrite, heading/scope change, and Required
split/merge use that same contract rather than source-specific classifiers.

For a valid base/target pair, the planner constructs a delta candidate and a
current-full candidate before choosing. Delta contains all changed current
structures, bounded current reading groups, compact prior-Support metadata,
current candidates for exact unchanged Evidence, and bounded exact historical
excerpts only for changed, removed or ambiguous Evidence. It does not repeatedly
transport unchanged historical Support bodies or semantically search for current
Evidence after exact correspondence fails.
Current-full contains the complete eligible effective current snapshot and omits
non-current `oldhistory`. “Full” means coverage of that current Source Projection,
not provider version
history, deleted upstream data, a repair for incomplete collection, or a grant of
new extraction authority. Partial Projection carry-forward remains current input;
an upstream omission without authoritative coverage still cannot prove deletion.

Each candidate receives a deterministic request-format forecast across all
requests needed for the logical assessment, including prompt/schema transport,
repeated per-request material, initial state, the existing cumulative-state
reserve, output reserve and supplied images. Future model-selected cumulative
state is unknowable during mode selection, so every emitted request still passes
actual admission before execution. After materializing delta, the planner may use
a safe image-free full lower bound to stop when full cannot win; otherwise it
materializes full before choosing. A plan is eligible only when it preserves
required coverage and every indivisible reading group fits the effective route
capacity. Claim Extraction and Support Assessment may both stream exact,
representation-safe ReadingGroups under one complete work manifest. The lower
forecast token cost wins and delta wins a tie; request and image counts/bytes
remain diagnostics while image token cost is part of the
request token count. The planner does not use an edit ratio, document-size
percentage, Fragment count percentage, or source-type preference. Mode selection
is execution policy only: Claim Extraction still limits Primary to authorized current work,
while Support Assessment may select any legitimately eligible current Evidence offered for the
fixed claim.

A fitting delta and claim group uses one model request. Larger deltas use the same
cumulative assessment contract over stable Source batches. Each request receives
the fixed claims, compact Support metadata, current exact catalog, the affected
bounded historical excerpts and processed-group metadata. Cumulative state keeps
selected supporting refs, decisive opposing refs and an uncertainty marker. It
does not carry an unbounded prose narrative. Final status is derived only after
the complete group manifest is satisfied; an unrelated later group cannot erase
an earlier revocation or exception.
Batches describe one base/target pair, not intermediate Source revisions. When
Support Assessment has no recorded verified baseline and complete-current proof is permitted,
current-full uses the same executor without assuming old Support validity. A
named but unavailable or mismatched baseline is not this case and fails before
semantic assessment.
Here “old” means Evidence from the historical Source revision. Earlier batches
of this same target revision remain valid assessment context in both modes;
their selected refs do not expire when the next batch omits their raw text.

Current selectors are limited to the current catalog and grounded current refs in
the cumulative witness state supplied in that request. These refs form one shared
candidate pool: a claim may select Evidence another claim previously selected.
Candidate availability is a request property, while judgments and complete
Evidence Units remain independent per claim/Support.
Refs omitted from the request, including other claim batches, are not selectable.
Historical material never becomes selectable current Evidence.
The application validates the final complete Evidence Unit from exact original
refs; it does not require a final model request to reread all retained raw text.
Cumulative witnesses are inference state, not stored Evidence. Bounded execution
still accepts model semantic misses, but complete range coverage, decisive-witness
retention and order-invariant reduction prevent transport partitioning from silently
forgetting an earlier judgment. An `insufficient` Support Assessment result skips
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

First-import extraction separately streams its full authorized catalog. Incremental
Claim Extraction Primary remains limited to authorized changed structures; its
selected read scope is either delta with local context or current-full ReadingGroups.
Neither mode widens Primary authority. Claim Extraction and Support Assessment
share catalog, budget and durable execution primitives,
while retaining distinct semantic duties.

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

## Sparse Claim Reconciliation over complete input catalogs

Claim contract v6 supersedes the v5 requirement for one explicit response per
challenger–incumbent pair. The product accepts semantic false negatives in
relationship discovery: omitted pairs propose no relationship action and are
not persisted or reconstructed as proven UNRELATED. This may retain duplicate
or conflicting claims or miss a competing replacement proposal. Explicit proof,
Source Authority/Review, stale and atomic guards remain mandatory; they do not
prove that a model discovered every semantic relationship.

Claim Reconciliation receives separate candidate, incumbent and current Evidence catalogs, linked
by application-issued IDs. Evidence text and each claim occur once per request;
Primary/Required role, observation/revision identity and validity remain explicit.
Incumbents carry their already completed current Support assessment. Historical
support is not misrepresented as current evidence, and missing audit evidence
references must not be fabricated. No retrieval top-k prunes incumbent input.

Each requested candidate returns exactly one row with evidence entailment status,
only discovered equivalent/contradictory/directional-refinement edges, and explicit
uncertain incumbent references. Empty edge arrays are valid. Equivalence is kept
because it prevents duplicate admission. A candidate lacking complete entailing
Evidence cannot escape as independent ADD. Explicit uncertainty preserves the
connected component under the existing reducer semantics. Only contradictions
and forward refinements carry their applicable proofs. IDs, uniqueness, all
candidate rows and applicable proof structure are validated before persistence.
Missing rows, unknown IDs, duplicate edges, truncation, refusal and technical
failures are never interpreted as empty discoveries.

One complete catalog is attempted first. Existing capacity subdivision partitions
catalog work only when actual input/image capacity requires it, preserving all
candidate/incumbent inputs. There is no pair-count packing limit or arbitrary
edge cap. Claim Reconciliation does not add candidate-to-candidate semantic
deduplication. Automated DestructiveValidation is separate fixed-claim Support
work and never treats a missing relation edge as proof of absence. The existing
conditional comparison of multiple discovered refiners remains unchanged.
Independent full incumbent Support assessment, the deterministic reducer and
atomic lifecycle commit still apply even when no relationship is emitted.

Acceptance separates false-negative relationships from incorrect lifecycle
mutations. It covers omitted equivalence, omitted competing replacements,
explicit ambiguity, scope narrowing, valid empty results, and incomplete transport.
Response size is a measurement of representation, not a claim of semantic recall
or live-provider latency. Budget/output ceilings and logical deadlines retain
their existing meanings.

Completed `claim_assess` results belong to the existing Source derivation, just
like support work. Their identity binds the lifecycle operation input (including
Support snapshot), ordered catalog identities, prompt and schema hashes, model,
budget and claim contract. Only a fully validated response with all requested candidate rows is reusable.
A retry reads completed work and computes unfinished requests; changed inputs
cannot borrow old judgments. A process loss before a successful result is stored
may repeat inference, so this is not an exactly-once provider-call guarantee.

This supersedes transient-only L4 result ownership. SQLite and HANA require every
referenced claim result to be completed before applying the existing atomic
Source projection/Lifecycle Plan. Independent successful work may survive a peer
failure, but no subset of its mutations or new Support is published. The existing
stale guards and complete incumbent Support coverage remain authoritative.

Structured failures carry content-free diagnostics from their own logical call
through the reconciliation failure to its terminal runtime event. Field paths,
validation rules, transport, response fingerprint and provider usage are safe
metadata; raw responses and source text are not telemetry. Concurrent sibling
signals must never be guessed into the failing call by error-code matching.

## Complete Support requests and model-facing identifiers

Support Assessment first plans the complete delta and current-full alternatives
for the complete fixed-claim cohort under one validation baseline, then attempts
the lower-cost eligible mode. Only a measured input, image, mandatory response-row,
or cumulative-state capacity failure invokes the existing transport partitioning.
This supersedes both selecting a packing by score before trying complete coverage
and choosing a mode merely because one request fits. Delta includes changed
material, exact current candidates for prior Support, representation-owned
reading groups, and bounded historical excerpts only for changed, removed or
ambiguous Evidence. Current-full reads the
eligible effective current projection without carrying non-current history or
changing its provider coverage meaning.

The response remains one independent judgment per work item with only its selected
Primary/Required refs. A hypothetical claim-by-every-fragment response is an output
allowance estimate, not a required output shape. That allowance saturates at the
route's generation capacity; the minimum serialized row coverage must also fit.
No Evidence list is silently shortened to satisfy this budget. Provider truncation,
refusal, invalid refs and incomplete task coverage cannot complete work, even when
the response text is syntactically valid JSON. Successful parsing alone is not
successful execution. The existing bounded correction and fail-closed lifecycle
boundary remain authoritative; no new semantic states or scheduler are introduced.

Support requests expose stable typed aliases: WRK for assessment tasks, PRM for
Primary-eligible current Evidence, REQ for Required-only current Evidence and HIS
for historical material. PRM Evidence may also be selected as Required. Prefixes
identify namespaces, not relationships between matching numeric suffixes. Numbers
use a minimum four digits and expand without truncation. Aliases remain stable
across every partition and cumulative state in the same assessment. Encoding and
decoding affect only identifier fields; source text and reasons are never rewritten.
Canonical Evidence coordinates and stored work results retain their internal IDs.
The support work contract is `support-delta-assessment-v2` and the input policy is
`revision-input-v4`; old completed work is not reinterpreted as new-wire output.
Evidence compiler and lifecycle semantics are unchanged.


### Compact Support judgments

Final successful Support judgments carry the work ID, status and complete selected
Primary/Required references on the model wire. They do not carry generated prose.
During streamed assessment, compact witness state carries selected supporting refs,
decisive opposing refs and an uncertainty marker. Negative and uncertain judgments
retain a bounded explanation of the decisive basis.
This supersedes the assumption that every successful item needs a generated reason.
The canonical stored result retains a deterministic success explanation; downstream
lifecycle decisions continue to use status and resolved Evidence, never that sentence
as additional authority. Cumulative assessment carries grounded Evidence witnesses,
not an unbounded narrative of unrelated facts. Final status cannot overwrite or forget
an unresolved earlier opposing witness.

Every requested work item must still be returned. Omission is not approval, unchanged
Support or coverage. Reference lists are never truncated to meet an output target.
The wire schema is distinct from the canonical stored result; cached canonical results
are validated without decoding aliases again. `support-delta-assessment-v3` and
`revision-input-v5` isolate the changed prompt/schema semantics from historical work.
Validation diagnostics identify the work, attempt, rule and expected item count without
logging source text or provider response bodies. A correction remains bounded and
complete; partial-result repair is not introduced by this decision.

Anthropic's [latency guidance](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-latency)
recommends reducing unnecessary output. Output reduction is measured separately from
end-to-end latency; input processing and provider waiting prevent proportional latency
claims from output token counts alone.

The earlier source-neutral reading and cost-selection amendment uses
`revision-input-v6`. That identity is included directly in the inference
capability hash and the Source derivation's `semantic_input_policy`; completed
v4/v5 work is not reinterpreted. The extraction contract remains
`projection-extraction-v9`, Support remains `revision-support-v2`, compiler
contract remains 4, authority policy remains 5, and the model presentation policy
is 4. The planner amendment changes request scope and presentation identity only;
it does not migrate stored Evidence or create a lifecycle version.

Implementing the 2026-09-21 amendment must allocate successor semantic-work and
input-policy identities for exact correspondence, witness state, streamed
current-full extraction and DestructiveValidation. Existing completed v6 work
must never be reinterpreted under the amended contract. Exact successor numbers
are assigned with the implementation so they cannot collide with independently
released work; no stored Evidence or lifecycle schema migration follows merely
from this contract change.
