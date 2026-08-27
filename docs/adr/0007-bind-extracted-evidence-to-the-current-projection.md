# Bind extracted evidence to the current Source Projection

Amended 2026-08-27 by [ADR 0030](0030-compile-revision-pinned-evidence-fragments.md).
The revision-pinned authority and transient-selector decisions remain in force.
ADR 0030 supersedes the single Block ID, provider-returned `evidence_quote`,
quote matching, and whole-Block fallback contract described below.

Amended 2026-08-12 to make batch-local Evidence Block identity the textual
admission authority and make provider-returned quote text an optional precision
hint rather than an exact-copy gate.

Amended 2026-08-20 to complete that transition: every new textual structured
response must carry one valid transient Evidence Block ID. Projection responses
use mutually exclusive textual and binary-Artifact variants; an Artifact claim
selects its supplied Source Observation and cannot carry textual quote or Block
authority.

Extractor-provided Source Observation identities are localization hints, not
Evidence authority. The current Source Projection and its revision-pinned
content are authoritative. New textual extraction binds through a valid
batch-local Evidence Block whose application-owned mapping selects the Source
Observation. New model output cannot use quote-only admission. Completed durable
derivation payloads remain Block-ID-free because the transient address has
already been resolved to exact current-revision Evidence before persistence.

This rule lives in the shared Evidence Catalog and localization Modules and does
not branch on provider type. A valid Block remains authoritative when its
optional quote cannot be refined, while revalidated no-op Evidence retains its
explicit current-revision validation. The same contract therefore applies to
document-based and conversational sources without weakening changed-scope
ownership.

When only Required Evidence changes, revalidated no-op Support may retain an
unchanged, revision-pinned Primary `WHOLE_OBSERVATION` with `NO_EXCERPT`.
An exact current-revision quote is required only when the Primary itself must
be re-anchored; the engine must not add a model dependency merely to replace
already valid whole-Observation authority with a range.

Rebinding an equivalent claim from old Support to current-revision Support is
one atomic no-op lifecycle action. While the Configured Source lifecycle gate
is enabled, the planner removes the old Support and attaches the validated new
Support in the same Plan. While the gate is closed, the planner stages those
exact mutations in the existing Lifecycle Review and leaves the incumbent and
its old Support active; it must not fail the complete Source Unit or bypass the
gate merely because the Memory content is unchanged.

When a revised Primary Observation requires semantic revalidation but the
structured provider cannot return a valid decision, or reports support without
a valid current-revision Block selection, the engine must not invent or
approximately bind Evidence. It stages the exact incumbent Support change
through the existing lifecycle Review gate, keeps the old Support active while
that Review is pending, and continues the otherwise complete Source Unit plan.
Provider unavailability or a model's inability to select valid Evidence is
therefore an item-level unresolved Evidence decision, not an exception that
invalidates every independently proven decision in the Source Unit. Internal
identity, coverage, and lifecycle-plan contract violations still fail the
derivation.

Agent-session patch intent is likewise a transient authority hint, not a second durable Evidence identity. After the claim is localized, its intent metadata and client identity are bound to the revision-pinned projected Evidence Unit. Relation Runs, current Evidence Relations, Evidence References, and Support Assertions for that claim must all use this one canonical Evidence Unit; a parallel intent-only unit may not become lifecycle authority.

Each claim retains its own canonical Evidence Unit, but that unit stores only the
claim-local exact excerpt or bounded Block fallback. The complete source text remains
stored once in the authoritative Source Observation Revision, and the Evidence
Reference pins the claim to that revision. A claim without localized text stores
empty Evidence Unit content and uses `NO_EXCERPT`; it must not claim
`SOURCE_EXCERPT` authority. This prevents lifecycle plans and Evidence storage
from multiplying one large Observation by the number of extracted claims while
preserving the complete revision-pinned audit path.

The public `get_memory` contract preserves that claim-local text Evidence after
the normal caller-visibility filter has been applied. MCP compaction therefore
keeps each source's `excerpt` together with its source and resource locators,
and keeps Artifact Evidence as separately fetchable metadata. It does not inline
the complete Source Observation Revision. Callers can inspect the claim's exact
support without multiplying or transferring the full document for every Memory.

## Canonical claim Evidence excerpt

Every textual extraction work item builds a provider-neutral Evidence Catalog
after work planning has established its owned authority. The Catalog divides
only selectable current Source text into bounded Blocks and gives those Blocks
deterministic IDs inside the immutable batch. The model selects one Block ID;
application code validates that address against the exact Catalog that was sent
and immediately resolves it to current Source text. Block IDs are transient
prompt addresses: completed derivation output stores only the resolved exact
excerpt and revision-pinned Source Anchor, so later segmentation changes cannot
reinterpret durable Evidence.

Changed-range work catalogs only inserted or replaced current ranges. The rest
of the updated document may remain read-only context but has no selectable Block
ID. Projection work catalogs only Primary Observations, while structural and
full-document work catalog only their owned bounded text. The same Catalog
Module serves every source Adapter after Source Projection and work planning;
provider-specific Block identity is neither required nor allowed.

For textual Evidence the selected Block is required admission authority. The
structured response schema, not prompt wording alone, enforces that every new
textual candidate selects exactly one Block. Projection Artifact candidates are
a separate schema variant: they select one supplied binary Artifact Observation
and cannot provide a textual quote or Block ID. An optional
`evidence_quote` may narrow the excerpt inside that Block through exact or
conservative representation-only canonical matching, including Markdown escape,
link, Unicode punctuation, and whitespace differences. A successful refinement
is mapped back to the exact Source characters. A missing or unlocalizable quote
does not reject a valid Block selection: the exact bounded Block becomes the
non-empty canonical excerpt. A missing or invalid Block ID fails structured
response validation or admission; it cannot fall back to quote-only ownership.

Invalid structured-response recovery must preserve that authority rule. One
logical extraction call may use the shared bounded schema-transport fallback
and validation retry under the same deadline, but every recovered textual
candidate must still satisfy the Block-ID schema. Exhaustion records only
content-free validation diagnostics and leaves the durable derivation batch in
`retryable_failure`; a later recovery may resume that exact immutable batch
under its existing revision and stale guards. It must not admit the quote,
invent a Block, apply a partial lifecycle mutation, or reinterpret a schema
failure as whole-Block fallback. Whole-Block fallback is available only after a
valid Block has already established Evidence authority.

Textual extraction therefore does not use `NO_EXCERPT` as a recovery for model
copy differences. Binary Artifact Evidence remains the explicit non-textual
exception. A whole-Observation Anchor may still be necessary when the resolved
excerpt repeats in one revision, but its inline excerpt remains non-empty; Anchor
scope and public excerpt presence are separate concerns.

Whole-Block fallback is an admitted, observable quality outcome rather than an
extraction error. The shared derivation path records a content-free bounded
sample containing the Source Observation and revision identities, exact range,
candidate/Block/quote hashes and lengths, extraction contract, derivation,
Source Unit, and target revision identities. This signal survives derivation
replay and is emitted through the existing Memory audit seam. It never persists
the Block ID, source text, quote text, prompt, or Memory content. A cross-Block
quote check is deliberately deferred until production telemetry demonstrates
that models select one Block while quoting another; the fallback path does not
reject such candidates speculatively.

An explicitly scoped re-extraction of an unchanged current Source Unit may
select all of that unit's current inference-eligible Observations as Primary
work. This is a derivation instruction, not new Source truth: it must not invent
a semantic Revision Delta, replace the current Observation or Source Unit
revision, or bypass the ordinary Source activity and lifecycle stale guards.
The replay instruction is part of the derivation identity so its batches cannot
reuse an ordinary no-op derivation. Normal incremental Sync and full discovery
retain their existing change-driven extraction behavior.

The Evidence Catalog enforces its inline byte envelope while constructing
Blocks from Source text, rather than truncating provider output after the fact.
Changed-range work accepts only Blocks constructed from authoritative changed
ranges. Structural work retains deterministic unit ownership;
projection-batch work retains Primary Observation ownership. A textual claim
with a valid Block therefore always has a bounded non-empty excerpt. Artifact
Evidence remains empty-text `SOURCE_ARTIFACT`.

The canonical excerpt is the sole durable text authority for the claim.
`EvidenceUnit.content`, `EvidenceUnit.excerpt`, `MemorySource.excerpt`, and the
deprecated compatibility field `Memory.extraction_context` are all derived
from that same value. The provider may not independently populate
`extraction_context`, and downstream code may not use
`evidence_quote or extraction_context` fallback selection. The compatibility
field remains temporarily to avoid coupling this correctness change to a
cross-adapter schema migration; its removal is tracked separately.

## Revision composition

An automatic same-source UPDATE does not merge incumbent and candidate Evidence.
It is permitted only when relation-first reconciliation proves that one
challenger `REFINES` the incumbent, preserves every incumbent truth, represents
the same Memory identity, and is itself the complete canonical current claim.
The replacement content is the exact admitted candidate, so its normal
current-revision Primary and Required Evidence supports the whole revision.

This proof is transient and creates no `MemoryRevision` aggregate or additional
Evidence identity. If the candidate would require synthesized merged text, lacks
current localized Evidence, or is merely a sibling/narrower claim, UPDATE is not
authorized. The lifecycle-safe fallback retains the incumbent and admits the
original claim-sized candidate independently.

Legacy cutover follows the same storage rule. An exact legacy excerpt may be
preserved, while lineage that lacks one uses empty `LEGACY_LIMITED` Evidence.
Cutover must never copy a complete Source Observation Revision into each
backfilled Evidence Unit. During cutover a Memory may temporarily retain more
than one active Primary Support; the audit treats it as mapped when any active
Primary exactly pins its Observation's current revision, rather than depending
on storage return order.

## Revision-range localization

A Block-resolved excerpt is materialized from its application-owned half-open
range in the authoritative current Observation Revision, including when the
same text appears more than once. A legacy exact quote without Block coordinates
uses `REVISION_RANGE` only when it occurs exactly once; an empty, missing, or
repeated legacy quote remains a conservative `WHOLE_OBSERVATION` Anchor.
Required and contextual references also remain
whole-Observation authority because they do not claim that one quote alone
contains their complete support.

`STABLE_FRAGMENT` is reserved for provider-backed fragment identity with a
proven mapping across revisions. Markdown headings, offsets, and similar
derived structure must not be promoted to stable fragment identity by
guessing. Range overlap can prove affected or disjoint only when both sides
use the same Observation Revision coordinate space. A whole-Observation
change or a range from another revision therefore resolves to `UNKNOWN`;
lifecycle processing expands that uncertainty conservatively instead of
claiming false disjointness.
