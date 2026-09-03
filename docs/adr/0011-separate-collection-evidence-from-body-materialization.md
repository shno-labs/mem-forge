# Separate collection evidence from body materialization

Status: Accepted

## Context

Local daemon sources currently discover provider state and transfer complete
document packages in one step. This preserves correctness but makes a no-op
sync proportional to the full corpus. A provider time filter, filesystem
watcher, or webhook alone would be faster but cannot prove complete membership,
safe deletion, or a durable checkpoint after missed events, truncated
pagination, authorization changes, or process failure.

The daemon-backed source types are GitHub Repository, Local Markdown, Jira,
and Teams. They expose different provider capabilities, so correctness cannot
depend on one Git-shaped algorithm or source-type branches in Cloud routes.

## Decision

Separate local collection into three stages behind one provider-neutral
collection interface:

1. **Discover** an attempt-scoped Collection Manifest containing stable item
   identity, opaque revision, explicit change kind, Collection Coverage, and an
   optional Candidate Checkpoint.
2. **Plan** on the server by matching exact revisions to previously attested
   immutable Source Sync Inputs and returning only the identities whose bodies
   are required.
3. **Materialize** and upload only those required bodies, then run the existing
   Source Projection and lifecycle path.

For sequential GitHub collection, materialization owns one required body through
its synchronous upload and then releases it before fetching the next. The outer
collection loop retains the complete manifest, counters and body-free receipts,
not all document bodies. This is a body-lifetime constraint behind the existing
single-document upload interface, not a new batch, queue or lifecycle state.
Fetching/uploading progress may alternate per item; both use the same workset
total, while failures remain explicit. Final processing still waits for complete
manifest materialization/reuse, and lease rejection stops further collection.

Collection Coverage has exactly three semantics:

- `complete_snapshot` proves the full current configured scope. Only this
  coverage may interpret absence as removal.
- `bounded_delta` reports only explicit upserts or provider tombstones since an
  accepted checkpoint. Absence has no meaning.
- `partial` reports useful observations without deletion authority. It cannot
  advance a checkpoint or finalize a no-op.

Snapshot authority belongs to the current run's validated immutable manifest,
not to a source type or replay adapter capability. A direct provider pull with
no bound input snapshot remains incremental even when that source type also has
an authoritative local-daemon collector; its prior successful watermark must
remain available to the connector.

The Candidate Checkpoint becomes current only with the successful Source
Projection and lifecycle transaction. Configuration/activity epoch, lease
attempt, authorization scope, pagination completeness, item identity, and body
revision are stale-guarded before commit. A body whose attested revision does
not equal the manifest revision fails the attempt rather than mixing snapshots.
Duplicate identities, missing revisions, incomplete pagination, transient read
errors, lost leases, or changed scope fail closed.

Existing Source Sync Inputs and Snapshot membership remain the durable
authority. Reusing an input attaches that immutable input to the new attempt;
it does not copy a document, replay lifecycle decisions, or create another
execution state machine.

The server persists one immutable digest and the declared item keys for each
attempt manifest, including coverage, `doc_id`, opaque revision, and change
kind. Every reused or newly materialized input must match its declared item;
count equality alone is not readiness. Source processing is rejected until
every declared item is materialized or reused. This makes a valid empty
complete snapshot distinguishable from an upload that has not finished.
Retrying the same attempt with different identities, revisions, change kinds,
or coverage is rejected.

Input Snapshot Presence is also preserved when the manifest contains zero
items. Presence selects the local replay path and prevents a connector from
falling back to live provider authentication. It does not make the snapshot
authoritative: an empty `bounded_delta` remains non-destructive, while an empty
`complete_snapshot` may authorize absence only through its separate validated
Collection Coverage.

An embedded SQLite job lease is revalidated in the same storage transaction as
manifest attachment. Cloud's lease authority and HANA are separate durable
stores, so Cloud validates the external lease immediately before the HANA
write, binds the immutable manifest to job attempt, config revision, and source
activity epoch, and validates the same lease again before processing is
enqueued. No cross-store transaction is implied.

Provider adapters obtain coverage and revisions with their strongest existing
capability:

- **GitHub Repository** resolves the configured ref once to an immutable commit
  and root tree. An accepted unchanged root tree is a no-op; a changed tree is
  fully enumerated and compared by path and blob SHA. Truncated recursive trees
  are walked by subtree or fail closed, and required bodies are fetched by the
  pinned object identity.
  Both server and daemon text collection use the raw Git Blobs representation,
  not Contents or JSON/Base64 materialization. Each transfer is bounded while
  reading by available inventory/transport lengths and the provider's 100 MB
  Blob envelope, then checked against those lengths and its recomputed Git
  object hash before strict UTF-8 decoding. This envelope is not an extraction
  memory guarantee or a new smaller document-size policy. A supplied invalid
  length, mismatch, incomplete response or invalid UTF-8 fails explicitly; no
  byte replacement, encoding guess or alternate endpoint repairs Evidence.
  Selected non-regular file modes are unsupported, not empty or absent files.
  The configured ref and path retain stable file identity; resolved commit/tree
  identities pin only the collection snapshot. Binary Artifacts retain their
  separate streaming/admission contract and storage limits.
- **Local Markdown** performs a portable complete configured-scope scan and
  content hash. It initially reads local bytes to establish revisions but
  uploads only changed bodies. Traversal, stat, read, decode, or mutation races
  make coverage partial; filesystem notifications and a future digest cache may
  accelerate discovery but never certify deletion or completeness.
- **Jira** performs a cursor-paged complete lightweight inventory of stable
  issue identity and revision for each ordinary run, then hydrates only changed
  issues. After issue fields and separately paged comments are materialized, a
  final lightweight revision read must still equal the inventory revision; a
  concurrent issue or comment update fails the attempt. `updated` windows and
  webhooks may prioritize work but do not replace the inventory because
  deletions, JQL scope exits, indexing delay, and window precision can otherwise
  be missed.
- **Teams** continues to use the existing delegated ChatSvc REST collector, not
  Microsoft Graph. Ordinary runs use bounded polling with overlap and stable
  window revisions; unchanged windows are not materialized into packages or
  uploaded. ChatSvc message polling itself remains collection evidence because
  the provider exposes no cheaper authoritative window revision feed. Historical
  pages use an exclusive `endTime` derived from the final raw row of the prior
  newest-first page; opaque `backwardLink` values remain audit evidence but are
  not pagination authority because ChatSvc can repeat them. A non-advancing time
  cursor fails the poll closed. A periodic or explicit complete reconciliation
  over the configured scope detects older changes.
  Bounded-poll absence never creates a tombstone, and incomplete conversation
  polling preserves prior state.

## Consequences

The shared server path interprets coverage facts rather than provider names;
provider differences remain inside adapters. The design adds no replay ledger,
new executor, webhook dependency, Graph fallback, provider-specific Cloud
route, or silent data repair. Confluence is not daemon-backed and receives no
implementation for this decision; a future adapter must satisfy the same
collection interface.

The correctness promise is no silent permanent omission and no destructive
action from incomplete evidence, with eventual convergence where a provider
can delay visibility. It is not zero-latency discovery of every remote edit.
Acceptance requires deterministic add, change, remove, no-op, truncated or
partial listing, concurrent mutation, lost checkpoint, revision mismatch,
lease fencing, SQLite/HANA contract, and real per-source canaries.

The accepted implementation persists the immutable manifest and eliminates
unchanged body uploads across all current daemon-backed source types. It does
not introduce a generic Candidate Checkpoint store: GitHub still enumerates a
changed or unaccepted tree, Jira still performs its lightweight inventory,
Local Markdown still hashes the configured scope, and Teams uses its existing
window ledger. The no-op, edit, add, removal, fencing, and SQLite/HANA parity
acceptance for issue #164 is complete through selective materialization and
bounded exact projection reuse. Root-tree probing, daemon-local digest caching,
and additional Teams checkpoint or reconciliation accelerators are optional
provider-adapter optimizations, not missing correctness or completion states.
They require a new measured latency or provider-cost trigger and must reuse
this contract rather than add another execution state machine.

Reusable inputs are selected by a bounded, indexed exact match on normalized
manifest membership `(workspace, source, doc_id, revision, change_kind)` and
latest input generation. The planner never loads all historical Source Sync
Inputs into Python. Inputs created before normalized manifest membership exists
are intentionally materialized once; there is no metadata-JSON fallback scan or
silent backfill.

After an immutable input has completed that first projection, a later run may
also reuse its current Source Projection without reading the retained body or
entering the per-document lifecycle pipeline. This is a run-level planning
decision, not a connector shortcut. The shared storage contract admits a member
only when the current manifest reuses the same input under the exact document
identity, revision, and change kind; the current Document revision and active
Source Unit lineage still exist; the current Source Unit revision has the exact
access-context fingerprint; the earlier and current manifests carry the same
source activity epoch and configuration revision; and no Projection Scope
transition is open. Force, repair, and rebaseline execution never use this
path. Any missing or mismatched fact sends that member through the existing
full path.

Projection reuse does not remove collection membership evidence. Reused members
remain part of `crawled_doc_ids`, complete-snapshot absence reconciliation, and
run progress, while their Document `last_synced` timestamp is not rewritten as a
surrogate membership ledger. The immutable attempt manifest is the run's
membership proof. SQLite and Cloud adapters resolve all eligible members with
one set query rather than one lookup per member.

Document body reuse and Source Projection completion are independent facts. An
equal Document content hash permits reuse of existing raw and normalized
artifacts, but it does not prove that the current Source Unit revision,
Observation revisions, or Lifecycle Plan committed. Per-item semantic work is
skipped only when the Source Projection delta says extraction is unnecessary;
a staged Document with no current projection must enter extraction even when
its body hash matches. Failed processing retains a newly staged Document as a
content read model so a retry can reuse its artifacts; the absent projection
still requires semantic work. Existing Documents restore their prior snapshot.
Neither the legacy lifecycle-inferencing deletion path nor projected
post-lifecycle deletion is a per-attempt sync compensation mechanism.

Lifecycle vector delivery is attempted once after the run-level projection
work. A pending durable outbox is not a reason to replay unchanged Source
Projections: delivery retries the existing outbox independently, and a transient
delivery failure cannot reverse the authoritative relational commit.

## References

- [Local daemon incremental sync capability review](../research/local-daemon-incremental-sync-capability-review.md)
- [ADR 0004: Use proven authoritative snapshots as the rebaseline corpus](0004-use-proven-authoritative-snapshots-for-rebaseline.md)
- [ADR 0002: Renew Teams access through a dedicated browser session](0002-renew-teams-access-through-a-dedicated-browser-session.md)
- [GitHub REST Git Trees](https://docs.github.com/rest/git/trees)
- [Jira Cloud issue search](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/)
- [Linux inotify](https://man7.org/linux/man-pages/man7/inotify.7.html)
- [Apple File System Events](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/FSEvents_ProgGuide/UsingtheFSEventsFramework/UsingtheFSEventsFramework.html)
