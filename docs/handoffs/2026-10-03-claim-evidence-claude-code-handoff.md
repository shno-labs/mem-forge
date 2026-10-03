# Claim/Evidence extraction — Claude Code handoff

Status: **NOT ACCEPTED; DO NOT MERGE OR DEPLOY.** The user requested finishing
this iteration and handing it to another Claude Code if it still failed. It
still fails semantic acceptance. No further prompt iteration or model call was
started after that request. This file is the starting point, not an execution backlog.

## Start here

- Canonical OSS checkout: `/Users/i551096/Dev/mem-inception`, branch
  `codex/complete-claim-evidence-extraction`; current saved commit is the branch
  head containing this handoff. Prior committed head was
  `04ad16c81c271dbe02e505e9cfc0816d0531158a`.
- Cloud worktree: `/Users/i551096/.codex/worktrees/claim-evidence-cloud/memforge-cloud`,
  branch `codex/complete-claim-evidence-cloud`. Use this worktree, not the primary
  Cloud checkout. Its requirements pin is updated to the saved OSS commit.
- Draft OSS PR: https://github.com/shno-labs/mem-forge/pull/495
- Draft Cloud PR: https://github.com/dodoman-sun/memforge-cloud/pull/545
- Primary `/Users/i551096/Dev/memforge-cloud` has unrelated local work. Do not
  reset, stash or overwrite it. Goal-start updated-main isolation already happened;
  these are current goal branches, not permission to discard later upstream work.
- Read `AGENTS.md` in both repos. Shared design belongs to OSS ADRs; HANA implements
  the same protocol. Any new goal-scoped refactor follows the updated-main workflow.
- Call Claude Code with `claude` (`/Users/i551096/.local/bin/claude`), not `claude-code`.

## Completion contract and human constraints

The full objective is a designed and validated claim/Evidence extraction scheme
using complete real sources, actual online Sonnet, independent blind source audits,
readable citations, stable future revision correspondence and safe whole-Support
assessment. Repository requirements also require PRs, Cloud checked deployment
and detailed smoke tests before completion. **None of the test counts below proves
that objective complete.** Do not narrow it to Confluence syntax or ref counts.

The user rejects admission pruning, switching Primary roles after generation,
extra mandatory same-model self-audit, fallback extraction stages and overengineering.
Improve extraction at its origin with generic instructions. No doc-type prompt
heuristics. Provider grammar/field semantics belong to their adapters. Required
recall is best effort: optional misses are acceptable; wrong or redundant refs
are separate errors. Keep accurate claim conditions/modality and useful knowledge.
No 100% Required recall/minimal-set proof/ref-count cap. Old→new format mismatches
at initial rollout are accepted; future uniquely identifiable unchanged material
under the same declared contract must match. Never force ambiguous duplicate matches.
Images/multimodal capability are deferred under issue497, not part of this rollout:
https://github.com/shno-labs/mem-forge/issues/497 . Frozen image PR496 is separate;
do not import its private extraction prototypes into this canonical branch.

Canonical design: `docs/adr/0046-separate-evidence-correspondence-from-citation-presentation.md`
(Proposed, not accepted). See its complete acceptance table. Current experiment
record: `docs/research/2026-10-02-complete-claim-evidence-validation.md`. Official
native-format evidence: `docs/research/2026-10-03-native-source-format-contracts.md`.
Earlier experiments in the research log remain negative history; they are not
current producer implementations or passed validation.

## Current execution path

1. Gene retains real provider input; source adapter creates immutable versioned
   observations and declares native grammar/fields.
2. `source_representation.py` resolves adapter-owned schemas. `RepresentationCompiler`
   and `pipeline/evidence_fragments.py` compile exact native selections, readable
   presentation, interpretation associations and complete ReadingGroups.
3. `pipeline/projection_context.py` separates complete read scope from eligible
   Primary authority. `pipeline/extraction_requests.py` uses existing provider
   capacity packing without skipping groups or adding business states.
4. `pipeline/memory_extractor.py` uses the shared v17 extraction contract and
   flat existing structured response. One semantic extraction owner emits final
   words and refs. Resolver/assembler checks actual selectors and complete work;
   it does not repair wording or prune valid candidates for clutter.
5. `pipeline/support_reading.py`, `revision_assessment.py` and `revision_work.py`
   reconstruct complete pinned old/new material and apply whole-claim assessment.
   Exact selected-ref matches alone do not authorize reuse when outside scope or
   conditions changed. Existing stale/access/absence/destructive coverage remains.
6. Stored Evidence and resource paths retain immutable raw/presentation integrity,
   profiles, part roles and historical authority. See committed04ad16c work/tests
   for complete tool resources and OSS/HANA/UI parity. Historical latest input
   must never substitute for an Evidence revision.

## Current round: actual online Sonnet still fails

Private root (sensitive source content; do not commit it):
`/Users/i551096/Downloads/MemForge-Evidence-Validation-2026-10-02/private/canonical-native-20261003`.

Actual Confluence input:71,051 bytes/70,981 chars, SHA
`38eda4ad6e0563c6a759881d1f35817d2ab3a4112a22363600d270d5a2a0789b`.
12 tables/60 physical rows/45 scenarios;24PASS,17Failed,4without outcome.
79 Fragments/ReadingGroups, all79 Primary-eligible selections planned once,
one canonical request, no skipped group. Original source is
`/Users/i551096/.memforge-agent/artifacts/confluence-6378070218-raw_source-38eda4ad6e0563c6.html`.
Do not replace this with the older70,032-character normalized Markdown cohort.

Latest completed generation is `scope-contract-v17`: one real online call,
89,732ms,56 untouched candidates/60 parts. Candidate SHA
`9a62af91c16d401ade082f4b5366236a7ddd18186fa1b602f55fe42083e54c1f`.
Blind packet `blind-packet-6f81` contains full source, immutable source material,
unchanged source-first inventories and both complete reviews. Freeze
`completed-v17-experiment-freeze.json` records32 artifacts. Prompts, DTOs,
telemetry and call metadata remain in the producer folder; no response was manually
edited or filtered. This is local canonical execution against the actual CF-bound
SAP AI Core endpoint, **not fixture Sonnet and not deployed pipeline acceptance**.

Both reviewers account for every45scenario and full family inventory (A16/B13).
All60 raw/presentation digest/native-range checks pass. Previously absent safe-skip
and never-assigned-unassign guards now appear, and unsupported date associations
are gone. However:

- `confluence-0048` still says the empty-PayrollRun task issue is **fixed by
  SFPAY-183257**. Native comment says `Fix by:` followed by the issue while row
  status says PASS; no issue resolution was fetched/proven. A calls this low
  genuine source-history ambiguity; B calls it a medium completed-resolution
  overstatement. Root leaves it unaccepted; do not select the more favorable
  review or infer external Jira resolution.
- `0002`, `0003`, `0004` each select a redundant Required table header even though
  Primary already contains the applicable column labels. The one requirements-list
  Required is useful. These are false-positive/redundancy findings, not optional
  recall failures.
- A reports a low further-refinement qualification gap in Compensation/Gross
  claim content; B accepts consolidation with the source/governing context.
  Keep both complete judgments and original denominator.

V15 had17 candidates/26parts, lost meaningful branches and had6 bad Required;
v16 had54/55, six date precision issues and two omitted guards. Their artifacts
and negative reviews are frozen separately. Do not rerun over those output files.
V17 strengthens generic annotations/modality/uncertain-guard instructions, but a
strong prompt instruction does not guarantee a correct model inference. There
is no external login/provider blocker explaining this residual semantic failure.
Both current reviewers retained their own prior conversational assessment;
implementation/treatment blind is documented, not fresh-reader independence.

## Deterministic correspondence and adapter state

Confluence adapter validates/suppresses bodyless TOC navigation; keeps headings,
code/container bodies, compact Status(title/colour), Jira(key/supplied server).
Opaque origin/column controls remain raw/canonical, so hidden origin changes cannot
match just because readable output is unchanged. All provider logic is in its adapter.

Complete native controlled prefix insertion+macro-ID changes match73 unique parts;
6 repeated parts remain ambiguous. All actual v17 selected parts verify. Complete
ADR0034 (123,896chars) has244 original parts all matching after prefix insertion.
These are named controlled perturbations, not universal semantic-equivalence
claims or uniqueness guarantees for arbitrary duplicate text. Full Support gates
remain separate from local correspondence.

Jira adapter work is schema v2. Current description/body use explicit provider
HTML paired with native_description/native_body in the same immutable record.
Old/new changelog values are literal, not Markdown/current HTML. Frozen schema v1
remains registered and nullable legacy profiles backfill v1 in SQLite/HANA.
`jira.py` owns builders, core-field time and history classification; the generic
projection calls it. Both stores import the same adapter classification.
`jira_html.py` owns supported HTML, comparison and mapped readable text, never
imports Confluence grammar. It preserves code/links/deletions/list and table scope,
and exposes supported semantic metadata or explicitly rejects unsupported syntax.
An actual false match (`A B C` vs`ABC`) from trimming inline whitespace was found,
fixed and tested through Support correspondence. No CSS engine/fallback was added.

Authentic complete Jira input:50,807bytes, SHA
`828b504feef809f8d9d9c19e551b70989fdb6f751fe7efe7a0f9c433db52dae3`, path
`/Users/i551096/.memforge-agent/artifacts/jira-SFPAY-184406-raw_source-828b504feef809f8.json`.
Native/current HTML1549/3401chars; prior/new history description1393/1549;
10 complete histories,0comments. Exact code body300chars SHA
`75484e5a651c70f85dd7418746ca645592c0f9927a98faae4235ea60ff8a80a7`.
All11 observations compile/verify;15/15 unique description parts correspond after
insertion/highlighting removal. Private structural audits are
`jira-native-adapter-structural-audit.json` and
`jira-native-attribute-bound-audit.json` (old audit preserved; current code view
has language label separately from exact body). **No online Jira semantic
extraction was run.** `jira-native-v17` has two source-only frozen inventories,
complete original source and a prepared canonical runner; no model candidates.

Known remaining Jira integration risk, reproduced with a controlled fixture:
`JiraGene.fetch` returns an already-hydrated nontruncated comments collection
without fetching `renderedBody`; projection v2 correctly rejects a nonempty body
with missing explicit HTML. Direct and truncated-comment fetches now request
`expand=renderedBody`, but the complete hydrated-comment path still needs review.
Local-agent capture/packages also need actual-format parity verification.
Do not silently restore Markdown parsing to hide this risk. There are no real
comments in the acceptance payload, so synthetic parser tests do not certify
connector comments. Tables with spans/nesting, unknown CSS/classes/elements and
HTML comments are explicitly unsupported in this bounded Jira HTML grammar;
verify additional actual supported cases before release.

## Access and reproduction

Python: `/Users/i551096/Dev/memforge-cloud/.venv/bin/python`;
Ruff: same `.venv/bin/ruff`; CF/GH: `/opt/homebrew/bin/cf`, `/opt/homebrew/bin/gh`.
CF target verified: `https://api.cf.eu12.hana.ondemand.com`, org
`GSHCM_AI_Innovation_hcmgcn-wo4dz1tb`, space`dev`.
App`memforge-cloud-service`, guid`1c0e93ef-98a6-4a48-ab8a-c5cb3a671529`,
binding`memforge-aicore`, model`sap/anthropic--claude-4.6-sonnet`.
Actual deployed OSS pin remains57f8b006. No new deployment/reprocess/product writes.
No active model/test process should remain after handoff.

Private `scope-contract-v17/run_canonical_native.py` uses actual CF binding in
memory and verified deployed structured-client factory; its metadata file has
redacted factory/profile, not saved credentials. Do not print `cf env`/rawbinding,
commit private payloads or run old `full-seven-v15`/image-worktree prototypes.
If authorized to rerun, create a fresh experiment directory and preserve old
originals; merely rerunning the script in-place overwrites negative evidence.
The user requested this handoff, not another run from the outgoing agent.

OSS verification command (run from OSS with `PYTHONPATH=src`):
```
/Users/i551096/Dev/memforge-cloud/.venv/bin/python -m pytest tests/test_jira_native_evidence.py tests/test_confluence_native_evidence.py tests/test_source_projection_adapters.py tests/test_source_projection_store.py tests/test_projection_fragments.py tests/test_projection_context.py tests/test_stored_input_currency.py tests/test_jira_gene.py tests/test_extraction_contract.py tests/test_support_reading.py tests/test_evidence_unit_support.py tests/test_extraction_requests.py -q
```
For HANA, put OSS `src` plus every **clean Cloud worktree** `packages/**/src`
on `PYTHONPATH` before the primary editable-install paths, then run
`python -m pytest tests/unit/test_hana_workspace_store.py -q` there. Using only
OSS `src` loads unrelated primary Cloud code and produces an old
`MemorySupportAssertion` import failure; this is not the current tested worktree.
Current HANA suite496passed/20.92s; complete listed OSS suite355passed/27.99s.
Changed Python files in both repos pass Ruff; git diff-check passes. Test logs
are retained privately as `current-iteration-oss-tests.txt` and
`current-iteration-hana-tests.txt` under the native cohort. These prove their
named engineering contracts, not online semantic or deployment acceptance.
Suites overlap earlier checks; do not sum them.

## What remains before success

Resolve/adjudicate named semantic precision and redundant-ref failures with a
proportionate extraction-origin design; do not restart a long patch-per-sample
cycle, add denied fallback stages, erase failures or invent a perfect guarantee.
Validate complete native Jira (including actual comment path), held-out source
families and large documents through the actual current runtime/online model,
with independent source-only inventories and untouched candidate blind review.
Audit every ADR acceptance row, whole-revision outside-ref qualification changes,
atomic Support/lifecycle behavior, historical get_memory/get_resource and adapter
parity. Then perform bounded cutover impact/dry-run/reprocess if authorized and
checked CF deployment/smoke. For deployment use the repository prepare-deploy
entrypoint and 2GB quota skill; never naked `cf push`. Keep PRs draft until ready.
The objective is intentionally unfinished, not marked complete or blocked.
