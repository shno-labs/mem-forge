# Claim / Evidence failure attribution

2026-10-04. **Supplemental diagnosis, not release acceptance.** This audit does
not replace frozen v18/v19 results, change blind scores or introduce another
extraction architecture. No model call, product write or implementation change
was made for these probes. The [validation report](2026-10-04-claim-evidence-design-validation.md)
and [handoff](2026-10-04-claim-evidence-handoff.md) remain negative acceptance evidence.

## Conclusion and boundaries

The failures have different causes. Historical unreadable Confluence references
are reproducible in deterministic normalization/compilation before ReadingGroup.
V19 Jira omits some native facts before inference. The v19 model also strengthens
source modality and chooses a redundant Required despite explicit generic
instructions. Those output errors establish failure on this cohort, not an
intrinsic Sonnet reasoning ceiling or proof that catalog binding is impossible.

## Historical Confluence regression

The same complete retained native storage was supplied to five historical source
snapshots in isolated Python processes. Imported module paths were recorded;
no new proposed adapter code was used. Each probe applies historical
`html_to_markdown` and `strip_boilerplate`, constructs the
`# title + semantic_markdown` page-body content used by historical projection,
and invokes the snapshot's complete `build_revision_fragment_index` with its
Markdown profile. These are actual current retained document bytes replayed
through historical code, not proof the same bytes existed at those commit dates.

Source SHA-256:
`38eda4ad6e0563c6a759881d1f35817d2ab3a4112a22363600d270d5a2a0789b`.
All snapshots use the same installed dependencies: markdownify 1.2.2,
BeautifulSoup 4.14.3, markdown-it-py 4.2.0. Historical deployment dependencies
were not recovered. All five compiler indexes report no errors.

| Code | Meaning | Fragments | Fragments with literal macro tags | Tags in presentations |
|---|---|---:|---:|---:|
| `58e3baedb762` | Parent of structure-preservation change | 90 | 0 | 0 |
| `a8302b5e5013` | 2026-09-08 structure-preservation change | 39 | 12 | 270 |
| `22205932694e` | Parent of ReadingGroup change | 39 | 12 | 270 |
| `87e665f5efa8` | 2026-09-26 ReadingGroup change | 39 | 12 | 270 |
| `57f8b006962b` | Current deployed OSS pin | 39 | 12 | 270 |

Before `a8302b5e`, Case-14 and Case-20 selections are separate Markdown table
rows of 346 and 722 characters. After it, both fall inside `f000023`, a
7,268-character `markdown-ordered-list` containing 65 literal `ac:`/`ri:` tags.
Its opening matches the screenshot's pattern: `1. Post use $batch will failed!`
followed by the second command comment and concatenated later cases. This
reproduces the reported unreadability pattern; it does not identify the persisted
Evidence row from the screenshot. ReadingGroup's parent and commit produce
byte-identical normalized bodies and identical fragment records/ranges/hashes.

### Isolating normalization and compiler contributions

A second offline 2x2 probe feeds each stored normalized body to the old/new
compiler independently, without changing source text or invoking a model.

| Normalizer | Compiler | Fragments | Literal macro tags | Case-14/20 selection |
|---|---|---:|---:|---|
| Before | Before | 90 | 0 | Two independent table rows |
| After | Before | 68 | 69 | One 7,236-character list item, 65 tags |
| Before | After | 37 | 0 | One 12,959-character Markdown table |
| After | After | 39 | 270 | One 7,268-character ordered group, 65 tags |

Preserving native HTML in normalization is sufficient to expose macro syntax
through this generic Markdown/HTML path. The new compiler's whole-table/group
policy independently broadens citation granularity. The combined change causes
the final observed form; normalization alone also broadens these selections.
A new whole-table compiler alone does not reintroduce macros
when the supplied normalized body has already stripped them.

### Intent and defect

Commit `a8302b5e501355c306576f4322a952b14bfd545f` deliberately preserves complex
HTML structures, changes selection from rows to whole tables/ordered groups,
and permits raw HTML presentations for protected structures. Its amendment to
[ADR 0030](../adr/0030-compile-revision-pinned-evidence-fragments.md), "Complete
structural units and bounded transport", explicitly records that decision.
Protecting headers, spans, ordering and associations was by design. Conflating
that reading/preservation boundary with citation granularity and a readable
representation is a design defect, with a native interpretation gap in
implementation. Preserving original material does not require exposing
transport/macro markup as the user's citation.

This adjacent-commit replay locates an introducing code change for this real
document. It does not establish the first bad production Memory date, exclude
every earlier document-specific issue, or show ReadingGroup has no other effect
on extraction. It shows ReadingGroup was not necessary to introduce this
deterministic representation failure.

Zero macro tags or smaller rows do not establish that the old normalizer
preserved all headers, spans, relationships or meaningful macro values. This
replay does not authorize returning to lossy normalization. Original material
and readable, precisely bound views must both be retained.

## V19 Jira input omissions

Frozen native JSON, projected Observation records and the exact sent prompt were
compared without rerunning extraction. `issue_record` copies only `CORE_FIELDS`:
summary, description, status, priority, assignee, labels, resolution, plus
identity/rendering fields. This whitelist is also present in the historical
deployed adapter; moving it into the proposed source adapter did not expand
field coverage by itself.

| Native fact | Location | Projected records / actual prompt |
|---|---|---|
| Affected version `2609`, not released | `/fields/versions/0` | Absent |
| Component `GBR Country Version` | `/fields/components/0/name` and description | Absent |
| Linked test's landmark/navigation summary | `/fields/issuelinks/*/inwardIssue/fields/summary` | Absent |
| Linked issue summary | `/fields/issuelinks/*/outwardIssue/fields/summary` | Absent |
| Two linked issue keys | Native links and retained Link history | Keys in prompt; summaries absent |

The country/component meaning is provided by native `components`, not guessed
from an undocumented customfield. Native `names` metadata is absent; this audit
does not infer other customfield meanings. Presence checks establish where input
is lost, not that every metadata fact must become a standalone Memory. Test
details may qualify as provenance/context rather than durable knowledge; current
operational status is not automatically lasting knowledge. Materiality and
equivalent-support disagreements still need adjudication under the approved
useful-knowledge standard.

Input-planning checks prove all **projected** authorized fragments were planned;
they cannot prove all useful **native** facts were represented. Source-to-
projection input integrity needs an independent audit. Missing native facts
cannot be attributed to model omission. They remain part of end-to-end
accountability and are not silently discounted to obtain a passing score.

## Model judgment versus capability limit

These errors occur with the needed source already available:

* `confluence-0048`: Primary preserves `A task will be produced ... Fix by`
  and PASS; claim changes this to `A task was produced ... fixed by`. PASS
  makes completion plausible but does not prove the named issue has been fixed.
  Reviewers disagree about severity; source uncertainty must still be preserved.
  The actual prompt requires preserving modality and prohibits invented resolution.
* `jira-0003`: Primary supports WCAG classification; Required labels repeat that
  classification and add no distinct contribution to the final claim/metadata.
  Both reviewers flag it. The actual prompt prohibits duplicate support and
  permits empty Required.

These are inference/instruction-compliance failures in the tested run, not
missing parser fields or provider truncation. No controlled model comparison,
repeated sampling or simpler-task upper bound was established. The experiment
cannot prove an intrinsic reasoning limit. Neither more prompt text nor another
model can be promised to cure these errors; nor do they prove catalog-based
exact selection intrinsically unsound.

Keep frozen coverage numbers as reported, but distinguish input loss, model
omission and materiality/equivalence disagreements. The redundant Required and
unresolved modality failure remain; this diagnosis does not make v19 accepted.

## Reproduction and evidence

Private directory:
`/Users/i551096/Downloads/MemForge-Evidence-Validation-2026-10-02/private/history-regression-20261004`.

* `snapshot-manifest.json`: full commits and extracted source paths.
* `snapshot-full-integrity.json`: post-replay comparison of all 182/182/190/189/194
  source files against the corresponding Git blob identities; zero differences
  or extra non-cache source files. SHA-256:
  `99483fe4021364d4d1641b825594d46a730c220c806955d5c4e5e2e5d82cd744`.
* `replay_snapshot.py`, `replay-process-results.json`, five `replay-*` directories:
  isolated historical normalization/index results and complete presentations.
* `replay_factor.py`, `factor-process-results.json`, four `factor-*` JSON files:
  2x2 normalization/compiler isolation.
* `a8302b5e-representation.diff`, `reading-group-boundary.diff`: Git evidence.
* `audit_frozen_input.py`, `frozen-v19-input-audit.json`: native/projected/prompt
  presence and untouched problem candidates. Audit SHA-256:
  `7067651df3384d902c7aadb80bf4872beb7bd659e6065943bd944392d2b7e33a`.
* `v19-freeze-reverification.json`: all 61 original frozen artifacts and 287
  frozen executable files still match their original hashes after this audit.

Run workers with the selected snapshot's `src` as `PYTHONPATH`, using
`/Users/i551096/Dev/memforge-cloud/.venv/bin/python`. Workers use exclusive output
destinations: choose new directories/files on reproduction. No secret, complete
private source or copied historical source is committed to this repository.

An independent agent checked 35 key snapshot files against Git blobs, verified
all five actual pure normalization/projection paths produce exactly the replay's
page-body content, and independently confirmed the 2x2 and Jira presence results.
The full source report is retained privately as
`independent-causal-review-20261004.md`. It found no material overclaim in the
causal report or v7/Proposed ADR, and requested the normalization-alone wording
clarification incorporated above. This is a causal/method review, not a new
semantic blind score or deployment acceptance.

## Design consequence and next boundary

Clarify A1 to audit material native facts through adapter output into the prompt;
retain A6 as end-to-end useful-knowledge coverage. This does not require dumping
all fields, source-specific generic prompt examples, output pruning or a repair
model. Field policy belongs to the adapter. The existing design already separates
original material, readable views, citation granularity and comparison identity;
the historical replay establishes why that separation is needed.

No replacement architecture is selected or verified. Full A1–A15 acceptance,
authentic consecutive provider revisions, held-out source families, current
parity/product verification and deployment remain open.
