# Bind extracted evidence to the current Source Projection

Extractor-provided Source Observation identities are localization hints, not evidence authority. The current Source Projection and its revision-pinned content are authoritative. A hint outside the changed evidence scope may be rebound only when the extracted quote has exactly one exact match in the current candidate Observations; missing or ambiguous matches fail closed.

This rule lives in the shared evidence-localization module and does not branch on provider type. Valid in-scope hints must still contain the quote, and revalidated no-op evidence retains its explicit current-revision validation. The same contract therefore applies to document-based and conversational sources without weakening changed-scope ownership.

When a revised Primary Observation still appears to support an incumbent
semantically but structured validation cannot return an exact quote from the
current revision, the engine must not invent or approximately bind Evidence.
It stages the exact incumbent Support change through the existing lifecycle
Review gate, keeps the old Support active while that Review is pending, and
continues the otherwise complete Source Unit plan. A model's inability to copy
one exact quote is therefore an item-level unresolved Evidence decision, not an
exception that invalidates every independently proven decision in the Source
Unit.

Agent-session patch intent is likewise a transient authority hint, not a second durable Evidence identity. After the claim is localized, its intent metadata and client identity are bound to the revision-pinned projected Evidence Unit. Relation Runs, current Evidence Relations, Evidence References, and Support Assertions for that claim must all use this one canonical Evidence Unit; a parallel intent-only unit may not become lifecycle authority.

Each claim retains its own canonical Evidence Unit, but that unit stores only the
claim-local exact quote or extraction context. The complete source text remains
stored once in the authoritative Source Observation Revision, and the Evidence
Reference pins the claim to that revision. A claim without localized text stores
empty Evidence Unit content and uses `NO_EXCERPT`; it must not claim
`SOURCE_EXCERPT` authority. This prevents lifecycle plans and Evidence storage
from multiplying one large Observation by the number of extracted claims while
preserving the complete revision-pinned audit path.
