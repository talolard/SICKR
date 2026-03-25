from __future__ import annotations

from urllib.parse import urlparse

from ikea_agent.retrieval.display_titles import derive_display_title


def test_derive_display_title_prefers_specific_slug_metadata() -> None:
    assert (
        derive_display_title(
            product_name="FEJKA",
            description_text="Artificial potted plant, indoor/outdoor monstera",
            url="https://www.ikea.com/de/de/p/fejka-kuenstliche-topfpflanze-drinnen-draussen-monstera-30582542/",
        )
        == "FEJKA Kuenstliche Topfpflanze Drinnen Draussen Monstera"
    )


def test_derive_display_title_returns_empty_string_when_product_name_missing() -> None:
    assert (
        derive_display_title(
            product_name="   ",
            description_text="Anything",
            url="https://www.ikea.com/de/de/p/anything-123/",
        )
        == ""
    )


def test_derive_display_title_falls_back_to_base_name_when_slug_and_description_match() -> None:
    assert (
        derive_display_title(
            product_name="BESTA",
            description_text="BESTA",
            url="https://www.ikea.com/de/de/p/besta-19284756/",
        )
        == "BESTA"
    )


def test_derive_display_title_prefixes_family_name_for_description_only_variants() -> None:
    assert (
        derive_display_title(
            product_name="FEJKA",
            description_text="Artificial bamboo plant",
            url=None,
        )
        == "FEJKA Artificial bamboo plant"
    )


def test_derive_display_title_uses_description_directly_for_non_family_names() -> None:
    assert (
        derive_display_title(
            product_name="KALLAX Shelf Unit",
            description_text="White shelving unit with inserts",
            url=None,
        )
        == "White shelving unit with inserts"
    )


def test_derive_display_title_ignores_non_product_urls() -> None:
    assert (
        derive_display_title(
            product_name="MALM",
            description_text=None,
            url=str(urlparse("https://www.ikea.com/de/de/cat/storage-furniture-st001/").geturl()),
        )
        == "MALM"
    )
