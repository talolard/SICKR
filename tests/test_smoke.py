from __future__ import annotations

from tal_maria_ikea.types import IkeaRecord


def test_smoke_import_and_type_contract() -> None:
    record = IkeaRecord(
        product_id="sku-1",
        product_name="Mock Product",
        category="lighting",
        description="Demo row",
        dimensions_text="10x10x10 cm",
        price_text="10.00",
    )

    assert record.product_id == "sku-1"
