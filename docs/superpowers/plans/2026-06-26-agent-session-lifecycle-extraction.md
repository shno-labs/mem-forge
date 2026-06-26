# Agent Session Lifecycle-First Extraction Plan

> **For agentic workers:** implement with TDD. Keep the first slice small:
> memory lifecycle owns supersession; claim projection follows the selected
> memory result. Do not add a claim lineage column unless the existing
> `agent_claims.id` projection identity proves insufficient.

**Goal:** Fix agent-session memory updates so stale memories can be superseded
even when the LLM did not receive or copy the old `claim_id`.

**Architecture:** The LLM extracts a durable session-outcome candidate. MemForge
reconciles the candidate against existing private same-user same-repo memories.
When reconciliation supersedes an old memory, the service resolves the current
claim projection by `old_memory_id`, reuses that `claim_id`, and moves the
projection to the new memory.

**Tech Stack:** Python, async SQLite, existing `MemoryStore`, existing evidence
lifecycle records, pytest/pytest-asyncio. Cloud HANA parity is required only for
new database protocol methods.

## File Structure

- Modify `docs/design/agent-knowledge-bundle.md`: document lifecycle-first
  extraction and paper runs.
- Modify `src/memforge/agent_knowledge.py`: resolve update/supersede targets
  from matched memory projections when model-supplied claim ids are absent.
- Modify `src/memforge/memory/store.py`: expose a narrow semantic candidate
  lookup for agent-session claim memories.
- Modify `src/memforge/storage/database.py`: add current claim lookup by
  `memory_id`.
- Modify cloud HANA adapter/protocol only if the lookup becomes part of the
  shared cloud workspace contract.
- Test `tests/test_agent_knowledge_bundle.py`: add regression for claim-id-free
  update resolution and projection movement.

## Tasks

- [ ] Step 1: Add failing OSS test where an update proposal has no `claim_id`,
  vector retrieval returns the old memory, and the service reuses the old claim.
- [ ] Step 2: Add SQLite lookup from memory id to the current agent claim.
- [ ] Step 3: Add a narrow `MemoryStore` retrieval helper for active private
  agent-session memories in the same owner/repo scope.
- [ ] Step 4: Update `AgentKnowledgeBundleService` so update/supersede actions
  without ids resolve through memory candidates before rejecting scope.
- [ ] Step 5: Update cloud HANA parity if the new lookup is required by cloud.
- [ ] Step 6: Run focused tests and `git diff --check`.

## Acceptance Criteria

- Existing id-based update/supersede behavior continues to pass.
- New claim-id-free update/supersede behavior reuses the existing
  `agent_claims.id` and moves that row to the new memory.
- If no safe memory target is found for an update/supersede proposal without
  ids, the service fails instead of creating a duplicate.
- No new lifecycle column is introduced.
- Cloud HANA remains contract-compatible when the cloud store is used.
