# GitHub Pages Source

GitHub Pages is a document source. Its source-specific work stops at
discovering pages, fetching rendered HTML, and normalizing the main article
body into stable markdown. Memory extraction, update handling, reconciliation,
support management, contradiction detection, and review gates stay in the
shared source-agnostic pipeline.

## Scope Model

The source supports three practical sync modes:

```text
single_page
  Sync exactly one page URL.

subtree
  Sync pages under one URL path prefix.

explicit_list
  Sync exactly the configured URL list.
```

The first version intentionally does not provide a section picker. Heading
anchors are renderer-dependent and can silently change. For large sites, users
should choose a single page, a path subtree, or an explicit URL list, then rely
on diff-guided extraction to handle small within-page updates.

## Authentication

The source supports two authentication modes:

```text
github_pat
  Use a GitHub personal access token stored through the encrypted source-secret
  path. Read repository Markdown through the GitHub API so private-mode Pages
  sites do not depend on an interactive browser session.

none
  Fetch rendered pages without authentication.
```

Browser-cookie authentication is intentionally not part of the first version.
Enterprise deployments should prefer `github_pat` when the Pages site requires
authenticated access. Repository-backed PAT mode accepts both standard GitHub
Enterprise Server project-site layouts:

```text
subdomain isolation enabled
  https://pages.<github-host>/<owner>/<repo>/...

subdomain isolation disabled
  https://<github-host>/pages/<owner>/<repo>/...
```

For the subdomain-isolated form, repository API requests use
`https://<github-host>/api/v3/repos/<owner>/<repo>`. The published Pages URL
remains the document identity and the URL shown to users. This split follows
GitHub Enterprise Server's documented Pages URL layouts and subdomain-isolation
model.

References:

- [GitHub Enterprise Server: What is GitHub Pages?](https://docs.github.com/en/enterprise-server@3.20/pages/getting-started-with-github-pages/what-is-github-pages)
- [GitHub Enterprise Server: Enabling subdomain isolation](https://docs.github.com/en/enterprise-server@3.20/admin/configuring-settings/configuring-network-settings/enabling-subdomain-isolation)

## Discovery

For PAT-backed sources, subtree discovery reads the repository tree and maps
Markdown paths back to published page URLs. For no-auth sources, subtree
discovery prefers `sitemap.xml`; if no sitemap is available, the source crawls
same-origin links from the subtree root and keeps only links under the
configured root path. Discovery is bounded by `max_depth` and `max_pages`;
hitting `max_pages` is a loud error, not a silent partial sync.

URLs are canonicalized before identity and scope checks:

```text
lowercase host
strip query and fragment
collapse repeated slashes
normalize trailing slash
same origin only
```

Document ids are stable hashes of canonical URLs:

```text
github-pages-<sha1(canonical_url)>
```

## Fetch And Normalize

No-auth fetch retrieves rendered HTML. PAT-backed fetch retrieves the matching
Markdown blob through the repository API. Rendered HTML normalization extracts
the main article content and removes documentation chrome:

```text
header
navigation
sidebars
table of contents
search UI
footer
script and style tags
```

The normalized markdown shape is:

```markdown
# <page title>

## Source Metadata
- Source Type: GitHub Pages
- Site URL: <configured site>
- Page URL: <canonical page>
- Version: <etag or last-modified>

## Document
<main article markdown>
```

The normalized output must avoid sync-time-only noise so the shared update
planner can safely compare old and new markdown.

## UI Pattern

GitHub Pages uses the existing schema-driven source dialog. It does not need a
custom picker wizard because users already have stable URLs.

The useful generic UI addition is discovery preview:

```text
POST /api/genes/{source_type}/preview-discovery
```

The preview runs the configured gene without saving the source and returns the
first discovered items. It stops after the requested preview limit plus one
item, so `truncated=true` means more items exist without making preview as
expensive as a full sync. This protects users from accidentally syncing a much
larger subtree than intended, and it also benefits other document sources.

## Memory Pipeline

After normalization, GitHub Pages documents use the same update behavior as all
other sources:

```text
first sync -> full_document extraction
small normalized diff -> diff_guided extraction
large normalized diff -> full_document extraction over deterministic units
extraction failure -> full_document fallback over deterministic units
```

The deterministic extraction units are owned by the shared memory pipeline, not
by the GitHub Pages gene. No GitHub Pages-specific memory extraction or
lifecycle rules are allowed.
