# Source-Agnostic Memory Extraction

This document expands the runtime design accepted by
[ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md). MemForge
keeps provider identity and structure at the Source Projection seam,
representation parsing inside the Evidence Fragment Compiler, semantic Evidence
selection in the extraction model, and lifecycle authority in application code.

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
  -> exact batch-local authorized ranges + bounded Context
  -> representation-aware Evidence Fragment Compiler
  -> immutable candidate catalog + display-only Context
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

### Evidence Fragment Compiler

The compiler has one external interface equivalent to:

```python
compile_fragments(
    revision: SourceObservationRevision,
    candidate_ranges: tuple[EvidenceCandidateRange, ...],
) -> EvidenceFragmentCatalog
```

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

For one persistent Markdown or HTML Observation, a provider delta may currently
identify the whole Observation rather than exact changed paragraphs. In that
case the batch's authorized range is necessarily broader. That is a projection
granularity limitation, not a reason to ask the role layer or the LLM to invent
finer authority. A future exact `FragmentMapping` may narrow the work without
changing this contract.

## Bounded Context and Required Selection

The planner deterministically finds bounded current Context through structural
ownership, immediate sequence neighbors, root information, and Source
relations. Budgets bound the material actually presented to the model.

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

One revalidation operation builds each current Revision's representation index
once. Every affected Evidence Unit then derives a bounded claim-specific
workset from that shared index. A prior stable-Fragment Anchor first requires
the projection's provider mapping across Revisions. Selection then prefers
persisted raw or presentation digest, exact prior presentation, exact current
claim text for Primary, or current-anchor overlap, and uses a bounded
deterministic lexical shortlist only when a coarse whole-Observation anchor
would otherwise expose a large Revision. Provider mapping proves
correspondence; durable text Evidence still resolves to an exact current range.
Candidate retrieval grants no Evidence role and does not replace semantic
validation.

The model selects transient `fNNNNNN` refs from that workset. A supported result
must select one Primary and one candidate for every Required selector. The
application validates full coverage and resolves the selected exact Fragments;
there is no model-returned Evidence text or quote-rematching step. This path is
shared by Markdown, plain text, canonical records, and current eligible
Artifacts and never branches on Source type. Required coverage has no separate
item-count cap: the model output budget scales with the complete selector set,
and an unrepresentable result becomes a typed capacity limitation instead of a
partial response.

Because the static response schema cannot enumerate one transient workset's
exact refs, a schema-valid but unknown, duplicate, or incomplete selection gets
one application-owned correction call with the same workset and exact allowed
refs. A valid correction continues normally. Exhaustion produces typed
`support_revalidation_failed`, preserves existing Support, creates no Review,
and stops the surrounding document retry from replaying extraction and relation
work. This is one provider-neutral execution rule after representation-specific
candidate construction, so it applies identically to Markdown, plain text,
canonical records, and eligible Artifacts.

Review is the last-resort semantic/authority outcome: `supported=false`, no
presentable current Evidence, or candidates that remain indistinguishable after
their representation type and bounded structural context are included. Model
transport/schema failure retains bounded runtime retry. Missing, unknown, or
duplicate refs receive one workset-local correction; exhausted correction is a
typed execution failure that cannot replay the surrounding document.
Unsupported representation, compiler-contract failure, and
capacity exhaustion are non-retryable operational limitations. Neither creates
a human Review. Runtime failures use `support_revalidation_failed`; typed
operational outcomes use
`support_revalidation_unsupported_representation`,
`support_revalidation_compiler_failure`, or
`support_revalidation_capacity_exceeded`, making the failure visible to Online
Evaluation without mutating lifecycle state. Successful stats include work-item
count, shared Revision-index count, prompt characters, actual model-call count,
and automatic rebind count.

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
  -> complete semantic CandidateLedger
  -> incumbent reconciliation
  -> atomic Lifecycle Plan
```

The durability gate rejects provenance bookkeeping such as attachment uploads
and routing-field history. A claim extracted from the actual supplied content
of an Artifact is different and may pass with revision-pinned Evidence. The
gate is shared and never switches on provider type.

CandidateLedger owns only within-revision uniqueness. It receives candidate
identity, Memory type, canonical content, and resolved Evidence identity. It
does not receive provider payloads and never rewrites candidate content. Its
only actions remain `KEEP` and `DROP_REDUNDANT -> canonical_index`.

The semantic ledger must return exactly one valid decision for every candidate.
Incomplete or over-budget coverage fails closed: no candidate is written and no
destructive incumbent lifecycle action is authorized. Exact duplicates are
collapsed before semantic budgets are applied.

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

## Open Optimization Question: Cross-Document Checks

Large source documents can create many new Memories. Cross-document relation
discovery still needs separate bounded ranking and response-budget decisions.
Those optimizations must not cap the complete candidate catalog, change Primary
eligibility, weaken complete incumbent coverage, or turn batching into a
lifecycle state.

## Non-Goals

- trusting model-returned Evidence text;
- quote rematching or whole-Block fallback;
- model-chosen Observation, Revision, offset, access, or lifecycle authority;
- source-specific relation-to-role matrices;
- persistent Fragment identity or Fragment lifecycle state;
- generic Evidence Boolean expressions;
- dynamic schemas containing every transient Fragment ID;
- ingestion replay as a verification shortcut.
