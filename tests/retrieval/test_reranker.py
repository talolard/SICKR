from __future__ import annotations

import pytest

from ikea_agent.config import AppSettings
from ikea_agent.retrieval.reranker import LexicalReranker, TransformerReranker
from ikea_agent.shared.types import RetrievalResult


def _sample_result(
    *,
    product_id: str,
    product_name: str,
    description_text: str,
    semantic_score: float,
) -> RetrievalResult:
    return RetrievalResult(
        canonical_product_key=product_id,
        product_name=product_name,
        product_type="storage",
        description_text=description_text,
        embedding_text=None,
        main_category="storage",
        sub_category="wardrobes",
        dimensions_text=None,
        width_cm=None,
        depth_cm=None,
        height_cm=None,
        price_eur=199.0,
        url=None,
        semantic_score=semantic_score,
        filter_pass_reasons=("ok",),
        rank_explanation="semantic_score",
    )


def test_lexical_reranker_promotes_token_overlap() -> None:
    reranker = LexicalReranker()
    results = [
        _sample_result(
            product_id="cabinet",
            product_name="BILLY cabinet",
            description_text="Tall cabinet for storage",
            semantic_score=0.4,
        ),
        _sample_result(
            product_id="chair",
            product_name="POANG chair",
            description_text="Reading chair",
            semantic_score=0.9,
        ),
    ]

    reranked = reranker.rerank("storage cabinet", results)

    assert reranked[0].result.canonical_product_key == "cabinet"
    assert reranked[0].rank_after == 1


def test_transformer_reranker_fails_fast_when_optional_deps_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_import_error(_name: str) -> object:
        raise ImportError("missing optional dependency")

    monkeypatch.setattr("ikea_agent.retrieval.reranker.import_module", _raise_import_error)

    with pytest.raises(RuntimeError, match="RERANK_BACKEND=lexical"):
        TransformerReranker(AppSettings())
