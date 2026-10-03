"""Canonical semantic contract shared by Memory extraction entrypoints."""

from __future__ import annotations

from memforge.pipeline.memory_value import MEMORY_VALUE_DEFINITION

__all__ = [
    "CONTRACT_SUPERSEDED",
    "DURABLE_MEMORY_QUALITY_RULES",
    "MEMORY_CLAIM_EVIDENCE_RULES",
    "PROJECTION_EXTRACTION_CONTRACT_VERSION",
    "PROJECTION_FRAGMENT_MODEL_PRESENTATION_POLICY_VERSION",
]


# Recorded on every Source derivation and hashed into its batch identities.
# Stored derivations with any other value are superseded, never resumed.
PROJECTION_EXTRACTION_CONTRACT_VERSION = "projection-extraction-v14"
PROJECTION_FRAGMENT_MODEL_PRESENTATION_POLICY_VERSION = 6
CONTRACT_SUPERSEDED = "CONTRACT_SUPERSEDED"


MEMORY_CLAIM_EVIDENCE_RULES = """Choose one eligible authentic readable Primary directly supporting the central conclusion. Read the authorized source and its supplied interpretation to determine the claim; Primary need not alone prove every clause. Prefer an equally complete focused view when available. A broader original view is valid when that alternative is unavailable.

Write one independently useful final claim with its governing scope, conditions, exceptions, branch precedence, order and modality. Preserve explicitly authored amendments, supersession and historical boundaries. Presented current refs do not imply every authored statement remains current. Preserve source uncertainty without inventing a resolution. A connected procedure or inseparable decision/reason may remain one claim; independently changing conclusions belong in separate Memories. Another Memory or additional citation cannot supply a qualification missing from this claim's content.

Assign valid_from/valid_until only from an authored effective boundary for the whole claim. Proposal, report, update and observed-event dates belong in content when useful; otherwise use null. A date for one clause does not date independently changing clauses.

After final content and metadata are settled within this same response, select Required for confident additional contribution beyond Primary, other selected refs and source-proven interpretation already included in the view. Another occurrence, a containing alternative or an already included heading is not automatically additional contribution. Outside conditions, branches and definitions may contribute. Eligibility permits selection; it does not oblige selection. Empty required_refs is valid. Related-ref recall is best effort: retain actual qualifiers in content even when an additional citation is omitted. No smallest-set requirement or ref-count target applies. Keep useful supported conclusions instead of dropping knowledge to reduce citation counts.

"""


DURABLE_MEMORY_QUALITY_RULES = MEMORY_VALUE_DEFINITION + """

ONE CLAIM, ONE MEMORY. Preserve each independently useful conclusion without reworded duplicates. Fold a rejected alternative into the chosen decision when it explains that same decision.

NO META-MEMORIES. Preserve durable system/domain knowledge rather than commit structure, diff splitting, tool use, validation output or whether a project rule was followed.

OWNED EVIDENCE SETS THE LANGUAGE. For each candidate, preserve the language of its owned source evidence. When that evidence is primarily Chinese, write memory.content in Chinese. Do not translate it to English unless the evidence itself is English or mixed-language phrasing is necessary to preserve exact technical identifiers. Read-only context may resolve meaning but must not change the candidate's language.

OPERATIONAL DOES NOT MEAN TRANSIENT. Keep an explicitly stated, repeatable procedure when it remains useful beyond the immediate event. Skip one-off observations, current status, and instance-specific details that establish no lasting knowledge.

"""
