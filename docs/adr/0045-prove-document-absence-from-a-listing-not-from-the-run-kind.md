# Prove document absence from a listing, not from the run kind

Status: Accepted

Date: 2026-09-30

## Context

A document Source Unit is tombstoned, and its Support removed, only when a
sync run proves that the document is gone. Today that proof is decided by the
kind of run (`source_run_projection_coverage`): the first sync and a force-full
sync may prove absence, and every other run is `PARTIAL_PROJECTION` because it
had a last sync time. The rule was written for connectors that narrow
discovery by `since`, and it has three consequences:

- A GitHub Repository Source in cloud-pull mode lists the whole repository
  tree on every run and attests it, yet no run after the first proves absence.
  Renamed and moved files keep their old Units forever. On EU12 dev, one
  repository Source holds 169 such Units and 792 Memories supported only by
  them.
- Jira and Confluence Sources can prove absence only in a force-full sync, and
  a force-full sync also re-extracts every Unit with the model. Of the eight
  Jira and Confluence Sources on EU12 dev, three have run one force-full sync
  since July; the others never have. Deleted issues and pages keep their
  Memories.
- A force-full sync treats every current Unit missing from the query result as
  deleted. A JQL with a relative date (`updated >= -30d`) or a status predicate
  therefore retires every older or closed issue in that run, although nothing
  was deleted.

Two different facts are mixed here. A query result says which items the
connector collects now. Absence says the provider no longer has the item.
Only the second may remove Support.

## Decision

### Absence means the provider no longer has the item

A document Unit becomes absent when its connector proves, in the current run,
that the provider no longer has the item: not found or gone at the provider
(for Atlassian, HTTP 404 or 410). An item that still exists but no longer
matches the configured query, tree or time window is not absent. A refusal to
show one item (HTTP 403 for that item) keeps it. A rejected credential, a
transport error and any other provider error fail the run, never prove
absence.

Absence is what the Source's credential can see. Jira answers 404, not 403,
for an issue the credential may not view, so an issue that becomes hidden from
the Source is absent to it, as a deleted one is. Confluence answers 404 for a
page in the trash unless trashed content is asked for, so a trashed page is
absent.

### Every run lists the configured scope

Every scheduled run of a document Source lists the provider keys of every item
in its configured scope, independent of `since`: identifiers only, no content,
no model call. The listing is complete or it is not used. Incomplete paging,
a truncated result or any listing or confirmation error leaves the run without
absence proof: every unlisted Unit keeps its Support, the run still succeeds
because its content is committed, the skipped check is logged with its cause,
and the next run lists again. Missing proof keeps what is held, as it does for
partial coverage everywhere else. Content discovery stays incremental and is
unchanged.

A connector whose discovery already walks the whole scope on every run and
uses `since` only to choose what to fetch lists from that walk at no extra
cost: the GitHub repository tree, the GitHub Pages repository tree or declared
exhaustive sitemap, and the Confluence page tree or spaces. Jira narrows
discovery by `since` in the JQL itself, so it lists with its own
identifier-only search of the configured JQL, ordered by key so that issues
updated while it pages keep their place. A connector that cannot list (a
bounded link crawl, a single page or explicit page list whose missing page
already fails discovery, conversations) proves no absence this way.

Current Units missing from a complete listing are *unlisted*. The connector
declares which kind of listing it produces:

- **Existence listing.** The listing enumerates everything the provider holds
  at the configured location: a repository tree at a ref, a local folder
  snapshot collected by the local agent. An unlisted Unit is absent.
- **Query listing.** The listing is the result of a query: JQL, CQL, a
  Confluence page tree or space. An unlisted Unit is confirmed by identifier
  in the same run. The connector asks the provider for the unlisted
  identifiers; those the provider reports not found are absent, and those it
  still returns stay current. Jira searches `issuekey in (...)` for a hundred
  identifiers per request without validating the query, so an unknown
  identifier drops out instead of failing the batch, and reads by id each one
  the search does not return. Confluence reads each unlisted page by id.

Absent Units receive a projected tombstone, and the existing Lifecycle Plan
removes their Support. A Memory retires only when its last active Support is
removed; pending Reviews on it become stale (ADR 0004, ADR 0038). No model
call is made for absence. `source_run_projection_coverage` no longer reads
whether the run is incremental: a run's discovery alone proves absence only
for a submitted authoritative snapshot or a complete discovery of a newly
configured scope, and every other run, first, incremental or force-full,
removes only what its listing proves absent.

### Leaving a query is not deletion

A Unit that is unlisted but still exists keeps its current revision and its
Support. It is not refreshed while it stays outside the query, it is refreshed
again when it re-enters, and every later run still confirms that it exists,
so a later deletion is still found. This matches ADR 0028 for conversations:
how much a connector collects is not authority to remove established
knowledge.

Removing knowledge because of age is a separate, explicit retention policy.
Teams has one (ADR 0028). Document Sources get none in this decision; if one
is added it follows the same rule as Teams: explicit, off by default, and
applied only with a complete listing of the same run.

### Explicit scope changes are unchanged

A user's change to the configured scope remains a scope transition (ADR
0005): Units outside the new scope are reconciled as removed, because the
user asked for it. That rule does not apply to a query whose results change
over time without a configuration change.

### Conversations and agent sessions

Conversation sources keep ADR 0028: a provider tombstone, an omission inside a
bounded poll with same-attempt scope evidence, or an explicit rolling
retention. Agent session sources have no provider to list: their knowledge
changes only through the Agent Knowledge authority (update, supersede) and
explicit user or maintenance retirement. Both are outside this decision.

## Falsifiable behavior

| Scenario | Required result |
|---|---|
| GitHub file renamed, incremental run | New path committed as a new Unit, then the old Unit is tombstoned in the same run |
| Jira issue deleted, incremental run | The issue is unlisted, the provider reports not found, and the Unit is tombstoned |
| Jira issue older than a relative-date JQL window | Unlisted, still found by id: Unit and Support kept |
| Jira issue closed under a `status != Done` JQL | Unlisted, still found by id: Unit and Support kept |
| Confluence page moved out of the configured page tree | Unlisted, still found by id: Unit and Support kept |
| Listing paging fails or is truncated | Run succeeds; no absence in this run; every unlisted Unit kept; the skipped check is logged |
| Provider rejects the credential | Discovery fails the run; nothing is tombstoned |
| Existence check returns 403 for one issue | Not absence; Unit kept; the run continues |
| Issue becomes hidden from the Source's credential | Jira answers 404 for it: absent to this Source, Unit tombstoned |
| Force-full sync of a relative-date JQL | Issues outside the window are confirmed by id and kept |
| User removes a project from the JQL | Scope transition removes that project's Units (ADR 0005) |
| Clock advances, nothing changes at the provider | No Unit tombstoned |

## Considered options

- **Periodic force-full sync.** Rejected: it re-extracts every Unit with the
  model to learn which documents are gone, and it still treats query drift as
  deletion.
- **Treat the query result as the scope and retire whatever leaves it.**
  Rejected: a time window or a status filter would turn Memory into a rolling
  window of recent items, which no user asked for.
- **Trust an existence listing only for GitHub.** Rejected: it fixes one
  connector and leaves Jira and Confluence deletions undetected.

## Consequences

- Each run makes identifier-only listing requests (for Jira about one request
  per hundred issues; none extra where discovery already walks the scope)
  plus lookups for unlisted identifiers. There is no content fetch and no
  model call. An unlisted item that still exists is confirmed again on every
  run, so the lookups grow with query drift: on EU12 the 678 unlisted Jira
  issues cost ten batch searches per run across four Sources.
- Absence no longer needs a force-full sync. A force-full sync keeps its
  meaning of re-reading every Unit, and removes only what the listing proves
  absent, like every other run.
- The first scheduled run after release retires what current Sources have
  accumulated. A read-only run of the new listing and confirmation against
  EU12 dev on 2026-09-30 found 183 absent Units, and 844 active Memories
  whose last Support they hold:

  | Source | Listing | Unlisted | Absent | Kept (still exists) | Memories retiring |
  |---|---|---|---|---|---|
  | GitHub repository, payroll_agent `src-6cb562f1` | existence | 169 | 169 | 0 | 791 |
  | GitHub Pages, payroll_agent `src-4bd1a62a` | existence | 9 | 9 | 0 | 18 |
  | Confluence page tree, payroll_agent `src-9c02f495` | query | 3 | 3 | 0 | 25 |
  | Confluence page tree, mount_tai `src-a053bd02` | query | 4 | 2 | 2 | 10 |
  | Jira, mount_tai `src-be49007d` | query | 621 | 0 | 621 | 0 |
  | Jira, mount_tai `src-70cb236e` | query | 43 | 0 | 43 | 0 |
  | Jira, mount_tai `src-841f0b76` | query | 12 | 0 | 12 | 0 |
  | Jira, mount_tai `src-e47815b5` | query | 2 | 0 | 2 | 0 |

  Of the five absent Confluence pages, four are in the trash and one was
  purged; the two kept pages are current pages that the tree walk no longer
  reaches. Seven other cloud-pull document Sources had nothing unlisted. Local-push
  repositories submit authoritative snapshots and are unchanged. The 678
  unlisted Jira issues still exist, apart from two in `src-be49007d` whose
  stored item cannot be read and which are kept unconfirmed; under the earlier
  rule a force-full sync of those Sources would have retired all of them.
- Jira collected by the local agent submits its JQL inventory as an
  authoritative snapshot, so that path still removes what leaves the query.
  Bringing it under this rule needs the agent to confirm unlisted issues by id
  and is left to a follow-up; no EU12 Source uses it.
- Cloud impact: OSS pin only. The connectors and the coverage decision are OSS
  code; HANA already stores tombstone revisions and applies the same Lifecycle
  Plan. The confirmation reads the stored item through store methods HANA
  already implements (`find_source_unit_by_document_id`,
  `get_source_unit_input`, `get_document`). No schema, configuration or `sap/`
  route change.

## Non-goals

No age-based retention for document Sources, no change to scope transitions,
no new Memory or Unit status, no provider webhooks, and no change to how
conversation or agent session knowledge is retired.
