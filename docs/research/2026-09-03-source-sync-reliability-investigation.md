# Source sync reliability investigation

Date: 2026-09-03. Status: researched recommendation, not approved implementation or deployed fix.

Scope: read-only runtime/provider checks and local, isolated reproductions. No ingestion replay, Source configuration change, Memory mutation, lifecycle rewrite, or upstream repository edit was performed. Local diagnostic fixtures do not call an LLM.

Code baseline: OSS `5aba41a8ef37a87a3abd1a887d5e71d97018b380`; Cloud `776937cd685e9c58dab8a680a61d384c3a95e448`.

## GitHub collection: immutable bytes before text normalization

### Finding and existing contract

There are two separate inconsistencies, not one generic retry problem:

1. Cloud text discovery records each file's blob SHA from the repository tree, but text fetch uses `contents/{path}?ref=main`. The branch can change between these requests. The current identity guard correctly rejects the newer response instead of mixing revisions. The request strategy makes an avoidable race possible.
2. An exact live Contents response advertised the expected blob SHA and 4,992-byte size but its Base64 body decoded to 5,017 bytes. Reading that same object through Git Blobs returned exactly 4,992 bytes and verified against the Git object SHA. This is reproducible provider representation behavior, not an evaluator false positive.

The first problem is reproducible in the existing unit test, but this does **not** establish that a branch movement caused the historical top-level README failure; that historical response was not recovered. The second problem is directly reproduced against the affected object.

The accepted [collection ADR](../adr/0011-separate-collection-evidence-from-body-materialization.md) already requires resolving the ref to an immutable commit/tree and materializing required bodies by pinned object identity. The implementation is asymmetric:

| Path | Discovery and materialization today |
| --- | --- |
| Cloud text | `GitHubRepoGene.discover()` stores tree blob SHA; `fetch()` calls mutable Contents URL; `normalize()` decodes UTF-8 with replacement. |
| Local daemon text | `_resolve_github_collection_snapshot()` pins commit/tree; `_github_blob()` reads by SHA; collection then decodes strict UTF-8. |
| Cloud binary Artifact | `open_source_artifact()` already streams immutable `git/blobs/{sha}` through the Artifact interface. |

Code: [Cloud discovery/fetch/normalize](../../src/memforge/genes/github_repo_gene.py), [shared response validation](../../src/memforge/github_repo_utils.py), [daemon snapshot/blob/materialization](../../src/memforge/main.py), and [local package admission](../../src/memforge/local_adapter.py). Cloud consumes these OSS implementations; no HANA-specific fix is indicated.

### Bounded live evidence

Source: `sfsf-appfnd-cookbook`; affected file `data_masking_orchestration_Service/example/agent_pii_masking/README.md`; object `b6af93d5ecfee34ea4ccec06ee5765410298515f`.

GET-only comparison using the authenticated `gh api --hostname <enterprise-host>` session:

```text
GET repos/<owner>/<repo>/git/blobs/b6af93d5ecfee34ea4ccec06ee5765410298515f
GET repos/<owner>/<repo>/contents/data_masking_orchestration_Service/example/agent_pii_masking/README.md?ref=main

blob_bytes=4992
blob_declared_size=4992
computed_blob_sha_matches=true
contents_bytes=5017
contents_declared_size=4992
contents_same_sha=true
contents_computed_blob_sha_matches=false
contents_bytes == blob_bytes.decode("cp1252").encode("utf8") : true
```

Calling the real `decode_github_contents_payload()` with that response raises `ValueError: GitHub contents API content size mismatch`.

The equality above proves a byte transformation, **not** that Windows-1252 is the intended encoding of the entire document. The raw blob contains valid UTF-8 sequences and an invalid UTF-8 byte `0xD6` at offset 4,250. Its intended text is ambiguous; decoding the entire file as Windows-1252 can corrupt the already-valid UTF-8 text.

An isolated call through the real daemon `_github_blob()` with its provider read replaced by the captured Blob response returned the exact bytes. The next current daemon step, `raw.decode("utf8")`, raised `UnicodeDecodeError` at offset 4,250. Thus changing the endpoint alone does not make this file ready for trustworthy extraction.

### Primary-source constraints

- Git Blobs addresses a file object by SHA and supports Base64 JSON or raw bytes, with a 100 MB provider limit. It is the appropriate immutable byte interface here; it does not require broader permissions than repository Contents read. [GitHub Git Blobs documentation](https://docs.github.com/en/rest/git/blobs)
- Contents can resolve branch/tag/commit refs, dereferences some symlinks, and has representation restrictions above 1 MB. Keeping mutable branch URLs or treating the Contents response as universally byte-identical is unnecessary when the tree already supplies a blob identity. [GitHub Contents documentation](https://docs.github.com/en/rest/repos/contents)
- A Git tree enumerates object identities and has a truncation signal. Do not relax complete-inventory validation when changing the body reader. [GitHub Git Trees documentation](https://docs.github.com/en/rest/git/trees)
- Git hashes the object header and original bytes; validating only the returned SHA field is weaker than recomputing the object identity. [Git object format](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
- Without external information, encoding detection cannot prove which text encoding was intended. `errors="replace"` changes source text instead of resolving that ambiguity. [Python codecs documentation](https://docs.python.org/3/library/codecs.html)
- `working-tree-encoding` is not a declaration that stored blobs use that encoding: supported Git clients normally convert those files to UTF-8 in the repository. Do not implement an ad hoc attributes parser as this fix. [Git attributes documentation](https://git-scm.com/docs/gitattributes#_working_tree_encoding)

### Recommended minimal design

Use one shared GitHub byte contract: **pin inventory, fetch each selected blob by identity, validate original bytes, then normalize text**.

1. Bring Cloud discovery into the already-accepted immutable commit/root-tree model used by the daemon. Keep the configured ref/path in stable document identity; substituting a commit SHA there would create new document identities on every commit.
2. Replace the Cloud text Contents read with the Blob endpoint. Reuse `github_repo_utils.py` for response validation in both transports: required identity, valid Base64 and length, expected inventory size when present, and recomputed Git blob SHA. HTTP/`gh` transport differences remain private to the two existing adapters.
3. Keep binary Artifact streaming and its existing storage/admission limits. Do not introduce a universal buffered download module, change extraction batch sizes, or claim that the GitHub 100 MB limit is MemForge's accepted document size.
4. Normalize verified text consistently: strict UTF-8 for the current supported text contract, with an explicit actionable decoding failure instead of Cloud's silent replacement. No automatic Windows-1252 fallback, confidence heuristic, per-source special case, or silent byte repair.
5. Treat the ambiguous sample as an unresolved source-content prerequisite. Ask the source author to confirm and normalize the file to UTF-8 in a normal new upstream revision. Alternatively, an explicit non-UTF-8 support contract can be considered if a real corpus requires it; that is not justified by pretending this mixed sample is clean Windows-1252. Neither action is performed by this investigation.

This is one correction to the existing collection interface, not another lifecycle state or retry subsystem. The simplest acceptable seam is the existing shared GitHub utilities, with both adapters using the same validation and text policy. A new inheritance hierarchy or general-purpose character-set framework would add no demonstrated leverage.

Alternative rejected: Contents with `ref=<commit>` fixes only the moving-ref race, not the observed transformed-body mismatch. Contents-to-Blob fallback leaves two competing byte contracts. Relaxing size/hash checks can admit transformed text under the original evidence identity.

### Reproduction and acceptance gates

Existing deterministic race/protocol reproduction executed successfully:

```sh
.venv/bin/python -m pytest -q tests/test_github_repo_gene.py \
  -k 'changed_after_discovery or non_base64 or malformed_base64'
```

Result: **3 passed, 15 deselected**. These are current safety tests, not proof that the proposed fix exists. In particular, `test_cloud_pull_rejects_contents_blob_that_changed_after_discovery` proves the mutable-ref race is reachable through real `discover()` and `fetch()` interfaces using a fake provider.

An additional in-memory fixture passed the bytes `"UTF8 punctuation — ".encode("utf8") + b"\xd6\n"` through real `GitHubRepoGene.normalize()`. Current Cloud returned `UTF8 punctuation — �`; the daemon's current strict decode raised `UnicodeDecodeError`. This is an executable adapter-parity failure, not a proposed detector.

Required implementation tests:

- Branch moves after discovery: Cloud and daemon still return the originally pinned blob; no request to mutable Contents and no change to document identity.
- Same object with transformed Contents representation: exact Blob bytes succeed byte validation; malformed or inconsistent Blob identity/size/hash still fails closed.
- Valid UTF-8 succeeds identically in both paths; mixed/invalid UTF-8 fails identically without replacement. Corrected UTF-8 sample succeeds as a new revision.
- Empty files remain authoritative empty; incomplete/truncated trees remain non-authoritative; HTTP/auth failures do not manufacture an empty result.
- Supported binary Artifact streaming, limits, and source lineage remain unchanged. Selected symlinks must not silently change from dereferenced content to a text claim containing the link target; retain an explicit supported-mode policy.
- Shared helper tests use genuine Git object hashes, not `readme-sha` placeholders. Cloud Gene and daemon materialization tests cross their real caller interfaces.

Next bounded live verification after implementation/deployment: GET-only read and normalize the exact two file objects, compare bytes/hash/revision, and confirm no mutable branch reads. Only after the ambiguous file has an authoritative text disposition should an authorized normal incremental Source sync prove end-to-end convergence. Do not claim all partial-sync files fixed merely because Blob fetch passes.

## Relation-first failure: preserve safety and make failures diagnosable

### Historical event versus reproducible implementation defects

The exact event `are-f74d22c593b8c6e20bad9549` belongs to `payroll_agent`, Source `src-6cb562f1`, Unit `unit-f77c24bb04cd5a53e0bab8bc`, run `ssr-3b068dd8f59640ad81fc367c24f96566`.

The relation-first stage must establish the relevant new/old claim relationships and incumbent Support decisions before constructing a complete Lifecycle Plan. An incomplete mandatory decision set cannot safely authorize update, supersede, or retire. A failure here is not a Plan rejected during database commit: no complete Plan is available to commit.

Historical evidence (Asia/Shanghai): the first execution failed at 2026-09-02 23:51:10; the same target revision subsequently applied at 2026-09-03 01:15:09, and a newer revision applied at 03:12:14. The run ended partial at 03:47:13 with the two GitHub fetch errors above. The historical failed execution remains valid history.

The original exception cannot currently be established. The retained trace contains the terminal projection, its parent is unavailable, and a bounded read of `MEMORY_AUDIT_EVENTS` for this Source/Document and 2026-09-02 15:28–15:52 UTC found no `source_unit_llm_summary`. The missing summary does not prove that this historical invocation used the recovery path. Neither a timeout nor a schema failure should be asserted as the original cause.

Three current implementation gaps are independently reproducible:

1. Reconciler call counts are accumulated after an entire classification/audit stage returns. If a later call fails, previously issued calls in that stage can be reported as zero. Planned batch counts on classifier exceptions are not a valid substitute for actual issued calls. See [reconciler](../../src/memforge/pipeline/reconciler.py) and [classifier](../../src/memforge/memory/relation_classifier.py).
2. `StructuredLlmError` already carries safe category/code fields, but reconciliation reduces the failure to text and the Lifecycle event omits those fields. The event only retains `relation_first_failed`. Use the existing structured error/event contracts, not a raw exception archive. See [structured client](../../src/memforge/llm/structured.py) and [MemoryEngine](../../src/memforge/memory/engine.py).
3. Normal `_process_item` owns a structured-call collector and a finally summary. `_resume_source_derivations` does not. This violates the existing requirement that each bound Unit lifecycle execution, including a failing execution, emits a summary. See [sync orchestration](../../src/memforge/pipeline/sync.py) and [ADR 0012](../adr/0012-deepen-the-extraction-lifecycle-hot-path.md).

### Local reproduction

An isolated harness uses fake model responses and temporary SQLite; it does not replay live Source ingestion or call a provider. Both the independent agent and parent ran:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests .venv/bin/python -m pytest \
  -p no:cacheprovider -q -s \
  /tmp/memforge-relation-rca.QU7ENm/test_relation_rca.py
```

Parent result: **3 intentionally failing assertions, 4 passing characterizations, 4.57 seconds**. The temporary harness is diagnostic material, not a committed regression suite.

```text
classification: actual_calls=2, reported_calls=0
support_audit: actual_calls=2, reported_calls=0
MemoryEngine: reason=relation_first_failed, error_code=null,
              old_revision_preserved=true, old_support_preserved=true, plan_count=0
recovery: provider_error/TimeoutError emitted by structured client,
          durable_summaries=0 (expected 1)
```

The Engine safety characterization crosses the real projected lifecycle interface. The recovery characterization stages a v9 derivation and runs the real recovery orchestration and structured client with a fake provider timeout; its reconciliation dependency is an isolated stub. These tests reproduce the mechanism and diagnostic defects, not the unavailable historical model response.

### Minimal correction and remaining uncertainty

- Reuse one existing execution/metrics scope for normal and recovery paths, with exactly one summary finalized after a real Unit is bound. Recovery already has that Unit identity; normal processing binds it after projection. No new audit table or execution ledger.
- Preserve safe failure operation, terminal category and code through reconciliation into existing event/audit fields. Do not retain provider request bodies, raw exception text, or tracebacks.
- Use actual structured-call telemetry for issued-call/attempt counts, including failed calls. Keep planned, completed, and attempted work distinct rather than redefining successful coverage as attempted coverage.
- Preserve complete mandatory coverage, atomic Plan application, and fail-closed behavior. Optional revision-composition proof already has conservative semantics; do not turn every optional proof failure into a fatal outcome.
- Keep the existing bounded provider/schema retry ownership. The logical deadline bounds one structured call, not hundreds of calls across a Unit. The observed successful 17,648-pair/296-call and 24,747-pair/408-call executions demonstrate large work, but do not establish why the earlier execution failed. Do not add another retry layer or reduce mandatory coverage based on these counts alone.

Acceptance: turn the three diagnostic red assertions green; exercise normal/recovery with the same provider failure, schema failure, logical deadline, and success; prove exactly-once summary, stable safe cause, accurate attempted-call counts, and unchanged zero-Plan/old-Support safety on mandatory failure. Existing structured retry tests must remain green.

This correction prevents future failures from losing their diagnostic cause. It does **not** guarantee that an external model never fails, or establish a fix for the historical unknown exception. A targeted runtime fix should follow the first reliably classified failure, not an assumed provider diagnosis.

## Retry UX: waiting is not active execution

### Reproduced defects

The CNP local collection job had completed two retryable connection failures and was queued until 2026-09-03 12:02:44 Asia/Shanghai. A later successful GitHub connectivity probe and an online daemon do not alter that durable not-before time. The existing broker policy is one hour after the first retryable failure and twelve hours after later failures, up to five attempts; this is explicit in [ADR 0001](../adr/0001-project-source-sync-activity-from-existing-execution-records.md).

The policy is not a queue deadlock. Three implementation/interaction gaps make it look like one:

1. The status response contains `next_attempt_at`, but `LocalAgentJobStatusResponse` and `SourceSyncActivity` drop it. `queued` then maps to `Syncing now`, a spinner/progress bar and disabled Sync. See [types](../../admin-ui/src/api/types.ts), [activity projection](../../admin-ui/src/views/sources/sourceSyncActivity.ts), [row](../../admin-ui/src/views/sources/SourceRow.tsx), and [status card](../../admin-ui/src/components/admin/SourceSyncStatusCard.tsx).
2. `enqueue_sync_local_agent_job` coalesces an existing queued job without advancing its future `next_attempt_at`. Manual and scheduled admission do not communicate different retry intent to that function. OSS local storage has the same omission. Cloud references: `local_agent_jobs.py`, `workspace_proxy_router.py`, `worker.py`; canonical OSS local enqueue: [database](../../src/memforge/storage/database.py).
3. The manual local-sync mutation waits for job completion through 1,800 two-second polls. A valid long wait becomes a browser timeout after about one hour; the error handler creates a synthetic failed job which takes precedence over the durable current-job query. See [SourcesPage](../../admin-ui/src/views/sources/SourcesPage.tsx). Request acceptance and durable completion have different owners and should not share this timeout.

Local deterministic probes ran without changing product files:

```text
Real sourceSyncActivity functions, queued job with future next_attempt_at:
  presentation={message:"Waiting to sync",detail:"Queued"}
  rowLabel="Syncing now"; blocksActions=true
  expected retry-time presentation assertion: FAIL

Real Cloud enqueue_sync_local_agent_job with a controlled store row:
  returned same job ID; coalesced=true; attempt_count=2
  next_attempt_at unchanged in the future
  expected manual-expedite assertion: FAIL

Actual pollLocalAgentSyncJob function, isolated with immediate fake timers:
  reads=1800; simulated_wait=60 minutes; error=LOCAL_AGENT_TIMEOUT
  durable job still queued
  expected accepted-request/nonterminal-wait assertion: FAIL
```

The polling probe extracted the function without modification, stripped TypeScript annotations with Node's built-in transpiler and supplied a constant queued GET response. It verifies polling control flow, not a rendered browser session or backend timer.

### Recommended behavior

Keep the existing job states and retry schedule. Derive waiting presentation from queued/pending plus a future not-before timestamp; do not add a database `vpn_wait` state or a VPN-monitoring subsystem.

| Durable situation | Presentation | User action |
| --- | --- | --- |
| Failed attempt, future retry time | Static clock, `Waiting to retry`, next retry time and safe prior failure reason; no progress bar | `Retry now` |
| Eligible queued job, not yet claimed | `Waiting for device` or ordinary queue label; not `Syncing now` | Existing job remains coalesced |
| Leased/running | Real phase and progress | No duplicate or restart of active execution |
| Terminal failure | Action-needed details | Existing authorized retry flow |

Manual `Retry now` should request immediate eligibility for the **same queued job**, using a small explicit manual/scheduled admission intent at the shared enqueue interface. The storage update must be conditional on that job still being queued; scheduled requests must preserve backoff. Keep job identity, attempt budget, configuration/epoch fencing, execution owner, and lease guards. A double click or a concurrent daemon claim cannot create a duplicate or steal a lease. Do not reset counters, pretend the failed attempt succeeded, or bypass paused/deleted/maintenance/access restrictions. An exhausted terminal job follows the existing new manual request policy.

The accepted request should return its durable job ID immediately, release request-pending UI state and invalidate the existing current-job query. Reuse that query as the ongoing authority for progress; remove the local one-hour wait and synthetic terminal failure from the sync-request path. A failure to refresh status is a status-fetch problem, not proof that the durable job failed.

Only expose the additional retry action during backoff; do not broadly unlock configuration/delete operations merely to enable that button. Keep the last successful sync timestamp until real success. Label the pending attempt as `Next retry`, separately from the recurring `Auto sync` schedule, so two different clocks are not presented as one promise. Preserve accessible status announcements without repeatedly announcing a seconds countdown.

The same presentation principle should cover server `SourceSyncRun` pending retries, which already expose `next_attempt_at`; local jobs and server runs keep their own lease/store implementations. Prove the manual admission semantics through each affected existing adapter, rather than introducing a generic replacement job engine.

Acceptance: future-retry/eligible-queue/active/terminal UI cases; accepted request is not pending for the job lifetime; refresh never synthesizes a durable failure; manual retry advances only an authorized queued job; scheduled enqueue does not; concurrent/repeated requests preserve one executable job and the attempt budget. Cover OSS SQLite, Cloud control-plane SQLite and HANA SQL/parameters plus route-level authorization and lease races.

Primary references: [W3C status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) distinguishes waiting, progress, outcomes and errors and recommends non-disruptive accessible announcements. [AWS retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html) supports bounded attempts and classified backoff as general reliability principles; it does not prescribe MemForge's twelve-hour interval or manual-retry product behavior. The interaction above is a project-specific design recommendation.

## Delivery boundary

Recommended implementation scope is the three corrections above, not a general scheduler, character-set framework, or relation-performance redesign. A code change must not be called production-verified until the affected OSS/Cloud contracts, PRs, deployment and bounded smoke are complete. The mixed-encoding upstream file requires a separate authoritative content disposition; the old relation exception remains unknown. No issue, PR, deployment, Source mutation or Memory mutation was created by this research.
