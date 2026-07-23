# Model binary Artifacts as revision-pinned Source Evidence

Status: Accepted (2026-07-23)

## Context

Source providers can attach screenshots, diagrams, PDFs, and other binary
objects to a page, issue, comment, message, or equivalent parent object.
Existing collection retains only the parent Document body and presentation
metadata. An attachment-upload event can therefore prove that a file was
uploaded, but it cannot support a claim about the file's contents.

Document raw, normalized, and PDF artifacts are presentation forms of one
Document. A provider attachment is different: it has its own provider identity,
revision, bytes, media type, and lifecycle while remaining inside the parent
Source Unit. Treating attachments as Documents would distort document
membership and counts. Treating them as unstructured metadata would make exact
Evidence, authorization, and resource retrieval fragile.

The user-facing contract is end to end:

`search -> get_memory -> get_resource -> exact bytes and MIME -> MCP client`

Every hop must preserve the same Artifact revision and active Evidence lineage.

## Decision

### One deep Source Artifact module

The shared implementation defines a small provider-neutral interface:

1. a Gene enumerates immutable Artifact descriptors for one fetched item and
   materializes the bytes for descriptors selected by the pipeline;
2. the Artifact store writes and reads exact bytes by stable Artifact identity;
3. Source Projection represents each Artifact as a typed Source Observation
   whose current revision is derived from the authoritative byte hash;
4. Evidence and resource retrieval resolve the Artifact through that
   revision-pinned Source Anchor.

Provider-specific attachment URLs, pagination, authentication, and revision
formats remain inside Genes. Lifecycle, storage protocols, extraction, routes,
and MCP do not branch on Confluence, Jira, or any future provider.

An Artifact descriptor contains:

- stable provider Artifact key;
- parent provider Observation key;
- opaque provider revision when available;
- filename and authoritative media type;
- byte size when available;
- provider locator needed only by the owning Gene.

Materialization verifies the declared identity, size, media type, and content
hash before projection. Unsupported media types, oversized payloads, truncated
downloads, identity drift, and revision drift fail closed. Metadata alone never
becomes content Evidence.

### Reuse Source Observation lifecycle authority

An Artifact is projected as a `binary_artifact` Source Observation inside the
parent Source Unit. Its Observation revision is the durable Artifact revision:

- the semantic hash is the exact byte hash;
- immutable revision metadata records the stored URI, authoritative media type,
  filename, size, provider revision, and parent Observation identity;
- the Observation content is an empty textual value because binary bytes are
  never embedded in relational JSON or prompt text;
- a whole-observation Source Anchor identifies the exact Artifact revision.

No parallel Artifact lifecycle state machine, replay ledger, provider-specific
LifecyclePlanner branch, or duplicate attachment Document is introduced.
Existing RevisionDelta membership, semantic, and access axes handle attachment
add, edit, delete, retry, and visibility changes. Existing Source Projection
foreign keys and stale guards remain authoritative.

The immutable Observation revision metadata is the Artifact record. A dedicated
Artifact table is unnecessary because exact lookup is by the already indexed
Observation revision identity, and lifecycle/currentness is already owned by
Source Projection. Storage adapters expose one Artifact lookup method rather
than leaking metadata JSON queries to callers.

### Exact Evidence and multimodal extraction

Visual extraction is optional and bounded per Source Unit. The extractor
receives current image Artifacts as typed media inputs alongside textual Primary
and Context Observations. It may emit a claim only when it names the Artifact
Observation as Primary Evidence. The Evidence Reference uses a whole-observation
Anchor; no synthetic quote or OCR text is fabricated to satisfy a text-only
contract.

Text claims continue to require exact textual localization. Visual claims use
the Artifact Anchor and store a content-free Evidence excerpt. Required
text/image observations may accompany the Primary Artifact using the existing
Evidence roles.

Enumeration, persistence, and inference have separate provider-neutral
budgets. A Gene scans at most 200 provider descriptors, then admits at most 100
supported Artifacts whose exact bytes also satisfy the 10 MiB per-Artifact and
30 MiB per-Source-Unit limits. Unsupported descriptors consume only the scan
budget, not the supported Artifact budget.

Inference reuses the generic Projection extraction planner. One structured call
contains at most eight Primary Observations, so a large image collection is
coalesced into bounded multimodal batches without dropping revision-pinned
Artifacts or changing Source Unit identity. The pipeline never performs one
unconditional LLM call per attachment. Enumeration or storage limits do not
silently become model-input limits, and model-input limits do not discard
retrievable Evidence.

The structured LLM module owns the standard multimodal message shape, one
logical-call deadline, retry/fallback accounting, and schema validation.
Callers do not know provider message formats. If the configured model cannot
consume the accepted media contract, extraction fails visibly rather than
silently substituting attachment metadata.

### Retrieval and MCP transport

`get_memory` resolves active Support Evidence. When an Evidence Anchor targets
a current `binary_artifact` Observation revision, the source detail includes an
Artifact resource descriptor containing the exact resource URL, revision
identity, media type, filename, size, and byte hash.

Active Support authorizes the complete revision-pinned Evidence bundle, not
only the one Reference that grants support. Artifact lookup first resolves an
active Support to its Evidence Unit, then returns current binary Artifact
References from that same unit. The returned Evidence role remains explicit:
`primary` and `required` can grant authority, while `context` remains associated
reading material and must not be promoted to supporting evidence. This lets an
agent retrieve an image that was inspected alongside a text-grounded claim
without weakening the claim's authority or inventing a second Support edge.

The Artifact route accepts the immutable Observation revision identity, applies
the same workspace/source visibility predicate as the supported Memory, and
reads only the URI recorded on that revision. Replaying a previously observed
URL after access is lost returns not found.

`get_resource` accepts Document and Source Artifact URLs through one parser.
File mode writes an exact local cache file. Base64 mode retains authoritative
MIME and byte hash. For image media, the MCP tool result emits native MCP
`ImageContent` (`type=image`, base64 data, MIME type) plus compact text metadata;
it does not wrap the binary payload only inside JSON text.

## Consequences

Confluence and Jira become two adapters for one real seam. A future attachment
provider implements the same descriptor/materialization interface without
changing lifecycle, Evidence, retrieval, or MCP modules.

The database gains no parallel Artifact ownership model. SQLite and HANA must
both implement exact revision lookup and the same visibility/currentness
semantics. Local filesystem and Cloud object storage must derive collision-
resistant paths from stable Artifact identity, never filename or title.

Acceptance tests live at the provider adapter, Artifact/Projection, and
agent-facing retrieval seams. They use known bytes and independent hashes,
exercise real storage adapters where available, and avoid mocked LLM judgment.
A real EA Customer Support image and a real Jira screenshot must complete the
full MCP client path before this decision is considered deployed.

## References

- [ADR 0007: Bind extracted evidence to the current Source Projection](0007-bind-extracted-evidence-to-the-current-projection.md)
- [ADR 0011: Separate collection evidence from body materialization](0011-separate-collection-evidence-from-body-materialization.md)
- [ADR 0013: Bind document artifacts to stable Document identity](0013-bind-document-artifacts-to-document-identity.md)
- `memforge-cloud` Issue #193
- [Confluence attachment API](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-attachment/)
- [Jira attachment content API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-attachments/)
- [MCP tool result content](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
