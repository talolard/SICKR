"""Derive and backfill durable display titles for catalog products."""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlparse

from sqlalchemy import Engine, bindparam, func, select, update

from ikea_agent.retrieval.schema import products_canonical

_SHORT_TOKEN_MAX_LENGTH = 3
_READ_MISSING_DISPLAY_TITLES_QUERY = (
    select(
        products_canonical.c.canonical_product_key,
        products_canonical.c.product_name,
        products_canonical.c.description_text,
        products_canonical.c.url,
        products_canonical.c.display_title,
    )
    .where(func.coalesce(func.trim(products_canonical.c.product_name), "") != "")
    .where(
        (products_canonical.c.display_title.is_(None))
        | (func.trim(products_canonical.c.display_title) == "")
    )
)


def derive_display_title(
    *,
    product_name: str,
    description_text: str | None,
    url: str | None,
) -> str:
    """Return the best available user-facing product title for runtime display."""

    base_name = _normalize_text(product_name)
    if base_name is None:
        return ""

    slug_title = _display_title_from_url(product_name=base_name, url=url)
    if slug_title is not None:
        return slug_title

    description_title = _display_title_from_description(
        product_name=base_name,
        description_text=description_text,
    )
    if description_title is not None:
        return description_title

    return base_name


def backfill_product_display_titles(engine: Engine) -> int:
    """Populate missing display-title metadata from existing catalog fields."""

    with engine.begin() as connection:
        rows = connection.execute(_READ_MISSING_DISPLAY_TITLES_QUERY).fetchall()
        updates = []
        for row in rows:
            display_title = derive_display_title(
                product_name=str(row[1]),
                description_text=_str_or_none(row[2]),
                url=_str_or_none(row[3]),
            )
            updates.append(
                {
                    "b_display_title": display_title,
                    "b_canonical_product_key": str(row[0]),
                }
            )
        if not updates:
            return 0
        connection.execute(
            update(products_canonical)
            .where(
                products_canonical.c.canonical_product_key == bindparam("b_canonical_product_key")
            )
            .values(display_title=bindparam("b_display_title")),
            updates,
        )
    return len(updates)


def _display_title_from_url(*, product_name: str, url: str | None) -> str | None:
    slug_tokens = _extract_slug_tokens(url)
    if not slug_tokens:
        return None

    base_tokens = _normalized_tokens(product_name)
    if slug_tokens[: len(base_tokens)] == base_tokens:
        remainder_tokens = slug_tokens[len(base_tokens) :]
        if not remainder_tokens:
            return None
        return f"{product_name} {_humanize_tokens(remainder_tokens)}"

    candidate = _humanize_tokens(slug_tokens)
    if _normalized_tokens(candidate) == base_tokens:
        return None
    if _looks_like_family_name(product_name):
        return f"{product_name} {candidate}"
    return candidate


def _display_title_from_description(
    *,
    product_name: str,
    description_text: str | None,
) -> str | None:
    description = _normalize_text(description_text)
    if description is None:
        return None
    if description.casefold() == product_name.casefold():
        return None
    if description.casefold().startswith(product_name.casefold()):
        return description
    if _looks_like_family_name(product_name):
        return f"{product_name} {description}"
    return description


def _extract_slug_tokens(url: str | None) -> list[str]:
    if url is None:
        return []
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    try:
        product_segment_index = path_parts.index("p") + 1
    except ValueError:
        return []
    if product_segment_index >= len(path_parts):
        return []
    raw_slug = path_parts[product_segment_index]
    slug_parts = [part for part in raw_slug.split("-") if part]
    if slug_parts and slug_parts[-1].isdigit():
        slug_parts = slug_parts[:-1]
    return [part.casefold() for part in slug_parts if not part.isdigit()]


def _humanize_tokens(tokens: Sequence[str]) -> str:
    return " ".join(_humanize_token(token) for token in tokens)


def _humanize_token(token: str) -> str:
    if len(token) <= _SHORT_TOKEN_MAX_LENGTH and token.isalpha():
        return token.upper()
    return token[:1].upper() + token[1:]


def _looks_like_family_name(product_name: str) -> bool:
    tokens = product_name.split()
    return len(tokens) == 1 or product_name.isupper()


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized.rstrip(".") or None


def _normalized_tokens(value: str) -> list[str]:
    return [token.casefold() for token in value.replace("/", " ").split() if token]


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
