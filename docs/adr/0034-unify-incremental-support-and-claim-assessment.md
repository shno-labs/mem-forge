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

The relationship-output clause in the preceding paragraph was itself superseded
by the 2026-09-22 amendment below; the current normative same-Unit contract is one
explicit label per exact-excluded pair.

### Classifier and Support-contract amendment (2026-09-22)

This amendment supersedes the earlier sparse same-Unit Claim Reconciliation and confidence-fallback assumptions. A **classifier model** is an executor role implemented by TypeSafe/Jev or a small-parameter LLM. Eligibility is decided for a complete task contract from a fixed evaluation set; runtime confidence is telemetry, not a per-item route to another model.

After deterministic exact consumption, same-Unit Claim Reconciliation classifies the complete remaining Candidate × Active-incumbent pair manifest. Every pair returns one relation enum. Cross-document discovery retains bounded retrieval followed by classification over `K` pairs.

Exact prior Evidence is classified as `EXACT_UNCHANGED`, `CONTAINER_CHANGED`, `MODIFIED`, `REMOVED`, `AMBIGUOUS` or `UNKNOWN`. Old exact excerpt is supplied only for `MODIFIED`, `REMOVED` and `AMBIGUOUS`; `UNKNOWN` is application-owned `UNRESOLVED(partial_coverage)` and KEEP. Exact-rebound claims are checked against capacity-safe ChangeBundles by a classifier model returning `AFFECTED` or `UNAFFECTED`; affected claims and directly changed Evidence enter complete Structured-LLM Support Assessment.

`AssessmentScope` is the logical DELTA or FULL_CURRENT_REVISION coverage. `AssessmentContext` is one call's one-or-more ReadingGroups. A ReadingGroup may contain several selectable EvidenceFragments. Full therefore means that all current Catalog contexts are eventually processed, not that raw full text appears in one request. The deterministic planner builds Delta plus its remaining Full continuation. Delta can finalize only `SUPPORTED`; otherwise it emits internal `NEEDS_FULL`. Completed Full produces the final semantic union `SUPPORTED(primary_ref, required_refs[]) | UNSUPPORTED`; incomplete coverage/execution is separately `UNRESOLVED(reason)` and KEEP. `REBIND_SUPPORT` atomically attaches target-Revision Support and marks the replaced assertion inactive without altering Memory identity or rewriting historical rows.

### Domain vocabulary

The durable design uses responsibility names rather than model-stage numbers:

| Responsibility | Meaning |
| --- | --- |
| Claim Extraction | extract new claims from authorized current change |
| Support Assessment | test one fixed existing claim and rebuild its complete current Evidence Unit |
| Claim Reconciliation | classify every mandatory same-Unit Candidate/Memory pair after deterministic exact consumption |
| Lifecycle Reconciliation | reduce current Support and relation results into guarded domain mutations |

Historical implementation notes may retain L1/L3/L4 labels, but public types,
methods, result states and new documentation must use the domain names above.

### Backend-neutral context and judgment execution

`RevisionContextPlanner` returns application-owned context, authority and work
manifests rather than a provider prompt. The selected plan is rendered as a
backend-neutral `ContextBundle` whose stable contract and revision-shared
material precede cohort, carried-state and attempt-only material. This permits a
Structured LLM adapter to use provider prompt-prefix caching without making
cache retention part of correctness, and permits an eligible classifier adapter
to evaluate the same state without reconstructing revision context.

Open-vocabulary Claim Extraction remains `GenerationWork`. Closed-set semantic decisions are `JudgmentWork`; a classifier model backed by
TypeSafe/Jev or a small-parameter LLM implements the judgment interface only where
its task-specific evaluation satisfies the complete contract. Runtime confidence
does not switch individual items to another backend. Classifier models do not
generate claims, discover arbitrary Evidence or reproduce compound Support
Assessment. Executor,
model, contract and context digest participate in work identity. Exact selector
validation, complete manifests, lifecycle reduction and destructive validation
remain application-owned for every executor.

The complete decision, operation inventory, cache layout and evaluation gate are
in [ADR 0036](0036-separate-semantic-work-from-inference-executors.md) and
[Semantic judgment execution](../design/semantic-judgment-execution.md).

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
| `EXACT_UNCHANGED` | one compatible exact fragment and unchanged container | current ref; direct REBIND if no changed groups |
| `CONTAINER_CHANGED` | exact fragment survives inside a changed ReadingGroup/container | current exact fragment + ChangeBundle; no old excerpt |
| `MODIFIED` | object/structure remains but fragment text changed | old exact excerpt + current corresponding ReadingGroup |
| `REMOVED` | authoritative complete coverage proves the old fragment absent | old exact excerpt + current-full scope |
| `AMBIGUOUS` | exact/structural correspondence is not unique | old exact excerpt + all candidate ReadingGroups |
| `UNKNOWN` | partial coverage cannot prove presence or absence | deterministic `UNRESOLVED(partial_coverage)`, KEEP, no model call |

`EXACT_UNCHANGED` proves survival of the original fragment, not absence of a distant exception. All added/modified ReadingGroups are grouped into capacity-safe ChangeBundles. A classifier model evaluates every exact-rebound fixed claim against each bundle as `AFFECTED` or `UNAFFECTED`; code OR-reduces multiple bundles. Only all-`UNAFFECTED` work completes KEEP+REBIND. There is no per-item confidence fallback.

The application retains Memory, Support and Evidence IDs, Observation/Revision identity, exact digests, coverage and provenance outside model input. Historical excerpt transfer is exhaustive and exclusive: `MODIFIED`, `REMOVED` and `AMBIGUOUS` receive it once; no other status does. The excerpt is immutable, non-selectable historical material.

### Delta and current-full input

`ReadingGroup` is a coherent current structure containing one or more selectable EvidenceFragments. `AssessmentContext` is one call's one-or-more ReadingGroups and prompt-local Evidence Catalog. `AssessmentScope` is the complete logical DELTA or FULL_CURRENT_REVISION work.

Delta contains all changed ReadingGroups, fixed claims/compact Support metadata, current context for directly affected Evidence, and historical excerpts exactly for `MODIFIED`, `REMOVED` and `AMBIGUOUS`. Evidence distribution alone does not approach Full. The planner deterministically produces Delta contexts and the remaining current-full continuation from exact correspondence, CatalogDiff, coverage, manifest and capacity. It never asks a model whether a negative Delta is conclusive. Delta can complete only a positive `SUPPORTED` result; otherwise work continues through the remaining Full contexts. The planner starts Full directly when Delta already covers the complete Full manifest, or when the complete serialized Full forecast is no more expensive than Delta plus continuation.

Current-full means all eligible effective-current Catalog contexts are processed. A small document may fit one AssessmentContext; a large one streams several contexts under one manifest and grounded previous state. Only complete context coverage plus authoritative provider coverage may produce `unsupported`; Full never upgrades a partial Projection.

`REVISION_FIRST` evidence-fixed batching and `COHORT_FIRST` cohort-fixed streaming are separate deterministic cache layouts. The first puts current Catalog before changing claim cohorts; the second puts fixed unresolved claims before changing AssessmentContexts. Previous state remains in the changing suffix. Cache behavior cannot alter scope, work identity or result.

### Cumulative Support witness state

Support Assessment works at `(memory_id, independent_support_id)` granularity. An Evidence Unit remains one Primary plus zero or more Required refs, possibly selected from several fragments or ReadingGroups in the current AssessmentContext.

The final semantic wire result is `SUPPORTED(work_id, primary_ref, required_refs[]) | UNSUPPORTED(work_id)`. Only `SUPPORTED` admits selectors. Its selectable current pool is the current AssessmentContext catalog plus current refs grounded by earlier contexts and rehydrated with exact current text in `carried_witness_catalog`; historical refs are never selectable. Streamed model output carries only `witness_delta` additions. Application code validates and monotonically union-merges them into grounded supporting/opposing sets, so omission cannot erase an earlier witness; no cumulative status is model-owned. Delta completion returns `SUPPORTED` or internal `NEEDS_FULL(witness_delta)`; completed Full returns `SUPPORTED` or `UNSUPPORTED`. Partial coverage, incomplete manifests, capacity/provider/schema failure, model abstention or order disagreement become application-owned `UNRESOLVED(reason)` and KEEP.

### Complete same-Unit Claim Reconciliation

Same-Unit Claim Reconciliation consumes deterministic exact matches, then creates the complete remaining Candidate × Active-incumbent pair manifest. A classifier model (Jev or small-parameter LLM) returns exactly one `EQUIVALENT`, `REFINES`, `CONTRADICTS`, `UNRELATED` or `INSUFFICIENT` label per pair. Catalog bodies are shared state; pair questions carry application IDs.

Capacity partitioning preserves the full manifest and runs under bounded concurrency. Missing/duplicate pairs, unknown IDs, truncation and provider failure cannot become `UNRELATED`. Partitions create no lifecycle state and publish no partial mutations. Relation labels are proposals and cannot authorize REMOVE or RETIRE. Cross-document discovery keeps bounded hybrid retrieval followed by classification over K pairs, where non-destructive recall loss remains accepted. Candidate-to-candidate semantic deduplication remains out of scope.

### Automated destructive validation

There is no human confirmation step. Before applying a proposed
`REMOVE_SUPPORT`, `SUPERSEDE` or `RETIRE_MEMORY`, Lifecycle Reconciliation runs
an automatic `DestructiveValidation` over the affected fixed claims. It verifies:

1. authoritative coverage or an explicit tombstone for every affected object;
2. complete Claim Extraction and Support Assessment manifests with no technical
   failure or unresolved independent Support;
3. resolvable decisive current witnesses and non-stale Support-set hashes;
4. every `UNSUPPORTED` proposal binds a completed authoritative Full receipt;
5. the aggregate active-Support count after simulating source-scoped removals.

The validator does not run another semantic scan. Support Planning/Assessment
owns the single Delta-to-Full continuation; DestructiveValidation verifies its
receipt, manifests, witnesses, Support count and stale guards. Unknown coverage,
unresolved execution, capacity failure or stale input yields KEEP and leaves the
validation baseline unchanged. Only zero
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
   snapshots. A source-neutral revision-input planner first determines the minimum
   safe scope, then constructs every eligible reading plan: complete changed
   ReadingGroups with compact Support metadata, current context for affected or
   ambiguous Evidence and bounded exact history only for `MODIFIED`, `REMOVED` and
   `AMBIGUOUS`; and complete current input without non-current history. When both
   plans satisfy the same correctness requirement, it forecasts their actual
   request formats and chooses the lower token cost; delta wins an exact tie.
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
3. One completed Support Assessment returns a discriminated semantic result for
   the fixed claim. `SUPPORTED` carries one current Primary and zero or more
   Required refs; `UNSUPPORTED` carries no selectors. Delta may only finalize
   `SUPPORTED`; otherwise internal `NEEDS_FULL` continues through the remaining
   Full manifest. Incomplete coverage or execution returns application-owned
   `UNRESOLVED(reason)` and KEEP. The application resolves
   complete current Evidence Units, and Required membership may split, merge,
   grow or shrink. An old offset locates only its own revision. Semantic selection
   of supplied current fragments does not reconstruct the author's edit history.
   Stored provenance remains exact and immutable.
4. Same-Unit Claim Reconciliation consumes deterministic exact matches, then
   classifies the complete remaining Candidate × Active-incumbent pair manifest.
   Every pair returns exactly one EQUIVALENT, directional REFINES, CONTRADICTS,
   UNRELATED or INSUFFICIENT label. Omission, duplicate output, unknown IDs and
   truncation are technical failures, not relationship labels. `REFINES` denotes
   the same knowledge item with a compatible directional change; the label alone
   still cannot replace a broader incumbent with a narrower rule. The reducer
   combines the complete relation manifest with Candidate admission, Support
   Assessment, source authority and scope facts before proposing actions. Relation
   labels never directly authorize destructive mutation.
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
does not recognize the gap. Current-full eliminates that particular omission for
a fitting current snapshot, but does not claim semantic recall. A completed Delta
that cannot establish Support normally transitions through `NEEDS_FULL`; it is
not an error. Illegal provenance, incomplete planned execution or provider
coverage, visibility errors, model abstention and destructive-authority
violations instead produce typed unresolved/fail-closed outcomes.
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
The latter is `UNRESOLVED(missing_or_invalid_baseline)` and must not be converted
into current-full, semantic `unsupported`, or a successful empty result. L1 likewise
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

Same-Unit sparse claim assessment uses the shared request catalog and completion
validator described in ADR 0009. Challenger/incumbent references are `NEW`/`MEM`;
Evidence catalog references are `PRM`/`REQ`, each followed by four digits. The
claim work identity includes the changed contract and schema, so older completed
work cannot be reused against a different catalog. This does not change current
Evidence entailment, complete incumbent support auditing, conditional exact
comparisons between competing refiners, or destructive revision proof.

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

The revision-input planner supersedes both blind full-first execution and a
negative conclusion from Delta alone. It is source-neutral: representation profiles supply exact
structures and reading groups; the planner does not branch on Confluence, Jira,
Teams, GitHub, local files, or agent clients. Support Assessment has one model responsibility:
assess the fixed claim and update its current Support evidence in light of the
selected complete input. A rule remaining in force is distinct from execution
compliance; missing results or unfinished examples do not by themselves revoke a
normative obligation. Deletion, rewrite, heading/scope change, and Required
split/merge use that same contract rather than source-specific classifiers.

For a valid base/target pair, the planner constructs Delta contexts plus the
ordered remaining current-full continuation. Delta contains all changed current
structures, bounded current reading groups, compact prior-Support metadata,
current candidates for exact unchanged Evidence, and bounded exact historical
excerpts only for `MODIFIED`, `REMOVED` or `AMBIGUOUS` Evidence. It does not repeatedly
transport unchanged historical Support bodies or semantically search for current
Evidence after exact correspondence fails.
Current-full contains the complete eligible effective current snapshot and omits
non-current `oldhistory`. “Full” means coverage of that current Source Projection,
not provider version
history, deleted upstream data, a repair for incomplete collection, or a grant of
new extraction authority. Partial Projection carry-forward remains current input;
an upstream omission without authoritative coverage still cannot prove deletion.

The plan receives a deterministic request-format forecast across all requests,
including prompt/schema transport, repeated material, initial/carried-state
reserve, output reserve and images. Every emitted request still passes actual
capacity admission. A plan is eligible only when every indivisible ReadingGroup
fits the route. Support starts with Delta unless Delta already covers the complete
Full manifest, or the complete serialized Full plan is no more expensive than
Delta plus its possible continuation. Delta can finalize
only `SUPPORTED`; otherwise internal `NEEDS_FULL` consumes the planned remainder.
Only completed current-full may finalize `UNSUPPORTED`. Claim Extraction and
Support Assessment may both stream exact ReadingGroups under complete manifests,
but Claim Extraction still limits Primary to authorized current work. The planner
does not use edit ratio, document-size percentage, Fragment-count percentage or
source-type preference, and it never asks a model whether a negative Delta is
conclusive.

A fitting delta and claim group uses one model request. Larger deltas use the same
cumulative assessment contract over stable Source batches. Each request receives
the fixed claims, compact Support metadata, current exact catalog, the affected
bounded historical excerpts and processed-group metadata. Cumulative state is
application-owned: code validates and monotonically union-merges each model
`witness_delta` into supporting/opposing current refs; the next request rehydrates
that union with exact current text and Primary eligibility. It does not
carry an unbounded prose narrative or cumulative Support status. Final status is
derived only after the complete group manifest is satisfied; an unrelated later
group cannot erase an earlier revocation or exception.
Batches describe one base/target pair, not intermediate Source revisions. When
Support Assessment has no recorded verified baseline and complete-current proof is permitted,
current-full uses the same executor without assuming old Support validity. A
named but unavailable or mismatched baseline is not this case and fails before
semantic assessment.
Here “old” means Evidence from the historical Source revision. Earlier batches
of this same target revision remain valid assessment context in both modes;
their selected current refs remain grounded because the next batch supplies the
corresponding exact text through `carried_witness_catalog`.

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
forgetting an earlier judgment. A Support Assessment that cannot complete produces
`UNRESOLVED(reason)`: the program emits a bare NOOP / KEEP, preserves its existing
Support and Evidence, and does not advance its validation baseline. If any
independent Support is unresolved, the whole incumbent is skipped for this round.
Other incumbents and extraction candidates continue, and the Source revision may
commit. No Review or hidden model substitution is required. The existing Plan
records the exact preserved Support IDs on its KEEP decision under the usual
Support-set stale guard. This exception cannot validate a new attachment or
authorize destructive mutation.
Skipped incumbents remain in the complete same-Unit relation manifest, but their
preserved Support prevents those relation labels from authorizing a destructive
action. They also remain eligible for ordinary candidate identity matching and
independent corroboration. A later assessment still uses each
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

Claim Reconciliation returns one relation label per mandatory pair and does not
repeat Support or Evidence selectors. UNRELATED is valid whether Support Assessment
supported the incumbent or not. CONTRADICTS proceeds through the existing
authority/Review action table; old support does not invalidate a contradictory
relationship by itself. An equivalent admitted challenger paired with an
unsupported incumbent, a refinement relation that conflicts with the Support
result, or `INSUFFICIENT` pair material is unresolved locally. Candidate admission
already owns whether supplied current Evidence entails the challenger, including
table column associations; relation classification cannot repair candidate text.

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

The target relation contract names the newly admitted claim `challenger` and the
active Memory `incumbent`; it does not reuse the former ambiguous `candidate_*`
revision-proof fields. `REFINES(challenger, incumbent)` means the same knowledge
item is stated more specifically in that direction. Lifecycle policy still rejects
whole-incumbent replacement when the challenger narrows population, time or scope
and therefore cannot preserve the incumbent's complete truth conditions.
Unsupported old claims need not be negated: loss of universal coverage alone does
not establish contradiction with a compatible subset rule.

Acceptance must evaluate the complete revision conjunction and the resulting
reducer action. Correct Support, relation and preservation fields alone do not
prove an eligible UPDATE. Frozen failed results remain evidence even when a later
prompt/schema version corrects them.

## Complete same-Unit pair classification

The earlier sparse-output contract is superseded for same-Unit work. Claim Reconciliation now classifies the complete exact-excluded Candidate × Active-incumbent pair manifest with a task-admitted classifier model. Every pair has one explicit relation label; omission is a technical failure, not “no edge.” Catalog text is encoded as shared state and token-aware request rectangles carry pair IDs, so model input does not duplicate both claim bodies for every pair.

The logical product may be large, but batching remains a computation detail. It cannot cap pairs, change atomicity, add business states or weaken same-source incumbent coverage. Existing Source Authority, Support Assessment, DestructiveValidation, stale guards and atomic commit remain mandatory; even `CONTRADICTS` is not a lifecycle action.

Cross-document relation discovery remains a different contract: existing access-filtered hybrid retrieval generates bounded K pairs and the same classifier labels them. Full-workspace N × M is not required, and a missed cross-document relation cannot authorize destructive mutation.

Completed classifier work binds exact pair manifest, catalog/context digests, executor/model/contract identity and budget. Retries compute unfinished transport partitions but cannot reuse judgments under changed input. SQLite and HANA still require complete work before applying the Source projection/Lifecycle Plan.

## Complete Support requests and model-facing identifiers

Support Assessment plans Delta contexts and the remaining current-full continuation
for the complete fixed-claim cohort under one validation baseline. It starts Full
when Delta already covers the complete Full manifest, or when the complete
serialized Full plan is no more expensive than Delta plus its possible
continuation. Only a measured input, image, mandatory response-row,
or cumulative-state capacity failure invokes the existing transport partitioning.
This supersedes both selecting a packing by score before trying complete coverage
and choosing a mode merely because one request fits. Delta includes changed
material, exact current candidates for prior Support, representation-owned
reading groups, and bounded historical excerpts only for `MODIFIED`, `REMOVED` or
`AMBIGUOUS` Evidence. Current-full reads the
eligible effective current projection without carrying non-current history or
changing its provider coverage meaning.

Delta response is `SUPPORTED(...)` or internal `NEEDS_FULL(witness_delta)`; Full
response is final `SUPPORTED(...) | UNSUPPORTED`. The response remains one
independent judgment per work item with only its selected
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
Implementation must allocate successor Support-work and revision-input contract
identities for the Delta/Full continuation and witness schemas; old completed work
is never reinterpreted as new-wire output. Evidence compiler and lifecycle
semantics are unchanged.


### Compact Support judgments

Final Support judgments use discriminated variants. `SUPPORTED` carries work ID,
status and complete Primary/Required refs; `UNSUPPORTED` carries only work ID and
status and cannot carry selectors. The final model wire result does not carry
generated prose. During streamed assessment, the model returns only current
`witness_delta` additions; application code validates and monotonically unions
them into supporting/opposing sets. Each next call rehydrates that union with exact
current text and Primary eligibility. Delta may return internal
`NEEDS_FULL(witness_delta)`; incomplete execution is application-owned
`UNRESOLVED(reason)`, not a semantic model status. Application diagnostics may retain
a bounded decisive basis outside the final wire result. This supersedes the
assumption that every successful item needs a
generated reason. The canonical stored result retains a deterministic success explanation; downstream
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
