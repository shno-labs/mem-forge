# Structure-preserving parsers, Jev judgments, and repeated-context caching

Research date: 2026-09-21. This note uses project source plus first-party
documentation and upstream source repositories. It is design evidence only: no
runtime code, dependency, provider configuration, or existing design document
was changed.

**Superseded where it conflicts with [ADR 0036](../adr/0036-separate-semantic-work-from-inference-executors.md)
and [Semantic judgment execution](../design/semantic-judgment-execution.md).**
The adopted design differs in these points: Support Assessment is Structured-LLM
`GenerationWork`, not a Jev judgment; same-Unit Relation is sparse Structured-LLM
discovery; runtime probabilities are diagnostic only and no confidence threshold
selects a backend or result; one configured backend serves each task, with no
automatic policy; DestructiveValidation runs no semantic scan; no warm-up
inference is sent. The adopted names are `RepresentationCompiler`,
`ContextBundle`, `GenerationExecutor` and `JudgmentExecutor` in place of
`RepresentationIndex`, `RevisionJudgmentContext`, `GenerativeClaimEngine` and
`JudgmentEngine`.

## Recommendation

Keep `ReadingGroup` as one source-neutral, operation-scoped abstraction owned by
the revision-context planner. Put format-specific parsing behind a small
`RepresentationIndex`/adapter contract that emits exact raw ranges, structural
relationships, selectable Fragments, and contextual groups. Parser tokens and
provider-specific position types must not escape that boundary.

For the formats currently in scope:

* retain `markdown-it-py` for Markdown structure and GFM-like tables, lists and
  inline interpretation; its source map is line-based, so one encapsulated
  coordinate adapter must continue to turn block line maps into exact ranges in
  the immutable Python string;
* retain an encapsulated exact-offset HTML event scanner for authoritative raw
  ranges; an HTML5 DOM parser can be used separately for presentation or
  conformance checks, but no reviewed Python DOM library provides both browser
  repair semantics and exact raw start/end ranges;
* retain the encapsulated canonical-JSON scanner because MemForge needs duplicate
  rejection, RFC 6901 pointer identity, exact field ranges, and a decoded-string
  to raw-source boundary map. The reviewed packages supply only subsets of that
  contract;
* do not replace an authority parser with the current Tree-sitter Markdown
  grammar. It has exact byte ranges, but its own maintainers say it has many
  inaccuracies and is not recommended where correctness matters.

Treat a general LLM and Jev as two implementations of a shared *judgment input*
contract only where the output is a bounded judgment. Claim generation remains
a generative capability. Jev is a strong optional backend for closed-set support,
relation, verification, routing, and candidate-selection work, subject to
measured domain accuracy and its option/context limits.

For repeated LLM calls, arrange the provider prompt as a deterministic stable
prefix followed by work-specific suffixes. Use provider prompt-cache controls
and record observed cache-read/write usage. Do not call this a portable KV-cache
contract: Anthropic documents exact-prefix prompt caching; TypeSafe currently
documents neither a cross-request prefix cache nor cache-hit fields.

## The coordinate contract comes before the parser

Current text anchors are half-open indices into `revision.content` and are later
used directly as `revision.content[start:end]`. The compiler hashes the UTF-8
encoding of that exact Python slice; it does not store UTF-8 byte offsets. See
[`_materialize_fragment`](../../src/memforge/pipeline/evidence_fragments.py) and
the exact slice check in the storage path. This distinction matters because one
Unicode code point can occupy several UTF-8 bytes, while some decoded JSON
characters can occupy several raw escape characters.

The adapter contract should therefore make these invariants explicit:

1. The authority coordinate space is a half-open range of Python `str` indices
   into the immutable stored revision.
2. Parsing may consume UTF-8 bytes, lines/columns, decoded strings, or a repaired
   DOM, but the adapter must map every result back to that authority space before
   emitting it.
3. Line-ending conversion, Unicode normalization, entity decoding, tag removal,
   whitespace folding, and JSON escape decoding produce presentation views. They
   must not replace the raw source before anchors are assigned.
4. A returned range is accepted only if slicing the immutable source and hashing
   it reproduces the Fragment descriptor. Ambiguous or unrepresentable mappings
   fail closed.

CommonMark itself defines characters as Unicode code points rather than bytes
and recognizes LF, CR, and CRLF line endings, so silently normalizing line
endings before range construction would change the coordinate system
([CommonMark characters and lines](https://spec.commonmark.org/0.31.2/#characters-and-lines)).
Tree-sitter, by contrast, exposes node `start_byte`/`end_byte` and documents the
node range explicitly in bytes
([py-tree-sitter `Node`](https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.Node.html)).
That makes an explicit conversion table mandatory if a Tree-sitter grammar is
ever used behind the adapter.

## Parser findings

| Format/library | Useful capability | Position contract | Material limitation | Recommendation |
| --- | --- | --- | --- | --- |
| Markdown: `markdown-it-py` | CommonMark parser, GFM-like preset, nested block tokens, tables, task lists through presets/plugins | token `map` is exactly `[line_begin, line_end]` | no character/byte range for inline children; exact cell/span offsets still belong to the adapter | Reuse as the primary structural parser |
| Markdown: Tree-sitter Markdown | recursive sections/lists and GFM pipe-table extension; Tree-sitter nodes have exact byte ranges | UTF-8/UTF-16 byte offsets and points | upstream explicitly reports inaccuracies and says not to use it where correctness matters; split block/inline parser adds integration complexity | Do not use for authoritative Evidence; possible differential-test oracle only |
| Markdown preprocessing: Pandoc `sourcepos` | can attach source-position attributes while reading CommonMark or Djot | output `data-pos` attributes | extension is limited to those readers and produces a transformed AST/document, not a guarantee that every output node is one exact original raw slice | Do not put on the authority path |
| HTML: Beautiful Soup + `html5lib` | browser-like error recovery and convenient DOM traversal | `sourceline` and `sourcepos` for start tags with parser-dependent meaning | no end range; repaired/synthesized/reparented DOM nodes need not correspond one-to-one with raw substrings | Optional semantic/presentation view, not anchor authority |
| HTML: `lxml` | mature fast tree/XPath API | original `sourceline` only | no exact start/end range; HTML parser behavior is not the full HTML5 tree-building contract | Optional query/presentation view |
| HTML: `selectolax`/Lexbor | fast HTML5 tree and CSS selectors | reviewed public node API exposes tree/text/raw text, not original node start/end offsets | serialization/text extraction can differ from the original source | Not sufficient for Evidence anchors |
| HTML: Tree-sitter HTML | recursive lexical elements, script/style raw text, exact byte ranges | byte ranges | lexical grammar is not the WHATWG browser tree builder; malformed markup and implied elements require a product policy | Evaluate only if the product chooses lexical, rather than browser-DOM, structure and validates a corpus |
| Canonical JSON: Python `json` | authoritative standard-library validation/decoding; `raw_decode` returns the end of one decoded top-level value | one top-level end index; decode errors include positions | no per-field ranges or decoded-string-to-raw map; duplicate names are accepted with the last value by default | Keep as validation/reference behavior, not the range index |
| Canonical JSON: `json-source-map` | maps JSON Pointers to key/value start/end line, column and Python character positions | Python string character positions | small focused project; reviewed source validates through `json.loads`, constructs pointers from raw key text without RFC 6901 escaping, and returns a dict that cannot preserve duplicate-key identity; no decoded-string boundary map | Do not adopt as the canonical Evidence parser |
| Canonical JSON: Tree-sitter JSON | exact lexical byte ranges and recursive object/array nodes | byte ranges | upstream grammar accepts comments, multiple top-level values, and a decimal point without following digits, so it is not strict canonical-JSON validation; no decoded-string boundary map | Not a replacement for the canonical scanner |

`markdown-it-py` documents both its `gfm-like`/`gfm-like2` presets and plugin
system in its [official usage guide](https://markdown-it-py.readthedocs.io/en/latest/using.html).
Its public token contract defines the source map as `[line_begin, line_end]`, not
as character offsets
([`Token.map`](https://markdown-it-py.readthedocs.io/en/latest/api/markdown_it.token.html#markdown_it.token.Token.map)).
This is sufficient for whole block slices when paired with one line-start index;
it is not proof of exact positions for emphasis, links, an individual table cell,
or an entity-decoded inline string.

The Tree-sitter Markdown repository enables GFM, task lists, strikethrough and
pipe tables by default, but also says that restrictions in the grammar cause
"lots of inaccuracies" and that it is not recommended where correctness is
important. Its standalone integration requires a block parse followed by an
inline parse over included ranges
([upstream README](https://github.com/tree-sitter-grammars/tree-sitter-markdown#readme)).
That makes the attractive byte ranges insufficient to justify replacing the
existing parser. Pandoc's `sourcepos` extension is likewise documented only for
the CommonMark and Djot readers
([Pandoc manual](https://pandoc.org/MANUAL.html#extension-sourcepos)).

For HTML, Beautiful Soup documents that `html.parser` and `html5lib` expose start
locations but disagree on whether `sourcepos` points to the first or final
character of an opening tag. The same page shows that `html5lib` synthesizes and
reparents elements while repairing invalid HTML
([Beautiful Soup line numbers and parser differences](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#line-numbers)).
`html5lib` describes its goal as conforming to the WHATWG algorithm used by
browsers ([upstream README](https://github.com/html5lib/html5lib-python#readme));
that repaired semantic tree is useful, but a synthesized node has no exact raw
range. `lxml` exposes only an original source line
([`_Element.sourceline`](https://lxml.de/api/lxml.etree._Element-class.html#sourceline)).

Python's `HTMLParser` is a reasonable substrate for an encapsulated raw scanner:
it reports current line/offset, exposes the raw latest opening tag, and has
separate start/end/data/entity callbacks. Its docs also warn that it does not
check matching end tags or emit implicit closes
([`html.parser`](https://docs.python.org/3/library/html.parser.html)). That is why
the scanner must own stack validation, absolute offset conversion, raw entity
boundaries, void elements, and an explicit malformed-input result instead of
exposing `HTMLParser` directly. The current `_OffsetHTMLParser` already follows
this general shape and should be deepened behind the representation adapter,
rather than duplicated between Fragment compilation and ReadingGroup planning.

`json-source-map` does provide character ranges and is worth keeping as an
independent test oracle for simple documents. Its [public contract](https://github.com/open-alchemy/json-source-map#readme)
defines line, column and character positions. Its [scanner source](https://github.com/open-alchemy/json-source-map/blob/main/json_source_map/handle.py),
however, interpolates decoded-looking raw key contents directly into slash paths;
it does not implement the `~0`/`~1` escaping that RFC 6901 requires, and its
top-level `dict(...)` representation cannot retain two identical pointers. The
stdlib also documents that duplicate object names are accepted and only the last
value is retained unless the caller intervenes
([Python `json` compliance notes](https://docs.python.org/3/library/json.html#standard-compliance-and-interoperability)).
Those properties conflict with canonical-record identity. The upstream
Tree-sitter JSON [grammar source](https://github.com/tree-sitter/tree-sitter-json/blob/master/grammar.js)
shows its comments, repeated root values and optional digits after a decimal point
directly.

The right amount of custom code is therefore a thin, tested ownership layer, not
a new general-purpose parser:

```text
ImmutableRevisionText
  -> RepresentationAdapter (Markdown | HTML | CanonicalRecord | PlainText)
       -> RepresentationIndex
            raw structural nodes/ranges
            selectable Fragment descriptors
            contextual parent/sibling relationships
            decoded-presentation <-> raw-coordinate maps where required
  -> ReadingGroupBuilder
       -> scope + container + before + target + after
          + authority/selectability + exact Fragment refs
```

The index is operation-local and shared by Fragment compilation, changed-range
planning and ReadingGroup construction. It is not a new database entity or
lifecycle state. Adapter conformance should cover Unicode outside ASCII, CRLF,
tabs, escaped JSON surrogate pairs, entity references, malformed HTML, nested
lists, tight/loose lists, block quotes, GFM tables with empty cells, and embedded
HTML. The acceptance invariant is always the exact original slice, not merely an
equivalent rendered string.

## What Jev is, and which model rounds are judgments

TypeSafe's current HTTP contract is one
`POST /v1/systemone` request containing `{state, model, questions}`. `state` is a
string, object, or array of text values; `questions` is a caller-named map. Every
question sees the same state and is evaluated independently. The response is
`{model, answers, usage}`, keyed by the caller's question IDs
([API reference](https://docs.typesafe.ai/api), [state contract](https://docs.typesafe.ai/concepts/state)).

Its three primitives are:

| Primitive | Meaning | Typed result |
| --- | --- | --- |
| `Noul` | whether one condition holds | `noul`, the probability of yes from 0 to 1; no separate confidence |
| `Choice` | one option from a closed set | winning `choice`, full option `probabilities`, and distribution-derived `confidence` |
| `Score` | degree on 2–10 ordered rubric levels | probability-weighted numeric `score`, `legend`, full level `probabilities`, and `confidence` |

A Choice accepts at most 255 options. Current `jev-1.13.0` documentation lists a
64k-token total request bound and a separate 32k-token bound on state plus the
longest question; limits and aliases may change, and CJK is accepted with lower
reported accuracy than English. Pin a version once thresholds are calibrated
([model reference](https://docs.typesafe.ai/models)). TypeSafe also warns that
irrelevant state degrades accuracy and that Jev is not a reliable counter or
calculator
([Jev jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13)).

Calling Jev "a classifier" is directionally useful but incomplete. It is a
closed-set semantic judgment engine: classification, Boolean judgment, graded
scoring and selection among values that application code already supplied. It
does not generate an arbitrary claim, explanation, ID, or Evidence span absent
from its choices. Typed output guarantees the interface, not truth; TypeSafe
explicitly requires domain validation and threshold calibration
([TypeSafe confidence guidance](https://docs.typesafe.ai/confidence)).

Applied to the target MemForge responsibilities:

| Responsibility | Judgment vs generation | Jev fit |
| --- | --- | --- |
| Claim Extraction | creates new claim text/type and then selects exact Evidence | Keep a generative LLM unless code first creates a complete candidate set; Jev can classify type or select Evidence after generation |
| Support Assessment | fixed claim; decide support/opposition/uncertainty and select from supplied current refs | Strong candidate. Compose Noul/Choice judgments and fail closed below calibrated thresholds; the complete Evidence Unit still needs application validation |
| Claim Reconciliation | determine EQUIVALENT/REFINES/CONTRADICTS for supplied claims | Strong for bounded candidate pairs. Sparse discovery over an unbounded catalog is not a single Jev classification; retrieve/partition candidates in code or retain the LLM path |
| Destructive Validation | fixed claim and supplied current projection; decide whether current support remains | Candidate only with conservative thresholds, complete manifests and unchanged deterministic lifecycle guards |
| Selector correction/routing | choose among a known legal set or route work | Natural Choice/Noul use case; deterministic validation remains final authority |

Multiple independent judgments over one state should be sent as one TypeSafe
request. They execute independently and cannot consume one another's answers.
The official parallel-question example reports a large cost/latency gain for its
13-question workload, but that is an example rather than an SLA
([parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions),
[fan-out pattern](https://docs.typesafe.ai/patterns/fan-out)). A second call is
needed when an earlier result changes the state, fetches Evidence, or defines the
next legal options.

The Python `AsyncTypeSafeClient` only awaits the same System One operation; it is
not a server-side batch job
([async client](https://docs.typesafe.ai/sdk/python/api/clients/async)). The live
OpenAPI currently exposes only `/v1/models` and `/v1/systemone`
([OpenAPI](https://api.typesafe.ai/openapi.json)). No offline batch/job endpoint,
cross-request prefix/KV cache, cache key, TTL, or cache hit/write usage field is
documented. A local `JsonCache` used by examples must not be described as model
prompt caching.

## Shared context contract, separate provider compilers

One universal "model call" interface would hide capabilities that determine
correctness. Use a shared immutable context envelope and capability-specific
ports instead:

```text
RevisionJudgmentContext
  identity:
    source/revision/profile/compiler/plan digests
  stable_state:
    policy + response contract + Fragment/claim catalogs
  reading_state:
    ordered ReadingGroups + authority and selectability
  work:
    stable work IDs + fixed claims/candidate pairs + expected slots
  limits:
    completeness + capacity + fail-closed policy

GenerativeClaimEngine.generate(context) -> GeneratedClaimCandidates
JudgmentEngine.judge(context, typed_questions) -> TypedJudgments
```

The LLM compiler serializes a stable instruction/schema/catalog prefix and a
work-specific suffix, then validates structured output locally. The Jev compiler
serializes named state and many independent typed questions, retaining raw
probabilities for application policy. A backend advertises capabilities such as
generation, closed-set choice, per-choice limit, shared-state fan-out, structured
output, and observable prompt-cache metrics. Orchestration chooses only a backend
that can satisfy the requested capability; it does not emulate missing generation
by silently narrowing work.

Stable semantic IDs and deterministic serialization are part of context identity.
The persisted/recoverable result binds to the source revision, Fragment catalog,
ReadingGroup plan, question/schema contract, model version and policy version.
Probabilities and cache hits are execution evidence, never lifecycle authority.

## Anthropic prompt caching for repeated batch context

Anthropic documents prompt caching as an exact reusable prefix. The cache order
is `tools`, then `system`, then `messages`, and the cache covers everything before
and including the selected breakpoint. Put invariant instructions, stable tool or
response definitions, the revision-pinned source/catalog, and shared policy first;
put per-work claims, ReadingGroups and requested slots after the last stable
breakpoint. Any changed content before that point produces a different cumulative
prefix. Tool-definition changes invalidate the following system/message cache
([Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)).

This is a concrete ordering opportunity for MemForge batch calls:

```text
[stable model contract]
[stable schema/tools]
[revision-pinned source or shared Fragment catalog]
[shared claim/catalog metadata]
--- cache breakpoint ---
[work-specific ReadingGroups / fixed claims / requested slots]
```

The order must be derived from actual reuse. If the same source snapshot is used
across many work requests, it belongs before the breakpoint. If each request has
a different source, only the earlier contract/schema may be reusable. A dynamic
schema or tool definition can move or invalidate the stable prefix; use one stable
wire schema when feasible and enforce request-specific ref membership in code.
Always verify behavior through provider usage fields rather than assuming the
transport's serialization.

Current documented mechanics relevant to orchestration are:

* automatic top-level `cache_control` targets the last cacheable block; explicit
  block breakpoints allow precise placement;
* there are at most four breakpoints; a lookup searches backward up to 20 content
  blocks from each explicit breakpoint and only finds prefixes previously written
  at a breakpoint;
* the default ephemeral TTL is five minutes and refreshes on a hit; the optional
  one-hour TTL costs more, and longer-TTL content must precede shorter-TTL content;
* a new entry becomes available after the first response starts. Parallel followers
  that require a warm entry must wait for that event. `max_tokens: 0` can prewarm
  synchronous calls;
* model-specific minimum prefix sizes apply; below the minimum, cache creation is
  silently skipped. Inspect `cache_creation_input_tokens` and
  `cache_read_input_tokens` instead of inferring a hit;
* cached tokens still occupy the context window. Caching reduces input cost and
  time to first token; it does not increase capacity or reduce the model's semantic
  attention burden.

Anthropic Message Batches process requests asynchronously and in arbitrary order.
Prompt caching is supported and its discount stacks with the batch discount, but
hits inside a batch are explicitly best effort; the current guide reports typical
observed hit rates rather than a guarantee. Because a batch can outlive the
five-minute TTL, Anthropic recommends considering the one-hour duration. Batch
requests require `max_tokens >= 1`, so zero-token prewarming is not available
inside a batch; results must be correlated by `custom_id`
([Anthropic Message Batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing)).

LiteLLM documents pass-through of Anthropic-style
`cache_control: {"type": "ephemeral"}` and normalizes cached token usage, including
Anthropic cache-creation tokens
([LiteLLM prompt caching](https://docs.litellm.ai/docs/completion/prompt_caching)).
That is transport support, not a provider-neutral semantic guarantee. Anthropic's
current model-specific minimums and observed provider usage remain authoritative.

Cache behavior must never affect completeness, ordering, Evidence authority,
retry identity, or lifecycle decisions. Record cache write/read tokens, request
latency, model/version and stable-prefix digest so the optimization can be
evaluated. If the provider does not expose such fields, record cache behavior as
unknown rather than claiming a hit.

## Design consequences

1. `ReadingGroup` remains a first-class value object inside one deep
   revision-context module. Format adapters build it; orchestration consumes it.
2. Parser reuse is preferred where the upstream contract matches the need.
   Custom code is confined to raw-coordinate mapping, canonical validation and
   exact structure-to-context policy that no reviewed package supplies together.
3. LLM and Jev share revision-pinned context identities and typed work manifests,
   but they do not share a lowest-common-denominator request shape.
4. Provider choice is explicit per responsibility and capability. Users may
   select the general LLM path, the Jev judgment path where supported, or an
   automatic policy whose resolution is recorded.
5. Prompt ordering and batching are execution optimizations. Complete coverage,
   exact Evidence resolution, local schema/ref validation, stale guards, and
   fail-closed lifecycle behavior remain application-owned.
