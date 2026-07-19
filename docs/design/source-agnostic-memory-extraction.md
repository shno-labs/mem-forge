# Source-Agnostic Memory Extraction

MemForge keeps source-specific behavior at the projection boundary. A provider
adapter owns how raw source data becomes stable Source Units, Observations, and
normalized artifacts. After that, memory extraction, candidate selection,
reconciliation, support management, review gating, and lifecycle/index writes
use the shared pipeline.

## Core Rule

```text
Projection adapters customize source identity and observation structure.
The memory pipeline stays centralized and reusable.
```

This means future sources such as GitHub Pages, local markdown repositories,
Slack, Outlook, or code-review systems should not need their own memory
extraction strategy. They should produce clean normalized markdown and let the
shared update planner decide between diff-guided extraction and full-document
fallback. Full-document extraction still uses deterministic structural units
inside the shared pipeline; source genes do not choose or implement those units.

## Normalization Contract

Each source type should normalize into markdown with these properties:

- deterministic section order
- stable headings for repeated source fields
- no fetch-time-only noise such as sync timestamps
- operational metadata separated from memory-bearing content
- comments, messages, revisions, or events sorted by source timestamp or stable id
- source wording preserved when modality matters, such as proposals, open
  questions, decisions, or rejected options

Example Jira shape:

```markdown
# [Story] PAY-123: Cutoff flow

## Source Metadata
- Status: In Progress
- Assignee: Alice
- Sprint: Payroll 42

## Description
...

## Acceptance Criteria
...

## Comments
### 2026-05-20 Alice
...
```

Example local markdown repository shape:

```markdown
# docs/cutoff-flow.md

## Repository Metadata
- Commit: abc123
- Branch: main

## Document
...
```

## Shared Update Strategy

For any updated source item with previous normalized markdown:

```text
small normalized diff -> diff_guided extraction
large normalized diff -> full_document extraction over deterministic units
missing previous content -> full_document extraction over deterministic units
diff-guided extraction failure -> full_document extraction over deterministic units
```

The planner is intentionally source-agnostic. `source_type` and `doc_type` are
prompt context, not strategy selectors.

## Full-Document Structural Units

Full-document mode means the whole normalized document is eligible for memory
extraction, not that the LLM receives one unbounded document blob. The shared
pipeline deterministically turns normalized markdown into extraction units:

```text
normalized markdown -> heading tree -> extraction units -> unit-level extraction
```

The rule is source-agnostic and deterministic:

- split on real markdown headings, ignoring headings inside fenced code blocks
- keep the whole normalized document as one unit when it fits the configured
  unit input budget (`max_unit_input_tokens`, currently 20,000)
- recursively split only oversized section subtrees, using child headings as
  the next ownership boundary
- keep parent preamble text as its own unit when a parent section must split
- preserve heading-path ownership for every unit
- split only oversized units with the shared overflow rule
- never use source-specific chunking in a gene

Each unit receives read-only context:

```text
document title
document URL
source_type and doc_type
heading path
resolved entities
document outline
glossary appendix
unit markdown
```

The outline and glossary can resolve scope, acronyms, and references. They are
not memory-bearing ownership zones. A model candidate must declare
`evidence_anchor = "unit"` to pass the ownership boundary check. Evidence
quotes remain useful for audit/provenance display, but raw quote containment is
not the hard gate because rendered text can differ from markdown syntax.

Unit identity is transient. It is not persisted on memories or source-support
rows. Persistence keeps the normal memory, source excerpt, source document, and
support kind. Unitization diagnostics stay in the audit event payload.

## Diff-Guided Extraction Contract

Input:

```text
source_type
doc_type
changed_hunks
full updated normalized markdown
resolved entities
same-document extracted memories
```

Extractor responsibility:

```text
Extract only durable memory changes caused by changed_hunks.
Use the full updated document only for context and quote validation.
Return [] for formatting-only or operational metadata-only changes.
```

The prompt is not the authority boundary. For every returned candidate, the
pipeline requires an exact current-revision evidence quote that overlaps an
inserted or replaced range. Candidates grounded only in unchanged context are
rejected and counted in the extraction audit. A deletion-only diff grants no
new-candidate authority; reconciliation owns incumbent removal. If the diff
cannot fit the prompt budget, the planner selects `full_document` instead of
silently truncating its authority.

For a document represented by one persistent Observation, a safe small diff
takes precedence over token-splitting that Observation into extraction batches.
Provider-native multi-Observation sources keep changed-Observation batching.

Operational metadata includes status, resolution, assignee, sprint, rank, labels,
timestamps, participants, reactions, and edit time. These fields can still be
used as context, but they should not become memories unless the changed text
explicitly states a durable decision, constraint, procedure, or architectural
fact.

## Candidate Durability and Uniqueness

All extraction batches for one Source Unit revision are aggregated before any
Memory write. The shared pipeline then applies two separate policies:

```text
all batch candidates
  -> deterministic durability gate
  -> deterministic exact-duplicate collapse
  -> complete semantic CandidateLedger
  -> incumbent reconciliation
  -> atomic lifecycle plan
```

The durability gate rejects provenance bookkeeping such as attachment uploads
and routing-field history. A claim extracted from the actual content of an
attachment is different: it may pass when its evidence points to that content
artifact. The gate is shared and never switches on provider type.

CandidateLedger owns only within-revision uniqueness. It receives candidate
index, memory type, self-contained content, and Observation identity. It does
not receive the full document, Evidence quote, incumbent Memory ledger, or
provider payload, and it never rewrites candidate content. Its only actions are
`KEEP` and `DROP_REDUNDANT -> canonical_index`.

The semantic ledger must return exactly one valid decision for every candidate.
An incomplete ledger receives one corrective retry. A second invalid response,
more than 200 non-identical candidates, or more than 100,000 serialized input
characters fails closed: no candidate is written and no destructive incumbent
lifecycle action is authorized. Exact duplicates are collapsed before these
semantic budgets are applied.

## Lifecycle Boundary

The shared lifecycle rules remain unchanged:

```text
MemoryEngine owns extraction/reconciliation decisions.
MemoryStore owns SQLite, FTS5, Chroma, rollback, and lifecycle side effects.
ReviewService owns human-gated approval/rejection.
```

New source types must not bypass these boundaries with direct memory writes.

## Audit Expectations

Every update should record:

```text
document_update_strategy_selected
memory_change_extraction_completed, when diff-guided extraction runs
  (including current_changed_range_count and
  rejected_outside_changed_range_count)
memory_extraction_completed, with unit_count, segmentation_version,
partition_strategy, and max_unit_input_tokens for full-document units
candidate_ledger_completed, when multiple or exact-duplicate candidates are selected
candidate_ledger_failed, when a complete bounded ledger cannot be proven
reconciliation_failed, when reconciliation returns no safe lifecycle decisions
reconciliation_decision_returned
reconciliation_authority_rejected, when needed
reconciliation_review_gated, when needed
lifecycle/index side-effect events from MemoryStore
```

The audit trail should make the strategy visible regardless of source type.

## Open Optimization Question: Cross-Document Checks

Large source documents can create many new memories. Cross-document
contradiction detection currently checks entity-overlap candidates after insert
and should have enough response budget for large structured outputs.

Future optimization needs a careful design pass before changing behavior:

- whether to batch contradiction candidate pairs by token budget
- whether to cap candidates per new memory, and what ranking signal should own
  that cap
- how to balance lower failure blast radius against repeated prompt overhead
- how failed batches should appear in the audit ledger

No candidate capping rule is finalized yet. The current short-term fix is to
avoid an obviously too-small response budget for contradiction detection.
