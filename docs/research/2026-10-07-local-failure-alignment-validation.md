# Local failure policy alignment validation

Date: 2026-10-07. Baseline: OSS `f9e3cb14`; Cloud `5865c3f`.

## Contract and outcome

The user reaffirmed extraction of new claims and citations, independent old-claim
Support Assessment, and value/deduplication-only Candidate Admission. Claim
faithfulness remains required; this removes a repeated admission judgment, not
Evidence authenticity or semantic quality requirements.

Restore ADR 0034 and the existing Diagram's local unjudgeable policy. Capacity
or persistently invalid output skips an isolated extraction ReadingGroup or
rejects an isolated Candidate for this round. Successful independent work may
commit in one atomic Lifecycle Plan. Incumbent Support is assessed independently;
unresolved old Support is preserved. Provider, timeout, request, source-binding,
identity/access and transaction failures prevent the Unit revision from committing.
Skipped material is revisited only on a later edit or explicit reprocess.

`projection-extraction-v22` and `candidate-admission-v7` isolate earlier pending
work. No schema, new lifecycle state, model stage, batch size, provider-specific
branch or destructive gate change is introduced.

## Deterministic evidence

The modified tests first reproduced 10 failures in planner, extraction,
admission and aggregation under the previous implementation. They exercise
whole native/Markdown structures, isolated capacity and invalid output, an
unknown candidate ID, invalid duplicate IDs, missing durable batch results,
rejection audit, durable admission work and exact Evidence binding failures.

An end-to-end SQLite test derives and reuses successful independent extraction,
then commits the next revision while retaining the incumbent and its Support.
Another combines local admission rejection and unresolved old Support while
adding independent knowledge. Durable commit-gate tests cover both valid and
unjudgeable admission work without adding a new work state.

Independent Spec review found that first-failure retention in shared context
aggregation could hide a later execution error. Shared runner aggregation now
lets any execution failure dominate an unjudgeable outcome, regardless of
context order. Six public runner cases force real context partitioning across
provider, timeout and request failures in both orders. Two engine cases prove
that a mixed failure commits no Memory, revision advancement or rejection audit.

## Verification

- 573 affected OSS checks pass across extraction requests/contract, admission,
  complete Support, Support/Relation coordination, projected lifecycle integration
  and store, sync bookkeeping, lifecycle guards, derivation work, revision work,
  and LLM batch runner.
- 536 Cloud checks pass in HANA workspace store, text-view delivery parity and
  revision lock-order tests, using the current OSS worktree on `sys.path`.
- Ruff and `git diff --check` pass.
- Shared Value constant reuse preserves admission instructions byte for byte:
  SHA-256 `8b42d971e73f8b9b0d74479e4b085fd0e5569c8e5e62109b540cc5422c01d0cb`.
  Extraction and other model prompt content is unchanged by this iteration.
- Two independent Codex review lanes covered Standards and Spec. The confirmed
  runner finding is fixed; the misleading planner union annotation and stale
  documentation version tuple are corrected. No accepted incremental blocker
  remains. Claude Code review was explicitly waived by the user.
- Diagram changes update responsibility labels only; flow connections are
  unchanged. The PNG was rendered and visually inspected with no clipping.

These deterministic checks verify application failure routing and lifecycle
boundaries, not model accuracy. Previous real-source online Sonnet observations
remain the semantic evidence; they are not rescored. The user's provisional
acceptance of the composite-to-subset inference error does not turn the original
replacement into a correct result or establish an error rate.

Checked Cloud deployment and live API/UI/installed-MCP evidence belongs in the
Cloud deployment handoff; static review is not deployment acceptance.
