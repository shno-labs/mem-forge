# Native Evidence semantics and independent revision work

Status: implemented and locally validated; deployment acceptance is recorded separately. Date: 2026-10-07.

## Runtime flow

The source adapter parses the immutable provider input into existing
`DeclaredTextFragment` and `DeclaredTextGroup` values. The representation compiler
binds selections to revision-pinned coordinates, raw integrity and typed views.
The current revision then supplies two independent calculations: new-work Primary
authority, and complete changed/current material for incumbent Support assessment.
Exact correspondence separately proves whether an old selection has one current
occurrence. Extraction and Support retain their existing runner and coordinator;
the lifecycle plan remains one guarded atomic commit.

This refines the RepresentationCompiler and extraction-authority nodes in
[the existing flow diagram](images/revision-update-flow.excalidraw). The diagram's
AMBIGUOUS-to-Support-Assessment route is unchanged. No stage, persistent catalog,
provider-specific pipeline branch, business status or model repair is added.

## Adapter ownership

The built-in projection owners are `confluence`, `jira`, `teams`, `github_repo`,
`github_pages`, `local_markdown` and `agent_session` in `source_adapters`.
Session receipt interpretation belongs to the session adapter. Confluence parent
pages and GitHub file predecessors are declared as typed Unit endpoints; shared
projection code assigns stable IDs without parsing provider-specific prefixes.
Standard Markdown structure remains a shared format. The GitHub Pages and local
Markdown adapters own URL/path/lineage and coverage semantics, not copies of the
Markdown parser. This projection boundary does not change managed-session intake
or its conversation-retention policy.

Every provider-specific tag, class, attribute, macro and field rule belongs in
its source adapter. Jira rendering decoration is declared in one element/class
policy table. Confluence native containers and macros declare their body shape
and semantic role. Parsing, canonical material, presentation and selection
traversal consume those same declarations. CanonicalRecord schemas and the
existing format interface remain the shared compiler's only input.

## Open vocabulary, closed structure

Both grammars read structure, not a list of names
([ADR 0048](../adr/0048-read-native-evidence-by-structure-with-an-open-vocabulary.md)).
A declaration refines how a known construct reads; it is never a gate. Only
markup that is not well formed is rejected: unbalanced or unclosed elements,
duplicate attributes, undefined entities, unclosed CDATA, and content placed
directly in a layout container that holds only sections or cells.

Confluence storage:

* An undeclared element is a container of its children. Text placed directly
  in a layout cell is its own selection.
* A macro is read by its envelope. A declared rule applies only when the
  instance has exactly the parameters and body shape it describes. Otherwise a
  macro without a body reads `[Macro name: parameter=value; …]`, a plain-text
  body is literal, and a rich-text body is a container: its blocks stay
  individually selectable, each non-empty parameter is a selection that governs
  them, and headings inside it govern nothing after it. A body with text placed
  directly in it stays one selection with the macro's name and parameters.
* A table's own rows form its grid; a table inside a cell is that cell's
  content. A table whose rows and spans form no rectangular grid is one whole
  selection read row by row.
* List content placed between items continues the item above it.
* Declared omissions: `ac:placeholder` is template instruction shown only in
  the editor, and `ac:task-id` / `ac:task-uuid` are opaque identities. They stay
  in comparison material.

Jira rendered HTML:

* An undeclared element is an inline container of its children. `script` and
  `style` content and comments are never displayed by HTML and are not text.
* An attribute, class or style outside the declared tables is never erased. It
  stays in comparison material and is shown after the text it controls, for
  example `Hidden exception [style: display:none]`. Its element is neither
  transparent nor omitted, so declared decoration cannot hide it.
* A table with spans, nested tables or uneven rows is one whole selection read
  row by row.

A Confluence macro without a body states what the page embeds: a child listing,
an include, an issue query, a diagram. What Confluence generates for it when
the page is viewed belongs to no page revision. It is never fetched during
compilation and never Evidence, so its absence cannot be read as a deletion.

Presentation containers preserve authored children and independent evidence
granularity. Layout cells bound heading interpretation to their own column.
Inline annotation identities do not replace or erase authored text. Semantic
controls retain meaning: links keep their target and supplied user identity,
colour controls remain readable, literal bodies retain whitespace, table headers
remain interpretation origins, and task completion participates in comparison.

The explicit supported Confluence additions are layout/section/cell, inline
comment markers, task lists, emoticons and local excerpt bodies. The Jira additions
cover provider table classes/wrappers, panels/noformat wrappers, mentions, font
controls and emoticon classes. Standard Jira link icons, no-wrap wrappers,
bookmark anchors, list markers and image sizing are rendering decoration;
issue-link identities and cited text retain their semantic material. Jira wiki
`+text+` is provider-rendered as `<ins>` for underline, not a content insertion
event. Format 2 normalizes that marker to underline before the same comparison
and presentation traversal; historical format 1 remains bound to schemas 2–4.
Likewise `-text-` / `<del>` is strikethrough, presented as `[struck through: …]`
without asserting a deletion event. Only issue/comment schemas advance to 5; literal changelog schema 4 is unchanged.
Source-specific declarations also cover Jira syntax-highlight classes and forced
line breaks. Constructs outside these declarations read by the structural rules
above.

External Confluence include, children and excerpt-include output is not present
in the immutable snapshot. These macros read as the reference they state, never
as the content they would display. Expanding collection/dependency ownership is
a separate decision; no source-body fetch is introduced during compilation or
get_memory.

## Three representations, one authentic input

* The anchor names one Observation revision and a Unicode range in its retained
  content. Decoded native-field ranges are translated by the existing compiler.
* `content_value`, kind and interpretation material form the versioned comparison
  input; display strings and model paraphrases never identify occurrences.
* Adapter presentation is a readable complete source selection. The existing
  extraction/Support response may supply separate focused `display_text`.

Offsets identify a selection in one revision, not its identity in another.
An unchanged unique selection is found by verified canonical material and then
bound to its new revision coordinates. Ambiguity never establishes an identity.

## Multiplicity and authority

Count changes in existing identical material authorize no arbitrary occurrence
as new Primary work. They also do not make independent new material unplannable.
The shared comparison calculation returns every genuinely new material key for
authority; current-reading calculation returns all current copies whose count
changed. Removed copies are inferred only when the population falls to zero.
This rule applies to standard text, canonical fields and nested native text.

Exact correspondence still checks both old and current cardinalities. A growing
or shrinking duplicate population routes the complete Support to assessment.
Mandatory incumbent coverage, unresolved handling, stale guards and destructive
validation remain unchanged. No terminal planning failure is suppressed at the
caller, and no broad unchanged content is granted new-work authority.

## Registered contract compatibility

This change extends previously rejected source syntax without changing previously
accepted native-format outputs. Existing representation/schema/view versions
remain registered. Frozen pre-change parser outputs and persisted Evidence rows
are the compatibility oracle; the new code must preserve coordinates, canonical
material, presentation, origins and reading groups for these inputs.

Changing an already accepted input's interpretation, selection boundaries or
presentation requires a new source contract and retained old interpretation.
Changing only computation policy uses execution-contract versions to supersede
unapplied older work without reinterpreting or migrating historical Evidence.
When a registered Observation profile changes, the planner validates the current
contract and authorizes the current Observation as upgrade reading. It does not
compute narrow ranges across different schema or text-format contracts. Stored
Evidence remains pinned to its historical representation; the existing
whole-Support assessment decides current claim support without exact reuse across
profiles. Subsequent same-profile revisions again use narrow changed ranges.
Authority segmentation policy 8 records this execution change.
The current identities are compiler contract 10, extraction v22 and admission v7;
the approved local failure policy and its validation are recorded in
[the canonical alignment evidence](../research/2026-10-07-local-failure-alignment-validation.md).

## Acceptance

1. Formerly rejected source layouts/controls compile through the real projection
   and fragment interfaces; semantic metadata and literal content stay readable.
2. Every frozen v1 parser result is unchanged; independently frozen persisted
   references pass both SQLite and HANA delivery with equal DTOs.
3. Unrelated insertion and accepted decoration preserve unique correspondence;
   changed governing headers/statuses are not classified as unchanged meaning.
4. Duplicate growth leaves independent new authority available, reports occurrence
   ambiguity, reads every affected current copy, and does not infer removal.
5. Full affected lifecycle checks still complete before commit; required failures
   cannot leave partial revision/Memory mutations.
6. A bounded real native-document replay, deployed API/resource/UI retrieval and
   incremental source update validate the actual deployed package. Fixture results
   and live provider/model results are reported separately.

Official grammar references:
* https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html
* https://docs.python.org/3/library/html.parser.html
* https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/ins
* https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/cite
