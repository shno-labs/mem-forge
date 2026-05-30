# Gene Plugin Standard v2 -- Design Document

> **Status**: Draft
> **Authors**: Multi-expert design panel (ABC/Lifecycle, Auth/Config, Data Contracts, Registry/SDK, Testing/Quality)
> **Date**: 2026-04-11
> **Scope**: Standardize the gene plugin architecture so built-in and 3rd-party genes follow a single, testable contract.

---

## Table of Contents

1. [Overview & Goals](#1-overview--goals)
2. [Gene ABC v2 -- Contract & Lifecycle](#2-gene-abc-v2----contract--lifecycle)
3. [Custom Exception Hierarchy](#3-custom-exception-hierarchy)
4. [Authentication Strategy System](#4-authentication-strategy-system)
5. [HTTP Client Factory](#5-http-client-factory)
6. [Configuration Standard](#6-configuration-standard)
7. [Data Contracts](#7-data-contracts)
8. [Shared Normalizer Utilities](#8-shared-normalizer-utilities)
9. [Plugin Registry v2](#9-plugin-registry-v2)
10. [Entry Points & 3rd-Party Discovery](#10-entry-points--3rd-party-discovery)
11. [Gene Developer Kit (GDK)](#11-gene-developer-kit-gdk)
12. [Testing Standard](#12-testing-standard)
13. [Quality Gates](#13-quality-gates)
14. [Observability & Metrics](#14-observability--metrics)
15. [Error Handling & Recovery](#15-error-handling--recovery)
16. [Versioning & Compatibility](#16-versioning--compatibility)
17. [Migration Guide (v1 to v2)](#17-migration-guide-v1-to-v2)
18. [Appendix: Current State & Bugs](#appendix-current-state--bugs)

---

## 1. Overview & Goals

### What is a Gene?

A **gene** is a plugin that integrates an external data source (Confluence, Jira, Slack, ServiceNow, Teams, etc.) into MemInception's memory extraction pipeline. Each gene encapsulates the complete lifecycle of syncing data: authentication, discovery, fetching, and normalization.

### Design Goals

| Goal | Description |
|------|-------------|
| **Standardized contract** | Every gene follows the same abstract interface, data models, and lifecycle. |
| **Pluggable authentication** | Authentication is decoupled from the gene via an `AuthStrategy` interface. |
| **3rd-party extensibility** | External developers can create, test, and publish genes as pip packages. |
| **Moderate validation** | Validate critical contracts at registration; warn (don't block) at runtime. |
| **Testability** | A compliance test suite any gene can inherit to prove correctness. |
| **No code in this doc** | This document is a design specification. Implementation follows separately. |

### Key Decisions (Manager-Approved)

| Decision | Choice |
|----------|--------|
| Auth method | **Pluggable auth strategy** -- `AuthStrategy` protocol; gene picks/implements one |
| Plugin loading | **Entry points (pip install)** -- 3rd-party genes are separate packages |
| Validation strictness | **Moderate** -- validate metadata + config schema at registration; normalize output checked with warnings |
| Document location | `docs/design/gene-standard.md` |

---

## 2. Gene ABC v2 -- Contract & Lifecycle

### 2.1 API Version

```python
GENE_API_VERSION = "2.0"
```

Every gene declares the API version it was built against:

```python
class SlackGene(Gene):
    GENE_API_VERSION = "2.0"
```

### 2.2 Redesigned Abstract Base Class

```python
class Gene(ABC):
    """Abstract base class for all MemInception data-source plugins.

    Lifecycle (called by the sync orchestrator):

        gene = create_gene("confluence", config, source_id, auth_context)
        async for item in gene.discover(since=last_sync):
            raw  = await gene.fetch(item)
            norm = await gene.normalize(raw)
        await gene.close()
    """

    GENE_API_VERSION: str = "2.0"

    def __init__(self, config: dict, source_id: str, auth_context: AuthContext) -> None:
        self.config = config
        self.source_id = source_id
        self.auth_context = auth_context
        self.client = auth_context.client    # convenience shortcut
        self._log = logging.getLogger(
            f"{__name__}.{type(self).__name__}[{source_id}]"
        )

    # ── Class-level metadata (static, no I/O) ──────────────────────

    @classmethod
    @abstractmethod
    def metadata(cls) -> GeneMetadata: ...

    @classmethod
    @abstractmethod
    def _gene_config_fields(cls) -> list[ConfigField]:
        """Return gene-specific config fields (scope, filters, toggles).

        Connection and authentication fields are injected by the base class.
        """

    @classmethod
    def config_schema(cls) -> GeneConfigSchema:
        """Build the full schema: base fields + strategy fields + gene fields.

        Concrete genes do NOT override this. Override _gene_config_fields() instead.
        """
        # (base class assembles connection + auth + gene-specific fields)

    # ── Core lifecycle (MUST implement) ─────────────────────────────

    @abstractmethod
    async def discover(self, since: datetime | None = None) -> AsyncIterator[ContentItem]:
        """Yield content items created/modified since `since`.

        If since is None, perform a full discovery (initial sync).
        """

    @abstractmethod
    async def fetch(self, item: ContentItem) -> RawContent:
        """Fetch raw content for a single discovered item."""

    @abstractmethod
    async def normalize(self, raw: RawContent) -> NormalizedContent:
        """Convert raw content to clean, comprehensive markdown.

        The normalizer is the critical quality gate. It MUST surface
        all meaningful structured data as readable markdown.
        """

    # ── Should implement (has default, override encouraged) ─────────

    async def health_check(self) -> HealthCheckResult:
        """Probe source connectivity and credential validity.

        Default: delegates to auth_context.strategy.validate().
        Override to add source-specific checks (e.g., API version, permissions).
        """
        return HealthCheckResult(healthy=True)

    async def close(self) -> None:
        """Release resources (HTTP clients, file handles, temp files).

        Default: closes auth_context.client. Override if gene holds
        additional resources.
        """
        await self.auth_context.close()

    @classmethod
    def validate_config(cls, config: dict) -> list[str]:
        """Validate a config dict before source creation.

        Default: checks required fields per config_schema().
        Override to add gene-specific validation (e.g., test JQL syntax).
        Returns list of error strings (empty = valid).
        """
        return []

    # ── May implement (truly optional extensions) ───────────────────

    async def fetch_pdf(self, item: ContentItem) -> bytes | None:
        """Export content as PDF. Returns None if not supported."""
        return None

    @classmethod
    def migrate_config(cls, config: dict, from_version: int) -> dict:
        """Migrate a config dict from an older schema version.

        Default: returns config unchanged.
        """
        return config
```

### 2.3 Lifecycle Contract

The sync orchestrator calls gene methods in this exact order:

```
PHASE 1: Registration (at import / pip install time)
  ├─ metadata()            validate GeneMetadata
  ├─ config_schema()       validate GeneConfigSchema
  └─ register in GENE_REGISTRY

PHASE 2: Source Creation (user submits config form)
  ├─ validate_config()     check config before persisting
  └─ store config in database

PHASE 3: Sync Run (triggered by scheduler or manual)
  ├─ AuthStrategy.authenticate()   → AuthContext (gene receives it)
  ├─ Gene.__init__(config, source_id, auth_context)
  ├─ health_check()                → pre-flight connectivity test
  ├─ discover(since=last_sync)     → yields ContentItem stream
  │   └─ for each item:
  │       ├─ fetch(item)           → RawContent
  │       ├─ normalize(raw)        → NormalizedContent
  │       └─ [orchestrator: store, enrich, extract memories]
  ├─ [orchestrator: detect deletions]
  └─ close()                       → cleanup (always called, even on error)
```

### 2.4 Method Classification

| Category | Methods | Contract |
|----------|---------|----------|
| **MUST implement** (abstract) | `metadata()`, `_gene_config_fields()`, `discover()`, `fetch()`, `normalize()` | Registration fails if missing |
| **SHOULD override** (useful default) | `health_check()`, `close()`, `validate_config()` | Default works but gene-specific override is better |
| **MAY implement** (optional extension) | `fetch_pdf()`, `migrate_config()` | Orchestrator uses capability detection |

### 2.5 Timeout Expectations

| Method | Expected Duration | Hard Timeout |
|--------|-------------------|--------------|
| `metadata()` | < 1ms (no I/O) | N/A (classmethod) |
| `config_schema()` | < 1ms (no I/O) | N/A (classmethod) |
| `health_check()` | < 5s | 10s |
| `discover()` (full) | < 5 min | 30 min |
| `discover()` (incremental) | < 1 min | 5 min |
| `fetch()` per item | < 10s | 60s |
| `normalize()` per item | < 1s | 10s |
| `close()` | < 1s | 5s |

### 2.6 Concurrency Guarantees

- `discover()` is called **sequentially** (one gene at a time).
- `fetch()` and `normalize()` **may be called concurrently** across items from the same `discover()` run.
- `health_check()` may be called at any time, including during a sync.
- `close()` is called exactly once after all items are processed (in a `finally` block).

---

## 3. Custom Exception Hierarchy

```
GeneError (base)
├── AuthenticationError       raised by: AuthStrategy.authenticate()
├── ConfigurationError        raised by: validate_config()
├── DiscoveryError            raised by: discover()
├── FetchError                raised by: fetch()
│   └── RateLimitError        raised by: fetch() on HTTP 429
│       └── .retry_after_seconds: float | None
├── NormalizationError        raised by: normalize()
└── HealthCheckError          raised by: health_check()
```

### Orchestrator Response to Each Exception

| Exception | Orchestrator Behavior |
|-----------|-----------------------|
| `AuthenticationError` | Abort entire sync. Record in sync_history. Mark source unhealthy. |
| `ConfigurationError` | Abort sync. Surface error in admin UI. |
| `DiscoveryError` | Abort sync (no items to process). |
| `FetchError` | Retry item (up to 3x with exponential backoff). Then mark as failed. |
| `RateLimitError` | If `retry_after_seconds` set, wait that duration. Then retry. |
| `NormalizationError` | Skip item. Log warning. |
| `HealthCheckError` | Log warning. Do NOT abort sync (health check is advisory). |
| Bare `Exception` | Treat as `FetchError` (retry + fail gracefully). |

---

## 4. Authentication Strategy System

### 4.1 Design: Auth Moves Out of the Gene

**Key change from v1:** `authenticate()` is **removed from the Gene ABC**. Authentication is handled by a pluggable `AuthStrategy` *before* the gene is instantiated. The gene receives a pre-authenticated `AuthContext` at construction time.

This is the target v2 design for future gene-standard work. The current
implementation still lets each built-in gene prepare its own client, but shared
helpers now cover Atlassian TLS validation, request throttling, and rate-limit
handling. A future AuthStrategy layer should preserve those shared boundaries
while moving authentication out of individual genes.

This target design is intended to eliminate:
- Per-gene auth drift, such as cookie, PAT, or OAuth handling being implemented differently.
- Duplicated SSO cookie code.
- Scattered TLS verification policy.

### 4.2 AuthStrategy Protocol

```python
@runtime_checkable
class AuthStrategy(Protocol):
    """Interface every authentication strategy must satisfy."""

    @property
    def name(self) -> str:
        """Machine-readable ID: "sso_browser", "oauth2", "api_key", etc."""

    @property
    def display_name(self) -> str:
        """Human-readable label for the config UI select dropdown."""

    def required_config_fields(self) -> list[ConfigField]:
        """Config fields this strategy injects (group="authentication")."""

    async def authenticate(
        self, config: dict, base_url: str, client_factory: HTTPClientFactory
    ) -> AuthContext:
        """Create an authenticated session. Raises AuthenticationError on failure."""

    async def refresh(self, context: AuthContext, config: dict) -> AuthContext:
        """Refresh an expired session. Default: re-authenticate."""

    async def validate(self, context: AuthContext) -> bool:
        """Lightweight probe: are credentials still usable?"""
```

### 4.3 AuthContext

```python
@dataclass
class AuthContext:
    """Holds the authenticated HTTP client and credential state.

    Created by an AuthStrategy, consumed by the gene.
    Genes access self.auth_context.client for HTTP calls.
    """
    client: httpx.AsyncClient
    headers: dict[str, str] = field(default_factory=dict)
    cookies: httpx.Cookies | None = None
    tokens: dict[str, str] = field(default_factory=dict)
    expires_at: float | None = None       # UTC epoch seconds
    extra: dict[str, Any] = field(default_factory=dict)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()
```

### 4.4 Built-in Auth Strategies

| Strategy | Name | Use Case | Required Config Fields |
|----------|------|----------|----------------------|
| **SSOBrowserStrategy** | `sso_browser` | Chrome cookie extraction for corporate SSO | `sso_browser_type` (SELECT: chrome/firefox/edge), `sso_cookie_domain` (optional) |
| **OAuth2Strategy** | `oauth2` | OAuth2 client_credentials or authorization_code | `oauth2_grant_type`, `oauth2_client_id`, `oauth2_client_secret` (SECRET), `oauth2_token_url`, `oauth2_scopes`, `oauth2_audience` |
| **APIKeyStrategy** | `api_key` | Header-based API key (most SaaS APIs) | `api_key` (SECRET), `api_key_header` (default: "Authorization"), `api_key_prefix` (default: "Bearer") |
| **BasicAuthStrategy** | `basic` | Username + password (HTTP Basic) | `username`, `password` (SECRET) |
| **NoAuthStrategy** | `none` | Public APIs, VPN-gated services | *(none)* |

### 4.5 Gene Declares Supported Strategies

`GeneMetadata` gains two new fields:

```python
@dataclass
class GeneMetadata:
    name: str
    display_name: str
    description: str
    default_sync_interval_minutes: int
    supported_auth_strategies: list[str]    # NEW: replaces auth_method
    default_auth_strategy: str              # NEW: pre-selected in UI
    data_shape: str
```

Example:

```python
GeneMetadata(
    name="confluence",
    display_name="Confluence",
    supported_auth_strategies=["sso_browser", "basic", "oauth2", "api_key"],
    default_auth_strategy="sso_browser",
    ...
)
```

### 4.6 Strategy Registry

```python
AUTH_STRATEGIES: dict[str, AuthStrategy] = {}

def register_strategy(strategy: AuthStrategy) -> AuthStrategy: ...
def get_strategy(name: str) -> AuthStrategy: ...
```

Built-in strategies are registered at import time. 3rd-party strategies can be registered alongside custom genes.

---

## 5. HTTP Client Factory

Genes **must not** construct `httpx.AsyncClient` directly. The factory centralizes HTTP concerns.

```python
@dataclass(frozen=True)
class HTTPClientConfig:
    ssl_verify: bool = True
    timeout: float = 30.0
    max_retries: int = 3
    follow_redirects: bool = True
    ca_bundle_path: str | None = None

    @classmethod
    def from_gene_config(cls, config: dict) -> HTTPClientConfig: ...


class HTTPClientFactory:
    """Builds pre-configured httpx.AsyncClient instances."""

    def __init__(self, http_config: HTTPClientConfig) -> None: ...

    def create(
        self,
        base_url: str,
        *,
        headers: dict[str, str] | None = None,
        cookies: httpx.Cookies | None = None,
        auth: httpx.Auth | None = None,
    ) -> httpx.AsyncClient:
        """Create a client with standard SSL, timeout, retry, and redirect settings."""

    async def teardown(self) -> None:
        """Close all clients created by this factory.
        Called in a finally block after the sync run."""
```

### Orchestrator Integration

```python
# In sync.py:
http_config = HTTPClientConfig.from_gene_config(source_config)
factory = HTTPClientFactory(http_config)
try:
    strategy = get_strategy(source_config["auth_strategy"])
    auth_context = await strategy.authenticate(source_config, base_url, factory)
    gene = create_gene(source_type, source_config, source_id, auth_context)
    # ... discover, fetch, normalize ...
finally:
    await factory.teardown()
```

---

## 6. Configuration Standard

### 6.1 Mandatory Config Groups

Every gene's schema contains these three groups (injected by base class):

| Group Key | Label | Order | Content |
|-----------|-------|-------|---------|
| `connection` | Connection | 0 | How to reach the source |
| `authentication` | Authentication | 1 | How to prove identity |
| `scope` | What to Sync | 2 | What to pull |

Genes may add additional groups with `order >= 3`.

### 6.2 Mandatory Fields (Base Class Injects)

| Field | Type | Group | Notes |
|-------|------|-------|-------|
| `base_url` | URL, required | connection | Always first. Trailing slash auto-stripped. |
| `ssl_verify` | BOOLEAN | connection | Default `true`. Replaces hardcoded `verify=False`. |
| `request_timeout` | INTEGER | connection | Default `30` seconds. |
| `auth_strategy` | SELECT | authentication | Options from `metadata().supported_auth_strategies`. |
| *(strategy fields)* | varies | authentication | Injected per selected strategy. |

Genes add their scope fields via `_gene_config_fields()`:

```python
# ConfluenceGene
@classmethod
def _gene_config_fields(cls) -> list[ConfigField]:
    return [
        ConfigField(key="spaces", label="Spaces to Sync",
                    field_type=ConfigFieldType.TAG_LIST, required=True,
                    group="scope", order=0),
        ConfigField(key="page_tree_root", label="Page Tree Root (optional)",
                    field_type=ConfigFieldType.STRING, required=False,
                    group="scope", order=1),
        # ...
    ]
```

### 6.3 Conditional Visibility

Strategy-specific fields use `visible_when` for dynamic UI rendering:

```python
@dataclass
class ConfigField:
    # ... existing fields ...
    visible_when: dict[str, str | list[str]] | None = None
    # Example: {"auth_strategy": "oauth2"} -> show only when OAuth2 is selected
```

Server-side validation respects visibility: a `required=True` field hidden by `visible_when` is not enforced when its condition is not met.

### 6.4 Secret Field Handling

Fields with `field_type=ConfigFieldType.SECRET`:

| Layer | Behavior |
|-------|----------|
| **Storage** | Encrypted at rest in a separate `source_secrets` table |
| **API responses** | Value replaced with `"********"` |
| **Logging** | Replaced with `"[REDACTED]"` via `mask_secrets()` |
| **Export/backup** | Omitted entirely |

### 6.5 Config Validation

```python
def validate_config(config: dict, schema: GeneConfigSchema) -> list[ValidationError]:
    """Validate a config dict. Returns empty list if valid.

    Checks:
    - Required fields (respecting visible_when conditions)
    - Type plausibility (URL starts with http, INTEGER is castable, etc.)
    - SELECT values within declared options
    """
```

Called at source creation (admin API) and pre-sync (orchestrator).

### 6.6 Config Migration

When a gene updates its schema, existing configs are forward-compatible via `migrate_config()`:

```python
@dataclass
class GeneConfigSchema:
    groups: list[ConfigGroup]
    fields: list[ConfigField]
    version: int = 1            # NEW: bumped on schema changes

class Gene(ABC):
    @classmethod
    def migrate_config(cls, config: dict, from_version: int) -> dict:
        """Migrate config from an older schema version. Default: no-op."""
        return config
```

---

## 7. Data Contracts

### 7.1 ContentItem Standard

The unit of discovery. Every gene yields `ContentItem` from `discover()`.

| Field | Type | Required | Semantic Definition |
|-------|------|----------|---------------------|
| `item_id` | `str` | Yes | `{gene_name}-{source_native_id}`. Must match `^[a-z]+-[A-Za-z0-9._-]+$` |
| `title` | `str` | Yes | Human-readable. For tickets: `"KEY: summary"` |
| `source_url` | `str` | Yes | Complete, clickable URL to view in source system |
| `last_modified` | `datetime` | Yes | Timezone-aware (UTC). Most recent meaningful change. |
| `content_type` | `str` | Yes | MIME type of raw content: `"text/html"`, `"application/json"`, `"text/plain"`, `"text/markdown"` |
| `space_or_project` | `str` | Yes | Organizational container (space key, project key, channel name) |
| `version` | `str` | Yes | Opaque, comparable string that changes when content changes. For changelog tracking only. |
| `author` | `str \| None` | No | Primary human responsible ("who do I ask about this content?") |
| `labels` | `list[str]` | No | Source-native labels, lowercased. Empty list if none. |
| `extra` | `dict` | Yes | Source-specific metadata. See below. |

### 7.2 `extra` Dict Minimum Schema

Every gene MUST populate:

```python
{
    "source_item_id": str,    # Source system's native ID, undecorated
    # + gene-specific keys (flat, snake_case)
}
```

**Confluence example:**
```python
{"source_item_id": "12345", "space_key": "PAY", "page_id": "12345"}
```

**Jira example:**
```python
{"source_item_id": "PAY-100", "issue_key": "PAY-100", "status": "In Progress", "priority": "High", "issue_type": "Story"}
```

### 7.3 RawContent Standard

| Rule | Detail |
|------|--------|
| **Content type** | Must match `ContentItem.content_type` |
| **Encoding** | Always UTF-8. Genes transcode other encodings in `fetch()`. |
| **Size < 500 KB** | Normal processing |
| **Size 500 KB - 2 MB** | Gene logs warning; pipeline proceeds normally |
| **Size > 2 MB** | Gene SHOULD split into sub-documents in `discover()` |

### 7.4 NormalizedContent Standard

#### Markdown Template

All genes MUST produce markdown conforming to this structure:

```markdown
# {Title}

**Key1**: Value1 | **Key2**: Value2
**Labels**: label1, label2

## Content

{main body -- substantive content}

## Relationships

{issue links, parent/child, cross-references}

## Discussion

{comments, replies -- chronologically ordered}
**AuthorName** (YYYY-MM-DD):
Comment body text.

## History

{status transitions, edit log}
- Old State -> New State (YYYY-MM-DD)
```

**Rules:**
1. Title line (`# ...`) MUST be first.
2. Metadata block immediately after title (no `##` heading).
3. Sections marked "if applicable" are omitted when empty (no empty headers).
4. Stable ordering: template order above.
5. Clean whitespace: use `strip_boilerplate()` as final pass.

#### source_semantics Minimum Contract

```python
{
    # ── Required keys (every gene) ──
    "source_type": str,             # Gene name: "confluence", "jira"
    "labels": list[str],            # Empty list if none
    "author": str | None,           # Same as ContentItem.author
    "created_at": str | None,       # ISO-8601 creation timestamp
    "url": str,                     # Canonical source URL

    # ── Gene-specific keys (namespaced) ──
    "confluence": { ... },          # Only for Confluence items
    "jira": { ... },                # Only for Jira items
}
```

**Why namespaced?** Prevents key collisions as genes are added. The 5 required keys are read by the orchestrator/enricher. Gene-specific sub-dicts are opaque to the core pipeline.

#### Quality Requirements Checklist

1. **No data loss**: Every non-empty structured field in RawContent appears in markdown.
2. **Human-readable**: No raw JSON blobs or API field names. Write `**Status**: In Progress`, not `"statusCategory": {...}`.
3. **LLM-extractable**: Facts/decisions as natural language or clearly labeled key-value pairs.
4. **No empty sections**: Omit section headers when content is empty.
5. **Code block preservation**: Fenced code blocks preserved; use `annotate_code_blocks()`.
6. **Provenance stays provenance**: Author, last-modified, document status,
   reviewer, revision-history, and link-list fields should remain clearly labeled
   metadata. They are stored for traceability but should not be phrased as domain
   facts that the memory extractor would persist.
7. **Normalization is the extension point**: Genes own source-specific
   normalization only. After `NormalizedContent` is produced, the shared
   source-agnostic update planner chooses diff-guided extraction or
   full-document fallback, and the centralized memory pipeline owns extraction,
   reconciliation, support management, review gating, and lifecycle writes. See
   `docs/design/source-agnostic-memory-extraction.md`.

---

## 8. Shared Normalizer Utilities

### 8.1 Existing Utilities (Usage Contract)

| Utility | When to Use |
|---------|-------------|
| `html_to_markdown(html)` | MUST use for any `content_type="text/html"` gene |
| `strip_boilerplate(md)` | MUST use as final cleanup step in every gene |
| `annotate_code_blocks(md)` | RECOMMENDED when content contains code |
| `count_tokens(text)` | Do NOT call from genes (orchestrator handles it) |

### 8.2 New Utilities to Add

#### `build_metadata_header()`

Builds the standard `# Title` + metadata block:

```python
def build_metadata_header(
    title: str,
    primary_fields: dict[str, str | None],    # inline: "**Key**: Val | ..."
    labels: list[str] | None = None,
    extra_lines: list[str] | None = None,     # additional "**Key**: Val" lines
) -> str: ...
```

#### `build_optional_section()`

Builds a `## Heading` section only if content exists:

```python
def build_optional_section(heading: str, lines: list[str]) -> str:
    """Returns "" if all lines are empty/whitespace."""
```

#### `json_field_to_markdown()`

Extracts JSON fields as markdown key-value lines (dot notation for nested access):

```python
def json_field_to_markdown(
    data: dict,
    field_map: dict[str, str],    # {"status.name": "Status", ...}
    prefix: str = "",
) -> list[str]: ...
```

#### `clean_text()`

Normalizes whitespace, strips control characters:

```python
def clean_text(text: str) -> str: ...
```

### 8.3 NormalizeHelper (Composition Helper)

A composable helper for building NormalizedContent with a fluent interface:

```python
class NormalizeHelper:
    def __init__(self, item: ContentItem) -> None: ...
    def set_header(self, title, primary_fields, labels, extra_lines) -> Self: ...
    def set_content(self, body: str) -> Self: ...
    def add_section(self, heading: str, lines: list[str]) -> Self: ...
    def set_semantics(self, source_type, created_at, gene_specific) -> Self: ...
    def build(self) -> NormalizedContent:
        """Assembles markdown, applies strip_boilerplate() + annotate_code_blocks(),
        validates template, populates required semantics keys, returns NormalizedContent."""
```

Genes may use the helper or build markdown manually -- it's a convenience, not a requirement.

---

## 9. Plugin Registry v2

### 9.1 Registry Data Structure

```python
GENE_REGISTRY: dict[str, type[Gene]] = {}    # backward-compatible

@dataclass
class GeneRegistryEntry:
    cls: type[Gene]
    metadata: GeneMetadata
    config_schema: GeneConfigSchema
    api_version: str
    origin: str                    # "builtin" | "entrypoint" | "manual"
    capabilities: set[str]         # auto-detected from class

_GENE_INFO: dict[str, GeneRegistryEntry] = {}
```

### 9.2 Public API

| Function | Purpose |
|----------|---------|
| `register_gene(gene_cls, *, origin="manual")` | Validate and register a gene class |
| `create_gene(name, config, source_id, auth_context)` | Instantiate with config validation |
| `list_available_genes()` | Return `list[GeneMetadata]` (backward-compatible) |
| `list_gene_entries()` | Return `list[GeneRegistryEntry]` (full info) |
| `get_gene_info(name)` | Return `GeneRegistryEntry` for one gene |

### 9.3 Registration Validation (Fail Hard)

`register_gene()` validates before accepting:

| Check | Error if Invalid |
|-------|------------------|
| Is a `Gene` subclass | `TypeError` |
| No abstract methods remain | `GeneRegistrationError` listing missing methods |
| `metadata()` returns valid `GeneMetadata` | `GeneRegistrationError` with specifics |
| `metadata().name` matches `^[a-z][a-z0-9_-]*$` | `GeneRegistrationError` with example |
| `config_schema()` returns valid `GeneConfigSchema` | `GeneRegistrationError` with specifics |
| All field groups reference declared groups | `GeneRegistrationError` |
| SELECT/MULTI_SELECT fields have options | `GeneRegistrationError` |
| `GENE_API_VERSION` major matches host | `GeneRegistrationError` |
| No name collision (built-in names are reserved) | `GeneRegistrationError` |

### 9.4 Capability Detection

Capabilities are auto-detected from the class, not declared:

| Capability Flag | Detection |
|-----------------|-----------|
| `supports_pdf_export` | Has `fetch_pdf()` not equal to base default |
| `supports_health_check` | Has `health_check()` not equal to base default |
| `supports_incremental_sync` | Default `True` (all genes accept `since`) |
| `supports_deletion_detection` | Has `detect_deletions()` method |
| `supports_webhooks` | Has `register_webhook()` method |

Capabilities are stored in `GeneRegistryEntry.capabilities` and exposed via admin API for UI badges.

---

## 10. Entry Points & 3rd-Party Discovery

### 10.1 Package Structure

A 3rd-party gene is a standard pip package:

```toml
# pyproject.toml
[project]
name = "meminception-gene-slack"
version = "0.3.0"
dependencies = ["meminception>=0.1.0"]

[project.entry-points."meminception.genes"]
slack = "meminception_slack:SlackGene"
```

The entry point *name* is informational. The registry key comes from `metadata().name`.

### 10.2 Boot Sequence

```python
# genes/__init__.py (bottom of module)
_register_builtins()              # 1. Built-in genes get "builtin" origin
_discover_entrypoint_genes()      # 2. Entry points cannot override builtins
```

### 10.3 Discovery Function

```python
def _discover_entrypoint_genes() -> None:
    """Scan installed packages for meminception.genes entry points."""
    eps = importlib.metadata.entry_points(group="meminception.genes")
    for ep in eps:
        try:
            gene_cls = ep.load()
            register_gene(gene_cls, origin="entrypoint")
        except GeneRegistrationError as exc:
            logger.warning("Skipping gene entry point %s: %s", ep.name, exc)
        except ImportError as exc:
            logger.warning("Skipping gene %s: missing dependency - %s", ep.name, exc)
        except Exception as exc:
            logger.warning("Skipping gene %s: load failed - %s", ep.name, exc)
```

### 10.4 Failure Modes

| Failure | Behavior |
|---------|----------|
| Missing dependency (`ImportError`) | WARNING log. Gene skipped. Others unaffected. |
| Not a `Gene` subclass | WARNING log. Gene skipped. |
| API version incompatible | WARNING log. Gene skipped. |
| Name collision with built-in | WARNING: "reserved by built-in". Gene skipped. |
| Name collision with another entry point | WARNING. Second gene skipped. |

---

## 11. Gene Developer Kit (GDK)

### 11.1 Template Project (Cookiecutter)

```
meminception-gene-{name}/
├── pyproject.toml              # entry_points, deps, build config
├── src/
│   └── meminception_{name}/
│       ├── __init__.py         # re-exports the Gene class
│       ├── gene.py             # Gene subclass skeleton
│       └── py.typed            # PEP 561 marker
└── tests/
    ├── conftest.py             # fixtures, mock HTTP routes
    ├── test_gene.py            # gene-specific unit tests
    └── test_compliance.py      # GeneTestSuite contract tests
```

### 11.2 Skeleton Gene (Generated)

```python
class {{ClassName}}(Gene):
    GENE_API_VERSION = "2.0"

    @classmethod
    def metadata(cls) -> GeneMetadata:
        return GeneMetadata(
            name="{{gene_name}}",
            display_name="{{display_name}}",
            description="{{short_description}}",
            default_sync_interval_minutes=60,
            supported_auth_strategies=["api_key"],
            default_auth_strategy="api_key",
            data_shape="{{data_shape}}",
        )

    @classmethod
    def _gene_config_fields(cls) -> list[ConfigField]:
        return [
            # Add source-specific scope fields, such as project keys or spaces.
        ]

    async def discover(self, since=None) -> AsyncIterator[ContentItem]:
        # Yield ContentItem instances discovered from the source.
        ...

    async def fetch(self, item: ContentItem) -> RawContent:
        # Fetch source-native content for the discovered item.
        ...

    async def normalize(self, raw: RawContent) -> NormalizedContent:
        # Convert source-native content into normalized markdown.
        ...
```

### 11.3 Compliance Test (One File)

```python
# tests/test_compliance.py
from meminception.testing import GeneTestSuite
from meminception_slack import SlackGene

class TestSlackCompliance(GeneTestSuite):
    gene_class = SlackGene
    sample_config = {"channels": "#general", ...}
    mock_routes = [
        {"method": "GET", "url_pattern": "/api/conversations.list", "json": {...}},
    ]
```

All contract tests inherited automatically (15+ tests covering every lifecycle stage).

### 11.4 Developer Documentation Outline

1. **Quick Start** -- cookiecutter, fill template fields, run pytest, pip install into MemInception
2. **Gene Lifecycle** -- diagram, method responsibilities, error expectations
3. **Data Model Reference** -- ContentItem, RawContent, NormalizedContent field-by-field
4. **Configuration Design** -- groups, fields, secrets, dynamic visibility
5. **Testing Your Gene** -- GeneTestSuite, MockHTTPServer, integration testing
6. **Publishing** -- PyPI naming (`meminception-gene-*`), versioning
7. **Capability Flags** -- what each enables
8. **Troubleshooting** -- common registration errors, debugging checklist

---

## 12. Testing Standard

### 12.1 GeneTestSuite (Contract Compliance)

A base `pytest` class that any gene subclasses. Gene developers override `gene_class`, `sample_config`, and `mock_routes`.

#### Test Catalog

| Test | Stage | Validates |
|------|-------|-----------|
| `test_010_metadata_valid` | metadata | GeneMetadata fields, name format, valid data_shape, valid auth strategies |
| `test_020_config_schema_valid` | config | Groups consistent, field types valid, SELECT has options, no duplicate keys |
| `test_030_authenticate_success` | auth | No exception with valid config + mock HTTP |
| `test_031_authenticate_failure` | auth | Raises AuthenticationError with bad config |
| `test_040_discover_yields_content_items` | discover | All items are ContentItem, item_id format, required fields populated |
| `test_041_discover_incremental` | discover | `since` parameter reduces results, all items newer than `since` |
| `test_050_fetch_returns_raw_content` | fetch | Returns RawContent, non-empty body, content_type matches |
| `test_060_normalize_returns_valid_markdown` | normalize | Non-empty markdown, starts with `#`, meets minimum length |
| `test_061_normalize_returns_valid_semantics` | normalize | Dict with 2+ keys, all JSON-serializable, string keys |
| `test_070_health_check` | health | Returns dict with `"healthy"` boolean key |
| `test_080_teardown_cleans_up` | close | No unclosed HTTP clients after `close()` |

### 12.2 Testing Utilities

| Utility | Purpose |
|---------|---------|
| `MockHTTPServer` | Configurable httpx mock transport. Routes matched by method + URL regex. |
| `sample_content_item(gene_name, **overrides)` | Factory for valid ContentItem with sensible defaults |
| `sample_raw_content(gene_name, body, **overrides)` | Factory for valid RawContent |
| `sample_normalized_content(...)` | Factory for valid NormalizedContent |
| `assert_valid_normalized_content(nc)` | Full contract validation in one call |
| `assert_valid_source_semantics(sem, gene_name, data_shape)` | Minimum keys + shape-specific checks |

### 12.3 Shape-Specific Minimum Semantics

| Data Shape | Minimum Keys in `source_semantics` |
|------------|--------------------------------------|
| `document` | `author` |
| `ticket` | `status`, `priority` |
| `message` | `sender` |
| `email` | `sender`, `subject` |
| `event` | `start_time` |

---

## 13. Quality Gates

### 13.1 Registration-Time (MUST Pass -- Blocks Registration)

| Check | Consequence |
|-------|-------------|
| Gene is `Gene` subclass with all abstract methods | `TypeError` |
| `metadata()` returns valid `GeneMetadata` | `GeneRegistrationError` |
| `config_schema()` returns valid `GeneConfigSchema` | `GeneRegistrationError` |
| `GENE_API_VERSION` major matches host | `GeneRegistrationError` |
| No name collision | `GeneRegistrationError` |

### 13.2 Runtime (WARNING Only -- Never Blocks Sync)

| Check | When | Severity |
|-------|------|----------|
| `markdown_body` empty | After `normalize()` | ERROR -- skip item |
| `markdown_body` < 50 chars | After `normalize()` | WARNING |
| Missing required `source_semantics` keys | After `normalize()` | WARNING |
| Non-standard top-level semantics keys | After `normalize()` | INFO |
| `item_id` format invalid | After `discover()` | WARNING |
| `last_modified` is timezone-naive | After `discover()` | WARNING (auto-fix to UTC) |
| `health_check()` returns unhealthy | Periodic probe | WARNING -- admin UI turns yellow |

### 13.3 Surfacing

- **Structured logs** with `warning_code`, `gene`, `source_id`, `item_id`
- **Sync history** table: `warnings` JSON array per sync run
- **Admin API**: `GET /api/sources/{id}/health` returns health + warning counts

---

## 14. Observability & Metrics

### 14.1 Per-Gene Metrics (Collected by Orchestrator)

| Metric | Type | Collected At |
|--------|------|--------------|
| `gene_discover_total` | Counter | End of discover -- total items yielded |
| `gene_discover_duration_seconds` | Histogram | Wall time of full discover() |
| `gene_fetch_success_total` | Counter | After each successful fetch() |
| `gene_fetch_failure_total` | Counter | After each failed fetch() |
| `gene_fetch_bytes_total` | Counter | Sum of len(raw.body) |
| `gene_normalize_duration_seconds` | Histogram | Wall time of each normalize() |
| `gene_normalize_tokens_total` | Counter | Sum of markdown token counts |
| `gene_auth_success_total` | Counter | After successful auth |
| `gene_auth_failure_total` | Counter | After failed auth |
| `gene_health_check_healthy` | Gauge (0/1) | After each health_check() |
| `gene_sync_items_total` | Counter | Items processed per sync |
| `gene_sync_items_failed` | Counter | Items failed after all retries |
| `gene_sync_memories_extracted` | Counter | Memories inserted per sync |

**Genes do not emit metrics.** The orchestrator wraps each lifecycle call and records timings/counts automatically.

### 14.2 Structured Logging Standard

**Orchestrator-level** (automatic):

| Stage | Level | Fields |
|-------|-------|--------|
| Auth start/success | INFO | gene, source_id |
| Auth failure | ERROR | gene, source_id, error |
| Discovery complete | INFO | gene, source_id, items_found, since |
| Fetch per-item | DEBUG | gene, source_id, item_id, bytes |
| Normalize per-item | DEBUG | gene, source_id, item_id, markdown_len |
| Sync complete | INFO | gene, source_id, run_id, processed, updated, failed, memories |

**Gene-internal** (developer responsibility via `self._log`):
- **DEBUG**: API requests, pagination, cache hits
- **INFO**: Major milestones (e.g., "switched to fallback mode")
- **WARNING**: Recoverable problems (e.g., "page had no body, skipping")
- **ERROR**: Never. Let exceptions propagate to orchestrator.

---

## 15. Error Handling & Recovery

### 15.1 Two-Tier Retry Model

| Tier | Owner | When | Max Attempts | Backoff |
|------|-------|------|-------------|---------|
| **Tier 1: Gene-internal** | Gene developer (optional) | Known-transient issues within one API call | 2 | Max 10s |
| **Tier 2: Orchestrator** | Automatic | Failed `fetch()` or `normalize()` | 3 | Exponential (2s, 4s, 8s) |

**Gene developer rule**: Raise exceptions, don't swallow them. The orchestrator handles retry.

### 15.2 HTTP Error Handling Matrix

| HTTP Status | Gene Action | Orchestrator Action |
|-------------|-------------|---------------------|
| 429 (Rate Limit) | MAY parse `Retry-After`. Otherwise raise. | Retry with backoff. |
| 401 (Auth Expired) | Raise. Do NOT retry auth. | Abort sync. Next sync re-authenticates. |
| 403 (Forbidden) | Raise. | Item failed. No retry. |
| 404 (Not Found) | Raise. | Item failed. Deletion detection handles cleanup. |
| 500 (Server Error) | Raise. | Retry with backoff. |
| Timeout | Let `httpx.TimeoutException` propagate. | Retry with backoff. |

### 15.3 Circuit Breaker (Orchestrator-Level)

Prevents a down source from consuming retry budget across many items:

```
CLOSED ──(5 consecutive failures)──> OPEN
  ^                                    |
  |                              (60s cooldown)
  |                                    v
  <──(2 consecutive successes)── HALF_OPEN
```

| Parameter | Default |
|-----------|---------|
| `failure_threshold` | 5 consecutive failures |
| `half_open_after_seconds` | 60 |
| `success_threshold` | 2 consecutive successes to close |

**OPEN state**: All remaining items immediately marked as failed. Sync completes as `"partial"` or `"failed"`. Log: `"Circuit open: {n} consecutive failures. Skipping {remaining} items."`.

Gene developers do not need to think about circuit breakers.

---

## 16. Versioning & Compatibility

### 16.1 GENE_API_VERSION Semantics

| Change Type | Version Bump |
|-------------|-------------|
| New abstract method | **Major** |
| Existing method signature changes | **Major** |
| Required field added to GeneMetadata | **Major** |
| New optional method with default | Minor |
| New optional GeneMetadata field | Minor |
| New ConfigFieldType variant | Minor |
| Bug fix in base defaults | Minor |

### 16.2 Compatibility Check

Major-version equality only:

```python
declared_major = int(gene_cls.GENE_API_VERSION.split(".")[0])
current_major  = int(GENE_API_VERSION.split(".")[0])

if declared_major != current_major:
    # HARD REJECT
```

If `GENE_API_VERSION` not declared: assume compatible, log DEBUG suggestion to add it.

### 16.3 Deprecation Strategy

1. **Minor release (e.g., 2.1)**: Old method/field works. `DeprecationWarning` at registration.
2. **Next major (e.g., 3.0)**: Removed. Registration fails with migration message.
3. **MIGRATING.md**: Ships with each major bump, listing every breaking change + mechanical fix.

---

## 17. Migration Guide (v1 to v2)

### 17.1 For Existing Genes (Confluence, Jira)

| Step | Change |
|------|--------|
| 1 | Add `GENE_API_VERSION = "2.0"` class attribute |
| 2 | Replace `auth_method: str` with `supported_auth_strategies: list[str]` + `default_auth_strategy: str` in metadata |
| 3 | Remove `authenticate()` method. Accept `auth_context: AuthContext` in `__init__`. Use `self.client` instead of `self._client`. |
| 4 | Rename `config_schema()` scope fields to `_gene_config_fields()`. Remove base_url and sso_login_url (now injected). |
| 5 | Keep all config access on `self.config`; current Jira code already follows this convention |
| 6 | Fix Confluence: remove `import ssl` (unused) |
| 7 | Restructure `source_semantics` to v2 contract: add 5 required keys, namespace gene-specific keys |
| 8 | Adopt markdown template: rename section headers (Jira), add `## Content` (Confluence) |
| 9 | Add `"source_item_id"` to `extra` dict |
| 10 | Decide whether Jira needs a dedicated `health_check()` beyond the sync-time browser-session validation path |
| 11 | Use `build_metadata_header()` and `build_optional_section()` from normalizer_utils |
| 12 | Add `close()` override if holding resources beyond the HTTP client |
| 13 | Move Confluence's `_get_chrome_cookies()` into `SSOBrowserStrategy` |

### 17.2 For the Orchestrator (sync.py)

| Change |
|--------|
| Create `HTTPClientFactory` and `AuthContext` before gene instantiation |
| Call `close()` in `finally` block (replaces nothing -- clients were never closed!) |
| Add runtime validation calls (`validate_content_item`, `validate_normalized_content`) |
| Use typed exception handling (`AuthenticationError` -> abort, `FetchError` -> retry, etc.) |
| Check `capabilities` for `supports_pdf_export` instead of `hasattr(gene, "fetch_pdf")` |
| Add circuit breaker around item processing loop |
| Instrument lifecycle calls with metrics |

### 17.3 For the Admin API (admin_api.py)

| Change |
|--------|
| Call `validate_config()` before source creation |
| Return `capabilities` in gene info endpoint |
| Support `visible_when` in config schema response |
| Mask SECRET fields in config responses |

---

## Appendix: Current State & Bugs

### A.1 Current Implementation Summary

| Component | File | Lines |
|-----------|------|-------|
| Gene ABC | `genes/base.py` | 195 |
| Registry | `genes/__init__.py` | 154 |
| ConfluenceGene | `genes/confluence_gene.py` | 419 |
| JiraGene | `genes/jira_gene.py` | 536 |
| Shared models | `models.py` | 509 |
| Sync orchestrator | `pipeline/sync.py` | 1321 |
| Normalizer utils | `pipeline/normalizer_utils.py` | 211 |
| Admin API | `server/admin_api.py` | 2607 |

### A.2 Current Gaps

| Gap | Severity | Location |
|-----|----------|----------|
| Built-in genes still own client/auth setup instead of receiving an AuthContext | Design gap for v2 standardization | `confluence_gene.py`, `jira_gene.py`, `teams_gene.py` |
| `GeneMetadata.auth_method` is still a single display/default string, while Jira now supports browser-session and PAT modes through config | Design mismatch | `models.py`, `jira_gene.py` |
| Jira has sync-time browser-session validation and rate-limit handling, but no standalone `health_check()` override | Operational gap | `jira_gene.py` |

### A.3 Inconsistency Summary

| Aspect | Confluence | Jira | v2 Standard |
|--------|-----------|------|-------------|
| Config access | `self.config` | `self.config` | `self.config` always |
| Auth implementation | HTTPS PAT with shared Atlassian helpers | Browser-session or PAT with shared Atlassian helpers | AuthStrategy handles it |
| SSL verification | Validated TLS or optional CA bundle | Validated TLS or optional CA bundle | `tls_ca_bundle` config field |
| health_check | Overridden (API ping) | Not implemented as a standalone method | SHOULD override (encouraged) |
| source_semantics | 4 fields, flat | 8 fields, flat | 5 required + namespaced gene-specific |
| Markdown structure | Shallow (header + body) | Deep (6 sections) | Standard template with optional sections |
| Normalizer utils | Uses html_to_markdown + strip_boilerplate | All inline | Use shared utils + NormalizeHelper |
| `extra` dict | 2 keys | 4 keys | Minimum: `source_item_id` |

---

*End of Gene Plugin Standard v2 Design Document*
