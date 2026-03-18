from __future__ import annotations

from dataclasses import asdict

from ikea_agent.shared.types import ShortRetrievalResult


def test_short_retrieval_result_contract_shape_is_stable() -> None:
    result = ShortRetrievalResult(
        product_id="prod-001",
        product_name="PAX wardrobe",
        product_type="Wardrobe",
        description_text="Wardrobe",
        main_category="Storage",
        sub_category="Wardrobes",
        width_cm=80.0,
        depth_cm=50.0,
        height_cm=200.0,
        price_eur=149.99,
    )

    serialized = asdict(result)

    assert list(serialized.keys()) == [
        "product_id",
        "product_name",
        "product_type",
        "description_text",
        "main_category",
        "sub_category",
        "width_cm",
        "depth_cm",
        "height_cm",
        "price_eur",
        "url",
        "display_title",
        "image_urls",
    ]
