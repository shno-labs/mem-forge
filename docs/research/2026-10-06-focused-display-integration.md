# Focused Evidence integration and production-path verification

Status: implementation verified at the tested seams; not a complete extraction
quality or product-release acceptance. No deployment or live reprocess occurred.

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

Claude Code CLI is unavailable on this host. No Claude Code reviewer lane or
remote plugin installation/restart validation is claimed by this report.

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
| A11 Lifecycle/stores | SQLite actual persistence/lifecycle and HANA query/decode parity pass; physical HANA acceptance pending. |
| A12 Citation delivery | DTO/MCP pinned-resource and privacy tests plus both UI builds; deployed API/UI smoke pending. |
| A13 Large execution | Complex full-source extraction and full-current-source Assessment completed online; typed capacity semantics retained. |
| A14 Upgrade | SQLite additive upgrade and historical contracts tested; live exact-count cutover/reprocess not performed. |
| A15 Product acceptance | Checked CF deployment and named live smoke not performed. |

Private root: `Downloads/MemForge-Evidence-Validation-2026-10-02/private/focused-display-integration-20261006`.
It contains sources, prompts, schema, immutable packet hashes, raw parsed outputs,
telemetry, exhaustive independent judgments, measurements and all test logs.
Private source wording is retained there rather than published in this report.
The old frozen experiment and original user checkouts remain untouched.
