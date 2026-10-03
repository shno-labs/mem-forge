# Evidence readability regression: historical source replay

Date: 2026-10-01. Repository baseline: `57f8b006`. Commit times below use Asia/Shanghai.
This is diagnostic evidence for [proposed ADR 0046](../adr/0046-separate-evidence-correspondence-from-citation-presentation.md),
not a second design contract or execution backlog. The fixture is synthetic and
contains no provider content, private identifiers or credentials.

## Finding

The table/macro readability regression is reproducible from
[`a8302b5e`](https://github.com/shno-labs/mem-forge/commit/a8302b5e501355c306576f4322a952b14bfd545f),
"Preserve complete evidence structures and localize unresolved claim decisions".
The commit was made on **2026-09-08 at 17:01:42**, and entered main through
[PR #426](https://github.com/shno-labs/mem-forge/pull/426), merge `98788a74`,
at **17:09:39**. Compiler contract 3 became 4.

The deliberate decision was to preserve whole structures. The resulting raw
macro presentation and malformed structure boundaries are defects in the
representation path, not a requirement for exact Evidence matching.

## Causal changes

`pipeline/normalizer_utils.py` added `_StructuralMarkdownConverter`. Tables
with nested paragraphs, preformatted blocks, lists or merged cells were retained
as raw HTML rather than converted to Markdown rows.

`pipeline/evidence_fragments.py` changed Markdown table selection from rows to
whole tables and retained raw serialization as the presentation of structural
HTML. That serialization includes Confluence's custom `ac:` macro elements.

A retained `<table>` is subsequently parsed as a CommonMark type-6 HTML block.
The blank line inside a cell's `<pre>` ends that block. The numbered notes after
the blank line become a Markdown ordered list and absorb later table rows. The
compiler reports no error, so downstream model selection and citation display
receive validly cataloged but incorrectly bounded material. A table without that
blank line can avoid the boundary corruption while still exposing raw macros;
the two failures must be tested separately.

## Fixed-source replay

The [replay script](replay_evidence_readability_history.py) reads the historical
normalizer and compiler from Git and applies each pair to the same synthetic
table: three data rows, a `<pre>` with a blank line and numbered notes, one empty
status, and a later status macro. Run from the repository root:

```sh
.venv/bin/python docs/research/replay_evidence_readability_history.py
```

| Source version | Compiler | Selected structures | Later row swallowed by list | Raw macro in Evidence | Compilation errors |
| --- | --- | --- | --- | --- | --- |
| `a8302b5e^` | 3 | Four `markdown-table-row` fragments, including header | No | No | None |
| `a8302b5e` | 4 | `html-block-atomic`, `markdown-ordered-list` | Yes | Yes | None |
| `05f0f3c2` | 4 | Same broken structure types | Yes | Yes | None |
| `57f8b006` | 4 | Same broken structure types | Yes | Yes | None |

Dependencies and shared projection types are held at the checkout environment;
this establishes a source-code regression boundary, not a replay of every
historical dependency lock or a Cloud deployment. It does not prove the earliest
production occurrence or that all earlier Evidence was semantically correct.
Compiler 3's flattened tables can lose merged-cell and nested-structure meaning,
so reverting the commit is not the proposed fix.

## Relationship to ReadingGroup documents and diagram

The source defect is already present before these later changes:

| Date/time | Commit | Relevant change |
| --- | --- | --- |
| Sep 20, 16:41 | `05f0f3c2` | Unified revision input scope planning and structural reading context; replay still fails |
| Sep 22, 13:11 | `5d5f0646` | Reusable revision context and judgment execution design |
| Sep 24, 16:51 | `83f9f512` | Ordered Support reading, Support/Relation coordination and shared runner design |
| Sep 24, 17:07 | `bb0bdce9` | Added revision flow PNG and Excalidraw diagram |
| Sep 26, 05:37 | `01b70093` | Ordered Support pass after exact correspondence |
| Sep 26, 11:14 | `87e665f5` | Per-ReadingGroup extraction and Unit Title |

ReadingGroup orchestrates complete reading and context; it inherited the
compiler's boundaries and presentation. It can expose a larger retained table
as context, but it did not originate this reproduced normalizer/compiler
regression. The existing [source-sync document](../design/source-sync-to-memory.md)
and [diagram](../design/images/revision-update-flow.png) explain that later
orchestration. The proposed fix retains complete reading while separating
source correspondence and readable, dependency-complete citation selections.

## Acceptance implications

Keep distinct fixtures for macro presentation, complete retained-table parsing,
row/header dependency closure and unchanged-source correspondence after a
renderer change. Prove pinned citations at the UI/MCP boundary as well as in
the compiler. A parser result without errors is insufficient acceptance
evidence when a later table row has become a list item.

Primary sources: [Confluence storage format](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html)
and [CommonMark HTML blocks](https://spec.commonmark.org/0.31.2/#html-blocks).
