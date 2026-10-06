# Model comparison: execution evidence and outstanding gates

Date: 2026-10-05. Status: **incomplete; no production design accepted or deployed**.
The [frozen protocol](2026-10-05-model-comparison-protocol.md) remains the
comparison contract. This report does not replace the prior failed Sonnet
extraction scores or the release acceptance contract.

## Execution status

| Work | Evidence | Limit |
|---|---|---|
| Paired Sonnet A/B/C execution | Eight logical calls completed against verified deployed Sonnet 4.6 configuration; ten provider attempts, seven parsed successes and one terminal failure | Fresh CF login resolved the earlier auth block; no production write or deployment |
| Independent extraction inventories and blind review | Two source-first evaluators froze inventories before outputs: A 135 atoms, B 132 including five supplementary; both reviewed all 170 candidates and 186 refs | No case meets every frozen per-family gate; denominators and usefulness-boundary disagreements remain separate |
| Literal relocation probe | Eight controlled cases' exhaustive exact locations independently checked | Five unique occurrences, one ambiguity, two missing quotes; no authentic consecutive provider revisions or model-generated mapping |
| Controlled full-Markdown Jev probe | Eight real provider responses; five clean supported expectations matched | Three cases are diagnostic due to source conflicts or scope ambiguity; this is not an eight-of-eight accuracy acceptance |
| Complete native Confluence/Jira Jev probe | Six real provider responses; two supported claims accepted and four altered unsupported claims not accepted | Exact three-class agreement is five of six; small hand-authored cohort, no extracted refs, coverage or lifecycle acceptance |

No model self-review, semantic post-processing, candidate pruning, provider-limit
increase, document clipping, introduced splitting or product writes were used.
The shared structured client retains its existing parsing recovery and JSON-text
format-repair/retry policy; zero output-format recovery is not claimed.
Private inputs and outputs remain in the local validation evidence directory.

## What the native classifier probe establishes

Actual returned model for all fourteen Jev calls was `jev-1.13.0`.
The native Confluence source contains 70,981 characters / 71,051 UTF-8 bytes;
the Jira source contains 50,807 characters / bytes. Each of the six requests
used its complete unchanged native source, not a selected excerpt.

The installed Jev wrapper rejects more than 60,000 characters before provider
admission. This is a wrapper constraint, distinct from the official API's
64k-token total and 32k-token state-plus-longest-question limits. The native
probe used the documented HTTP API without changing those limits. Each request
contained one complete document and one question; no retry or input reduction
was needed. Credentials were consumed in runtime memory and never persisted.

| Source | Questions | Actual input tokens per question | Approximate wall time per question |
|---|---|---|---|
| Native Confluence | Three | 26,797–26,806 | 1.63–1.70 seconds |
| Native Jira | Three | 21,619–21,620 | 1.48–1.68 seconds |

The classifier accepted both source-backed claims and did not classify any of
the four deliberately altered claims as supported. This is positive mechanism
evidence for fixed-claim support judgments on complete native material. It
does not test claim extraction, arbitrary quotation selection, display fidelity,
reference identity or useful-knowledge coverage.

For one condition-expanded Jira obligation, the predeclared label was
`insufficient`, but the model returned `contradicted` with confidence 1.0.
The source-first evaluator had already identified a pragmatic ambiguity between
those two labels while ruling out `supported`. Preserve the original label:
exact agreement remains **5/6**, not 6/6. Distinguishing insufficiency from
contradiction can affect lifecycle decisions, so successful rejection of the
altered claim does not establish safe destructive lifecycle classification.
Confidence is not measured correctness.

The source/claim/label audit was completed before calls. Its original hash was
preserved. However, the supplemental audit of the exact final HTTP wording and
state shape finished after the responses. The final request wording differs
from the cohort proposal while sources, claims and labels remain unchanged.
Record this as post-run transport verification, not complete pre-execution
transport adjudication or a release-grade blind validation.

## Measured cost and context implications

The controlled Markdown probe consumed 40,398 input / 358 output tokens.
The complete native probe consumed 145,260 input / 276 output tokens.
At the archived current official TypeSafe rate of $0.042 per million input
tokens, with free output, the arithmetic estimates are $0.001696716 and
$0.00610092 respectively, or approximately **$0.0078 total**. This is a public
price calculation from actual usage, not an invoice or a Sonnet cost measure.

A complete native Confluence support question cost approximately $0.00113 in
this cohort. Repeating the complete state for every ref or Memory multiplies
that cost. The official API can share a state across independent questions;
this experiment did not implement or approve a production grouping policy.

The observed Confluence requests already use about 26.8k input tokens. They
do not demonstrate arbitrary large-document support: a longer state or both
complete old and new documents may exceed the official state/question limit.
No input-windowing or semantic mapping policy has been accepted to resolve
that future boundary.

## Paired Sonnet execution and method limits

Verified configured and invoked online model route: `sap/anthropic--claude-4.6-sonnet`.

| Source | Catalog A | Rendered flexible-quote B | Native-quote C |
|---|---|---|---|
| Confluence | 56 candidates; all Primary bound | 53 candidates; 12 Primary missing | Terminal logical deadline after three attempts |
| Jira | 5 candidates; all Primary bound | 5 candidates; one Primary missing; method-qualified | One candidate; Primary missing |
| ADR0040 | 29 candidates; all Primary bound | 21 candidates; ten Primary missing | Not planned |

The terminal native Confluence request first returned a schema enum error at
`memories.49.memory_type`; JSON-text fallback then returned invalid JSON; the
third attempt exhausted the shared 300-second logical deadline. The first two
responses each ended with `stop`, at 14,630 and 14,301 completion tokens. This
is not an observed 32,768-token truncation. Raw malformed content was not
persisted in this original experiment; diagnostics do not identify the actual
invalid enum value, so it is not reconstructed or guessed.

The production planner packs authorized ReadingGroups into the fewest fitting
requests and existing incumbent assessment groups Memory IDs. In this cohort,
the unchanged planner produced one extraction request per document. A uses
that execution path. B/C deliberately use one direct complete-document
structured call; they do not exercise the production batch runner's splitting
or recovery. A terminal B/C call cannot prove production batching failed.
The input-fit estimate also does not guarantee output validity or execution
time. No split or policy change has been introduced to make the comparison pass.

The independent reviewers separately verified all 162 located/bound selected
refs against their actual representation carriers. All passed; the 24 missing
Primary occurrences remain missing. Native semantic assessment remains
independent: bound coordinates are not semantic proof. Neither exact excerpt
selection nor forced cross-revision ref mapping can explain every failed gate;
the eight calls exercise extraction on single snapshots, not revision mapping.

Jira B has an actual transport defect in the experimental harness: universal
newline reading removed 32 CR characters, while 25/95 structural ranges still
referenced the pre-normalized material. It is retained as a compromised,
descriptive case, not a clean causal comparison. Original frozen bytes remained
unchanged, but final byte/hash correspondence was not enforced at every read.
The method audit also records incomplete dependency freezing and limited raw
failure capture. These limits do not justify rerunning or rewriting failed
outputs under the original case identity.

## Whole-snapshot summary trial

The [revision-bound summary proposal](../design/claim-evidence-summary-citations.md)
was frozen independently and reviewed before inference. The final method audit
closed five named recording/admission gaps without altering any source, prompt
or schema bytes. All 275 frozen files matched at dispatch and after execution.
The trial uses the same complete native inputs, configured Sonnet route and
budgets; there is no quotation, offset selection or ref-to-ref mapping gate.

| Source | Candidates / refs / Required | Provider attempts | Elapsed |
|---|---|---|---|
| Confluence | 46 / 46 / 0 | Two; native-schema enum error then successful JSON-text fallback | 142.781 s |
| Jira | 3 / 4 / 1 | One | 14.449 s |
| ADR0040 | 18 / 36 / 18 | One | 55.264 s |

All three logical calls completed, with four provider attempts. Reported usage
is 79,462 prompt and 18,397 completion tokens including the failed Confluence
attempt. That first attempt is now preserved before schema validation: its
valid JSON contained 31 candidates, 13 labeled `requirement`, outside the four
allowed types. The fallback returned 46 schema-valid candidates. No types were
coerced, and the failed attempt is not relabeled a successful extraction. No
output reached the token cap. Requested schema transport is not independent
proof of provider-side constrained-decoding enforcement.

The two original source-first reviewers are assessing all 67 final candidates
and 86 selected support summaries against their unchanged inventories. Each
summary explicitly declares whole-snapshot scope and generated display origin;
its snapshot identity is checked independently of semantic truth. Exact quote
occurrence is not a gate for this citation kind. Coverage remains explicit
Memory content: useful independent assertions only appearing in a support note
do not become separately retrieved Memories, and a note cannot substitute for
a missing central claim condition. Raw denominators and usefulness-boundary
disagreements remain visible. Final independent semantic review is complete; no source family meets all accepted gates.

## Sealed summary-citation review

Both independent reviewers examined every final candidate and ref, and every
original inventory atom. Inventories and earlier reports stayed unchanged.
All 86 declared snapshot bindings match the authentic retained source bytes.
Neither reviewer required an exact quote, offset or ref-to-ref mapping.

| Source | Reviewer A explicit Memory coverage | Reviewer B explicit Memory coverage | Selected Required |
|---|---|---|---|
| Confluence | 36/61 (59.02%) | 37/62 (59.68%) | None; recall not penalized |
| Jira | 7/9 (77.78%) | 6/10 (60%) | 1/1 |
| ADR0040 | 10/65 (15.38%) | 9/55 (16.36%) | Both: 16/18 (88.89%) |

These are useful-knowledge coverage scores, not the percentage of truthful
claims. The reviewers disagree about some granularity, materiality and severity
boundaries; their denominators and detailed findings remain separately visible.
Both identify the ADR claim/Primary placing the Document pointer before Unit
revision, contrary to the source's raw-then-revision-then-pointer order. Both
identify a Required summary falsely restricting stored input to syncs that
actually commit, and a Confluence Primary inventing a next-period correction
target. Reviewer A additionally classifies omitted release/paid/retro conditions
and cleaned-up ambiguous chronology as major. Do not pool overlapping findings
or choose the more favorable reviewer as acceptance.

Many independently useful ADR facts appear only in support notes. Under the
predeclared standalone-Memory measure these are not full claim coverage, even
where the notes are faithful. Historical metrics and bundled pointers retain
explicit usefulness-boundary caveats; no denominator was repaired after seeing
outputs. The shared write-order error alone already violates the accepted
zero-major-error gate, independently of those disputes.

**Causal conclusion:** this whole-snapshot experiment has no exact excerpt or
cross-revision mapping step, yet still fails semantic and coverage acceptance.
Removing those constraints alone is therefore insufficient for the tested
strategy. This does not prove excerpts are mandatory, static matching is always
appropriate, or Sonnet has an intrinsic ceiling under every architecture. The
small comparison changes several input/output choices together; it cannot
isolate a single causal contribution or establish population accuracy.

The trial produces readable derived notes and authentic coarse provenance.
Those are separate achievements from faithful direct support and useful claim
coverage. No candidate filter, semantic repair layer, schema coercion, smaller
batch policy or production deployment was introduced in response to failure.
The current summary proposal remains unaccepted. The requested updated
[handoff](2026-10-05-claim-evidence-current-handoff.md) preserves all failure
and replay evidence before another architectural iteration.

Production adoption still requires authentic immutable evidence snapshots:
latest-only stored raw input does not make a historical revision citation
readable. Historical observation representations must be demonstrably complete
before reuse. Semantic support on new revisions is a separate incumbent-claim
assessment; similarity cannot fabricate provenance or destructive authority.

Authentic consecutive revisions, complete incumbent assessment, arbitrary
large-document capacity, shared citation API/store integration and deployment
acceptance remain outstanding. No extraction-only trial proves stable future
lineage or production readiness.

## Evidence identifiers

Local private root: `model-comparison-20261005` under the existing validation
directory. Full customer/provider source text is not copied into this report.

* A/B/C input/executable freeze aggregate:
  `70edb31142f33061196ef28499d9b12a5601e4f6c07e29ead600268c47d04b07`.
* Inventory A: `a051d85cd54bee22eb947c99f13a8b5ee7ee86346913bdc81b4ff84122a5ae5e`.
* Inventory B: `4dd77aae06c0a26f104a7c06de64b39509b8baf7fcac14db9e9a108aa2b04799`.
* Controlled revision cohort:
  `8a52b221106922c52c115e28867fb50f5f9b015c8a67d79dbb203d6de36139d5`.
* Native classifier cohort:
  `bef74c4520774e457490d8c0d1ff6ebf5bdbe6806dac70386dd7c19e53e28a01`.
* Original pre-inference native claim/label audit:
  `f7c0e50934c24e28d8e1597c483062d4113e32fe26d6dff54620bb87675dcf8c`.

The first audit survives byte-identically in its preserved snapshot; its later
transport supplement has a separate hash. Raw provider model/answers/usage,
request hashes, locator ranges, ambiguity dispositions and independent reviews
are retained alongside the cohort, including the CF authentication failure.
