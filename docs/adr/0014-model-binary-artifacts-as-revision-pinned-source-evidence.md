# Model binary Artifacts as revision-pinned Source Evidence

Status: Accepted (2026-07-23)

Amended: 2026-07-27 by [ADR 0017](0017-stage-recoverable-source-unit-derivation-before-lifecycle-commit.md);
2026-07-28 to define current-body Artifact membership and provider encoding
normalization.

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
   opens a bounded body stream only when the shared transfer module requests
   that descriptor;
2. the Artifact store writes and reads exact bytes by stable Artifact identity;
3. Source Projection represents each Artifact as a typed Source Observation
   whose current revision is derived from the authoritative byte hash;
4. Evidence and resource retrieval resolve the Artifact through that
   revision-pinned Source Anchor.

Provider-specific attachment URLs, pagination, authentication, and revision
formats remain inside Genes. Lifecycle, storage protocols, extraction, routes,
and MCP do not branch on Confluence, Jira, or any future provider.

For Jira Data Center secure-attachment locators, the attachment id is the
provider identity and the final path segment is only a display filename. The
Jira Gene rejects a secure-route id that differs from the descriptor id, then
retains the same-origin secure route and replaces its display segment with the
deterministic safe name `attachment-{id}` before streaming. This avoids
container-level rejection of historical filenames while preserving the exact
attachment id, bytes, media type, declared size, and revision. REST
content-by-id locators and non-secure attachment routes remain unchanged;
thumbnails are never substituted for originals.

### Current body reachability defines Artifact membership

A provider-owned attachment inventory is not itself current Source Evidence.
The owning Gene resolves authoritative Artifact-producing constructs from the
exact current source-body revision against a complete provider inventory and
returns only **Effective Source Artifacts** for materialization. An attachment
that remains owned by a page but is no longer referenced by its current body is
inventory residue: it is neither downloaded nor projected into the target
Source Unit revision.

Resolution is structural and provider-native. Confluence parses documented
storage-format constructs such as `ac:image` plus `ri:attachment`, then joins
the case-sensitive `ri:filename` to exactly one current attachment entity.
Both sides of this comparison receive the same single XHTML character-reference
decoding because Confluence may expose a storage-body character as Unicode
while returning its attachment title as an encoded entity. No broader Unicode,
case, whitespace, or path normalization is permitted. If this exact decoding
causes multiple entities to share a comparison key, resolution remains
ambiguous and fails closed. The filename is only a provider reference key for
this join; the resolved attachment ID and current provider revision remain the
durable Artifact identity. Duplicate body occurrences resolve to one Artifact.
Filename substrings, rendered download URLs, Markdown output, and browser
pixels never establish Artifact identity.

Artifact membership has explicit coverage. Complete coverage means every
supported Artifact-producing construct was resolved against authoritative
inventory; only then may omission of a previously current Artifact establish
removal. Missing or ambiguous inventory matches, malformed constructs, and
unsupported dynamic inventory filters fail closed without falling back to the
whole attachment inventory or to an empty authoritative set. External URL
images and attachments explicitly owned by another provider container remain
outside the current Source Unit rather than being copied under guessed
identity.

Provider-native collection constructs are supported only when their membership
can be reproduced deterministically. A local Confluence Gallery may resolve
the current page's images using its documented case-sensitive include/exclude
parameters. Label-filtered or cross-page Galleries require authoritative label
or container data; until that data is present, they are incomplete rather than
best-effort. Future body representations such as Atlas Doc Format require a
separate adapter at the same seam instead of reusing storage-format guesses.

An Artifact descriptor contains:

- stable provider Artifact key;
- parent provider Observation key;
- opaque provider revision when available;
- filename and authoritative media type;
- exact byte size only when the provider contract guarantees it for the
  revision-pinned response;
- provider locator needed only by the owning Gene.

Provider-reported estimates do not become integrity assertions. In particular,
Confluence `extensions.fileSize` may disagree with the bytes returned by a
version-pinned attachment download, so the Confluence Gene leaves the optional
exact-size field unset.

### Collection topology does not change the Artifact contract

A provider may be reachable from the service or only from the user's local
agent. Both topologies implement the same descriptor and byte contract.
Service-executed Genes stream provider bytes directly into the shared transfer
module. A local agent first submits provider bytes to one generic raw Artifact
intake, then submits its source package with the resulting immutable input
hashes. The service resolves those hashes only inside the same source,
workspace, current source-activity epoch, and Source Unit while the package
request itself holds a current local-agent lease. This permits safe immutable
deduplication across retries in one source epoch without letting a stale input
cross a reconfiguration or lifecycle fence. The resolved package reconstructs
the same `RawSourceArtifact` interface and verifies stored bytes against the
attested content hash when they are opened.

The local agent runs the provider's lightweight inventory or message collection
before materialization. It uploads Artifacts only for Source Units selected by
the fenced manifest, one Artifact at a time. Unchanged Jira issues, GitHub files,
and Teams windows therefore perform no attachment download or binary upload.
The package semantic attestation includes each Artifact provider key, provider
revision, and byte hash, while service-owned storage URIs remain internal.

Current provider capabilities are explicit:

| Source | Supported binary evidence | Exact boundary |
| --- | --- | --- |
| Confluence | Page image/PDF attachments | Version-pinned attachment response |
| Jira | Issue and comment image/PDF attachments in service and local-agent execution | Attachment id, revision, and exact issue/comment parent |
| GitHub Repository | Explicitly selected image/PDF repository files in cloud-pull and local-push execution | Immutable blob SHA and repository path |
| Microsoft Teams | Inline image hosted content in chats, channel roots, and channel replies | Exact message id plus hosted-content id; channel retrieval also requires the exact team id, and replies retain the root-message id required by the Graph route |
| Microsoft Teams file attachment | Not hosted content | SharePoint/OneDrive ownership and permission are a separate provider capability and must not be guessed from a message URL |
| GitHub Pages | No implicit referenced-image crawl | Use a GitHub Repository source when repository blob identity is required |
| Local Markdown | No implicit referenced-file crawl | Arbitrary Markdown links are not authoritative Artifact identities |
| Agent Session | No attachment contract | A future producer must supply stable attachment identity, revision, bytes, and parent Observation before this path is enabled |

Unsupported rows do not silently drop an enumerated Artifact: they define that
the source has no authoritative enumeration contract for that object class.
Extraction and lifecycle code remain provider-neutral and receive Artifacts
only from supported Gene capabilities.

The shared transfer module copies each body into a small-memory spooled file
while counting bytes and computing SHA-256. It verifies any exact declared,
transport-reported, and observed size, media type, identity, and revision before
projection, then rewinds the same file-like body for persistence. Unsupported
media types, oversized payloads, truncated downloads, identity drift, and
revision drift fail closed. Metadata alone never becomes content Evidence.
Local-agent collection additionally materializes only manifest-selected Source
Units and holds at most one bounded Artifact body while uploading it. Provider
responses are read incrementally where the provider client supports streaming;
APIs that return one encoded blob are rejected from their declared inventory
size before retrieval and remain subject to the same per-Artifact limit.

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
budgets. Provider inventory is paginated until the provider proves completion;
cursor cycles, non-advancing pages, malformed pages, and incomplete coverage
fail collection. Artifact count is an operational metric, not a correctness
limit. The initial storage defaults admit at most 64 MiB per Artifact and
128 MiB per Source Unit; these guard transfer, spool, and storage resources
rather than model input.

The prior design used the same 10 MiB per-Artifact and 30 MiB aggregate limits
for both persistence and inference because complete bodies were materialized as
`bytes`. That coupling is superseded. The initial inference defaults remain 10
MiB per Artifact and 15 MiB per extraction batch. The 15 MiB value is a
calibratable raw-binary worker/request safety budget, not a provider or MCP
protocol limit: encoded requests and decoded images consume materially more
memory than the compressed source bytes. Image structure, encoding/MIME
consistency, decompression pixels, and inference bytes are classified while the
bounded materialization spool is available. An Artifact that fails an
inference criterion but remains inside the storage contract is preserved
exactly with a safe ineligibility reason; it is not silently discarded or sent
to the model.

Historical revisions written before deterministic eligibility metadata remain
readable through one shared compatibility parser. Only the proven legacy shape,
where both eligibility fields are absent, uses that historical writer contract:
the Artifact is admitted only when its recorded size is inside the inference
byte budget. The intermediate writer that stored a boolean without a reason may
be interpreted as byte-limit ineligible only when the recorded size independently
proves that condition. An explicit null eligibility, a reason without an
eligibility decision, and every other missing or inconsistent combination are
invalid rather than guessed. Projection admission consumes this normalized
decision and does not reapply its own size-based eligibility rule; size remains
available separately for batch byte accounting. This compatibility does not
introduce migration, metadata versions, or another Artifact or lifecycle state.

Inference reuses the generic Projection extraction planner. One structured call
contains at most eight Primary Observations and satisfies the aggregate binary
byte budget, so a large image collection is coalesced into bounded multimodal
batches without dropping revision-pinned Artifacts or changing Source Unit
identity. The pipeline loads binary bodies only for the admitted batch, inside
the existing extraction admission slot; it does not retain all Source Unit
images while waiting for that slot. The pipeline never performs one
unconditional LLM call per attachment. Enumeration or storage limits do not
silently become model-input limits, and model-input limits do not discard
retrievable originals.

The structured LLM module owns the standard multimodal message shape, one
logical-call deadline, retry/fallback accounting, and schema validation.
Callers do not know provider message formats. If the configured model cannot
consume the accepted media contract, extraction fails visibly rather than
silently substituting attachment metadata.

The same structured multimodal response may return one concise selection
summary for an image supplied to the call. Each valid unique summary must name
one supplied Artifact Observation. Missing, duplicate, invented, or invalid
summaries are discarded and counted without invalidating otherwise valid
Memory candidates. The summary is bounded to 240 characters, omits unnecessary
customer, case, person, and credential identifiers, and describes only enough
visible purpose or content for an agent to choose whether to fetch the
Artifact.

The summary is stored as optional metadata on the exact immutable Artifact
Observation revision. It does not alter the revision identity, byte hash,
Evidence role, Support, retrieval ranking, or lifecycle authority. Historical
revisions without summaries remain valid and are not silently reprocessed.
Because the summary shares the existing extraction response, it adds no
steady-state logical LLM call, executor, queue, or retrieval-time model request.

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
streams only the URI recorded on that revision. It emits the authoritative
length and hash and verifies the streamed byte count and digest. Replaying a
previously observed URL after access is lost returns not found.

`get_resource` accepts Document and Source Artifact URLs through one parser.
File mode streams to a local cache file and rejects a byte-count or SHA-256
mismatch against authoritative response headers before publishing the path.
Base64 mode retains authoritative MIME and byte hash. For image media, the MCP tool result emits native MCP
`ImageContent` (`type=image`, base64 data, MIME type) plus compact text metadata;
it does not wrap the binary payload only inside JSON text.

Internal storage and REST representations retain revision, Evidence, and hash
fields for authorization and audit. The agent-facing MCP `get_memory`
projection exposes only the Artifact summary, Evidence role, filename, media
type, size, and resource URL. `get_memory` is a deterministic read and never
generates or repairs a summary. A missing summary therefore remains explicit
for historical or inference-ineligible Artifacts instead of triggering hidden
work.

## Consequences

Confluence and Jira become two adapters for one real seam. A future attachment
provider implements the same descriptor/materialization interface without
changing lifecycle, Evidence, retrieval, or MCP modules.

Local storage performs an atomic streamed copy from the validated file-like
body into a content-addressed revision path under the stable Artifact identity.
Cloud adapters use the same stable-identity-plus-hash key shape with their
managed file-like upload path. A new provider revision therefore cannot
overwrite bytes still referenced by an older immutable Observation revision.
Neither adapter requires a second complete in-memory copy, and retrieval uses
the shared streaming route rather than `read_artifact()` materialization.

The database gains no parallel Artifact ownership model. SQLite and HANA must
both implement exact revision lookup and the same visibility/currentness
semantics. Local filesystem and Cloud object storage must derive collision-
resistant paths from stable Artifact identity, never filename or title.

Acceptance tests live at the provider adapter, Artifact/Projection, and
agent-facing retrieval seams. They use known bytes and independent hashes,
exercise real storage adapters where available, and avoid treating mocked LLM
judgment as semantic proof. Deterministic tests enforce summary identity,
length, revision persistence, adapter parity, and MCP projection; the live
multimodal smoke verifies description usefulness and privacy.
A real EA Customer Support image and a real Jira screenshot must complete the
full MCP client path before this decision is considered deployed.

## References

- [ADR 0007: Bind extracted evidence to the current Source Projection](0007-bind-extracted-evidence-to-the-current-projection.md)
- [ADR 0011: Separate collection evidence from body materialization](0011-separate-collection-evidence-from-body-materialization.md)
- [ADR 0013: Bind document artifacts to stable Document identity](0013-bind-document-artifacts-to-document-identity.md)
- `memforge-cloud` Issue #193
- [Confluence attachment API](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-attachment/)
- [Jira attachment content API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-attachments/)
- [Microsoft Graph hosted content resource](https://learn.microsoft.com/en-us/graph/api/resources/chatmessagehostedcontent)
- [Microsoft Graph hosted content bytes](https://learn.microsoft.com/en-us/graph/api/chatmessagehostedcontent-get)
- [GitHub repository contents API](https://docs.github.com/en/rest/repos/contents)
- [GitHub Git blobs API](https://docs.github.com/en/rest/git/blobs)
- [MCP tool result content](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
