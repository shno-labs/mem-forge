# Frozen native Evidence delivery validation

2026-10-04. Supplemental local storage/transport evidence; **not release
acceptance**. V19 semantic quality remains failed. No product code or prompt was
changed, no model was called, and no production data was written for this probe.

## Cohort and result

The untouched frozen v19 selections were restored from the experiment's
`dataclasses.asdict` export into the public typed payload codec, without changing
source text, ranges, digests, roles or origins. Authentic complete native
Confluence and Jira sources reconstructed the original projection identities.
The local visibility variants were workspace Confluence and owner-private Jira.

| Check | Evidence and boundary |
|---|---|
| Actual local lifecycle persistence | 56 Confluence and five Jira Memories, with 57 and seven supporting reference parts, written using `apply_source_projection_lifecycle` into an isolated SQLite database. Exact same-Plan retries succeeded. The complete cohort was obtained from CREATE_MEMORY mutation IDs, without paginated list sampling. |
| Full public grouped read | All 64 selected parts retained exact anchor, role, excerpt, descriptor, raw/presentation hashes and current/interpretation flags. |
| HANA grouped reader parity | Actual HANA adapter query and DTO path matched SQLite for all 61 Memories using a bridge to those local SQLite rows. This is **not physical HANA execution**, persistence or transaction evidence. |
| Actual shared HTTP routes | 186 successful reads: 61 Memory details, 64 selected-reference resources and 61 Unit resources. Detail and compact output preserved the complete Evidence after allowing only omission of the text item's optional null artifact. Reference resources identified the selected reference and contained its pinned Observation revision; reference and Unit response SHA headers matched the returned bytes. |
| Owner/nonowner checks | Ten nonowner requests for the five private Jira Memories and their Unit resources returned 404. This does not exercise a public Memory with a separately private group or source access revocation. |

The pinned-resource checks establish selected-reference/revision membership and
response integrity, not an independently asserted byte-for-byte comparison of
every returned source-material record with original native input. The original
source is parsed into authoritative Observations; these are distinct boundaries.
The probe does not evaluate whether a claim or selected Required is semantically
correct. Failed v19 candidates remain failed and exist only in the isolated DB.

## Preserved harness failures

The first four attempts are retained with scripts/logs/results, rather than
misclassified as product failures:

1. Experiment `asdict` origins were passed directly to the public wire decoder;
   its format rejection was correct. The harness now restores typed origins and
   then tests the actual public codec.
2. The harness supplied unsupported visibility arguments to low-level
   `list_memories`.
3. Its default 50-row listing was mistaken for the complete 56-row Confluence
   cohort. The harness now uses exact Lifecycle Plan creation IDs.
4. Strict detail/compact dictionary equality treated omitted `artifact:null`
   for text as loss. The saved diagnostic found this sole difference on the
   inspected item. Attempt five permits only that omission and compares every
   other Evidence field exactly across the full cohort.

Attempt five passed. These corrections modify only a private verification
script; they do not repair model selections or product data.

## Deterministic and independent evidence

The current fresh Cloud adapter, mounted-route compatibility and descriptor
parity suites passed **520 tests** in 34.96 seconds. These tests overlap older
reported counts and are not an aggregate unique-test count. They do not imply
physical HANA or CF product acceptance.

An independent audit separately exercised authentic Confluence composite
origins through both public grouped readers with supplied SQL rows, the admin
DTO and the compact function. It passed complete-role delivery, private-group
visibility, inactive historical Support, valid unavailable view/profile
handling, and corrupt Required-origin rejection. Its report identifies a
pre-existing supplied-reference-ID immutability difference (HANA UPSERT versus
SQLite first-write preservation). Ordinary content-addressed native candidates
and exact Plan retries do not naturally trigger it; it is a separate contract
gap, not evidence that this passing cohort loses references.

## Remaining boundaries

Do not mark A11/A12 completely covered. Physical HANA descriptor writes and
transaction behavior, private-group/public-Memory and source revocation HTTP
variants, stale/rollback and corruption/unavailable-view HTTP outcomes,
historical pinned-resource transitions, and UI behavior remain unverified by
this cohort. The [semantic validation](2026-10-04-claim-evidence-design-validation.md)
and [causal audit](2026-10-04-claim-evidence-causal-audit.md) remain governing
evidence for extraction quality and failure attribution.

## Artifacts

Private root:
`/Users/i551096/Downloads/MemForge-Evidence-Validation-2026-10-02/private/delivery-contract-20261004`.

- `native_roundtrip.py`, preserved attempt scripts and attempt directories.
- `attempt-5/command.json`, `native-roundtrip.log`,
  `native-roundtrip-result.json`, `hana-group-read-sql.json` and isolated DB.
- `attempt-4/compaction-difference.json`.
- `cloud-suite-command.json`, `cloud-suite.log`, `cloud-suite-result.json`.
- Independent report and probe copies, with the originals under `/tmp`.

Scripts use the fresh OSS/Cloud source paths recorded in command artifacts.
Use a fresh exclusive output directory on reproduction. No private source,
database or secret is committed with this document.
