# Revision-bound evidence summaries

Status: Proposed experiment; no production cutover approved.
Date: 2026-10-05.

The user questioned whether exact excerpts and mandatory ref-to-ref mapping
are necessary to achieve readable, accurate cited Memories. This proposal
separates source provenance from knowledge continuity. It is evaluated beside
the [catalog/flexible-quote protocol](../research/2026-10-05-model-comparison-protocol.md),
not as a repair of its failed outputs.

## Runtime flow

Collection produces an authorized input snapshot. The owning adapter declares
its representation and source/visibility context. The application retains the
snapshot once, with immutable identity and a readable-resource path. The
configured LLM reads that input and emits atomic claims, one Primary support
summary and best-effort additional Required support summaries. The application
attaches the authoritative snapshot identity; the model never invents revision
IDs, URLs, byte coordinates or authority.

Citation presentation explicitly says **generated evidence summary** and
**whole-snapshot source scope**. It is not a verbatim quotation or a promise
that a precise paragraph was selected. A citation links to the actual retained
revision material. Optional existing source-native navigation anchors can aid
inspection, but their absence does not make a truthful claim unpublishable.

Primary describes the substantive source assertion supporting the central
claim. Required describes distinct additional support; it must not repeat
Primary or merely add related background. Multiple notes against one snapshot
do not establish independent sources. Retain the existing role vocabulary,
with this explicit change to citation granularity and display semantics.

On a new revision, the lifecycle process evaluates every affected same-source
incumbent claim against the new authorized input. A supported unchanged claim
can keep its Memory identity and gain Support bound to the new snapshot. A
changed claim proceeds through the existing Lifecycle Plan semantics. Unknown,
absence, contradiction and authority remain distinct; probabilistic similarity
cannot authorize destructive lifecycle action. Historical Support remains
bound to its original snapshot. **No old summary must map one-to-one to a new
summary.** Exact unchanged input reuse is an optimization, conditional on the
current source and access context, not semantic proof for changed inputs.

## Ownership and implementability

Source-specific syntax and meaning belong to their adapters. Generic code owns
snapshot integrity, caller access, model invocation, citation binding and
lifecycle transactions. A summary is derived content: its stored text/hash
does not prove the source supports it. Semantic accuracy must be measured
against authentic source, not against the model's own summary or self-review.

Current `SourceUnitRevision` is an append-only manifest of observation revisions;
it contains no body. Current `SourceUnitInput` retains the latest raw input
only, and its object URI can be overwritten. Some historical observation
content is complete enough for a representation; other adapters project only
selected fields. Therefore a revision label plus the current raw URI is not
an acceptable historical whole-document citation.

Production adoption requires a retained immutable snapshot of exactly the
authorized evidence representation the model used, associated with that
revision. Existing observation storage may serve this where complete and
faithful. Otherwise use immutable content-addressed source storage, with one
snapshot shared by its citations; do not duplicate documents per ref or
fabricate an old native payload from incomplete projections. Snapshot writing
and revision/Support commit must obey the existing ordering, retry, stale and
visibility contracts in OSS and every adapter. Managed input must retain its
authorized representation, not silently expand collection to private raw chats.

The quote-specific storage/view contract cannot be repurposed to claim that a
generated summary is a deterministic original-text rendering. A proposed
summary citation needs an explicit scope/display contract and shared API/store
parity. This experiment establishes neither that integration nor a migration.
Historical refs remain unchanged; the user accepts reprocessing for upgrade.

## Falsifiable experiment

Use the same complete native Confluence, Jira and real Markdown inputs as the
paired experiment. Freeze exact bytes, prompt, schema, replay dependencies,
current verified Sonnet factory and existing limits before inference. The model
returns content/type/metadata and Primary/Required summaries; the application
binds each to the actual evaluation snapshot SHA-256. This is a real retained
input identity, not an attested provider revision number. No program or model
attempts an excerpt range, summary-to-summary map, semantic post-processing or
admission pruning. Preserve provider message contents before schema validation
without capturing headers/credentials, refuse overwriting attempts after an
interruption, and record missing/unreadable message content explicitly. Preserve
the same shared structured-client transport policy as the paired experiment:
existing deterministic JSON parsing recovery and provider format-repair retries
remain enabled and are reported, rather than claimed absent. A response that
remains invalid under that policy stays a failure. Freeze the budget baseline
and runtime identity, and recheck actual configured request admission before
inference. Live credentials stay in memory; neither provider bindings nor
credential-bearing configuration are persisted.

The two independent source-first evaluators use their existing frozen
inventories. Summaries are evaluated as derived support notes, not original
quotes. Required recall is best effort; relevant/distinct proportion must reach
95%. No major claim or Primary-summary error, at least 95% useful coverage per
source, and faithful readable summaries are required. Provenance means the
correct snapshot is bound and readable; it does not give every summary a
semantic PASS. Preserve disputes about useful historical metrics separately.

Successful extraction would justify a bounded revision-assessment experiment
on complete incumbent sets, followed by authentic revision and persistence
acceptance. It would not establish stable future lineage, arbitrary-document
capacity, destructive safety or production readiness. Larger inputs still
face provider context limits; changing citation shape does not remove them.

This design does not introduce a new batching policy. Existing workload
planning remains a separate computation concern. No split, cap increase or
partial publication is used to make the experiment pass.
