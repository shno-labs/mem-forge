# Unify explicit Memory correction under resolved authority

Status: Accepted (2026-08-19)

## Context

The former `replace_memory` command handled Direct User and Managed Capture
knowledge but rejected Memories with active configured-source Support. That
left agents with two unsafe temptations: create an unrelated private Memory, or
ask an operator to bypass Source lifecycle. At the same time, deciding from a
raw `workspace_admin` role would leak Cloud membership vocabulary into the
single-owner OSS runtime and would mistake management capability for Source
ownership.

## Decision

Expose one confirmed command, `propose_memory_correction`. The command resolves
the target, complete active Support Set, visibility, and Correction Authority
server-side. Direct User and owner-managed capture corrections apply for the
Memory Owner. Configured-source corrections apply immediately only when the
actor can manage every active supporting Source. The OSS Self-Hosted Owner and
Cloud request adapters map their deployment-specific identity models into the
same `CorrectionAuthority` interface; the Memory module does not inspect Cloud
roles.

For configured-source correction, the authority decision uses Source ids and
the Support Set hash produced from one adapter snapshot. The authorized write
rechecks that hash inside the same transaction that creates the correction
Document and challenger, supersedes the incumbent, records the approved
Review, and publishes Review-owned vector work. A stale snapshot rolls back
the entire proposal and leaves no pending challenger or Review.

Every ordinary proposal is represented by a hidden `user_correction`
challenger and one supersede Review. An authorized submission resolves the
Review immediately, so it has no pending human step while retaining the same
atomic decision audit. An unauthorized but visible submission leaves the
Review pending. The Review pins the incumbent and challenger versions plus the
complete active Support Set hash. Approval fails stale if any participant or
Support changes.

Approval makes the pinned incumbent Support Assertions non-current, preserves
their Evidence and provenance on the historical incumbent, activates the
correction, supersedes the incumbent, and writes Review-owned durable vector
work in one relational transaction. Rejection retires only the challenger.
The old `replace_memory` MCP tool, REST route, and client method are removed.

## Consequences

- Agents learn one correction interface and always show a readable preview and
  obtain explicit user confirmation before calling it.
- Being able to read a workspace Memory is insufficient to apply a correction;
  partial authority over a shared Support Set creates a Review.
- Workspace visibility is inherited from the incumbent. The correction is
  recorded honestly as `user_correction`, never as fabricated Teams, Jira,
  Confluence, or GitHub Evidence.
- SQLite and Cloud adapters implement the same Support hash, Review CAS,
  provenance preservation, and vector-outbox contract.
- Self-hosted OSS exposes and consumes `owner`; it no longer masquerades as a
  Cloud Workspace Admin.
