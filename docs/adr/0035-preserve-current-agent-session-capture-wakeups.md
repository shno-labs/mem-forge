# Preserve current Agent Session capture wakeups

Status: Accepted (2026-09-08)

## Context

Agent hooks durably mark a session pending and start a detached run-once worker.
The worker processes a bounded number of rows under one host-local single-flight
lock. A non-blocking worker start could lose the only wakeup for a newly pending
session when another worker held that lock. Ordering every claim only by age
could also leave the session that triggered the hook behind unrelated historical
backlog.

The pending flag made the window retryable, but did not guarantee a timely pass
after the current hook. This was a scheduling violation at the local queue
boundary; bookmark advancement, upload idempotency, and service-side Agent
Session processing remained correct.

## Decision

Every hook-started worker carries the requesting `(client, session_id)`, waits
for the queue's existing advisory single-flight lock, and gives that exact row
first position in its bounded claim when the row is pending and lease-eligible.
Remaining claim capacity continues to use the existing age order. Workers that
are invoked directly without a requesting identity keep age order, and direct
callers may retain non-waiting lock behavior.

The worker still materializes the live transcript range only after it owns the
row's random lease token. Upload success advances the bookmark under that token
and the captured `request_seq`; failure releases the claim while preserving the
pending row. A newer hook request during upload therefore remains pending for a
later pass. A process crash releases the advisory file lock, while the durable
SQLite lease prevents another worker from claiming the row until that lease is
eligible again.

## Consequences

The current hook window is no longer stranded merely because an older worker
was active or the queue contained more rows than one claim. Concurrent workers
remain serialized, and the existing `max_sessions` limit remains a transport
and computation bound. This decision adds no business state, lifecycle state,
queue table, daemon, or server contract, and it does not weaken fail-open hook
behavior or fail-closed workspace selection.

Waiting detached workers may briefly accumulate during overlapping hooks. Each
exits after one bounded pass, and OS process exit releases the advisory lock.
The normal `RECOVER` path remains the durable recovery mechanism for expired
leases or interrupted processes.

## References

- [Agent Session SaaS Plugin Flow](../design/agent-session-saas-plugin-flow.md)
- [ADR 0021: Select workspaces at the v1 request boundary](0021-select-workspaces-at-the-v1-request-boundary.md)
- [Python `fcntl.flock` documentation](https://docs.python.org/3/library/fcntl.html#fcntl.flock)
