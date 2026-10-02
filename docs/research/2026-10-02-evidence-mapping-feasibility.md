# Evidence mapping: real-content and online Sonnet feasibility evaluation

Date: 2026-10-02. Design baseline: `7cefb371`; public corpus pin: `57f8b006`.
This report supports [proposed ADR 0046](../adr/0046-separate-evidence-correspondence-from-citation-presentation.md).
It does not describe released behavior or authorize deployment. Private provider
content, identifiers and credentials are excluded from this repository.

## Question and falsifiable criteria

Can exact source selection correspondence survive harmless revision/presentation
changes while citations become readable, without inventing provenance or losing
valuable claims to reduce ref count?

Mechanical success requires exact pinned source binding for every displayed
value, both-side occurrence uniqueness or verified structural disambiguation,
same Source/Unit/Observation authority, and separate interpretation/dependency
checks before Support reuse. Corrupt bindings, cross-Observation reuse,
unresolved duplicates and changed dependencies must fail their respective gates.

Semantic success requires direct Primary selection, necessary Required refs,
complete qualifications and retained durable knowledge together. Fewer refs or
more extracted candidates alone are not success. No admission repair, semantic
pruning or new candidate rejection rule is used in this experiment.

## Real inputs and controlled experiments

| Input | Unicode characters | Source status | Evaluation role |
| --- | ---: | --- | --- |
| Private Confluence document | 70,032 | Retained normalized snapshot; 11 retained HTML tables, macros, nested code/lists, merged cells | Complete-document mechanical and paired extraction |
| Private Jira document | 2,076 | Read-only normalized content; 2,112 UTF-8 bytes | Complete-document paired extraction and source-mapping validation |
| ADR 0034 | 123,896 | Repository text pinned to `57f8b006` | Complete-source mechanical/capacity stress |
| ADR 0045 | 11,600 | Repository text pinned to `57f8b006` | Complete-document paired extraction and source-mapping validation |

The actual current compiler reports `catalog_too_large` for the pinned ADR 0034
under its unchanged 120,000 presentation-character contract. It is excluded
from all paired semantic arms and retained as an explicit capacity failure.
No chunking, increased limit, schema split or batching bypass was attempted.

Provider native raw-resource requests for the two private documents returned
404. Consequently this experiment tests real retained normalized content and
controlled revisions of it, **not native provider history or consecutive real
provider versions**. Insertions, rearrangement, value changes, duplicates and
repeated large inputs below are explicitly controlled perturbations.

The deterministic probe also uses the full current source-agnostic extraction
design and current ADR 0034 as a separate mechanical cohort; its checks do not
depend on model-selected passages. The exported four-document readable catalog
is independently frozen and validated.

## Deterministic mapping and readable representation

The private prototype is outside the runtime import path. It parses retained
source structures once, keeps Unicode scalar half-open spans and raw integrity,
indexes exact structured content values, verifies candidate equality/cardinality,
and renders mapped values independently of correspondence. It does not use an
LLM quote, fuzzy text, rendered-text equality or arbitrary diff tie-breaking.

After adding the duplicate-collapse counterexample: **65 PASS, 0 FAIL, five
explicit limitation groups**. These cover native input/history availability,
production/semantic contracts, prototype representation scope, absence of real
provider revision sequences, and complete interpretive closure.

The initial prototype incorrectly accepted two identical base occurrences
collapsing to one target. Three new counterexample checks failed before the
both-side cardinality correction and pass afterward. This motivated ADR 0046's
clarification: material correspondence does not prove physical edit survival,
and target uniqueness alone cannot certify occurrence identity.

Deliberate guard faults demonstrate that the suite can turn red:

| Disabled guard | Failed checks | Process result |
| --- | ---: | --- |
| Source integrity | 9 | Exit 1 |
| Header/dependency reuse gate | 1 | Exit 1 |
| Same-Observation authority | 3 | Exit 1 |

All **344 exported Fragments** validate their exact source bindings and displayed
value provenance. All 11 Confluence tables retain complete source selections;
299 cells carry source-verified row/column/merged-cell coverage. Stored macro
status titles and issue keys are represented; control markup is hidden without
inventing business values. Empty status remains explicit unknown.

Merged tables have selectable complete mapped structures. Local merged-row
closure remains unproven and is not offered as safe local Evidence. General
footnote/scope closure and a native Confluence XML profile remain unimplemented.

| Controlled repeated/reordered real tables | Characters | Compilation median | Fixed 48-row lookup median |
| --- | ---: | ---: | ---: |
| 1x | 66,044 | 63 ms | 12 ms |
| 2x | 132,090 | 118 ms | 12 ms |
| 4x | 264,182 | 243 ms | 12 ms |
| 8x | 528,366 | 477 ms | 13 ms |

The repeated input deliberately creates ambiguity; lookup timing includes
ambiguous outcomes, not successful matches for every duplicate. These are local
prototype observations with a cached immutable input/index, not an asymptotic
proof, production benchmark or large-document semantic capacity acceptance.

## Independent semantic replay and blind review protocol

Three fresh agent contexts read the complete supplied catalog for each paired
document, with the same unchanged durable-knowledge rules and response schema:

1. Actual current compiler presentation and current extraction prompt.
2. Identical current compiler payload and the source-neutral selection prompt.
3. Source-mapped readable prototype presentation and that same selection prompt.

The initial auxiliary experiment used independent Codex agent replay. It was
explicitly superseded as provider-quality evidence when the user required online
Sonnet verification. Its results remain a separate auxiliary comparison; they
are not combined with the Sonnet denominator. Claude Code could not participate:
its read-only readiness request returned that the account is on hold. Thus this
is context-independent review within one model family, not cross-model evidence.

The first preparation attempt exposed internal `f` IDs directly instead of the
runtime's `p/r` catalog IDs. That attempt was interrupted and excluded. Corrected
inputs were frozen, checked for identical payloads in arms 1/2, and replayed in
new contexts. No candidate was repaired or discarded after generation for
citation quality.

Two other fresh agents first receive only full original sources and unchanged
quality rules. Each writes its expected-claim inventory before seeing candidates.
Then they receive anonymous variants with order randomized separately per
document, selected citations, exact source selections and pinned content hashes.
They receive no arm identity, proposal, generation prompt, implementation,
coordinator hypothesis or peer review. The coordinator retains the unblinding
manifest. Candidate IDs and all selected refs undergo mechanical validation.

### Actual online Sonnet replay

Read-only CF CLI and SSH verified the running dev app's profile, AI Core binding,
Cloud client factory and OSS pin (`57f8b006`). The provider is
`sap/anthropic--claude-4.6-sonnet`, not a Codex simulation or the unavailable
Claude Code account. Credentials are not included in the experiment packet.

An isolated replay used the CF-bound SAP AI Core online endpoint through the
canonical `LiteLlmStructuredClient`, native `json_schema_response_format` and
`memforge_prompt` template-variable transport. Although the local Cloud factory
source is older, every resulting structured-client configuration field was
compared with the actual deployed factory and was equal for this model/config.
The exercised OSS client, request-budget and extraction prompt files are unchanged
from the deployed OSS pin. No unrelated Cloud module was loaded as an end-to-end
runtime proof.

All **9 logical calls / 9 provider attempts succeeded**, with native schema,
no retries or schema fallback. Provider-reported usage: **99,454 input + 12,401
output = 111,855 tokens**. All **79 candidates** pass the production Pydantic
response schema and known-ref/role/span checks; no output was repaired or pruned.

| Online Sonnet arm | Confluence candidates / Required parts | Jira candidates / Required parts | ADR 0045 candidates / Required parts |
| --- | ---: | ---: | ---: |
| Current representation + current prompt | 10 / 15 | 3 / 5 | 11 / 22 |
| Current representation + generic selection prompt | 10 / 5 | 2 / 2 | 11 / 4 |
| Readable mapped representation + generic selection prompt | 19 / 11 | 2 / 2 | 11 / 1 |

These are emitted counts, not accepted-claim or coverage scores. A decrease in
candidate count may reflect duplicate removal or lost knowledge and requires
source review. Two additional fresh agents independently froze 34 and 39 expected
claims from full sources before receiving any of these 79 anonymous candidates.
They did not see the auxiliary Codex candidates or reviews.

This is online-provider document-level replay with complete catalogs, **not the
deployed per-ReadingGroup runner, admission or lifecycle commit**. No model output
is admitted to production. That execution boundary remains an explicit release
gap; provider success must not be labeled a full pipeline smoke test.

### First online blind review: semantic acceptance failed

Both reviewers read all 79 candidates and 96 unique selected citation entries.
They agreed that the readable arm had no non-direct Primary in this cohort and
substantially fewer unnecessary Required parts, but it lost usable knowledge
coverage and emitted unsupported qualifications or transient assertions.

| Arm | Accepted as emitted, reviewer 1 / 2 | Non-direct Primary, reviewer 1 / 2 | Unnecessary Required parts, reviewer 1 / 2 |
| --- | ---: | ---: | ---: |
| Current representation + current prompt (24 candidates) | 13 / 13 | 2 / 1 | 28 / 31 |
| Current representation + generic prompt (23 candidates) | 10 / 11 | 2 / 1 | 1 / 1 |
| Readable representation + generic prompt (32 candidates) | 10 / 8 | 0 / 0 | 7 / 7 |

These categories overlap and are not production admission actions. Durability
exclusions use the unchanged existing policy, distinct from citation defects.
The readable arm had 5/8 incomplete-qualification judgments and 19/20 durability
exclusions. More emitted candidates did not compensate for lower usable coverage.
This falsifies the first generic-prompt version's semantic acceptance, while
leaving the deterministic source-mapping evidence intact. The reviewers differed
on borderline qualifications/policy; their individual judgments are preserved.

### One controlled prompt correction and retest

The named hypothesis is that generic exhaustive atomic-assertion reading,
explicit rule/instance distinction, smallest complete direct selection and
selected-Evidence qualification closure reduce the observed defects. The prompt
adds these rules uniformly, without document/provider examples or a type route.
Existing durable-knowledge rules, representation, ref IDs, response schema and
admission remain unchanged. No emitted candidate is repaired, pruned or rewritten.

The original current-prompt baseline remains frozen. Both corrected-prompt arms
were replayed on the same three full documents: **6 logical calls / 6 attempts**
succeeded against online Sonnet, with **72,864 input + 9,172 output = 82,036
tokens**. The exact factory functions/helpers were read from the deployed app
for this replay. All 84 comparison candidates, including the 24 frozen baseline
candidates, pass schema/ref/role/span checks.

Two new blind contexts first read original sources, unchanged quality rules and
the earlier independently frozen source inventories. They receive newly
anonymous comparison packets and no previous candidate reviews, prompt changes
or treatment identities. Keeping the 34/39-claim denominators fixed prevents
retuning the expected inventory to fit an output. Questionable inventory entries
may be flagged separately but cannot silently disappear from the denominator.

### Second blind review and adjudication

Both fresh reviewers assessed all 84 candidates and the fixed inventories.
One reviewer treated any redundant Required ref as grounds to reject a candidate
"as emitted", whereas the other kept citation clutter separate. This made their
raw accepted counts incomparable (the first rejected the entire unchanged
baseline). Preserve those original judgments, but do not use that disagreement
to claim baseline knowledge has disappeared or to add an admission rejection.

For a consistent analysis, derive a **grounded durable claim** from each frozen
review's source-faithfulness, complete qualification, unchanged durability bar
and absence of missing selected support. Primary directness and redundant refs
remain separate measures. This is an evaluation calculation, not an output
filter, admission change or post-extraction repair.

| Second-round arm | Grounded durable claims, reviewer 1 / 2 | Non-direct Primary, reviewer 1 / 2 | Unnecessary Required parts, reviewer 1 / 2 |
| --- | ---: | ---: | ---: |
| Frozen current baseline (24 candidates) | 13 / 13 | 2 / 1 | 31 / 29 |
| Current representation + corrected generic prompt (25 candidates) | 11 / 13 | 2 / 1 | 2 / 2 |
| Readable representation + corrected generic prompt (35 candidates) | 15 / 16 | 0 / 0 | 1 / 1 |

Both reviewers found better direct Primary selection and less citation clutter.
However, the readable arm still has 9/8 incomplete-qualification judgments and
6/5 source-faithfulness failures. Under each review's fixed inventory and the
common grounded-claim calculation, **4 / 3 baseline-covered expected claims no
longer have complete covered support in the readable arm**. More new grounded
claims cannot cancel those specific losses. The private adjudication packet
records every lost claim ID, gained claim ID and supporting candidate mapping.
Reviewer uncertainty and different policy/qualification judgments remain visible;
the result is not reduced to a single optimistic score.

**Disposition: no deployment acceptance.** The renderer-independent mapping
mechanism is feasible for the tested supported selections, and the corrected
selection prompt improves citation roles. Semantic coverage/qualification is
still below the design contract. A whole-document complete-catalog replay is
not evidence that the existing per-ReadingGroup runtime will preserve every
expected claim. The next implementation acceptance must exercise that actual
complete-reading boundary and the named missing-condition/support fixtures,
alongside native immutable history, resource/access and adapter parity. Further
blindly repeated prompt runs or a new admission rejection are not substitutes.

Across both online rounds, **15 logical calls / 15 provider attempts succeeded**,
using **172,318 input + 21,573 output = 193,891 reported tokens**. Every generation
input/output and independent review remains frozen. No failed semantic result
was dropped, and no current production Memory was created, retired or modified.

## Architectural correction from independent audit

The earlier draft incorrectly treated ADR 0041's Unit input as historical native
snapshot authority. It stores only current input and its objects are overwritten.
The corrected proposal uses the existing immutable Observation Revision's native
coordinate text and immutable citation-relevant fields; binary input requires
revision-pinned retained Artifacts. Current Unit input remains reprocess input.

Legacy normalized Evidence is preserved under its declared representation.
Unavailable native history cannot be reconstructed from current provider data.
Current whole-Support assessment can establish new current Evidence; it cannot
prove old native correspondence. This is a shared OSS design correction, not a
Cloud adapter workaround or a new snapshot/identity ledger.

Primary standards inspected for this audit include W3C Web Annotation quote and
position selectors, Canonical XML, CommonMark and Atlassian storage format.
Selectors/parser coordinates alone do not establish occurrence continuity;
canonical XML alone does not define application meaning. See ADR 0046's sources.

## Reproducibility and release boundary

Private retained inputs, frozen catalogs, mapping receipts, probe code/results,
generation inputs/outputs, independent inventories/reviews and the unblinding
manifest are kept in the local experiment packet. They must not be uploaded to
the public repository. Public conclusions preserve the cohort sizes, protocol,
failed hypotheses and limitations without publishing provider contents.

No production source sync, reprocess, lifecycle write, provider mutation or
Cloud Foundry deployment occurred. This documentation update does not implement
native snapshot retention, correspondence, prompts, resource resolution or
OSS/Cloud/proxy parity. Every ADR 0046 acceptance row remains part of the runtime
release contract; successful offline mapping cannot substitute for those checks.

Repository verification for this documentation update: changed relative links
and `git diff --check` pass; current Support-reading and Source-projection
contract tests pass (**28 tests**). Those existing runtime tests do not test the
proposed matcher or prove the new release contract.
