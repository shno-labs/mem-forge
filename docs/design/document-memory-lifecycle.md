# Document Memory Lifecycle

This is the domain reference for source-backed Memory authority, Support and
lifecycle actions. For the complete runtime flow, model responsibilities and
assessment flow, start with [Source sync to Memory](source-sync-to-memory.md).
The unified assessment contract is in [ADR 0034](../adr/0034-unify-incremental-support-and-claim-assessment.md);
immutable Evidence semantics remain defined by
[ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md).

## Memory, Evidence and Support

A Source Unit owns its scoped contribution to a Memory. A current Support
Assertion attaches one complete Evidence Unit: exactly one Primary and zero or
more Required references, jointly necessary for that claim. Context is separate.
Independent complete Evidence Units provide alternative support; partial pieces
from unrelated sources or access scopes cannot be combined to fabricate one.

A Memory's claim, source provenance, and support validity are different facts.
Equivalent claims from different documents may reuse a Memory identity while
retaining independent Evidence Units and Support. The compatibility proof and
current Support/authority snapshot govern reuse and mutation. Legacy
`memory_sources` extracted/corroborated edges are not the canonical v2 authority
model and cannot substitute for complete scoped Support.

Evidence pins immutable observed content. Current Source Unit membership may
reuse unchanged Observation revisions. A source update does not rewrite every
Evidence revision ID, and a document link is not necessarily a historical
Evidence snapshot link.

## Operations

| Operation | Meaning and boundary |
|---|---|
| ADD | Create an independently supported Memory only after admission and identity matching; an equivalent compatible target receives Support instead. |
| NOOP | Keep claim and identity. Current Evidence may still be reconstructed and scoped Support replaced atomically. |
| UPDATE | A complete same-identity refinement preserves all incumbent meaning and scope. The planner creates a replacement Memory record and supersedes the prior materialization with revision semantics. |
| SUPERSEDE | An explicit incompatible replacement has complete Evidence and destructive authority. Other independent Support or source gates can require Review. |
| REMOVE_SUPPORT / reconciliation DELETE | Remove the current operation's entire affected Support assertion. It is not physical Memory deletion; another complete valid Support can keep Memory active. |
| RETIRE | Remove a Memory from active use through a lawful Plan when its support/authority conditions allow; preserve lifecycle history and deliver index cleanup through the owning path. |

EQUIVALENT is not a wording-update permission. REFINES does not automatically
mean UPDATE: a narrower sibling can remain independent, and missing proof is
not proof of compatibility. CONTRADICTS is a relation, not permission to replace
another source's knowledge. Explicit historical/time or environment differences
must be considered before classifying a conflict.

## Reviews and asynchronous conflicts

Support validation baseline ownership is defined in
[ADR 0034](../adr/0034-unify-incremental-support-and-claim-assessment.md#support-validation-baseline-ownership-2026-09-07).
Pending Review alone neither proves nor prevents validation progress.

Review is a case over an action or relationship, not a universal Memory status.
A gated LifecycleReview can stage a hidden challenger and proposed mutations;
its approval/rejection goes through the complete Plan. A cross-source conflict
Review records a disagreement and does not automatically retire either Memory.
The review kind determines its postcondition; confirm/dismiss must not be
interpreted as approve/reject a destructive proposal.

A durable Review may protect only its exact explicitly contested prior-revision
Support. It does not turn that Support into verified current Evidence or exempt
unrelated stale edges. Terminal lifecycle changes stale applicable pending
Reviews in the same transaction. Approval resolves its own target Review before
applying the approved mutations, so rollback also rolls back the resolution.

Cross-document discovery is bounded and asynchronous after the authoritative
commit. A temporary interval of visible, unmarked conflict is accepted.
Different Source lineages with a verified contradiction can create a conflict
Review; a same-Source, different-document contradiction remains a non-destructive
relation. Neither path is an exhaustive global consistency check. See
[ADR 0009](../adr/0009-bound-cross-document-relation-discovery.md) for the
retrieval channels, work ownership and completion guards.

An existing single-proposal Review is not a multi-choice conflict-resolution
interface. Ambiguous competing refiners cannot be made safe merely by setting a
review flag on an ADD or NOOP. Preserve the current fail-closed boundary unless
one complete protected proposal can be represented.

## Commit and recovery ownership

MemoryEngine prepares assessments, complete Evidence and an action Plan outside
the transaction. MemoryStore and storage adapters apply Projection, Memory,
Support, Review and durable follow-up work atomically under current authority,
coverage and stale guards. Network model/provider/vector calls do not hold the
business transaction open. Vector outbox and RelationDiscoveryWork have their
own retry and completion boundaries.

A source-level run contains per-Unit commits; failure in one Unit does not roll
back unrelated successful Units. Current-source complete incumbent coverage
cannot be replaced by bounded cross-document search. Ordinary replay does not
resurrect terminal Memory; explicit authorized rebaseline recovery has its own
contract.

Detailed owners: [ADR 0017](../adr/0017-stage-recoverable-source-unit-derivation-before-lifecycle-commit.md),
[ADR 0019](../adr/0019-drain-vector-outbox-from-current-relational-truth.md),
[ADR 0023](../adr/0023-keep-review-orchestration-outside-memory-lifecycle.md), and
[ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md).
Scenario examples and per-step implementation differences are maintained once,
in the [complete flow](source-sync-to-memory.md).
