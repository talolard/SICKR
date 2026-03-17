"""Typed reranker backends with explicit factory selection."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Literal, Protocol, overload

from ikea_agent.config import AppSettings
from ikea_agent.shared.types import RetrievalResult


@dataclass(frozen=True, slots=True)
class RerankedItem:
    """One item with before/after rank metadata."""

    result: RetrievalResult
    rank_before: int
    rank_after: int
    rerank_score: float


class Reranker(Protocol):
    """Typed reranker protocol used by chat graph runtime."""

    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[RerankedItem]:
        """Return reordered items with before/after metadata."""


class IdentityReranker:
    """No-op reranker preserving semantic candidate order."""

    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[RerankedItem]:
        """Return identity-ranked items with original semantic order."""

        _ = query_text
        return [
            RerankedItem(
                result=item,
                rank_before=index + 1,
                rank_after=index + 1,
                rerank_score=item.semantic_score,
            )
            for index, item in enumerate(results)
        ]


class LexicalReranker:
    """Token-overlap reranker that combines lexical and semantic signals."""

    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[RerankedItem]:
        """Return reranked items using lexical token overlap scoring."""

        scores = _lexical_scores(query_text, results)
        return _build_reranked_items(results=results, scores=scores)


class TransformerReranker:
    """Cross-encoder reranker for explicit transformer-backed installs."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        _require_transformer_dependencies()

    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[RerankedItem]:
        """Return reranked items using the configured cross-encoder model."""

        scores = _transformer_scores(
            query_text=query_text, results=results, settings=self._settings
        )
        return _build_reranked_items(results=results, scores=scores)


RerankerBackend = Literal["identity", "lexical", "transformer"]


@overload
def get_reranker(backend: Literal["identity"], settings: AppSettings) -> IdentityReranker: ...


@overload
def get_reranker(backend: Literal["lexical"], settings: AppSettings) -> LexicalReranker: ...


@overload
def get_reranker(backend: Literal["transformer"], settings: AppSettings) -> TransformerReranker: ...


def get_reranker(backend: RerankerBackend, settings: AppSettings) -> Reranker:
    """Return explicit reranker backend instance for the selected literal."""

    if backend == "identity":
        return IdentityReranker()
    if backend == "lexical":
        return LexicalReranker()
    return TransformerReranker(settings)


def _build_reranked_items(
    *, results: list[RetrievalResult], scores: list[float]
) -> list[RerankedItem]:
    scored = list(enumerate(results))
    scored.sort(
        key=lambda item: (
            -scores[item[0]],
            -item[1].semantic_score,
            item[1].canonical_product_key,
        )
    )
    reranked_results = [item[1] for item in scored]
    score_map = {item.canonical_product_key: scores[idx] for idx, item in enumerate(results)}
    return [
        RerankedItem(
            result=result,
            rank_before=_rank_of(results, result.canonical_product_key),
            rank_after=index + 1,
            rerank_score=score_map.get(result.canonical_product_key, 0.0),
        )
        for index, result in enumerate(reranked_results)
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


def _transformer_scores(
    *,
    query_text: str,
    results: list[RetrievalResult],
    settings: AppSettings,
) -> list[float]:
    torch_mod, transformers_mod = _require_transformer_dependencies()

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


def _require_transformer_dependencies() -> tuple[Any, Any]:
    """Fail fast when transformer reranking is selected without optional deps."""

    try:
        torch_mod = import_module("torch")
        transformers_mod = import_module("transformers")
    except Exception as exc:
        raise RuntimeError(
            "Transformer reranker requires optional `torch` and `transformers` "
            "dependencies. Install them or set RERANK_BACKEND=lexical."
        ) from exc
    return torch_mod, transformers_mod


def _tokens(text: str) -> list[str]:
    return [token.strip().lower() for token in text.split() if token.strip()]


def _rank_of(results: list[RetrievalResult], canonical_product_key: str) -> int:
    for index, item in enumerate(results):
        if item.canonical_product_key == canonical_product_key:
            return index + 1
    return len(results) + 1
