from __future__ import annotations

from ikea_agent.shared.types import PriceFilterEUR, RetrievalFilters, RetrievalRequest


def test_smoke_import_and_type_contract() -> None:
    request = RetrievalRequest(
        query_text="black picture frame",
        result_limit=10,
        filters=RetrievalFilters(price=PriceFilterEUR(min_eur=5.0, max_eur=20.0)),
    )

    assert request.result_limit == 10
    assert request.filters.price.min_eur == 5.0
