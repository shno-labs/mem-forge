# Selected Evidence with model-generated focused display

Status: In implementation. Selected-block display pilot and functional role review
completed; production integration and release acceptance remain in progress.
Date: 2026-10-06.

Update: persistence, API/MCP, both UIs and actual online production-path replay
are implemented and verified at the seams in the
[integration report](../research/2026-10-06-focused-display-integration.md).
Full coverage and deployment acceptance are not implied.

This proposal records the user's direction after the whole-snapshot summary
experiment: keep Primary/Required selectors and existing source-block
correspondence, while letting the extraction model produce a shorter, faithful
restatement of each selected block. A table row remains an acceptable selectable
block. The earlier frozen experiments and their failed results remain unchanged.

## Flow and ownership

The owning source adapter supplies complete source blocks and their reading
context. Source-specific rich-text, macro, table, and field interpretation stays
inside that adapter. The existing planner and `LlmBatchRunner` execute Claim
Extraction. In the same response that selects each Primary/Required ref, the
model emits its `display_text`. There is no new model call or review/repair stage.

The implemented wire representation is `evidence_displays: [{ref, text}]` alongside
the existing `primary_ref` and `required_refs`. Exactly one display names each
distinct selected ref; catalog resolution still rejects duplicate or ineligible
selectors and binds text by ref identity, independently of canonical Required
ordering. `projection-extraction-v20` invalidates unapplied older extraction work.
Supported results of existing ordered Support Assessment also return displays
in that response; continue/unsupported results remain compact. Its journal
contract is `support-ordered-reading-v9`. No extra rendering model is introduced.

For example, a model selection has this conceptual shape:

```json
{"ref": "R014", "display_text": "A person hired after the cutoff has no paid result for that period. Assigning them to a correction for that period is rejected."}
```

The ref above is illustrative and request-local, not a persistent identity.
The application resolves it against the exact request catalog and retains the
selected block's authentic revision, anchor, original content, content digests,
and existing adapter-rendered text. The generated text is a separate field; it
must not replace the authoritative excerpt, adapter presentation, or their
integrity hashes. Role selection and claim support still refer to the full
selected block, not to the generated text.

Internal storage and service contracts must distinguish generated display from
source excerpt. UI and `get_memory` may present it simply as Evidence text,
without an LLM-generation label or a public generation-origin field. It must
not be declared a verbatim source quotation. Detailed evidence inspection must
expose the retained source block and its revision. A current provider page URL
alone is not historical provenance.
The generated display must not become authority for admission, correspondence,
Support Assessment, or destructive lifecycle decisions.

`display_text` is optional on resolved parts, stored references and read projections;
old references remain readable without fabricated generation. SQLite migration110
and HANA's reference-table column extension persist it separately from `excerpt`.
Derivation outputs and Lifecycle Plan payloads retain it. API detail returns
readable `text` plus the full source `excerpt`; MCP's compact `get_memory` returns
`text` without repeating the full block, and keeps the pinned resource locator.
Both UIs render ordinary text and allow expanding Source evidence when it differs.
No public generation-origin field or LLM label is required.

## Generic generation rule

Copy the selected block's relevant wording as closely as practical, preserving
source language, technical identifiers, material conditions, negation, modality,
sequence, and uncertainty. Omit unrelated material and presentation syntax;
do not replace specifics with an overview or add explanations and conclusions.
Formatting may change to make relationships readable. No fixed character target
should force omission of material conditions.

Each display belongs to its own selected block. Context supplied by that block's
declared adapter view, such as table headers, can identify meaning. Separate
Required content must not be silently rewritten into the Primary display.
Primary/Required selection remains governed by the existing direct-support and
relevant/nonredundant rules. No source-specific examples or syntax rules are
needed in the generic extraction prompt.

## Revision correspondence

Correspondence uses the retained source-block identity/content and existing
context rules. Generated wording never participates in the correspondence
key, and generation variability cannot create a source change.

An unchanged block still needs unambiguous correspondence. Duplicate content
does not establish a unique occurrence. An unchanged ref also does not prove
that distant edits leave the claim supported; existing Change Impact and Support
Assessment responsibilities remain intact.

A comment or other content changing within a selected row can make that row
modified even when the generated display would stay the same. This is the
accepted conservative consequence of keeping row granularity, not grounds for
matching by generated text. Changed evidence is assessed through the existing
lifecycle path, and any retained/generated display must correspond to the
selected target evidence and supported claim. Historical displays and evidence
remain bound to their historical revision.

Program rebind, including exact selection used in coordinator rechecks, preserves
an existing display only when the complete adapter presentation digest is unchanged.
Core correspondence can remain exact while a header or other interpretation
origin changes. In that case old display is cleared; API shows the current complete
source presentation. Semantic reassessment returns new displays with its new refs.
Presentation retention never changes correspondence routing or lifecycle validity.

## Limits and bounded validation

Static checks establish selector validity and source integrity, not faithful
restatement or semantic suitability of Primary. Correct document or row binding
does not make a fabricated sentence true. The user accepts occasional generated
display errors; report their frequency and severity separately from claim and
selected-evidence correctness instead of relabeling them exact quotations.
No new numerical display-error threshold has been accepted. Existing claim,
selected-ref relevance, and useful-knowledge coverage measurements remain separate.
The user's 2026-10-06 role-quality clarification accepts nonideal Primary/Required
choice once joint Evidence delivery and revision lifecycle correctness are verified;
see [ADR0047](../adr/0047-define-claim-evidence-extraction-outcomes.md). Preserve the
old stricter measurements, rather than relabeling the frozen experiment.

The earlier whole-snapshot summary trial did not test this combined mechanism:
it had no selected-block constraints. Its failures are evidence of generation
risk, not proof that this proposal passes or fails. Validate once on the frozen
real source cohort through the actual planner/runner, independently reviewing
claims, selected blocks, generated displays, coverage, and redundancy. Include
bounded revision cases for unchanged moved blocks, duplicate rows, edits within
rows, and changed governing context. Do not change batch policy, prune candidates,
or add a semantic repair step to make the trial pass.

Relevant primary-source precedent: [Anthropic citations](https://platform.claude.com/docs/en/build-with-claude/citations)
distinguish generated response text from source pointers/extracted cited text,
and allow caller-supplied custom-content blocks as citation granularity. This
supports the separation of responsibilities; it does not establish availability
of that provider feature on the SAP route or fidelity of generated display.
