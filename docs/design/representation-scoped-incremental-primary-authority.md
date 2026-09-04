# Representation-scoped Incremental Primary Authority

Status: Implemented for review in [OSS issue #390](https://github.com/shno-labs/mem-forge/issues/390)

Date: 2026-09-04

Canonical decision to amend during implementation: [ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md)

## 1. Decision

MemForge will create one provider-neutral `ProjectionEvidenceWorkPlanner` for
every active extraction contract whose descriptor has
`uses_fragment_catalog=true`. The planner receives the immutable committed base
revision, the immutable staged target projection, the authorized work
transition, and the access identity. It returns exact current-revision candidate
ranges with deterministic Primary eligibility.

`projection-extraction-v9` is the currently affected contract, not the dispatch
condition. A future v10 or later fragment-catalog contract inherits this seam
automatically through its active contract descriptor. Historical exact replay
continues to use the authority policy recorded by that historical contract.

The public design has one flow for every Source type:

```text
provider payload
  -> SourceProjectionAdapter
     owns identity, topology, edit/delete facts, relations and coverage
  -> immutable base + staged target Source Projection
  -> ProjectionEvidenceWorkPlanner
     owns current-work authority and bounded Context planning
  -> EvidenceCandidateRange(primary_eligible=true|false)
  -> Evidence Fragment Compiler
     owns representation parsing and exact Fragment boundaries
  -> Fragment Catalog
  -> LLM selects primary_ref + required_refs
  -> Resolver, Evidence Unit and existing lifecycle pipeline
```

The planner module has three private representation adapters behind one shared
`RepresentationIndex` seam:

1. range-addressable text: `markdown-structural` and `plain-text`;
2. registered `canonical-record`;
3. whole-object `binary-artifact`.

The index is the one implementation of structural/field boundaries used by
both authority planning and Fragment compilation. The planner and compiler do
not parse CommonMark, raw HTML, canonical JSON, or nested text independently.

There is no Jira, GitHub, Teams, Confluence, or client-specific branch in the
Evidence or lifecycle layer. A future Source reuses one of these representation
contracts or registers a new representation contract with exact coordinates.

## 2. Problem being fixed

The active Support-v2 / `projection-extraction-v9` path currently calls
`plan_projection_extraction_batches()` directly. It sees that an Observation
changed, but it does not consume the existing base/target changed ranges when
deciding which current text may become Primary.

For a document represented by one text Observation, a small edit therefore
becomes:

```text
one paragraph changed
  -> Observation semantic hash changed
  -> RevisionDelta contains WHOLE_OBSERVATION
  -> v9 makes every Fragment in the current document Primary-capable
```

This is wrong because complete read/parse access is not the same as claim
authority. The model may need surrounding old text to understand a change, but
unchanged old text must not be presented as a newly authoritative Primary.

Minimized current-code probes establish the boundary:

| Update | Current result | Expected result |
| --- | --- | --- |
| Jira adds one comment Observation | only the new comment is Primary-capable | correct |
| GitHub appends one Markdown section | the whole file is Primary-capable | only changed complete structures are Primary-capable |
| Jira changes only `/description` | unchanged summary, status and labels are also Primary-capable | only the changed description field is Primary-capable |

The large meeting-minutes incident is one consequence: historical text was
allowed to produce new candidates, which inflated downstream mandatory
candidate/incumbent relation work. Relation reconciliation remains complete;
the fix removes work that should never have become a new candidate.

## 3. Invariants

The implementation must preserve all of these rules:

1. **Primary comes from authorized work.** In an ordinary incremental run, a
   structure that is disjoint from every changed target range cannot become
   Primary. The smallest safe structure intersecting a change may include
   unchanged characters needed to preserve a claim-coherent Evidence Fragment.
2. **Context is not authority.** Current, accessible old material may be
   Required-only or display Context; Source relations never grant Primary.
3. **Parse access is not role access.** A compiler may read a complete canonical
   record or structural block while only a contained changed range is Primary.
4. **The compiler never widens.** It may split or narrow an authorized range into
   exact Fragments; it cannot make an unauthorized parent or sibling Primary.
5. **No LLM decides what changed.** Change detection, eligibility, and reference
   validation are deterministic.
6. **Deletion does not create a claim.** Removal-only work produces no new
   Primary candidate but still runs incumbent Support and lifecycle evaluation.
7. **Retry uses the same facts.** The same committed base, staged target, work
   kind, policy version and ranges reproduce the same catalog digest.
8. **Batching is only presentation/computation.** It cannot change authority,
   lifecycle state, complete coverage, or atomic commit semantics.
9. **Failure is typed and fail-closed.** An unmappable change never falls back to
   the whole document or whole record.
10. **Historical truth is preserved.** This change does not rerun ingestion,
    mutate existing Memories, fabricate lineage, or rewrite lifecycle history.

## 4. Module boundary

### 4.1 Internal interface

The implemented extraction interface is intentionally smaller than the
conceptual transition value considered during design:

```python
plan_projection_evidence_work(
    target_projection,
    committed_base_snapshot,
    reprocess_all_current_observations,
    extraction_contract_version,
) -> tuple[ProjectionExtractionBatch, ...] | TypedPlanningFailure
```

`SourceUnitDeriver` binds this plan to the access-context and inference-
capability hashes. `SourceUnitDerivationContext` carries the source-activity
epoch and, for an all-current reprocess, the explicit source-sync operation ID.
Those values participate in derivation identity without creating another
public request hierarchy or persistent business state.

The supported extraction transitions mean:

- `INITIAL`: the target Observation is newly introduced;
- `INCREMENTAL`: compare the request's committed current base snapshot captured
  at staging with the staged target;
- `REPROCESS`: all-current scope is explicit and carries the authorizing source
  sync operation identity; when a previous revision exists, the same committed
  base validation remains mandatory.

NOOP Evidence-Unit revalidation is deliberately not routed through the new-
candidate extraction planner. The existing revision-pinned revalidation
compiler in `projection_fragments.py` authorizes the complete current/rebound
Primary-plus-Required set for one named Evidence Unit. Keeping that separate
prevents extraction scope from becoming lifecycle authority and avoids a second
transition state machine. Independent Evidence Units are not flattened.

The top-level committed base snapshot is one value containing the Unit revision and its complete
Observation Revision membership. The caller cannot pass an unrelated Unit row
and a separate arbitrary revision mapping. The planner verifies the snapshot's
Unit ownership, complete membership, and equality with
`RevisionDelta.previous_unit_revision_id`. `None` is valid only for `INITIAL`;
`INCREMENTAL` and reprocessing an existing revision use the same committed base
for plan identity and stale guards.

The result contains:

```python
ProjectionEvidenceWorkPlan(
    base_unit_revision_id=...,
    target_unit_revision_id=...,
    primary_ranges=(EvidenceCandidateRange(..., primary_eligible=True), ...),
    required_only_ranges=(EvidenceCandidateRange(..., primary_eligible=False), ...),
    display_context=(...),
    access_context_hash=...,
    source_activity_epoch=...,
    inference_capability_hash=...,
    authority_policy_version=...,
    digest=...,
)
```

This is one deep-module facade. Private representation mapping, bounded Context
selection, and presentation packing do not leak source-specific concepts to
callers.

### 4.2 Responsibility split

| Module | Owns | Must not own |
| --- | --- | --- |
| `SourceProjectionAdapter` | provider identity, stable Unit/Observation topology, immutable revisions, provider semantic/location/membership/access change facts, relations, coverage, representation profile and deterministic canonical provider shape | Primary/Required roles, schema comparison values, or Memory lifecycle actions |
| `ProjectionEvidenceWorkPlanner` | transition validation, representation-scoped changed authority, bounded current Context, access/source-activity/model-capability binding and stable plan digest | provider API semantics, model judgments, Memory actions |
| private representation adapter / `RepresentationIndex` | one implementation of base/target structural or field mapping and exact target coordinates | Source type branches or lifecycle policy |
| Evidence Fragment Compiler | exact structural/field Fragment compilation inside supplied ranges | widening authority or inferring change |
| LLM | claim content and selection among offered refs | offsets, IDs, change detection, eligibility, lifecycle action |
| Resolver / lifecycle | exact ref validation, Evidence Unit, Support and lifecycle safety | repairing or guessing an invalid authority plan |

The `SourceProjectionAdapter` still determines that an Observation was added,
changed, removed, moved, or access-modified. The work planner translates only a
confirmed content change into Evidence authority using the Revision's declared
representation. This keeps provider facts at the projection seam and Evidence
authority at the Evidence seam.

`ProjectionEvidenceWorkPlanner` replaces the authority selection, Context
ownership and authority digest responsibilities currently embedded in
`plan_projection_extraction_batches()`. Presentation batching either stays
private to this module or becomes a pure packer that consumes already authorized
ranges. The old changed-Observation/whole-authority path is removed for active
fragment-catalog contracts; it cannot remain as a parallel entrypoint.

## 5. Representation algorithms

### 5.1 Range-addressable text

Applies to `markdown-structural` and `plain-text`.

For `INCREMENTAL` work:

1. load exact base and target Observation Revision content;
2. build base and target views with the registered `RepresentationIndex`;
3. deterministically pair unchanged structures using content hash and structural
   ancestry, then compute target-side changed half-open Unicode ranges;
4. expand each range through the same index to complete, claim-coherent
   structures;
5. merge only identical or overlapping authorized structures;
6. emit those current target ranges as Primary-capable;
7. use bounded accessible neighbors, parents and related Observations only as
   Required-only or display Context.

Examples of complete structures are a paragraph, list item, table row or whole
table when row isolation is unsafe, blockquote, code block, and CommonMark raw
HTML block. A one-character edit is not exposed as one-character Evidence. The
existing Markdown/private raw-HTML compiler seam owns structural boundaries.

A block moved without content or structural-ancestry change remains unchanged
and is not reauthorized. Moving content under a different heading/list/table
owner may change its meaning and is therefore changed work. Duplicate structures
are paired only when occurrence mapping is deterministic. An ambiguous duplicate
mapping returns the typed unmappable result instead of selecting an arbitrary
occurrence or widening to the document.

If base/target coordinates cannot be mapped exactly, return
`INCREMENTAL_AUTHORITY_UNMAPPABLE`. Do not authorize the whole document.

### 5.2 Canonical record

The representation adapter parses the complete base and target canonical JSON
into the shared index because exact JSON Pointer and escaped-string coordinates
require the full record. The planner then compares only fields registered in the
record's versioned schema.

For each registered field:

- unchanged semantic value: not Primary; it may be bounded Required-only Context;
- added or changed selectable value: map its exact current raw JSON range and
  make only that field Primary-capable;
- removed value: no current Primary range; record removal work for incumbent
  Support evaluation;
- nested Markdown/plain text: apply the registered nested representation mapper
  within that field, then map the result back to exact canonical JSON ranges;
- unregistered metadata change: no Primary authority.

A canonical schema may also declare a deterministic tombstone signal that is
not selectable Evidence. Target state is authoritative: whenever the target
signal is active, that Observation contributes zero Primary ranges, including
an initially collected or exactly retried already-deleted record. If a prior
live representation exists, its claim-bearing ranges enter complete Evidence
Unit revalidation. This is explicit provider deletion, not an omission: it
applies even when the enclosing Source Projection is partial and takes
precedence over the general Added Observation rule. Teams uses its existing
deleted timestamp this way; future Slack/email message schemas can reuse the
same representation contract without a source-specific branch.

This is deliberately not a generic recursive JSON diff. A source adapter
registers a bounded schema of claim-bearing fields. Arrays or objects declared
as one field are compared as one semantic field unless the schema explicitly
defines stable child fields.

For this fix, existing stored canonical JSON and the v1 schema remain unchanged.
The versioned canonical schema owns a deterministic comparison projection for
each registered object-valued field. For Jira status, priority, assignee and
resolution, both base and target are reduced to the same stable claim-bearing
identity/label subset before equality is tested; volatile URLs, avatar/icon
metadata, expansion fields, and transport-only shape do not grant authority.
The raw immutable record and Fragment coordinates remain unchanged.

This avoids a false one-time v1-to-v2 content change for existing Jira bases. A
future change to the stored canonical shape must use a new representation schema
plus an explicit old/new compatibility mapper. Without that mapper, mixed-shape
comparison fails closed and cannot masquerade as a business-content update. The
planner does not perform generic recursive provider-object diffing.

`atomic field` means the field remains an indivisible Evidence Fragment when
that field changes. It does **not** mean an attachment, timestamp, deletion
marker, or other non-selectable field may reauthorize unchanged claim text.
Whole-record Primary is allowed only when the schema explicitly declares the
record itself as the claim-bearing field, as Jira changelog currently does.

If a registered pointer has an invalid runtime type or cannot map exactly,
return `CANONICAL_FIELD_MAPPING_INVALID`. Do not authorize sibling fields or the
whole record.

This implementation changes the prior compiler precondition that rejected a
canonical-record `REVISION_RANGE`. The compiler still receives and parses the
complete immutable revision, but it accepts only exact field/nested ranges that
the same registered `RepresentationIndex` can validate. Complete parse access no
longer implies a `WHOLE_OBSERVATION` Primary range. Planning and compilation
share the index implementation and index digest; they do not duplicate parsers.

### 5.3 Whole binary Artifact

A current Artifact remains atomic, but selectability is decided by one shared
`artifact_selectable_for_model` predicate used by planning, batch loading, and
catalog construction:

- newly added Artifact bytes: whole Artifact may be Primary;
- changed Artifact bytes: whole current Artifact may be Primary;
- metadata, filename, location, or access-only change: no new Primary;
- removed Artifact: no new Primary; evaluate incumbent Support;
- bytes not supplied to or unsupported by the configured model: never selectable
  Evidence.

The fix does not invent byte ranges, OCR lineage, or filename-based Evidence.
For example, the current loader can supply valid supported images; a PDF is not
selectable merely because its media type is accepted for storage. PDF Evidence
requires an actual model-loading or exact page-coordinate contract.
The predicate is resolved from the request's versioned
`inference_capability_hash`, which is also part of plan and catalog identity;
planning cannot reuse an Artifact decision under a model capability set with a
different hash.

## 6. Operation semantics

| Operation | Primary authority | Other required work |
| --- | --- | --- |
| Initial projection | all inference-eligible ranges owned by the current batch | bounded Context; complete lifecycle plan |
| Added Observation | complete declared representation of the new Observation | existing related Observations remain Required-only/Context |
| Text edit | changed complete structural ranges in the target | unchanged text may be bounded Context |
| Canonical field edit | changed registered claim-bearing fields only | unchanged fields may be bounded Context |
| Non-selectable metadata edit | none | projection/read-model update only |
| Canonical tombstone signal is active in target | none, even for an added or retried Observation | if a prior live representation exists, revalidate/removal-review every complete Evidence Unit supported by its claim ranges |
| Location/rename-only | none | preserve/validate provider identity and rename lineage |
| Provider access-only | none | advance the projection only under the source-activity fence; do not extract a claim or silently rewrite Support visibility |
| Removed field/range inside a present Observation | none | revalidate every complete Evidence Unit that selected the removed range |
| Observation/Artifact absence under complete authoritative coverage | none | create the existing exact review-gated Support-removal proposal |
| Omission under partial/ambiguous coverage | none | carry forward the prior revision and Support; absence is not proven |
| Approved exact Support removal | none | remove only that Evidence-Unit Support; retire only if no other complete active Support remains |
| Explicit reprocess | exact operator-selected current ranges, or explicit all-current scope | distinct auditable operation and policy identity |
| Evidence revalidation | exact current/rebound incumbent ranges authorized by the revalidation command | existing stale and authority guards |
| Exact retry/restart | identical persisted plan | no new diff, no LLM-based widening |

Pending or rejected removal Review does not silently delete old Support. Pending
Review preserves the existing active/contested Support according to the accepted
lifecycle contract. Review approval is stale if the Source revision, any selected
Evidence Unit, affected Memory, Support topology, access authority, or source
activity epoch changed. Multiple independent Supports are evaluated separately;
removing one does not retire a Memory still supported elsewhere.

`SourceUnitRevision.access_hash` is a provider projection fact.
`EvidenceUnit`/Support `access_context_hash` is lifecycle authority. A provider
access or location update may advance projection state without claim extraction,
but a lifecycle access-context change invalidates the prepared plan and follows
the existing scope-transition/lifecycle rules.

## 7. Source-type coverage

All currently specialized Source types and the extension seam are covered
below. Tests must enter through the active Support-v2/v9 derivation interface,
not only call a private compiler helper.

| Source / Observation | Representation | Incremental Primary rule | Required acceptance case |
| --- | --- | --- | --- |
| Confluence `page_body` | `markdown-structural` | only changed title/body structures; unchanged page history is not Primary | edit one paragraph; an unchanged section cannot be selected as Primary |
| Jira `issue_core` | `canonical-record: jira-issue-core` | only changed registered fields after schema-owned stable comparison projection; nested `/description` uses Markdown structures | description-only and status-icon/avatar-only edits do not authorize summary/status/labels |
| Jira `comment` | `canonical-record: jira-comment` | a new comment authorizes `/body`; an existing body edit authorizes the changed body structure; attachment-only change authorizes nothing | add comment, edit body, and attachment-only regressions |
| Jira `changelog` | `canonical-record: jira-changelog` | new stable history Observation is Primary; the registered root record remains atomic | old histories stay non-Primary when one new history is appended |
| Jira Artifact | `binary-artifact` | added/changed bytes are whole-object Primary only when the shared model-selectability predicate succeeds | attachment inventory, filename, or stored-but-unsupplied PDF alone is not Evidence |
| GitHub Repository `file_content` | `markdown-structural` | only changed complete file structures | append one section; old sections are Required-only/Context |
| GitHub Repository Artifact | `binary-artifact` | changed supplied bytes only when the shared model-selectability predicate succeeds | rename/location-only does not re-extract bytes |
| GitHub Pages `page_content` | `markdown-structural` | only changed complete rendered-page structures | navigation/template noise does not authorize unchanged claim text unless normalized semantic content actually changed there |
| Local Markdown `file_content` | `markdown-structural` | only changed complete file structures | edit list/table/raw-HTML content without widening to the whole file |
| Teams `message` | `canonical-record: teams-message` | new message authorizes `/content`; content edit authorizes changed nested text; attachment-only edit authorizes nothing; active deleted signal invalidates prior content Support without new Primary | add, content edit, unchanged-content delete, and attachment-only regressions |
| Teams hosted image | `binary-artifact` | added/changed and actually supplied valid image bytes only | message metadata, invalid/oversized image, or unsupplied media cannot stand in for image Evidence |
| Agent Session `session_summary` | `markdown-structural` | new immutable window is naturally bounded; an updated same-identity window authorizes only changed structures | run for both Codex and Claude clients; client identity does not change semantics |
| Managed Agent concept, currently projected as `session_summary` | `markdown-structural` after upstream user-authority validation | exact newly projected or changed concept structures | exercise the real managed-knowledge producer; upstream event authorization remains required |
| Reserved `agent_concept` observation contract | registered `markdown-structural`, but no current normal producer | no new runtime behavior in this fix | keep dormant/legacy contract readable; do not migrate stable Observation identity |
| Extension fallback `document_content` | declared normalized `markdown-structural`, partial coverage | changed complete structures only; omission cannot prove deletion | unknown Source type gets identical Markdown behavior without a new Evidence branch |
| Binary Artifact from any Source | `binary-artifact` | same whole-object rule | SQLite/HANA parity across at least two provider paths |
| Direct User create/correction | no normal v9 Source extraction | explicit user authority; this planner is not called | existing Virtual Document provenance remains unchanged |
| Consolidated/read-model projection | no claim-authoring extraction | never becomes a new Primary source | no re-extraction of derived Memory text |

### Future Slack, email, HTML-only, PDF, and other types

- Slack should project stable message Observations and use a registered
  canonical-message schema. It inherits Teams-like representation behavior,
  not Teams source code or a Slack Evidence branch.
- Email/MIME should register claim-bearing headers/body/attachments as a
  canonical schema plus nested text and Artifact profiles.
- HTML-only content needs one exact reversible HTML representation adapter; it
  does not change this planner interface. CommonMark raw HTML remains private to
  `markdown-structural`.
- PDF needs page/object coordinates and revision identity before it may expose
  range-addressable Evidence. Until then, an eligible supplied PDF is atomic or
  unselectable according to its declared contract.
- Any new format that cannot provide exact current coordinates may be collected
  but must fail closed for new Evidence extraction.

## 8. Identity, staging, and retry

The base is the committed current Source Unit Revision captured when planning
and staging begins. This includes a location/access-only revision that advanced
without a Memory Lifecycle Plan. It is not a mutable normalized document row,
latest downloaded artifact, failed derivation target, or an older revision
chosen only because it last changed Memory state.

The lifecycle baseline is separate: current Support topology and hashes, Memory
versions, gate state, access authority, and source-activity epoch. The target is
the immutable staged projection for the current attempt. Before apply, the store
must prove that the committed current revision and lifecycle baseline still
equal the captured base; then target Projection and the complete Lifecycle Plan
commit atomically.

The existing derivation/batch identity must include:

- work kind and explicit scope;
- base and target Source Unit Revision IDs;
- ordered base and target Observation Revision IDs;
- complete representation profile and canonical schema versions;
- ordered Primary and Required-only candidate ranges;
- access context hash, source-activity epoch, and operation/authorization identity;
- versioned inference capability hash used for Artifact selectability;
- authority policy version;
- Context/presentation policy version already required by ADR 0030;
- resulting catalog digest.

Before the first remote model call, the canonical authority-plan payload above
is included in the existing staged derivation/batch manifest and batch input
hash. The payload itself, or all inputs sufficient to reconstruct it exactly,
must be atomically durable with the staged target. Persisting only a digest is
insufficient because a changed parser or policy could recompute different
ranges under the same target.

An exact retry loads or reconstructs this same manifest. Completed batch output
is reusable only under that exact manifest, and lifecycle commit must reference
the same derivation identity that produced the resolved Evidence. Recovery and
ordinary Source progress remain distinct:

- exact base, target, scope and policy match: `RESUME_EXACT_DERIVATION`;
- the same immutable base/target/stable scope but authority, presentation,
  extractor or compiler contract changed: `COMMIT_POLICY_REPLACEMENT`; the old
  attempt receives `DERIVATION_INPUT_SUPERSEDED`;
- target, base, source-activity epoch or access scope changed: create an ordinary
  new derivation and supersede the old attempt under the existing newer
  target/activity rules, not policy replacement;
- a representation profile/schema change that creates a new immutable Revision
  identity is a new target, not reuse of the old target.

A retry never compares the target against itself and interprets an empty diff
as permission for full-document extraction.

Pending/retryable work for an inactive extraction contract receives
`CONTRACT_SUPERSEDED`. Completed historical output remains immutable audit
history and cannot be applied as current-policy output. Historical
misclassification requires a separately authorized, exact operational recovery;
ordinary retry does not reactivate it.

No new replay ledger, dependency graph, or per-field lifecycle table is needed.
Use existing immutable revisions, expanded derivation manifests, and typed
failure fields.

## 9. Failure contract

The planner interface returns `ProjectionEvidenceWorkPlan |
TypedPlanningFailure`; it does not throw an unclassified exception before a
durable attempt exists. The facade translates implementation exceptions into
the following typed non-retryable policy/data failures and records the existing
safe runtime event/Finding:

| Code | Meaning | Disposition |
| --- | --- | --- |
| `INCREMENTAL_BASE_UNAVAILABLE` | required committed base snapshot cannot be proven complete | keep target staged and base current; report/review; no fabricated full extraction |
| `INCREMENTAL_AUTHORITY_UNMAPPABLE` | text change cannot map to exact target coordinates/structures | fail closed; no whole-document fallback |
| `CANONICAL_FIELD_MAPPING_INVALID` | registered schema field/type/raw range is invalid | fail closed; do not authorize siblings |
| `EVIDENCE_WORK_IDENTITY_INCOMPLETE` | active compiler work lacks its access-context or inference-capability identity | fail closed before the LLM; no unscoped batch reuse |
| `REPRESENTATION_PROFILE_UNSUPPORTED` | staged target profile is unknown | retain collected content only in the existing non-selectable staging/raw store; do not make it the current inference Revision |
| `REPROCESS_AUTHORIZATION_MISSING` | an all-current reprocess has no explicit source-sync operation identity | fail closed before the LLM; do not silently reuse ordinary incremental authority |
| `STRUCTURAL_UNIT_TOO_LARGE` | one complete authorized structure cannot fit the presentation budget | fail closed and preserve the complete structure; do not split it or retry the LLM |
| `AUTHORITY_PLAN_STALE` | base, target, policy, scope, or access context changed before apply | prepare a new derivation; do not reuse old output |

Transient provider/model/transport failures keep their existing bounded retry.
These deterministic authority failures do not become recoverable by resampling
the LLM. For every deterministic planning failure, the current Projection,
Document read model, Support and Memory remain at the committed base. A known
representation Artifact that deterministically fails the existing
model-selectability predicate may use the existing not-inference-eligible
coverage; an unknown profile cannot be smuggled into current inference state by
that path.

### Durable audit and Online Evaluation

Fail-closed planning must not become an invisible application-log-only error.
Before the attempt exits, the pipeline records one durable, content-safe runtime
audit event even though the staged target never becomes the current Projection.
The same attempt stores a canonical `authority_plan_identity` snapshot; it is
immutable on exact retry and is the source of the apply-time stale guard rather
than a value recomputed from mutable current state.
The event contains enough identity for deterministic Online Evaluation:

- outcome (`fail` or explicitly defined `degraded`) and typed reason code;
- Source, Source Unit, base/target Unit Revision, Observation Revision and
  derivation/attempt identity;
- work transition, representation profile/schema, authority policy, active
  extraction contract and inference capability identity;
- changed/authorized/unmappable structure counts and a bounded reason category;
- trace, deployment and source-activity epoch needed for runtime correlation;
- whether LLM invocation and lifecycle mutation were skipped.

It does not store raw source content, Evidence text, credentials, access tokens,
or unbounded parser errors. Exact retries keep attempt accounting but Online
Evaluation groups the same base/target/policy failure by stable identity instead
of presenting every retry as a new product issue.

The deterministic evaluator maps `evidence_authority_planning` to the
`evidence_authority_planning` criterion and labels a failed event `fail`. It
must treat an unexpected mapping/profile/schema
failure as a real authority-planning failure, not an extraction-model failure or
an evaluator false positive. Its bounded verification points back to the staged
base/target and stored plan/failure manifest; it must not require source
reingestion or Memory/lifecycle mutation.

## 10. Performance consequence

The planner reduces candidate creation before expensive relation-first
reconciliation:

```text
authorized changed structures
  -> extracted candidates
  -> exact duplicate/admission gates
  -> candidates x mandatory same-Unit incumbents
```

For the observed large file, every historical candidate removed before the
matrix avoids comparisons with every mandatory incumbent. This does not weaken
incumbent coverage, introduce top-k pruning, or promise that a true first import
or whole-document rewrite will be cheap.

The planner may stream or hold parser-owned structure metadata as the compiler
already does. It must not retain duplicate whole-document copies or add a
process-wide parse cache. Performance tests should measure candidate count,
authorized character count, relation pair count, model calls, elapsed time and
peak RSS without changing business semantics.

## 11. Implementation plan

1. Add red active-contract v9 tests proving the current GitHub and Jira failures.
2. Introduce the `ProjectionEvidenceWorkPlanner` facade, typed request/result,
   immutable plan and durable manifest payload.
3. Implement one shared `RepresentationIndex` seam with the three private
   representation adapters. Authority planning and Fragment compilation reuse
   the same boundary/offset implementation and index digest.
4. Replace the authority, Context and digest ownership in the current batch
   planner. Route every active `uses_fragment_catalog` contract through the new
   module, then run a pure presentation packer. Keep historical contract replay
   readable; do not silently downgrade.
5. Add every source/operation acceptance case from sections 6 and 7.
6. Amend ADR 0030 to distinguish complete representation input from exact
   Primary authority and to record schema-field incremental semantics.
7. Add shared SQLite/HANA contract tests for plan identity, stale guards and
   retry reconstruction; Cloud code implements the OSS protocol directly.
8. Open OSS and Cloud PRs, pin the exact OSS merge, deploy through the checked
   Cloud Foundry entrypoint, and run bounded post-watermark smokes for Markdown,
   Jira canonical record, and Teams message updates.
9. Verify online evaluation for the acceptance cohort. Do not rerun full source
   ingestion or modify historical Memory/lifecycle data as validation.

## 12. Test matrix

The minimum deterministic suite is:

- initial, added, text-edit, canonical-field-edit, metadata-only, location-only,
  access-only, removal-only, explicit reprocess, revalidation and exact retry;
- Markdown paragraph, list item, table, blockquote, code fence, raw HTML,
  inline-HTML paragraph, duplicate/moved structures, duplicate table rows,
  emoji/non-ASCII and edit at document end;
- canonical strings with JSON escapes/non-ASCII, null/add/remove, array/object
  field changes, nested Markdown/raw HTML and invalid registered types;
- new versus edited Jira comments/messages, Jira provider-object metadata-only
  changes against existing v1 base records, Confluence title-only change, and
  attachment/delete-only revisions;
- partial projection carried Jira/Teams revisions never regain Primary;
- Teams target-deleted message yields zero Primary when initially collected or
  exactly retried; when a prior live message exists it invalidates prior Evidence
  even under a partial projection, while ordinary missing message does not;
- partial projection carry-forward versus complete-snapshot removal proof,
  pending/rejected/approved removal Review, stale Review, multi-Support removal,
  last-Support retirement and same-run deferred blocker;
- managed concept through the real `session_summary` producer for Codex and
  Claude, plus a dormant `agent_concept` compatibility assertion;
- valid supplied image, invalid/oversized image and stored-but-unsupplied PDF;
- direct `plain-text` representation contract, even though no current built-in
  Source emits it;
- Jira changelog `attachment_event`/`operational_transition` continues through
  the existing deterministic quality gate instead of duplicating that policy;
- active `evidence-unit-set-v2` plus `projection-extraction-v9` selection, not a
  default marker that accidentally exercises v8;
- repeated planning/compilation produces byte-identical ranges, refs and digest;
- changing the inference capability hash changes Artifact plan/catalog identity
  and prevents cross-model batch reuse;
- every typed planning failure emits one content-safe durable runtime event with
  stable grouping identity; Online Evaluation classifies it without raw content,
  source reingestion, or Memory/lifecycle mutation;
- resolver rejects any Primary outside the authorized ranges;
- SQLite and HANA prove atomic manifest staging, exact reuse/mismatch rejection,
  source-activity/base stale guards, policy replacement, pending Review Support
  preservation, multi-Support removal, atomic rollback, Support/read-model
  invariants, and equivalent transaction/locking behavior;
- a future fake Source with `document_content + markdown-structural` passes the
  same extension contract without adding a source branch.

## 13. Non-goals

- no GitHub-only or Jira-only fix;
- no arbitrary recursive JSON diff;
- no persistent per-field lifecycle state;
- no LLM-based change/role decision;
- no whole-document or whole-record fallback after mapping failure;
- no top-k replacement for mandatory destructive lifecycle coverage;
- no increased timeout, concurrency, or batch fragmentation as the remedy;
- no redesign of relation conflict Review or exhaustive multi-window extraction;
- no source ingestion rerun, Source rebaseline, Memory mutation, Support rewrite,
  or lifecycle-history rewrite;
- no promise that genuine first imports or full rewrites avoid large relation work.

## 14. Existing design records changed by this implementation

This implementation supersedes the prior ADR 0030 assumption that every
compiler-backed `canonical-record` keeps whole-Observation **Primary authority**
until compilation, and it refines Markdown authority from whole changed Observation
to changed complete structure. The replacement rules are:

> A canonical record keeps complete read/parse access, while incremental Primary
> authority is limited to changed registered claim-bearing fields.

> Range-addressable text grants Primary only to the smallest safe complete
> structures that intersect proven changed target ranges.

The implementation updates ADR 0030's runtime flow, Primary eligibility,
representation-owned segmentation, source matrix, catalog identity and retry
sections, plus
[`source-agnostic-memory-extraction.md`](source-agnostic-memory-extraction.md) so
they do not retain the old whole-record-authority wording. It must preserve the
existing decisions about exact raw JSON coordinates, registered schema
ownership, nested representation parsing, typed failure, Fragment selection,
Evidence Units and lifecycle authority.

The relation-conflict and large-matrix recovery work in
[`large-document-reconciliation-recovery.md`](large-document-reconciliation-recovery.md)
is related but separate. This document fixes which content may become a new
candidate; it does not weaken or replace mandatory relation reconciliation for
candidates that remain.

## 15. Completion criteria

The fix is complete only when:

- one shared planner covers every applicable source-backed compiler-extraction
  row in section 7; Direct User and consolidated read models remain intentionally
  outside it;
- a structure disjoint from all changed ranges cannot become Primary in ordinary
  incremental fragment-catalog work;
- complete canonical-record parsing remains available without authorizing
  unchanged fields;
- removal and metadata-only changes produce no false new candidates while their
  non-extraction responsibilities still run;
- retries preserve exact base/target authority and catalog identity;
- v8 history remains readable without becoming an active-policy fallback;
- OSS/SQLite and Cloud/HANA contract behavior matches;
- the canonical ADR, both PRs, CF deployment evidence and bounded live smokes
  are recorded against issue #390.

The code and read-only deployment smoke may merge before the separately
authorized post-watermark Source canary. Issue #390 remains open until the
Markdown/Jira/Teams incremental canary and resulting Online Evaluation cohort
are recorded; this does not authorize an ingestion rerun or historical data
rewrite.

This is a bounded design: one facade, three representation strategies, existing
Source Projection and Evidence/lifecycle contracts, and no new business state.
