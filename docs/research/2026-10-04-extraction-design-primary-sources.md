# Primary constraints for a complete grounded-extraction design

Bounded official-source research, 2026-10-04. No implementation changes, deployment, paid model call or source mutation. This is input to the design contract, not proof that MemForge already implements it or that any extraction experiment has passed. The cited standards do not require adopting their complete schemas or adding a new framework.

## 1. Keep source version, selector, comparison material and readable view distinct

[W3C Web Annotation Data Model, selectors](https://www.w3.org/TR/annotation-model/#selectors) separates the source resource from a selector identifying its segment. [States](https://www.w3.org/TR/annotation-model/#states) describe which temporal/format representation the annotation addresses; resources change over time and can have multiple representations. [Time State](https://www.w3.org/TR/annotation-model/#time-state) can record an appropriate timestamp and/or persistent copy, but does not itself guarantee that a historical copy exists.

For this design, the useful principle is small: persist the existing immutable source revision and exact selector; separately derive the readable view and format-versioned comparison value. A latest provider URL or timestamp is navigation/metadata, not recovered historical authority. A selected source hash proves byte identity under its declared coordinate space; a display hash proves the produced view's identity. Neither establishes that a claim is entailed, that a condition was preserved, or that two differently encoded passages have the same meaning.

No new annotation ledger is implied. Existing Source revision, Evidence anchor and adapter format contracts can carry this distinction. Future unchanged matching should use explicitly declared material and identity constraints, not presentation bytes or transient ref numbers. Readable transformation must remain format-owned: entity decoding in ordinary HTML is different from literal HTML characters inside code. The W3C text-quote normalization rules concern its annotation text representation; they are **not** a license to generically strip all markup from MemForge's authoritative native storage or literal code.

## 2. Quotes and offsets solve different problems; neither solves all correspondence

[Text Quote Selector](https://www.w3.org/TR/annotation-model/#text-quote-selector) uses `exact` plus immediately preceding `prefix` and following `suffix` to distinguish copies of the same text. The standard explicitly says that if multiple matching sequences remain, the selection should match **all** of them. Thus an exact quote, even with context, does not guarantee a unique occurrence. MemForge's need to reuse one historical Evidence occurrence is stricter: ambiguous repeated material cannot be assigned an arbitrary new occurrence. A source-attested stable child identity can disambiguate; similarity, position proximity or a model's confidence cannot manufacture that identity.

[Text Position Selector](https://www.w3.org/TR/annotation-model/#text-position-selector) uses an inclusive start/exclusive end and warns that position selectors are brittle under edits or dynamically transcluded content. The standard recommends State information for the appropriate representation. Its text selectors count **Unicode code points**, not programming-language code units, and distinguish logical from visual order. A browser's UTF-16 index, a byte offset and a Python Unicode index must not be silently mixed; format/coordinate declarations and decode-to-parent maps are necessary at the boundary.

Proportionate alternatives:

- **Pinned positions plus raw hash**: deterministic and auditable within an immutable revision; requires a separate correspondence rule after edits.
- **Quote plus context**: easier to propose from model output; requires deterministic resolution against the exact full authorized snapshot, duplicate handling, and preservation of authored scope. It does not replace revision/identity authority.
- **Source-attested node/message/comment ID plus declared material**: strong when the source actually supplies stable identity; unavailable for arbitrary anonymous repeated paragraphs. Do not invent IDs through fuzzy matching.

These mechanisms can be combined through existing adapter contracts. The acceptance requirement should name what counts as unchanged under a given format and what must be returned as ambiguous, rather than promise unambiguous mappings for indistinguishable duplicate occurrences.

## 3. Source revisions and conversation scope require real provider framing

Official provider contracts already checked in the bounded preceding review:

- [Jira DC REST API 9.12.2](https://docs.atlassian.com/software/jira/docs/api/REST/9.12.2/) supports comment update and delete operations. Comments are not universally append-only. Stable comment ID, body snapshot, `created`/`updated`, visibility and collection completeness are distinct facts. Current `renderedFields`/comment `renderedBody` HTML does not attest formatting of a missing historic old field value.
- [Graph `chatMessage`](https://learn.microsoft.com/en-us/graph/api/resources/chatmessage?view=graph-rest-1.0) states that IDs are unique within chat/channel/reply-to-message scope, not globally; `lastModifiedDateTime` also changes with reactions; `lastEditedDateTime` specifically records editing; deletion is represented separately. `replyToId` applies to channel messages, not chats.
- [List chat messages](https://learn.microsoft.com/en-us/graph/api/chat-list-messages?view=graph-rest-1.0) defaults to last-modified descending and also supports created-time descending. [List channel messages](https://learn.microsoft.com/en-us/graph/api/channel-list-messages?view=graph-rest-1.0) returns roots without replies and sorts by modification of the whole reply chain. [Reply collection](https://learn.microsoft.com/en-us/graph/api/chatmessage-list-replies?view=graph-rest-1.0) is separate.

Chronological reading is an application choice, not source-attested semantic parentage. It cannot alone resolve quoted replies, an ambiguous confirmation, or precedence between two statements. No universal chat quoted-reply serialization was established by these official pages. Preserve explicit provider framing where available and distinguish it from a reading-order heuristic. The adapter owns provider identity, timestamp meaning, literal/HTML/structured body grammar and framing; the shared pipeline consumes declared source-neutral facts.

## 4. Structured output and valid citation pointers do not prove semantic support

[Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) documents constrained-decoding guarantees for parseability, required fields and types. Those guarantees are about schema validity; they do not independently establish that a claim follows from the source, preserves negation/conditions/history, uses the right Primary, or selects relevant additional evidence. A span can be in range, a quote can occur exactly and JSON can be valid while the claim is inaccurate.

[Anthropic citations](https://docs.claude.com/en/docs/build-with-claude/citations) documents valid pointers to supplied documents and direct extraction of `cited_text`. It reports improved citation relevance in its own evaluations, not perfect entailment, unique cross-revision correspondence or complete additional-reference recall. Citations operate on supplied document chunks; the model/provider citation locator is not automatically a native Source revision selector. Exact mapping back to the stored authority still belongs to the application.

The official current constraints matter only if that provider feature is selected:

- Built-in citations support **text**, not image citations.
- Built-in citations and `output_config.format` JSON outputs are documented as incompatible (HTTP 400). A custom JSON quote/span/ref field is not the built-in citation feature, so this incompatibility must not be misapplied to it.
- The configured cloud model/transport must actually support the selected mechanism. A capability in direct-provider documentation is not proof of parity in every provider gateway or user-configured LLM.

Alternatives relevant to this plan: retain provider-neutral structured selection resolved deterministically by the application; or consider built-in citation pointers as an optional provider-specific input/comparison experiment. Making native citations the mandatory shared lifecycle interface would trade portability and strict JSON integration for provider-managed chunk pointers, without removing semantic validation needs. No additional repair/self-audit stage is implied by either alternative.

## 5. Keep image claims within supplied evidence and the agreed scope

[Anthropic vision](https://platform.claude.com/docs/en/build-with-claude/vision) documents approximate spatial/localization output, potentially inaccurate counting and mistakes on low-quality/rotated/small images. Supplying genuine bytes and meeting transport limits therefore does not guarantee correct interpretation. A caption, URL or attachment identity proves neither unseen pixels nor a diagram's factual relationships.

This is a design boundary, not a request to add the deferred image-capability feature. An ordinary citation can preserve an immutable artifact identity/resource without requiring every consuming LLM to be multimodal. Any claim of interpreted image content needs actual supplied image evidence and separately scoped acceptance; text-only and image acceptance must not be conflated.

## Implication for the design-first validation contract

Define and validate these separately: authoritative snapshot/coverage and access; source-owned faithful rendering/literals; deterministic selector resolution and ambiguity; future unchanged correspondence under a declared format; whole-claim scope/support; and citation readability/Primary relevance/best-effort additional references. Correct selectors are necessary but insufficient for correct claims. Schema validity, exact quote occurrence, pointer validity and a green parser cannot substitute for complete real-document semantic evaluation.

Reasonable omission of an additional related reference can be accepted without weakening the correctness of the claim or the integrity/access boundary of its persisted supporting set. A design should not claim 100% optional citation recall or perfect semantic extraction merely because transport and deterministic mapping are reliable. The named adversarial controls should include duplicate passages, edited/deleted comments, non-text-changing modification timestamps, missing quote context, literal markup, qualifier/history changes and renderer-only display changes. This establishes risks to validate; it does not authorize implementation, extra canaries or a larger framework.

## Capture provenance

Fresh successful reads on 2026-10-04:

- Web Annotation Model: 284,185 bytes; SHA-256 `a7513e022f56c0a6f4e99ac11aec03f3451d1ff1ce14054780b3ccfb38fa7980`.
- [W3C Selectors and States](https://www.w3.org/TR/selectors-states/), supplementary reading (use the Web Annotation Recommendation above as primary): 180,359 bytes; SHA-256 `c6e316205f4e2d54cbab5fb809bdf070cab631f094c000611adc50f06bc27b96`.
- Anthropic citations: 1,266,521 bytes; SHA-256 `c25106a08380696d7fa6c5539facc0ccda6a472fad2d0572b580e68e5e9df9e5`.
- Anthropic vision: 893,305 bytes; SHA-256 `6e917c0cb5efcae3bbe24e45786be3a12baf53f2af21423828390c3b0bab8435`.
- Jira REST 9.12.2: 1,230,298 bytes; SHA-256 `4a04cfac3a91d25ccd0197c6a1afdfe11ba7f48d9a0e68ea8fba7c4e22e261fa`.
  The Change Item schema separately declares `field`, `from`, `fromString`,
  `to` and `toString`; comment expansion explicitly documents `renderedBody`
  as HTML. Historical values therefore retain their event/field role and do
  not borrow current-body rendering. These provider semantics belong in the
  Jira adapter, not shared compiler field-name heuristics.

The same-day official structured-output/Jira/Graph captures and exact links are recorded in `/tmp/memforge-claude-design-contract-check.md`; no redundant download was needed. Repository research `docs/research/2026-10-03-native-source-format-contracts.md` separately records the complete native-body hashes and 300-character code conservation evidence. Those parser/source facts are not paid-model or blind-review acceptance evidence.
