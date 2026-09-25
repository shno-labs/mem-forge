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
pair receives exactly one label:

| Label | Meaning |
| --- | --- |
| `none` | no relation a reader needs, including one statement being more specific than the other |
| `equivalent` | both state the same knowledge |
| `updates` | both apply to the same situation, cannot both hold now, and the texts show a change over time |
| `contradicts` | both apply to the same situation and cannot both hold, with no change over time between them |

The label definitions are domain-neutral; no list of scope dimensions (version,
country, environment, ticket) is part of the contract. A pair whose statements
can both hold under any reading is `none`. When the judgment is not certain,
the pair is `none`: a false conflict warns every reader of both Memories, while
a missed one only omits a hint.

For `updates`, the program orders the pair by the source revision time of each
Memory's Evidence; the model does not choose the direction. When the times do
not order the pair, it is recorded as `contradicts`. Directional `REFINES` is no
longer recorded for cross-document pairs.

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
is not committed to this repository.

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
content and Support of both Memories. When either changes, the relation stops
being current, and the next discovery for the changed Memory judges the pair
again. A Lifecycle write still owns authoritative Support relations and may
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
once per workspace, with the report and the apply step approved separately:

| Existing record | Becomes |
| --- | --- |
| confirmed Review | `contradicts` relation, with the reviewer and time kept in its audit record |
| dismissed Review | dismissal for that pair and both Memories' content |
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
  (conflict context read, dismissal write, exhausted-work listing and re-run),
  which the HANA adapter must implement.
- The one-time conversion runs per workspace through the Cloud maintenance path;
  its apply and Review deletion steps require operator approval.
- The classifier and its interim Structured LLM use the existing LiteLLM `sap/`
  routes and the LLM batch runner. No configuration is added.
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
