# Native Source format contracts: Confluence and Jira

Source-only research and bounded adapter review, 2026-10-03. This record contains primary-source links, artifact identities and structural findings; **no private source text or model output**. It consolidates the independent native-body, Jira-field and Confluence-display audits. It does not certify complete claim extraction, online Sonnet quality, blind-review acceptance, deployment or lifecycle convergence.

## Authentic inputs and conservation evidence

| Complete retained input | Size and SHA-256 | Source-only finding |
|---|---|---|
| Confluence native page body, artifact `confluence-6378070218-raw_source-38eda4ad6e0563c6.html` | 71,051 bytes / 70,981 Unicode characters; `38eda4ad6e0563c6a759881d1f35817d2ab3a4112a22363600d270d5a2a0789b` | Full native tree balances; 27 tag names / 1,372 element starts; 78 macros / 225 scalar macro parameters; 12 independent tables / 60 rows / 354 authored cells. |
| Jira native issue response, artifact `jira-SFPAY-184406-raw_source-828b504feef809f8.json` | 50,807 bytes; `828b504feef809f8d9d9c19e551b70989fdb6f751fe7efe7a0f9c433db52dae3` | Response explicitly includes `renderedFields` and `changelog`; current native description 1,549 characters, returned HTML 3,401 characters; zero comments; ten complete changelog histories. |

These private artifacts are retained in the local Source artifact store, not copied into the repository. Byte/character counts and hashes refer to the actual native inputs, not normalized exports or reconstructed Markdown.

### Confluence complete grammar inventory

Tag counts: `a:58; ac:link:33; ac:parameter:225; ac:structured-macro:78; br:54; code:4; col:48; colgroup:11; div:99; em:1; h1:4; h2:3; h3:2; li:5; p:156; pre:16; ri:page:1; ri:user:32; span:68; strong:22; table:12; tbody:12; td:308; th:46; time:13; tr:60; ul:1`.

Macro structures: one self-closing `toc` with no parameters/body; 43 bodyless `status` macros with `colour,title`; 34 bodyless `jira` macros with `server,serverId,key` (16), `server,columnIds,columns,serverId,key` (17), or `showSummary,server,columnIds,columns,serverId,key` (one). All macro parameters are scalar; no duplicate parameter names or unvalued/duplicate attributes occur.

All 12 tables are top-level, with row×column dimensions `4×3, 1×2, 8×6, 1×2, 21×7, 6×7, 1×2, 9×6, 1×2, 3×6, 1×2, 4×6`. One cell has rowspan 2; there is no colspan or nested table. Each table independently passed the then-current adapter's row/coverage validation. The 16 ordinary HTML `pre` elements are not CDATA code macros: twelve contain no element children; four contain macros and/or line breaks. Preserve their actual structure, rather than reclassifying them as literal storage bodies.

Other observed structures: nine numbered headings; 99 `content-wrapper` divs; styled spans and table/column widths; link URLs; 32 opaque user resources; one page-title resource; 13 date elements. No comments, declarations, processing instructions, CDATA, unknown tags or additional macro families occurred. This inventory does not prove support for structures absent from the input.

The initial public adapter call failed specifically at undeclared `toc`, after the full tree parsed successfully. The subsequent display diff recognizes that bodyless macro and omits generated navigation, preserving native storage, real headings and authored siblings. That change was statically reviewed; the original reproduced failure is historical evidence, not a statement that the current adapter still rejects this input.

### Jira current and historical field conservation

The current provider HTML uses ten tag names: `p:14, b:6, br:3, tt:1, a:4, div:2, pre:1, span:13, img:3`. It includes syntax-highlighter spans/classes and three attachment-preview links/images. All three authored attachment names correspond to returned preview titles after separating the native thumbnail option; none of the images has alt text. Identity/title navigation can be exposed without claiming unseen image contents.

The native description's observed code region has **300 authored characters**. Joining provider `pre` text through the syntax-highlighter spans and decoding HTML entities preserves **all 300 characters exactly**, SHA-256 `75484e5a651c70f85dd7418746ca645592c0f9927a98faae4235ea60ff8a80a7`. This includes both original opening tags, their region attribute and the author's incomplete trailing code. No closing tag was fabricated. This addresses the concrete earlier Markdown interpreter loss of an outer literal HTML tag; it does not establish preservation of every possible Jira field or renderer.

The issue response has `startAt=0,maxResults=10,total=10` and ten returned changelog histories; its comment collection has `startAt=0,total=0` and no comments. This is completeness **for this response**, not a universal ten-history API limit or comment acceptance evidence. Future truncated response totals must continue using the existing partial-projection/coverage semantics.

Ten change items cover duedate (one), Link (two), Request Source (one), Attachment (three), Affected Areas (one), summary (one), description (one). Their old/new values include twelve strings and eight nulls. The description change's prior native value has 1,393 characters, while its new value is the same 1,549-character string as the current field. **Current returned HTML does not attest a rendering of that prior value.** Null is not an invented empty string.

Field hashes: current native description `11c304c944b8043725156ba4ac15980800dfbd9ead2c5ea387d41fcaf2389cdc`; current returned HTML `2de02de91941eed323610015c533f86738e2a77c72a2835e7b2835838a006ec4`; prior native description `31d211f09018dc827779e034e3798e9b48b2ac7582f01834c633b46e76d68e33`.

## Provider contracts and ownership

[Confluence storage format](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html) describes XML-based storage with custom macro/resource elements and XHTML-style structure. [Table of Contents Macro](https://confluence.atlassian.com/doc/table-of-contents-macro-182682099.html) explicitly documents macro name `toc`, **body None**, and navigation parameters. [Cloud TOC](https://support.atlassian.com/confluence-cloud/docs/insert-the-table-of-contents-macro/) confirms that it scans current-page headings to generate navigation.

TOC is therefore a known generated-navigation structure. The Confluence adapter may validate and suppress that output while retaining its original configuration, real headings and sibling text. Unknown macros, invalid bodies, duplicate/unknown parameters or unclassified authored content must not become silent omissions. Status title/colour and Jira key remain visible; verbose column/display settings may be suppressed. [Jira Issues Macro](https://confluence.atlassian.com/doc/jira-issues-macro-139380.html) separates Jira instance selection from display options: server identity is origin, not merely cosmetic. Preserve it in raw material/provenance even when normal excerpts are abbreviated.

[Jira Data Center REST API 9.12.2](https://docs.atlassian.com/software/jira/docs/api/REST/9.12.2/) expressly documents `expand=renderedFields` as field values in **HTML format**, and comment `expand=renderedBody` as the body rendered in HTML. [Configuring renderers](https://confluence.atlassian.com/adminjiraserver/configuring-renderers-938847270.html) states that renderers are configured per field and may differ by project/issue type; renderers/macros are extensible apps. A native Jira string, source type or code-like marker alone therefore cannot declare wiki grammar. Returned HTML attests a provider-formatted view of the returned snapshot, without requiring a renderer-configuration guess.

All native grammar, macro classification, literal-code rules and meaningful rendering decisions belong in their corresponding Source adapter. The shared compiler consumes the existing declared-format callback and exact decoded-string-to-parent coordinate map; the shared extraction prompt consumes faithful views and adapter interpretation. Neither should acquire Confluence/Jira grammar branches or reconstruct missing source content.

## Proposed Jira v2 interface review

At the time of this record, canonical Jira v1 still declares description/comment/change strings as Markdown. The following is a reviewed **proposed contract**, not a claim that v2 is implemented or accepted:

1. Add versioned Jira issue/comment v2 schemas preserving paired originals: the native field value and the exact provider-returned HTML from the **same field/comment snapshot**, together with the declared provider-HTML format. Parse/cite the immutable returned HTML through a Jira-owned `DeclaredTextFormat`. A nested paired object or separate native/rendered scalar fields is sufficient; no new provenance ledger is required.
2. Keep **v1 registered and frozen for retained history**, including explicit Jira legacy profile declarations for pre-profile backfill. Moving the current writer to v2 must not make NULL-profile old records acquire v2 or cause historical citation reads to borrow current provider rendering. A new content/schema identity and normal one-time re-extraction/reassessment are appropriate; lossless v1→v2 correspondence is not required.
3. Keep native originals available for inspection without duplicating them as equivalent model-facing citations. Provider HTML is authoritative as a returned presentation, not proof that every app/renderer preserves every token. No Markdown reconstruction, wiki grammar sniffing or silent omission is justified if nonempty current fields lack required rendering. Empty/null fields represent absent content and must retain that distinction.
4. Changelog v2 old/new strings are **literal native scalar values**, under Jira-owned interpretation of previous/new field and event time. They are neither the current field's HTML nor implicitly Markdown/wiki. Preserve null values and dates; a change event timestamp does not establish the business rule's effective date. Historic formatted views require independently attested historic rendering; this payload has none.
5. Current issue collection/get calls already request `renderedFields`. Separate comment fetch and truncated-comment top-up paths must request **`expand=renderedBody`**, keeping comment ID/body/renderedBody paired in the same response. Cached/discovery payloads also require explicit validation or that existing fetch path before a new complete comment representation can be claimed. The zero-comment cohort cannot validate this supported variant.

The v2 contract is an actual source-representation change, unlike Confluence's abbreviated display/TOC support addition: v2 introduces provider-returned HTML alongside native values and corrects historical scalar interpretation. Version current writers without editing immutable old observations.

## Future correspondence and evidence limits

Selection coordinates must address retained native/returned source, never display strings or latest `SourceUnitInput`. Within the same declared contract, compare adapter material: text/literal values, semantic structure and link/media identity, with bilateral uniqueness. Known syntax-highlighter decoration, attribute order, offsets and display labels must not alone invalidate unchanged selection content. Preserve meaningful formatting; do not remove all attributes through generic cleanup. A partial ref must not inherit the full field's native digest as its identity, or an unrelated paragraph edit would invalidate all refs.

Confluence's display-only diff retains its canonical material and persisted schema; its extraction/presentation policy bump invalidates earlier model-input work. Jira v2 requires a new schema identity. Neither exact ref correspondence nor the 300-character conservation check proves that an entire Memory remains supported after surrounding qualifiers, history or scope change. Existing whole-claim assessment remains separate.

These source/parser findings close named representation questions. They do **not** replace complete actual-document extraction, online configured Sonnet calls, independent blind review of claims/citations, adapter boundary tests or deployment smoke evidence.

## Official captures

Official pages read online on 2026-10-03; hashes identify downloaded page bytes and are not provider source revisions:

| Official page | Download bytes | SHA-256 |
|---|---:|---|
| Confluence storage format | 186,996 | `dbe0cc8305ab173cedf533f8c240294686969747752018f4c44d5235e98dc430` |
| Data Center TOC macro | 176,343 | `4689bef34143e195e4ca8598601d3f5b8e570a88ae99e47a1a0bbfd72e1f9470` |
| Cloud TOC | 554,141 | `d8764e51a98f07e6bb04e5b3e90a49d6a228d6af78af2f4bf03cfcb5511a7544` |
| Jira Issues Macro | 180,846 | `d8539313c6740f538eda73072e08e14c05ac325435dc00a1a0ebc6bce29f5137` |
| Jira DC REST API 9.12.2 | 1,230,298 | `4a04cfac3a91d25ccd0197c6a1afdfe11ba7f48d9a0e68ea8fba7c4e22e261fa` |
| Configuring renderers | 158,508 | `92589556234b8f37ce5d195a57b9436639e514b005c0b54b11709bf50d363e3b` |

[Jira Cloud REST v2 issue documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issues/) was additionally inspected (4,458,477 bytes, SHA-256 `d993ef78c55d1c0d314934894021f8e94b148b547587484ed9ebbed39da43a7a`). It does not by itself prove ADF/v3 parity, historical renderer semantics or acceptance of this string-based provider variant.

Implementation references: [Confluence declarations](../../src/memforge/source_adapters/confluence.py), [native storage parser](../../src/memforge/source_adapters/confluence_storage.py), [Jira declarations](../../src/memforge/source_adapters/jira.py), [declared format contract](../../src/memforge/source_adapters/contracts.py), [Jira gene](../../src/memforge/genes/jira_gene.py), [canonical projection](../../src/memforge/pipeline/source_projection_adapters.py), [representation registry](../../src/memforge/source_representation.py). Durable architectural decisions belong in the canonical ADR; this research record supplies source evidence, not a separate execution backlog.
