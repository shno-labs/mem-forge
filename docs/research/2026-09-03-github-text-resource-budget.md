# GitHub text resource budget refinement

Status: design proposal, not implemented or approved for rollout. No source sync,
Memory mutation, production query or upstream content edit was performed.
Code inspected: OSS `5aba41a8`; Cloud `776937c`.

## Findings that change the proposal

- Cloud text currently uses buffered Requests GET, JSON parsing and Base64
  decoding (`genes/github_repo_gene.py:357`). Its existing private Requests
  adapter already exposes a streaming context manager; binary GitHub Artifacts
  already use the immutable Blob raw media type (`:387`, `:543`). HTTPX is not
  the transport used here; no HTTP client replacement is needed.
- The daemon's `_github_blob` uses `subprocess.run(capture_output=True,
  text=True)` through `_gh_api_json`. Reading stdout after process completion
  and then checking length is not a pre-buffer size guard (`main.py:450,530`).
- `_push_github_profile_to_source` downloads sequentially but keeps every text
  body in `prepared` until its later upload loop (`main.py:2662,2710,2747`).
  Per-file limits alone therefore do not bound collection-resident bodies.
- The upload interface is already one document per request
  (`tool_client.py:252`). Releasing each body after its existing upload does not
  require a new batching protocol or a smaller batch size.
- Cloud's checked-in manifest configures one process-wide document lifecycle
  admission slot, but OSS defaults can disable this gate. The manifest currently
  specifies a 2G worker; neither that nor an older 1G runtime snapshot is proof
  of the live deployment's current resources.
- Text size is not a sufficient parser-memory bound: structural planning first
  materializes Markdown tokens (`pipeline/evidence_fragments.py:612`). Existing
  per-catalog limits are not a pre-allocation bound on that parser.

## Recommended design

### 1. One immutable raw-byte contract

Use `GET git/blobs/{sha}` with `Accept: application/vnd.github.raw+json` for
text in both collection modes. This supersedes the earlier proposal to buffer
Blob JSON/Base64. Do not fall back to Contents or reinterpret a JSON response as
text. Preserve TLS, configured enterprise host, credentials and error typing.

Reuse the existing HTTP streaming adapter. Give the daemon a private bounded
binary-stdout reader for this raw endpoint, not a generic replacement CLI
framework. Do not route text through `_gh_api_json`; keep metadata JSON and
binary Artifact contracts separate. Stop and reap the child on limit, lease
loss, cancellation or deadline; stderr must also be bounded and drained so it
cannot deadlock the read. Verify child as well as parent resource behavior.

Use one shared byte accumulator/validator interface behind these two existing
transport adapters. Inventory size, when available, permits early rejection;
actual bytes are authoritative. Read at most the remaining allowance plus one
sentinel byte, then stop on excess; a false/missing Content-Length cannot bypass
the limit. Retain the existing 256 KiB stream chunk scale as an implementation
detail, not a Memory fragment size or a new user setting.

For HTTP request identity encoding, reject unexpected content encoding before
automatic decompression on this raw-byte path. At EOF verify actual length
against the inventory if present, recompute Git object SHA using the actual
length and complete bytes, then strict UTF-8 decode. Unknown inventory length
does not justify unbounded buffering. EOF/exit success, hash and decoding must
all pass before materialization is accepted. Empty valid objects remain valid.

### 2. Bound body lifetime, not the number of business items

Daemon text processing becomes read -> validate -> upload through the existing
per-document interface -> release body -> next file. Retain the complete
manifest and small result/receipt metadata, not all document bodies. This is a
body-lifetime change, not batching or a new lifecycle state. Preserve full
membership, exact revision and lease fencing; call existing processing/finalize
only after every required item is uploaded or authoritatively reused. An
interrupted or incomplete collection must not authorize absence/removal.

Keep binary Artifact handling unchanged. Preserve truthful monotonic aggregate
progress when interleaving text reading and uploads; do not reset counters or
claim overall upload completion before all required bodies finish.

Cloud text fetch stays inside existing whole-document admission. Reuse that
gate for memory-heavy processing; do not add another download queue, weighted
scheduler, distributed semaphore or temporary-file replay subsystem.

### 3. Make the byte policy explicit without claiming it is an RSS guarantee

Proposed first validation point: **4 MiB of original text bytes per file**,
shared by Cloud/daemon/package admission. This is a candidate product limit,
not a value derived from GitHub's maximum or copied from binary Artifacts, and
not an approved compatibility reduction. It must be checked against real
configured inventories and existing larger supported files before adoption.
If larger files exist, report that cohort and decide its supported handling;
do not silently exclude it, truncate it, increase limits automatically or
pretend the old code had this cap.

Why test 4 MiB: it is a modest multi-megabyte starting point for bounded full
text materialization. The measurements below justify testing it, **not**
declaring it universally safe. Do not expose a per-Source tuning panel or a
collection of budget knobs in this fix. Implementation must keep the effective
policy identical across execution modes and enforce it on the receiving side
so an older daemon cannot bypass it. Deployment/daemon version skew belongs in
acceptance and rollout evidence.

Raw streaming removes JSON/Base64 download amplification. It does not remove
decoded Unicode, Markdown/HTML parser structures, projection state, local
upload serialization or downstream LLM/catalog costs. Ordinary JSON document
uploads still exist; their wire bytes and receiving-process peak must be
measured separately. No whole-process memory safety claim follows from the
download byte cap alone.

### 4. Failure behavior

Report the path, original size if known, effective limit and failed stage.
Oversize, integrity failure and invalid UTF-8 are not empty/deleted documents.
Preserve prior Memory/Support and snapshot completeness guards. A fixed-size
policy rejection is not a transient network failure and should not consume
repeated automatic download attempts for the same immutable revision.
Partial versus failed source status continues to follow existing execution-mode
semantics; do not promise Cloud pull and fenced local collection can finalize
the same incomplete workset.

### 5. Bounded acceptance before choosing a release default

- Use fake HTTP/CLI streams: below/at/above limit, absent/lying lengths,
  truncated bodies, raw endpoint returning JSON, altered hash, encoding errors,
  unexpected compression, nonzero child exit and cancellation cleanup.
- Verify bytes are limited before whole-response buffering; monitor fake child
  cleanup and bound stderr. A decoded-length check after `capture_output` does
  not pass this test.
- Run multiple synthetic documents through daemon collection. Already uploaded
  bodies must not remain in `prepared`; process memory must not scale with the
  sum of all file texts. No new uploads or processing are performed on live
  Sources for this acceptance.
- Exercise actual normalization, structural planning, projection/compiler and
  representative old/new revision state at configured concurrency, using prose,
  dense lists, tables, inline/raw HTML and Unicode. Use a resource-limited test
  process/container so pathological inputs cannot exhaust the development host.
- Record startup/base RSS, absolute peak and remaining headroom for web/worker
  separately; a reasonable validation gate is at least 25% headroom at the
  actual target quota, subject to the tested workload. Test direct Cloud pull
  and daemon upload/replay, not just the reader or one parser function.
- Inventory and size-distribution checks before rollout are read-only. They do
  not authorize fetching all bodies, LLM processing, sync or upstream edits.

If dense structures fail this gate, do not repeatedly guess smaller byte caps
or add ad-hoc Markdown truncation. Determine the specific existing parser seam
where a small resource guard can stop allocation; bring that bounded design
back for review. A parser guard is not established by this transport proposal.
Until this named risk and compatibility are verified, B is not production-ready.

## Bounded local evidence

Synthetic input only; real `_markdown_protected_ranges`, no LLM/database/network.
Each case ran in a fresh process with the existing OSS virtual environment.
macOS `getrusage(RUSAGE_SELF).ru_maxrss` reports bytes. This is a single-pass
characterization, not full-pipeline performance or a portable sizing formula.

| Input | Original bytes | Structural ranges | Parse seconds | Process peak MiB | Peak increase MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Repeated ordinary prose | 4,194,304 | 14,267 | 0.314 | 86.73 | 30.27 |
| Dense `- x` list | 262,144 | 65,536 | 1.362 | 213.67 | 164.50 |

Probe: `/tmp/memforge-text-budget.xCI40Y/probe.py` (diagnostic, not a permanent
test dependency). Commands, from the OSS checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python /tmp/memforge-text-budget.xCI40Y/probe.py prose 4096
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python /tmp/memforge-text-budget.xCI40Y/probe.py dense 256
```

## Primary references

- [GitHub Blob API](https://docs.github.com/en/rest/git/blobs): raw and Base64
  media types; the provider's maximum is not an application memory budget.
- [Requests streaming](https://requests.readthedocs.io/en/latest/user/advanced/#body-content-workflow):
  opt-in streaming and explicit connection closure on partial consumption.
- [GitHub CLI API](https://cli.github.com/manual/gh_api): custom Accept headers;
  the parent still owns its stdout resource policy.
- [Python subprocess communication](https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.subprocess.Process.communicate):
  communication buffers output; bounded reads/cleanup require explicit ownership.
