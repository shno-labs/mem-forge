# Read native Evidence by structure, with an open vocabulary

Status: Accepted

Date: 2026-10-09

## Context

The Confluence and Jira adapters compile provider-native text into
revision-pinned Evidence selections. Confluence pages are read from the storage
format; Jira descriptions and comments are read from the HTML the provider
renders for each field.

Both providers have an open vocabulary. Installed apps add Confluence macros
freely, and the storage elements Atlassian itself writes exceed its published
reference (task identities and emoji attributes are examples). Jira's renderer
emits classes, attributes and styles that vary with the markup and the
installed renderer plugins. A grammar that enumerates accepted names therefore
never converges, and a name it has not seen fails the whole Source Unit. In one
real page tree, 90 pages could not be compiled and 17 could: 26 distinct macros
and 23 distinct causes, with two or more causes on most pages. Those Units stay on
their last committed revision, so nothing is retired in error, but their
knowledge stops updating.

Two representations of a Confluence page are available from the same REST
response, and they differ in kind:

- **Storage** is the authored body. It is identical for every fetch of one page
  version. Every macro has the same envelope: named parameters and an optional
  rich-text or plain-text body. A macro with a body carries its authored text;
  a macro without one carries only the reference it was configured with.
- **Rendered HTML** (`view`, `export_view`) is computed for the caller at
  request time. It is not a function of the page version: repeated fetches of
  one version differ in attribute order and generated identifiers. It embeds
  content owned by other pages and issues, emits placeholders for output that
  only a browser loads, and hides authored bodies behind the same generic
  classes it uses for runtime controls. The REST API has no completeness
  indicator for it.

Making rendered HTML the Evidence input was considered and rejected. Its only
material gain is display names for user references, which storage records as
opaque keys. Every deterministic completeness check available for it is derived
from storage, so storage would still have to be parsed in full. Generated
content that fails to load would be indistinguishable from an authored
deletion, and guarding against that requires holding every Memory of an
affected page unresolved for as long as the page embeds any generated content.

## Decision

Native text adapters read structure, not a list of names.

1. **Storage is the Confluence Evidence representation.** Evidence is a pure
   function of the version-pinned authored body.
2. **Vocabulary is open; structure is closed.** An element, attribute, class,
   style or macro name the adapter does not declare is never an error. Only
   markup that is not well formed is rejected, and that rejection is the signal
   that the body was not obtained intact.
3. **Declared rules refine; the structural rule is total.** A declared rule
   applies only to an instance that has exactly the shape it describes. Every
   other macro is read by its envelope: its name, every parameter value and its
   body. An undeclared rich-text body keeps its blocks individually selectable
   under the macro's parameter values, and bounds the headings inside it.
4. **Present by default; omit only by declaration.** Whatever an adapter does
   not present is, for lifecycle, indistinguishable from deleted content. The
   fallback therefore always shows the content, and each omission is named in
   the adapter with its reason: editor-only template instructions, opaque
   identities, and elements HTML never displays.
5. **Nothing undeclared is erased from comparison.** Undeclared attributes,
   classes and styles remain in comparison material, so a change to them is
   never classified as unchanged. In Jira's rendered HTML they are also shown
   beside the text they control.
6. **Generated content is not Evidence.** A macro without a body states what
   the page embeds. What the provider generates for it when the page is viewed
   belongs to no page revision; it is neither fetched nor inferred, and its
   absence can never be read as a deletion.

The rules live in the Confluence and Jira adapters. The shared compiler,
correspondence, Support routing and lifecycle flow are unchanged, and no
lifecycle state is added.

## Consequences

- A page or issue is rejected only when its markup is malformed. Its previous
  revision, Support and Memories are then kept exactly as before.
- Inputs the adapters already accepted produce identical selections,
  comparison material and presentation. No format, schema or compiler version
  changes, stored Evidence stays valid, and exact cross-revision correspondence
  is unaffected. A change that alters the output of an accepted input still
  requires a new source contract.
- Knowledge that exists only in generated macro output (child listings,
  includes, property reports, issue tables) is not learned from the embedding
  page. It is learned from the page or issue that owns it when that Unit is in
  scope.
- Constructs outside the declared rules read with less polish: an undeclared
  macro shows its raw parameter names, and a table whose cells form no grid is
  one whole selection. This is deliberate; a noisier selection is recoverable
  and a rejected page is not.
- A future provider element that is not page content appears as text until the
  adapter declares it. Declaring it is a presentation change for inputs that
  contain it.
- User references stay opaque keys. Resolving them needs the provider's user
  API and is a separate decision.
- Diagram and attachment content is outside this decision.

## References

- [Native Evidence semantics](../design/evidence-adapter-semantics.md)
- [ADR 0030](0030-compile-revision-pinned-evidence-fragments.md)
- [Confluence Storage Format](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html)
- [Confluence content representations](https://docs.atlassian.com/atlassian-confluence/6.2.4/com/atlassian/confluence/api/model/content/ContentRepresentation.html)
