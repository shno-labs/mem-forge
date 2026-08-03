# Fixed named slots in LLM structured outputs

Date: 2026-08-02

## Conclusion

`slot_00 ... slot_N` as individually named, nullable object properties is **not a generally recognized best practice** for repeated LLM output. The first-party OpenAI, Anthropic, and Gemini examples model homogeneous repeated records as an array. JSON Schema itself describes arrays as ordered collections and uses `items` for homogeneous entries.

The former MemForge shape was nevertheless a **reasonable specialized protocol**: it encoded a fixed-capacity answer sheet whose keys were owned by the caller, so the model did not emit datastore identity and every active input could be checked for coverage. Its weakness was that fixed capacity was represented by many `Decision | null` properties. Pydantic turned each one into a union, which directly conflicted with Claude's strict-schema complexity limit.

Therefore:

- Do not describe fixed nullable slots as an industry best practice.
- Do not reduce the 24/32 business batch sizes to 15 merely to satisfy Claude's 16-union limit; that is a provider-driven behavioral change.
- The simplest portable baseline is an ordered `decisions` array plus application validation of exact coverage. If reordering or omission must be detected explicitly, each item can carry a caller-owned batch-local `slot_id`; it must not carry a datastore ID.
- If Claude-native schema-level exact cardinality is a hard requirement, fixed required properties remain defensible, but the nullable fixed-capacity form is a poor fit for Claude strict output. Dynamically generating only the active, non-null slots is possible but adds schema/cache complexity and is not a common official pattern.

## What the pre-change schema did

Before the ordered-array change, the repository defined:

- `CandidateLedgerResponse`: 24 required properties, `slot_00` through `slot_23`, each `CandidateLedgerDecision | None`.
- `EntityBatchValidationResponse`: 32 required properties, `slot_00` through `slot_31`, each `EntityBatchValidationDecision | None`.
- Active slots must contain a decision; unused capacity is represented by `null`. Application code binds each slot back to the corresponding request-owned candidate or entity mention.

The generated Pydantic schemas contain:

| Response | Outer nullable-slot unions | Inner nullable-field unions | Total union parameters |
| --- | ---: | ---: | ---: |
| Candidate Ledger | 24 | 1 (`canonical_index`) | 25 |
| Entity Batch | 32 | 1 (`matched_id`) | 33 |

Pydantic documents that optional/nullable fields permit `null` in the generated schema and shows them as `anyOf: [T, null]`; it emits `list[T]` as one `array` with an `items` schema. See [Pydantic JSON Schema](https://pydantic.dev/docs/validation/latest/concepts/json_schema/).

## What primary sources recommend or demonstrate

### Repeated homogeneous results: arrays are the normal representation

The [JSON Schema array reference](https://json-schema.org/understanding-json-schema/reference/array) says arrays contain ordered elements and distinguishes:

- list validation: arbitrary-length homogeneous entries described by one `items` schema;
- tuple validation: positions with different schemas, represented by `prefixItems`.

It also defines `minItems` and `maxItems` for length. Thus an array does not inherently mean “uncheckable completeness”: where the provider supports both keywords, `minItems == maxItems == N` expresses exact cardinality. `prefixItems` by itself does not require all positions to be present.

First-party provider examples follow this model:

- The [OpenAI Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs) represents repeated `steps` as `list[Step]` / an array of objects. It recommends clear, intuitive key names and supports `minItems` and `maxItems` for non-fine-tuned models.
- The [Anthropic Structured Outputs guide](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) uses arrays such as `next_steps` for repeated values.
- The [Gemini Structured Outputs guide](https://ai.google.dev/gemini-api/docs/structured-output) uses arrays for ingredients, instructions, and scorers, and lists `items`, `prefixItems`, `minItems`, and `maxItems` as supported array keywords.

None of these official guides presents `slot_00 ... slot_N` nullable properties as the preferred representation of homogeneous batches.

### Completeness and identity are different guarantees

A strict schema can guarantee structure, required fields, and—where supported—array length. It cannot guarantee that the model placed the *semantically correct judgment* in the position associated with a particular input. The same limitation applies to named slots: a schema cannot tell whether the model wrote candidate B's judgment under `slot_00`.

The fixed-slot design does provide useful deterministic checks:

- every named active field can be required;
- extra fields can be forbidden;
- caller code, rather than the model, owns the mapping to datastore identity.

An ordered array preserves the last property without exposing identity:

```json
{
  "decisions": [
    {
      "action": "KEEP",
      "canonical_index": null,
      "reason": "Distinct candidate"
    }
  ]
}
```

Caller code binds `decisions[i]` to `inputs[i]` and validates `len(decisions) == len(inputs)`. JSON Schema explicitly defines arrays as ordered. If the protocol wants explicit omission/duplication detection independent of position, use a batch-local identifier:

```json
{
  "decisions": [
    {
      "slot_id": "s00",
      "action": "KEEP",
      "canonical_slot_id": null,
      "reason": "Distinct candidate"
    }
  ]
}
```

The application then validates that the returned `slot_id` set exactly equals the issued set, contains no duplicates, and that every cross-reference targets an allowed slot. This is an architectural synthesis from the identity requirement, not a provider-prescribed schema.

### Nullable unions are specifically expensive for Claude

Anthropic states that structured-output schemas are compiled into grammars. Its [schema complexity limits](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#schema-complexity-limits) cap, across all strict schemas in one request:

- optional parameters at 24;
- parameters using `anyOf` or a type array such as `["string", "null"]` at 16.

Anthropic explains that union parameters are especially expensive because they create exponential compilation cost. The documented simplification sequence is to reduce optional parameters, simplify nesting, and split requests when needed.

Those outer shapes exceeded that limit before considering their inner nullable field: Candidate Ledger produced 25 union parameters and Entity Batch 33. Changing 24/32 to 15 would merely make `15 outer + 1 inner = 16`; it would not make fixed nullable slots a better general model.

### Exact-length arrays are not equally portable

Provider support matters:

- JSON Schema defines `minItems` and `maxItems` generally.
- OpenAI currently supports both for standard Structured Outputs, while documenting extra restrictions for fine-tuned models. See [OpenAI supported schemas](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas).
- Gemini lists both as supported. See [Gemini JSON Schema support](https://ai.google.dev/gemini-api/docs/structured-output#json-schema-support).
- Anthropic's current supported-feature table limits array `minItems` to 0 or 1 and does not provide general exact-`N` array cardinality. Its SDKs can strip unsupported constraints, add them to descriptions, and validate the response against the original schema afterward. See [Anthropic JSON Schema limitations and SDK transformation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations).

Consequently, an exact-length array can be grammar-enforced on OpenAI/Gemini but must be application-validated on Claude. This was the strongest argument for the named-property protocol—but also the reason it should be described as a Claude/provider trade-off rather than a universal best practice.

## Adopted minimal design for MemForge

Use this contract unless measurements show that Claude post-validation causes unacceptable retries:

```python
class CandidateLedgerResponse(StructuredResponseModel):
    decisions: list[CandidateLedgerDecision]
```

Then retain deterministic boundary checks:

1. The returned decision count equals the active input count.
2. Array position, or a batch-local `slot_id`, maps to exactly one caller-owned input.
3. Candidate Ledger canonical references point only to visible, valid earlier candidates.
4. Entity `matched_id` values belong to the candidate set supplied for that input.
5. Invalid responses receive the existing bounded retry/fallback behavior.

For OpenAI/Gemini, exact `minItems`/`maxItems` may additionally be pushed into the wire schema. For Claude, use its supported simplified array schema and keep the same Pydantic/application checks. This preserves the 24/32 business batch sizes, caller-owned identity, and coverage invariant without creating 24/32 outer nullable unions.

### Native Anthropic transport through SAP orchestration

The ordered array removes the schema-complexity blocker but does not by itself
select native structured output. LiteLLM 1.86 reports no native response-schema
capability for `sap/anthropic--claude-4.6-sonnet`, so an automatic-only client
would still choose JSON text even when the deployed gateway supports Claude
structured output.

A bounded live probe against the Cloud Foundry-bound SAP AI Core environment on
2026-08-03 established the current transport behavior:

- a minimal schema succeeded through both SAP's documented `response_format`
  prompt field and Anthropic's current `output_config.format` model parameter;
- the raw Pydantic Candidate Ledger and Entity Batch schemas failed because
  they still contained unsupported generation constraints such as `minimum`,
  `maximum`, and `maxLength`;
- the same two schemas succeeded after the public
  `anthropic.transform_schema()` conversion, returning one schema-valid ordered
  decision in each probe.

Anthropic documents `output_config.format` as the current API shape and explains
that its SDK transformer removes unsupported wire constraints, adds
`additionalProperties: false`, and validates the result against the original
schema. See [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
SAP's orchestration API permits model-specific parameters through the model
configuration, while its response-formatting guide separately documents the
prompt-level `response_format` field. See [SAP response formatting](https://help.sap.com/docs/sap-ai-core/generative-ai/response-formatting).

The adopted seam is therefore one explicit transport choice at deployment
construction: `auto` keeps LiteLLM capability discovery for ordinary models;
`anthropic_output_config` sends the provider-transformed schema through
`output_config.format`. This does not add a lifecycle state or a second domain
schema. The original Pydantic model and application-level coverage checks remain
authoritative after the provider response.

If schema-level completeness on Claude is explicitly judged more important than portability, keep named slots—but generate only the active required non-null slots rather than padding a fixed maximum with nullable fields. That alternative should be adopted only with evidence because every active batch size changes the schema and may reduce grammar-cache reuse.

## Bottom line

The former design was **reasonable in intent but specialized in representation**. Fixed named slots protect caller-owned binding and make omissions structurally visible, but nullable padding is exactly the schema pattern Claude penalizes. Arrays are the official and JSON-Schema-native representation for homogeneous repeated decisions; application-level exact coverage validation is the least complex provider-neutral solution adopted here.
