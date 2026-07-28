# Stage recoverable Source Unit derivation before lifecycle commit

Status: Accepted (2026-07-27)

Amended: 2026-07-28 to define lifecycle handling for authoritatively removed
supporting Observations.

## Context

Source synchronization currently treats four different facts as one
page-level success value:

1. the provider item and Artifact inventory were enumerated;
2. exact Artifact bytes were validated and stored;
3. every bounded LLM derivation batch returned a valid response;
4. one complete Memory lifecycle plan was applied with the target Source
   Projection.

That coupling makes remote inference a hidden prerequisite for preserving
authoritative provider evidence. One failed extraction batch discards valid
outputs from every other batch, leaves the target Source Projection
uncommitted, and forces a later source sync to repeat provider transfer and
successful model work. Optional Artifact selection summaries also participate
in the same failure decision even though they are not Evidence.

A production Confluence run exposed all variants at once: count-based Artifact
admission rejected otherwise valid pages, an undecodable image failed its whole
batch, missing Artifact summaries invalidated Memory extraction, and generic
structured-response validation failures erased successful sibling batches.
The worker and queue remained healthy.

Structured-output providers guarantee a JSON shape only within their supported
schema subset. They do not guarantee semantically complete or correct values,
so application validation remains required. A transaction that includes a
remote model call is therefore not a database transaction. Durable staging and
idempotent consumption are required to close the gap between immutable source
input and a later local commit.

## Decision

### Keep three independent completeness contracts

The pipeline uses three different contracts and never substitutes one for
another:

- **Projection Coverage** describes what the provider collection observed.
  `Partial Projection` continues to mean an incomplete provider view only.
- **Artifact Eligibility** records whether one authoritative Artifact was
  materialized and whether its exact stored revision can participate in the
  configured inference contract.
- **Derivation Coverage** records the terminal disposition of every Primary
  observation in one immutable target Source Unit revision.

Derivation Coverage has one entry for every required Primary observation:

- `derived` — every batch segment for the observation completed and produced
  validated model judgments;
- `not_inference_eligible` — exact source bytes remain stored and retrievable,
  but deterministic validation proved that the revision cannot be sent to the
  configured model contract;
- `pending` — at least one required batch has no terminal result;
- `retryable_failure` — a bounded attempt failed because of provider,
  transport, timeout, or structured-response validation;
- `superseded` — a newer staged target or source-activity epoch made the
  derivation stale before commit.

`derived` and `not_inference_eligible` are terminal. A derivation is closed only
when every required Primary observation has a terminal disposition.
`not_inference_eligible` never authorizes destructive Memory lifecycle action
for incumbents whose authority depends on that observation. The complete
Lifecycle Plan keeps those exact Support edges and records an existing
Finding/Review reason for the unresolved current revision. It may still commit
independent, fully derived observations from the same Source Unit.

`pending` and `retryable_failure` do not authorize a Lifecycle Plan. They retain
the staged target and completed sibling batches for a later bounded attempt.

### Review authoritatively removed support before advancing Projection

A complete proposed Source Projection can prove that an Observation which
currently supports an active Memory is no longer a member of its Source Unit.
An incumbent audit `NOOP` does not override that structural fact. Before
building the Lifecycle Plan, the engine converts that operation into a
review-gated support-removal proposal.

The exact incumbent Support remains active and contested while the Review is
pending, so no historical Evidence is invented or silently discarded. The
atomic apply may advance the complete Projection because the existing support
invariant recognizes that exact pending Review as the explicit disposition of
the old edge. Approval or rejection later uses the normal lifecycle review
contract. Partial Projection, unresolved provider membership, and ambiguous
identity never prove removal and cannot enter this path.

### One deep Source Unit Derivation module

The external seam is one operation:

```python
class SourceUnitDeriver:
    async def derive(
        self,
        request: SourceUnitDerivationRequest,
    ) -> SourceUnitDerivationResult: ...
```

The request identifies one immutable target Source Unit revision, its base
revision, the complete proposed Source Projection payload, the staged Document
snapshot, exact stored Source Artifacts, the source-activity epoch, and an
extractor contract version. Callers do not plan model batches, persist batch
outputs, merge retry state, validate optional summaries, or decide whether a
Lifecycle Plan has complete derivation authority.

The result exposes:

- the derivation identity and status;
- complete Derivation Coverage;
- validated Memory candidates only when coverage is closed;
- valid optional Artifact summaries;
- safe failure codes and field paths;
- aggregate metrics without prompt, response, content, image, locator, or
  credential payloads.

The implementation hides deterministic planning, durable staging, bounded
parallel model calls, idempotent batch-result reuse, inference eligibility,
summary validation, safe diagnostics, and final assembly. SQLite and HANA are
adapters at one internal persistence seam.

### Stage before remote work; commit current state once

Before the first remote model call, the datastore atomically stages:

- the exact proposed Source Projection payload and its exact payload hash;
- a separate stable Projection identity hash that excludes operational run id,
  checkpoint, and observation timestamps;
- base and target Source Unit revision identities;
- source-activity epoch and extractor contract version;
- the staged Document snapshot required to resume without a provider read;
- one deterministic manifest row per derivation batch.

The staged projection is not yet the current Source Projection. Current
Document, Source Projection, Evidence, Support, and Memory lifecycle remain on
the last complete revision while retryable work is incomplete.

Batch identity is derived from the target Source Unit revision, extractor
contract version, Primary Observation revision identities, and deterministic
segment ranges. It never contains the operational sync run id. Retrying the
same immutable target therefore reuses completed outputs and executes only
missing or failed batches.

Derivation identity additionally includes the stable context identity and
source-activity epoch. The primary derivation ID is the sole datastore
uniqueness boundary: a superseded attempt never prevents a new activity epoch
from deriving the same provider revision under a new access or configuration
contract.

The staged Document context follows the same rule: its complete snapshot has an
exact payload hash, while a separate identity hash includes only stable content,
access, and source-activity inputs. Identity hashes decide safe reuse; exact
payload hashes detect stored snapshot corruption. The two are never
interchangeable.

Each successful batch result is written before another remote call is required.
The record contains validated candidate values and valid optional summaries,
not prompt or raw response payloads. A crash can repeat at most the in-flight
call; it cannot erase previously completed batches.

Stable identity excludes only operational sync-run fields, observation
timestamps, and optional Artifact summaries produced by this derivation. Exact
payload hashes still protect the durable recovery snapshot from corruption;
stable identity hashes authorize reuse and the final commit. Optional summaries
are authorized separately by the completed, hash-verified batch output that
produced them.

When Derivation Coverage closes, the pipeline assembles one complete candidate
ledger and one complete Lifecycle Plan. There is no single-Observation or
single-batch bypass around this boundary. One local datastore transaction then:

1. verifies the source-activity epoch, base Source Unit revision, target
   Projection identity, full derivation-context identity, staged Document
   identity, active Support hashes, and Memory versions;
2. writes the identity-equivalent staged Document as current;
3. advances the identity-equivalent complete Source Projection;
4. applies the complete Lifecycle Plan;
5. marks the derivation `applied`.

A stale or superseded derivation cannot update any current pointer or Memory
state. Retrying an already applied derivation is an idempotent no-op.

This is a transactional staging/outbox use inside the existing workspace
database. It is not a second Source Artifact or Memory lifecycle state machine:
Source Observation and Lifecycle Plan records remain the only current evidence
and mutation authorities.

### Compose candidate uniqueness from bounded decision ledgers

Candidate uniqueness is a proof over every extracted candidate, but the proof
does not require one model response to contain every decision. Before model
work, candidates receive a deterministic specificity precedence based on
normalized content length, Memory type, content, and original position. The
complete candidate inventory remains visible to every decision batch, while
each response is responsible for exactly one bounded set of candidate indices.

A candidate index is datastore-owned identity and is never emitted by the
model. Each batch uses a fixed response object whose named slots are all
schema-required. The request maps active slots to candidate indices and unused
slots to null; the model returns only the ordered judgment or null required by
each slot. Code binds active slots back to their indices. Duplicate,
out-of-range, omitted, or model-invented decision-row identities are therefore
not representable by a schema-valid response. Canonical target indices remain
model judgments and are validated against the lower-precedence rule.

A redundant candidate may point only to a lower-precedence index. This makes
the decision graph acyclic without relying on model compliance across batches.
After all bounded batches validate, a deterministic reducer resolves each
canonical chain to a terminal KEEP decision, validates one complete global
ledger, and restores the original candidate order. No candidate enters
reconciliation until that global completeness proof closes.

This bounds response cardinality independently from Source Unit cardinality.
Raising the output-token limit, retrying an oversized monolithic response,
truncating candidates, or accepting a partial ledger is not an accepted
recovery path.

### Compose reconciliation completeness from bounded ledgers

Lifecycle reconciliation completeness is a proof over all candidates and all
active incumbents; it is not a requirement that one model response contain the
entire Cartesian comparison. Every input size uses the same two protocols and
is partitioned without dropping candidates into:

1. bounded candidate-by-incumbent relation cells, each of which returns exactly
   one decision in every active candidate slot in that cell; and
2. one independent bounded support audit for every incumbent.

The deterministic reducer authorizes ADD only after a candidate has crossed
every incumbent cell. It rejects ambiguous destructive matches, merges
compatible duplicate NOOP relations, and requires each candidate relation to
agree with the independent incumbent-support audit. Every cell and audit must
validate before the existing atomic Lifecycle Plan may be built.

The two phases use different fixed-slot structured response schemas. Candidate
slots and incumbent-audit slots are schema-required named fields. The request
maps active slots to datastore-owned identities and unused slots to null; code
binds judgments back to those identities. A candidate relation cannot emit its
candidate index or a Memory ID. It may choose only a bounded incumbent slot as
its semantic target and cannot express DELETE. An incumbent audit cannot emit
a Memory ID or candidate identity and can express only NOOP or DELETE. Missing,
duplicated, out-of-range, or model-invented row identities are therefore not
representable by a schema-valid response. Prompt instructions are not the
identity or phase boundary; the schema and request-owned slot maps are.

The previous combined-list protocol and its candidate-indexed decision arrays
are removed from the lifecycle path. Keeping a smaller-input list protocol
would preserve the same identity ambiguity that fixed slots eliminate for
larger inputs.

This separates semantic completeness from provider response size. Increasing a
token limit, retrying one oversized response, truncating candidates, or treating
a missing decision as ADD would weaken the proof and is not an accepted recovery
path.

### Make model schemas contain judgments only

The structured LLM response contains only values the model must judge:

- claim content and type;
- confidence, entity mentions, and validity dates;
- exact quoted text when the evidence is textual;
- the selected Primary Observation identity;
- required Context Observation identities;
- optional Artifact selection summaries.

Internal values such as `evidence_anchor`, `extraction_context`, Evidence role,
revision identity, and Source Anchor kind are absent from the model-facing
schema. The derivation module computes them deterministically from the selected
Observation and evidence form after validation.

Artifact summary validation is independent from Memory candidate validation.
Each valid, unique summary for a supplied image may be retained. Missing,
duplicate, unknown, oversized, or otherwise invalid summary entries are
discarded and counted safely; they never invalidate a valid Memory candidate.
A missing summary remains an explicit optional metadata absence.

### Classify image eligibility before batch planning

Exact image bytes are inspected during provider-neutral Artifact
materialization, while the bounded spool is already available. Successful
storage and inference eligibility are separate outcomes.

An image may be stored with `inference_eligible=false` and a safe deterministic
reason such as unsupported encoding, invalid image structure, decompression
limit, or inference byte limit. The original exact bytes, MIME type, size, and
hash remain revision-pinned and retrievable. The planner never includes such an
Artifact in a remote model request.

Integrity failures that make the stored bytes untrustworthy still fail
materialization. Inference failures do not masquerade as storage failures.

### Bound work, not source cardinality

Artifact enumeration uses provider pagination until the provider proves the
inventory complete. Materialization streams or spools one bounded Artifact at
a time and retains per-Artifact and aggregate byte policies. Inference keeps
its existing per-Artifact, per-batch byte, and active-working-set budgets.

An arbitrary per-page Artifact count is not a correctness boundary and is
removed. Count may remain a metric and an operational warning, but it cannot
silently truncate inventory or permanently reject an otherwise byte-bounded
Source Unit.

Provider pagination must detect cycles, non-advancing cursors, malformed pages,
and incomplete coverage. Those are provider collection failures, not Artifact
count policy.

### Resume before recollection

A source activity first resumes current, non-stale staged derivations for that
source. Because the proposed projection, Document snapshot, stored Artifact
URIs, and batch manifest are durable, this path does not read the provider or
repeat completed model batches.

After bounded derivation recovery, normal provider collection runs and may
stage a newer target. An explicit source reconfiguration or activity-epoch
change supersedes incompatible staged work. Ordinary provider change after the
last observation is handled by the next collection exactly like any completed
sync; it does not invalidate the fact that the staged revision was
authoritative when observed.

## Rejected alternatives

### Reuse Partial Projection for model failure

Rejected. Projection Coverage states provider visibility and removal authority.
Using it for downstream inference would make an exact complete provider result
look incomplete and would mix two independent evidence claims.

### Apply one Lifecycle Plan per successful extraction batch

Rejected. Cross-batch candidate uniqueness, incumbent coverage, required
context, and destructive lifecycle safety are Source Unit concerns. A
successful batch cannot prove that an incumbent owned by a failed sibling batch
may be changed or removed.

### Keep synchronous page atomicity and retry the whole page

Rejected. It repeats provider download and successful model work, makes remote
availability part of source-evidence durability, and has no durable boundary
for crash recovery.

### Commit Source Projection current before derivation

Rejected as the default. It would make current Source Observation revisions
advance while active Support remains on the previous revision without a
complete Lifecycle Plan or explicit unresolved-evidence disposition. Staging
preserves the existing current-state invariant and still retains exact target
evidence for recovery.

### Treat optional summaries as required response completeness

Rejected. A selection hint is not Evidence and cannot decide whether valid
Memory claims or Source Projection lineage commit.

### Add provider-specific count exceptions or fallback models

Rejected. Provider-specific exceptions preserve the shallow coupling, and a
fallback model does not repair transaction ownership, durable progress, or
semantic validation.

## Consequences

Source sync can distinguish provider collection failure from pending or failed
Memory processing. UI and durable run status report the phase and safe failure
class rather than describing every downstream problem as an unsynced page.

Failed remote derivation no longer loses authoritative Artifact identity or
successful sibling work. Current Memory lifecycle remains atomic and
stale-guarded. Permanently inference-ineligible evidence remains retrievable and
cannot silently authorize destructive mutation.

The datastore gains recoverable staging records and batch manifests. Both
SQLite and HANA must implement the same identities, state transitions,
idempotency, stale guards, and query semantics. This added storage is justified
by removing repeated provider/model work and by making the remote/local
transaction split explicit.

The model-facing schema becomes smaller and more portable across structured
output providers. Application validation still remains mandatory because
schema-valid output can be semantically invalid.

## Acceptance

- A deterministic multi-batch test proves that one retryable failure preserves
  completed sibling results, stages the exact target, leaves current lifecycle
  unchanged, and resumes only failed work.
- A reconciliation-matrix test proves that a candidate population larger than
  one model response is completely partitioned across bounded relation cells,
  receives one independent incumbent-support audit, and produces one merged
  operation per candidate without truncation.
- A stale target and a changed source-activity epoch both fail before current
  state changes.
- Closed coverage with an inference-ineligible Artifact preserves its exact
  bytes and protects affected incumbent Support.
- Complete coverage that removes a supporting Observation stages an exact
  pending Review and advances Projection without silently retiring the Memory;
  partial or ambiguous coverage cannot do so.
- Missing, duplicate, invented, or invalid optional summaries cannot invalidate
  valid candidates and are never persisted.
- The model-facing schema has no internal evidence-anchor field.
- Provider-neutral tests cover more than 100 Artifacts without count-based
  rejection while byte and active-working-set limits remain enforced.
- SQLite and HANA adapter contract tests prove equivalent staging, batch
  completion, resume, supersession, and apply behavior.
- Cloud deployment and a bounded live cohort prove durable state, UI phase,
  Source Projection/Lifecycle convergence, vector delivery, and worker RSS.

## References

- [ADR 0007: Bind extracted evidence to the current Source Projection](0007-bind-extracted-evidence-to-the-current-projection.md)
- [ADR 0012: Deepen the extraction lifecycle hot path](0012-deepen-the-extraction-lifecycle-hot-path.md)
- [ADR 0014: Model binary Artifacts as revision-pinned Source Evidence](0014-model-binary-artifacts-as-revision-pinned-source-evidence.md)
- [Google Gemini structured output validation](https://ai.google.dev/gemini-api/docs/structured-output)
- [LiteLLM structured outputs](https://docs.litellm.ai/docs/completion/json_mode)
- [AWS transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
- `memforge-cloud` Issue #277
