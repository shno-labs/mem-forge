# Sparse claim catalog contract

Canonical decision: [ADR 0034](../adr/0034-unify-incremental-support-and-claim-assessment.md#sparse-claim-discovery-over-complete-input-catalogs). This is the single-round relationship-discovery design; no new default destructive-action recheck is added.

The request contains `new_claims`, `existing_claims`, and `evidence_catalog`. Short IDs are application-issued and scoped to the immutable request. Candidate evidence references preserve Primary/Required roles and observation/revision identity. Existing claims carry the completed current Support audit, not an inferred connection to another claim's evidence. Evidence records are deduplicated only by exact canonical content and provenance. Current full Support audit coverage remains independent of sparse relationship output.

```json
{
  "new_claims": [{"id":"C0","text":"Codes expire after ten minutes.","type":"fact","valid_from":null,"valid_until":null,"evidence_refs":["E0"]}],
  "existing_claims": [{"id":"M0","text":"Codes expire after five minutes.","type":"fact","valid_from":null,"valid_until":null,"current_support":{"supported":false,"reason":"Current source changes the expiry."}}],
  "evidence_catalog": {"E0":{"role":"primary","excerpt":"Codes expire after ten minutes.","observation_id":"obs-current","revision_id":"rev-current","kind":"text"}}
}
```

The example excerpts stand in for authoritative current Evidence; the real executor preserves exact supplied records. No historical Support or missing audit reference is manufactured from this example shape.

```json
{
  "results": [{
    "candidate_id":"C0",
    "evidence_status":"entailed",
    "relations":[{
      "existing_id":"M0",
      "relation":"contradicts",
      "reason":"The same code flow has incompatible expiry durations.",
      "contradiction":{"same_subject_and_scope":true,"incompatible_assertions":"ten minutes versus five minutes"},
      "revision_assessment":null
    }],
    "uncertain_existing_ids":[]
  }]
}
```

A candidate with no discovered edges still returns its row with `relations: []`. Equivalence must be reported because it consumes a duplicate candidate. Directional refinement uses `refines_challenger_to_candidate` or `refines_candidate_to_challenger`; only the former has the existing four-condition revision proof. Missing/inadequate proof is local unresolved assessment, not an invented unrelated edge. Explicit uncertainty lists incumbent IDs and preserves the connected component. Evidence-insufficient candidates cannot be admitted through an empty result; uncertainty found in one capacity partition applies across that candidate's returned relationships.

The reducer consumes only actual returned edges. Unreferenced supported incumbents remain; unsupported incumbents still go through existing Support/lifecycle rules. Omitted equivalents can produce duplicates; an omitted competing replacement can make a returned proposal appear unique. These are accepted discovery false negatives and are tested separately from proof/authority/stale/transport failures. The existing conditional comparison for multiple discovered refiners is retained; no default second LLM pass is added.

Each request must return all its candidate rows exactly once and only known incumbent references, without duplicate or contradictory edge entries. Valid-looking JSON with truncation/refusal completion metadata fails. Capacity subdivision uses the existing executor to partition complete input rectangles only when needed; no top-k, pair-count packing or business-state splitting is introduced. Validated sparse results retain exact input/model/schema identities in DerivationWork, and SQLite/HANA require completed work at the existing atomic commit gate.

## Verification evidence

- Dedicated fixtures exercise 8 candidates x 183 incumbents in one fitting request with eight empty candidate rows, shared evidence once, no generated unrelated pairs, and no pair matrix materialized in the reducer.
- Capacity-limited fixture partitions the same input without dropping catalog IDs. A final subrequest failure, SQLite close/reopen and retry reuse every completed subrequest; only the unfinished request calls the provider. Different operation identity recomputes work. HANA runs the corresponding durable result-reuse and final commit-gate checks.
- Fixtures cover all relation directions, required proofs, missing Required evidence, explicit uncertainty, empty discovery versus evidence insufficiency, unknown/duplicate IDs, missing candidate rows, conflicting discovered proposals, omitted competing proposals, schema diagnostics and valid JSON with incomplete completion metadata.

A bounded live-provider experiment used synthetic claims, current configured `sap/anthropic--claude-4.6-sonnet`, and three logical calls in a separate CF diagnostic process. It read existing model configuration, performed no ingestion, passed no store to claim execution, and wrote no Memory, derivation or lifecycle records. New module definitions were loaded only in that isolated process before deployment. Each call completed with one provider attempt, no retries/fallbacks.

| Synthetic workload | Logical calls | Prompt characters | Input tokens | Output tokens | Wall seconds | Returned pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v5 dense 3x4 | 1 | 9,373 | 3,005 | 877 | 8.554 | 12 |
| v6 sparse 3x4 | 1 | 5,164 | 2,228 | 370 | 4.382 | 2 |
| v6 sparse 8x183 | 1 | 48,199 | 13,020 | 594 | 5.975 | 2 |

The two planted relationships (contradiction and equivalence) were found in every applicable run. The larger cohort used five new independent claims and 179 independent incumbent distractors in addition to the small cohort. This is one simple synthetic sample, not the original large document, a recall estimate, a full model benchmark, or a guaranteed latency improvement. Original source ingestion was not rerun.
