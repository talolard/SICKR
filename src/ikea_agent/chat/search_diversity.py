"""MMR-based search diversification for chat retrieval outputs."""

from __future__ import annotations

from dataclasses import dataclass
from re import sub

from ikea_agent.retrieval.reranker import RerankedItem
from ikea_agent.shared.types import SearchResultDiversityWarning, ShortRetrievalResult

_MIN_WARNING_RESULTS = 2
_DOMINANCE_WARNING_THRESHOLD = 0.6
_FAMILY_MIN_TOKEN_LEN = 3


@dataclass(frozen=True, slots=True)
class DiversifiedSearchOutput:
    """MMR-selected result list plus optional warning metadata."""

    results: list[ShortRetrievalResult]
    warning: SearchResultDiversityWarning | None


def diversify_results(
    *,
    reranked_items: list[RerankedItem],
    similarity_lookup: dict[tuple[str, str], float],
    limit: int,
    lambda_weight: float,
    preselect_limit: int,
) -> DiversifiedSearchOutput:
    """Select a diverse subset using MMR and precomputed pair similarities."""

    if limit <= 0 or not reranked_items:
        return DiversifiedSearchOutput(results=[], warning=None)

    deduped_items = _dedupe_by_product_key(reranked_items)
    normalized_scores = _normalize_scores(deduped_items)
    top_candidates = sorted(
        deduped_items,
        key=lambda item: (-normalized_scores[item.result.canonical_product_key], item.rank_after),
    )[: max(limit, preselect_limit)]
    selected = _mmr_select(
        candidates=top_candidates,
        normalized_scores=normalized_scores,
        similarity_lookup=similarity_lookup,
        limit=limit,
        lambda_weight=lambda_weight,
    )
    selected_results = [item.result.to_short_result() for item in selected]
    return DiversifiedSearchOutput(
        results=selected_results,
        warning=_build_warning(selected_results),
    )


def _mmr_select(
    *,
    candidates: list[RerankedItem],
    normalized_scores: dict[str, float],
    similarity_lookup: dict[tuple[str, str], float],
    limit: int,
    lambda_weight: float,
) -> list[RerankedItem]:
    selected: list[RerankedItem] = []
    selected_keys: set[str] = set()

    for _ in range(limit):
        best_item: RerankedItem | None = None
        best_score = float("-inf")

        for candidate in candidates:
            candidate_key = candidate.result.canonical_product_key
            if candidate_key in selected_keys:
                continue

            redundancy = 0.0
            if selected:
                redundancy = max(
                    _pair_similarity(
                        candidate_key, existing.result.canonical_product_key, similarity_lookup
                    )
                    for existing in selected
                )

            relevance = normalized_scores.get(candidate_key, 0.0)
            mmr_score = (lambda_weight * relevance) - ((1.0 - lambda_weight) * redundancy)
            if mmr_score > best_score:
                best_item = candidate
                best_score = mmr_score

        if best_item is None:
            break
        selected.append(best_item)
        selected_keys.add(best_item.result.canonical_product_key)

    return selected


def _pair_similarity(
    source_key: str,
    neighbor_key: str,
    similarity_lookup: dict[tuple[str, str], float],
) -> float:
    direct = similarity_lookup.get((source_key, neighbor_key))
    if direct is not None:
        return direct
    reverse = similarity_lookup.get((neighbor_key, source_key))
    if reverse is not None:
        return reverse
    return 0.0


def _dedupe_by_product_key(reranked_items: list[RerankedItem]) -> list[RerankedItem]:
    seen: set[str] = set()
    deduped: list[RerankedItem] = []
    for item in reranked_items:
        key = item.result.canonical_product_key
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _normalize_scores(reranked_items: list[RerankedItem]) -> dict[str, float]:
    if not reranked_items:
        return {}

    raw_scores = [item.rerank_score for item in reranked_items]
    minimum = min(raw_scores)
    maximum = max(raw_scores)
    if maximum <= minimum:
        return {item.result.canonical_product_key: 1.0 for item in reranked_items}
    scale = maximum - minimum
    return {
        item.result.canonical_product_key: (item.rerank_score - minimum) / scale
        for item in reranked_items
    }


def _build_warning(results: list[ShortRetrievalResult]) -> SearchResultDiversityWarning | None:
    if len(results) < _MIN_WARNING_RESULTS:
        return None
    families = [_family_key(item) for item in results]
    dominant_family = max(families, key=families.count)
    dominant_count = families.count(dominant_family)
    dominant_share = dominant_count / len(results)
    if dominant_share < _DOMINANCE_WARNING_THRESHOLD:
        return None
    return SearchResultDiversityWarning(
        kind="high_family_concentration",
        message=(
            f"Search results are concentrated in family '{dominant_family}' "
            f"({dominant_count}/{len(results)}). Consider refining query terms or filters."
        ),
        dominant_family=dominant_family,
        dominant_share=dominant_share,
        analyzed_result_count=len(results),
    )


def _family_key(result: ShortRetrievalResult) -> str:
    tokens = _tokens(
        " ".join([result.product_name, result.product_type or "", result.description_text or ""])
    )
    for token in tokens:
        if len(token) >= _FAMILY_MIN_TOKEN_LEN:
            return token
    return result.product_id.split("-", maxsplit=1)[0].lower()


def _tokens(text: str) -> list[str]:
    cleaned = sub(r"[^a-z0-9]+", " ", text.lower())
    return [token for token in cleaned.split() if token]
