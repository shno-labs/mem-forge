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
policy table. Confluence native containers and macros declare their attributes,
body shape and semantic role. Parsing, canonical material, presentation and
selection traversal consume those same declarations. CanonicalRecord schemas
and the existing format interface remain the shared compiler's only input.

Presentation containers preserve authored children and independent evidence
granularity. Layout cells bound heading interpretation to their own column.
Inline annotation identities do not replace or erase authored text. Semantic
controls retain meaning: links keep their target and supplied user identity,
colour controls remain readable, literal bodies retain whitespace, table headers
remain interpretation origins, and task completion participates in comparison.

The explicit supported Confluence additions are layout/section/cell, inline
comment markers, task lists, emoticons and local excerpt bodies. The Jira additions
cover provider table classes/wrappers, panels/noformat wrappers, mentions, font
controls and emoticon classes. This is not a claim of universal plugin grammar
support. Malformed structures and unknown semantic controls still fail explicitly.

External Confluence include, children and excerpt-include output is not present
in the existing immutable snapshot. These constructs cannot be unwrapped or
dropped and called complete Evidence. Their adapter error identifies the missing
external content. Expanding collection/dependency ownership is outside this change;
no source-body fetch is introduced during compilation or get_memory.

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
