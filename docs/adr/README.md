# Architecture decision log

This directory records durable shared MemForge decisions. Start with
[design ownership](../README.md#design-ownership) for the maintained subsystem
flows, or use the index below to find the rationale for a specific contract.
Cloud records link shared OSS decisions and describe Cloud-only consequences.

## Reading and maintaining records

Read a record's status, amendments and replacement links before applying it.
Some records retain superseded assumptions; a proposal or accepted design does
not establish that implementation or deployment has passed validation. The
[Source sync to Memory flow](../design/source-sync-to-memory.md) and its linked
designs distinguish current implementation from target behavior.

Follow the repository's [architecture decision ownership](../../AGENTS.md#architecture-decision-ownership)
and the user's approved design. Update the relevant record in the same PR when
validated work materially changes or clarifies that decision; retain important
supersession context. Avoid rewriting existing records solely to normalize their
format. Use a separate record when a distinct architectural decision benefits
from its own rationale, and check current records and open work before choosing
its number. [_template.md](_template.md) is an optional starting point.

Keep execution backlog and deferred features in GitHub Issues. Link design and
validation evidence from the relevant issue or PR rather than maintaining a
second status register here. This index lists every numbered record, including
historical records; status and relationships remain in each record.

## Decisions

| ADR | Decision |
| --- | --- |
| [0001](0001-project-source-sync-activity-from-existing-execution-records.md) | Project source sync activity from existing execution records |
| [0002](0002-renew-teams-access-through-a-dedicated-browser-session.md) | Renew Teams access through a dedicated browser session |
| [0003](0003-keep-source-list-organization-personal.md) | Keep Source List organization personal and orthogonal to Projects |
| [0004](0004-use-proven-authoritative-snapshots-for-rebaseline.md) | Use proven authoritative snapshots as the rebaseline corpus |
| [0005](0005-preserve-provider-identity-across-scope-transitions.md) | Preserve provider identity across explicit scope transitions |
| [0006](0006-bound-memory-identity-recall-before-semantic-proof.md) | Bound Memory identity recall before semantic proof |
| [0007](0007-bind-extracted-evidence-to-the-current-projection.md) | Bind extracted evidence to the current Source Projection |
| [0008](0008-prune-only-proven-disjoint-incumbents.md) | Prune only proven-disjoint incumbents before reconciliation |
| [0009](0009-bound-cross-document-relation-discovery.md) | Bound cross-document relation discovery before semantic classification |
| [0010](0010-keep-support-provenance-projection-complete.md) | Keep the support provenance projection complete |
| [0011](0011-separate-collection-evidence-from-body-materialization.md) | Separate collection evidence from body materialization |
| [0012](0012-deepen-the-extraction-lifecycle-hot-path.md) | Deepen the extraction lifecycle hot path |
| [0013](0013-bind-document-artifacts-to-document-identity.md) | Bind document artifacts to stable Document identity |
| [0014](0014-model-binary-artifacts-as-revision-pinned-source-evidence.md) | Model binary Artifacts as revision-pinned Source Evidence |
| [0015](0015-keep-the-oss-public-beta-local-only.md) | Keep the OSS public beta local-only |
| [0016](0016-keep-manual-memory-creation-independent-of-repository-roots.md) | Keep manual Memory creation independent of repository roots |
| [0017](0017-stage-recoverable-source-unit-derivation-before-lifecycle-commit.md) | Stage recoverable Source Unit derivation before lifecycle commit |
| [0018](0018-settle-mcp-roots-before-workspace-routed-tool-calls.md) | Resolve request-scoped repository context before workspace-routed tool calls |
| [0019](0019-drain-vector-outbox-from-current-relational-truth.md) | Drain the Memory-vector outbox from current relational truth |
| [0020](0020-list-current-memories-with-a-request-bound-keyset.md) | List current Memories with a request-bound keyset |
| [0021](0021-select-workspaces-at-the-v1-request-boundary.md) | Select workspaces at the v1 request boundary |
| [0022](0022-resolve-ranked-search-intent-from-validated-client-hints.md) | Resolve ranked search intent from validated client hints |
| [0023](0023-keep-review-orchestration-outside-memory-lifecycle.md) | Keep Review orchestration outside Memory lifecycle |
| [0024](0024-separate-lexical-candidate-eligibility-from-term-rarity.md) | Separate lexical candidate eligibility from term rarity |
| [0025](0025-correlate-online-quality-events-with-source-derivation.md) | Correlate agent runtime facts, telemetry, and evaluation |
| [0026](0026-separate-online-assessment-from-offline-evaluation-execution.md) | Separate online assessment from offline evaluation execution |
| [0027](0027-unify-explicit-memory-correction-under-authority.md) | Unify explicit Memory correction under resolved authority |
| [0028](0028-separate-conversation-coverage-from-content-and-retention.md) | Separate conversation coverage from content and retention |
| [0029](0029-manage-local-collection-as-a-user-service.md) | Manage local collection as an operating-system user service |
| [0030](0030-compile-revision-pinned-evidence-fragments.md) | Compile revision-pinned Evidence Fragments |
| [0031](0031-distribute-personal-local-oss-as-an-installed-tool.md) | Distribute personal-local OSS as an installed tool |
| [0032](0032-guard-local-data-upgrades-with-recoverable-migrations.md) | Guard local data upgrades with recoverable migrations |
| [0033](0033-retire-sources-without-erasing-support-v2-history.md) | Retire sources without erasing Support v2 history |
| [0034](0034-unify-incremental-support-and-claim-assessment.md) | Unify incremental Support and claim assessment within the existing lifecycle |
| [0035](0035-preserve-current-agent-session-capture-wakeups.md) | Coalesce Agent Session capture under one on-demand owner |
| [0036](0036-separate-semantic-work-from-inference-executors.md) | Separate semantic work from inference executors |
| [0037](0037-record-cross-document-conflicts-as-relations.md) | Record cross-document conflicts as relations, not Reviews |
| [0038](0038-make-evidence-unit-support-the-only-support-model.md) | Make Evidence Unit Support the only Support model |
| [0039](0039-create-memories-within-the-source-unit.md) | Create Memories within the Source Unit |
| [0040](0040-keep-stored-input-current-and-isolate-derivation-recovery.md) | Keep stored input current and isolate derivation recovery |
| [0041](0041-record-stored-input-on-the-source-unit-revision.md) | Record stored input on the Source Unit revision |
| [0042](0042-fence-source-writes-with-activity-leases-alone.md) | Fence Source writes with activity leases alone |
| [0043](0043-assign-model-judgments-by-task-shape-and-share-one-decision-contract.md) | Assign model judgments by task shape and share one decision contract |
| [0044](0044-build-the-admin-ui-v2-beside-v1-and-remove-v1-after-a-parallel-run.md) | Build the admin UI V2 beside V1 and remove V1 after a parallel run |
| [0045](0045-prove-document-absence-from-a-listing-not-from-the-run-kind.md) | Prove document absence from a listing, not from the run kind |
| [0047](0047-define-claim-evidence-extraction-outcomes.md) | Define claim and Evidence extraction outcomes before implementation |
