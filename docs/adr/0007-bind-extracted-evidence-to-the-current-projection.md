# Bind extracted evidence to the current Source Projection

Extractor-provided Source Observation identities are localization hints, not evidence authority. The current Source Projection and its revision-pinned content are authoritative. A hint outside the changed evidence scope may be rebound only when the extracted quote has exactly one exact match in the current candidate Observations; missing or ambiguous matches fail closed.

This rule lives in the shared evidence-localization module and does not branch on provider type. Valid in-scope hints must still contain the quote, and revalidated no-op evidence retains its explicit current-revision validation. The same contract therefore applies to document-based and conversational sources without weakening changed-scope ownership.
