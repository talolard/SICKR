"""Local reranking with lexical baseline and optional transformer backend."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.shared.types import RetrievalResult


@dataclass(frozen=True, slots=True)
class RerankedItem:
    """One item with before/after rank metadata."""

    result: RetrievalResult
    rank_before: int
    rank_after: int
    rerank_score: float


class RerankerService:
    """Rerank top retrieval candidates using a local backend."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[RerankedItem]:
        """Return reordered items with before/after metadata."""

        if not self._settings.rerank_enabled:
            return _identity_ranking(results)
        candidate_limit = min(self._settings.rerank_candidate_limit, len(results))
        candidates = results[:candidate_limit]
        remainder = results[candidate_limit:]

        backend = self._settings.rerank_backend
        if backend == "transformer":
            scores = _transformer_scores(query_text, candidates)
        else:
            scores = _lexical_scores(query_text, candidates)

        scored = list(enumerate(candidates))
        scored.sort(
            key=lambda item: (
                -scores[item[0]],
                -item[1].semantic_score,
                item[1].canonical_product_key,
            )
        )

        reranked_results = [item[1] for item in scored]
        reranked_results.extend(remainder)
        score_map = {item.canonical_product_key: scores[idx] for idx, item in enumerate(candidates)}
        return [
            RerankedItem(
                result=result,
                rank_before=_rank_of(results, result.canonical_product_key),
                rank_after=index + 1,
                rerank_score=score_map.get(result.canonical_product_key, 0.0),
            )
            for index, result in enumerate(reranked_results)
        ]


def _identity_ranking(results: list[RetrievalResult]) -> list[RerankedItem]:
    return [
        RerankedItem(
            result=item,
            rank_before=index + 1,
            rank_after=index + 1,
            rerank_score=item.semantic_score,
        )
        for index, item in enumerate(results)
    ]


def _lexical_scores(query_text: str, results: list[RetrievalResult]) -> list[float]:
    query_tokens = set(_tokens(query_text))
    values: list[float] = []
    for item in results:
        item_tokens = set(
            _tokens(
                " ".join(
                    [
                        item.product_name,
                        item.product_type or "",
                        item.description_text or "",
                        item.main_category or "",
                        item.sub_category or "",
                    ]
                )
            )
        )
        overlap = len(query_tokens & item_tokens)
        denominator = max(1, len(query_tokens))
        lexical_score = overlap / denominator
        values.append((0.7 * lexical_score) + (0.3 * item.semantic_score))
    return values


def _transformer_scores(query_text: str, results: list[RetrievalResult]) -> list[float]:
    try:
        torch_mod = import_module("torch")
        transformers_mod = import_module("transformers")
    except Exception:
        return _lexical_scores(query_text, results)

    settings = get_settings()
    device = "mps" if torch_mod.backends.mps.is_available() else "cpu"
    tokenizer = transformers_mod.AutoTokenizer.from_pretrained(settings.rerank_model_name)
    model = transformers_mod.AutoModelForSequenceClassification.from_pretrained(
        settings.rerank_model_name
    )
    model.to(device)
    model.eval()

    pairs = [
        [
            query_text,
            " ".join(
                [
                    item.product_name,
                    item.product_type or "",
                    item.description_text or "",
                    item.main_category or "",
                ]
            ),
        ]
        for item in results
    ]
    tokenized: dict[str, Any] = tokenizer(pairs, padding=True, truncation=True, return_tensors="pt")
    tokenized = {key: value.to(device) for key, value in tokenized.items()}
    with torch_mod.no_grad():
        logits = model(**tokenized).logits.squeeze(-1)
    return [float(score) for score in logits.detach().cpu().tolist()]


def _tokens(text: str) -> list[str]:
    return [token.strip().lower() for token in text.split() if token.strip()]


def _rank_of(results: list[RetrievalResult], canonical_product_key: str) -> int:
    for index, item in enumerate(results):
        if item.canonical_product_key == canonical_product_key:
            return index + 1
    return len(results) + 1
