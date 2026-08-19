# Domain Context

## Workspace selection

- **Workspace Directory** — The principal-scoped list of workspaces the caller may know about, including current active/selectable state. Listing it is discovery, not a prerequisite for data-plane requests.
- **Requested Workspace** — An explicit `workspace_id` supplied on one HTTP or MCP operation. It is validated without revealing inaccessible workspaces.
- **Local Workspace Binding** — A user-confirmed client-side mapping from a Git repository or ordinary directory to a workspace. It supplies a request selector without sending the local path or granting authority.
- **Hook Workspace Fallback** — An optional client-local workspace used only by automatic hooks when no project binding or pinned session selection exists. It never scopes an interactive operation.
- **Authorized Workspace Context** — The single workspace selected, authorized, and bound to one data-plane request. Handlers and durable work consume this context rather than resolving workspace again.
- **Workspace Selection Source** — The reason the Authorized Workspace Context was chosen: Requested Workspace or the caller's singleton accessible workspace.
- **Repository Context** — Repository attribution used for provenance and retrieval relevance. It never selects or authorizes a workspace.
- **Self-Hosted Owner** — The single authenticated owner of the OSS `local` workspace. It has local management capabilities without borrowing a Cloud Workspace Membership Role. _Avoid_: Local Workspace Admin

## Source synchronization

- **Source Lifecycle** — Whether a configured source is active or paused. Lifecycle is independent of where collection executes and whether the current device can perform that collection.
- **Local Execution** — Collection work that must run through the source owner's MemForge daemon on a user-controlled device.
- **Device Readiness** — Whether the source owner's local daemon is recently connected and able to accept collection work.
- **Connection Readiness** — Whether a source-specific connection dependency, such as an authenticated browser session, is usable or requires user action.
- **Local Source Readiness** — The user-facing result derived from Device Readiness and Connection Readiness for a source that uses Local Execution. It never replaces Source Lifecycle.
- **Source Readiness** — The compact source-row outcome derived from execution location, Device Readiness when collection is local, and Connection Readiness when the connector exposes it.
- **Source Sync Activity** — The user-visible lifecycle of current or recent work to bring one source up to date. It can cover both collection from the source and processing into memories.
- **Collection** — Reading source items and, when required, transferring them from the execution device to MemForge.
- **Collection Manifest** — An attempt-scoped declaration of stable Source Item identities and opaque revisions. It describes discovered membership without carrying every item body.
- **Collection Coverage** — The proof attached to one collection result: a Complete Snapshot covers the whole configured scope, a Bounded Delta covers only explicit changes since a checkpoint, and Partial coverage proves neither absence nor a safe checkpoint advance.
- **Candidate Checkpoint** — A provider position proposed by collection but not made current until the corresponding Source Projection and lifecycle transaction succeeds.
- **Processing** — Turning collected source items into stored documents and memories.
- **Attachment Inventory** — The current provider entities owned by a source item, whether or not the item's current body references or displays them. Inventory membership alone does not make an attachment current Source Evidence.
- **Body Artifact Reference** — An authoritative reference from one exact current source-body revision to a provider Artifact. It preserves the provider's reference semantics rather than inferring reachability from filenames, URLs, or attachment ownership.
- **Effective Source Artifact** — A current provider Artifact reached through a resolved Body Artifact Reference and pinned to its exact provider identity and revision. Only Effective Source Artifacts enter current materialization, Source Projection, and derivation.
- **Artifact Membership Coverage** — Whether every Artifact-producing construct in one current source-body revision was resolved against authoritative provider inventory. Only Complete coverage makes an omitted prior Artifact an authoritative removal.
- **Progress Snapshot** — The latest trustworthy statement of an activity's phase and measurable progress. It is a current observation, not a history of progress events.
- **Determinate Progress** — Progress with a trustworthy total, presented as completed out of total.
- **Indeterminate Progress** — Progress whose total is not yet knowable, presented without a percentage while still reporting useful counts when available.

## Agent evaluation

- **Agent Operation** — One logical, versioned product work item whose input is stable across internal retries and recovery executions. For Source lifecycle reconciliation it is one exact Source Unit projection plus its pinned candidate, incumbent, Support, gate, and contract inputs; it is not one model call, relation pair, or lifecycle mutation.
- **Agent Execution** — One durable execution of an Agent Operation. Internal provider or document retries remain inside the same execution until its owner commits a terminal result. A later scheduler or lease recovery is a new Agent Execution of the same Agent Operation.
- **Agent Attempt** — One internal try within an Agent Execution. Attempts may contribute bounded diagnostics and counts, but a handled failed attempt is not itself a failed Agent Operation.
- **Agent Terminal Outcome** — The single final runtime fact for one Agent Execution after its internal retry policy finishes. A terminal outcome records what the product did; it is not an evaluation score or accepted ground truth.
- **Agent Runtime Event** — An immutable, content-free product record of an Agent Terminal Outcome or another explicitly admitted high-value runtime occurrence. Its product identity and source lineage remain authoritative when traces are absent or sampled.
- **Agent Assessment** — A versioned code, model, or human judgment targeting an Agent Runtime Event or Agent Evaluation Result. A missing assessment is unknown, never pass.
- **Agent Evaluation Case** — One immutable, authorized offline replay input promoted from a durable Agent Runtime Event or curated evidence. It pins exact lineage and protected artifacts rather than mutable current product state or retained telemetry.
- **Accepted Ground Truth Revision** — One append-only human-approved or deterministic reference for an Agent Evaluation Case. A runtime anomaly, external Score, or LLM judgment does not become ground truth automatically. _Avoid_: Accepted Ground Truth, golden answer
- **Agent Evaluation Cohort** — One immutable, explicitly enumerated set of Agent Evaluation Case and Accepted Ground Truth Revision pairs used for comparable evaluation runs. It is not a live query or mutable dataset view. _Avoid_: Current dataset
- **Agent Evaluation Run** — One pinned candidate and optional baseline execution over one Agent Evaluation Cohort. It is evaluation work, not a Source Sync or Agent Execution.
- **Agent Evaluation Result** — One immutable candidate output or execution failure for a case and replicate in an Agent Evaluation Run. Semantic judgments about it remain separate Agent Assessments. _Avoid_: Assessment, ground truth
- **Online Agent Evaluation** — Automatic, non-blocking assessment of admitted facts from real product executions. Its normal path is content-free and deterministic; sampled semantic or human follow-up is asynchronous and does not rewrite the product outcome. _Avoid_: Production approval, live release gate
- **Offline Agent Evaluation** — Explicit execution of a pinned candidate and evaluator contract over an immutable Agent Evaluation Cohort. It may compare a baseline or inform a release decision, but it cannot mutate Source, Memory, or lifecycle state. _Avoid_: Source Sync, production retry
- **Agent Evaluation Execution** — Service-owned execution of one Agent Evaluation Run, durably admitted before a long-running worker claims it. CLI, HTTP, UI, schedulers, and CI are control-plane callers rather than execution owners. _Avoid_: CLI evaluation process, Langfuse experiment authority
- **Agent Evaluation Release Gate** — A versioned policy decision over one complete, pinned offline run and optional paired baseline. Unknown or incomplete evidence cannot become pass, and Langfuse availability cannot determine the verdict. _Avoid_: Online assessment, aggregate quality score

## Memory provenance

- **Memory Origin Kind** — The derived category describing how one provenance source introduced knowledge into MemForge: **Direct User** for an explicit user lifecycle action, **Managed Capture** for a system-managed coding-agent capture, or **Configured Source** for a user-configured ingestion connection. It does not replace Source Type, Client, Repository Context, ownership, or visibility.
- **Direct User** — Knowledge explicitly confirmed through a user lifecycle action such as creating or correcting a Memory. The submitting coding agent is the Client, and an associated repository is Repository Context; neither becomes the Source.
- **Managed Capture** — Knowledge produced from a system-created capture Source, such as an Agent Session Source, without requiring the user to configure an ingestion connection.
- **Configured Source** — Knowledge produced from a user-configured ingestion connection such as Confluence, Jira, Teams, GitHub Repository, or Local Repository.

## Memory retrieval

- **Requested Retrieval Intent** — An optional query-scoped hint selected by an Agent Client from the user's conversational goal. It may request General Hybrid Retrieval, Known Item Lookup, or Relationship Exploration, but cannot weaken visibility, provenance, or facet constraints.
- **Resolved Retrieval Intent** — The validated query-scoped purpose that selects ranked retrieval behavior from the user's goal rather than from the query language or an individual retrieval mechanism. The service resolves General Hybrid Retrieval, Known Item Lookup, or Relationship Exploration from a valid Requested Retrieval Intent or a deterministic fallback.
- **General Hybrid Retrieval** — Ranked retrieval for an open-ended natural-language query, including when the query and relevant Memory use different languages. Semantic, content lexical, metadata lexical, and relationship evidence remain independent contributors rather than mutually exclusive modes. Avoid: _Semantic lookup, lexical lookup_.
- **Known Item Lookup** — Ranked retrieval for a specifically named or identified item, such as an external identifier, title, or code symbol. An Agent Client keeps the query self-contained and quotes an exact title or name when conversation context supplies one; the service may use that explicit identity for bounded metadata recall while preserving the full query for the other channels. It expresses the user's expected target, not a lexical-only implementation.
- **Relationship Exploration** — Ranked retrieval whose primary goal is to discover Memories connected through entities or relationships. It does not bypass normal visibility or provenance constraints.
- **Deterministic Listing** — A separate current-state enumeration constrained by an explicit time window and optional Source facets, without relevance ranking or an invented query. It is not a Resolved Retrieval Intent. Avoid: _Empty search, queryless semantic search_.

## Memory lifecycle migration

- **Lifecycle Migration Inventory** — A backend scan of every active Configured Source in the datastore, without applying a caller's source-discoverability filter. Agent Session sources are candidates when the Lifecycle Gate is not Enabled or the bidirectional Active Same-Source Support Invariant is violated in either direction. Inventory output contains identifiers and counts, never private source content or owner identity.
- **Active Same-Source Support Invariant** — Support authority and its source provenance projection are bidirectionally complete for active configured-source Memories: every `memory_sources` edge has active same-source Support, and every active Support has the exact `memory_sources` edge for its Evidence document. An Enabled gate does not override either violation.
- **Support Provenance Projection** — The `memory_sources` read model used by source facets, source-card counts, timestamps, access filtering, and document provenance. It materializes exact active Support membership but is not lifecycle authority; a cross-document Relation without Support does not create this projection.
- **Lifecycle Migration Attempt** — One idempotent durable recovery job identified by an explicit attempt label. Unprovable lineage remains a durable open finding and keeps destructive lifecycle gated; semantic similarity cannot close it.
- **Non-Migrating SQLite Open** — An existing SQLite workspace opened through `Database.connect(run_migrations=False)`. It uses SQLite read-only/query-only mode, does not create the database or parent directories, and does not create schema or run migrations. It is for operator evaluation, never normal serving or repair.

## Memory review

- **Review** — An auditable request for a human-authorized decision when MemForge cannot safely complete or classify a Memory change on its own. Review status records whether that request is pending or terminal; it is not a Memory lifecycle state.
- **Review Decision** — One action allowed by a Review's kind and presentation, together with its exact lifecycle postcondition. The same approve or reject storage result can represent different user-facing decisions only when the presentation states those consequences explicitly.
- **Decision Fingerprint** — A deterministic digest of the Review identity, pinned participants, and proposed decision input. A caller must present the current fingerprint when applying a decision so analysis of an older Review cannot mutate newer state.
- **Decision Manifest** — A bounded, caller-supplied set of Review Decisions and Decision Fingerprints proposed for validation or confirmed application. It is request data, not a durable workflow, lifecycle state, or all-or-nothing transaction.
- **Cross-Source Conflict Review** — A Review of a proposed contradiction between two independently supported active Memories. Confirming or dismissing the finding closes the Review but does not select source authority or retire either Memory.
- **Memory Correction Proposal** — A user-confirmed proposed canonical replacement for one current Memory. An authorized actor may apply it immediately; otherwise it remains a hidden challenger in a Review. The proposal never changes visibility or Source provenance by pretending to originate from the incumbent Source.
- **Correction Authority** — The capability to apply a Memory Correction Proposal directly. A private Memory Owner has it for their own Memory; a Source Owner, Cloud Workspace Admin, or Self-Hosted Owner has it only when they can manage the complete active supporting Source set. _Avoid_: Admin flag, Source ownership

## Connector authentication

- **Teams Access Token** — A short-lived bearer credential that authorizes one local Teams collection session against a specific Teams service audience.
- **Teams Browser Session** — A persistent, user-authenticated Teams Web session that can acquire fresh Teams Access Tokens without another visible sign-in while enterprise SSO remains valid.
- **Silent Session Renewal** — Renewal of a Teams Access Token through the Teams Browser Session without presenting authentication UI to the user.
- **Interactive Reauthentication** — A visible Teams Web sign-in required when the Teams Browser Session can no longer renew silently because enterprise SSO, MFA, or access policy requires user interaction.

## Source organization

**Project**:
A semantic relevance grouping for memories and their sources inside a workspace. A Project is not a personal list organization mechanism or an access boundary.
_Avoid_: Collection, folder, source group

**Source**:
A configured connection that contributes source items and memories to a workspace.
_Avoid_: Integration instance, connector row

**Source List View**:
A user's presentation of Sources in one workspace. It may filter, sort, or prioritize Sources without changing their configuration or Project binding.
_Avoid_: Collection

**Pinned Source**:
A Source prioritized for one user within its existing Project group. Pinning neither moves nor duplicates the Source and has no effect on other users.
_Avoid_: Favorite collection, promoted source

**Source List Sort**:
A user's ordering preference applied independently inside each Project group after Pinned Sources have been prioritized.
_Avoid_: Source priority

**Source Search**:
An ephemeral narrowing of the Source List View by Source name, source type, or Project. Searching does not change persisted Source organization.
_Avoid_: Source query

## GitHub Repository scope

- **Repository Access** — Where GitHub API access executes. `cloud_pull` uses MemForge Cloud credentials and network access; `local_push` uses the source owner's daemon, local `gh` session, VPN, and network access. It never changes the data origin: both modes read the configured remote GitHub repository. Avoid: _Local clone mode, local repository_.
- **Repository Base Scope** — The positive boundary of a GitHub Repository source. An empty `include_paths` list means the whole repository; otherwise only the selected remote folders and files are candidates. Avoid: _Local folder selection_.
- **Repository Exclusion** — A selected remote folder or file removed from the Repository Base Scope. Exclusions win over inclusions and apply to all descendants. A child below an excluded path cannot be re-included. Avoid: _Ignore hint, inferred outdated content_.
- **Effective Repository Scope** — The deterministic set of remote files remaining after base scope, exclusions, and extension filters are applied. Suggested exclusions require explicit user confirmation and never change this set automatically.
- **Repository File Identity** — Built-in GitHub Repository collection identifies a file by canonical repository path because Git has no immutable file ID. A path move is a removed file plus a new file unless a future/provider adapter supplies explicit authoritative rename evidence; matching blob SHA alone never proves a move because copy plus delete is ambiguous.
