# Agent Knowledge Bundle

Status: implemented V1 design, revised 2026-06-26

Agent Knowledge Bundle is the service-owned structure for Codex, Claude Code,
and future coding-agent session memories. V1 is intentionally narrow:
agent-session knowledge is private to the uploading user. Repository identity is
used for grouping, retrieval, and ranking, not for authorization.

The design keeps the existing MemForge principle:

```text
The local adapter captures evidence. MemForge owns memory decisions.
```

## Goals

- Avoid turning every transcript window into an isolated generated source.
- Give durable takeaways stable concept and claim identities.
- Let later windows move the same claim projection to the current memory row
  when lifecycle reconciliation supersedes older knowledge.
- Keep search fast by searching memory rows, not markdown files.
- Keep cloud tenancy simple: agent-session memories are private-only in V1.

## Non-Goals

- No workspace-shared agent-session memories in V1.
- No review queue for team-published session memories.
- No user hand-editing of concept markdown.
- No Jira, Confluence, or document-source migration to bundles.
- No replacement of the main memory search engine.

## Architecture

```text
Codex / Claude Code
  -> local adapter captures bounded evidence + repo metadata
  -> POST /api/agent-sessions/windows
  -> server canonicalizes, redacts, and hashes the window
  -> LLM extracts a durable session-outcome candidate or no_output
  -> server reconciles the candidate against existing private memories
  -> deterministic service validation
  -> DB-backed writes persist concept, claim, citation, and memory state
  -> markdown is rendered from DB state
  -> search returns private memory rows
```

There is no `/windows` path that generates a package and then starts a source
sync. The explicit `/api/agent-sessions/documents` endpoint still accepts an
already-generated document, but it is a separate upload mode and not part of the
window flow.

## Lifecycle

### 1. Local Adapter Capture

The Codex or Claude Code adapter reads a bounded window from the local session
and sends:

- client name, session id, trigger, workspace, branch, commit;
- repository identity, normalized later by the server;
- canonical or native evidence events;
- optional transcript fallback;
- a receipt describing the uploaded window.

The adapter does not choose whether something becomes memory. It does not write
concept files and does not decide which existing memory to update.

### 2. Server Intake

The server authenticates the request, resolves the principal, redacts obvious
secrets, canonicalizes events, computes a stable window hash, and checks
idempotency. The same window hash and range returns the prior processed result
instead of creating duplicate knowledge.

The server also normalizes `repo_identifier`, for example:

```text
git@github.tools.sap:hcm/memforge-cloud.git
  -> github.tools.sap/hcm/memforge-cloud
```

### 3. Session Outcome Extraction

The LLM's first job is extraction, not lifecycle ownership. It decides whether
the session window contains a durable private memory candidate and renders that
candidate into `claim_text` plus `durable_claim`.

The model must not be the owner of existing projection identity. It may describe
that a candidate updates or replaces earlier knowledge, but it must not be the
only component that can find the old `claim_id`.

### 4. Memory-First Reconciliation

MemForge reconciles a durable candidate against existing memories that are legal
for this window to consider:

```text
owner_user_id == current principal
visibility == private
repo_identifier == normalized repo identifier
```

The relation decision starts from memory rows, because memory rows are the
search and lifecycle surface. If a candidate supersedes an existing memory,
MemForge looks up the current `agent_claims` projection for that old
`memory_id`, reuses the existing `claim_id`, writes the new memory row, marks
the old memory superseded, and moves the projection to the new memory.

This is the bottom-up rule:

```text
session outcome -> memory candidate -> memory lifecycle -> claim projection
```

The projection never drives lifecycle by itself. It follows the memory result.

### 5. Structured Patch Proposal

The LLM returns an `AgentKnowledgePatchProposal` with one action:

```text
create_new_concept
add_new_claim
update_existing_claim
supersede_existing_claim
no_output
```

The proposal is intentionally a proposal. For backward compatibility it may
carry `concept_id` and `claim_id`, but the robust path does not require the LLM
to supply them. When lifecycle reconciliation selects an old memory, the service
derives the claim from the old memory projection.

Example:

```json
{
  "action": "update_existing_claim",
  "concept_id": "akb_concept_a1b2c3",
  "claim_id": "akb_claim_d4e5f6",
  "claim_text": "Workspace schedulers must start during app startup so overdue source schedules run without UI traffic.",
  "memory_type": "procedure",
  "tags": ["scheduler", "source-sync"],
  "confidence": 0.86,
  "citations": ["agent-window://codex/session-123/sha256-..."],
  "reason": "The new window corrects and confirms the existing scheduler startup claim."
}
```

### 6. Deterministic Validation

The service validates the proposal with simple hard rules:

- existing concept must belong to the current user;
- existing concept must be private;
- existing concept repo must match the current normalized repo;
- existing claim must belong to the proposed concept;
- a claim resolved from an old memory must point to a private same-user
  same-repo concept;
- empty claim text is skipped;
- `no_output` is recorded as processed but not durable.

These are not broad fallbacks. They are the small correctness boundary around
LLM placement.

### 7. DB-Authoritative Write

When a proposal is accepted, MemForge writes structured records:

```text
agent_concepts
  id, source_id, owner_user_id, visibility, repo_identifier,
  concept_type, concept_path, title, markdown_body,
  frontmatter_json, timestamps

agent_claims
  id, concept_id, display_anchor, claim_text, memory_type,
  tags_json, confidence, memory_id, timestamps

agent_claim_citations
  id, claim_id, citation_url, timestamps
```

The database is authoritative because it owns ACLs, migrations, indexes, and
stable IDs. Markdown is rendered from the database after writes. Markdown is
readable and exportable, but it is not the transactional source of truth.

### 8. Memory Row Reconciliation

Each durable claim projection points at exactly one current memory row through
`agent_claims.memory_id`.

- `create_new_concept` creates a concept, a claim, and a private memory row.
- `add_new_claim` adds a claim to an existing private concept and creates a new
  private memory row.
- `update_existing_claim` or `supersede_existing_claim` creates a new memory row,
  marks the old memory superseded, and moves the existing claim projection to
  the new memory.

The stable unit is:

```text
concept_id#claim_id
```

The memory row remains the search surface. Concept markdown is provenance and
human-readable structure.

### 9. Search Behavior

Search continues to search memory rows using the existing memory search path.
For cloud users, agent-session memories are filtered by normal private-memory
predicates, so user A cannot retrieve user B's agent-session memories.

Repo identity is useful when a client provides repo context, but it is not an
authorization boundary. It can help future ranking, filtering, or startup
context selection.

### 10. Paper Run: Why The Old Memory Was Not Superseded

```text
09:00
memory: "Jira validity dates should default offset-less datetimes to UTC"
claim_id: akb_claim_utc_fallback
memory_id: mem_old

11:00
new session decision: "Validity dates are date-only; do not use UTC fallback"
```

Old flow:

1. The prompt includes only a limited list of recent concepts and claims.
2. `akb_claim_utc_fallback` is absent from that prompt, or the model does not
   copy its exact id.
3. The model returns `create_new_concept` or `add_new_claim`.
4. The service has no old `claim_id`, so it never asks which memory should be
   superseded.
5. `mem_old` stays active.

The failure is not that claim projection cannot be updated. The failure is that
projection identity was the entry point into lifecycle, and the old projection
was missing from the model's small context.

### 11. Paper Run: Revised Flow

```text
09:00
claim_id: akb_claim_utc_fallback
memory_id: mem_old
text: "Jira validity dates default offset-less datetimes to UTC"

11:00
new candidate:
  durable_claim.rule = "Validity dates are date-only"
  durable_claim.scope = "Jira extracted memory validity fields"
```

New flow:

1. The model extracts the 11:00 candidate without owning the old claim id.
2. MemForge retrieves same-user same-repo private memory candidates.
3. Reconciliation selects `mem_old` as the memory being superseded.
4. MemForge resolves `agent_claims.memory_id == mem_old`, obtaining
   `akb_claim_utc_fallback`.
5. The write creates `mem_new`, marks `mem_old` superseded, and upserts
   `agent_claims.id == akb_claim_utc_fallback` so it points at `mem_new`.
6. Concept markdown is re-rendered from the current claim projection.

The claim id stays stable, but it is a projection id, not the mechanism that
discovers lifecycle.

### 12. Update Example

First session window:

```text
Evidence: scheduler startup failed because the app only claimed schedules after UI traffic.
Proposal: create_new_concept
Result:
  concept_id = akb_concept_scheduler
  claim_id   = akb_claim_startup
  memory_id  = mem_123
```

Later session window:

```text
Evidence: the same scheduler issue was fixed by starting the scheduler during app startup.
Candidate: akb_concept_scheduler with akb_claim_startup
Proposal: update_existing_claim
Validation: same user, private, same repo, claim belongs to concept
Result:
  agent_claims.akb_claim_startup is updated
  memory mem_456 is created
  memory mem_123 is marked superseded
  a citation to the new window is appended
```

The result is one evolving claim projection pointing at the current memory row,
not two active conflicting memories.

## Why This Is Not A Guardrail-Heavy Design

The robust part is the data model:

- concept IDs and claim IDs are stable;
- claim IDs point to memory IDs;
- writes are scoped by owner and repo;
- markdown is rendered from DB state;
- repeated windows are idempotent.

The validation layer is intentionally small. It prevents illegal writes and
records explicit outcomes. It does not hide failures behind broad compatibility
fallbacks.

## Testing Strategy

Unit and API tests should cover:

- creating a private concept, claim, citation, and memory row;
- updating an existing private claim by creating a new current memory row and
  superseding the old one;
- rejecting another user's concept;
- same-window idempotency;
- prompt context plus memory-row reconciliation for same-user, same-repo,
  same-client agent-session memories;
- cloud adapter contract methods for HANA.

The cloud HANA adapter must implement the same concept/claim/citation methods
as the OSS database so future storage backends can be tested against the same
contract shape.
