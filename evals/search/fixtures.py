"""Seeded search results for second-step search-agent evals."""

from __future__ import annotations

from dataclasses import dataclass

from ikea_agent.shared.types import ShortRetrievalResult


def _result(
    *,
    product_id: str,
    product_name: str,
    description_text: str,
    product_type: str = "Furniture",
    main_category: str = "general",
    sub_category: str = "general",
    width_cm: float | None = None,
    depth_cm: float | None = None,
    height_cm: float | None = None,
    price_eur: float | None = None,
) -> ShortRetrievalResult:
    return ShortRetrievalResult(
        product_id=product_id,
        product_name=product_name,
        product_type=product_type,
        description_text=description_text,
        main_category=main_category,
        sub_category=sub_category,
        width_cm=width_cm,
        depth_cm=depth_cm,
        height_cm=height_cm,
        price_eur=price_eur,
    )


@dataclass(frozen=True, slots=True)
class SearchEvalQueryOverride:
    """Specific seeded results for queries that mention certain terms."""

    query_terms: tuple[str, ...]
    results: tuple[ShortRetrievalResult, ...]

    def matches(self, semantic_query: str) -> bool:
        """Return True when the semantic query should use this override result set."""

        normalized_query = semantic_query.lower()
        return any(term.lower() in normalized_query for term in self.query_terms)


@dataclass(frozen=True, slots=True)
class SearchEvalFixture:
    """Fixture-backed search results for bundle-stage eval cases."""

    name: str
    description: str
    default_results: tuple[ShortRetrievalResult, ...] = ()
    query_overrides: tuple[SearchEvalQueryOverride, ...] = ()

    def resolve_results(self, semantic_query: str) -> list[ShortRetrievalResult]:
        """Return seeded results for one semantic query."""

        for override in self.query_overrides:
            if override.matches(semantic_query):
                return list(override.results)
        return list(self.default_results)


SEARCH_EVAL_FIXTURES: dict[str, SearchEvalFixture] = {
    "gallery_wall_bundle_seed": SearchEvalFixture(
        name="gallery_wall_bundle_seed",
        description=(
            "Fixture distilled from the existing rental-gallery-wall search scenario so "
            "the eval can exercise `propose_bundle` after retrieval."
        ),
        default_results=(
            _result(
                product_id="gallery-frame-1",
                product_name="LUSTIGT frame set",
                description_text="Photo frame set for a mixed gallery wall display.",
                product_type="Decoration",
                main_category="decoration",
                sub_category="frames",
                price_eur=29.99,
            ),
            _result(
                product_id="gallery-shelf-1",
                product_name="MOSSLANDA picture ledge",
                description_text="Shallow wall ledge suited to photos and small decor.",
                product_type="Storage",
                main_category="storage",
                sub_category="wall_shelf",
                width_cm=55.0,
                depth_cm=12.0,
                height_cm=7.0,
                price_eur=14.99,
            ),
            _result(
                product_id="gallery-clock-1",
                product_name="PLUGGIS wall clock",
                description_text="Compact decorative wall clock to break up a photo display.",
                product_type="Decoration",
                main_category="decoration",
                sub_category="clock",
                price_eur=19.99,
            ),
            _result(
                product_id="gallery-adhesive-1",
                product_name="Damage-free mounting strips",
                description_text="High-strength adhesive mounting strips for renter-safe installs.",
                product_type="Accessories",
                main_category="organizers",
                sub_category="mounting",
                price_eur=7.99,
            ),
        ),
    ),
    "hallway_complementary_seed": SearchEvalFixture(
        name="hallway_complementary_seed",
        description=(
            "Fixture grounded in thread agent_search-286fe4b8, with portable lights and "
            "supporting products such as floating shelves, adhesive mounts, and a narrow "
            "console table."
        ),
        default_results=(
            _result(
                product_id="hall-lamp-1",
                product_name="LÄNSPORT portable lamp",
                description_text="Battery-powered portable lamp for shelf or ledge placement.",
                product_type="Lighting",
                main_category="lighting",
                sub_category="portable_lamp",
                price_eur=17.99,
            ),
            _result(
                product_id="hall-lamp-2",
                product_name="NÖDMAST portable lamp",
                description_text="Portable accent lamp that works without wall wiring.",
                product_type="Lighting",
                main_category="lighting",
                sub_category="portable_lamp",
                price_eur=14.99,
            ),
            _result(
                product_id="hall-shelf-1",
                product_name="BERGSHULT floating shelf",
                description_text="Narrow floating shelf suitable for a hallway wall.",
                product_type="Storage",
                main_category="storage",
                sub_category="wall_shelf",
                width_cm=80.0,
                depth_cm=20.0,
                height_cm=3.0,
                price_eur=24.99,
            ),
            _result(
                product_id="hall-console-1",
                product_name="TORNBY narrow console table",
                description_text=(
                    "Slim hallway console table for surfaces where drilling is not ideal."
                ),
                product_type="Furniture",
                main_category="living_room",
                sub_category="console_table",
                width_cm=90.0,
                depth_cm=24.0,
                height_cm=75.0,
                price_eur=59.99,
            ),
            _result(
                product_id="hall-adhesive-1",
                product_name="Damage-free adhesive strips",
                description_text="Adhesive mounting strips for lighter wall accessories.",
                product_type="Accessories",
                main_category="organizers",
                sub_category="mounting",
                price_eur=8.99,
            ),
        ),
    ),
    "unsupported_no_match": SearchEvalFixture(
        name="unsupported_no_match",
        description=(
            "Deliberately empty results for requests that the current catalog cannot satisfy, "
            "used to assert that the agent does not fabricate a bundle."
        ),
    ),
}
