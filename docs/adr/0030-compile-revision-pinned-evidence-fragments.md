# ADR 0030: Compile revision-pinned Evidence Fragments

## Status

Accepted (2026-08-27)

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
  -> extraction model returns Memory + primary_ref + required_refs
  -> Evidence Resolver validates and materializes exact revision-pinned references
  -> one complete Evidence Unit
  -> one Support Assertion
  -> relation-first reconciliation and one atomic Lifecycle Plan
```

The ordinary source-extraction response never returns authoritative Evidence
text, source offsets, Observation identities, durable fragment identities, or
lifecycle actions. Structured-output validity proves only response shape.
Application code owns Evidence authority and immediately rejects an unknown,
stale, out-of-scope, cross-catalog, mixed-access, or unresolvable selection.
Managed Agent Session patch intent is a distinct upstream command proposal and
is constrained separately below; it never becomes lifecycle authority.

## Evidence Fragment catalogs

An Evidence Fragment is an application-owned structural region inside one
current Source Observation Revision. Each offered Fragment carries an exact
revision coordinate and content hash. Its short model-facing reference is valid
only inside the exact immutable catalog sent to that model call and is absent
from completed derivation and durable lifecycle records.

The compiler varies by representation, not by Configured Source type. Every
inference-eligible Source Observation Revision declares one typed, versioned
Evidence Representation Profile rather than asking extraction code to infer
syntax from `source_type`, MIME, or content. Unknown or inconsistent profiles
fail closed.

The one external compiler interface is equivalent to:

```python
compile_fragments(
    revision: SourceObservationRevision,
    profile: EvidenceRepresentationProfile,
    owned_ranges: tuple[SourceAnchor, ...],
) -> EvidenceFragmentCatalog
```

`EvidenceRepresentationProfile` carries an exact profile name, a separate
positive integer version, and a coordinate-space contract. The registry key is
the pair `(name, version)`; the name never embeds a `-vN` suffix. A version bump
is required only when Fragment boundaries or coordinate semantics change, not
for an implementation fix that preserves identical catalog output.
Representation adapters and nested text parsing remain private implementation
seams. The profile is technical revision/audit metadata, not Source identity,
Evidence authority, or another lifecycle state.

The initial private adapter set is deliberately small:

- `markdown-structural` compiles normalized Markdown, including embedded
  HTML, headings, paragraphs, lists, tables, blockquotes, and code blocks;
- `canonical-record` compiles application-owned structured records into
  field- or record-level Fragments and delegates nested text bodies to the
  declared text representation;
- `plain-text` compiles paragraphs or one explicitly atomic text record;
- `binary-artifact` exposes one whole revision-pinned Artifact.

These are private adapters behind one compiler interface, not four extraction
paths and not one compiler class per Source type. Future HTML-only, PDF-page,
email/MIME, or other formats enter through the same representation seam only
when a real Source Observation contract can declare their coordinate space and
revision identity.

Provider adapters continue to own provider identity, Source Unit and
Observation topology, edit/delete semantics, relations, scope, and coverage.
Evidence and Lifecycle code never branch on `source_type`.

### Current source matrix

| Source path | Projected shape | Evidence Representation Profile | Design consequence |
| --- | --- | --- | --- |
| Confluence | One normalized page-body Observation plus revision-pinned Artifacts | `markdown-structural`; `binary-artifact` | Embedded storage HTML is compiled inside Markdown; attachment inventory alone is not Evidence. |
| Jira | Canonical issue-core, comment, and changelog Observations plus Artifacts | `canonical-record`; `binary-artifact` | Field and comment identity remain provider-owned; the compiler does not parse raw Jira payloads. |
| GitHub Repository | Normalized file-content Observation plus explicitly supported repository-file Artifacts | `markdown-structural`; `binary-artifact` | Markdown, code fences, and embedded HTML share one structural compiler. |
| GitHub Pages | Normalized rendered-page Observation | `markdown-structural` | No implicit linked-image crawl or provider-specific compiler. |
| Local Markdown | Revision-pinned local-file Markdown Observation | `markdown-structural` | Local collection topology does not change Evidence semantics. |
| Teams | Canonical message Observations with reply/precedence relations and separately projected hosted-image Artifacts | `canonical-record`; nested declared text; `binary-artifact` | Message edit/delete and conversation coverage remain Source Projection concerns. |
| Agent Session document intake | Session-summary Markdown Observation | `markdown-structural` | Codex and Claude Code use the same compiler; client remains provenance, not Source or syntax. |
| Managed Agent Knowledge patch | Structurally classified session events followed by a projected concept-Markdown Observation | upstream authority contract plus `markdown-structural` | Transient patch intent and event IDs authorize the proposal; the projected Evidence Unit remains durable authority. |
| Extension Gene fallback | Declared normalized Markdown, canonical record, plain text, or Artifact under Partial Projection unless it proves more | declared profile only | An extension without a supported profile may collect content but cannot invent selectable Evidence. |
| Direct User create/correction | User-confirmed provenance in Virtual Documents; no Gene extraction | no model compiler | Explicit user authority is preserved and projected separately as described below. |

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
content. `binary-artifact` is offered only for an exact current Artifact that
is inference-eligible and actually supplied to the configured model. A stored
but ineligible or unsupported Artifact remains retrievable under its existing
contract and cannot be selected as claim Evidence.

## Managed Agent Sessions and Direct User provenance

Codex and Claude Code are Clients of the same per-user `agent_session` Source
contract; they do not create different Source types or compiler implementations.
Two existing managed-capture paths remain distinct while converging on the same
durable Evidence seam:

1. Agent Session document intake projects an authorized session summary as a
   normal Markdown Observation and uses ordinary Fragment extraction.
2. Managed Agent Knowledge first classifies canonical session events using
   structural roles and may return a typed create/update/supersede patch intent
   plus cited primary event IDs. That output is transient command intent, not a
   Lifecycle action. Application code validates the cited user authority,
   projects the durable concept/claim Markdown, compiles its exact current
   Evidence, runs relation-first reconciliation, and remains the sole owner of
   lifecycle mutations.

The Fragment compiler does not reclassify raw Codex/Claude events, promote tool
logs or assistant narration to authority, or persist patch intent as a parallel
Evidence identity. Current event citations and client/session receipts remain
audit provenance for the one revision-pinned projected Evidence Unit.

`user_memory` and `user_correction` Virtual Documents do not call an extraction
model and therefore do not need transient Fragment references. Their explicit,
confirmed provenance is application-owned Primary Evidence. Existing correction
authority, Support-set stale hashes, hidden challenger Review, and atomic
replacement semantics remain unchanged. They may use the same role-aware
`get_memory` projection without being forced through Source Projection or a
Configured-Source compiler path.

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
resolved Primary/Required part-set digest, and access context. Compiler profile,
version, and catalog digest are audit and deterministic-reconstruction metadata,
not business identity; changing the compiler alone cannot create a different
Evidence Unit when the resolved current Evidence is identical. Each contained
Evidence Reference retains its role and exact revision-pinned Source Anchor.

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

When a Revision Delta is proven Disjoint from every Primary and Required
Anchor, the current Evidence Unit remains valid. An Affected or Unknown result
creates one revalidation work item for the complete unit. The work item compiles
a fresh catalog from the target revisions, presents the incumbent claim and its
old resolved Evidence as read-only comparison context, and resolves a complete
new Primary/Required set or an explicit unsupported/unknown result. It never
maps an old transient Fragment reference into a new catalog. A provider-backed
`FragmentMapping` may narrow impact or provide a rebind hint, but derived
Markdown/HTML/record Fragments are not promoted to stable identity.

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

Reconciliation still requires complete Mandatory Incumbent Scope coverage.
Fragment compilation and revalidation can prove Evidence selection, but cannot
turn an omitted incumbent into KEEP or reduce the requirement that every
affected incumbent receives exactly one terminal reconciliation decision.

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

### Retry and recovery

The target Source Unit Revision, representation profile/version, owned
authority surface, and catalog digest are deterministic inputs to one immutable
derivation batch. Before a batch completes, retry may reconstruct that exact
catalog and rerun extraction under the existing deadline and stale guards. The
model-facing Fragment references remain local to that reconstruction.

After a batch completes, the durable derivation output contains only resolved
Evidence Units and References. Scheduler recovery reuses that output and may
apply it only when the target revisions, access context, incumbent Memory
versions, and complete Evidence-Unit Support topology still match the Plan's
stale guards. A mismatch abandons the stale Plan and recalculates from current
Projection state; it never recompiles under a newer profile while pretending to
resume the old batch. No replay ledger or fragment lifecycle state is added.

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
