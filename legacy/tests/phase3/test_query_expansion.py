from __future__ import annotations

from ikea_agent.phase3.query_expansion import QueryExpansionService


def test_query_expansion_auto_applies_for_constraint_query() -> None:
    service = QueryExpansionService()

    outcome = service.expand("Couch 100cm wide less than 100 euro", mode="auto")

    assert outcome.applied is True
    assert outcome.extracted_filters["width_max_cm"] == 100.0
    assert outcome.extracted_filters["max_price_eur"] == 100.0


def test_query_expansion_auto_skips_non_constraint_query() -> None:
    service = QueryExpansionService()

    outcome = service.expand("nice cozy living room decor", mode="auto")

    assert outcome.applied is False
    assert outcome.extracted_filters == {}


def test_query_expansion_off_never_applies() -> None:
    service = QueryExpansionService()

    outcome = service.expand("Sofa under 200 euro", mode="off")

    assert outcome.applied is False
    assert outcome.extracted_filters == {}
