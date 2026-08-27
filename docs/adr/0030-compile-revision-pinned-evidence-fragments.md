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
    authority_ranges: tuple[EvidenceAuthorityRange, ...],
) -> EvidenceFragmentCatalog
```

Each `EvidenceAuthorityRange` contains one owned Source Anchor and an
application-owned `eligible_roles` set. Claim-authoritative ranges permit
`PRIMARY` and `REQUIRED`; bounded dependency ranges permit `REQUIRED` only.
Read-only Context ranges have no selectable role and are presented outside the
catalog. The compiler copies the eligible-role set to every contained Fragment;
representation parsing can narrow structure but can never widen authority.

`EvidenceRepresentationProfile` carries an exact profile name, a separate
positive integer version, a coordinate-space contract, and an optional typed
representation-schema reference. The registry key is the pair
`(name, version)`; the name never embeds a `-vN` suffix. A version bump is
required only when Fragment boundaries or coordinate semantics change, not for
an implementation fix that preserves identical catalog output. The schema
reference is required for `canonical-record` and forbidden for profiles that do
not consume a record schema.
Representation adapters and nested text parsing remain private implementation
seams. The profile is technical revision/audit metadata, not Source identity,
Evidence authority, or another lifecycle state.

The profile is persisted on every new `SourceObservationRevision` as dedicated
typed `profile_name`, `profile_version`, `coordinate_space`, and nullable
`representation_schema_name` / `representation_schema_version` fields. It is
not hidden in free-form metadata. The Source Projection Adapter supplies these
values when constructing the immutable Revision; Evidence code only validates
and consumes them. New inference-eligible Revisions cannot be stored without a
supported profile.

The initial private adapter set is deliberately small:

- `markdown-structural` compiles normalized Markdown headings, paragraphs,
  lists, tables, blockquotes, and code blocks. A CommonMark raw-HTML block or
  inline region is not one automatically atomic Markdown Fragment: the adapter
  delegates that exact source range to an offset-preserving embedded-HTML
  subparser so elements such as `li`, `tr`, `blockquote`, and `p` may become
  child Fragments in the same Observation Revision coordinate space;
- `canonical-record` compiles application-owned canonical JSON records into
  field- or record-level Fragments and delegates only fields declared as nested
  text by a registered representation-schema descriptor;
- `plain-text` compiles paragraphs or one explicitly atomic text record;
- `binary-artifact` exposes one whole revision-pinned Artifact.

These are private adapters behind one compiler interface, not four extraction
paths and not one compiler class per Source type. Future HTML-only, PDF-page,
email/MIME, or other formats enter through the same representation seam only
when a real Source Observation contract can declare their coordinate space and
revision identity.

Embedded HTML delegation is an internal seam of `markdown-structural`, not a
second public profile decision. The model-visible Fragment text may use a
deterministic tag-free/entity-decoded presentation, but the Fragment authority
always maps to one exact raw Markdown/HTML range in
`SourceObservationRevision.content`. If malformed or unsupported HTML prevents
an exact reversible mapping, that region is unselectable and reports a bounded
compiler error; it never falls back to the enclosing raw-HTML block.

The first version adds no generic embedded-language parser registry. Raw HTML
is handled because it is a standard CommonMark construct and a demonstrated
source shape. Fenced code, YAML front matter, Mermaid, MDX/JSX, math, template
directives, and other embedded syntaxes remain one atomic Fragment, deterministic
metadata, or an unselectable region according to their existing normalized
representation. A finer subparser is added only after a real claim-local
Evidence requirement proves that atomic treatment is insufficient and the
format has an exact reversible coordinate contract.

`canonical-record` does not contain Jira, Teams, or other Source-type branches.
Its schema descriptor is data owned by the projecting adapter and declares a
schema name/version, selectable JSON Pointer paths, atomic fields, and any
nested-text profile for a string field. Stored record content is deterministic
canonical JSON. The compiler records raw half-open ranges in that exact stored
JSON and uses a deterministic JSON-token decoder to map each decoded string
boundary back to the raw token boundary, including escapes and non-ASCII text.
A nested Fragment therefore has decoded presentation text but an authoritative
contiguous range in the immutable canonical JSON. A missing descriptor, a path
whose runtime type violates the descriptor, or a decoded boundary that cannot
map exactly makes that field unselectable and fails the bounded compilation;
the compiler never guesses a schema from `observation_type` or `source_type`.

### Deterministic catalog contract

All text coordinates are zero-based, half-open Unicode scalar-value indices in
the exact stored string. The compiler does not normalize authority text before
assigning ranges. Presentation text is a versioned pure rendering of the
authoritative slice: Markdown presentation preserves source text; embedded
HTML presentation removes tags, decodes entities, and applies one documented
whitespace normalization; canonical-record presentation decodes the selected
JSON value. The raw slice hash and presentation hash are both kept in the
catalog and the resolved Evidence Reference.

Only non-overlapping, minimal claim-bearing ranges are selectable. Structural
parents such as heading paths are catalog metadata, not overlapping selectable
Fragments. When an embedded adapter yields selectable children, those children
replace the enclosing atomic candidate. A candidate must be wholly contained
inside exactly one authority range; a range crossing an authority boundary is
rejected rather than clipped. The Resolver accepts `primary_ref` only from a
Fragment eligible for Primary and accepts each `required_ref` only from a
Fragment eligible for Required. A dependency/context input can therefore become
Required when application planning explicitly authorized that range, but it can
never become Primary merely because the model selected it.

Catalog order is deterministic by Observation Revision id, range start, range
end, Fragment kind, raw-slice hash, and presentation hash. Model references are
catalog-local ordinal tokens (`f000001`, `f000002`, ...), assigned only after
that sort. The catalog digest hashes the target Source Unit Revision, ordered
Observation Revision ids, complete representation profiles and schema refs,
authority ranges with eligible roles, compiler contract version, and every
ordered Fragment descriptor including its eligible roles.
Compiler retries must reproduce the same digest and tokens byte-for-byte.

Fragment-count and presentation-size limits are explicit compiler inputs and
part of the derivation runtime contract. Exceeding either returns a typed
`CATALOG_TOO_LARGE` result; it never silently truncates, merges Fragments,
widens to a parent, or creates lifecycle-visible batching. Concrete provider
token budgets remain deployment configuration and may change without changing
Evidence semantics because the chosen values are persisted with the derivation
batch and included in its deterministic input hash.

Malformed raw-HTML tests must cover an unclosed element, nested lists, table
rows with entities, comments, script/style raw text, duplicate visible text,
and a Unicode escape boundary in a canonical-record nested field. For every
selectable case, tests assert exact raw range, raw slice hash, presentation
text/hash, ordering, catalog digest, and retry reconstruction. Unsupported or
ambiguous cases assert a typed fail-closed result and no parent fallback.

Provider adapters continue to own provider identity, Source Unit and
Observation topology, edit/delete semantics, relations, scope, and coverage.
Evidence and Lifecycle code never branch on `source_type`.

### Current source matrix

| Source path | Projected shape | Evidence Representation Profile | Design consequence |
| --- | --- | --- | --- |
| Confluence | One normalized page-body Observation plus revision-pinned Artifacts | `markdown-structural`; `binary-artifact` | HTML converted by the Gene is ordinary Markdown; any preserved raw HTML uses the private embedded-HTML subparser. Attachment inventory alone is not Evidence. |
| Jira | Canonical issue-core, comment, and changelog Observations plus Artifacts | `canonical-record`; `binary-artifact` | Field and comment identity remain provider-owned; the compiler does not parse raw Jira payloads. |
| GitHub Repository | Normalized file-content Observation plus explicitly supported repository-file Artifacts | `markdown-structural`; `binary-artifact` | Markdown and code fences compile directly; preserved raw HTML delegates internally without changing the profile. |
| GitHub Pages | Normalized rendered-page Observation | `markdown-structural` | No implicit linked-image crawl or provider-specific compiler. |
| Local Markdown | Revision-pinned local-file Markdown Observation | `markdown-structural` | Local collection topology does not change Evidence semantics. |
| Teams | Canonical message Observations with reply/precedence relations and separately projected hosted-image Artifacts | `canonical-record`; nested declared text; `binary-artifact` | Message edit/delete and conversation coverage remain Source Projection concerns. |
| Agent Session document intake | Session-summary Markdown Observation | `markdown-structural` | Codex and Claude Code use the same compiler; client remains provenance, not Source or syntax. |
| Managed Agent Knowledge patch | Structurally classified session events followed by a projected concept-Markdown Observation | upstream authority contract plus `markdown-structural` | Transient patch intent and event IDs authorize the proposal; the projected Evidence Unit remains durable authority. |
| Extension Gene fallback | Declared normalized Markdown, canonical record, plain text, or Artifact under Partial Projection unless it proves more | declared profile only | An extension without a supported profile may collect content but cannot invent selectable Evidence. |
| Direct User create/correction | User-confirmed provenance in Virtual Documents; no Gene extraction | no model compiler | Explicit user authority is preserved and projected separately as described below. |

### Existing-revision profile cutover

The schema change is additive. Profile fields are initially nullable only so
already stored immutable Revisions remain readable. Each built-in Projection
Adapter implements one provider-neutral backfill hook that declares the profile
from the adapter's stored Observation contract and representation-schema
version. The migration invokes that hook over existing rows and updates only
the new technical columns; it does not recollect a provider, rerun ingestion,
change content or semantic hashes, create a new Revision, or mutate Evidence or
Memory lifecycle.

The backfill hook may inspect the stable Observation classification and stored
projection metadata that its adapter owns, but it may not sniff content or make
Evidence/Lifecycle branch on Source type. If the responsible adapter cannot
declare one exact profile and schema for a historical Revision, the profile
remains absent. That Revision stays retrievable but is ineligible for new
Fragment compilation or automatic revalidation; any existing Support that
depends on it enters the existing legacy-limited/gated treatment described in
the Support cutover below. After all built-in adapters write profiles for new
rows, storage rejects any new inference-eligible Revision without one.

Text Fragments use exact half-open ranges in the immutable Observation Revision.
HTML list items, table rows, blockquotes, Markdown paragraphs, list items,
table rows, and code blocks may therefore be independently selectable while
mapping back to exact source characters. A whole Observation is selectable
only when its versioned representation contract explicitly declares that
Observation atomic; it is not a recovery fallback for failed localization.

Binary Artifact catalog entries carry a distinct `artifact` kind, but the model
uses the same transient reference selection shape for text and Artifacts. The
offered reference resolves to the Artifact Observation's whole-observation
Anchor and exact revision metadata and bytes. Filename, upload event, parent
body, URL, OCR guess, or Artifact summary never substitutes for inspected
Artifact content. `binary-artifact` is offered only for an exact current
Artifact that is inference-eligible and actually supplied to the configured
model. A stored but ineligible or unsupported Artifact remains retrievable
under its existing contract and cannot be selected as claim Evidence.

### Extraction selection contract

`projection-extraction-v9` replaces all text-versus-Artifact candidate variants
with one discriminated candidate whose Evidence selection is:

```json
{
  "content": "...",
  "memory_type": "fact",
  "primary_ref": "f000012",
  "required_refs": ["f000018"]
}
```

The selected catalog entry carries the `text` or `artifact` discriminator; the
model never returns Observation ids, offsets, Evidence text, hashes, profile
names, or lifecycle actions. `primary_ref` is required and singular.
`required_refs` is an ordered, duplicate-free list and may mix text and Artifact
entries with the Primary when all entries belong to the same offered catalog,
Configured Source, Source Unit Revision, and access context. The resolver sorts
the durable Required set by canonical Fragment order before hashing, so model
array order is not business identity.

The existing `projection-extraction-v8` contract is never interpreted as v9.
Completed v8 derivations and lifecycle history remain immutable and readable
through the existing legacy Evidence projection. A pending or retryable v8
derivation is terminally failed with a typed `CONTRACT_SUPERSEDED` reason at the
deployment boundary and may be rescheduled as a new v9 derivation against the
same still-current stored Source Unit Revision; this recompiles stored content
but does not rerun ingestion. A
pending Lifecycle Plan or Review whose stale guard or staged mutations use the
old reference-level Support schema cannot apply after cutover: it remains as
audit history and is recalculated from current state on its next authorized
operation. There is no dual-write and no payload-shape guessing.

The v9 compiler, prompt, schema, and Resolver may merge behind a disabled
contract gate and may run content-free metrics or non-authoritative shadow
validation, but v9 output cannot create Evidence, Support, a Lifecycle Plan, or
a Review while `support_scope_version` is v1. v9 becomes the default and its
resolved Units become admissible only in the same controlled activation that
sets `evidence-unit-set-v2`. This prevents a compound v9 Primary/Required result
from ever being persisted temporarily as independent reference-scoped Support.

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

The managed-patch schema adopts the same fixed evidence logic before
projection: one `primary_event_id` and ordered, duplicate-free
`required_event_ids`. Existing plural `primary_evidence_ids` payloads remain
readable audit data; pending payloads with more than one independent primary
event are split into atomic claim proposals or sent to Review, never collapsed
arbitrarily. The authority validator resolves every event id inside the same
authorized session, rejects assistant/tool-only authority, and creates one
deterministic concept-Markdown Revision plus an event-to-source-range receipt.
Only those typed authority ranges are compiled. The resolved Fragment
References become durable Evidence; event ids and the receipt remain audit
provenance and cannot be supplied directly to Lifecycle Plan mutations. A
completed legacy managed patch is not replayed merely to adopt the new schema.

`user_memory` and `user_correction` Virtual Documents do not call an extraction
model and therefore do not need transient Fragment references. Their explicit,
confirmed provenance is application-owned Primary Evidence. Existing correction
authority, Support-set stale hashes, hidden challenger Review, and atomic
replacement semantics remain unchanged. They may use the same role-aware
`get_memory` projection without being forced through Source Projection or a
Configured-Source compiler path.

## Evidence roles

Every source-backed Evidence Unit contains exactly one Primary Evidence
Reference and zero or more Required Evidence References. Zero or more Context
Evidence References may be associated through the separate current Context
projection described below.

- **Primary** directly states the claim and is the authority from which the
  claim may be extracted. A text Primary resolves from `primary_ref`; a visual
  claim may select a supplied Artifact as Primary.
- **Required** is necessary for the claim to stand or retain its meaning. The
  model may promote only a reference from the bounded dependency/context input
  of the current work. Merely helpful material is not Required.
- **Context** assists interpretation and resource inspection but does not
  support the claim or independently trigger invalidation. Context is selected
  by application-owned planning; the model does not return arbitrary Context
  references. It is not a member of the immutable supporting Evidence Unit.

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
Evidence Reference retains its role, kind, exact revision-pinned Source Anchor,
raw-slice or Artifact digest, presentation hash, and exact text excerpt or
authorized Artifact metadata. The existing singular Evidence Unit `excerpt`
is retained only as a compatibility projection of the Primary text and is not
the durable source for multipart Evidence.

The v2 part-set digest is exactly the hash of the canonically sorted tuple for
each supporting part:
`(role, kind, observation_id, observation_revision_id, anchor_kind,
range_start, range_end, raw_slice_or_artifact_digest)`. It excludes the
presentation hash, display excerpt, Fragment/catalog reference, catalog digest,
representation profile/schema, compiler contract version, and extraction-model
metadata. A presentation-only or compiler-only change therefore cannot create
a different Evidence Unit or Support edge when authoritative revision, Anchor,
role, kind, and raw/Artifact content are unchanged.

A Memory Support Assertion points to the complete Evidence Unit. It never
points independently to one contained Primary or Required reference. An
Evidence Unit supports its claim only while its Primary and every Required
reference are current and valid. Context currentness affects only the related
context projection.

Context reuses the immutable `evidence_references` table but makes its current
mandatory `evidence_unit_id` nullable under a role/ownership check: Primary and
Required rows require an Evidence Unit id; Context rows require it to be null.
The new `evidence_context_associations` table contains `id`,
`evidence_unit_id`, `evidence_reference_id`, `active`, `created_at`, and
`updated_at` / nullable `removed_at`, with mandatory foreign keys and unique
`(evidence_unit_id, evidence_reference_id)`. Store validation accepts only a
Context-role Reference on that association. Association id is the deterministic
hash of the Unit and Reference ids.

Replacing Context atomically deactivates the old association(s) and inserts or
reactivates the exact new revision-pinned association(s). Evidence References
remain immutable; the association is deliberately a mutable current projection,
not an interval-history ledger. Reactivation updates `active`, `updated_at`, and
`removed_at`; the existing derivation/operation audit records preserve why the
projection changed. At most one active row exists for one Unit/Context Reference
pair, and `get_memory` returns only active associations. The association is not
part of Evidence Unit identity, Support identity, support-set hashes, stale
guards, or destructive lifecycle authority. On a Context-only revision change,
application-owned context planning may replace or remove it while the supporting
Evidence Unit and Support Assertion remain unchanged. A Context Reference
promoted to Primary or Required by a later derivation is materialized as a new
supporting Reference in a new Evidence Unit through the ordinary revalidation
path; the old Context Reference remains immutable.

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

### Support schema and cutover

The canonical storage model adds a unit-scoped Support table with
`id`, `memory_id`, `evidence_unit_id`, `source_id`, `access_context_hash`,
`active`, `created_at`, and `removed_at`. The unique key is
`(memory_id, evidence_unit_id)`. A Support id is the deterministic hash of that
pair plus `source_id` and `access_context_hash`; changing any of them creates a
different edge. The Evidence Unit foreign key is mandatory. Domain validation
and the transactional store require exactly one Primary, no duplicate
Primary/Required Anchor-role pair, and all referenced Revisions to match the
Unit's Source, Source Unit Revision, and access context before a Support can be
activated. SQLite and HANA enforce the same constraints and error behavior.

The migration is additive and has four bounded phases; it never dual-writes one
logical Support edge:

1. A compatibility release adds the new unit-scoped table, a durable
   `support_scope_version` marker, and protocol implementations while the
   legacy writer remains the sole writer. Both old and new binaries refuse an
   unknown marker. No v2 Support is active yet.
2. In one report-only inventory, group old rows by
   `(memory_id, evidence_unit_id, source_id, access_context_hash)`. A group is
   mechanically eligible only when its Unit has exactly one Primary and every
   support-granting Primary/Required Reference has exactly one old row with the
   same active state. Active rows require non-empty creation times; inactive
   rows additionally require non-empty removal times.
3. At the controlled cutover, web/worker lifecycle writers are quiesced and one
   migration lease protects an exact-count, idempotent final backfill. It creates
   one new Support edge for every eligible group. Both use the earliest creation
   time; all-active groups become active, while all-inactive groups become
   inactive with the latest removal time.
   Mixed, incomplete, multi-Primary, missing-Unit, or access/source-inconsistent
   groups are never collapsed or inferred.
4. In the same cutover transaction, rebuild and validate `memory_sources`, set
   the marker to `evidence-unit-set-v2`, and activate v2 code. From that point,
   all new writes, current-support queries, support hashes, Lifecycle Plan
   mutations, Reviews, recovery, and provenance checks use Unit ids and the
   legacy table is immutable archive.

Before the marker changes, rollback removes no data: the new binary may be
withdrawn and the legacy writer resumed. After the first v2 write, downgrade to
a reference-scoped writer is forbidden; recovery is forward-only because an
old writer cannot preserve Unit atomicity. SQLite performs the switch under its
exclusive migration transaction. HANA uses the same logical preflight counts,
migration lease, marker, and postcondition checks even though its DDL transaction
mechanics differ. The Cloud rollout must stop old workers before changing the
marker and must not use an overlapping rolling deployment for this boundary.

An ineligible legacy group does not disappear and does not silently keep
destructive authority. Its existing Memory lifecycle state and old rows remain
unchanged, it is surfaced through the existing `LEGACY_LIMITED_EVIDENCE`
provenance/Review path, and automatic destructive reconciliation is gated until
fresh current Evidence or an authorized review supplies one complete Unit.
During the bounded transition, a canonical OSS legacy reader may count such an
edge only to preserve the Memory's current availability; it cannot satisfy a
new unit-scoped stale guard or authorize UPDATE, SUPERSEDE, REMOVE_SUPPORT, or
RETIRE. This is one shared migration rule for SQLite and HANA, not an adapter
compatibility branch, and is removed only after an inventory proves no active
legacy-limited edges remain.

Old support-set fingerprints are versioned as `reference-set-v1`; the new hash
is `evidence-unit-set-v2` over sorted active `(support_id, evidence_unit_id,
source_id, access_context_hash)` tuples plus each Unit's sorted
Primary/Required part digest. A plan or pending Review carrying v1 cannot be
applied by v2 code and is treated as stale. Existing Review records are never
deleted or rewritten; a continued review creates a new v2 proposal linked by
the existing review lineage. `memory_sources` is rebuilt and checked from the
union of active v2 Supports and explicitly gated legacy-limited edges during
the transition, then from v2 Supports alone after convergence.

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
the detail operation for verifiable provenance and adds a grouped role-aware
`evidence[]` projection. One array entry represents one independent Evidence
Unit/Support alternative; its `items[]` contains the jointly required Primary
and Required parts plus the current non-supporting Context associations:

```json
{
  "evidence": [
    {
      "evidence_unit_id": "eunit-...",
      "support_id": "support-...",
      "support_status": "active",
      "source_id": "src-...",
      "source_unit_revision_id": "unitrev-...",
      "items": [
        {
          "role": "primary",
          "kind": "text",
          "observation_revision_id": "obsrev-...",
          "range": {"start": 120, "end": 181},
          "content_hash": "...",
          "excerpt": "...",
          "resource": null,
          "contributes_to_support": true
        },
        {
          "role": "context",
          "kind": "artifact",
          "observation_revision_id": "obsrev-...",
          "range": null,
          "content_hash": "...",
          "excerpt": null,
          "resource": {"kind": "artifact", "id": "...", "url": "..."},
          "contributes_to_support": false
        }
      ]
    }
  ]
}
```

Independent active Units are logical alternatives; within one Unit, Primary
plus every Required item are jointly necessary. Context never changes that
logic. Units sort by active status, creation time, then Unit id. Items sort
Primary first, Required by canonical Anchor order, then current Context by
canonical Anchor order. Authorization is applied before grouping; an Evidence
Unit is not returned partially. If the caller cannot read every supporting
Primary/Required item, the entire Unit is omitted. Context items are omitted
individually when unauthorized because they do not grant or prove Support.

For text, `excerpt` is reconstructed from the exact stored Revision range and
must match the durable raw-slice hash before return; a mismatch fails the Unit
closed and emits a Finding rather than returning stale text. For Artifacts,
`content_hash` is the revision-pinned byte digest and `resource.url` is an
authorized fetch route; `get_resource` remains the operation that returns exact
bytes. Primary Evidence is the default claim citation, Required Evidence is
presented as a dependency, and Context is explicitly marked non-supporting.

Existing `sources[]` and `evidence_artifacts[]` fields remain compatibility
projections derived from the same authorized grouped result during one release
window; they are never queried through a second source-of-truth path. Their
deprecation is announced before removal. Artifact summaries remain selection hints only;
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
- **Add a generic Markdown embedded-language parser registry** — rejected as
  speculative. The initial Markdown adapter delegates only CommonMark raw HTML;
  every later nested syntax requires a demonstrated Evidence consumer and exact
  offset contract before gaining a subparser.

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

- [Implementation umbrella: shno-labs/mem-forge#303](https://github.com/shno-labs/mem-forge/issues/303)
- [Profile and compiler slice: shno-labs/mem-forge#305](https://github.com/shno-labs/mem-forge/issues/305)
- [Selection and resolver slice: shno-labs/mem-forge#306](https://github.com/shno-labs/mem-forge/issues/306)
- [Evidence-Unit Support slice: shno-labs/mem-forge#307](https://github.com/shno-labs/mem-forge/issues/307)
- [Grouped retrieval/evaluation slice: shno-labs/mem-forge#308](https://github.com/shno-labs/mem-forge/issues/308)
- [Cloud HANA rollout slice: dodoman-sun/memforge-cloud#391](https://github.com/dodoman-sun/memforge-cloud/issues/391)
- [ADR 0007: Bind extracted evidence to the current Source Projection](0007-bind-extracted-evidence-to-the-current-projection.md)
- [ADR 0010: Keep the support provenance projection complete](0010-keep-support-provenance-projection-complete.md)
- [ADR 0014: Model binary Artifacts as revision-pinned Source Evidence](0014-model-binary-artifacts-as-revision-pinned-source-evidence.md)
- [ADR 0028: Separate conversation coverage from content and retention](0028-separate-conversation-coverage-from-content-and-retention.md)
- [CommonMark: HTML blocks are raw Markdown regions](https://spec.commonmark.org/spec#html-blocks)
- [W3C Web Annotation Data Model selectors](https://www.w3.org/TR/annotation-model/#selectors)
