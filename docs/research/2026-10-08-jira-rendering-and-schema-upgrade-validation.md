# Jira rendered Evidence and representation-upgrade validation

## Contract and cause

The bounded failed source run contained 112 documents: 93 failed because the
Jira adapter rejected provider-rendered HTML, and 19 failed when new-work planning
compared registered schema-v1 Markdown fields with schema-v4 rendered HTML.
Both failures belong to shared OSS behavior, not the HANA adapter or model output.

The repair keeps provider syntax in the Jira adapter. Explicitly declared layout
decoration leaves authored content intact; issue/attachment/user identities,
literal code, formatting and citation structure remain semantic
material. Unknown semantic controls, malformed structure and unsupported CSS
remain explicit failures. No issue-specific branch, model repair or Cloud shim
is introduced.

The planner compares narrow field ranges only within one registered profile.
A representation upgrade authorizes the current Observation for fresh reading.
It does not pretend incompatible formats have exact correspondence. Historical
Evidence is immutable, whole-Support assessment remains independent, and the next
same-profile revision returns to incremental authority. Authority policy 8
invalidates older unapplied execution work through the existing work identity.
See [ADR0047](../adr/0047-define-claim-evidence-extraction-outcomes.md) and
[adapter semantics](../design/evidence-adapter-semantics.md).

## Acceptance evidence before deployment

- The anonymized regressions reproduce all seven original error families.
  The legacy-schema regression produced `CANONICAL_FIELD_MAPPING_INVALID` before
  the repair and now verifies current reading, non-exact historical Support,
  and narrow authority on the subsequent same-profile change.
- The frozen cohort contains 112 actual Jira responses and 486 separately
  collected comments. Every provider issue response's comment total equals the
  collected count; none of its changelogs is truncated. The 598 nonempty rendered
  description/comment fields all parse after the repair.
- Real input replay through projection, fragment construction and text-view
  integrity checking produces 21,998 fragments without fragment-index errors.
- All 31 saved historical revisions for the 19 mapping failures pass a
  controlled legacy-to-current planning harness. It retains the original
  Observation/Revision identity and content, but uses synthetic aggregate Unit
  membership for the test; this is not a replay of stored Unit lifecycle history.
  Its 323 historical Support parts are never classified `EXACT_UNCHANGED`
  across the incompatible profiles.
- Differential comparison against the immutable pre-change parser at
  `c35a7eaf` covers 406 previously accepted inputs from the actual cohort and
  existing test literals. Their fragments, coordinates, comparison values,
  presentations, origins and groups are unchanged.
- The Jira-specific suite passes 48 tests. The focused projection, Evidence,
  authority, reading and assessment suites also pass. Runtime deployment and
  source retry results are recorded separately in the Cloud handoff.

Private provider snapshots and the replay harness are retained locally in
`~/Downloads/MemForge-Jira-Failures-2026-10-08/` with restrictive file permissions;
they are excluded from Git. These are provider re-fetches after the failed run,
not a claim that its original response bytes or a live model verdict were saved.

## Deployment acceptance boundary

The proof above is deterministic adapter and planner validation. Deployment
acceptance must additionally attest the pinned OSS package, retry the failed
source through the normal sync path, and inspect its bounded new run/derivation
outcomes and current Support lineage. Keep historical failed jobs and Evidence.
Do not clear errors or rewrite provenance merely to make the UI green.


## Provider formatting correction

A further native/rendered corpus check found 28 `<ins>` nodes; 20 exactly match
native Jira `+text+` spans and none came from authored `<ins>` HTML. Rendering
these as `[inserted: …]` introduced an event meaning that the Jira source does
not assert. Generic HTML element semantics were insufficient for this provider.
The public Jira renderer help endpoint required authentication during this
check; the paired native/rendered provider snapshots are the concrete evidence.

The same corpus contains 62 `<del>` nodes, including ten exact native `-text-`
pairs. These denote strikethrough, not a deletion event.

The correction is source-owned: format 2 normalizes parsed `<ins>` to underline
and strikethrough tags to a formatting node with `[struck through: …]` text
while preserving coordinates and authored children. New issue/comment schema 5
uses it; historical schemas 2–4 keep format 1, and changelog schema 4 stays
unchanged. Existing incompatible-profile planning and Support assessment apply,
with subsequent same-profile changes remaining incremental. No historical
Evidence is rewritten and no additional lifecycle state is introduced.

Verification includes paragraph, standalone text and table/header origins;
schema 4-to-5 non-exact Support and schema 5-to-5 exact correspondence for
unchanged content. Differential replay against the deployed `d8f2d264` parser
covers all 598 real rendered fields with zero changes to format-1 output.
The legacy-to-current corpus replay remains the same controlled harness, not a
claim that stored lifecycle history has been reconstructed.

The final focused adapter, projection-store, native-semantics and text-view
suites pass 270 tests (55 Jira-specific). Current replay of all 598 rendered
fields emits no invented insertion/deletion labels; registered format-1 output
continues to match the deployed parser exactly. Standards and Spec reviews find
no remaining blocking issues in this versioned correction.
