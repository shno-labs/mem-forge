# Local daemon incremental sync capability review

Date: 2026-07-22

## Scope

The current local-agent sync contract exposes four sync operations:
`github_repo_sync`, `local_markdown_sync`, `jira_sync`, and `teams_sync`.
Confluence is currently server-executed, so it is useful as a provider comparison
but is not a daemon implementation target for this change.

The goal is not to force every connector through a Git-shaped algorithm. The
shared contract must separate change detection, completeness evidence, and body
materialization so each adapter can use the strongest provider capability it
actually has.

## Primary-source findings

### GitHub repositories

GitHub's Git Trees endpoint returns path, object type, size, and blob SHA for
tree entries. A recursive response is complete only when `truncated` is false;
GitHub documents a 100,000-entry / 7 MB recursive-tree limit and directs clients
to walk subtrees when the response is truncated. The commit endpoint also
exposes the root tree SHA. These object identities support two levels of
short-circuiting: an unchanged accepted root tree proves a repository no-op,
while a changed tree can still be filtered and compared by per-file blob SHA
before any blob body is fetched.

Sources:

- [GitHub REST: Git trees](https://docs.github.com/en/rest/git/trees)
- [GitHub REST: commits](https://docs.github.com/en/rest/commits/commits)

### Local files

Filesystem notifications are accelerators, not completeness evidence. Linux
documents that an inotify queue can overflow and events are then lost; robust
applications may need to rebuild the cache. Apple's FSEvents documentation
likewise defines dropped-event conditions that require a rescan. Therefore a
portable daemon must retain a metadata inventory scan as the correctness path.
Content hashes remain the strongest portable content revision. A daemon-local
digest cache may avoid rereading bytes when a stat fingerprint is unchanged,
but a missing/invalid cache or explicit verification run must recompute hashes;
watcher state alone must never authorize deletion or a no-op.

Sources:

- [Linux inotify manual](https://man7.org/linux/man-pages/man7/inotify.7.html)
- [Apple File System Events programming guide](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/FSEvents_ProgGuide/UsingtheFSEventsFramework/UsingtheFSEventsFramework.html)

### Jira

Jira search supports JQL and paginated issue discovery. MemForge's existing
Jira Gene already accepts a `since` time and adds `updated >= ...`, but the
local-daemon caller currently invokes `discover(None)`, forcing a full search
and full package upload on each run. Jira does not provide a general opaque
issue-delta token comparable to Microsoft Graph. The reviewed V1 therefore
keeps a complete cursor-paged lightweight inventory of stable issue identity
and revision on every ordinary run, while hydrating only changed issues.
`updated` windows and Jira issue-created, updated, and deleted webhooks may
prioritize candidates, but they are not completeness authority: indexing delay,
time precision, deletion, and JQL scope exits can otherwise be missed.

Sources:

- [Jira Cloud REST: issue search](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/)
- [Jira Cloud webhooks](https://developer.atlassian.com/cloud/jira/platform/webhooks/)
- [Jira Data Center webhooks](https://developer.atlassian.com/server/jira/platform/webhooks/)

### Microsoft Teams (current ChatSvc REST collector)

MemForge's current local Teams message collector uses the Teams ChatSvc REST
endpoints with a delegated local session and a stable-window ledger. This
optimization must remain on that REST path; it must not introduce Microsoft
Graph delta tokens, Graph application permissions, or a Graph fallback.

Microsoft Graph's opaque-token chat-message delta flow is included below only
as a comparison showing the general checkpoint pattern. Its endpoint requires
application permissions, is limited to the last eight months, and handles
replies separately, so it is not the implementation contract for MemForge's
current Teams source.

The current Teams Gene already implements `since`, conversation
`lastActivity` filtering, bounded backward pagination with overlap/context, and
stable window revisions. However, the daemon caller currently invokes
`discover(None)`, so it repeatedly polls the configured maximum-age history.
The provider-neutral refinement is therefore to pass a last-successful time or
window checkpoint plus overlap into the existing ChatSvc REST collector and
suppress upload of unchanged overlapping window revisions. Explicit tombstones
or complete REST poll coverage remain necessary for destructive absence
handling. A periodic or explicit complete reconciliation over the configured
scope is required to discover edits or deletes outside the ordinary overlap.
No `deltaLink` is persisted or interpreted.

Sources:

- [Microsoft Graph: chatMessage delta](https://learn.microsoft.com/en-us/graph/api/chatmessage-delta?view=graph-rest-1.0)
- [Microsoft Graph delta-query overview](https://learn.microsoft.com/en-gb/graph/delta-query-overview)

### Confluence comparison

Confluence is not currently daemon-backed. Its APIs nevertheless reinforce the
same model: cursor-paged metadata search, stable page identity, version number,
status, and last-modified predicates can limit body hydration, but there is no
general native delta token. A future local Confluence adapter should declare
those capabilities through the shared collector interface rather than add a
route branch.

Sources:

- [Confluence REST API v2 pagination](https://developer.atlassian.com/cloud/confluence/rest/v2/intro/)
- [Confluence advanced CQL search](https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/)

## Design consequences

Use one capability-based collection module with three stages:

1. **Checkpoint probe**: use an opaque provider checkpoint when available. An
   exact accepted checkpoint may prove a no-op without enumerating every item.
2. **Inventory or delta discovery**: emit stable item identity, opaque revision,
   change kind, and explicit coverage (`complete_snapshot`, `bounded_delta`, or
   `partial`). Finish all pagination before claiming complete coverage.
3. **Body materialization**: after server comparison, fetch/read and upload only
   the item bodies requested by the returned plan.

The server must not interpret provider tokens. It validates the source config
revision, activity epoch, lease attempt, prior checkpoint, coverage kind, and
stable identities; reuses only exact attested revisions; and returns required
bodies. A candidate next checkpoint is promoted only with the successful Source
Projection/lifecycle transaction, never merely because the daemon finished
collection.

Absence is destructive only for a complete snapshot. Bounded delta collection
removes an item only from an explicit provider deletion/tombstone. Partial
coverage cannot advance a checkpoint or finalize a no-op. Webhooks and file
watchers can wake or narrow a run, but cannot certify no-op or deletion.

Fallback should degrade by capability: invalid checkpoint -> metadata
re-enumeration; unavailable revision -> body hashing/materialization; incomplete
pagination -> retry/fail closed. It should not default directly to uploading
every body when metadata comparison is still possible.

## Recommended sequencing

1. Finish the complete-snapshot manifest seam and apply it to GitHub with one
   immutable commit/tree boundary and body-to-revision attestation.
2. Reuse the same seam for local Markdown to remove full-body uploads; keep
   portable full hashing first, fail partial scans closed, and evaluate a local
   digest cache separately.
3. Reuse the seam for Jira's complete lightweight metadata inventory and
   selective hydration; use `since` and webhooks only as accelerators.
4. Wire Teams' existing ChatSvc REST `since`/ledger flow and skip unchanged
   overlap windows, with periodic or explicit complete reconciliation; do not
   introduce Graph delta or application permissions as part of this
   optimization.
5. Keep complete reconciliation canaries for deletion/scope coverage; do not
   turn every ordinary incremental run into a full body replay.

The initial implementation stops after the shared immutable manifest/readiness
boundary and selective body transfer. Candidate-checkpoint promotion and the
provider accelerators in steps 1 and 4 remain tracked by issue #164 so their
durability is not approximated with daemon-local flags or provider branches.
