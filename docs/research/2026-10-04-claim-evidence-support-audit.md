# Support Assessment contract audit

2026-10-04. Read-only audit of the fresh worktree against design v7. No product
code/prompt changes, online model calls or production writes. This is additional
negative/structural evidence, not another extraction architecture or release
acceptance. The frozen v19 semantic scores are unchanged.

## Runtime flow

1. `memory/engine.py` loads every scoped incumbent's active Support parts and
   their own pinned Observation revisions. Each Support uses its validation
   baseline, rather than assuming all Evidence came from the last Unit revision.
   An unavailable baseline requires full-current reading when no part is
   UNKNOWN; UNKNOWN parts still take precedence and remain unresolved.
2. `pipeline/support_reading.py` compares each part against complete old/new
   representation indexes. Exact correspondence and whole-claim validity are
   separate. Every part exact and no revision changes permits program rebind;
   exact parts with other changes require Change Impact; changed/removed or
   ambiguous parts require Support Assessment. UNKNOWN parts leave the whole
   Support unresolved.
3. `pipeline/revision_work.py` supplies fixed claim/type/effective dates, current
   source interpretation, corresponding prior refs or historical excerpts,
   changed/removed material and carried witnesses. A usable baseline puts all
   changes and the Support's current Evidence first. Without one, the first part
   is the whole current revision. Current refs remain selectable; historical
   excerpts do not.
4. Change Impact UNAFFECTED permits reuse only with every part exactly current.
   AFFECTED or an impact execution failure takes the ordinary assessment route.
   Assessment selects current Primary/Required for the fixed claim. An
   unsupported result can retire Support only after complete ordinary reading;
   a candidate-local conflict recheck is not such absence authority.
5. The revalidated RawMemory copies the incumbent's content, type and validity
   boundaries. It does not rewrite the claim. Relation coordination can request
   its existing bounded recheck for a conflict; this is not new-candidate
   extraction self-review. Existing Candidate Admission separately judges value
   and same-round duplicates, with no evidence-completeness rejection/reselection.

Relevant current methods: `plan_support_revision`, `_correspond`, `_route`,
`RevisionWorkExecutor.assess_many`, `_change_impact`, `_read`, `_chain_task`,
`_revalidated_memory`, and `MemoryEngine.prepare_and_commit_projected_lifecycle`.
Source syntax interpretation is supplied through representation contracts; these
Support methods do not parse Confluence macros or Jira-specific keys.

## Real native no-change probe

The actual isolated SQLite data from the frozen-native delivery probe supplied
61 stored Memories and 64 active parts. Complete authentic native sources were
reconstructed with their original identities. The actual Support planner and
executor rebound all 56 Confluence/57-part and five Jira/seven-part Supports
against the **same pinned revision**, with zero model calls. Content, type,
anchors, roles, excerpts and composite descriptors were preserved exactly.

This closes a named structural seam for native composite Support, not semantic
acceptance. It is not cross-version insertion/reordering evidence, an authentic
consecutive provider revision test, a Change Impact judgment, a lifecycle commit
after assessment or proof that failed v19 claims are true. The first harness
attempt incorrectly accessed `Memory.doc_id`; provenance lives separately. Its
failed script/log/result are retained. The corrected probe uses the actual
`get_memories_by_source_doc` API and verifies the complete cohort counts.

## Confirmed implementation/contract differences

### Duplicate selectors are silently normalized in Support

The canonical catalog resolver rejects a Primary repeated in Required or a
repeated Required selector with `duplicate_ref`. However, Support's
`_resolved_selection` calls `_distinct_required` first, removing those selectors
before validation. A private full-current executor probe supplied a schema-valid
fixture verdict with the Primary repeated twice in Required: one fixture request
produced supported with one resolved part. No online model was used.

The helper already exists at deployed baseline `57f8b006`; the existing
`test_noop_duplicate_required_refs_normalize_without_retry` integration fixture
explicitly expects it. This is not a newly introduced source-adapter defect or
Candidate Admission repair. It is a shared Support implementation and test
expectation inconsistent with v7's requirement to surface malformed references
rather than silently clean them into success.

Selector duplication and semantic redundancy must not be conflated. Two distinct
valid selectors that repeat the same meaning are **not** removed by this helper.
It cannot fix the actual v19 WCAG Primary/Required failure. Any correction must
respect the shared resolver contract at model-response decoding; it must not
introduce a semantic pruning/repair stage to alter acceptance scores.

### Corrupt descriptors share the incomplete-coverage outcome

`_correspond` returns UNKNOWN when a stored supported descriptor fails equality
with its reconstruction, raw/presentation integrity is inconsistent, or an old
view is unsupported. `_route` then uses UNRESOLVED_PARTIAL_COVERAGE. An independent
private probe distinguishes supported-v1 corrupt origins, unsupported view
versions and retired profiles and reproduces that outcome under complete input.

No exact rebind or destructive absence decision is made for these cases, which
preserves the tested safety boundary. But supported-contract corruption is a
technical integrity failure under v7, not provider partial coverage. Unsupported
historical interpretation may remain explicitly unavailable/unresolved; it must
not be relabelled as corrupt merely because its compiler is unavailable. The
implementation currently loses that distinction. The shared OSS boundary needs
to enforce the already specified difference; a HANA/source-type workaround would
not satisfy the design.

Some existing comments still say retired Evidence is dropped. Current code
retains it as UNKNOWN and prevents reuse; comments are not evidence of actual
dropping. Reprocess removes the baseline but does not override that UNKNOWN
guard; this audit does not establish that the complete upgrade path can recover
every old incompatible Support. A14 still requires bounded end-to-end evidence.
No product edits are included in this audit.

## Model and acceptance boundaries

Support Assessment uses the supplied main model. Change Impact uses
`decision_task_model`; the current evaluated-task registry is empty, so it also
uses that main model even if a decision model setting exists. This is a static
routing fact, not proof that either stage ran online. Frozen v19 telemetry records
`projection_fragment_memory_extraction` only; that Sonnet experiment does not
validate online Support or Change Impact accuracy.

A separate historical eight-fixed-claim probe used three Sonnet requests on
2026-10-02. It patched the then-current support definition and used mapped
representations without baseline/prior Support; no Change Impact request ran.
It remains historical limited evidence, not current native/v7 held-out semantic
acceptance or proof of a model capability ceiling.

Deterministic/fake-client tests prove routing, state accounting and exact binding.
They cannot establish A10's semantic judgments about exceptions, framing or
outside-ref changes. The implementation differences above also prevent claiming
the complete Support contract is covered. No model capability ceiling follows
from these deterministic defects or from the still-unverified semantic stages.

The independent seam run passed 95 tests and failed three retired-UnitTitle
tests. All three failures occur constructing outdated Jira fixtures without
explicit provider-rendered HTML, before the Support assertions execute. Do not
label them as three runtime retirement defects or silently claim full suite
convergence. Their old dropping/rebind expectations also need review against
the current contract; this audit did not edit fixtures or rerun a smaller green
subset to hide the failures.

## Evidence

Private parent probe:
`/Users/i551096/Downloads/MemForge-Evidence-Validation-2026-10-02/private/support-contract-20261004`.

- `probe_support.py`, preserved `probe-support-attempt-1.py`, original failed
  command/log/result, and successful `attempt-2/` command/log/result.
- Successful fixture prompt and raw response are retained privately, not in Git.
- Independent audit/probe artifacts are copied beside the parent evidence.
- `freeze-reverification.json` confirms all 61 original frozen artifacts and
  287 frozen executable files still match their hashes after these audits.

The [delivery validation](2026-10-04-claim-evidence-delivery-validation.md),
[causal audit](2026-10-04-claim-evidence-causal-audit.md) and
[semantic validation](2026-10-04-claim-evidence-design-validation.md) describe
different checks. Their passing portions do not override the failed quality gates
or missing A1–A15 acceptance variants.
