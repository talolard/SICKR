"""Seed the local Postgres catalog and image metadata from canonical inputs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy import Connection, Engine, text
from sqlalchemy.sql.elements import TextClause

from ikea_agent.config import get_settings
from ikea_agent.retrieval.display_titles import derive_display_title
from ikea_agent.shared.db_contract import (
    IMAGE_CATALOG_SEED_SYSTEM,
    LOCAL_IMAGE_STORAGE_BACKEND,
    POSTGRES_SEED_SYSTEM,
    REMOTE_IMAGE_STORAGE_BACKEND,
)
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url

_PRODUCTS_PARQUET_PATH = "data/parquet/products_canonical"
_EMBEDDINGS_PARQUET_PATH = "data/parquet/product_embeddings"
_PRODUCTS_CANONICAL_TABLE = "catalog.products_canonical"
_PRODUCT_EMBEDDINGS_TABLE = "catalog.product_embeddings"
_PRODUCT_IMAGES_TABLE = "catalog.product_images"
_PRODUCT_EMBEDDING_NEIGHBORS_TABLE = "catalog.product_embedding_neighbors"
_READ_PARQUET_IMAGE_QUERY = """
    SELECT
        image_asset_key,
        repo_canonical_product_key,
        CAST(product_id AS VARCHAR),
        image_rank,
        COALESCE(is_og_image, FALSE),
        image_role,
        local_path,
        canonical_image_url,
        storage_uri,
        extraction_source,
        crawl_run_id,
        source_page_url,
        sha256,
        content_type,
        width_px,
        height_px,
        scraped_at,
        downloaded_at
    FROM read_parquet(?)
    WHERE repo_canonical_product_key IS NOT NULL
      AND CAST(product_id AS VARCHAR) IS NOT NULL
    ORDER BY image_asset_key
"""
_READ_JSON_IMAGE_QUERY = """
    SELECT
        image_asset_key,
        repo_canonical_product_key,
        CAST(product_id AS VARCHAR),
        image_rank,
        COALESCE(is_og_image, FALSE),
        image_role,
        local_path,
        canonical_image_url,
        storage_uri,
        extraction_source,
        crawl_run_id,
        source_page_url,
        sha256,
        content_type,
        width_px,
        height_px,
        scraped_at,
        downloaded_at
    FROM read_json_auto(?)
    WHERE repo_canonical_product_key IS NOT NULL
      AND CAST(product_id AS VARCHAR) IS NOT NULL
    ORDER BY image_asset_key
"""
_ROW_COUNT_QUERY_BY_TABLE = {
    _PRODUCTS_CANONICAL_TABLE: text("SELECT count(*) FROM catalog.products_canonical"),
    _PRODUCT_EMBEDDINGS_TABLE: text("SELECT count(*) FROM catalog.product_embeddings"),
    _PRODUCT_IMAGES_TABLE: text("SELECT count(*) FROM catalog.product_images"),
    _PRODUCT_EMBEDDING_NEIGHBORS_TABLE: text(
        "SELECT count(*) FROM catalog.product_embedding_neighbors"
    ),
}


@dataclass(frozen=True, slots=True)
class SeedSummary:
    """Observable outcome of one Postgres seed operation."""

    postgres_seed_version: str
    image_catalog_seed_version: str
    image_catalog_source: str
    products_count: int
    embeddings_count: int
    image_count: int
    skipped: bool


def main() -> None:
    """Seed local Postgres tables from repo-local canonical inputs."""

    parser = argparse.ArgumentParser(description="Seed the local Postgres catalog tables.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--image-catalog-root", default=None)
    parser.add_argument("--image-catalog-run-id", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    repo_root = Path(args.repo_root or Path.cwd()).resolve()
    image_catalog_root = Path(
        args.image_catalog_root or settings.ikea_image_catalog_root_dir
    ).expanduser()
    image_catalog_run_id = args.image_catalog_run_id or settings.ikea_image_catalog_run_id
    database_url = resolve_database_url(
        database_url=args.database_url or settings.database_url,
        duckdb_path=settings.duckdb_path,
    )
    engine = create_database_engine(database_url)
    summary = seed_postgres_database(
        engine=engine,
        repo_root=repo_root,
        image_catalog_root=image_catalog_root,
        image_catalog_run_id=image_catalog_run_id,
        force=args.force,
    )
    print(json.dumps(asdict(summary), indent=2, sort_keys=True))


def seed_postgres_database(
    *,
    engine: Engine,
    repo_root: Path,
    image_catalog_root: Path,
    image_catalog_run_id: str | None,
    force: bool,
) -> SeedSummary:
    """Seed catalog and image metadata into the local Postgres database."""

    products_parquet = repo_root / _PRODUCTS_PARQUET_PATH
    embeddings_parquet = repo_root / _EMBEDDINGS_PARQUET_PATH
    image_catalog_source = _select_image_catalog_source(
        image_catalog_root=image_catalog_root,
        run_id=image_catalog_run_id,
    )
    postgres_seed_version = _fingerprint_paths([products_parquet, embeddings_parquet])
    image_catalog_seed_version = _fingerprint_paths([image_catalog_source])
    current_postgres_seed_version = _read_seed_version(
        engine=engine, system_name=POSTGRES_SEED_SYSTEM
    )
    current_image_seed_version = _read_seed_version(
        engine=engine, system_name=IMAGE_CATALOG_SEED_SYSTEM
    )
    if (
        not force
        and current_postgres_seed_version == postgres_seed_version
        and current_image_seed_version == image_catalog_seed_version
    ):
        with engine.connect() as connection:
            products_count = _count_rows(connection, _PRODUCTS_CANONICAL_TABLE)
            embeddings_count = _count_rows(connection, _PRODUCT_EMBEDDINGS_TABLE)
            image_count = _count_rows(connection, _PRODUCT_IMAGES_TABLE)
        return SeedSummary(
            postgres_seed_version=postgres_seed_version,
            image_catalog_seed_version=image_catalog_seed_version,
            image_catalog_source=str(image_catalog_source),
            products_count=products_count,
            embeddings_count=embeddings_count,
            image_count=image_count,
            skipped=True,
        )

    product_rows = _load_product_rows(products_parquet=products_parquet)
    embedding_rows = _load_embedding_rows(embeddings_parquet=embeddings_parquet)
    image_rows = _load_image_rows(catalog_source=image_catalog_source)

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM catalog.product_embedding_neighbors"))
        connection.execute(text("DELETE FROM catalog.product_images"))
        connection.execute(text("DELETE FROM catalog.product_embeddings"))
        connection.execute(text("DELETE FROM catalog.products_canonical"))

        _insert_rows(
            connection=connection,
            statement=text(
                """
                INSERT INTO catalog.products_canonical (
                    canonical_product_key,
                    product_id,
                    unique_id,
                    country,
                    product_name,
                    display_title,
                    product_type,
                    description_text,
                    main_category,
                    sub_category,
                    dimensions_text,
                    width_cm,
                    depth_cm,
                    height_cm,
                    price_eur,
                    currency,
                    rating,
                    rating_count,
                    badge,
                    online_sellable,
                    url,
                    source_updated_at
                ) VALUES (
                    :canonical_product_key,
                    :product_id,
                    :unique_id,
                    :country,
                    :product_name,
                    :display_title,
                    :product_type,
                    :description_text,
                    :main_category,
                    :sub_category,
                    :dimensions_text,
                    :width_cm,
                    :depth_cm,
                    :height_cm,
                    :price_eur,
                    :currency,
                    :rating,
                    :rating_count,
                    :badge,
                    :online_sellable,
                    :url,
                    :source_updated_at
                )
                """
            ),
            rows=product_rows,
        )
        _insert_rows(
            connection=connection,
            statement=text(
                """
                INSERT INTO catalog.product_embeddings (
                    canonical_product_key,
                    embedding_model,
                    run_id,
                    embedding_vector,
                    embedded_text,
                    embedded_at
                ) VALUES (
                    :canonical_product_key,
                    :embedding_model,
                    :run_id,
                    :embedding_vector,
                    :embedded_text,
                    :embedded_at
                )
                """
            ),
            rows=embedding_rows,
        )
        _insert_rows(
            connection=connection,
            statement=text(
                """
                INSERT INTO catalog.product_images (
                    image_asset_key,
                    canonical_product_key,
                    product_id,
                    image_rank,
                    is_og_image,
                    image_role,
                    storage_backend_kind,
                    storage_locator,
                    public_url,
                    local_path,
                    canonical_image_url,
                    provenance,
                    crawl_run_id,
                    source_page_url,
                    sha256,
                    content_type,
                    width_px,
                    height_px,
                    refreshed_at
                ) VALUES (
                    :image_asset_key,
                    :canonical_product_key,
                    :product_id,
                    :image_rank,
                    :is_og_image,
                    :image_role,
                    :storage_backend_kind,
                    :storage_locator,
                    :public_url,
                    :local_path,
                    :canonical_image_url,
                    :provenance,
                    :crawl_run_id,
                    :source_page_url,
                    :sha256,
                    :content_type,
                    :width_px,
                    :height_px,
                    :refreshed_at
                )
                """
            ),
            rows=image_rows,
        )
        _write_seed_state(
            connection=connection,
            system_name=POSTGRES_SEED_SYSTEM,
            version=postgres_seed_version,
            source_kind="parquet",
            details={
                "products_parquet": str(products_parquet),
                "embeddings_parquet": str(embeddings_parquet),
                "products_count": len(product_rows),
                "embeddings_count": len(embedding_rows),
            },
        )
        _write_seed_state(
            connection=connection,
            system_name=IMAGE_CATALOG_SEED_SYSTEM,
            version=image_catalog_seed_version,
            source_kind="image_catalog",
            details={
                "catalog_source": str(image_catalog_source),
                "image_count": len(image_rows),
            },
        )

    return SeedSummary(
        postgres_seed_version=postgres_seed_version,
        image_catalog_seed_version=image_catalog_seed_version,
        image_catalog_source=str(image_catalog_source),
        products_count=len(product_rows),
        embeddings_count=len(embedding_rows),
        image_count=len(image_rows),
        skipped=False,
    )


def _load_product_rows(*, products_parquet: Path) -> list[dict[str, object]]:
    connection = duckdb.connect()
    try:
        rows = connection.execute(
            """
            SELECT
                canonical_product_key,
                CAST(product_id AS VARCHAR),
                unique_id,
                country,
                product_name,
                product_type,
                description_text,
                main_category,
                sub_category,
                dimensions_text,
                width_cm,
                depth_cm,
                height_cm,
                price_eur,
                currency,
                rating,
                rating_count,
                badge,
                online_sellable,
                url,
                source_updated_at
            FROM read_parquet(?)
            WHERE country = 'Germany'
            ORDER BY canonical_product_key
            """,
            [str(products_parquet)],
        ).fetchall()
    finally:
        connection.close()
    product_rows: list[dict[str, object]] = []
    for row in rows:
        product_name = _str_or_none(row[4]) or ""
        description_text = _str_or_none(row[6])
        url = _str_or_none(row[19])
        product_rows.append(
            {
                "canonical_product_key": str(row[0]),
                "product_id": _str_or_none(row[1]),
                "unique_id": _str_or_none(row[2]),
                "country": _str_or_none(row[3]),
                "product_name": product_name,
                "display_title": derive_display_title(
                    product_name=product_name,
                    description_text=description_text,
                    url=url,
                ),
                "product_type": _str_or_none(row[5]),
                "description_text": description_text,
                "main_category": _str_or_none(row[7]),
                "sub_category": _str_or_none(row[8]),
                "dimensions_text": _str_or_none(row[9]),
                "width_cm": _float_or_none(row[10]),
                "depth_cm": _float_or_none(row[11]),
                "height_cm": _float_or_none(row[12]),
                "price_eur": _float_or_none(row[13]),
                "currency": _str_or_none(row[14]),
                "rating": _float_or_none(row[15]),
                "rating_count": _int_or_none(row[16]),
                "badge": _str_or_none(row[17]),
                "online_sellable": bool(row[18]),
                "url": url,
                "source_updated_at": row[20],
            }
        )
    return product_rows


def _load_embedding_rows(*, embeddings_parquet: Path) -> list[dict[str, object]]:
    connection = duckdb.connect()
    try:
        rows = connection.execute(
            """
            SELECT
                canonical_product_key,
                embedding_model,
                run_id,
                embedding_vector,
                embedded_text,
                embedded_at
            FROM read_parquet(?)
            ORDER BY canonical_product_key, embedding_model
            """,
            [str(embeddings_parquet)],
        ).fetchall()
    finally:
        connection.close()
    return [
        {
            "canonical_product_key": str(row[0]),
            "embedding_model": str(row[1]),
            "run_id": _str_or_none(row[2]),
            "embedding_vector": list(row[3]) if isinstance(row[3], list | tuple) else [],
            "embedded_text": _str_or_none(row[4]),
            "embedded_at": row[5],
        }
        for row in rows
    ]


def _load_image_rows(*, catalog_source: Path) -> list[dict[str, object]]:
    connection = duckdb.connect()
    try:
        rows = connection.execute(
            _image_catalog_query(catalog_source),
            [str(catalog_source)],
        ).fetchall()
    finally:
        connection.close()

    deduped_rows: dict[str, dict[str, object]] = {}
    for row in rows:
        image_asset_key = _str_or_none(row[0])
        canonical_product_key = _str_or_none(row[1])
        product_id = _str_or_none(row[2])
        if image_asset_key is None or canonical_product_key is None or product_id is None:
            continue
        local_path = _str_or_none(row[6])
        canonical_image_url = _str_or_none(row[7])
        storage_locator = _str_or_none(row[8]) or canonical_image_url or local_path
        if storage_locator is None:
            continue
        storage_backend_kind = (
            LOCAL_IMAGE_STORAGE_BACKEND if local_path is not None else REMOTE_IMAGE_STORAGE_BACKEND
        )
        deduped_rows[image_asset_key] = {
            "image_asset_key": image_asset_key,
            "canonical_product_key": canonical_product_key,
            "product_id": product_id,
            "image_rank": _int_or_none(row[3]),
            "is_og_image": bool(row[4]),
            "image_role": _str_or_none(row[5]),
            "storage_backend_kind": storage_backend_kind,
            "storage_locator": storage_locator,
            "public_url": canonical_image_url,
            "local_path": local_path,
            "canonical_image_url": canonical_image_url,
            "provenance": _str_or_none(row[9]),
            "crawl_run_id": _str_or_none(row[10]),
            "source_page_url": _str_or_none(row[11]),
            "sha256": _str_or_none(row[12]),
            "content_type": _str_or_none(row[13]),
            "width_px": _int_or_none(row[14]),
            "height_px": _int_or_none(row[15]),
            "refreshed_at": _datetime_or_none(row[16]) or _datetime_or_none(row[17]),
        }
    return list(deduped_rows.values())


def _image_catalog_query(catalog_source: Path) -> str:
    if catalog_source.suffix == ".parquet":
        return _READ_PARQUET_IMAGE_QUERY
    return _READ_JSON_IMAGE_QUERY


def _select_image_catalog_source(*, image_catalog_root: Path, run_id: str | None) -> Path:
    runs_root = image_catalog_root / "runs"
    if not runs_root.exists():
        msg = f"Image catalog root does not exist: {image_catalog_root}"
        raise FileNotFoundError(msg)
    if run_id:
        run_dir = runs_root / run_id
        candidate = _catalog_source_for_run_dir(run_dir)
        if candidate is not None:
            return candidate
        msg = f"Configured image catalog run has no catalog file: {run_dir}"
        raise FileNotFoundError(msg)

    candidates = _catalog_source_candidates(runs_root)
    if not candidates:
        msg = f"No image catalog outputs found under {runs_root}"
        raise FileNotFoundError(msg)
    candidates.sort(key=_catalog_source_sort_key, reverse=True)
    return candidates[0]


def _catalog_source_candidates(runs_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for run_dir in runs_root.iterdir():
        if not run_dir.is_dir():
            continue
        candidate = _catalog_source_for_run_dir(run_dir)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _catalog_source_for_run_dir(run_dir: Path) -> Path | None:
    parquet_path = run_dir / "catalog.parquet"
    if parquet_path.exists():
        return parquet_path
    jsonl_path = run_dir / "catalog.jsonl"
    if jsonl_path.exists():
        return jsonl_path
    return None


def _catalog_source_sort_key(path: Path) -> tuple[int, int, str]:
    return (
        1 if path.suffix == ".parquet" else 0,
        path.stat().st_mtime_ns,
        path.as_posix(),
    )


def _fingerprint_paths(paths: list[Path]) -> str:
    digest = sha256()
    for path in sorted(paths):
        resolved = path.expanduser().resolve()
        digest.update(str(resolved).encode())
        if resolved.is_dir():
            for file_path in sorted(item for item in resolved.rglob("*") if item.is_file()):
                digest.update(str(file_path.relative_to(resolved)).encode())
                stat = file_path.stat()
                digest.update(str(stat.st_size).encode())
                digest.update(str(stat.st_mtime_ns).encode())
        else:
            stat = resolved.stat()
            digest.update(str(stat.st_size).encode())
            digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()


def _read_seed_version(*, engine: Engine, system_name: str) -> str | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT version
                FROM ops.seed_state
                WHERE system_name = :system_name
                """
            ),
            {"system_name": system_name},
        ).fetchone()
    if row is None or row[0] is None:
        return None
    return str(row[0])


def _write_seed_state(
    *,
    connection: Connection,
    system_name: str,
    version: str,
    source_kind: str,
    details: dict[str, Any],
) -> None:
    connection.execute(
        text("DELETE FROM ops.seed_state WHERE system_name = :system_name"),
        {"system_name": system_name},
    )
    connection.execute(
        text(
            """
            INSERT INTO ops.seed_state (
                system_name,
                version,
                source_kind,
                status,
                details_json,
                updated_at
            ) VALUES (
                :system_name,
                :version,
                :source_kind,
                'ready',
                :details_json,
                :updated_at
            )
            """
        ),
        {
            "system_name": system_name,
            "version": version,
            "source_kind": source_kind,
            "details_json": json.dumps(details, sort_keys=True),
            "updated_at": datetime.now(tz=UTC),
        },
    )


def _insert_rows(
    *,
    connection: Connection,
    statement: TextClause,
    rows: list[dict[str, object]],
    batch_size: int = 500,
) -> None:
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        if batch:
            connection.execute(statement, batch)


def _count_rows(connection: Connection, table_name: str) -> int:
    query = _ROW_COUNT_QUERY_BY_TABLE.get(table_name)
    if query is None:
        msg = f"Unsupported count_rows table: {table_name}"
        raise ValueError(msg)
    value = connection.execute(query).scalar_one()
    return int(value)


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    return None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return None


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _datetime_or_none(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    return None


if __name__ == "__main__":
    main()
