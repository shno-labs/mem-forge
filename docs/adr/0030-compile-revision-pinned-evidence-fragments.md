# Compile revision-pinned Evidence Fragments

Status: Accepted (2026-08-27)

MemForge will replace provider-returned evidence text, single coarse Block
selection, quote matching, and whole-Block fallback with application-owned
Evidence Fragments. The model selects one Primary Fragment and zero or more
Required Fragments from one immutable extraction catalog; application code
resolves every selection to exact current-revision Evidence and binds the
result as one indivisible Evidence Unit. This preserves revision-pinned
authority while removing format-sensitive quote copying and preventing a
partially supported compound claim from entering lifecycle state.

This decision supersedes the selection and fallback portions of
[ADR 0007](0007-bind-extracted-evidence-to-the-current-projection.md). It keeps
ADR 0007's revision ownership, Source Projection, stale-guard, atomic lifecycle,
and Artifact authority decisions. It also amends
[ADR 0010](0010-keep-support-provenance-projection-complete.md) so one Support
Assertion attaches a complete Evidence Unit rather than one Evidence Reference.

## Runtime flow

```text
Current Source Projection
  -> owned Source Observation Revisions and bounded Context
  -> representation-aware Evidence Fragment Compiler
  -> immutable extraction catalog with transient Fragment references
  -> model returns Memory + primary_ref + required_refs
  -> Evidence Resolver validates and materializes exact revision-pinned references
  -> one complete Evidence Unit
  -> one Support Assertion
  -> relation-first reconciliation and one atomic Lifecycle Plan
```

The model never returns authoritative Evidence text, source offsets,
Observation identities, durable fragment identities, or lifecycle actions.
Structured-output validity proves only response shape. Application code owns
Evidence authority and immediately rejects an unknown, stale, out-of-scope,
cross-catalog, mixed-access, or unresolvable selection.

## Evidence Fragment catalogs

An Evidence Fragment is an application-owned structural region inside one
current Source Observation Revision. Each offered Fragment carries an exact
revision coordinate and content hash. Its short model-facing reference is valid
only inside the exact immutable catalog sent to that model call and is absent
from completed derivation and durable lifecycle records.

The compiler varies by representation, not by Configured Source type. Its
private adapters initially cover Markdown structure, HTML structure, plain
text, atomic conversational records, and whole binary Artifacts. Future PDF
page text or other formats enter through the same private representation seam.
GitHub, Jira, Confluence, Teams, Agent Session, future Slack, and other provider
adapters continue to own provider identity, Source Unit and Observation
topology, edit/delete semantics, relations, scope, and coverage. Evidence and
Lifecycle code never branch on `source_type`.

Text Fragments use exact half-open ranges in the immutable Observation Revision.
HTML list items, table rows, blockquotes, Markdown paragraphs, list items,
table rows, and code blocks may therefore be independently selectable while
mapping back to exact source characters. A whole Observation is selectable
only when its versioned representation contract explicitly declares that
Observation atomic; it is not a recovery fallback for failed localization.

Binary Artifact selection remains a distinct schema variant. The offered
reference resolves to the Artifact Observation's whole-observation Anchor and
exact revision metadata and bytes. Filename, upload event, parent body, URL,
OCR guess, or Artifact summary never substitutes for inspected Artifact
content.

## Evidence roles

Every source-backed Evidence Unit contains exactly one Primary Evidence
Reference, zero or more Required Evidence References, and zero or more Context
Evidence References.

- **Primary** directly states the claim and is the authority from which the
  claim may be extracted. A text Primary resolves from `primary_ref`; a visual
  claim may select a supplied Artifact as Primary.
- **Required** is necessary for the claim to stand or retain its meaning. The
  model may promote only a reference from the bounded dependency/context input
  of the current work. Merely helpful material is not Required.
- **Context** assists interpretation and resource inspection but does not
  support the claim or independently trigger invalidation. Context is selected
  by application-owned planning; the model does not return arbitrary Context
  references.

Primary and Required are jointly necessary evidence for one claim. This is one
fixed domain invariant, not a configurable Boolean expression language. The
design adds no nested evidence expressions, `N_OF_M` policy, fragment lifecycle
state, or general-purpose Support rules. If one candidate appears to need
multiple independently claim-bearing Primary references, extraction normally
splits it into atomic Memories instead of widening the Evidence model.

## Evidence Unit and Support

The existing Evidence Unit is deepened as the claim-level aggregate. Its
identity includes the target Source Unit Revision, claim content hash, complete
resolved Primary/Required part-set digest, access context, and compiler
contract. Each contained Evidence Reference retains its role and exact
revision-pinned Source Anchor.

A Memory Support Assertion points to the complete Evidence Unit. It never
points independently to one contained Primary or Required reference. An
Evidence Unit supports its claim only while its Primary and every Required
reference are current and valid. Context currentness affects only the related
context projection.

A Memory may have multiple independent Support Assertions from access-compatible
Evidence Units. Removing or invalidating one unit preserves the Memory while
another complete unit remains. Retirement occurs only after authoritative
removal of the last complete Support. Cross-source units remain independent;
they are not combined into one cross-source conjunction.

The initial contract permits one Evidence Unit to reference only one Configured
Source, one Source Unit Revision, and one compatible access context. A model
cannot return Fragment references from another catalog, Source Unit, Source, or
visibility scope to widen reconciliation authority. Cross-Unit claim
dependencies require a separate future lifecycle decision rather than a hidden
exception in extraction.

## Revision and lifecycle semantics

Fragment references never survive their catalog and are never followed across
revisions. A new Source Observation or Source Unit Revision produces a fresh
catalog. Durable Evidence keeps only resolved Observation Revision identities,
Anchors, exact source-derived text or Artifact metadata, roles, and part-set
hashes.

- **Equivalent NOOP** revalidates the complete current Evidence Unit and
  atomically replaces the old source-scoped Support with the new revision-pinned
  unit. It never carries forward only the still-valid members of an incomplete
  Primary/Required set.
- **UPDATE** requires a complete current Evidence Unit plus relation-first proof
  that the challenger is the same Memory identity, preserves every incumbent
  truth, and is the complete canonical current claim.
- **SUPERSEDE** requires an explicitly identified replacement with complete
  current Evidence and source-local destructive authority. Fragment selection
  itself never authorizes supersession.
- **Support removal** removes the entire affected Evidence-Unit Support
  Assertion. It is not supersession. The Memory remains active while another
  complete independent Support remains.
- **RETIRE** occurs only when authoritative coverage proves removal and no
  complete Support remains.

Partial Projection, missing scope attestation, stale catalog, provider failure,
or unresolved semantic coverage preserves current Support and produces the
existing bounded failure, Finding, or Review outcome. While a Lifecycle Gate is
closed, a Review stages complete remove-old/attach-new Evidence-Unit mutations
and leaves the old unit active. Plan and Review stale guards hash complete
Evidence-Unit Support topology, not flat member-reference rows.

The Evidence Resolver reports only Evidence outcomes such as accepted,
rebind-complete, unsupported, stale, or needs semantic review. Relation-first
reconciliation and the Lifecycle Planner remain the sole owners of KEEP,
UPDATE, SUPERSEDE, REMOVE_SUPPORT, and RETIRE. No new Memory lifecycle status is
introduced.

## Retrieval projection

`search` continues to return canonical Memory summaries. `get_memory` remains
the detail operation for verifiable provenance and adds a unified role-aware
Evidence projection. Each returned Evidence item identifies its role, text or
Artifact kind, current Observation Revision, source/document locator, and
either an exact excerpt or a fetchable Artifact URL. Primary Evidence is the
default claim citation, Required Evidence is presented as a dependency, and
Context is explicitly marked as non-supporting related material.

Existing `sources[]` and `evidence_artifacts[]` fields remain compatibility
projections during migration. Artifact summaries remain selection hints only;
callers use `get_resource` to inspect exact authorized bytes. A Context Artifact
may therefore appear in `get_memory` without keeping the Memory active or
causing lifecycle invalidation when that Context alone changes.

## Considered options

- **Trust model-returned Evidence text and remove selectors** — rejected because
  generated text cannot prove current-revision identity, exact source content,
  uniqueness, access scope, or deterministic replay. Re-matching it would
  recreate the localization problem under another name.
- **Keep existing coarse Block IDs and remove quote matching** — rejected
  because formatting warnings would disappear while a compound claim could
  silently select only one partially supporting Block.
- **Keep quote matching and whole-Block fallback** — rejected because model
  copying is representation-sensitive for HTML and tables, and fallback can
  widen Evidence without proving complete claim-local support.
- **Add a generic AND/OR Support expression engine** — rejected as unnecessary.
  Evidence Units have one fixed Primary-plus-all-Required invariant; independent
  Supports already express alternatives without a new logic language.

## Consequences

The canonical OSS storage protocols, SQLite adapter, HANA adapter, fakes, route
contracts, and tests must interpret Evidence-Unit Support identically. HANA or
another adapter may not retain per-reference Support semantics as a
compatibility shortcut. `memory_sources` remains a materialized provenance read
model whose bidirectional invariant is checked against complete Evidence-Unit
Supports.

The extraction structured schema, Evidence catalog and localization Modules,
projection Evidence materialization, no-op revalidation, revision composition,
Lifecycle Plan mutations, Review fingerprints, support hashes, retrieval
detail schema, and online evaluation taxonomy all change together. The old
`whole_block_fallback` signal remains immutable historical evidence; the new
contract records fragment/compiler identity, selected role counts, resolved
part ranges and hashes, and explicit rejection or review reasons without
persisting source text in runtime events.

This ADR defines design and acceptance semantics only. It does not authorize
source re-ingestion, historical Memory rewriting, lifecycle repair, automatic
reassessment of prior events, or deployment.

## References

- [ADR 0007: Bind extracted evidence to the current Source Projection](0007-bind-extracted-evidence-to-the-current-projection.md)
- [ADR 0010: Keep the support provenance projection complete](0010-keep-support-provenance-projection-complete.md)
- [ADR 0014: Model binary Artifacts as revision-pinned Source Evidence](0014-model-binary-artifacts-as-revision-pinned-source-evidence.md)
- [ADR 0028: Separate conversation coverage from content and retention](0028-separate-conversation-coverage-from-content-and-retention.md)
- [W3C Web Annotation Data Model selectors](https://www.w3.org/TR/annotation-model/#selectors)
