# Project source sync activity from existing execution records

Amended: 2026-07-29 to preserve run progress across lease recovery and fence
exhausted attempts; 2026-08-08 to make the lease-fenced terminal transaction
the authority for Source freshness and history; 2026-08-12 to preserve
provider-neutral retryability across the pipeline and durable worker seam;
2026-08-18 to defer retryable local collection jobs at the broker boundary;
2026-09-02 to terminalize jobs invalidated by a Source Activity epoch fence;
2026-09-03 to distinguish durable retry waiting from execution and bind manual
retry to the displayed execution record.

Local collection jobs, server processing runs, and lifecycle-maintenance jobs keep their independent durable lifecycles because they have different owners, leases, retries, and storage transactions. The Sources UI consumes one Source Sync Activity read model projected from those records, rather than introducing a cross-store master operation or extending one execution record to own the others.

This keeps execution recovery local to each existing state machine while giving every source type one refresh-safe progress contract and presenter. Server processing persists its latest Progress Snapshot on its run; local collection exposes the snapshot already persisted with its job; lifecycle maintenance contributes its durable status without pretending to have per-document progress. Active maintenance outranks stale terminal sync history, uses provider-neutral memory-update language, and blocks conflicting source mutations in the UI while storage remains authoritative. Completed maintenance shows a short terminal acknowledgement and then becomes visually quiet while still suppressing obsolete failed-sync history. A failed maintenance attempt remains in lifecycle history, but remains actionable on the Source row only while current lifecycle state is still blocking: the Source is gated, an open cutover finding exists, or lifecycle vector delivery remains incomplete. The projection selects the relevant activity and never treats progress-delivery failure as source-sync failure.

Local collection authority is continuous rather than an admission-only check. An
explicit lease rejection fences the running attempt immediately, and failure to
renew beyond the last confirmed lease deadline fences it locally even when the
server is unreachable. A fenced daemon attempt stops at its next cooperative
checkpoint and never submits a terminal completion. A transient ownership loss
may leave the durable job eligible for a new attempt, but a server-observed
Source Activity epoch mismatch is irreversible: the server terminally fails the
job as non-retryable before rejecting the heartbeat, so an invalidated job can
never be leased again. Local progress distinguishes provider discovery,
content fetching, and Cloud upload so a refresh-safe UI does not present a slow
collection phase as a frozen previous phase.

Provider clients classify transport reachability separately from command or
configuration failures before completing a local collection job. In particular,
a GitHub CLI connection failure is a retryable provider connection error rather
than a generic CLI usage error; authentication, authorization, repository, and
invalid-response failures remain non-retryable unless their own typed contract
says otherwise. The broker, not the daemon process, owns the durable wait: the
same job becomes eligible one hour after its first retryable failure and twelve
hours after each later retryable failure, up to the existing five-attempt limit.
Queued jobs persist their not-before timestamp, and SQLite and Cloud adapters
must exclude them from leasing until that timestamp. Terminal completion clears
the timestamp and remains visible as Action needed after the attempt budget is
exhausted.

Waiting for a not-before timestamp is not execution. The activity presenter
shows a static waiting state, the next retry time, and an authorized Retry now
action; it reserves Syncing and busy progress for actual execution. Manual sync
(including the existing force entrypoint) may advance a pending/queued record's
eligibility. Scheduled admission preserves its backoff. Neither action resets
attempt counts or failure history, and a running lease is never preempted.

An exact retry identifies both the execution kind and its existing ID. Retrying
a server run after local collection must not recollect or upload the Source.
The owning store validates source/workspace, authority, configuration and
maintenance fences, conditionally advances the queued record, and returns its
authoritative state. A stale click on a running or terminal record does not
create new work. Ordinary new sync requests retain the existing successor rules
for new configuration, snapshots and force intent; those are not exact retries.
Schedule advancement and job admission remain one atomic transaction.

HTTP acceptance and durable completion are separate. The browser releases the
request state when admission returns and observes workspace-scoped existing
job/run queries. Query errors are display errors, never synthetic failed jobs.
A local completion receipt keeps Source refresh active until its server run (or
a newer authoritative run) is visible. Configure and Delete remain protected
while the Source has active work, even when Retry now is available. No combined
task state machine or cross-store polling coordinator is introduced.

Admission responses expose the accepted record's server-created timestamp and
current status. The UI retains only this real receipt until the corresponding
query observes that execution or a newer one; terminal responses need no pending
receipt. This handles both query outages and short executions skipped by a
latest-record view without comparing browser clocks. The UI
uses an exact, authorized job/run read when the latest view cannot establish
completion (including equal timestamps); timestamps are not an ordering token.
Current Source-job listing selects canonical sync operations before limiting and grouping by Source;
setup/auth jobs remain available through their own exact job reads.

OSS local jobs add the nullable eligibility timestamp without backfilling old
rows. Rolling back to a broker that ignores this column loses retry-delay
enforcement; operators must stop affected executors if that guarantee is needed
during rollback. The column and durable failure history are retained.

Server-processing progress belongs to the durable run, not to one worker lease.
After validating the Source and before constructing its runtime or calling its
provider, a first attempt with no snapshot persists `discovering: 0`; the
pipeline replaces that placeholder with real totals as soon as discovery
produces them. A recovered lease resumes from the last monotonic Progress
Snapshot and must neither clear it merely because the process attempt changed
nor regress it to the initial placeholder. If process death bypasses normal
failure handling after the configured execution-attempt budget has been
consumed, a recovery worker may claim the expired lease only to apply the fenced
terminal failure. It must not reconstruct the runtime, call a provider, or
execute the Source again. This keeps storage adapters free of runtime retry
policy while ensuring that an OOM cannot create an unbounded recovery loop.

Durable Source Unit derivation recovery is exposed as
`recovering_derivations`, with its outer completed/total workset measured in
the Source's normal item unit. The presenter describes this as resuming Memory
creation and leaves inner extraction, Candidate Ledger, identity, and lifecycle
work indeterminate. `reconciling` is reserved for authoritative removed-item
detection, so a recovery attempt cannot be presented as deletion checking.

Local package intake also preserves web-runtime liveness. Document artifact
stores remain synchronous shared adapters, but an async HTTP intake must run
their blocking object-store or filesystem writes outside the request event
loop before it records the resulting package URI in the durable source input.
This is one provider-neutral persistence boundary for local Markdown, GitHub,
Jira, and Teams packages; Cloud routes must not add source-specific offload
branches, and liveness timeouts are not a substitute for keeping blocking I/O
off the event loop.

A terminal source-sync failure remains available through Last sync details, but
the Source row presents it as actionable only when the current viewer has the
Source capability to run sync. This prevents a managed or read-only Source from
offering an impossible Retry action while preserving the execution record.
Source sync capability is derived from the Source Gene's declared
`execution_kinds`; a Source type with no execution kind never enters manual,
scheduled, or worker-owned ordinary sync. Historical sync records remain
auditable, but are not projected as current Source activity for such a type.

For a managed push Source, a successful durable intake receipt advances the
Source row's freshness watermark without creating an ordinary sync record.
The receipt and the monotonic watermark commit atomically in every storage
adapter; failed receipts do not advance it, and older or exact retries cannot
move it backward. The read model therefore reflects accepted source activity
while preserving the boundary between push intake and connector sync.

When local collection successfully starts server processing, its terminal
result records the returned `SourceSyncRun` ID as an immutable handoff receipt.
A local sync cannot report success without that identity, and an idempotent
terminal retry must repeat the same identity. This correlates the two existing
state machines without a master execution record, replay ledger, or
cross-store transaction.

For an ordinary durable server run, one lease-fenced terminal transaction owns
the run status, `SyncState`, the Source's successful freshness watermark, and
exactly one history row correlated by the durable `SourceSyncRun` ID. A no-op
success is still a successful terminal result. Failed and partial results are
recorded for diagnosis but never advance the successful freshness watermark;
retryable attempts are not terminal history. The pipeline returns a
provider-neutral `SyncState` and delegates persistence to the durable worker.
Non-durable CLI or maintenance callers use the same atomic result interface
rather than issuing separate state and history writes. SQLite owns this shared
contract; Cloud implements the same transaction in its HANA adapter without a
source-type or route-level branch.

A Gene may report a typed Source Configuration Error when the same configured
scope cannot succeed on another execution attempt. The pipeline preserves that
provider-neutral retryability disposition on its returned `SyncState`; it does
not reduce the exception to an unclassified error string. The durable worker
still owns retry scheduling and the terminal transaction: retryable failures
enter bounded backoff, while a non-retryable failure becomes terminal on its
first completed attempt with its actionable error message and no
`next_attempt_at`. Storage adapters receive only the resulting retry decision
and remain independent of Gene types and provider error text.
