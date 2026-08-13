# Stage recoverable Source Unit derivation before lifecycle commit

Status: Accepted (2026-07-27)

Amended: 2026-08-13 to require structural-unit selectable text to map into the
single current Source Observation authority. When a provider's rendered
Document view adds text outside that Observation, planning uses projection
batches over the Observation revision instead. The extraction contract advances
so staged output from the prior authority boundary is not reused.

Amended: 2026-07-31 to require canonical claim Evidence localization before a
successful batch output becomes durable. Provider-returned quotes from an older
extractor contract cannot be reused as if they satisfied the canonical excerpt
contract.

Amended: 2026-07-31 to make provider-neutral work planning part of the deep
Source Unit Derivation module. The work kind and its bounded input identity are
now durable manifest data rather than a transient caller branch.

Amended: 2026-07-30 to advance the projection extraction contract when the
shared candidate-language semantics changed. Completed batch output may be
reused only under the exact extractor contract that produced it.

Amended: 2026-07-28 to define lifecycle handling for authoritatively removed
supporting Observations and complete relation/audit disagreements, and to bound
Candidate Ledger request input independently from Source Unit cardinality.

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

The deriver selects one of three provider-neutral work shapes before staging:

- one textual Observation with a safe small-diff plan uses one changed-range
  work item and validates every returned exact quote against the current
  changed ranges;
- one textual Observation that requires full-document extraction is partitioned
  into deterministic structural Markdown units only when the rendered Document
  text maps into that Observation authority; otherwise it uses an Observation
  projection batch;
- multiple Observations, or any Artifact-bearing projection, retains
  Observation/Artifact projection batches.

Callers execute the work item chosen by the deriver but do not choose or
reconstruct that plan. The work kind, changed-hunk or structural-unit identity,
and exact content hashes participate in the manifest and derivation identity.
Recovery therefore resumes only outputs produced for the same immutable
Projection, context, strategy, and extraction contract. Changing this planning
contract advances the extraction contract version.

If diff-guided work raises or returns a terminal extraction error, the deriver
persists that failed attempt and stages one alternative structural-work
manifest for the same immutable target. The document update remains
`diff_guided`; an explicit derivation work-strategy override selects structural
execution without changing the lifecycle meaning of the update. The override
is operational and is excluded from stable lifecycle-context identity, while
the structural batch hashes still produce a distinct derivation identity.
Successful structural fallback supersedes the failed diff attempt. Callers do
not implement or reconstruct this policy.

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

A material extraction prompt or response-schema change advances the extractor
contract version. The new version changes derivation and batch input identity,
so a staged output produced under an older semantic contract cannot be reused
as if it satisfied the new contract. This invalidation applies only when a
derivation is planned or resumed; it does not manufacture changed observations
or reprocess an already-applied, unchanged Source Projection.

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
The record contains validated candidate values, canonical claim Evidence
excerpts, and valid optional summaries, not prompt or raw response payloads.
Provider-returned `evidence_quote` and `extraction_context` are not two durable
authorities. A crash can repeat at most the in-flight call; it cannot erase
previously completed batches.

Stable identity excludes only operational sync-run fields, observation
timestamps, and optional Artifact summaries produced by this derivation. Exact
payload hashes still protect the durable recovery snapshot from corruption;
stable identity hashes authorize reuse and the final commit. Optional summaries
are authorized separately by the completed, hash-verified batch output that
produced them.

Observation membership is unordered in the Source Unit revision identity.
New Source Unit revisions therefore persist Observation revision IDs in
canonical sorted order. When an identity-equivalent historical revision
already exists with the same exact member set in a different order, projection
reuses that immutable row verbatim. Provider enumeration order and retry order
cannot create a second payload for the same revision ID; a different member set
still fails the immutable identity check.

Observation revision identity includes the bounded inference contract that
changes how its content may support a claim. In particular,
`claim_evidence_scope` participates in the semantic hash: adding atomic-claim
scope to an unchanged Teams message or Jira comment creates a new immutable
revision instead of attempting to enrich an old row in place. Operational
metadata such as author, timestamps, and provider display fields remains
outside semantic identity so harmless enrichment does not cause re-extraction.

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
Recovery may encounter an older completed attempt after another attempt for
the same immutable Projection scope has already committed its deterministic
Lifecycle Plan. The committed plan is authoritative: recovery marks the older
attempt `superseded` and skips extraction and reconciliation. It must not call
the model again and then compare a newly inferred payload with the already
applied plan.

One immutable Projection scope may also have more than one non-terminal
derivation context when an earlier execution persisted the target Projection
and a later retry deliberately changed execution strategy, for example from
diff-guided to full-document derivation. Those contexts are alternatives, not
independent lifecycle work. Before recovery, the pipeline keeps only the latest
context for each source-activity epoch, Source Unit, target revision, and stable
Projection identity, and marks older contexts `superseded`. Progress counts
only the selected contexts. This prevents an obsolete strategy from failing
again before its later fallback can run, while preserving the complete target
Projection, Evidence authority, and one atomic Lifecycle Plan.

This is a transactional staging/outbox use inside the existing workspace
database. It is not a second Source Artifact or Memory lifecycle state machine:
Source Observation and Lifecycle Plan records remain the only current evidence
and mutation authorities.

### Compose bounded candidate admission without a Source Unit count limit

Candidate admission is a quality operation over every extracted candidate, not
lifecycle or provenance authority and not a proof that no semantic duplicate
exists anywhere in the Source Unit. Exact normalized-content deduplication
remains complete and deterministic over the whole Source Unit. Semantic
admission then gives every exact-unique candidate one disposition through
bounded request and response batches.

Before model work, candidates receive deterministic specificity precedence
based on normalized content length, Memory type, content, and original
position. Each decision batch sees only its bounded candidate set and is
responsible for exactly those candidate indices. A batch may shrink below its
bounded decision-batch limit to satisfy the request-context budget. Total
Source Unit candidate cardinality is never a request budget and never a
document failure condition.

A candidate index is datastore-owned identity and is never emitted by the
model. Each batch returns an ordered decision array. Application code requires
its length to equal the active candidate count, then binds each array position
back to the corresponding candidate index. Missing or excess judgments reject
the response; no model-emitted decision-row identity is accepted. Canonical
target indices remain model judgments and are validated against both the
lower-precedence rule and the candidate set visible in that request.

A redundant candidate may point only to a visible lower-precedence index. This
makes each decision graph acyclic without relying on model compliance. After
all bounded batches validate, a deterministic reducer resolves canonical
chains to terminal KEEP decisions, verifies that every exact-unique candidate
has one disposition, and restores the original candidate order. No candidate
enters reconciliation until that coverage proof closes.

A semantic duplicate outside the bounded comparison set is conservatively
kept. Missing a quality optimization cannot discard knowledge or authorize a
destructive lifecycle action. Existing candidate identity admission,
same-source reconciliation, and Relation/Review contracts remain responsible
for their own complete safety proofs.

Candidate admission is also non-authoritative when the structured client
cannot return a valid response after its provider fallback. Code closes that
bounded batch locally with KEEP for every active candidate, continues later
batches, and records only fixed fallback batch/candidate counts. It does not
persist provider text or treat the failed quality optimization as lifecycle
authority. A response that reaches application validation but violates the
exact-coverage or canonical-target contract remains a deterministic contract
failure rather than being silently accepted.

The structured client may spend one configured transport-retry token on a
second JSON-text attempt when both the native-schema response and first
JSON-text fallback reached the provider successfully but failed Pydantic schema
validation. The retry remains inside the same logical deadline and telemetry
budget. It does not retry ambiguous multi-object framing, deterministic
application-contract failures, provider outages beyond their existing retry
policy, or any response after the budget is exhausted.

The same bounded admission judgment may reject a candidate as low value only
when the candidate is merely instance output or source-recoverable detail and
does not preserve a reusable decision, rule, invariant, conclusion, or
procedure. Low-value rejection is distinct from redundancy and has no
canonical target. Uncertainty, partial overlap, or conflicting claims resolve
to KEEP; conflict handling belongs to Relation/Review rather than admission.

This bounds request and response cardinality independently from Source Unit
cardinality. Raising a global candidate limit, raising the output-token limit,
retrying an oversized monolithic request, truncating candidates, or accepting
a partial disposition ledger is not an accepted recovery path.

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

When every required relation cell and support audit is complete and valid but
their dispositions disagree for one incumbent, the disagreement is a complete
Lifecycle Review decision rather than failed derivation coverage. A candidate
replacement paired with an audit KEEP stages that exact replacement for Review;
a candidate KEEP paired with an audit support removal stages that exact removal
for Review. The pending Review retains the incumbent's exact active Support,
while non-conflicting decisions in the same complete Lifecycle Plan may commit
and the Source Projection may advance.

Missing slots, invalid identities, multiple destructive candidate targets, and
incomplete incumbent coverage do not become Reviews. They remain failed
reconciliation because no single complete proposal exists for a reviewer to
approve or reject.

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

Artifact revisions created before this classifier are interpreted only through
the historical writer contract centralized in the Source Artifact module.
Missing eligibility is not proof of ineligibility: the pre-classifier contract
admits the revision only within its recorded inference byte budget. A legacy
false value without a reason is accepted only when that same size proves the
byte-limit reason. Lifecycle and derivation callers consume this one parsed
result and do not compose their own legacy field combinations.

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
- A Candidate Ledger test proves that a structured-client failure keeps every
  candidate in only that bounded admission batch, records safe fallback counts,
  and continues later batches without exposing response content.
- A reconciliation-matrix test proves that a candidate population larger than
  one model response is completely partitioned across bounded relation cells,
  receives one independent incumbent-support audit, and produces one merged
  operation per candidate without truncation.
- A stale target and a changed source-activity epoch both fail before current
  state changes.
- Reordering an unchanged provider Artifact inventory reuses the exact prior
  Source Unit revision and cannot create an immutable-identity retry conflict.
- Upgrading the inference scope of an unchanged Teams message or Jira comment
  creates a new immutable Observation revision, while operational metadata
  enrichment continues to reuse the prior revision.
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
