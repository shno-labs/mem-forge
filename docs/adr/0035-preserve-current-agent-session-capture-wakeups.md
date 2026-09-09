# Coalesce Agent Session capture under one on-demand owner

Status: Accepted (2026-09-09)

## Context

Stop, PreCompact, and SessionStart recovery must preserve new capture requests
while a worker uploads or exits. A pending content flag alone cannot distinguish
a fresh wake from historical backlog. One waiting process per hook serializes
uploads but allows unbounded process accumulation and repeated failed attempts.

## Decision

All capture hooks use one scheduling entry. Each request persists a
`wake_requested_at` on the existing session cursor, preserving its first waiting
time. A claim consumes that wake atomically with its lease and request sequence.
New requests during upload set a new wake; stale results cannot clear it. A
successful bounded prefix rearms its remaining tail. Workspace pinning, upload
idempotency, and bookmark/lease guards remain unchanged.

The hook reserves the queue's POSIX advisory file lock non-blockingly before
spawning. It transfers the same locked open file description through `pass_fds`
and closes its own copy without unlocking. Hooks that find an owner enqueue
without spawning waiting processes. The owner consumes rounds of at most five
sessions, prioritizing fresh wakes over historical pending rows. Historical
recovery has a total budget of five sessions per activation. Continuous fresh
work can delay history; there is no historical completion deadline.

Enqueue commits before the producer ensures ownership. The ownership probe uses
a short SQLite write transaction. The exiting owner rechecks eligible work under
`BEGIN IMMEDIATE`, releases its file lock while that transaction is still held,
then commits and exits without doing further queue work. If enqueue wins, the
owner sees it; if exit wins, the producer can acquire ownership. Network requests
and transcript scans run outside these write transactions.

Failures preserve the pending bookmark and record completion time. Eligibility
requires at least 60 seconds since failure completion; a failed identity is also
excluded for the rest of that activation. A worker with no eligible work exits
without polling or scheduling a timer. Later hooks or explicit recovery retry
eligible pending work. SessionStart promotes its current already-pending row as
well as rearming an idle row whose transcript grew. Pending promotion precedes
the idle check: either its new sequence protects the in-flight result, or the
idle check observes the completed row and rearms its tail.

## Consequences

This supersedes the earlier per-hook waiting worker and process-local requesting
identity priority. Process ownership is bounded and normal shutdown cannot lose
a durable wake. The scheduler adds only a nullable local cursor field, defaulting
to NULL for existing rows; it adds no service, business, or lifecycle state.

Spawn failure or process death preserves pending work and releases OS ownership.
An in-flight lease still delays recovery until expiry. No later hook means no
automatic crash recovery. Missing POSIX locking fails closed with a diagnostic;
macOS and Linux use real process/lock tests. During upgrades, stop old client
sessions and allow old workers to exit before restarting both clients on the new
artifact: mixed old waiting workers do not provide the new process-count bound.

## References

- [Agent Session SaaS Plugin Flow](../design/agent-session-saas-plugin-flow.md)
- [ADR 0021: Workspace selection](0021-select-workspaces-at-the-v1-request-boundary.md)
- [SQLite write transactions](https://www.sqlite.org/lang_transaction.html)
- [Python descriptor inheritance](https://docs.python.org/3/library/subprocess.html#subprocess.Popen)
- [POSIX flock ownership](https://man7.org/linux/man-pages/man2/flock.2.html)
