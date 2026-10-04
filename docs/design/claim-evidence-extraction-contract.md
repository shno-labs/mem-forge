# Claim and Evidence extraction contract

Status: proposed, design version 3, 2026-10-04. Implementation and online
acceptance are not implied by this document. This proposal is the completion
contract for subsequent implementation and validation, subject to the design
review recorded in the accompanying validation report. Quality thresholds in
section 9 were explicitly approved by the user on 2026-10-04. The input/selection
architecture is a hypothesis to compare, not an already accepted constraint.

## 0. Architecture decision: does catalog-first extraction earn its complexity?

"Every Memory has citations" describes the stored result, not how the model must
produce it. Primary and Required describe semantic contribution; neither requires
a menu of preselected Fragments. Parsing/indexing source material remains
necessary for provenance regardless of the model-facing representation.

The first design version inherited catalog-first without a comparative decision.
The user explicitly challenged that premise. Before implementing more selection
rules, compare these two complete alternatives under the same outcome contracts:

| | A: catalog-first | B: source-first |
|---|---|---|
| Model reads | Complete natural structural reading with application-defined selectable view IDs | Complete natural structural reading organized by authenticated Observation/declared source field; no preselected evidence-snippet menu |
| Model returns | Claim + one Primary view ID + additional Required view IDs | Claim + one Primary exact-quote selector + additional Required exact-quote selectors |
| Initial source binding | Known ID resolves to a compiler-proven selection | Program uniquely locates the quote in the named supplied source region and proves its native origin/interpretation |
| Evidence extent | Chosen from safe predefined views | Derived from claim-specific exact selections and source-proven structural interpretation |
| Advantage to test | Low output overhead; explicit eligible candidates and deterministic binding | Less preselection bias; claim-specific quotations and natural reading without catalog noise |
| Risk to test | Precut evidence too broad/narrow, catalog clutter, unnatural attention to IDs, selection/reading/matching conflation | Misquotes, duplicate ambiguity, missing native coordinate maps, extra output tokens, unsafe partial-structure selections |

Both produce the same immutable Evidence/Support contracts. A source region in B
is an authored record or declared body field, not an old Fragment with its `p...`
name removed. A paragraph/row marker added solely to offer a fixed evidence menu
would be a variant of A and must be labelled that way.

### B's compact selector and resolution

Use the existing compact claim fields but replace the selector fields with:

```json
{
  "primary_evidence": {"region_id": "body-1", "exact": "verbatim source text"},
  "required_evidence": []
}
```

The model may supply verbatim prefix/suffix only to disambiguate an actual
repeated quote; it never emits source offsets, native hashes or rewritten proof.
`region_id` identifies source scope during this request, not a durable citation
identity. The program checks quote equality, both native binding and supplied
reading, source authority and structural completeness. A quote about an unrelated
old assertion does not become new authorized work because it is easy to locate.

The compiler must map the selected visible text to native source ranges/fields
and supply necessary source-bound framing. Finding the words in a rendered
document is not sufficient. Finding a quote only in an added label does not
prove an authored statement. A syntactically partial selection is expanded only
by a declared deterministic structural rule, preserving the selected quoted text
and the added interpretation; no semantic rewrite or evidence guessing is used.

An unbound/misquoted/ambiguous selector is an explicit technical failure. Its
candidate and failed document remain in the evaluation denominator. It is not
silently discarded or replaced with a convenient catalog ref. Current atomic
derivation semantics prevent partial publication. Independently from binding,
reviewers assess whether the exact quote actually supports the claim.

After binding, future correspondence uses the source-owned selection identity,
canonical material and interpretation contract in section 6, not the model's
quote string as the sole matching key. Duplicate handling and outside-selection
impact remain mandatory in B.

### Decision experiment and rule

Implementation feasibility comes before the paid semantic comparison. The
catalog contract was chosen deliberately to make exact source selection
application-owned; its reliable addressing is not an accidental constraint to
remove. ADR 0030 records why HTML/table-sensitive quote copying and whole-Block
fallback were rejected. That is a design rationale, not fresh A/B measurement.

The static audit establishes the following starting point:

| Seam | A: concrete reusable implementation | Additional work B needs |
|---|---|---|
| Native coordinate binding | DeclaredTextFragment native start/end; canonical JSON decoded-to-raw map; exact source anchors and digests | Reverse map from arbitrary visible substring through XML/HTML/entity/rendering transformations to exact native origins |
| Historical selection reconstruction | support_reading locates the old compiled selection by its exact anchor and canonical content | Reconstruction of a selected quote that is not an existing Fragment; canonical subselection lookup without enumerating all substrings |
| Structural interpretation | Declared groups and complete row/paragraph/code views | Safe interpretation of partial dynamic selections; no semantic guess about omitted negation, labels or list order |
| Work authority | Existing range-indexed eligible refs | Resolve quote origins first and verify each actual core range against the same authority map |
| Output and completeness | Compact IDs; existing planner and resolver | Longer quoted completions and additional failure surface; fail complete work rather than silently dropping misquotes |

The draft's native parser exports complete selection ranges and canonical
values; it does not export a general reversible visible-character source map.
Its matcher requires an old compiled-fragment anchor. Therefore B is not a
prompt-only replacement, and an easy Markdown demonstration cannot establish
its Confluence/Jira feasibility. Expanding every quote back to the same existing
fragment may test different claim formation but does not prove finer Evidence.

**The implementation baseline is A.** First determine whether its observed
defects follow from representation/framing and input policy, or from an inherent
preselection limitation. Readability, adapter locality and stable matching do not
require abandoning A. No source-first production implementation is authorized
by this comparison document.

Advance B to a paid comparison only after a bounded, real-native technical
feasibility demonstration proves its additional seams with a small maintainable
interface and without a second parser framework, substring catalog, semantic
closure graph or fallback to A. If that proof needs substantial speculative
infrastructure, reject B for this scope and record the tradeoff. A source-first
semantic-only experiment is not architecture acceptance.

Freeze common adapter source material, structural reading, authority, model
route, compact claim fields and quality rules. Change only model-facing evidence
selection and its defined deterministic resolver. Evaluate each arm on complete
real sources, not one favorable excerpt or only easy plaintext. Do not implement
a production switch, dual pipeline, source-specific preferred mode or rescue
path between arms.

For A, use coherent readable views rather than intentionally broken old raw
macro rendering. For B, verify every emitted quote's native mapping, and count
unmapped quotes as failures rather than semantic success. This separates the
architecture comparison from the old renderer regression. Compare faithfulness,
useful coverage, Primary/Required quality, binding failures, output limits and
implementation depth/locality. Original main remains a separately labelled
regression baseline; it is not the sole fair architecture comparator.

Choose B if its feasibility gate passes and it meets the accepted criteria with a materially simpler or more
accurate result and complete native binding. Choose A if its constraints improve
quality/binding enough to justify the selection-menu cost. If neither passes,
the one-pass design is unaccepted; record the falsified assumption and discuss
the next architectural choice instead of inserting a repair step. Do not declare
the architecture selected on schema-valid output or a plaintext-only trial.
Equivalent quality favors A's already reliable binding and lower implementation
and token cost. A failing semantic experiment does not automatically justify B:
both use an LLM and either can infer an unsupported conclusion.

The remaining sections define common outcome/ownership/lifecycle requirements.
References to catalog IDs specifically describe A. B retains authorized reading
and exact resolution but uses the selector above. The eventual release installs
one selected design, not both experimental arms.

## 1. Outcome and scope

Every published Memory has a self-contained, useful claim and authentic,
revision-pinned citations that a reader can understand. A citation points to
exact retained source material; readable formatting does not determine its
identity. A later source revision preserves correspondence for unchanged,
unambiguously identifiable material. A corresponding citation does not, by
itself, prove that the whole claim remains valid.

Required selection is best effort. We accept missing supplementary references
when the claim remains accurate and the Primary is meaningful. We do not
optimize for a minimum reference count, demand perfect Required recall, or
discard useful claims to make a citation metric improve.

This work covers source framing, representation, claim extraction, text Evidence
selection, correspondence, Support integration, storage and tool/UI delivery.
It uses the existing Source Projection, Evidence Unit, Support and Lifecycle
Plan domain records. It adds no claim-verifier pipeline, repair model, new
lifecycle states, durable Fragment catalog or dependency graph subsystem.

Multimodal image understanding and new image-reference delivery are deferred
under [issue #497](https://github.com/shno-labs/mem-forge/issues/497).
Existing Artifact identity and visibility contracts remain in force. Text may
state an authenticated caption; it may not invent unseen image contents or
silently replace existing pixel Evidence with a filename or caption.

Shared behavior belongs in OSS. Cloud implements the same storage and retrieval
contracts; it does not supply source-specific parser fixes. This proposal does
not authorize merging, deploying or reprocessing live workspaces.

## 2. Runtime flow and responsibilities

```text
complete provider snapshot / explicitly bounded update
  -> source adapter: scoped identity, retained native facts, framing, coverage
  -> immutable current Projection + committed baseline
  -> representation compiler: source selections, interpretation, comparisons
  -> work planner: authorized claim work + complete structural reading
  -> one semantic extraction per existing planned request
  -> deterministic resolution of returned catalog refs
  -> existing Support / relation / atomic Lifecycle Plan
  -> stored immutable Evidence -> get_memory / resource / UI

new revision
  -> adapter + compiler, with the same comparison contract
  -> exact correspondence for incumbent Evidence
  -> whole-Support change assessment when required
  -> existing atomic Lifecycle Plan
```

The following responsibilities must remain separate even if one private module
implements several of them:

| Responsibility | Owner | What it must not infer |
|---|---|---|
| Provider identity, timestamps, author, edit/delete/reply, snapshot completeness | Source adapter and collector contract | Semantic claim truth from an API timestamp or adjacent message |
| Native syntax, field meanings, generated navigation, supported format grammar | Source adapter; standard-format parser may be reused | Generic regex rules guessing which provider produced text |
| Exact raw ranges, declared selections, readable views and comparison values | Representation compiler consuming adapter declarations | Final Primary/Required roles or claim truth |
| Changed/added work and permitted context | Existing work planner | Authority from topic relevance or request packing |
| Claim, central evidence and supplementary contribution | Extraction model | New provenance, arbitrary coordinates or external issue resolution |
| Ref validity, immutable binding, access and stale guards | Evidence resolver / existing stores | Semantic repair or silent removal of inconvenient candidates |
| Whole-claim validity and lifecycle decisions | Existing Support and Lifecycle modules | Unaffected claim merely because one local ref matched |

Central registration and dispatch may name adapters. Native parsing and field
policy must live behind the adapter interface, not in that dispatch or generic
utility bodies. Confluence storage macros are Confluence grammar, including
embedded Jira macros; Jira issue/comment payload grammar belongs to Jira.

### Current implementation gaps, before changes

The main baseline is `57f8b006`; the prior draft is `879ddd9d`. Main conflates
raw structural serialization with citation presentation and explicitly asks
for scope headings as Required. The draft removes that prompt instruction and
introduces adapter-owned native Confluence/Jira contracts and separate comparison
values, but has not passed complete semantic acceptance. Teams framing and
ordering, managed-session generated structures and full native Jira comment
collection have not been accepted against this contract.

The existing multi-provider projection dispatcher still builds some provider
records itself. An adapter-owned builder or declaration is needed wherever it
encodes provider semantics. Moving already neutral registration or standard
Markdown algorithms into each adapter would duplicate implementation and is
not a repair.

## 3. Input and adapter interface

Reuse the existing projection interface. Its result must retain:

* scoped immutable Source Unit and Observation identity;
* original native material needed to interpret and verify the revision;
* versioned representation contract and deterministic comparison semantics;
* authored body and authenticated framing, each bound to retained source fields;
* explicit structural relationships, original effective-date facts when supplied;
* exact collection coverage, access scope, edit/delete facts and source times.

The collector must not substitute converted Markdown for native XML/JSON while
declaring a native profile. Reconstructed display titles are labels, not new
authored body. Authenticated identity/framing is available for attribution, but
its value must retain immutable provenance if a claim asserts it.

### What can enter the selectable catalog

Authored substantive text, meaningful source fields and source-proven structures
can be selected. A heading may state substantive knowledge. Identity, author,
time or history can contribute to a claim, but their availability does not make
them automatically Primary or Required.

Pure generated navigation, transport controls and generated citation wrappers
remain provenance/display metadata rather than authored claim evidence when the
adapter can identify them from a native construct or managed format declaration.
The word "Citations" or a JSON-looking sentence alone does not prove a wrapper.
Unrecognized material must not be deleted by a general text-pattern heuristic.

Current facts and historical old/new values are visibly distinguished. Historical
values remain available where history is authorized; they are not presented as
current facts. Redundant current-body copies may be omitted only with an exact,
source-proven duplicate relationship that preserves historical boundaries.
History volume is not itself grounds for deleting history.

### Source-specific requirements

| Adapter | Required behavior |
|---|---|
| Confluence | Parse retained storage XML/custom elements directly; render status titles, issue keys and authored bodies; omit verified bodyless navigation; preserve nested code, list/table scope, links, annotations and empty/unknown status without fabricating values. |
| Jira | Retain native values and explicit supplied rendered bodies together; distinguish issue core, comments and history; preserve authored old/new values and their times; render syntax under Jira's declared format; edits/deletions and partial comment/history pagination must be represented accurately. |
| Teams | Preserve message identity within conversation/channel/thread scope, sender and correctly named source times; keep quoted/authored text distinguishable; retain authenticated reply links. A chronological reading order is not proof of reply or supersession. |
| Markdown/HTML repositories and pages | Use declared standard format; retain headings, code, links, tables and lists. Source identity/front matter must not become claim text simply because a normalizer prepended it. |
| Managed agent sessions | Identify generated envelopes and citation metadata through the capture format; preserve authored conversational knowledge and its event provenance. Authored technical JSON/code remains substantive. |

The Teams adapter must not use `lastModifiedDateTime` as a body-edit timestamp:
reactions can change it. Jira comments are editable and deletable, not append-only.
Provider declarations do not excuse ignoring access changes or incomplete input.

Unsupported meaning-bearing native grammar is a typed representation limitation,
not a silently flattened success. Harmless format details may be ignored only
by a documented adapter comparison rule. Unsupported material must not be used
to infer authoritative absence or retire incumbent Memories.

## 4. Reading, selection and presentation

### Complete reading

Preserve complete syntactic meaning: table associations, list order and lead-ins,
message boundaries, relevant supplied reply context, definitions and governing
scope. The compiler exposes these structures to the existing planner. A message
is read with its authenticated framing; its several independent assertions need
not become one inseparable citation.

Reading context does not automatically become selected Evidence. Reading more
of a source does not widen Primary authority. No source is summarized, truncated
or partially sampled and then reported as a complete successful extraction.

### Selectable citation views

Prefer a focused, complete source-proven view when it is equally meaningful.
Keep a larger complete view when a safe smaller one is unavailable. A table row
can display source-bound column labels. An ordered instruction retains necessary
ordering context. A message paragraph can display source-bound sender/time
framing. These views do not invent evidence or ask the LLM to reconstruct source.

Displayed framing or labels are compiler-produced interpretation with an exact
origin in the retained revision and a versioned reconstruction contract. The
binding audit must cover every displayed factual value, not just the central
raw range. Changes to interpretation are visible to Support assessment even when
the central selected text itself is unchanged.

There is no unconditional "headers, footnotes and exceptions become Required"
rule. They are included in a readable view only when needed to interpret it,
or selected as supplementary Evidence when they actually support a distinct
part of the final claim. A dependency already fully supplied with Primary is
not selected again merely because it has another catalog ref.

### Text presentation invariants

Presentation preserves original statements, code text and associations. It may
decode markup, expose native field labels and remove verified presentation
controls. It may not paraphrase conclusions, infer dates or reconcile ambiguous
annotations. Raw material and its immutable hashes remain available separately.
Raw `ac:`/JSON control syntax must not leak into ordinary readable excerpts.

All logical citations remain represented in get_memory even if their complete
text is opened through pinned resources. An excerpt budget must disclose
incompleteness; it must not silently drop Required identities or switch to the
latest source revision. Rendering details and matching versions are distinct.

## 5. Claim and reference extraction

Use the existing compact output fields: content, memory_type, entity_refs,
valid_from, valid_until, primary_ref and required_refs. Model-facing refs are
opaque, request-local selectors. Do not ask the model to emit raw spans, hashes,
rewritten evidence, lifecycle actions, or a repeated per-clause proof schema.

The model writes the final claim and selects its evidence in the same response.
There is no second self-review call, admission-time semantic rewriting, automatic
Primary promotion, or Required pruning to compensate for a weak extraction.
Candidate Admission retains its independent value and same-round deduplication
duties, followed by existing relation work. Its `evidence_incomplete` entailment
rejection/reselection duty is removed for this design: a missing supplementary
ref must not erase an otherwise accurate useful claim. The shared admission
prompt/schema and work-manifest expectations must change explicitly, rather
than leaving candidate-admission-v5 behind the new extraction contract. Raw
extraction is evaluated before value/deduplication can alter its denominator.
Incumbent whole-Support assessment remains a separate lifecycle duty. It must
assess the whole current claim/source, not treat a previously omitted optional
Required ref as proof that the knowledge was unsupported.

### Claim contract

One Memory expresses an independently useful conclusion with material scope,
conditions, exceptions and modality. A connected procedure or inseparable
decision/reason may stay together. Independent conclusions that can change
separately remain separate. Neither another Memory nor a citation supplies a
material qualification omitted from the claim itself.

A proposal stays a proposal, an expected result stays expected, and a linked
remedy is not a proven completed fix. Authored disagreements or unknown outcomes
remain explicit. No inference about external issue resolution is allowed unless
that resolution was supplied as authenticated, authorized source material.
Effective dates describe authored effective boundaries, not merely source update,
message creation, report or reference dates.

### Primary contract

Exactly one eligible view directly supports the central conclusion. It need not
prove every supporting detail. A substantive heading, a decision or explicit
approval may be Primary; a decorative title, unrelated recent message or citation
link list is not Primary merely because it is eligible.

An explicit current approval may establish the decision while its authenticated
referent supplies the decision's parameters as Required. This is a new decision
asserted by the approval, not origination of the old proposal merely because it
was nearby. Without a proven referent the model must preserve the ambiguity.

### Required contract

Select additional refs only for confident contribution to a stated part of the
final claim or metadata beyond what Primary and its source-proven interpretation
already supply. Conditions, definitions, reasons or other procedural steps can
contribute. Topic similarity, ancestry, a duplicate occurrence, or "might be
helpful" background does not suffice.

An empty list is valid. Supplementary recall is best effort; no exact dependency
closure or smallest-set search is required. A missed supplementary citation does
not authorize omission of a known material condition from the claim. No hard
reference-count cap applies.

### Generic extraction instruction for A

The production instruction should express the following single contract; source
syntax instructions come from the adapter's declared interpretation:

```text
Extract independently useful claims from the authorized source material.
Preserve each claim's material scope, conditions, exceptions, order and whether
it states a proposal, requirement, expectation, observation or completed change.
State uncertainty as the source states it; do not invent resolutions or dates.

Choose one eligible Primary directly supporting the central conclusion.
Choose a focused complete view when available; a complete broader view is valid.
Select Required only when it adds confident support for a specific part of the
final claim or metadata beyond Primary and the supplied source interpretation.
Do not repeat included labels, duplicate evidence or merely related background.
Empty Required is valid; supplementary-reference recall is best effort.
Keep supported useful knowledge; do not shorten coverage to reduce citations.

Respect the catalog's authority. Read-only context can interpret a new assertion
but cannot become unrelated new claim work. Return only the existing compact
claim fields and supplied refs. Never create evidence text or source coordinates.
```

### Source-neutral examples

| Source structure | Correct behavior |
|---|---|
| A rule says "P applies when C"; a separate section defines C | Keep C in the claim. The rule is Primary; the definition may be Required if the claim uses it. A general document heading is not automatically selected. |
| A row view already labels an outcome as expected | Preserve expectation. Do not also select the same header solely to repeat "expected". |
| An authenticated reply explicitly approves a referenced proposal | Approval can be Primary for the decision; referenced proposal supplies parameters as Required. A nearby unlinked message does not establish that relationship. |
| A note associates a successful outcome with a possible remedy | State the association/uncertainty actually supplied; do not assert completion, causation or an external issue's resolution. |

These examples test relationships and modality, not Confluence, Jira or any
single document vocabulary. Held-out evaluation must include other structures.

## 6. Cross-revision correspondence

### Stored binding and separate comparison

Each selected Evidence part retains its Source/Unit/Observation identity,
immutable revision, raw coordinates and integrity, representation contract,
readable presentation integrity and access context. Reconstruct comparison and
interpretation from that exact retained revision, never from the latest body.
The binding audit already shows one required extension for composite text views:
store one typed `text_view` descriptor on resolved and persisted text Evidence
parts. It contains a stable view kind, versioned view contract and exact
interpretation-origin anchors with raw integrity. The immutable source revision
already supplies native profile/schema; do not duplicate those fields.

Origins cover compiler-added labels/framing, not arbitrary semantically related
paragraphs. They are application-owned provenance for this view, never model
output or a new Required role. Prefer same-Observation origins; cross-Observation
substantive evidence remains explicitly selected Primary/Required, not hidden in
a view descriptor. Each retained view contract deterministically reconstructs
the core and origins and verifies the stored presentation. Matching separately
reconstructs canonical core material under the source comparison contract.

Round-trip this descriptor through derivation results, Lifecycle Plan, Evidence
identity, SQLite/HANA, Support and delivery using a shared versioned JSON field
on the existing reference record. Old nullable descriptors mean the historical
simple-view contract, not permission to invent origins. Preserve registered old
view contracts. If historical reconstruction is genuinely unavailable, preserve
the old excerpt/history and report unavailable correspondence; never substitute
the latest renderer. This is one binding descriptor, not a persistent catalog
or semantic dependency graph.

Matching uses an adapter-defined, versioned canonical structure/content value.
It does not use readable text equality, LLM paraphrase, semantic similarity or
an offset copied from a previous revision. Render-only upgrades do not change
comparison values. Canonicalization ignores only declared harmless syntax;
code whitespace, links, authored annotations and meaningful native attributes
must retain their declared semantics.

### Deterministic algorithm

1. Verify old material, exact selection, profile, Source/Unit/Observation and
   access. Build complete old/new representation indexes once.
2. Compare same-identity observations and compatible contracts. Index selection
   kind and canonical content values; verify equality after fingerprint lookup.
3. Resolve a unique occurrence on both sides, or use an authenticated stable
   structural identity to disambiguate repeated content. Sibling offsets and
   incidental parser positions are not stable identities.
4. Bind to the verified target coordinates. Separately account for changed
   interpretation, governing context and removed/added material in Support.
5. Return exact correspondence, changed/removed material, or an explicit
   ambiguous/unavailable result. No fuzzy best guess becomes exact evidence.

Two identical old occurrences collapsing to one new occurrence are not a unique
old-to-new correspondence. Equal words do not prove which physical occurrence
survived. Ambiguous material may need whole-Support assessment; it must not be
silently mapped or treated as proof of disappearance.

### The achievable guarantee

With a fixed comparison contract, unchanged uniquely identified source selections
must correspond after offset shifts, insertion of unrelated material and declared
render-only changes, independently of document size. The acceptance suite must
prove this for all eligible selections in each frozen document, not just the refs
chosen by the model.

There is no unconditional guarantee for arbitrary duplicate text without stable
identity, missing old material, changed semantic context, unsupported format or
an incompatible comparison contract. Recognizing ambiguity is the accurate
result. This is a limitation of source identity, not an excuse to guess.

The user accepts one upgrade reprocess if old/new representation contracts are
incompatible. Historical Evidence remains immutable and readable under its
retained contract. Future supported revisions use the stable new comparison
contract; changing that contract again requires explicit compatibility evidence
or another disclosed reprocess, not an invisible migration.

## 7. Incremental and lifecycle contract

Retain existing added/changed Primary authority. Complete structural reading
must not convert unrelated old assertions into new claim work. An incorrect
Primary is not repaired by promoting Required-only text. Investigate any missing
new claim against the exact run authority and the existing incumbent Support
assessment before proposing an authority-contract change.

The authority calculation must compare declared native text structures as well
as nested standard text. A changed JSON body field is not proof that every
native paragraph/row in that field changed. Compare compiled core material and
its meaning-bearing source interpretation; authorize the affected views. Do
not infer new work from offset shifts or mechanically grant the entire native
field merely because it has a declared text-format parser instead of a
`nested_profile`. Unknown occurrence identity is not proof of exact unchanged
material or permission for unrelated new assertions. This is shared compiler/
planner behavior, with native meaning declared by adapters.

Changed framing or qualifiers must participate in the relevant current work and
Support impact assessment; they cannot be ignored because body text matches.
Any material claim update originates through the existing whole-Support path.
Reprocess explicitly authorizes the selected current revision.

Unit Title remains a human-facing display label. It can no longer substantiate
new claim facts without pinned evidence. Author, title, type, identity or time
asserted in content or used as factual interpretation belongs in the immutable
native Observation representation; a meaning-bearing change participates in
revision identity, comparison and Support impact. Pure display aliases do not
create claim work. This explicitly supersedes ADR 0034's current permission to
state mutable Unit Title values as unsupported facts and its exemption of all
title-only changes from semantic work.

Dropping retired Required parts cannot silently turn a previously supported
claim into deterministic reuse. Incompatible claim-bearing contracts require the
bounded upgrade reprocess or existing explicit unresolved assessment. Historical
Evidence stays verifiable and no unsupported absence/retirement is inferred.

Exact correspondence and whole-claim validity are separate. No content change
with verified unchanged interpretation permits existing deterministic reuse.
Changes outside selected refs still undergo the existing impact/whole-Support
assessment. Partial coverage cannot establish deletion. Stale/version/access
checks, idempotency, same-source destructive coverage and cross-source authority
remain unchanged. One atomic Lifecycle Plan applies all accepted work together.

Malformed refs or integrity/authority violations are technical failures. They
must be surfaced, not silently cleaned into semantic success. No new semantic
candidate-rejection rule is introduced to make poor model outputs disappear.

## 8. Large documents and execution limits

Index complete immutable structures once and reuse that index for correspondence,
reading and verification. Request catalogs are bounded presentations of exactly
planned work, not the master comparison index. No unbounded quadratic pairwise
match search or model-assisted matching is needed.

Preserve the existing approved request-planning/executor contract. Packing is a
transport detail, not a new business state or a new definition of a claim.
Every authorized selection belongs to one planned work item; complete structural
context remains available. Do not add batching, split schemas, raise a cap or
halve work to make a failing model path pass. A newly proposed change to those
limits requires alternatives and user confirmation first.

The compact schema avoids repeating claim meaning for each citation. A truncated
response is a failed request; no partial success, recovered JSON suffix or extra
continuation-generated citations are published. Capacity evidence is recorded
separately from semantic errors and coverage.

## 9. Validation fixed before experiments

Freeze the design version, code versions, source bytes, source-profile contracts,
work authority, model route/configuration, prompts and output schema before each
acceptance experiment. Preserve untouched responses and failure artifacts.
Do not overwrite prior runs. Private source and secrets stay outside Git.

### Cohort

Use complete real native Confluence and Jira inputs, including a real comment
path before claiming comment acceptance; a real Teams conversation with
authenticated framing and relationships; managed-session material; and held-out
Markdown/HTML documents. At least one large, complex document must exercise
planning/capacity as well as all-selection correspondence.

The previously tuned Confluence page is a regression source, not the held-out
proof of generality. Existing normalized snapshots cannot certify native parser
behavior. Controlled revision edits are labelled controlled; authentic consecutive
provider revisions are labelled authentic. A missing source prerequisite is
reported as unverified, never replaced by a synthetic fixture and called real.

### Acceptance matrix

| ID | Contract and falsifiable check | Pass condition |
|---|---|---|
| A1 | Native collection and profile declaration | Complete input/coverage and immutable framing agree with adapter declaration; no invented native data. |
| A2 | Adapter locality | Source grammar/field semantics reside in the owning adapter; shared pipeline consumes declarations. |
| A3 | Full compiler integrity | Every selection and every displayed factual value binds to pinned source; code/structure preserved; no raw control markup masquerades as readable evidence. |
| A4 | Reading/work authority | Every authorized selection planned once; no skipped semantic work, context-authority expansion or missing structural interpretation. |
| A5 | Claim faithfulness | No accepted critical/major unsupported conclusion, lost material condition, invented modality/date or external resolution; report minor precision findings separately. |
| A6 | Useful knowledge coverage | At least 95% of adjudicated independent useful-claim inventory covered per source family; no material branch/guard omitted; no benefit from silent admission pruning. |
| A7 | Primary relevance | Every accepted Primary directly supports the central assertion in its authenticated interpretation; eligibility alone is insufficient. |
| A8 | Required quality | At least 95% of selected supplementary refs make a distinct relevant contribution across the cohort; report counts and per-source values. No recall/minimum-count target. |
| A9 | Correspondence | All unchanged unique/stably identified selections correspond under declared insertion/reordering/format transformations; all ambiguity, changed semantics and corrupt source guards behave correctly. |
| A10 | Outside-ref changes | Modified headers, qualifiers, exceptions, framing, effective boundaries and removed text trigger correct whole-Support outcomes even when selected text matches. |
| A11 | Source lifecycle and stores | Edit/delete/partial coverage/access/stale/idempotent cases agree between OSS/SQLite and HANA at the user-facing seam. |
| A12 | Citation delivery | get_memory, resource and UI preserve same revision/roles/visibility; complete pinned text is available and excerpt limits are explicit. |
| A13 | Large/execution behavior | Full declared work fits existing planner or reports typed capacity failure; no success through truncation or unapproved workload changes. |
| A14 | Upgrade/reprocess | Exact bounded dry-run and explicit cutover preserve old history and establish new future-revision contracts; no fake provenance. |
| A15 | Product acceptance | Checked CF deploy and named smoke evidence for changed cloud runtime before release; source-only/model-only replay is not deployment acceptance. |

95% targets are user-approved cohort acceptance criteria, not production probability
guarantees. They permit occasional supplementary-reference mistakes rather
than claiming perfection. Serious unsupported assertions and wrong central
citations remain release blockers. Reviewer inventories need adjudication of
equivalent wording, duplicates and materiality; no reviewer is a perfect oracle.

### Independent evaluation

Two fresh reviewer contexts first inventory each full source without candidates,
design, prompt, variant identity or peer judgment. Only after inventories are
frozen do they review anonymously ordered untouched model outputs with full
source and exact citation bindings. They report every candidate and source-family
coverage. Root adjudicates disagreements from the source and publishes both
reviews and reasons; it does not choose a favorable reviewer.

Use the actual online CF-configured Sonnet route. Record model identifier,
endpoint/factory/configuration identity, usage, attempt counts, limits and source
hashes with credentials redacted. Baseline and candidate receive the same real
cohort and workload. Structured JSON success is not evidence entailment.
Fixture tests prove structural contracts only.

### Order and stop rule

1. Review this design, audit A/B technical feasibility and current main/draft against A1–A15. Resolve
   contradictory design assumptions before code or paid extraction experiments.
2. Build only the source reading/selector/binding experiment justified by the feasibility audit,
   using verified modules where they satisfy the contract. Native binding is a
   prerequisite; a semantic-only quote trial is clearly labelled preliminary.
3. Execute a frozen real-source main/refined-A Sonnet comparison and blind
   review; include B only if its technical feasibility gate passed. No candidate
   repair/filtering or model self-review is included.
4. For a failure, record the acceptance ID, source/candidate evidence, falsified
   assumption and classification: design defect, implementation violation,
   ambiguous source, provider/runtime failure or historical data.
5. Change the design first when its assumption is false; revise the owning
   implementation when the contract is sound. A parser counterexample belongs
   to its adapter, not a new generic prompt instruction.
6. Freeze a new version and reverify the affected seam and existing fixed cohort.
   Preserve a held-out source before semantic retest. Stop when acceptance
   converges; do not expand cohorts without a named uncovered risk.

If a one-pass extraction cannot meet the agreed quality target on the frozen
cohort, report that design as unaccepted and discuss the smallest architectural
alternative. Do not continue indefinitely with per-sample wording patches or
quietly introduce a reviewer/repair model into production.

## 10. Implementation and release plan

Implementation follows the matrix, not a source-specific patch list:

1. Validate A as the implementation baseline and apply section 0's feasibility
   gate before pursuing a replacement; then
   confirm reuse of draft native parsing/comparison against A2/A3/A9; establish
   framing and supported-format declarations for remaining sources.
2. Integrate interpretation, author/time provenance and meaningful/generated
   field distinction behind adapters; update shared compiler/catalog contracts
   and all affected tests/stores together.
3. Install one compact generic extraction instruction and preserve existing
   output fields, authority and complete executor work. No semantic repair stage.
4. Verify whole-Support outside-ref impact and pinned historical delivery in
   OSS and Cloud, then perform the frozen online/independent semantic evaluation.
5. Update canonical OSS ADRs for validated material decisions. Cloud ADRs cover
   only cloud-specific consequences. Open PRs for each changed repository.
6. After design acceptance and deployment authorization, follow the checked CF
   prepare-deploy path, smoke tests and bounded reprocess/cutover contract.

Old PRs #495/#545 retain their negative evidence and draft status. This design
does not assume their full implementation is accepted, nor discard their tested
parsers simply to start over. No merge happens without the branch/PR audit.

## 11. Alternatives and durable decisions

* **Readable text as matching identity:** rejected; renderer changes and repeated
  text can cause false matches and misses.
* **All headings/history excluded or every message one ref:** rejected as a
  general rule; the same structure can be substantive or contextual, and
  reading granularity need not equal citation or comparison granularity.
* **Catalog-first as an unquestioned architecture:** rejected; precise source
  storage does not dictate how a model reads or selects its evidence.
* **All exact context becomes Required:** rejected; source interpretation and
  supplementary semantic contribution are different responsibilities.
* **Admission promotion/pruning or self-review repair:** rejected for this work;
  it obscures extraction defects and can drop useful knowledge.
* **LLM/Fuzzy correspondence:** rejected; source identity must remain auditable.
* **A new fine-grained semantic graph/schema:** rejected; existing projection,
  source declarations and Evidence/Support contracts suffice unless a named
  seam audit proves otherwise.
* **Source-specific generic prompt examples:** rejected; adapters own native
  grammar while the generic prompt states claim/evidence principles.

The design retains the existing distinction between local correspondence,
whole-Support validity, authorized new work and atomic lifecycle effects.
It supersedes assumptions that raw serialization is necessary for precise
citations, that structural ancestry requires Required selection, or that
unchanged selected text proves an unchanged claim.

## 12. Sources and related contracts

* [ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md): compiled
  revision-pinned Evidence and exact authority.
* [ADR 0034](../adr/0034-unify-incremental-support-and-claim-assessment.md): whole
  Support assessment and existing lifecycle; this proposal modifies no destructive gate.
* [Source-agnostic extraction](source-agnostic-memory-extraction.md): current
  runtime; conflicts with this proposed contract are listed in the validation audit.
* [Confluence storage format](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html).
* [Jira Data Center REST](https://docs.atlassian.com/software/jira/docs/api/REST/9.12.2/): comment update/delete and rendered expansion.
* [Graph chatMessage](https://learn.microsoft.com/en-us/graph/api/resources/chatmessage?view=graph-rest-1.0): scoped identity and source times.
* [Graph chat list](https://learn.microsoft.com/en-us/graph/api/chat-list-messages?view=graph-rest-1.0) and [channel list](https://learn.microsoft.com/en-us/graph/api/channel-list-messages?view=graph-rest-1.0): ordering and reply collection limits.
* [W3C Web Annotation selectors](https://www.w3.org/TR/annotation-model/#selectors): selecting source material is distinct from a complete application revision/identity contract.
* [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs): schema validity is not semantic entailment.
