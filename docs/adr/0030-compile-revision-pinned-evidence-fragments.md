# ADR 0030: Compile revision-pinned Evidence Fragments

## Status

Accepted (2026-08-27; amended 2026-09-01)

MemForge will replace provider-returned evidence text, single coarse Block
selection, quote matching, and whole-Block fallback with application-owned
Evidence Fragments. The model selects one Primary Fragment and zero or more
Required Fragments from one immutable extraction catalog. Application code
marks only current authorized work as Primary-eligible, while exact bounded
Context may be selected only as Required; application code then
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
  -> batch-local authorized work and bounded Context
  -> representation-aware Evidence Fragment Compiler
  -> immutable candidate Corpus with transient global references
  -> one bounded presentation
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
only inside one exact immutable Fragment Corpus and is absent from completed
derivation and durable lifecycle records. A bounded presentation window is a
lossless transient view of that Corpus: it preserves the global reference and
never renumbers, duplicates, splits, or widens a Fragment.

The compiler varies by representation, not by Configured Source type. Every
inference-eligible Source Observation Revision declares one typed, versioned
Evidence Representation Profile rather than asking extraction code to infer
syntax from `source_type`, MIME, or content. Unknown or inconsistent profiles
fail closed.

The one external compiler interface is equivalent to:

```python
compile_fragments(
    revision: SourceObservationRevision,
    candidate_ranges: tuple[EvidenceCandidateRange, ...],
) -> EvidenceFragmentCatalog
```

The compiler reads the profile only from the immutable Revision and resolves it
through the application-owned representation registry. A missing or unsupported
profile returns a deterministic typed failure; a caller cannot supply or override
the Revision's representation.

Each `EvidenceCandidateRange` contains one owned Source Anchor and one transient
application-owned `primary_eligible` Boolean. Every selectable range may be
selected as `REQUIRED`; only current authorized work has
`primary_eligible=true` and may be selected as `PRIMARY`. Exact bounded Context
has `primary_eligible=false`. Material that cannot become exact supporting
Evidence remains outside the catalog as display-only Context. The compiler
copies this Boolean to every contained Fragment; representation parsing can
narrow structure but can never widen authority.

`primary_eligible` answers only whether a claim may originate from the range in
the current work. It is determined from changed/added batch ranges, an explicit
reprocess selection, current or rebound incumbent ranges authorized for
revalidation, exact managed-user event authority, or a current inference-eligible
Artifact actually supplied to the model. It is not inferred from content or
Source relation type, and it is not persisted as Source or lifecycle state.

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
and consumes them. Every new Source Observation Revision must use one exact
application-registered representation contract; an unknown contract is rejected
rather than persisted as an inference Revision. An extension may retain raw or
normalized collected content outside this selectable projection until it can
declare a supported profile. Historical Revisions whose profile cannot be
backfilled remain retrievable and carry-only but cannot enter Fragment
compilation.

The initial private adapter set is deliberately small:

- `markdown-structural` compiles normalized Markdown headings, paragraphs,
  lists, tables, blockquotes, and code blocks. CommonMark `html_inline` tokens
  are validated and rendered through the private offset-preserving HTML seam but
  remain inside one claim-coherent Markdown paragraph. Raw-HTML blocks may yield
  structural `li`, `tr`, `blockquote`, or `p` Fragments when exact non-overlapping
  child ranges are available; otherwise the exact CommonMark block is one
  intentionally atomic Fragment;
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
`SourceObservationRevision.content`. CommonMark recognizes individual inline
open and closing tags; it does not require them to form a balanced DOM. The
compiler therefore uses CommonMark `html_inline` tokens for validity and exact
source localization rather than imposing tag-pair balance. Unsafe content or a
token that cannot map reversibly is unselectable. Selecting an enclosing
paragraph or raw-HTML block is permitted only when that is the representation's
deterministic, predeclared structural unit; it is never localization-error
fallback.

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

Compiler-backed v9 Primary authority segmentation follows the immutable
representation profile. `markdown-structural` and `plain-text` are
range-addressable and may be divided into exact presentation ranges.
`canonical-record` and every whole-Artifact coordinate profile retain whole-
Observation authority through compilation: record fields must be decoded before
their exact raw ranges exist, and Artifact bytes are atomic. This decision comes
from the profile even when the current compiler registry does not support that
profile version; the compiler then returns its typed unsupported-profile error
without receiving a partial range. The planner never branches on Jira, Teams,
or another Source type.

Legacy projection extraction still presents batch Markdown directly and keeps
its existing `max_primary_chars` segmentation. The v9 authority/segmentation
policy has a distinct version in extraction-batch identity so completed v9 work
from the earlier generic character-slicing policy is not silently reused while
legacy batch identity remains stable.

### Deterministic catalog contract

All text coordinates are zero-based, half-open Unicode scalar-value indices in
the exact stored string. The compiler does not normalize authority text before
assigning ranges. Presentation text is a versioned pure rendering of the
authoritative slice: Markdown presentation preserves source text; embedded
HTML presentation removes tags, decodes entities, and applies one documented
whitespace normalization; canonical-record presentation decodes the selected
JSON value. The raw slice hash and presentation hash are both kept in the
catalog and the resolved Evidence Reference.

Only non-overlapping, claim-coherent structural ranges are selectable. The
compiler prefers the smallest range that independently preserves the claim, but
retains the enclosing deterministic paragraph or block when finer segmentation
would destroy independent support. Structural
parents such as heading paths are catalog metadata, not overlapping selectable
Fragments. When an embedded adapter yields selectable children, those children
replace the enclosing atomic candidate. A candidate must be wholly contained
inside exactly one candidate range; a range crossing an authorized-work
boundary is rejected rather than clipped. The Resolver accepts `primary_ref`
only from a Fragment with `primary_eligible=true`. It accepts any other
selectable Fragment as `required_ref`. Bounded Context can therefore become
Required when the model determines that the claim would otherwise be
unsupported, ambiguous, or change meaning, but it can never become Primary
merely because the model selected it.

Source relations only help application planning find bounded Context. A direct
`precedes`, `replies_to`, `contained_by`, or `references` relation does not by
itself set `primary_eligible` or make its endpoint Required. The model decides
which presented Context is actually Required; unselected Context does not enter
the Evidence Unit.

Catalog order is deterministic by Observation Revision id, range start, range
end, Fragment kind, raw-slice hash, and presentation hash. Model references are
catalog-local typed ordinal tokens assigned only after that sort:
Primary-capable Fragments use `pNNNNNN`, while Required-only Fragments use
`rNNNNNN`. A `p...` Fragment may still be selected as Required for another
claim. The prefix is transient model capability, not durable Evidence role or
identity. The catalog digest hashes the target Source Unit Revision, ordered
Observation Revision ids, complete representation profiles and schema refs,
candidate ranges with Primary eligibility, the authority-policy/compiler
contract version, and every ordered Fragment descriptor including its
Primary-eligibility bit.
Compiler retries must reproduce the same digest and tokens byte-for-byte.

Normal v9 extraction currently has one explicit catalog/presentation ceiling.
Exceeding it returns typed `CATALOG_TOO_LARGE`; the planner and compiler never
raw-slice a canonical record, silently truncate Fragments, widen to a parent,
or fall back to whole-block Evidence. Generic exhaustive multi-window discovery
and final adjudication require a separate post-compilation trigger and contract;
they are deferred to [issue 365](https://github.com/shno-labs/mem-forge/issues/365)
rather than being implied by Source batching.

Raw-HTML tests must cover valid unclosed CommonMark open tags, nested lists,
table rows with entities, comments, script/style raw text, duplicate visible text,
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
| Jira | Canonical issue-core, comment, and changelog Observations plus Artifacts | `canonical-record`; `binary-artifact` | Field and comment identity remain provider-owned; whole canonical authority reaches schema compilation before exact field ranges are presented. |
| GitHub Repository | Normalized file-content Observation plus explicitly supported repository-file Artifacts | `markdown-structural`; `binary-artifact` | Markdown and code fences compile directly; preserved raw HTML delegates internally without changing the profile. |
| GitHub Pages | Normalized rendered-page Observation | `markdown-structural` | No implicit linked-image crawl or provider-specific compiler. |
| Local Markdown | Revision-pinned local-file Markdown Observation | `markdown-structural` | Local collection topology does not change Evidence semantics. |
| Teams | Canonical message Observations with reply/precedence relations and separately projected hosted-image Artifacts | `canonical-record`; nested declared text; `binary-artifact` | Message edit/delete and conversation coverage remain Source Projection concerns; canonical messages use the same whole-authority compiler contract as every canonical record. |
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

A Partial Projection may carry an unprofiled historical Revision only by
referencing an exact current row that already exists under the same Configured
Source and Source Unit. Storage validates its immutable content, semantic hash,
metadata, observed time, and any supplied profile, then uses the persisted row
as the effective Revision in the new projection payload. The carried path never
inserts a Revision. Historical projection-run retry treats an absent legacy
profile field as equivalent only to an explicit null field; every other payload
difference remains an immutable retry collision.

Text Fragments use exact half-open ranges in the immutable Observation Revision.
HTML list items, table rows, blockquotes, Markdown paragraphs, list items,
table rows, and code blocks may therefore be independently selectable while
mapping back to exact source characters. `canonical-record` receives whole-
Observation candidate authority so its schema compiler can decode fields before
emitting exact field or nested-text ranges; that does not make the whole record
a selectable fallback. A whole Observation Fragment is selectable only when its
versioned representation contract explicitly declares that Observation atomic.

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
  "primary_ref": "p000012",
  "required_refs": ["r000018"]
}
```

The selected catalog entry carries the `text` or `artifact` discriminator; the
model never returns Observation ids, offsets, Evidence text, hashes, profile
names, or lifecycle actions. `primary_ref` is required and singular.
Its structured schema accepts only `pNNNNNN`. `required_refs` is an ordered,
duplicate-free list accepting `pNNNNNN` or `rNNNNNN`, and may mix text and Artifact
entries with the Primary when all entries belong to the same offered catalog,
Configured Source, Source Unit Revision, and access context. The resolver sorts
the durable Required set by canonical Fragment order before hashing, so model
array order is not business identity.

The prompt presents `primary_candidates` and `required_only_candidates`
separately. If a durable claim is stated only by Required-only historical
Context and no Primary candidate directly states it, the model must return an
empty `memories` array. This prevents a routine current delta from being used
merely as a pretext to re-extract a durable historical claim.

Provider output can redundantly repeat a Required ref or repeat the singular
`primary_ref` inside `required_refs`. At the LLM candidate-admission boundary,
the application removes Primary from Required and de-duplicates Required by
first occurrence exactly once; the Resolver then applies canonical Fragment
order. The Resolver itself retains duplicate rejection for every direct or
non-LLM caller. This repair does not choose, guess, or widen a reference.
Unknown, malformed, stale, cross-catalog, inaccessible, and Primary-ineligible
refs still fail closed.
Normalization emits only a bounded removed-ref count and fingerprint, never
Evidence text or raw transient refs. A well-formed selector and its resulting
Evidence Unit identity remain unchanged. Runtime evaluator contract 3 classifies
a successfully normalized and resolved selector as accepted while retaining its
degraded normalization reason for operational visibility.

Application code determines Primary capability without semantic LLM
classification. The model determines which bounded Context is actually
Required. Typed model refs make that capability structural in the schema;
Resolver eligibility validation remains defense-in-depth and never repairs an
invalid selector. No dynamic per-catalog enum is required. The presentation
policy has a separate version in v9 Source Derivation input identity so a
corrected same-revision batch is not silently reused. It does not change
Fragment coordinates, catalog digest, Evidence Unit identity, or lifecycle
state. Legacy v8 derivation identity remains unchanged.

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

One managed claim may be rendered as several adjacent Markdown structures, for
example paragraphs followed by a list or code block. This remains one claim and
one Evidence Unit. The Resolver first prefers one compiler-owned Fragment that
contains the exact claim range. When none exists, it deterministically selects
the smallest source-ordered, non-overlapping Fragment set whose union covers
every non-whitespace character in that range; the first Fragment is Primary and
the remaining Fragments are Required parts of the same Unit. Any uncovered
content, ambiguous range, ineligible role, or cross-Revision set fails closed.
The event receipt records the exact revision range for this multipart case. It
does not widen Evidence to the whole Observation, introduce quote matching, or
turn structural pieces into independent claims.

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
  claim may select a supplied Artifact as Primary. The selected Fragment must
  be Primary-eligible for the current work.
- **Required** is necessary for the claim to stand or retain its meaning. The
  model may select any exact current Fragment presented in the candidate
  catalog, including bounded Context that is not Primary-eligible. Merely
  helpful material is not Required.
- **Context** assists interpretation and resource inspection but does not
  support the claim or independently trigger invalidation. Application planning
  chooses bounded Context; the model may promote a selectable Context Fragment
  only to Required. Unselected or display-only Context is not a member of the
  immutable supporting Evidence Unit, and the model does not return Context
  references.

Primary and Required are jointly necessary evidence for one claim. This is one
fixed domain invariant, not a configurable Boolean expression language. The
design adds no nested evidence expressions, `N_OF_M` policy, fragment lifecycle
state, or general-purpose Support rules. If one candidate appears to need
multiple independently claim-bearing Primary references, extraction normally
splits it into atomic Memories instead of widening the Evidence model.

The application does not statically decide whether bounded Context is Required.
It decides only Primary eligibility. This preserves deterministic extraction
authority while leaving semantic necessity to the model inside one exact,
bounded, fail-closed catalog.

## Evidence Unit and Support

The existing Evidence Unit is deepened as the claim-level aggregate. Its
identity includes the stable Source Unit id, claim content hash, complete
resolved Primary/Required part-set digest, and access context. The target Source
Unit Revision is retained as construction and audit scope, but is not identity:
a Context-only Observation revision may change that aggregate Revision without
changing any supporting part. Compiler profile,
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
presentation hash, display excerpt, target Source Unit Revision,
Fragment/catalog reference, catalog digest,
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
   rows additionally require non-empty removal times. The Unit's pinned
   `SourceUnitRevision` must belong to the same `SourceUnit`, and every
   supporting Reference Revision must be a member of that pinned Unit Revision;
   otherwise the group is `unit_revision_lineage_invalid` and remains
   legacy-limited rather than failing during apply.
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

### Recovery of preserved legacy-limited Support

Post-cutover recovery never edits, relabels, or reactivates the archived v1
Unit, References, or Support rows. A still-active Memory may gain authority
only by attaching a newly materialized Evidence Unit pinned to one exact
stored-current `SourceUnitRevision`.

Two inputs share the same final v2 validation and `ATTACH_SUPPORT` mutation:

- A mixed text/Artifact group that failed only because the cutover classified
  every Reference from Unit-level provenance is reconstructed per Reference.
  Each Observation Revision's declared representation profile decides whether
  the part is text or an Artifact; all bytes/ranges and Artifact digests must
  verify exactly.
- A group whose historical Unit Revision row is absent is not mechanically
  repaired. The current stored Unit is compiled into the ordinary transient
  Fragment catalog. A structured LLM returns `supported`, `not_supported`, or
  `inconclusive`; only `supported` may select one Primary and zero or more
  Required catalog references. The application resolver validates those refs
  and materializes new revision-pinned parts. The model never supplies durable
  ids, Evidence text, historical membership, or a lifecycle action.

The structured response schema represents those three decisions as explicit
discriminated variants. `supported` requires `primary_ref` in the provider-facing
JSON Schema, while `not_supported` and `inconclusive` cannot carry selectors.
This conditional contract must not exist only in a post-response validator,
because such a validator can reject output that the provider was told was valid.
An exhausted `invalid_response` is scoped to its exact transient batch and does
not skip independent batches or Source Unit scopes. A provider or logical
deadline failure may stop further calls for that Source invocation to avoid
amplifying an unavailable dependency; every unexecuted item remains explicitly
inconclusive. Reports retain only content-free terminal category and error code.

Recovery is a support-only maintenance operation. It cannot emit UPDATE,
SUPERSEDE, REMOVE_SUPPORT, RETIRE, or Review mutations. `not_supported`, an
unusable catalog, unavailable current authority, invalid model coverage, or an
invalid selector leaves the Memory and legacy group unchanged and remains in
the immutable recovery report. Terminal Memories are history and are never
reactivated. An already-active v2 alternative is reported without mutation.

The report identity covers Memory version, current support-set hash, current
Unit Revision, access context, catalog digest, disposition, and selected
transient refs. Apply loads that exact persisted decision manifest under the
existing per-Source lifecycle maintenance fence; it does not ask the LLM to
repeat its semantic judgment. Application code reloads the complete current
candidate set, recompiles each deterministic catalog, requires the stored
catalog digest, resolves the stored transient refs, and rebuilds mechanical
parts. Any changed candidate coverage, revision, Memory version, Support
topology, access context, catalog, or selector makes the report stale before a
mutation. Ordinary Plan stale guards then enforce the same snapshot again at
commit. A matching inactive v2 Support is historical removal and must never be
reactivated by recovery. SQLite and HANA use this same contract and persist the
dry-run in the existing support-cutover report facility; no recovery state
machine, historical Source replay, or separate replay ledger is introduced.

Recovery reports carry a selector contract version. Version 1 preserves the
original one-call catalog identity. Version 2 records the complete Corpus
digest and final global refs after either the one-call fast path or exhaustive
windowed selection. Exact-report apply recompiles only the versioned Corpus and
resolves the persisted final refs; it never reconstructs window transcripts or
calls the LLM. Existing version-1 reports remain immutable and replay against
their original compiler limits.

Version 3 admits current inference-eligible image Artifacts into that same
Corpus only after the shared Projection image loader reads the exact stored
bytes, verifies the revision-declared length and SHA-256 digest, and supplies
the image to the structured call. Each Artifact catalog entry exposes the
transient Fragment ref together with the image's model-input label so the model
can select the ref without returning a durable Observation identity. Window
screening and final adjudication receive only images represented by the
Fragments in that exact payload. The persisted report retains the Corpus
digest and selected refs, never image bytes or model transcripts. Exact-report
apply reconstructs a version-3 Corpus from unchanged current revision metadata
and resolves those refs without reading Artifact bytes or calling the LLM;
metadata or catalog drift makes the report stale. Version-1 and version-2
reports retain their original text-only semantics.

A recovery report may additionally declare one explicit, sorted, duplicate-free
Memory-id cohort. The cohort is part of immutable report identity and narrows
candidate loading before any catalog compilation or LLM call. Replay and apply
must find every requested Memory in the same configured Source, retain every
legacy candidate group belonging to each requested Memory, and compare only
that exact group set; a missing or cross-Source Memory, duplicate requested id,
or changed candidate makes the report stale. An absent cohort preserves the
historical whole-Source report contract and still requires complete Source
candidate coverage. This is a maintenance request boundary, not lifecycle
batching, a new Support state, or permission to omit an incumbent from ordinary
reconciliation. Operator CLIs accept the cohort only while creating a report;
apply derives it solely from the persisted report and never asks the LLM again.

Legacy Support recovery is transitional maintenance, not the steady-state path
for new Memories. Once the support marker is `evidence-unit-set-v2`, ordinary
extraction and reconciliation create v2 Evidence Units and Support Assertions
directly. The shared Projection image loader is long-lived extraction
infrastructure. The recovery CLI, report preparation, and apply orchestration
remain only until an exact inventory proves zero active legacy-limited groups,
no unapplied recovery report or active recovery job remains, and SQLite/HANA
strict audits converge through one compatibility window. A later bounded
cleanup may then remove those executable maintenance entry points while
preserving historical report rows and the minimum read-only parser needed for
audit; it must not delete or rewrite lifecycle history.

## Revision and lifecycle semantics

Fragment references never survive their catalog and are never followed across
revisions. A new Source Observation or Source Unit Revision produces a fresh
catalog. Durable Evidence keeps only resolved Observation Revision identities,
Anchors, exact source-derived text or Artifact metadata, roles, and part-set
hashes.

When a Revision Delta is proven Disjoint from every Primary and Required
Anchor, the current Evidence Unit remains valid. An Affected or Unknown result
creates one revalidation work item for the complete unit. The work item compiles
a fresh catalog from the target revisions. Its current authorized work includes
the current or rebound incumbent claim range and any affected supporting ranges
that the revalidation must prove; an unchanged incumbent Primary may therefore
remain Primary when only a Required part changed. The work presents the
incumbent claim and old resolved Evidence as comparison context and resolves a
complete new Primary/Required set or an explicit unsupported/unknown result. It
never maps an old transient Fragment reference into a new catalog. A provider-backed
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

NOOP revalidation scopes v2 incumbents by Evidence Unit id; the legacy v1 path
continues to scope by Evidence Reference id. For every affected Unit, the
application recompiles each current supporting Observation through its declared
representation. A structured support judgment that accepts changed Required
material receives one transient selector per affected Required Reference and
must return one exact current presentation quote for every selector. Distinct
Required References retain distinct selectors even when they belong to the same
Observation. Revalidation first groups supporting parts by Evidence Unit id. A
single Unit is rebound as one indivisible alternative; multiple independent
Units in the same affected Source Unit are not flattened or arbitrarily chosen.
Until the lifecycle operation shape can replace several alternatives atomically,
that case is typed ambiguous and preserves every incumbent Support through
Review. The shared representation compiler maps decoded canonical-record
quotes, including escaped newlines, quotes, and Unicode, back to exact raw JSON
ranges; lifecycle code never tests decoded presentation text against raw record
content. The catalog Resolver then materializes the complete Unit. Expected
ambiguous or unpresentable selection stages the existing Review-safe outcome;
compiler or resolver contract violations propagate as failures rather than
being misclassified as lifecycle Review. The shared Unit-support postcondition
remains transactional and fail-closed but is causal rather than global. A Plan
is rejected when it introduces stale or incomplete Support, leaves invalid
Support in its own Source Unit, or consumes stale cross-Unit Support to
authorize a destructive decision. A structurally valid historical Support
owned by another Unit does not block a support-preserving write that neither
mutates nor consumes that edge. Creating a pending Review is support-preserving
because its proposed mutations remain staged. The unrelated stale edge remains
ineligible for destructive authority and visible to lifecycle audit until its
owning Unit handles it.

One prepared Source Unit commit therefore has three execution dispositions:

- **APPLIED** commits the complete atomic Plan;
- **DEFERRED** rolls back and returns exact content-free cross-Unit blocker
  identities when the Plan depends on Support whose owner may still commit in
  the same Source run;
- **REJECTED** rolls back malformed lineage, self-introduced staleness, changed
  Memory or access authority, and every conflict that cannot safely converge.

These are commit dispositions, not Memory lifecycle states. A Deferred attempt
retains one same-process Prepared Lifecycle Intent containing the already
resolved Evidence, semantic operations, identity decisions, and exact initial
Support-to-owner topology. After normal per-Unit and authoritative tombstone
processing completes, the Source orchestrator may rematerialize only declared
blocker-owned Support changes, stale guards, and the deterministic Plan, then
perform at most three ordered commit-only convergence rounds. It never repeats
extraction, candidate admission, reconciliation, entity or identity model work.
Only blockers owned by Units in the same run are eligible; any round with zero
successful commits stops immediately. The Unit Plan remains atomic across all
its Memories, and an unresolved dependency remains failed. No dependency graph,
durable retry queue, replay ledger, source-type branch, or weakened destructive
authority is introduced.

The external MemoryEngine seam exposes only:

```text
prepare_and_commit_projected_lifecycle(...)
  -> applied stats | Deferred(handle, blocker owner ids) | Rejected

retry_deferred_projected_lifecycle(handle, eligible same-run owner ids)
  -> applied stats | Deferred(new handle) | Rejected
```

The Deferred handle is opaque. Initial Support ownership, declared-owner
accumulation, authority hashes, Plan rematerialization, idempotency, and attempt
accounting remain private to MemoryEngine. GeneSyncOrchestrator owns only the
eligible Unit/tombstone set and the bounded round/no-progress policy. It never
reads or mutates prepared topology state.

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
apply it only when the target revisions and semantic preparation authority
still match. Within the same process, a Deferred Prepared Lifecycle Intent may
accept only Support topology and derived Memory timestamp/corroboration changes
caused by its declared same-run blockers; Memory content, status, visibility,
owner, validity, gate, or access-context changes reject it. A process restart
discards the transient intent and falls back to ordinary durable derivation
recovery. It never recompiles under a newer profile while pretending to resume
the old batch, and no replay ledger or fragment lifecycle state is added.

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

`evidence[]` is the sole Memory-detail provenance projection. Each projected
Unit carries its canonical document/resource locator, while Direct User and
other application-authoritative Virtual Documents use an explicit document
group with no fabricated Observation, Revision, Evidence Reference, or Source
Unit identity. Artifact summaries remain selection hints only;
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
- **Let the model assign any role to every presented Fragment** — rejected
  because unchanged Context could become the Primary for a newly extracted
  claim. Requiring only that some selected reference intersects current work is
  also insufficient: an unrelated current Fragment could be added as Required
  while an old claim remains Primary.
- **Map generic Source relation types to Required authority** — rejected because
  ordering, reply, containment, and reference edges identify useful bounded
  Context but do not prove that the Context is necessary for one claim. The
  application determines only Primary eligibility; the model selects necessary
  Required refs from the bounded catalog.
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
contract records fragment/compiler and authority/segmentation-policy identity,
selected role counts, attempted Primary eligibility, a content-free selection
fingerprint, resolved
part ranges and hashes, and explicit rejection or review reasons without
persisting source text in runtime events.

Changing which ranges are Primary-eligible changes batch admission semantics.
The manifest and catalog digest must therefore carry an authority-policy or
extraction-contract discriminator so completed work under an older policy is not
silently reused. No new persistent Fragment, Context, or lifecycle state is
introduced.

This ADR defines design and acceptance semantics only. It does not authorize
source re-ingestion, historical Memory rewriting, lifecycle repair, automatic
reassessment of prior events, or deployment.

## References

- [Detailed source-agnostic extraction design](../design/source-agnostic-memory-extraction.md)
- [Implementation umbrella: shno-labs/mem-forge#303](https://github.com/shno-labs/mem-forge/issues/303)
- [Profile and compiler slice: shno-labs/mem-forge#305](https://github.com/shno-labs/mem-forge/issues/305)
- [Selection and resolver slice: shno-labs/mem-forge#306](https://github.com/shno-labs/mem-forge/issues/306)
- [Evidence-Unit Support slice: shno-labs/mem-forge#307](https://github.com/shno-labs/mem-forge/issues/307)
- [Grouped retrieval/evaluation slice: shno-labs/mem-forge#308](https://github.com/shno-labs/mem-forge/issues/308)
- [Cloud HANA rollout slice: dodoman-sun/memforge-cloud#391](https://github.com/dodoman-sun/memforge-cloud/issues/391)
- [Legacy-limited Support recovery: shno-labs/mem-forge#316](https://github.com/shno-labs/mem-forge/issues/316)
- [Budgeted Fragment Corpus selection: shno-labs/mem-forge#329](https://github.com/shno-labs/mem-forge/issues/329)
- [Canonical whole-authority planning: shno-labs/mem-forge#363](https://github.com/shno-labs/mem-forge/issues/363)
- [Generic multi-window extraction: shno-labs/mem-forge#365](https://github.com/shno-labs/mem-forge/issues/365)
- [Artifact-aware legacy Support revalidation: shno-labs/mem-forge#332](https://github.com/shno-labs/mem-forge/issues/332)
- [Exact recovery Memory cohorts: shno-labs/mem-forge#335](https://github.com/shno-labs/mem-forge/issues/335)
- [ADR 0007: Bind extracted evidence to the current Source Projection](0007-bind-extracted-evidence-to-the-current-projection.md)
- [ADR 0010: Keep the support provenance projection complete](0010-keep-support-provenance-projection-complete.md)
- [ADR 0014: Model binary Artifacts as revision-pinned Source Evidence](0014-model-binary-artifacts-as-revision-pinned-source-evidence.md)
- [ADR 0028: Separate conversation coverage from content and retention](0028-separate-conversation-coverage-from-content-and-retention.md)
- [CommonMark: HTML blocks are raw Markdown regions](https://spec.commonmark.org/spec#html-blocks)
- [W3C Web Annotation Data Model selectors](https://www.w3.org/TR/annotation-model/#selectors)
