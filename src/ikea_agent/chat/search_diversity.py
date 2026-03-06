"""Helpers to diversify repetitive retrieval outputs for agent tool responses."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from re import sub

from ikea_agent.shared.types import SearchResultDiversityWarning, ShortRetrievalResult

_FAMILY_MIN_TOKEN_LEN = 3
_MIN_WARNING_RESULTS = 2
_DOMINANCE_WARNING_THRESHOLD = 0.6


@dataclass(frozen=True, slots=True)
class DiversifiedSearchOutput:
    """Diversified result list plus optional warning metadata."""

    results: list[ShortRetrievalResult]
    warning: SearchResultDiversityWarning | None


def diversify_results(
    *,
    results: list[ShortRetrievalResult],
    limit: int,
) -> DiversifiedSearchOutput:
    """Round-robin families so one product line does not dominate top output."""

    if limit <= 0 or not results:
        return DiversifiedSearchOutput(results=[], warning=None)

    deduped_results = _dedupe_by_product_id(results)
    grouped = _group_by_family(deduped_results)
    interleaved = _round_robin_groups(grouped)
    selected = interleaved[:limit]
    warning = _build_warning(deduped_results)
    return DiversifiedSearchOutput(results=selected, warning=warning)


def _dedupe_by_product_id(results: list[ShortRetrievalResult]) -> list[ShortRetrievalResult]:
    seen: set[str] = set()
    deduped: list[ShortRetrievalResult] = []
    for item in results:
        if item.product_id in seen:
            continue
        seen.add(item.product_id)
        deduped.append(item)
    return deduped


def _group_by_family(results: list[ShortRetrievalResult]) -> list[list[ShortRetrievalResult]]:
    grouped: dict[str, list[ShortRetrievalResult]] = defaultdict(list)
    for item in results:
        grouped[_family_key(item)].append(item)
    return sorted(grouped.values(), key=len, reverse=True)


def _round_robin_groups(groups: list[list[ShortRetrievalResult]]) -> list[ShortRetrievalResult]:
    output: list[ShortRetrievalResult] = []
    index = 0
    while True:
        added_any = False
        for group in groups:
            if index < len(group):
                output.append(group[index])
                added_any = True
        if not added_any:
            break
        index += 1
    return output


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
