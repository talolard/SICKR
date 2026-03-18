from __future__ import annotations

from pathlib import Path

from ikea_image_catalog.extractors import (
    build_page_fetch_url,
    extract_discovery_records,
    image_asset_key_from_url,
)
from ikea_image_catalog.models import ProductSeed

FIXTURES_ROOT = Path(__file__).parent / "fixtures"


def _fixture_text(name: str) -> str:
    return (FIXTURES_ROOT / name).read_text(encoding="utf-8")


def test_build_page_fetch_url_preserves_product_path() -> None:
    source_url = "https://www.ikea.com/au/en/p/ordning-dish-drainer-stainless-steel-00179535/"

    fetch_url = build_page_fetch_url(source_url)

    assert fetch_url.startswith(source_url)
    assert "type=xml" in fetch_url
    assert "dataset=normal%2CallImages%2Cprices%2Cattributes" in fetch_url


def test_extract_discovery_records_filters_unrelated_images_for_au_fixture() -> None:
    seed = ProductSeed(
        product_id="179535",
        repo_canonical_product_key=None,
        product_name="ORDNING",
        country="Australia",
        source_page_url="https://www.ikea.com/au/en/p/ordning-dish-drainer-stainless-steel-00179535/",
        page_fetch_url=build_page_fetch_url(
            "https://www.ikea.com/au/en/p/ordning-dish-drainer-stainless-steel-00179535/"
        ),
    )

    records = extract_discovery_records(
        seed=seed,
        page_text=_fixture_text("au_ordning.html"),
        page_http_status=200,
        crawl_run_id="test-au",
    )

    assert len(records) == 6
    assert records[0].is_og_image is True
    assert records[0].image_role == "MAIN_PRODUCT_IMAGE"
    assert records[0].variant_query_codes == ["u", "xu"]
    assert records[0].page_article_number == "00179535"
    assert all("dyvlinge" not in row.canonical_image_url for row in records)
    assert all("hemkomst" not in row.canonical_image_url for row in records)


def test_extract_discovery_records_preserves_us_and_de_product_images() -> None:
    us_seed = ProductSeed(
        product_id="80275887",
        repo_canonical_product_key="80275887-DE",
        product_name="KALLAX",
        country="USA",
        source_page_url="https://www.ikea.com/us/en/p/kallax-shelf-unit-white-80275887/",
        page_fetch_url=build_page_fetch_url(
            "https://www.ikea.com/us/en/p/kallax-shelf-unit-white-80275887/"
        ),
    )
    de_seed = ProductSeed(
        product_id="263850",
        repo_canonical_product_key="263850-DE",
        product_name="BILLY",
        country="Germany",
        source_page_url="https://www.ikea.com/de/de/p/billy-buecherregal-weiss-00263850/",
        page_fetch_url=build_page_fetch_url(
            "https://www.ikea.com/de/de/p/billy-buecherregal-weiss-00263850/"
        ),
    )

    us_records = extract_discovery_records(
        seed=us_seed,
        page_text=_fixture_text("us_kallax.html"),
        page_http_status=200,
        crawl_run_id="test-us",
    )
    de_records = extract_discovery_records(
        seed=de_seed,
        page_text=_fixture_text("de_billy.html"),
        page_http_status=200,
        crawl_run_id="test-de",
    )

    assert len(us_records) == 8
    assert len(de_records) == 3
    assert us_records[0].page_article_number == "80275887"
    assert de_records[0].page_article_number == "00263850"
    assert all("other-product" not in row.canonical_image_url for row in us_records)
    assert all("ingkadam" not in row.canonical_image_url for row in de_records)


def test_image_asset_key_from_url_is_locale_agnostic() -> None:
    image_url = "https://www.ikea.com/de/de/images/products/billy-buecherregal-weiss__0625599_pe692385_s5.jpg?f=u"

    assert (
        image_asset_key_from_url(image_url) == "billy-buecherregal-weiss__0625599_pe692385_s5.jpg"
    )
