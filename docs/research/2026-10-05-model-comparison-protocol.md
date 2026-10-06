# Catalog versus flexible quotation: frozen comparison protocol

Status: experimental, not an approved production replacement. Date: 2026-10-05.

This experiment follows the [model-led assessment](2026-10-04-model-led-ref-extraction-assessment.md).
The user authorized comparing mechanisms rather than further tuning catalog
prompts. Existing release gates remain unchanged. No production writes, deployment,
candidate pruning, model self-review, semantic repair or prompt tuning after outputs.

## Questions and controls

1. Does allowing a continuous quotation improve direct Primary selection and
   coverage, with the available readable source material held constant?
2. Does supplying complete native material recover knowledge absent from the
   adapter's material, and can model-produced readable interpretations stay faithful?
3. Can unchanged quotations relocate exactly after controlled revisions, and
   can a probabilistic classifier distinguish contextual invalidation from relocation?

| Arm | Source input | Citation selection |
|---|---|---|
| A | Current canonical catalog and its structural context | Existing selectors and production resolver |
| B | The same catalog source views, order and interpretation metadata | Verbatim continuous quote, with optional immediate prefix/suffix |
| C | Complete retained native source | Verbatim native quote plus separately labelled model-produced readable interpretation |

B retains adapter omissions. B is not a parser-free design and does not prove
native input completeness. A/B share the existing substantive knowledge rules;
their reference instructions/schema differ. C changes both representation and
input completeness, so it cannot isolate granularity. A focused quotation can
cross previous fragment boundaries. Exact quotation location proves provenance,
not semantic support or faithfulness of a generated interpretation.

The paired pilot comprises the complete retained Confluence storage document,
complete Jira issue/history document, and repo-owned ADR 0040 Markdown (A/B;
C would duplicate the Markdown input). These are authentic snapshots, not
authentic consecutive provider revisions. The ADR is additional format evidence;
do not claim statistically representative performance or a held-out corpus
without auditing its earlier exposure.

Every arm sends a complete per-document input under the existing configured
Sonnet output/context limits. No limit increase or introduced document splitting.
Preserve transport failures, malformed output and unlocatable/ambiguous quotes;
do not remove candidates to improve the score. Freeze sources, prompts, schemas,
executable hashes and request counts before paid calls. Use the verified deployed
SAP AI Core Sonnet factory and current CF binding in memory only. If credentials
or factory verification are unavailable, paid execution remains pending.

## Measurement and independent review

Two fresh independent evaluators receive only native originals and criteria,
freeze useful-knowledge inventories, then receive all results with anonymous
arm labels and shuffled order. Record per-document coverage and disagreements;
do not pool away a failed source family. Gates: no major claim or Primary error;
at least 95% useful coverage without missing material conditions; at least 95%
selected Required relevant and distinct, with best-effort supplementary recall.
Also count unreadable or misleading citations and locator outcomes. Model-readable
interpretations in C are assessed independently, never treated as verbatim quotes.

Record actual request/response tokens, wall time, provider calls/retries and
transport status. Any direct-provider-price arithmetic is an estimate, not the
SAP AI Core invoice. This pilot is mechanism evidence, not a full release gate.

## Revision experiment boundary

Use a separately frozen controlled-edit cohort derived from authentic text.
Include insertion, relocation, repeated identical text, meaning-preserving edits,
changed governing conditions outside the quote and changed outcomes. Record
literal location and semantic support as separate judgments. Freeze expected
answers before inference; never label controlled edits as provider history.
Jev may classify candidate relationships and fixed-claim support; it cannot
generate arbitrary citations. Its confidence is not measured correctness.
Candidate recall, false matches and uncertainty must all be reported. Native
provider revision acceptance remains a separate required gap.

Results adjust the design only after this frozen comparison. A failure is
attributed to input availability, selection/locating, semantic extraction,
generated display, or provider execution instead of adding a catch-all fallback.
