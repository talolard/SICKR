"""Seed the local Postgres catalog and image metadata from canonical inputs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from pyarrow import parquet as pq
from sqlalchemy import Connection, Engine, delete, func, insert, select
from sqlalchemy.sql.base import Executable

from ikea_agent.config import get_settings
from ikea_agent.retrieval.display_titles import derive_display_title
from ikea_agent.retrieval.schema import (
    product_embedding_neighbors,
    product_embeddings,
    product_images,
    products_canonical,
)
from ikea_agent.shared.db_contract import (
    IMAGE_CATALOG_SEED_SYSTEM,
    LOCAL_IMAGE_STORAGE_BACKEND,
    POSTGRES_SEED_SYSTEM,
    PRODUCT_EMBEDDING_DIMENSIONS,
    REMOTE_IMAGE_STORAGE_BACKEND,
)
from ikea_agent.shared.ops_schema import seed_state
from ikea_agent.shared.sqlalchemy_db import create_database_engine, resolve_database_url

_PRODUCTS_PARQUET_PATH = "data/parquet/products_canonical"
_EMBEDDINGS_PARQUET_PATH = "data/parquet/product_embeddings"
_PRODUCTS_CANONICAL_TABLE = "catalog.products_canonical"
_PRODUCT_EMBEDDINGS_TABLE = "catalog.product_embeddings"
_PRODUCT_IMAGES_TABLE = "catalog.product_images"
_PRODUCT_EMBEDDING_NEIGHBORS_TABLE = "catalog.product_embedding_neighbors"
_ROW_COUNT_QUERY_BY_TABLE = {
    _PRODUCTS_CANONICAL_TABLE: select(func.count()).select_from(products_canonical),
    _PRODUCT_EMBEDDINGS_TABLE: select(func.count()).select_from(product_embeddings),
    _PRODUCT_IMAGES_TABLE: select(func.count()).select_from(product_images),
    _PRODUCT_EMBEDDING_NEIGHBORS_TABLE: select(func.count()).select_from(
        product_embedding_neighbors
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
    database_url = resolve_database_url(database_url=args.database_url or settings.database_url)
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
        connection.execute(product_embedding_neighbors.delete())
        connection.execute(product_images.delete())
        connection.execute(product_embeddings.delete())
        connection.execute(products_canonical.delete())

        _insert_rows(
            connection=connection,
            statement=products_canonical.insert(),
            rows=product_rows,
        )
        _insert_rows(
            connection=connection,
            statement=product_embeddings.insert(),
            rows=embedding_rows,
        )
        _insert_rows(
            connection=connection,
            statement=product_images.insert(),
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
    product_rows: list[dict[str, object]] = []
    rows = sorted(
        (
            row
            for row in _read_parquet_rows(parquet_path=products_parquet)
            if _str_or_none(row.get("country")) == "Germany"
        ),
        key=lambda row: _str_or_none(row.get("canonical_product_key")) or "",
    )
    for row in rows:
        product_name = _str_or_none(row.get("product_name")) or ""
        description_text = _str_or_none(row.get("description_text"))
        url = _str_or_none(row.get("url"))
        product_rows.append(
            {
                "canonical_product_key": str(row["canonical_product_key"]),
                "product_id": _str_or_none(row.get("product_id")),
                "unique_id": _str_or_none(row.get("unique_id")),
                "country": _str_or_none(row.get("country")),
                "product_name": product_name,
                "display_title": derive_display_title(
                    product_name=product_name,
                    description_text=description_text,
                    url=url,
                ),
                "product_type": _str_or_none(row.get("product_type")),
                "description_text": description_text,
                "main_category": _str_or_none(row.get("main_category")),
                "sub_category": _str_or_none(row.get("sub_category")),
                "dimensions_text": _str_or_none(row.get("dimensions_text")),
                "width_cm": _float_or_none(row.get("width_cm")),
                "depth_cm": _float_or_none(row.get("depth_cm")),
                "height_cm": _float_or_none(row.get("height_cm")),
                "price_eur": _float_or_none(row.get("price_eur")),
                "currency": _str_or_none(row.get("currency")),
                "rating": _float_or_none(row.get("rating")),
                "rating_count": _int_or_none(row.get("rating_count")),
                "badge": _str_or_none(row.get("badge")),
                "online_sellable": bool(row.get("online_sellable")),
                "url": url,
                "source_updated_at": row.get("source_updated_at"),
            }
        )
    return product_rows


def _load_embedding_rows(*, embeddings_parquet: Path) -> list[dict[str, object]]:
    rows = sorted(
        _read_parquet_rows(parquet_path=embeddings_parquet),
        key=lambda row: (
            _str_or_none(row.get("canonical_product_key")) or "",
            _str_or_none(row.get("embedding_model")) or "",
        ),
    )
    embedding_rows: list[dict[str, object]] = []
    for row in rows:
        embedding_vector = tuple(
            float(item)
            for item in _sequence_or_empty(row.get("embedding_vector"))
            if isinstance(item, int | float)
        )
        if embedding_vector and len(embedding_vector) != PRODUCT_EMBEDDING_DIMENSIONS:
            msg = (
                f"Embedding width mismatch for {row['canonical_product_key']}: "
                f"expected {PRODUCT_EMBEDDING_DIMENSIONS}, got {len(embedding_vector)}."
            )
            raise ValueError(msg)
        embedding_rows.append(
            {
                "canonical_product_key": str(row["canonical_product_key"]),
                "embedding_model": str(row["embedding_model"]),
                "run_id": _str_or_none(row.get("run_id")),
                "embedding_vector": embedding_vector,
                "embedded_text": _str_or_none(row.get("embedded_text")),
                "embedded_at": row.get("embedded_at"),
            }
        )
    return embedding_rows


def _load_image_rows(*, catalog_source: Path) -> list[dict[str, object]]:
    deduped_rows: dict[str, dict[str, object]] = {}
    for row in _read_image_rows(catalog_source=catalog_source):
        image_asset_key = _str_or_none(row.get("image_asset_key"))
        canonical_product_key = _str_or_none(row.get("repo_canonical_product_key"))
        product_id = _str_or_none(row.get("product_id"))
        if image_asset_key is None or canonical_product_key is None or product_id is None:
            continue
        local_path = _str_or_none(row.get("local_path"))
        canonical_image_url = _str_or_none(row.get("canonical_image_url"))
        storage_locator = _str_or_none(row.get("storage_uri")) or canonical_image_url or local_path
        if storage_locator is None:
            continue
        storage_backend_kind = (
            LOCAL_IMAGE_STORAGE_BACKEND if local_path is not None else REMOTE_IMAGE_STORAGE_BACKEND
        )
        deduped_rows[image_asset_key] = {
            "image_asset_key": image_asset_key,
            "canonical_product_key": canonical_product_key,
            "product_id": product_id,
            "image_rank": _int_or_none(row.get("image_rank")),
            "is_og_image": bool(row.get("is_og_image")),
            "image_role": _str_or_none(row.get("image_role")),
            "storage_backend_kind": storage_backend_kind,
            "storage_locator": storage_locator,
            "public_url": canonical_image_url,
            "local_path": local_path,
            "canonical_image_url": canonical_image_url,
            "provenance": _str_or_none(row.get("extraction_source")),
            "crawl_run_id": _str_or_none(row.get("crawl_run_id")),
            "source_page_url": _str_or_none(row.get("source_page_url")),
            "sha256": _str_or_none(row.get("sha256")),
            "content_type": _str_or_none(row.get("content_type")),
            "width_px": _int_or_none(row.get("width_px")),
            "height_px": _int_or_none(row.get("height_px")),
            "refreshed_at": _datetime_or_none(row.get("scraped_at"))
            or _datetime_or_none(row.get("downloaded_at")),
        }
    return list(deduped_rows.values())


def _read_image_rows(*, catalog_source: Path) -> list[dict[str, object]]:
    if catalog_source.suffix == ".parquet":
        return _read_parquet_rows(parquet_path=catalog_source)
    return _read_jsonl_rows(jsonl_path=catalog_source)


def _read_parquet_rows(*, parquet_path: Path) -> list[dict[str, object]]:
    table = pq.read_table(parquet_path)
    return [dict(row) for row in table.to_pylist() if isinstance(row, dict)]


def _read_jsonl_rows(*, jsonl_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with jsonl_path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            loaded = json.loads(line)
            if isinstance(loaded, dict):
                rows.append(loaded)
    return rows


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
            select(seed_state.c.version).where(seed_state.c.system_name == system_name)
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
        delete(seed_state).where(seed_state.c.system_name == system_name),
    )
    connection.execute(
        insert(seed_state).values(
            system_name=system_name,
            version=version,
            source_kind=source_kind,
            status="ready",
            details_json=json.dumps(details, sort_keys=True),
            updated_at=datetime.now(tz=UTC),
        ),
    )


def _insert_rows(
    *,
    connection: Connection,
    statement: Executable,
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


def _sequence_or_empty(value: object) -> tuple[object, ...]:
    if value is None:
        return ()
    if hasattr(value, "tolist"):
        return _sequence_or_empty(value.tolist())
    if isinstance(value, list | tuple):
        return tuple(value)
    return ()


if __name__ == "__main__":
    main()
