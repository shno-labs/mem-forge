# Focused Evidence integration and production-path verification

Status: provisional acceptance at the tested extraction, storage, delivery and
revision-lifecycle seams. The checked Cloud deployment and one bounded real
Confluence reprocess passed. Useful-coverage quality remains unscored; authentic
consecutive provider edits and both desktop-client release lanes are not claimed.

## Runtime contract

One extraction response selects Primary/Required IDs and supplies focused text
for each selected ref. The application binds text by ref ID, retaining the full
source excerpt, typed interpretation, anchor and integrity digests separately.
Neither generated wording nor its length affects source identity, part membership
or revision correspondence. Source syntax and field semantics stay in adapters.

SQLite migration110 and the HANA reference-column extension store optional
`display_text`. Derivation and Lifecycle Plan payloads retain it. API detail
returns readable `text` and full `excerpt`; compact MCP returns text, every
Primary/Required part and pinned resource locators. Both UIs expose full source
inspection. No public LLM label, extra semantic repair or rendering call is added.

Supported Assessment results generate new text in the existing response. Exact
program rebind preserves old text only when the entire source presentation digest
is unchanged; changed interpretation clears it. Current source presentation then
remains available. Missing historic display is not fabricated during upgrade.

## Bounded local checks

- OSS affected-source, extraction, transport, Support, lifecycle and delivery
  suite: **1,024 passed**, 79.90s.
- Cloud HANA store, delivery parity and admin proxy suites: **524 passed**,
  23.79s. These are adapter/query and decode tests, not physical HANA roundtrips.
- Focused-display checks cover selector/body membership, Required ordering,
  source authority, payload serialization, existing-call Assessment, exact rebind,
  changed interpretation and actual SQLite close/reopen persistence.
- Additive SQLite upgrade is tested with retained Evidence and missing display
  column; existing refs survive, and API exposes the source text without inventing
  generated display.
- Upgrade, focused-display, packaged-copy, MCP and evidence-schema checks:
  **25 passed**, 6.87s, after the broad regression suite.
- V2 Memory detail UI: **7 passed**, including collapsed full-source inspection.
  V1 and V2 production builds and Python lint passed. Plugin runtime copies sync.

Earlier test failures remain in private logs. Old fixtures lacked the new required
display schema. Corrected fixtures preserve their intended malformed-JSON,
unknown-selector and capacity assertions; no product bypass was added. No batch
policy, provider limit or output budget was changed.

## Full-CI regression closure

The first complete Python CI run failed: 73 failed, 3,784 passed. The earlier
1,024 affected-path tests were not a substitute for that full run. Native
Jira/Confluence test providers still emitted snapshots without their declared
native/provider-rendered representation; MCP and relation expectations predated
retained identity and typed field interpretation. Those fixtures/assertions were
aligned without changing production adapters or weakening lifecycle assertions.

Two public managed-session Memory-detail tests exposed a production defect:
valid Markdown HTML claim-marker comments were recorded as compilation errors,
so pinned-view verification rejected otherwise complete source representations.
The generic Markdown compiler now excludes valid comment-only framing without
creating Evidence or an error. Malformed/nested comments and unsafe HTML remain
unacceptable. Compiler contract version 9 invalidates the prior compilation
contract; no stored source, coordinate, digest or matching rule is rewritten.
The independent incremental reviewer approved the narrow correction, including
negative syntax cases. All ten affected test files passed: **669 passed**,
31.10s. Complete CI for commit `22ebc69b` passed: **3,861 Python tests**, V1/V2 UI
tests and builds, V2 browser end-to-end tests, distribution verification,
OpenAPI/package-copy checks and lint. Useful-coverage follow-up is tracked in
[Issue500](https://github.com/shno-labs/mem-forge/issues/500); it is a quality
metric for this provisional release, not a claimed95% pass.

The changed MCP response requires a distinct plugin cache identity. Package,
MCP, hook and both plugin manifests are advanced together to0.1.64 for a remote
RC-tag installation test; no final package/tag publication is implied.

## Online production path

The actual Cloud structured-client factory from the fresh Cloud worktree and the
OSS production extractor, planner, runner, selector resolver and assembly were
used without process-local prompt/schema substitution. CF binding credentials
were used only in memory. Model: `sap/anthropic--claude-4.6-sonnet`; extraction
contract `projection-extraction-v20`, Support contract `support-ordered-reading-v9`.

Three complete frozen real inputs were planned as three requests, with no skipped
Reading Groups. All three and one full-current-source Support Assessment returned
valid output in native-schema mode, one attempt each, no retry/fallback/truncation.
This is online local replay, not a deployed service canary or genuine consecutive
provider revision test.

| Source | Claims | Primary / Required | Source excerpt median / max | Focused text median / max |
| --- | ---: | ---: | ---: | ---: |
| Native Confluence | 56 | 56 / 1 | 662 / 1,263 chars | 295 / 892 chars |
| Native Jira | 7 | 7 / 4 | 206 / 451 chars | 134 / 406 chars |
| Complete Markdown ADR0040 | 23 | 23 / 2 | 448 / 1,592 chars | 414 / 1,642 chars |

The 86 claims retain 93 source-bound display parts. Text can be longer than its
excerpt when faithfully restoring relationships; there is no fixed shortening
target. Confluence total citation text fell from36,338 to17,970 characters.
The complex-source Assessment completed in17.4s with its unchanged1,708-token
allowance. This closes the named output-budget concern for that sample, not every
possible document/workload. Reported input/output token totals for the four calls
were58,988/24,535. Recorded client telemetry is not SDK-internal HTTP attestation.

## Independent review and scope

The incremental code reviewer approved binding, all storage/copy paths, typed UI
delivery and source/display separation. Its missing-type concern was caused by
an incomplete review packet; inspection of the actual generated type and passing
TypeScript check closed it. Negative changed-interpretation and existing-call
Assessment tests closed the two recommended evidence gaps. Decisions are recorded
in the private implementation handoff log.

A fresh blind reviewer inspected all86 claims and93 displays against the complete
native sources. It found **zero major whole-source unsupported conclusions,
wrong-modality claims or material display fidelity defects**. Two claims miss
selected supplementary context that is present elsewhere in the source; one
retains an unresolved cross-row reference. These are reported under the user's
best-effort Required and provisional role acceptance, not repaired or filtered.

The reviewer found **nine useful omission groups**, including historical stale
stored-input behavior and a bounded incident-recovery requirement in the ADR.
It had no independently frozen denominator for this new run and reports no95%
coverage score. Earlier two-reviewer scores and failures remain unchanged;
this result does not supersede or rescore them. Accurate claims, useful coverage,
faithful displays and deterministic provenance are separate measurements.

Claude Code CLI is unavailable on this host. No Claude Code reviewer or remote
Claude plugin installation/restart lane is claimed by this report.

## Checked deployment and bounded product acceptance

Cloud commit `31b85d4c7c9ccde637b21cb8abffd679fb3ba58b` pins OSS runtime commit
`0f2bdbde61c875775c75f155dc6aef630c9d7dba`. Complete OSS CI passed at that commit,
including Python, both UI packages, browser end-to-end checks and distribution
contracts. Deployment used the prescribed checked prepare-deploy entrypoint,
composed both matching UIs and restored the temporary worker scale change.
Runtime package metadata independently confirmed0.1.64 from the pinned GitHub
archive. The development service has one1GB web and one2GB worker process;
both were running after the acceptance run and `/healthz` returned200/ok.

One previously declared Confluence document was reprocessed, with no provider
content edit, workspace-wide replay or historical repair. Report-only preview
found one available unit,46existing Memories/Supports and83estimated model calls.
That old-representation estimate is not executed-call telemetry. The actual run
completed successfully in272seconds, one lease attempt, no recovery. Its new
derivation uses `projection-extraction-v20`; extraction and lifecycle telemetry
report expected outcomes. Lifecycle Assessment recorded four model calls.

A repeatable-read physical HANA snapshot correlated this exact run, unit,
creation watermark, projection lineage, plan, mutations, Support, Reviews and
vector outbox. The single applied plan checked all46incumbents and contains
32Memory creates,76Support attaches,46old-Support removals and two supersessions.
Current population is76active Memories/Supports with215ref parts. Every active
part points at its current observation revision and has nonempty focused text.
All34new vector-outbox entries are completed, with no new Review or open scope
transition. Four pending and six stale historical Reviews remain unchanged;
inactive Support and terminal Memories are classified separately. No new
Finding is inferred from historical populations. Exact parameterized SQL, pinned
run IDs, timestamps and redacted CF evidence are retained in the private handoff.

The originally reported Memory retained its ID and claim. Its Primary text fell
from7,268characters to242; its complete cleaned source block remains464characters.
Three Required parts retain relevant context and the second scenario, including
its failure status. HANA NCLOB text, API text/full excerpt and both source
digests match for all four parts. Actual remote-installed MCP processes return
the same four parts, typed views, Support/anchor IDs and pinned resource URLs;
the complete authentic pinned source resource remains readable. Authenticated
deployed UI smoke confirmed focused paragraphs and expandable original Evidence.
This is a provenance/display/lifecycle acceptance, not a new semantic coverage
score or a claim that every role choice is ideal.

The first joint audit read timed out through CF SSH. A read-only transport probe
and the same joint query with stage diagnostics completed in108seconds. No
second product run, data patch, query splitting or relaxed assertion was used.
The captured snapshot converged; no additional canary was started.

## Remote plugin acceptance boundary

Remote tag `memforge-memory-v0.1.64-rc.1` names committed plugin/runtime revision
`73b29b52b5e5fd059e5770caa8281a5be513566e`. A disposable Codex profile installed
`memory@memforge` from the GitHub marketplace at that tag. Marketplace commit,
cache0.1.64 and packaged-file parity were verified. New CLI processes repeated
plugin-version and MCP-cwd checks. Two fresh installed stdio processes before
and after reprocess passed `initialize`,16-tool inventory, real `get_memory`
and pinned `get_resource` reads. Installed SessionStart, Stop and PreCompact
commands also passed against an isolated local receipt receiver, with no product
writes or transcript capture.

No user cache was edited or manual MCP registration added. This proves isolated
CLI/process restart behavior, not an actual restart of the user's Codex Desktop.
The current conversation still uses its earlier plugin process. The RC is not
a final package publication; Claude Code and user Desktop release gates remain
explicit boundaries rather than being silently marked complete.

## Completion-contract audit

| ID | Current evidence and remaining boundary |
| --- | --- |
| A1 Native input | Native Confluence/Jira and complete ADR replay; remaining source families have fixtures, not new real-provider acceptance. |
| A2 Adapter locality | Source adapters own native grammar/framing; generic dispatch and shared compiler consume declarations. Static and source-matrix tests pass. |
| A3 Source integrity | Actual adapters verify pinned ranges, raw/presentation digests and interpretation origins. Display is separate and independently reviewed. |
| A4 Work authority | Full authorized primary coverage planned once, no skipped groups, unchanged runner. |
| A5 Claim faithfulness | No major defect observed in this86-claim blind review; previous failures remain evidence. No universal truth guarantee. |
| A6 Useful coverage | Nine omission groups;95% is not established for this run. |
| A7 Primary relevance | Nonideal roles provisionally accepted under joint delivery and revision behavior; eligibility remains enforced. |
| A8 Required quality | All parts retained; omissions remain best effort. No new95% relevance score asserted. |
| A9 Correspondence | Unchanged/moved, modified, duplicate and interpretation tests pass; controlled revisions, not real consecutive provider edits. |
| A10 Outside-ref changes | Governing changes route to full Support work; old display cleared on changed interpretation. |
| A11 Lifecycle/stores | SQLite persistence/lifecycle, HANA parity and one physical bounded HANA lifecycle/NCLOB roundtrip pass. All215current parts and34completed new vector entries checked; historical Reviews preserved. |
| A12 Citation delivery | DTO/MCP privacy and both UI tests pass; deployed authenticated API/UI and remote installed MCP/pinned-resource smoke pass for the declared document. |
| A13 Large execution | Complex full-source extraction and full-current-source Assessment completed online; typed capacity semantics retained. |
| A14 Upgrade | SQLite additive upgrade, physical HANA additive column and one exact-count live native-representation upgrade pass; no broad historical recovery performed. |
| A15 Product acceptance | Checked pinned CF deployment and declared document smoke pass provisionally. Coverage is a quality metric under Issue500; genuine consecutive provider edits and user Desktop/Claude release lanes are not certified. |

Private root: `Downloads/MemForge-Evidence-Validation-2026-10-02/private/focused-display-integration-20261006`.
It contains sources, prompts, schema, immutable packet hashes, raw parsed outputs,
telemetry, exhaustive independent judgments, measurements and all test logs.
Private source wording is retained there rather than published in this report.
The old frozen experiment and original user checkouts remain untouched.
