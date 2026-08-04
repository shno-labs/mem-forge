# Bind extracted evidence to the current Source Projection

Extractor-provided Source Observation identities are localization hints, not evidence authority. The current Source Projection and its revision-pinned content are authoritative. A hint outside the changed evidence scope may be rebound only when the extracted quote has exactly one exact match in the current candidate Observations; missing or ambiguous matches fail closed.

This rule lives in the shared evidence-localization module and does not branch on provider type. Valid in-scope hints must still contain the quote, and revalidated no-op evidence retains its explicit current-revision validation. The same contract therefore applies to document-based and conversational sources without weakening changed-scope ownership.

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
an exact quote from the current revision, the engine must not invent or
approximately bind Evidence. It stages the exact incumbent Support change
through the existing lifecycle Review gate, keeps the old Support active while
that Review is pending, and continues the otherwise complete Source Unit plan.
Provider unavailability or a model's inability to copy one exact quote is
therefore an item-level unresolved Evidence decision, not an exception that
invalidates every independently proven decision in the Source Unit. Internal
identity, coverage, and lifecycle-plan contract violations still fail the
derivation.

Agent-session patch intent is likewise a transient authority hint, not a second durable Evidence identity. After the claim is localized, its intent metadata and client identity are bound to the revision-pinned projected Evidence Unit. Relation Runs, current Evidence Relations, Evidence References, and Support Assertions for that claim must all use this one canonical Evidence Unit; a parallel intent-only unit may not become lifecycle authority.

Each claim retains its own canonical Evidence Unit, but that unit stores only the
claim-local exact quote or extraction context. The complete source text remains
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

Provider-returned `evidence_quote` is an untrusted localization proposal. Before
durable derivation output is staged, the shared Evidence localization module
validates that proposal against the immutable work scope and produces one
canonical claim Evidence excerpt or no inline excerpt. Accepted text is
preserved verbatim; the pipeline must not silently truncate it into a different
quote. A generous operational byte envelope may prevent an unbounded inline
payload, but exceeding that envelope omits or rejects the excerpt according to
the work contract instead of changing its text.

Changed-range work requires an exact current-revision quote that intersects the
authoritative changed ranges. An unavailable inline excerpt therefore rejects
that candidate and may activate the existing structural fallback. Structural
work retains its deterministic unit-ownership gate; projection-batch work
retains its Primary Observation gate. In those whole-scope cases an otherwise
valid claim may remain revision-pinned with `WHOLE_OBSERVATION` and
`NO_EXCERPT`, but the complete unit or Observation is not copied into claim
Evidence. Short atomic Observations may still be preserved verbatim when the
whole Observation is the actual claim Evidence. The Source Projection adapter,
not downstream source-type branching, declares that atomic Evidence scope in
Observation revision metadata. Artifact Evidence remains empty-text
`SOURCE_ARTIFACT`.

The canonical excerpt is the sole durable text authority for the claim.
`EvidenceUnit.content`, `EvidenceUnit.excerpt`, `MemorySource.excerpt`, and the
deprecated compatibility field `Memory.extraction_context` are all derived
from that same value. The provider may not independently populate
`extraction_context`, and downstream code may not use
`evidence_quote or extraction_context` fallback selection. The compatibility
field remains temporarily to avoid coupling this correctness change to a
cross-adapter schema migration; its removal is tracked separately.

Legacy cutover follows the same storage rule. An exact legacy excerpt may be
preserved, while lineage that lacks one uses empty `LEGACY_LIMITED` Evidence.
Cutover must never copy a complete Source Observation Revision into each
backfilled Evidence Unit. During cutover a Memory may temporarily retain more
than one active Primary Support; the audit treats it as mapped when any active
Primary exactly pins its Observation's current revision, rather than depending
on storage return order.

## Revision-range localization

A Primary exact quote that occurs exactly once in the authoritative current
Observation Revision is materialized as a half-open `REVISION_RANGE` Anchor.
An empty, missing, or repeated quote remains a conservative
`WHOLE_OBSERVATION` Anchor. Required and contextual references also remain
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
