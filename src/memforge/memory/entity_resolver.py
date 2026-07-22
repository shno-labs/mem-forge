"""Bounded batch resolution of extracted entity mentions."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from math import sqrt
from time import perf_counter
from typing import Any

from memforge.models import Entity, EntityAlias, canonicalize_entity_name
from memforge.storage.adapters.protocols import EntityResolutionContext, RelationalStore

logger = logging.getLogger(__name__)

__all__ = [
    "EntityResolutionBatch",
    "EntityResolutionContext",
    "EntityResolutionMetrics",
    "EntityResolver",
    "validate_alias",
]


@dataclass(frozen=True, slots=True)
class EntityResolutionMetrics:
    unique_mentions: int
    exact_hits: int
    alias_hits: int
    embedded_mentions: int
    ambiguous_mentions: int
    embedding_batches: int
    structured_llm_calls: int
    candidate_count: int
    new_entities: int
    elapsed_ms: int


@dataclass(frozen=True, slots=True)
class EntityResolutionBatch:
    """Resolved canonical IDs plus content-free batch metrics."""

    ids_by_canonical_name: Mapping[str, int]
    metrics: EntityResolutionMetrics

    def entity_id(self, mention: str) -> int | None:
        return self.ids_by_canonical_name.get(canonicalize_entity_name(mention))


def validate_alias(alias_name: str, canonical_name: str) -> bool:
    """Return whether two spellings have a deterministic lexical resemblance."""

    alias = canonicalize_entity_name(alias_name)
    canonical = canonicalize_entity_name(canonical_name)
    if not alias or not canonical:
        return False
    alias_tokens = set(alias.split())
    canonical_tokens = set(canonical.split())
    return bool(
        alias_tokens & canonical_tokens
        or alias in canonical
        or canonical in alias
        or SequenceMatcher(None, alias, canonical).ratio() >= 0.5
    )


_ENTITY_BATCH_PROMPT = """Resolve each entity mention against only its supplied candidates.

Mentions and candidate IDs:
{cases_json}

Document context:
{context}

Return one decision for every mention. matched_id must be one supplied candidate
ID or null. Related, parent/child, or same-category entities are not identical.
Return only the structured response."""


class EntityResolver:
    """Own bounded entity recall, ambiguity proof, alias learning, and creation."""

    def __init__(
        self,
        store: RelationalStore,
        embed_cfg: dict | None = None,
        structured_llm_client: Any = None,
        llm_model: str = "claude-sonnet-4-20250514",
        embedding_threshold: float = 0.6,
        candidate_limit: int = 10,
        confidence_threshold: float = 0.9,
    ) -> None:
        self.store = store
        self.embed_cfg = embed_cfg
        self.structured_llm_client = structured_llm_client
        self.llm_model = llm_model
        self.embedding_threshold = embedding_threshold
        self.candidate_limit = candidate_limit
        self.confidence_threshold = confidence_threshold
        self._last_metrics: EntityResolutionMetrics | None = None

    @property
    def stats(self) -> dict[str, int]:
        """Return the latest batch metrics for existing observability callers."""

        metrics = self._last_metrics
        if metrics is None:
            return {}
        return {
            "unique_mentions": metrics.unique_mentions,
            "exact_match": metrics.exact_hits,
            "alias_match": metrics.alias_hits,
            "embedded_mentions": metrics.embedded_mentions,
            "ambiguous_mentions": metrics.ambiguous_mentions,
            "embedding_batches": metrics.embedding_batches,
            "structured_llm_calls": metrics.structured_llm_calls,
            "candidate_count": metrics.candidate_count,
            "new_entity": metrics.new_entities,
            "total_resolved": metrics.unique_mentions,
            "elapsed_ms": metrics.elapsed_ms,
        }

    async def resolve_many(
        self,
        mentions: Sequence[str],
        *,
        doc_context: str | None = None,
    ) -> EntityResolutionBatch:
        """Resolve distinct mentions with bounded storage and model batches."""

        started = perf_counter()
        display_by_canonical: dict[str, str] = {}
        for mention in mentions:
            canonical = canonicalize_entity_name(mention)
            if canonical:
                display_by_canonical.setdefault(canonical, mention.strip() or canonical)
        canonical_names = tuple(display_by_canonical)
        if not canonical_names:
            return self._finish_batch(started=started, resolved={})

        context = await self.store.load_entity_resolution_context(
            canonical_names,
            candidate_limit=self.candidate_limit,
        )
        resolved: dict[str, int] = {
            canonical: entity.id
            for canonical, entity in context.exact_matches.items()
            if canonical in display_by_canonical
        }
        exact_hits = len(resolved)
        alias_hits = 0
        for canonical, alias in context.alias_matches.items():
            if canonical in display_by_canonical and canonical not in resolved:
                resolved[canonical] = alias.canonical_id
                alias_hits += 1

        unresolved = tuple(canonical for canonical in canonical_names if canonical not in resolved)
        recalled: dict[str, tuple[Entity, ...]] = {
            canonical: tuple(context.candidates.get(canonical, ()))
            for canonical in unresolved
        }
        candidate_count = sum(len(items) for items in recalled.values())
        embedded_mentions = 0
        embedding_batches = 0
        ambiguous: dict[str, tuple[Entity, ...]] = {}
        if unresolved and self.embed_cfg:
            unique_candidate_names = tuple(
                dict.fromkeys(
                    candidate.canonical_name
                    for canonical in unresolved
                    for candidate in recalled[canonical]
                )
            )
            texts = [*unresolved, *unique_candidate_names]
            if texts:
                from memforge.retrieval.embeddings import embed_texts

                vectors = await asyncio.to_thread(
                    embed_texts,
                    texts,
                    self.embed_cfg["base_url"],
                    self.embed_cfg["api_key"],
                    self.embed_cfg["model"],
                )
                embedding_batches = 1
                embedded_mentions = len(unresolved)
                vectors_by_text = dict(zip(texts, vectors, strict=True))
                for canonical in unresolved:
                    candidates = tuple(
                        candidate
                        for candidate in recalled[canonical]
                        if _cosine(
                            vectors_by_text[canonical],
                            vectors_by_text[candidate.canonical_name],
                        )
                        >= self.embedding_threshold
                    )
                    if candidates:
                        ambiguous[canonical] = candidates

        structured_llm_calls = 0
        learned_aliases: list[EntityAlias] = []
        if ambiguous and self.structured_llm_client is not None:
            cases = [
                {
                    "mention": mention,
                    "candidates": [
                        {"id": candidate.id, "name": candidate.canonical_name}
                        for candidate in candidates
                    ],
                }
                for mention, candidates in ambiguous.items()
            ]
            response = await self.structured_llm_client.validate_entity_batch(
                _ENTITY_BATCH_PROMPT.format(
                    cases_json=json.dumps(cases, ensure_ascii=False, sort_keys=True),
                    context=(doc_context or "")[:2000],
                ),
                max_tokens=max(512, min(4096, len(cases) * 256)),
                model=self.llm_model,
            )
            structured_llm_calls = 1
            decisions: dict[str, object] = {}
            duplicates: set[str] = set()
            for decision in response.decisions:
                mention = canonicalize_entity_name(decision.mention)
                if mention in decisions:
                    duplicates.add(mention)
                decisions[mention] = decision
            for mention, candidates in ambiguous.items():
                decision = decisions.get(mention)
                if decision is None or mention in duplicates:
                    continue
                candidate_ids = {candidate.id for candidate in candidates}
                matched_id = getattr(decision, "matched_id", None)
                confidence = float(getattr(decision, "confidence", 0.0))
                if matched_id not in candidate_ids or confidence < self.confidence_threshold:
                    continue
                resolved[mention] = int(matched_id)
                learned_aliases.append(
                    EntityAlias(
                        alias=display_by_canonical[mention],
                        alias_normalized=mention,
                        canonical_id=int(matched_id),
                        source="resolver_confirmed",
                    )
                )

        new_names = tuple(canonical for canonical in unresolved if canonical not in resolved)
        if new_names:
            created = await self.store.upsert_entities(
                tuple((canonical, display_by_canonical[canonical]) for canonical in new_names)
            )
            missing = set(new_names).difference(created)
            if missing:
                raise RuntimeError(f"entity batch upsert omitted canonical names: {sorted(missing)}")
            resolved.update({canonical: int(created[canonical]) for canonical in new_names})
        if learned_aliases:
            await self.store.insert_aliases(tuple(learned_aliases))

        return self._finish_batch(
            started=started,
            resolved=resolved,
            exact_hits=exact_hits,
            alias_hits=alias_hits,
            embedded_mentions=embedded_mentions,
            ambiguous_mentions=len(ambiguous),
            embedding_batches=embedding_batches,
            structured_llm_calls=structured_llm_calls,
            candidate_count=candidate_count,
            new_entities=len(new_names),
        )

    async def resolve(
        self,
        extracted_name: str,
        *,
        doc_context: str | None = None,
    ) -> int:
        """Resolve one mention through the same batch contract."""

        result = await self.resolve_many((extracted_name,), doc_context=doc_context)
        entity_id = result.entity_id(extracted_name)
        if entity_id is None:
            raise RuntimeError("entity resolution produced no ID")
        return entity_id

    def _finish_batch(
        self,
        *,
        started: float,
        resolved: Mapping[str, int],
        exact_hits: int = 0,
        alias_hits: int = 0,
        embedded_mentions: int = 0,
        ambiguous_mentions: int = 0,
        embedding_batches: int = 0,
        structured_llm_calls: int = 0,
        candidate_count: int = 0,
        new_entities: int = 0,
    ) -> EntityResolutionBatch:
        metrics = EntityResolutionMetrics(
            unique_mentions=len(resolved),
            exact_hits=exact_hits,
            alias_hits=alias_hits,
            embedded_mentions=embedded_mentions,
            ambiguous_mentions=ambiguous_mentions,
            embedding_batches=embedding_batches,
            structured_llm_calls=structured_llm_calls,
            candidate_count=candidate_count,
            new_entities=new_entities,
            elapsed_ms=max(0, round((perf_counter() - started) * 1000)),
        )
        self._last_metrics = metrics
        logger.info(
            "entity_resolution_batch unique=%d exact=%d alias=%d embedded=%d "
            "ambiguous=%d candidates=%d embedding_batches=%d llm_calls=%d new=%d elapsed_ms=%d",
            metrics.unique_mentions,
            metrics.exact_hits,
            metrics.alias_hits,
            metrics.embedded_mentions,
            metrics.ambiguous_mentions,
            metrics.candidate_count,
            metrics.embedding_batches,
            metrics.structured_llm_calls,
            metrics.new_entities,
            metrics.elapsed_ms,
        )
        return EntityResolutionBatch(dict(resolved), metrics)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(left, right, strict=True))
    left_norm = sqrt(sum(float(value) ** 2 for value in left))
    right_norm = sqrt(sum(float(value) ** 2 for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)
