# Record cross-document conflicts as relations, not Reviews

Status: Accepted

Date: 2026-09-25

## Context

MemForge compares one committed Memory against bounded candidates from other
Source Units after the Lifecycle transaction commits
([ADR 0009](0009-bound-cross-document-relation-discovery.md)). A contradiction
between two different Sources creates a pending Cross-Source Conflict Review.
Confirming or dismissing that Review changes neither Memory; search attaches a
warning for a confirmed or pending Review.

Production data from the Mount Tai workspace between 2026-07 and 2026-09 shows
three problems with that output:

- Of 86 resolved Reviews, 10 were confirmed and 76 were dismissed. The dismissal
  notes name the same causes: the two statements concern different tickets,
  runs, times, scopes, or intended versus observed behavior, so both can hold.
- 40 Reviews are still pending, the newest created on 2026-08-28. A queue that
  needs a human for every finding grows faster than anyone clears it, and a
  pending finding already shows as a warning in search.
- The confirmed conflicts fall into three kinds: knowledge that changed over
  time (a later decision, a renamed enumeration), a specification against
  observed behavior, and extraction errors (one ticket number attributed to two
  different bugs). Three of the ten came from different tickets of the same
  Jira Source, so the useful boundary is the Source Unit, not the Source.

Discovery also persists `EQUIVALENT` and directional `REFINES` edges that no
reader consumes.

## Decision

### Boundary

Relations between claims are judged where their authority lives:

| Relation | When | Why |
| --- | --- | --- |
| Same Source Unit | in the revision, before commit (Sparse Relation and SupportRelationCoordinator, ADR 0034) | the Unit may change its own Memories, so the outcome decides what commits |
| Same claim in another Source Unit | before creating a Memory (cross-document identity) | it decides whether to create a Memory or add Support to an existing one |
| Conflict or change across Source Units | after commit, asynchronously | a Unit has no authority over another Unit's Memories; the outcome is an annotation, and its candidates come from workspace-wide retrieval |

The rule is: a judgment whose outcome changes what this revision commits runs
before commit; a judgment that only annotates runs after it. Cross-document
discovery applies to every pair of Memories from different Source Units,
whether or not they belong to the same Source.

### One label per pair

Candidate retrieval stays bounded as in ADR 0009. Each (challenger, candidate)
pair receives exactly one label. The labels depend on whether the two
statements are about the same situation: they are only if they concern the
same object, the same scope, the same kind of statement (what should be, what
actually happened, or what was planned or decided) and the same occurrence.
Statements about different events or runs concern different occurrences;
statements about the same lasting state or decision concern the same one even
when their sources recorded them at different times, which is what makes an
`updates` pair possible. If any of these differs or cannot be established, the
pair is `none`.

| Label | Meaning |
| --- | --- |
| `none` | not the same situation, or the same situation with statements that can both hold without stating the same knowledge (for example, one is more specific than the other) |
| `equivalent` | same situation, and both state the same knowledge |
| `updates` | same situation, both cannot hold now, and the later statement replaces the earlier one |
| `contradicts` | same situation, both cannot hold, and neither replaces the other over time |

The label definitions are domain-neutral; no list of scope dimensions (version,
country, environment, ticket) is part of the contract. A requirement and an
observed behavior, a design and a defect, or two different runs are different
kinds of statement or different occurrences, so such a pair is `none`. When
the judgment is not certain, the pair is `none`: a false relation warns every
reader of both Memories, while a missed one only omits a hint.

For each Memory the classifier sees the statement, its memory type, the source
type and document title, the source revision time of its Primary Evidence, and
the Evidence text that supports it. The Evidence text is the anchored Fragment
text of the Primary and Required Evidence as Support Assessment reads it:
record fields in source order, each labeled by its JSON pointer so that the
fields of one array item stay together (a Jira comment body, each changelog
item's field, previous value and new value), never the stored raw record. The
source revision time (`RelationSubject.evidence_time`) is the `observed_at` of
the Observation Revision the Primary Evidence is anchored to, while that
revision is still current: the time the source itself gives that content (a page
version, a commit, a comment, a changelog entry, a message, an agent session
event; design `source-sync-to-memory.md` section 0.9). Every Source follows this
one rule. Where the anchored revision is no longer current or the source records
no time, the time is unknown, never a sync or submission time. The title, time
and Evidence are the inputs for deciding whether two statements are about the
same situation.

The Evidence text is only as narrow as the stored Anchor. A whole-Observation
Anchor shows the whole Observation, so a page or file Primary shows the whole
page or file, up to the Fragment catalog limits (`DEFAULT_MAX_FRAGMENTS`,
`DEFAULT_MAX_PRESENTATION_CHARS`); an Observation beyond them, an anchored
revision that is no longer current, and a non-text Primary such as an image
attachment show no Evidence text. Narrower Evidence comes from narrower Anchors
at extraction and Support, not from the classifier.

For `updates`, the program orders the pair by the same source revision time the
classifier sees for each Memory (`RelationSubject.evidence_time`); the model
does not choose the direction. A relation stores both times with its label, so
readers see the order and dates it was decided on. When the times do not order
the pair (either is unknown, or both fall on the same date), it is recorded as
`contradicts`. Directional `REFINES` is no longer recorded for cross-document
pairs.

### Executor

Cross-document relation is a classifier responsibility
([ADR 0036](0036-separate-semantic-work-from-inference-executors.md)): independent
pairs, one closed label each, sent through the LLM batch runner. Until a
classifier backend passes evaluation, the existing Structured LLM returns the
same four labels under the same contract and is instructed to return `none`
when unsure. A classifier backend applies a per-label confidence threshold below
which the pair is `none`. The threshold is a named contract constant whose
value and evaluation run are recorded with the classifier version; it is not a
configuration knob.

Evaluation uses a fixed set of human-labeled pairs: the confirmed and dismissed
Cross-Source Conflict Reviews of the workspace in which they were decided,
pinned under the offline evaluation mechanism
([memory-evaluation-mechanism](../design/memory-evaluation-mechanism.md)). Any
change of prompt, label definition, backend or threshold is evaluated on that
set before rollout, the same gate the Change Impact classifier uses. The set
holds workspace content, so it stays with the workspace's evaluation store and
is not committed to this repository. Each case pins the classifier input of
both Memories and the classifier contract version
(`cross-document-relation-v2`); a contract that changes the input is evaluated
on a set seeded again under it. The run report stays content-free, and a
maintenance operator reads each case's input, accepted label and the model's
label and reason for failure analysis.

### Relations are the output

A completed discovery run writes relations only. It creates no Review.

- `equivalent`: search returns one of the pair and names the other Memory's
  Source as agreeing. Neither Memory changes; merging identities stays the
  pre-creation identity step's job.
- `updates`: when both are retrieved, the newer Memory ranks ahead, and the
  older one carries a note naming the newer Memory, its Source and date.
  Neither Memory is retired or hidden.
- `contradicts`: whenever either Memory is returned, the other is attached with
  a warning, so the reader sees both statements, their Sources and dates.

A relation is attached only when the caller can see both Memories, using the
existing visibility-safe conflict read model. A relation is valid for the exact
content of both Memories. When either content changes, the relation stops being
current, and the next discovery for the changed Memory judges the pair again. A
Support change leaves the relation current, because the label describes the two
statements; its order and dates stay those it was decided on until discovery
judges the pair again. A Lifecycle write still owns authoritative Support relations and may
replace the whole projection; discovery never deletes or overrides them.

### People act at the point of use

There is no queue to clear. A person who sees a relation in search, in Memory
detail, or through an agent can:

- **Dismiss it** ("not a conflict", "not an update", "not the same"). The
  dismissal is stored for the pair, the label and both Memories' current
  content, with the actor and time. It hides that relation until either Memory
  changes, and it can be undone. Anyone who can see both Memories may dismiss;
  it only removes a hint and grants no lifecycle authority.
- **Correct or retire the outdated Memory** through the existing Memory
  Correction Proposal and retirement paths, under their own Correction Authority.
  An agent may propose the correction after the user states which statement is
  right; the user confirms it as for any correction.

The admin UI can filter Memories that currently carry a relation. It is a view,
not a work queue, and has no pending state.

### Failed and exhausted work

Bounded exponential retry stays as in ADR 0009. Exhausted discovery work is
visible: the admin API lists it with its last error, and a count is exported
with the worker metrics. An operator can re-run exhausted or completed
discovery work selected by error code, time range or classifier version, for
example after a defect is fixed or a new classifier version passes evaluation.
The re-run records the previous status and error in an audit event before the
work is leased again; the normal content, Support and access guards still
decide whether the work is current or obsolete.

### Migration

The Cross-Source Conflict Review kind is removed. Existing data is converted
once per workspace, with the report and the apply step approved separately.
A confirmed Review carries the label `contradicts` and a dismissed one `none`;
the report and apply requests may relabel decided Reviews by id, with the same
relabels the relation evaluation set is seeded with:

| Existing record | Becomes |
| --- | --- |
| decided Review labeled `contradicts`, `updates` or `equivalent` | relation of that label decided by review, with both Memories' Evidence times as discovery would show them, and the reviewer and time kept in its audit record; `updates` is recorded as `contradicts` when those times do not order the pair |
| decided Review labeled `none` | dismissal of `contradicts` and `updates` for that pair and both Memories' content |
| pending Review | re-run of discovery for the challenger |
| exhausted discovery work | re-run of discovery |

Converted Review rows are deleted after the conversion report matches the
applied counts. Deleting them is a separate approved step.

## Consequences

- A person is never required to act for a relation to be useful, and there is
  no backlog to monitor. The cost of a false relation falls on readers, which is
  why the contract prefers `none` when unsure and gates every change on the
  labeled evaluation set.
- Changed knowledge across documents is separated from genuine disagreement:
  `updates` points readers to the newer statement without retiring the older
  one, which only its own Source or a Correction can do.
- The same classifier contract covers conflicts inside one Source and across
  Sources, and relations that no reader used are no longer written.
- Discovery remains bounded. No completed run proves the absence of conflicts,
  and a Memory may be read before its relations are known.

## Cloud impact

- HANA stores the new labels, the relation dismissal and the re-run audit event,
  and implements the conflict read model from relations instead of Reviews. This
  changes storage protocol methods in `src/memforge/storage/adapters/protocols.py`
  (relation read, source references, discovery completion and failure, work
  count) and adds workspace database methods the admin API calls (dismissal
  write and undo, relation view, exhausted-work listing and re-run, conversion),
  which the HANA adapter must implement. A stored relation carries both
  Memories' Evidence times; Support state carries no source time.
- The one-time conversion runs per workspace through the Cloud maintenance path;
  its apply and Review deletion steps require operator approval.
- The classifier and its interim Structured LLM use the existing LiteLLM `sap/`
  routes and the LLM batch runner. No configuration is added.
- The classifier input reads the current Observation Revisions of each
  Memory's Source Unit (`get_current_source_observation_revisions`, with its
  Evidence Representation Profile and `observed_at`, the only source of the
  Evidence time) and the document title (`get_document`), which the HANA adapter
  already implements. Discovery and the conversion build that input with the
  same methods. `record_source_projection` writes a missing `observed_at` once
  when a later projection gives it, and the HANA adapter does the same.
- `proxy/external_runtime.py` call sites do not change.

## Related

- [ADR 0009](0009-bound-cross-document-relation-discovery.md): bounded retrieval,
  lease and completion contract, which this decision keeps; its Review output is
  superseded here.
- [ADR 0034](0034-unify-incremental-support-and-claim-assessment.md): same-Unit
  relation and pre-creation identity.
- [ADR 0036](0036-separate-semantic-work-from-inference-executors.md): classifier
  executor and evaluation gate.
- [Source sync to Memory](../design/source-sync-to-memory.md): cross-document paths.
