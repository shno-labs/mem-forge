# GitHub daemon body-lifetime repair

Tracked only in [#385](https://github.com/shno-labs/mem-forge/issues/385), within
the existing B single-document upload/release scope. Canonical ownership is
[ADR 0011](../adr/0011-separate-collection-evidence-from-body-materialization.md).

## Change

The baseline `c2ff2c68` downloaded all required text into `prepared`, then
uploaded it. The collector now invokes one synchronous document-transfer helper
per required manifest entry. That helper owns raw bytes/decoded text until its
existing upload completes and returns only a small receipt plus byte accounting.
No body escapes into the outer results list. This retains memory for one body
and its transport representations, plus O(file-count) manifest/receipt metadata;
it does not promise constant total memory or bounded arbitrary single-file size.

The complete snapshot is still planned before any body reads. Invalid UTF-8,
provider/read failures and unsuccessful uploads preserve failed-path results;
the collector does not start processing after any such failure. A rejected
lease propagates immediately before further reads/uploads. Existing binary
Artifact size checks, hash/package linkage and source/job/snapshot identity
remain unchanged. There is no new cache, spool, worker, state, upload protocol,
batching, text truncation or size cap.

Progress uses the existing fetching/uploading phases for each document. The
workset total is fixed; phase-local completed counts distinguish a finished read
from a finished upload. Byte metrics describe prepared bodies and submitted
document transfers, not network overhead or proof that a failed request was
durably accepted. Artifact preparation/read failures are no longer counted as
successfully prepared bodies merely because metadata was listed.

## Red/green evidence

- A task-handler test with external GitHub/Cloud boundaries simulated first
  failed: actual order was manifest, read A, read B, read C, upload A...
  It now observes manifest, read A, upload A, read B, upload B, read C, upload C,
  then processing.
- The same test covers a middle-file decode error and upload rejection: later
  files can transfer but processing is never started. A middle-file lease
  rejection stops before reading the next body.
- Existing no-op, complete-tree, image Artifact, oversized-Artifact, source
  workspace and lease tests continue to exercise the task-handler path.

The memory regression executes the actual handler/reader/decoder/upload loop
with a body-discarding simulated Cloud receiver. Each body is 512 KiB. Imports
are warmed first; Python traced allocation peaks are measured for 2 and 12
files. The test permits metadata slack but rejects retaining ten extra bodies.

| Actual collection implementation | Peak, 2 files | Peak, 12 files |
| --- | ---: | ---: |
| Baseline `c2ff2c68` | 3,466,496 bytes | 8,721,242 bytes |
| Per-document lifetime | 2,418,530 bytes | 2,427,672 bytes |

The identical memory test fails on the baseline and passes on the repair. A
diagnostic-only pytest plugin loaded the baseline function from the immutable
git object into the isolated test process; it did not revert working files.
`tracemalloc` reports Python allocation peaks, not full OS RSS or live daemon
headroom ([Python documentation](https://docs.python.org/3.12/library/tracemalloc.html)).
No provider/LLM call, live sync, Memory write or history change was performed.

Commands from the OSS checkout with the configured test runtime and
`PYTHONPATH=src:tests`:

```sh
python -m pytest tests/test_cli_agent_tools.py -k github -q
python -m pytest tests/test_cli_agent_tools.py tests/test_local_agent_snapshot_manifest.py tests/test_local_adapter_api.py -q
python -m pytest tests/test_local_agent_daemon.py tests/test_local_agent_daemon_broker.py tests/test_local_agent_source_contract.py -q
```

This closes the multi-file body-retention defect in code. It does not complete
B's remaining raw-Blob streaming/immutable-byte work or fix the upstream
mixed-encoding file. Runtime activation still requires releasing/updating the
local daemon; changing the Cloud dependency pin alone does not update an
already installed local daemon. No merge or deployment is claimed here.
