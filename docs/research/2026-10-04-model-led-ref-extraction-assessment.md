# Model-led reference extraction and revision assessment

2026-10-04. Architecture/cost assessment requested by the user. **Proposal, not
validated replacement design.** No Jev or new Sonnet inference was executed for
this assessment. The original failed v19 experiment and current technical Support
correction remain separate evidence. This document does not authorize new batching,
provider limits, destructive lifecycle policy or production deployment.

## Finding

Deterministic source interpretation already caused unreadability/input loss;
the historical Confluence normalization/whole-group boundary and Jira omitted
native fields are reproduced before inference. Model-selected citations also fail
despite complete relevant input. Current controlled correspondence has positive
evidence but authentic consecutive complex-provider history is incomplete. These
facts do not establish static mapping as the main end-to-end failure cause.

The implementation has accumulated native interpretation, precise citation
granularity, render-independent identity, historical contracts and lifecycle
integrity in one proposed upgrade. Technical convergence alone cannot select
that architecture. A simpler model-led evidence-selection contract is a legitimate
alternative; neither generic model ability nor cheap classification proves it.

## Alternatives

| Approach | Ownership | Main benefit | Named limitation |
| --- | --- | --- | --- |
| Current declared catalog and exact correspondence | Adapter/compiler creates ref candidates; LLM chooses roles/claims; code proves identity | Cheap no-change reuse, exact source binding | Parser/schema and granularity maintenance; candidate input may exclude useful material |
| Generative extraction plus model semantic revision judgments | LLM proposes claims/quoted passages; classifier judges candidate support in new snapshot | Flexible evidence boundaries, fewer deep format-specific comparison rules | Still needs readable authenticated input, source locating and candidate discovery; model errors/cost remain |
| Lightweight source binding plus model-led semantics | Adapter owns snapshot/rendering; LLM chooses quotes; code validates source occurrence; exact identity fast path; classifier assesses semantic support | Keeps cheap literal work while reducing compiler semantic responsibilities | Not yet validated; scope/context discovery must not miss conditions outside selected refs |

The recommended **evaluation candidate**, not accepted implementation, is the
third approach. Keep existing Primary/Required roles. Let the generative model
choose evidence scope instead of requiring every useful citation to be a
compiler-predeclared semantic fragment. Program-owned anchors copy real source
passages rather than model paraphrases. If identical quotes have multiple
occurrences, use supplied snapshot/block identity and context rather than guessing.
This is a proposal to simplify authority, not another admission repair stage.

Revision semantics should distinguish source identity from support validity:
exact unchanged source may cheaply retain a located reference, while changed or
reworded source requires judging the fixed claim against current evidence/context.
A semantic correspondence creates authenticated current Evidence and a new
Support through the existing lifecycle; it must not relabel it byte-identical.
Assess against the original claim/current snapshot, rather than chaining previous
classifier guesses as if they were authoritative source facts. Conditions outside
the selected quote remain part of whole-Support validity. The classifier input
selection is therefore an explicit coverage responsibility, not a solved problem.

Provider grammar, collection and rendering stay in owning adapters. Models cannot
recover external macro values absent from the supplied snapshot. A provider-rendered
view or model-assisted interpretation must itself be retained/authenticated before
it supplies citable text; generated readable paraphrases alone are not quotations.
Jev text-only input does not address the deferred image-citation feature.

## Current primary-source evidence

[TypeSafe Models](https://docs.typesafe.ai/models.md) reports Jev 1.13.0 at
$0.042 per million input tokens, output free; 64k total request tokens and 32k
for state plus the longest question. It consumes state once per request and
evaluates questions independently. It accepts text, not images or free-form
generation. [Pre-parsed value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md)
uses code to find candidates, the classifier to select, and code to copy the
source value; Choice has at most 255 options. An LLM may propose candidates, but
Jev cannot choose an omitted one.

[Citation checking](https://docs.typesafe.ai/cookbooks/citation_check.md) locates
quotes in code before semantic support classification. Its small RFC demonstration
is not validation on MemForge documents. [Jev jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
explicitly records indirection, date/counting, large irrelevant state, option
order and generation limitations. [Confidence](https://docs.typesafe.ai/confidence.md)
does not establish our domain error rate. Evaluate thresholds on labelled MemForge
data, not a universal confidence number.

[Claude citations](https://platform.claude.com/docs/en/build-with-claude/citations.md)
is a useful comparison: models choose passages, while the API extracts quoted
text and valid document pointers. It still uses sentence/custom-block granularity.
Native citations are incompatible with strict structured-output format in that
API. This feature is **not verified on our SAP AI Core transport**, nor suitable
as the only provider-neutral contract without adaptation.

## Cost and execution

Actual frozen v19 transport telemetry, not estimated document tokenization:

| Source | Input tokens | Output tokens | Sonnet 4.6 direct-API arithmetic |
| --- | ---: | ---: | ---: |
| Confluence | 16,399 | 8,334 | $0.174207 |
| Jira | 16,831 | 656 | $0.060333 |

Arithmetic uses official [pricing](https://platform.claude.com/docs/en/about-claude/pricing.md)
of $3/M input and $15/M output. It is **not SAP AI Core billing** and does not
include old-ref context, generated quote output, Support work, classifier calls,
retries or other pipeline operations. Ten thousand Confluence-like full extraction
calls would be approximately $1,742 under those assumptions. A hypothetical
100k-input/8,334-output call is $0.42501. Free-quote output may cost more than ref IDs.

Jev arithmetic is cheap: 64 separate 1k-token classification requests cost
approximately $0.002688; 64 repeated 16,399-token inputs cost $0.044080512.
These are illustrative billed-input scenarios, not measured Jev token counts or
performance. Multiple independent questions can share one state and avoid those
64 repetitions when the request fits both budgets. Do not assume old/new large
documents fit Jev: two roughly 16k-token states plus questions approach or exceed
its 32k state constraint, and tokenizers differ.

The user reports variable workspace size with potentially several hundred
documents and a high upper bound; update frequency and maximum document length
remain unspecified. Do not turn that example into a product capacity limit.
For 300 documents at the measured Confluence-like extraction size, an initial
full import is $52.26; 10% updated daily over 30 days is $156.79/month; every
document updated daily is $1,567.86/month; every document updated five times daily
is $7,839.32/month. These are explicit update scenarios, not observed usage or
all-in prices. At 100k input and 8,334 output tokens, the every-document-daily
scenario is $3,825.09/month. Cost evaluation must track bytes/tokens processed,
updates and full/partial semantic reads, not just stored document count.

It is not necessary to resend the full document per ref. One extraction request
may cover a document; one classification request may cover several independent
judgments; changed passages may supply bounded semantic work when their governing
context is included. If the input exceeds capacity, splitting is a design choice
with cross-section-condition and execution-contract consequences, not a silent
workaround. The requested large-source benchmark must establish these costs.

[Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md)
reuses an identical prefix with 5-minute/one-hour TTLs; it does not guarantee full
cross-revision reuse after edits. Direct-API Batch pricing is 50% cheaper but
asynchronous and is distinct from splitting one document into multiple requests.
Neither caching nor Batch availability is established for our SAP AI Core path.

## Decision evidence required

Before choosing a replacement, compare the three ownership contracts on the
same authentic documents/consecutive revisions, a held-out family and the
approved source-first blind criteria. Record source-to-model completeness,
claim/Primary correctness, useful coverage, distinct Required precision, quote
locatability, false semantic reuse, unnecessary reassessment, input/output tokens,
request count and latency. Include moved/reworded duplicates and outside-ref scope
changes. Exact identity correctness and probabilistic semantic support are separate
metrics. Jev self-confidence is not a blind reviewer or a source completeness oracle.

This is a falsifiable architecture comparison rather than a new prompt iteration.
The current semantic design remains unaccepted. No replacement, cost ceiling,
classifier threshold or batching strategy has been approved or validated here.

Public-document snapshots/hashes and cost arithmetic are retained privately in
`/Users/i551096/Downloads/MemForge-Evidence-Validation-2026-10-02/private/model-mapping-assessment-20261004`.
