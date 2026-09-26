# Source-Agnostic Memory Extraction

Scope: current extraction and Evidence-selection mechanics. The complete runtime
entry is [Source sync to Memory](source-sync-to-memory.md); its L3/L4 changes
are implemented under [ADR 0034](../adr/0034-unify-incremental-support-and-claim-assessment.md).
This document does not define a second lifecycle or conflict-discovery pipeline.


This document expands the runtime design accepted by
[ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md). MemForge
keeps provider identity and structure at the Source Projection seam,
representation parsing inside the Representation Compiler, semantic Evidence
selection in the extraction model, and lifecycle authority in application code.
The compiler and ReadingGroup index are one private `RepresentationCompiler`
module; parser-specific ASTs and provider position types do not escape it.
Inference transport and reusable context layout are defined separately by
[Semantic judgment execution](semantic-judgment-execution.md), so changing an
eligible judgment executor cannot change Evidence authority or document
segmentation.

The design is source-agnostic without pretending every source has one format.
Jira comments, Teams messages, Markdown sections, HTML structures, canonical
records, supplied Artifacts, and managed agent-session projections all enter the
same extraction contract after their source and representation adapters have
done their own deterministic work.

## Runtime Flow

```text
provider payload
  -> SourceProjectionAdapter
  -> complete current Source Projection + Revision Delta
  -> committed base + staged target ProjectionEvidenceWorkPlanner
  -> exact authorized ranges + complete representation index
  -> RepresentationCompiler: exact Fragments + ReadingGroups
  -> RevisionInputPlanner expands reading groups and compares delta/current-full cost
  -> immutable request catalog + display-only Context
  -> LLM returns Memory content + primary_ref + required_refs
  -> deterministic Evidence Resolver
  -> one revision-pinned Evidence Unit
  -> candidate selection and relation-first reconciliation
  -> one atomic Lifecycle Plan
```

The complete Source Projection may contain the whole current Jira issue,
conversation, document, or session. Ordinary extraction does not make that
whole projection claim-authoritative. The planner authorizes exact work for the
current batch and includes only bounded current Context needed to interpret it.

## Module Responsibilities

### SourceProjectionAdapter

The adapter owns provider facts:

- stable Source Unit and Observation identity;
- immutable Observation Revisions;
- edit, delete, ordering, containment, reply, and reference relations;
- Revision Delta and provider coverage;
- representation-profile assignment for each new Revision.

It does not assign final Evidence roles. A `precedes`, `replies_to`,
`contained_by`, or `references` relation may help the planner find bounded
Context, but the relation alone never grants Primary or Required authority.

### EvidenceRepresentationProfile

The profile declares how one immutable Revision exposes exact Evidence. It is
selected by representation rather than Configured Source type. Markdown, HTML,
canonical records, plain text, and whole Artifacts use their registered,
versioned representation contracts. A representation adapter may split or
narrow exact structure, but it cannot widen the planner's authorized ranges.

### Representation Compiler

The compiler parses one immutable Revision once and exposes both exact Evidence
Fragments and the ReadingGroups needed to interpret them. Its private interface
is equivalent to:

```python
compile_representation(
    revision: SourceObservationRevision,
    candidate_ranges: tuple[EvidenceCandidateRange, ...],
) -> CompiledRepresentation | TypedRepresentationFailure
```

`CompiledRepresentation` contains one exact coordinate map, structural
manifest, Fragment catalog and reading index. Markdown uses `markdown-it-py`
plus a private raw-coordinate adapter; raw HTML and canonical JSON retain small
private exact scanners because reviewed DOM/source-map packages do not satisfy
the full coordinate and identity contract. All emitted ranges are verified
against the immutable raw slice. Parser objects remain internal and no durable
Fragment or ReadingGroup entity is introduced.

Each candidate range carries one exact current-revision Anchor and one transient
Boolean:

```text
primary_eligible = true
  The current work authorizes a claim to originate from this range.

primary_eligible = false
  The range is bounded Context. The model may select it only as Required.
```

Every selectable Fragment may be selected as Required. Only a Fragment with
`primary_eligible=true` may be selected as Primary. Material that cannot become
exact supporting Evidence remains outside the catalog as display-only Context.
The compiler copies the Boolean to contained Fragments and never infers it from
the text or syntax.

This Boolean is transient catalog policy, not a persistent Source, Fragment, or
lifecycle state. Durable Evidence stores only the resolved role, exact Revision
and Anchor, content or Artifact digest, and access scope.

### RevisionInputPlanner

The planner plans Claim Extraction input. It receives an extraction task with
its already-authorized current ranges, asks the representation-owned reading
index to expand the selected structures, then builds complete delta and
current-full request candidates when a valid baseline permits both. The
extraction request policy materializes actual requests and forecasts
prompt/schema tokens, images, output reservation and repeated request data. A
safe image-free lower bound may prove full cannot beat an already materialized
delta; otherwise full is materialized before comparison. The planner chooses the
lower forecast token cost; delta wins an exact tie. Request and image
counts/bytes remain diagnostics. It uses no source-type branch or percentage
threshold. A normal-update L1 current-full candidate must fit its complete
reading scope in one request. Initial extraction and L1 delta may still
partition authorized Primary work with local reading context.

The result records mode, exact catalog, reading groups, selection reason,
estimated complete cost and materialized transport. These values are derivation
input, not persistent Source, Evidence, Support or lifecycle state. Reading
expansion adds Context only: current-full preserves the extraction task's exact
Primary bits, and a Fragment added for reading is never Primary-eligible.

Support Assessment does not use this planner. It judges fixed claims, so it has
no Primary authority to plan and no request mode to choose. Exact Evidence
correspondence routes each whole Support: when every Evidence part is exactly
unchanged and the revision has no changed content, the program rebinds the
Support; when every part is exactly unchanged and the revision has changed
content, removed content included, Change Impact judges the claim against the
ChangeBundle of changed ReadingGroups and removed old text, an `UNAFFECTED`
Support is rebound by the program, and an `AFFECTED` Support or a Change Impact
execution failure is read like the rest; when an Evidence part lies in an
Observation whose presence the partial Projection cannot prove, such as a
comment the provider did not return, the Support is kept as
`UNRESOLVED(partial_coverage)` without a model call; every other Support is read
in the
[ordered current-revision reading](../adr/0034-unify-incremental-support-and-claim-assessment.md#ordered-current-revision-reading).
That reading covers the complete current revision in one fixed order. Its first
part holds the changed ReadingGroups, the removed text and the ReadingGroups of
the Support's own prior Evidence; each work item may exit once its first part
has been read. A Support without a usable validation baseline reads the whole
current revision as its first part.

The delta/current-full comparison above is the implemented `revision-input-v6`
behavior. Target (Cloud #505): Claim Extraction makes no cost comparison. On an
update, it reads only the changed structures, with their ReadingGroups as
context; Primary is already limited to the changed authorized work. A first
import streams per ReadingGroup through the LLM batch runner of
[ADR 0036](../adr/0036-separate-semantic-work-from-inference-executors.md), so no
extraction read has to fit one request.

## Deterministic Primary Eligibility

The application answers only one static authority question before extraction:

> May a new or revalidated claim originate from this exact range in this work?

The answer depends on the work kind, not on an LLM interpretation of the text:

| Work kind | `primary_eligible=true` ranges |
| --- | --- |
| ordinary incremental extraction | exact changed or added ranges in the current batch |
| initial extraction | added ranges owned by the current batch, not another batch |
| explicit reprocess | current ranges explicitly selected by the authorized operation |
| Evidence revalidation | current or rebound incumbent claim ranges and affected supporting ranges authorized for the revalidation |
| managed agent knowledge | exact user-authorized event ranges projected into current Evidence |
| supplied Artifact extraction | current inference-eligible Artifact actually supplied to the model |

The name is deliberately not `delta`: initial extraction, explicit reprocess,
revalidation, and managed capture can authorize claim work without an ordinary
changed/added delta. The planner retains one internal concept of authorized work
instead of adding a separate domain state for every work kind.

A provider delta may identify a whole mutable Observation. For active
compiler-backed work, the representation-owned planner compares complete
structures or schema fields before granting incremental Primary eligibility;
a coarse provider delta does not automatically authorize the whole old body.
See [representation-scoped incremental authority](representation-scoped-incremental-primary-authority.md)
for the implemented algorithm and [ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md)
for the canonical boundary. Whole-record parsing permission is not Primary
permission for every decoded field.

## Bounded Context and Required Selection

The planner deterministically finds bounded current Context through the
representation's operation-local reading index. Markdown and exact raw HTML use
heading scopes plus the first complete paragraph immediately under the heading,
and complete list containers plus an immediate prose lead-in. Documents without
headings and `plain-text` do not receive a guessed semantic section. Registered
canonical records add only contextual fields declared by the schema; a registered
nested Markdown string reuses the same section/list rules through its decoded-to-raw
coordinate map. Teams message content therefore follows its canonical schema and
nested text contract. Agent
Session `session_summary` content follows `markdown-structural`; neither path asks
the selector to infer structure from arbitrary JSON. Source relations may supply
additional exact Context under their existing contract. Budgets bound the
material actually presented to the model.

Tables and binary Artifacts retain their existing atomic representation and get
no additional reading group. The reading index does not budget or batch requests;
the revision request policy enforces actual route capacity after expansion.

Reading expansion starts from the caller's selected Fragments and runs once;
newly added Context does not recursively trigger unrelated groups. A complete
unordered list is read together, including nested items and a proven lead-in,
but each top-level item keeps its own exact Anchor and Evidence role. Whole-list
reading therefore does not turn the list into one Evidence Unit or authorize
unchanged peer items as new Primary Evidence.

The planner does not decide which Context is semantically necessary. Every
exact, current, access-compatible Context Fragment admitted to the candidate
catalog has `primary_eligible=false`. The extraction model may select such a
Fragment in `required_refs` when the claim would otherwise be unsupported,
ambiguous, or change meaning. If the model does not select it, it remains
Context and does not become part of the immutable Evidence Unit.

This avoids two unsafe or brittle alternatives:

- a generic relation-to-role matrix, where an ordering relation such as
  `precedes` accidentally becomes Required authority;
- unrestricted model authority, where unchanged Context may become the Primary
  for a newly extracted claim.

Display-only Context is material shown for interpretation but not offered as a
selectable Fragment. Examples include authorized structural labels, outlines,
glossary hints, or an explicitly non-Evidence summary for an unsupplied Artifact.
An inaccessible range is excluded before prompt construction; an unsupported or
inconsistent Evidence Representation Profile fails closed rather than becoming
display-only input. The model never returns Context references.

## Catalog and Model Contract

One catalog belongs to one exact Source, Source Unit Revision, access context,
batch workset, compiler contract, and presentation. It contains only exact
current-revision Fragments admitted for that batch; it is not the complete
Source Unit contents.

Conceptually, the model sees:

```json
{
  "primary_candidates": [
    {
      "ref": "p000012",
      "kind": "text",
      "type": "paragraph",
      "text": "Approved. Apply this to production."
    }
  ],
  "required_only_candidates": [
    {
      "ref": "r000004",
      "kind": "text",
      "type": "paragraph",
      "text": "Set the production timeout to 60 seconds."
    }
  ]
}
```

The model returns generated canonical Memory text and transient selectors:

```json
{
  "content": "Production timeout should be 60 seconds.",
  "memory_type": "decision",
  "confidence": 0.92,
  "entity_refs": [],
  "valid_from": null,
  "valid_until": null,
  "primary_ref": "p000012",
  "required_refs": ["r000004"]
}
```

The model does not return Evidence text, Observation or Revision IDs, offsets,
hashes, representation profiles, Context refs, or lifecycle actions. Typed
`p...` and `r...` refs remain catalog-local and transient. They encode only
model-facing capability: `primary_ref` accepts `p...`; `required_refs` accepts
both. They are not durable role-prefixed identity, and no dynamic enum schema
is required.

If no durable claim is directly stated in `primary_candidates`, the model must
return `{"memories": []}` even when Required-only historical Context contains
strong durable knowledge. Required-only Context may clarify a current claim;
it cannot authorize re-extraction of an old one.

The Resolver fails closed unless all of these hold:

- exactly one `primary_ref` resolves in this catalog;
- the Primary selector uses the `p...` namespace and resolves to a
  Primary-capable Fragment;
- every Required ref resolves in the same catalog;
- the LLM admission boundary removes redundant Required refs exactly once,
  including any repeat of the singular Primary, before canonical catalog
  ordering; direct Resolver callers remain subject to duplicate rejection;
- every selected Fragment is current, exact, access-compatible, and within the
  supplied Artifact and batch budgets;
- the catalog, policy contract, and stale guards match the work being applied.

The weaker rule "some selected Fragment intersects the current work" is not
sufficient. It would permit an unchanged old claim to become Primary while an
unrelated changed Fragment is added as Required merely to pass admission.

## Incremental, Initial, and Large Work

For an ordinary provider-native multi-Observation update, added Observations
and exact current structures or registered fields proven changed against the
committed base produce the authorized work. The model receives their compiled
Fragments plus bounded Context, not the complete Jira issue or conversation.

Initial extraction may authorize every added Observation, but batching remains
a transport and computation detail. Only exact ranges owned by the current batch
are Primary-eligible; an adjacent Observation assigned to another batch cannot
cross that authority seam.

Large `markdown-structural` and `plain-text` Observations are indexed into
complete representation-owned structures before packing. Each authorized
structure has one Primary batch owner; there is no overlapping Primary window.
Primary eligibility remains local to each exact range, and Context cannot widen
it to the whole Observation.

For a valid base/target pair, `RevisionInputPlanner` forecasts complete delta and
current-full extraction transports and chooses the lower forecast token cost,
with delta winning ties. Delta includes the complete removed/replaced structural
history emitted by the delta; it does not semantically prune old material before
extraction. Current-full reads the complete eligible effective current Source
Projection and omits non-current history. Partial Projection carry-forward
remains current, and full does not turn an uncovered upstream omission into a
deletion. Full reading does not promote Context to Primary. Normal-update L1 full
reading must fit one request. A named extraction baseline that is missing or does
not match fails as a technical contract violation; ordinary incremental L1 never
uses that failure as initial-import authority.

L3 Support Assessment uses the ordered current-revision reading instead of this
comparison. A Support without a recorded validation baseline, or whose named
baseline snapshot is missing or inconsistent, reads the whole current revision
as its first part; an unusable named snapshot is logged as a diagnostic, not
treated as a failure.

Target (Cloud #505): see the target note in [RevisionInputPlanner](#revisioninputplanner)
and [ADR 0034, Ordered current-revision reading](../adr/0034-unify-incremental-support-and-claim-assessment.md#ordered-current-revision-reading).

For compiler-backed v9, `canonical-record` and whole-Artifact coordinate
profiles are different representation contracts, not Source-type exceptions.
The canonical planner first resolves schema-owned fields, compares their stable
business projections, and maps changed nested Markdown/plain-text structures
back to raw JSON. Only those exact current ranges are Primary-capable at
compilation. Artifacts remain atomic. An unregistered or unmappable profile
returns a typed planning failure before the LLM; it never falls back to whole
Observation authority. Legacy projection extraction continues to
character-segment its direct batch-Markdown prompt.

Neither v9 profile is raw character-sliced to satisfy a planner budget. The
current normal-extraction catalog remains one-call bounded: an over-limit
compiled result fails with typed `catalog_too_large` and no fallback. Generic
multi-window extraction is deferred to
[issue 365](https://github.com/shno-labs/mem-forge/issues/365).

A deletion-only delta grants no new-candidate authority. Absence, Support
removal, and retirement remain reconciliation concerns.

## Artifact Rules

An Artifact may enter the selectable catalog only when its current bytes are
inference-eligible and actually supplied to the configured model. A filename,
upload event, parent text, OCR guess, or stored metadata does not substitute for
Artifact content.

A supplied Artifact can be Primary-eligible when the current work authorizes a
visual claim to originate from it. A supplied bounded Context Artifact may be
selected as Required but not Primary. An unsupplied Artifact may contribute an
explicitly non-Evidence display summary but cannot become Support; an
inaccessible Artifact is excluded.

Primary and Required media share the same byte and concurrency budgets. Adapter
implementations must preserve this behavior across SQLite and HANA.

## Evidence Unit and Lifecycle

The selected Primary plus every selected Required Fragment resolve atomically to
one immutable Evidence Unit. They are jointly necessary; there is no AND/OR or
`N_OF_M` evidence language. Unselected Context is not a member of the Unit and
does not independently invalidate it.

Role selection does not authorize a lifecycle action. Relation-first
reconciliation, complete incumbent coverage, source authority, Reviews, and
stale guards remain the sole owners of update, supersede, Support removal, and
retirement.

Revalidation uses the same candidate contract with a different authorized
workset. An unchanged incumbent Primary may remain Primary when only one
Required part changed, provided the revalidation work explicitly includes the
current or rebound incumbent range. Therefore the invariant is
Primary-from-authorized-work, not Primary-from-delta.

L3 performs one fixed-claim Support assessment and complete current Evidence
reconstruction, reading the complete current revision in the ordered
current-revision reading. Required membership can
split, merge, grow or shrink; there is no selector per old Required part. One
local correction remains available for unknown current refs. Unresolved support
and exhausted correction cannot become independent ADD or a whole-document
semantic retry. See [ADR 0034](../adr/0034-unify-incremental-support-and-claim-assessment.md)
for orchestration and [ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md)
for immutable representation and storage invariants.

Retries must reconstruct the same workset, candidate catalog, policy contract,
access context, binary inference capability, and digest. A change to any of
these inputs changes v9 Source Derivation and batch identity, so completed output
from the old authority or model-input contract cannot be silently reused.

Lifecycle commit validation is scoped to causal inputs. Unrelated structurally
valid stale Support from another Source Unit cannot authorize a destructive
decision, but it does not block a support-preserving write such as pending
Review creation. A Plan that consumes that edge is Deferred only when its owner
belongs to the same Source run; malformed, self-stale, or authority-changed work
is Rejected. The orchestrator retries Deferred work through the prepared
commit-only interface for at most three progress-making rounds after normal
per-Unit updates and authoritative tombstones. Only Support topology changes
owned by the exact typed same-run blockers may be rematerialized. No model call,
dependency graph, or durable retry state is part of convergence.

MemoryEngine presents this behavior through one prepare-and-commit interface
and one retry-deferred interface. Deferred work crosses the seam as an opaque
handle plus content-free blocking Source Unit ids. The Source orchestrator supplies
only the current run's eligible Unit/tombstone ids and owns the three-round
budget; topology snapshots, owner authorization, semantic authority guards,
attempt accounting, Plan rematerialization, and idempotency stay private to
MemoryEngine.

## Candidate Durability and Uniqueness

All extraction batches for one Source Unit Revision are aggregated before any
Memory write. The shared pipeline then applies separate policies:

```text
all resolved batch candidates
  -> deterministic durability gate
  -> deterministic exact-duplicate collapse
  -> candidate admission
  -> incumbent reconciliation
  -> atomic Lifecycle Plan
```

The durability gate rejects provenance bookkeeping such as attachment uploads
and routing-field history. A claim extracted from the actual supplied content
of an Artifact is different and may pass with revision-pinned Evidence. The
gate is shared and never switches on provider type.

Candidate admission owns complete Evidence support and within-revision
uniqueness. It receives each candidate's claim, Memory type, validity and the
exact text of its selected Primary and Required Evidence, plus every claim of
the round as shared context. It does not receive provider payloads and never
rewrites candidate content. Each candidate is `ADMITTED` or `REJECTED` with
reason `evidence_incomplete` or `low_value`, and may name same-round
duplicates, which the program merges among admitted candidates.

Admission must return exactly one valid decision for every candidate. Incomplete
or over-budget coverage fails closed: no candidate is written, the Source Unit
revision is not committed and the next sync retries it. Exact duplicates are
collapsed before any model call.

## Lifecycle Module Ownership

The shared lifecycle ownership remains unchanged:

```text
MemoryEngine owns extraction and reconciliation decisions.
GeneSyncOrchestrator owns bounded same-run commit convergence.
MemoryStore owns relational, search-index, rollback, and lifecycle side effects.
ReviewService owns human-gated approval and rejection.
```

New source types and representation adapters must not bypass these Modules with
direct Memory or Support writes.

## Support Model

Evidence Unit Support is the only Support model. Each active Support Assertion
names one complete Evidence Unit: the claim, its exact Primary and Required
parts pinned to stable Observation Revisions, and the access context. Lifecycle
Plans add and remove Support only by Evidence Unit identity, and a Support set
hash covers the complete active Unit set of one Memory.

The workspace records this model in its Support scope marker. Storage refuses to
open a workspace whose marker names any other scope, and an older workspace that
still holds reference-scoped Support rows refuses to start instead of being
converted in place. This rule is representation- and Source-neutral: all
providers reach it through the same stable Observation and current-Revision
identities.

## Source-Type Extensibility

The authority rule does not branch on Source type:

- Jira comments and Teams or future Slack messages use provider-native
  Observation deltas and bounded conversation Context.
- Markdown, GitHub, Confluence, local files, and agent-session documents use
  their declared representation profile; raw CommonMark HTML remains a private
  Markdown adapter concern.
- Canonical records expose schema-owned fields and ranges through the canonical
  record representation adapter.
- Codex and Claude Code managed-event capture keeps its explicit user-authority
  validator before projecting ordinary current Evidence.
- Binary Artifacts keep the supplied-byte eligibility rule.

Adding a Source type requires a SourceProjectionAdapter and registered
representation profile only when those things genuinely vary. It does not add a
source-specific extraction strategy, compiler interface, role matrix, or
lifecycle path.

## Verification Contract

Tests should exercise the external extraction-and-resolution interface rather
than private planner state. At minimum they prove:

1. ordinary current work can supply one Primary;
2. a current approval may select an older proposal as Required;
3. unchanged Context cannot become Primary, even when a Source relation exists;
4. ordering, neighbor, and root Context do not gain authority by themselves;
5. multiple changed ranges still produce exactly one Primary per atomic
   claim and canonical Required ordering;
6. initial extraction remains isolated by batch;
7. explicit reprocess and revalidation authorize their current work without an
   ordinary delta;
8. deletion-only work emits no new extraction catalog;
9. v9 range-addressable Observations preserve range-local authority, canonical
   records expose only changed registered fields, Artifacts remain atomic only
   when selectable, unsupported profiles fail closed, and legacy prompt
   segmentation remains bounded;
10. supplied and unsupplied Artifacts remain distinguishable;
11. repeated compilation of the same inputs produces the same catalog and
    policy digest;
12. a Required change invalidates the complete Evidence Unit while unselected
    Context does not;
13. normal extraction, replay, and startup recovery resolve one registered
    active extraction-contract descriptor from the durable Support scope, so a
    future compiler-backed contract is promoted without version-specific caller
    branches;
14. inactive-contract pending/retryable derivations receive the typed
    `CONTRACT_SUPERSEDED` disposition, while completed inactive-contract output
    remains immutable audit history;
15. recovery classifies exact-manifest resume versus current-policy replacement
    before lifecycle commit; the derivation that produced extraction output is
    the same derivation marked applied, and a policy-stale attempt is explicitly
    superseded rather than silently receiving the replacement result;
16. compiler-backed range planning packs complete representation-owned
    structural units, assigns each unit one Primary batch owner, and returns a
    typed capacity outcome when one protected unit exceeds the presentation
    budget; it never slices or widens authority to make a batch fit.

For a persisted incident, bounded verification should rehydrate the stored
Source Projection and derivation batch, compile the old and proposed catalogs,
and run any retained structured response through the Resolver. It does not need
to rerun source ingestion or rewrite Memory or lifecycle history.

## Audit Expectations

Every extraction should record content-free diagnostics sufficient to separate
planning, model, admission, and lifecycle failures:

```text
source derivation and batch identity
extraction and authority-policy contract identity
catalog digest and candidate counts
structured LLM call outcome
attempted Primary eligibility
selected Primary/Required counts
salted selection fingerprint
typed admission rejection reason
candidate-ledger and reconciliation outcome
lifecycle or Review outcome
support-revalidation work items, shared Revision indexes, prompt characters,
automatic rebinds, and typed execution failure when applicable
```

Runtime events do not persist Fragment text or transient Fragment IDs. The
selection fingerprint distinguishes the same generated Memory content paired
with different selectors without exposing Evidence.

## Cross-document checks

Identity matching before creation and bounded asynchronous relation discovery
after commit are separate existing contracts. Their pipeline, scenarios and
accepted temporary conflict window are described in
[Source sync to Memory](source-sync-to-memory.md); durable discovery semantics
remain in [ADR 0009](../adr/0009-bound-cross-document-relation-discovery.md).
They must not cap complete same-Unit incumbent coverage or widen Primary authority.

## Non-Goals

- trusting model-returned Evidence text;
- quote rematching or whole-Block fallback;
- model-chosen Observation, Revision, offset, access, or lifecycle authority;
- source-specific relation-to-role matrices;
- persistent Fragment identity or Fragment lifecycle state;
- generic Evidence Boolean expressions;
- dynamic schemas containing every transient Fragment ID;
- ingestion replay as a verification shortcut.
