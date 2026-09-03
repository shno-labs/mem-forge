# Parser memory evaluation: remove waste before adding policy

Coordinated by [#385](https://github.com/shno-labs/mem-forge/issues/385).
This evaluates existing behavior, not an observed production OOM. Synthetic,
local, fresh-process measurements; no Source ingestion, LLM, database or Memory
mutation. Baseline OSS `a9f66532`, with local Python 3.12 and installed
`markdown-it-py` 4.x. Live CF quota and full-pipeline headroom were not measured.

## Findings

1. `_markdown_protected_ranges` used the full parser although it only consumes
   block token positions. Inline children, links/emphasis parsing and HTML source
   metadata are unused at this stage. Full inline work remains necessary in
   `_markdown_candidates` for actual Evidence compilation and HTML eligibility.
2. The compiler parses the complete revision before applying authority ranges.
   A later batch can repeat this work. Repetition alone is not evidence of a
   memory leak; these measurements do not establish leak behavior or justify a persistent cache.
   Complete structural context must be preserved; slicing raw Markdown before
   parsing would reintroduce the earlier broken-structure defect.
3. The daemon downloads text into the entire `prepared` list before uploading.
   Therefore retained text scales with the sum of changed file bodies, not just
   the largest file. This is a genuine ownership/lifetime problem already in B's
   approved per-document upload/release plan. That collection change is **not**
   implemented by the parser optimization recorded here.

## One-variable comparison

The same `plan_revision_structural_units` interface was called with identical
revision content and a 6,000-character planning budget. The only variable was
enabling/disabling the parser's inline stage. Every corresponding StructuralUnit
tuple had an identical SHA-256 digest. Values are process high-water RSS increases
above the imported-runtime baseline, not document size or live worker total.

| Synthetic input (~128 KiB each) | Full parser increase MiB | Block-only planning increase MiB |
| --- | ---: | ---: |
| Prose | 0.98 | 0.84 |
| Inline markup/links/HTML | 11.09 | 3.09 |
| Tables | 43.50 | 35.86 |
| Dense `- x` list (32,768 items) | 80.67 | 71.31 |

The prior 256 KiB dense-list repro (65,536 items) was reproduced on the old code:
212.52 MiB process peak, 163.20 MiB increase. After the product change it was
196.00 MiB peak, 143.53 MiB increase. A separate 4 MiB prose run after the change
peaked at 85.94 MiB, a 25.75 MiB increase. These are single-run characterizations,
not portable limits or proof of all-input memory safety. Structural density,
not byte count alone, explains why the smaller stress input costs more.

## Decision and bounded repair

Use the existing parser's supported rule control: disable `inline` only on the
call-local structural-planning parser. Do not disable it on the compiler, replace
CommonMark with regexes, split structures, or introduce a shared parse cache.
The library explicitly separates block and inline stages and supports rule
control ([official design](https://markdown-it-py.readthedocs.io/en/latest/architecture.html),
[usage](https://markdown-it-py.readthedocs.io/en/latest/using.html)).

The new planner-to-compiler regression first failed with 10 unnecessary inline
calls. After the fix, planning makes zero; subsequent real compilation still
parses inline content and emits eight validated tag-free HTML paragraph
fragments. Existing structural/HTML/catalog tests retain exact Evidence behavior.

Do not add a generic parser-budget framework merely because this pre-existing
stress input is expensive. It is not the root cause of the two GitHub byte-read
failures. Equally, do not claim the small planning optimization removes the
remaining full-compiler cost. B still needs bounded raw-byte correctness,
per-document body release, and input-compatibility/resource validation. A new
cap must not silently reduce existing support; 4 MiB remains unadopted.

## Reproduction

The diagnostic-only harness `/tmp/memforge-parser-evaluate.9nbUlM/compare.py`
used the real planner, repeated prose/list/table/inline fixtures, and independent
processes. `full` and `block` modes differed only in parser rule configuration;
the baseline measurements were taken before the product change. The original
`/tmp/memforge-text-budget.xCI40Y/probe.py` reproduced the 256 KiB and 4 MiB cases.
Neither temporary path is a product or CI dependency.

Permanent regression command:

```sh
PYTHONPATH=src:tests python -m pytest \
  tests/test_projection_context.py tests/test_evidence_fragments.py \
  tests/test_projection_fragments.py -q
```

Issue #385 owns further work; this document is measurement evidence, not another
execution backlog. No merge, deployment or production remediation is claimed.
