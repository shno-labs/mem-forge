# Pinned Evidence resource: shared contract review

Status: bounded static review, not implementation or runtime acceptance. Reviewed the working tree on 2026-10-03. Canonical requirement: [ADR 0046, tool boundary](../adr/0046-separate-evidence-correspondence-from-citation-presentation.md#6-carry-citations-through-the-actual-tool-boundary).

## Finding

Existing immutable Observation Revisions, Evidence References, Evidence Units and retained Support assertions are sufficient to serve historical text citations after Support rebinding or retirement. No additional table, provenance ledger, compatibility matcher or business state is needed. `get_memory_evidence_units` currently selects only active Support assertions; that restriction is appropriate for the normal current Memory projection, but prevents an old citation resource from resolving its retained Unit.

The current `/source-units/{id}/content` operation reads the latest `SourceUnitInput`, not immutable revision authority. Its URL cannot prove a historical citation. The new working-tree guard removes such a content/PDF link when the Unit revision differs; a pinned resource is still required.

Evidence reads verify the stored raw digest against the exact immutable revision range, then verify the readable excerpt's presentation digest. They already reject the entire supporting Unit if a supporting reference is invalid, missing, outside its source lineage, or the Unit lacks exactly one Primary. Reuse this boundary rather than writing a second citation verifier.

Sources: [SQLite projection](../../src/memforge/storage/database.py), methods `get_memory_evidence_units` and `_project_memory_evidence_item`; [shared protocol](../../src/memforge/storage/adapters/protocols.py); [SQLite forwarding adapter](../../src/memforge/storage/adapters/sqlite/relational.py); [admin projection/resource routes](../../src/memforge/server/admin_api.py).

## Smallest shared change

Extend the existing store contract to `get_memory_evidence_units(memory_id, *, include_historical=False)`. The default retains current behavior. A pinned resource uses `True` to include the same Memory's inactive Support assertions; the Unit/reference validation remains identical. Implement the exact signature and behavior in SQLite, HANA and their forwarding adapters. Historical membership is proven by the retained assertion joining Memory to Unit, never by a semantic search or latest source input.

Use a Memory-scoped pinned resource, for example `/api/v1/memories/{memory_id}/evidence/{evidence_unit_id}/references/{reference_id}`. A Unit-scoped resource with an explicit selected-reference identity is also sufficient. Resolve the Unit from that Memory's historical projection and select the reference by persisted identity. Return its readable excerpt, exact anchor, raw/presentation digests, Source Unit/revision, and the complete Primary/Required supporting set. Optional raw selected bytes/text can be included as such; raw markup is not the ordinary `get_memory` excerpt. Read only stored immutable Observation Revision content, including legacy normalized content under its actual declared format.

The resource checks the same Memory visibility predicate used by `get_memory`, the Unit's own `visibility`/`owner_user_id`, and current Source access. The current projection only carries Source identity and checks Source discoverability; `EvidenceUnit` already stores its own access fields, but the projection omits them. Include those fields in the internal projection or obtain the existing `get_evidence_unit` record, then apply the same Unit predicate before returning any supporting part. A visible Primary must not allow access to an inaccessible Required part. No caller-controlled Unit/reference ID may bypass Memory membership or the complete Unit checks.

Unavailable historical material returns an explicit unavailable result. Denied access should keep the existing default-deny 404 behavior, avoiding disclosure of whether another user's Unit exists. Integrity mismatch must be distinguishable from successful content, e.g. a typed 409. A latest provider URL can remain navigation; it is never a historical proof substitute.

Sources: [Evidence domain records](../../src/memforge/memory/evidence.py), `EvidenceUnit`, `MemoryEvidenceUnitProjection`; [Memory visibility route](../../src/memforge/server/admin_api.py), `get_memory`, `_filter_visible_ids`; [Source access owner](../../src/memforge/source_access.py). Cloud parity target: `packages/adapters/store/hana/src/memforge_cloud/adapters/store/hana/workspace.py`, `get_memory_evidence_units` and its public forwarding method.

## Context and history boundary

Primary/Required references belong to their immutable Unit. Context references instead use `evidence_context_associations`, explicitly a mutable current projection. Associations retain inactive rows, but may be reactivated; their current timestamps are not a complete historical snapshot. Do not remove `association.active = 1` and describe all ever-associated Context as one past revision's context set.

A previously emitted Context reference can still resolve by its exact retained reference ID and a retained association to that Unit, including inactive association membership. Return it explicitly as non-supporting Context and distinguish association status. The complete supporting dependency set remains the immutable Primary/Required set. If the application needs a complete historical Context snapshot, that is a separate requirement; it is not established by the current schema and is unnecessary for restoring retained Primary/Required citations.

Normal lifecycle retirement/rebinding deactivates Support assertions without deleting their Evidence. Physical Memory/source deletion and explicit evidence graph deletion can remove authority through existing cascades; after such deletion, return unavailable rather than fabricate history. Existing artifact resolution also requires `so.current_revision_id`; it cannot yet be called a historical artifact reader. This review does not introduce image/model-capability work.

Sources: [SQLite schema and writes](../../src/memforge/storage/database.py), `replace_evidence_context_associations`, `_stage_lifecycle_evidence_unlocked`, `_delete_evidence_graph_for_memory_unlocked`, `get_source_artifact_revision`.

## Actual tool boundary

The current MCP compactor drops `evidence_reference_id`, observation/revision identity, Source Unit/revision, anchor range and digests. Preserve those identities and the pinned resource URL for every item. Keep every Primary/Required item even when shortening its excerpt; annotate each shortened excerpt with `truncated: true` and its original character count. Do not truncate a JSON string and then present it as a complete parsed resource or silently discard the tail of the Unit's references.

`get_resource` currently accepts only current Document/Source Unit and Source Artifact paths. Add an exact allowlisted pinned-resource path while preserving same-origin restrictions, workspace routing and path validation. File mode can deliver a large complete JSON resource. Text mode should either return complete valid JSON within its transport budget, or return a structured explicitly incomplete view preserving every citation identity; exceeding a byte ceiling can remain an explicit error with file-mode guidance.

Source: [MCP proxy](../../src/memforge/plugin_mcp_proxy.py), `_compact_memory_evidence_unit`, `_compact_memory_evidence_item`, `_parse_resource_url`, `_fetch_resource_inline`.

## Transport references

Official sources read online on 2026-10-03:

- [RFC 9110, sections 8.3, 8.8.3 and 9.3.2](https://www.rfc-editor.org/rfc/rfc9110.html): media type identifies the transferred representation, ETag identifies that representation, and HEAD describes the corresponding GET. Compute HTTP ETag and `X-Content-SHA256` over the actual serialized response, not the selected raw range digest when returning a JSON envelope. Keep the selected raw/presentation digests as separate JSON fields. Use private/no-store caching when access can change; a revision-pinned URL is not perpetual authorization. Text source downloaded: SHA-256 `21c1cdce6ab0e5509b04d84a28000836c7a087cf786efe6f04877ebfff47232a`.
- [RFC 8259, sections 8.1 and 11](https://www.rfc-editor.org/rfc/rfc8259.html): interoperable JSON is UTF-8 and uses `application/json`. A character-truncated prefix is not a complete JSON document. Text source downloaded: SHA-256 `61a5378f4255c720beb2a4b4a63b29540147c140f36988bf086291989b4cd2d7`.
- [MCP Resources specification, 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/server/resources): resource reads carry URI and media type and support text/binary contents. This project currently exposes a `get_resource` tool; using an HTTP pinned resource does not require adding MCP subscriptions or another resource subsystem. HTML downloaded: SHA-256 `e0b9457ceccf74e55371a202d9270a118e0f4941ebd97018c2990d5691b422db`.

## Required boundary evidence

Test current versus historical inclusion; inactive Support after rebind/retire; wrong Memory/Unit/ref membership; missing revision/range digest corruption; private Unit under workspace Source; inaccessible Required causing complete Unit omission; Context exact retained-reference resolution; latest input overwritten while historical resource remains unchanged; legacy normalized history honestly declared; and tool compaction/budget behavior preserving all identities. HANA tests must assert matching active/history SQL predicates, Memory/Unit parameters, provenance constraints and returned semantics. Passing a current-only reader test cannot establish historical acceptance.

## Controlled implementation validation

The shared implementation now reads retained Support and the complete supporting
part set, checking the persisted Unit part-set digest as well as each reference's
raw/presentation integrity. Memory, Unit and Source permissions apply before
emitting the resource. A Unit-backed ordinary Document association cannot mask
a denied or invalid Unit by emitting a replacement Primary.

Historical citation validity does not require equality with today's compiler
Fragment boundaries. The resource returns stored verified citations and the
complete immutable Unit source material under its actual representation profile.
A part URL may read one exact retained Context association; its material is
explicitly non-supporting and not necessarily a member of the supporting Unit's
historical manifest. This does not construct a past Context snapshot.

A second bounded independent static review found the prior compiler-boundary
and missing-Required issues closed, with no new blocking access/provenance path.
This is static evidence, not online-model or blind semantic acceptance.

Executed from the canonical OSS checkout using the shared Cloud Python runtime:

- API/SQLite/Evidence/relation/time cohort: **190 passed in 27.76 seconds**.
  Command: `python -m pytest tests/test_evidence_unit_support.py tests/test_memory_quality.py tests/test_admin_entities_adapter_contract.py tests/test_cross_document_relation_cases.py tests/test_cross_document_relation_group_cases.py tests/test_relation_discovery.py tests/test_relation_discovery_operations.py tests/test_source_revision_time.py -q`.
- Both actual tool clients, compaction, package synchronization and hooks:
  **253 passed in 10.10 seconds**. Command: `python -m pytest tests/test_pinned_evidence_tools.py tests/test_tool_client_sources.py tests/test_hook_adapter.py tests/test_plugin_mcp_relations.py tests/test_sync_plugin_mcp_proxy.py -q`.
- Clean HANA workspace plus admin proxy contract cohort, with all clean Cloud
  package directories and canonical OSS source explicitly selected on
  `PYTHONPATH`: **516 passed in 21.81 seconds**. Command:
  `python -m pytest tests/unit/test_hana_workspace_store.py tests/integration/test_hana_admin_proxy_compat.py -q`.

Controls cover inactive Support and changed current revision, private Unit under
workspace Source, source/Memory access, wrong Memory/Unit membership, corrupted
or deleted Required, incomplete manifest, a retained range spanning two compiler
Fragments, exact inactive Context association, preservation of every ref identity,
whole-resource and part URL routing, same-origin/path/query validation, corrupt
stream digest, complete UTF-8 JSON, and explicit file-mode guidance on budget
limits. HANA tests assert the same active/history/context SQL predicates and
bound parameters. Test doubles carry the actual Unit digest and current protocol
signatures; a hand-seeded image fixture without a v2 digest was corrected to
represent valid v2 supporting membership rather than adding a reader exception.

Detailed output: `/tmp/memforge-pinned-api-store-tests.txt`,
`/tmp/memforge-pinned-tool-tests.txt`, `/tmp/memforge-pinned-hana-tests.txt`.
These are controlled runtime/fake-adapter tests. CF/HANA live SQL execution,
remote RC plugin installation/restart, online Sonnet plus fresh blind review,
composed Cloud UI build/deployment and product smoke remain separate unpassed gates.
No model request, provider document fetch, deployment or product reprocess was
performed in this resource-validation step.

The broader affected native/Support/Review/lifecycle cohort passed **362 tests in
62.92 seconds** after a synthetic clone fixture was corrected to recompute its
part-set digest when changing Observation identity. The initial run passed 361
and rejected that incorrectly cloned digest, so no production reader exception
was added. Command: `python -m pytest tests/test_source_unit_input.py tests/test_memory_evidence_store.py tests/test_projected_lifecycle_store.py tests/test_support_relation_coordinator.py tests/test_support_relation_coordination.py tests/test_confluence_native_evidence.py tests/test_projected_lifecycle_integration.py tests/test_memory_reviews.py -q`.
Output: `/tmp/memforge-pinned-lifecycle-native-tests.txt`.

Both OSS V1 and V2 UI production builds passed with the bundled Node runtime
and the lockfile-installed dependencies. V2 API types were regenerated from the
actual exported OpenAPI document. The six existing V2 Memory detail tests passed
in 9.65 seconds. Both UI versions link the complete pinned Unit and each exact
citation. Commands: `npm run build` in `admin-ui/` and `admin/`, and
`vitest run src/features/memories/MemoryDetailPage.test.tsx` in `admin/`.
Output: `/tmp/memforge-pinned-ui-v1-build.txt`,
`/tmp/memforge-pinned-ui-v2-build.txt`, `/tmp/memforge-pinned-ui-v2-tests.txt`.
This proves controlled OSS UI builds, not composed Cloud deployment or browser
acceptance against real historical sources.
