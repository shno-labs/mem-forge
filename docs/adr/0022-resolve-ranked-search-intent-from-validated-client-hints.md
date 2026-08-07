# Resolve ranked search intent from validated client hints

Status: Proposed (2026-08-07)

MemForge ranked search accepts an optional Requested Retrieval Intent from an Agent Client because the client can use conversational context that is absent from the query string. The service resolves that hint through minimal deterministic validation, falls back without an LLM call when the hint is absent, and never derives intent from the query language or a semantic-versus-lexical classification. General Hybrid Retrieval and Known Item Lookup hints are honored; Relationship Exploration falls back to General Hybrid Retrieval when scoped entity linking produces no traversable entity. Deterministic Listing remains a separate operation rather than a search intent.

## Consequences

All ranked intents continue to run independent vector, content lexical, metadata lexical, and eligible relationship channels before intent-specific weighted rank fusion. Intent can alter ranking policy but cannot alter visibility, source/time facets, provenance rules, or other authorization boundaries. Agent Clients should construct a self-contained query in the user's language while preserving identifiers and domain terms; clients that omit intent retain a deterministic, provider-neutral default.

The MCP `search` contract requires a natural-language query and accepts `general_hybrid`, `known_item`, or `relationship` as an optional intent hint. Queryless SearchEngine and HTTP compatibility may remain behind that public contract, but deterministic current-state enumeration is exposed through `list_recent_memories`, not as a search mode. Source and time facets remain explicit caller constraints and are never inferred from intent or repository context.

The compact Agent Client response reports the requested and resolved intent, the intent source, and any fallback reason. Per-result channel ranks and weighted fusion contributions remain available to evaluation and service diagnostics rather than expanding every MCP result.

The OSS contract is language-neutral and embedding-provider-neutral: it does not detect or translate query languages, and it does not claim cross-language quality for a model that lacks multilingual capability. Deterministic tests prove intent and channel behavior for Unicode queries; real cross-language quality gates run only for deployments or configurations that declare a multilingual embedding capability.

Each resolved ranked intent uses one stable fusion policy rather than language- or sentence-shape-dependent weights. A bounded evaluation sweep selects the concrete weights subject to existing exact-identity, metadata, graph, visibility, and adapter-parity hard constraints. Release cases with a canonical target require that target in the first five results while preserving any stricter existing family-specific gate.
