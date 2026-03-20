"""Build and validate a versioned Postgres snapshot artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, delete, func, insert, select

from ikea_agent.config import get_settings
from ikea_agent.retrieval.catalog_repository import CatalogRepository, EmbeddingSnapshotRepository
from ikea_agent.retrieval.schema import (
    product_embedding_neighbors,
    product_embeddings,
    product_images,
    products_canonical,
)
from ikea_agent.shared.db_contract import (
    POSTGRES_SNAPSHOT_SYSTEM,
    PRODUCT_EMBEDDING_DISTANCE_METRIC,
)
from ikea_agent.shared.ops_schema import seed_state
from ikea_agent.shared.sqlalchemy_db import create_database_engine
from ingest.precompute_embedding_neighbors import build_neighbor_rows
from scripts.docker_deps.seed_postgres import (
    SeedSummary,
    _fingerprint_paths,
    seed_postgres_database,
)

_POSTGRES_DB = "ikea_agent"
_POSTGRES_USER = "ikea"
_POSTGRES_PASSWORD = "ikea"  # noqa: S105
_ARTIFACT_FILENAME = "postgres.dump"
_MANIFEST_FILENAME = "manifest.json"
_LATEST_FILENAME = "latest.json"
_CONTAINER_ARTIFACT_PATH = Path("/tmp") / _ARTIFACT_FILENAME  # noqa: S108


@dataclass(frozen=True, slots=True)
class SnapshotStack:
    """Ephemeral Postgres stack used for building or validating snapshots."""

    compose_file: Path
    env_file: Path
    port: int
    project_name: str

    @property
    def database_url(self) -> str:
        """Return the SQLAlchemy URL for this stack's Postgres instance."""

        return (
            f"postgresql+psycopg://{_POSTGRES_USER}:{_POSTGRES_PASSWORD}"
            f"@127.0.0.1:{self.port}/{_POSTGRES_DB}"
        )


@dataclass(frozen=True, slots=True)
class SnapshotBuildSummary:
    """Observable result of one snapshot build."""

    artifact_dir: str
    artifact_path: str
    embeddings_count: int
    image_catalog_seed_version: str
    image_catalog_source: str
    image_count: int
    latest_path: str
    manifest_path: str
    migration_head: str
    neighbor_count: int
    postgres_seed_version: str
    products_count: int
    restore_validated: bool
    snapshot_version: str


def main() -> None:
    """Build a versioned Postgres snapshot and validate restore."""

    args = _parse_args()
    summary = build_postgres_snapshot(
        repo_root=Path(args.repo_root).expanduser().resolve(),
        output_root=Path(args.output_root).expanduser().resolve(),
        image_catalog_root=(
            None
            if args.image_catalog_root is None
            else Path(args.image_catalog_root).expanduser().resolve()
        ),
        image_catalog_run_id=args.image_catalog_run_id,
        builder_port=args.builder_port,
        validator_port=args.validator_port,
        project_prefix=args.project_prefix,
        embedding_neighbor_limit=args.embedding_neighbor_limit,
        keep_temp_stacks=args.keep_temp_stacks,
    )
    summary_json = json.dumps(asdict(summary), indent=2, sort_keys=True) + "\n"
    if args.summary_path is not None:
        summary_path = Path(args.summary_path).expanduser().resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary_json, encoding="utf-8")
    print(summary_json, end="")


def build_postgres_snapshot(
    *,
    repo_root: Path,
    output_root: Path,
    image_catalog_root: Path | None,
    image_catalog_run_id: str | None,
    builder_port: int,
    validator_port: int,
    project_prefix: str,
    embedding_neighbor_limit: int | None,
    keep_temp_stacks: bool,
) -> SnapshotBuildSummary:
    """Create one versioned dump and prove it restores into a fresh Postgres stack."""

    settings = get_settings()
    resolved_image_catalog_root = (
        image_catalog_root
        if image_catalog_root is not None
        else Path(settings.ikea_image_catalog_root_dir).expanduser().resolve()
    )
    resolved_image_catalog_run_id = image_catalog_run_id or settings.ikea_image_catalog_run_id
    resolved_neighbor_limit = (
        settings.embedding_neighbor_limit
        if embedding_neighbor_limit is None
        else embedding_neighbor_limit
    )
    output_root.mkdir(parents=True, exist_ok=True)
    migration_head = _migration_head(repo_root)
    builder_fingerprint = _builder_fingerprint(repo_root)
    head_branch = _git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    head_sha = _git_output(repo_root, "rev-parse", "HEAD")

    with tempfile.TemporaryDirectory(prefix="ikea-postgres-snapshot-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        builder_stack = _create_stack(
            repo_root=repo_root,
            temp_dir=temp_dir,
            stack_name="builder",
            project_name=f"{project_prefix}-builder",
            port=builder_port,
        )
        validator_stack = _create_stack(
            repo_root=repo_root,
            temp_dir=temp_dir,
            stack_name="validator",
            project_name=f"{project_prefix}-validator",
            port=validator_port,
        )

        try:
            _recreate_stack(builder_stack)
            _upgrade_database(builder_stack.database_url)
            builder_engine = create_database_engine(builder_stack.database_url)
            seed_summary = seed_postgres_database(
                engine=builder_engine,
                repo_root=repo_root,
                image_catalog_root=resolved_image_catalog_root,
                image_catalog_run_id=resolved_image_catalog_run_id,
                force=True,
            )
            neighbor_count = _materialize_neighbor_rows(
                engine=builder_engine,
                embedding_model=settings.gemini_model,
                neighbor_limit=resolved_neighbor_limit,
            )

            snapshot_version = _snapshot_version(
                migration_head=migration_head,
                builder_fingerprint=builder_fingerprint,
                postgres_seed_version=seed_summary.postgres_seed_version,
                image_catalog_seed_version=seed_summary.image_catalog_seed_version,
                embedding_model=settings.gemini_model,
                neighbor_limit=resolved_neighbor_limit,
            )
            manifest_payload = _build_manifest_payload(
                snapshot_version=snapshot_version,
                migration_head=migration_head,
                builder_fingerprint=builder_fingerprint,
                seed_summary=seed_summary,
                embedding_model=settings.gemini_model,
                neighbor_limit=resolved_neighbor_limit,
                neighbor_count=neighbor_count,
            )
            _write_snapshot_state(
                engine=builder_engine,
                snapshot_version=snapshot_version,
                details=manifest_payload,
            )

            artifact_dir = output_root / snapshot_version
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = artifact_dir / _ARTIFACT_FILENAME
            manifest_path = artifact_dir / _MANIFEST_FILENAME
            latest_path = output_root / _LATEST_FILENAME

            _dump_snapshot(builder_stack, artifact_path)
            manifest_payload["artifact"] = {
                "filename": artifact_path.name,
                "format": "pg_dump_custom",
                "sha256": _sha256_for_path(artifact_path),
                "size_bytes": artifact_path.stat().st_size,
            }

            _recreate_stack(validator_stack)
            _restore_snapshot(validator_stack, artifact_path)
            validation = _validate_restored_snapshot(
                database_url=validator_stack.database_url,
                snapshot_version=snapshot_version,
                image_catalog_root=resolved_image_catalog_root,
                expected_counts={
                    "products_count": seed_summary.products_count,
                    "embeddings_count": seed_summary.embeddings_count,
                    "image_count": seed_summary.image_count,
                    "neighbor_count": neighbor_count,
                },
            )
            manifest_payload["validation"] = validation

            manifest_path.write_text(
                json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            latest_path.write_text(
                json.dumps(
                    {
                        "artifact_name": f"local-{snapshot_version}",
                        "artifact_path": str(artifact_path),
                        "built_at": datetime.now(tz=UTC).isoformat(),
                        "head_branch": head_branch,
                        "head_sha": head_sha,
                        "manifest_path": str(manifest_path),
                        "migration_head": migration_head,
                        "snapshot_version": snapshot_version,
                        "source_kind": "local_build",
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            return SnapshotBuildSummary(
                artifact_dir=str(artifact_dir),
                artifact_path=str(artifact_path),
                embeddings_count=seed_summary.embeddings_count,
                image_catalog_seed_version=seed_summary.image_catalog_seed_version,
                image_catalog_source=seed_summary.image_catalog_source,
                image_count=seed_summary.image_count,
                latest_path=str(latest_path),
                manifest_path=str(manifest_path),
                migration_head=migration_head,
                neighbor_count=neighbor_count,
                postgres_seed_version=seed_summary.postgres_seed_version,
                products_count=seed_summary.products_count,
                restore_validated=bool(validation["restored_counts_match"]),
                snapshot_version=snapshot_version,
            )
        finally:
            if not keep_temp_stacks:
                _down_stack(builder_stack)
                _down_stack(validator_stack)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Postgres snapshot artifact.")
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    parser.add_argument(
        "--output-root",
        default=str(Path.cwd() / ".tmp_untracked" / "docker-deps" / "snapshots"),
    )
    parser.add_argument("--image-catalog-root", default=None)
    parser.add_argument("--image-catalog-run-id", default=None)
    parser.add_argument("--builder-port", type=int, default=25432)
    parser.add_argument("--validator-port", type=int, default=26432)
    parser.add_argument("--project-prefix", default="ikea-postgres-snapshot")
    parser.add_argument("--embedding-neighbor-limit", type=int, default=None)
    parser.add_argument("--keep-temp-stacks", action="store_true")
    parser.add_argument("--summary-path", default=None)
    return parser.parse_args()


def _create_stack(
    *,
    repo_root: Path,
    temp_dir: Path,
    stack_name: str,
    project_name: str,
    port: int,
) -> SnapshotStack:
    env_file = temp_dir / f"{stack_name}.env"
    env_file.write_text(
        "\n".join(
            (
                f"POSTGRES_PORT={port}",
                f"POSTGRES_DB={_POSTGRES_DB}",
                f"POSTGRES_USER={_POSTGRES_USER}",
                f"POSTGRES_PASSWORD={_POSTGRES_PASSWORD}",
                f"POSTGRES_VOLUME_NAME={project_name}-postgres-data",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return SnapshotStack(
        compose_file=repo_root / "docker" / "compose.postgres.yml",
        env_file=env_file,
        port=port,
        project_name=project_name,
    )


def _recreate_stack(stack: SnapshotStack) -> None:
    _down_stack(stack)
    _compose_run(stack, "up", "-d", "postgres")
    _wait_for_postgres(stack)


def _down_stack(stack: SnapshotStack) -> None:
    _compose_run(stack, "down", "--volumes", "--remove-orphans", check=False)


def _wait_for_postgres(stack: SnapshotStack) -> None:
    for _ in range(90):
        result = _compose_run(
            stack,
            "exec",
            "-T",
            "postgres",
            "pg_isready",
            "-U",
            _POSTGRES_USER,
            "-d",
            _POSTGRES_DB,
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    msg = f"Postgres did not become ready for {stack.project_name} on port {stack.port}."
    raise RuntimeError(msg)


def _upgrade_database(database_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def _materialize_neighbor_rows(
    *,
    engine: Engine,
    embedding_model: str,
    neighbor_limit: int,
) -> int:
    """Materialize legacy neighbor rows only when a build explicitly requests them."""

    repository = EmbeddingSnapshotRepository(engine)
    if neighbor_limit <= 0:
        repository.replace_neighbor_rows(embedding_model=embedding_model, rows=())
        return 0

    rows = repository.read_embedding_rows(embedding_model=embedding_model)
    neighbor_rows_by_model = build_neighbor_rows(
        embedding_rows=rows,
        neighbor_limit=neighbor_limit,
    )
    total_inserted = 0
    for current_model, neighbor_rows in neighbor_rows_by_model.items():
        total_inserted += repository.replace_neighbor_rows(
            embedding_model=current_model,
            rows=neighbor_rows,
        )
    return total_inserted


def _snapshot_version(
    *,
    migration_head: str,
    builder_fingerprint: str,
    postgres_seed_version: str,
    image_catalog_seed_version: str,
    embedding_model: str,
    neighbor_limit: int,
) -> str:
    payload = {
        "builder_fingerprint": builder_fingerprint,
        "embedding_model": embedding_model,
        "image_catalog_seed_version": image_catalog_seed_version,
        "migration_head": migration_head,
        "neighbor_limit": neighbor_limit,
        "postgres_seed_version": postgres_seed_version,
    }
    digest = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"pgsnapshot-{migration_head}-{digest[:16]}"


def _build_manifest_payload(
    *,
    snapshot_version: str,
    migration_head: str,
    builder_fingerprint: str,
    seed_summary: SeedSummary,
    embedding_model: str,
    neighbor_limit: int,
    neighbor_count: int,
) -> dict[str, object]:
    return {
        "builder_fingerprint": builder_fingerprint,
        "built_at": datetime.now(tz=UTC).isoformat(),
        "distance_metric": PRODUCT_EMBEDDING_DISTANCE_METRIC,
        "embedding_model": embedding_model,
        "image_catalog_source": seed_summary.image_catalog_source,
        "input_fingerprints": {
            "image_catalog_seed_version": seed_summary.image_catalog_seed_version,
            "postgres_seed_version": seed_summary.postgres_seed_version,
        },
        "migration_head": migration_head,
        "neighbor_state": {
            "limit": neighbor_limit,
            "materialized_row_count": neighbor_count,
            "strategy": "legacy_precomputed"
            if neighbor_limit > 0
            else "pgvector_candidate_set_runtime",
        },
        "row_counts": {
            "embeddings_count": seed_summary.embeddings_count,
            "image_count": seed_summary.image_count,
            "neighbor_count": neighbor_count,
            "products_count": seed_summary.products_count,
        },
        "snapshot_version": snapshot_version,
    }


def _write_snapshot_state(
    *,
    engine: Engine,
    snapshot_version: str,
    details: dict[str, object],
) -> None:
    with engine.begin() as connection:
        connection.execute(
            delete(seed_state).where(seed_state.c.system_name == POSTGRES_SNAPSHOT_SYSTEM),
        )
        connection.execute(
            insert(seed_state).values(
                system_name=POSTGRES_SNAPSHOT_SYSTEM,
                version=snapshot_version,
                source_kind="postgres_snapshot",
                status="ready",
                details_json=json.dumps(details, sort_keys=True),
                updated_at=datetime.now(tz=UTC),
            ),
        )


def _dump_snapshot(stack: SnapshotStack, artifact_path: Path) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    _compose_run(
        stack,
        "exec",
        "-T",
        "postgres",
        "pg_dump",
        "-U",
        _POSTGRES_USER,
        "-d",
        _POSTGRES_DB,
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(_CONTAINER_ARTIFACT_PATH),
    )
    _docker_run("cp", f"{_container_id(stack)}:{_CONTAINER_ARTIFACT_PATH}", str(artifact_path))


def _restore_snapshot(stack: SnapshotStack, artifact_path: Path) -> None:
    _docker_run("cp", str(artifact_path), f"{_container_id(stack)}:{_CONTAINER_ARTIFACT_PATH}")
    _compose_run(
        stack,
        "exec",
        "-T",
        "postgres",
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "-U",
        _POSTGRES_USER,
        "-d",
        _POSTGRES_DB,
        str(_CONTAINER_ARTIFACT_PATH),
    )


def _validate_restored_snapshot(
    *,
    database_url: str,
    snapshot_version: str,
    image_catalog_root: Path,
    expected_counts: dict[str, int],
) -> dict[str, object]:
    settings = get_settings()
    engine = create_database_engine(database_url)
    _ = image_catalog_root
    image_repository = CatalogRepository(engine)
    embedding_repository = EmbeddingSnapshotRepository(engine)
    embeddings = embedding_repository.read_embedding_rows(settings.gemini_model)
    with engine.connect() as connection:
        restored_counts = {
            "products_count": int(
                connection.execute(
                    select(func.count()).select_from(products_canonical)
                ).scalar_one()
            ),
            "embeddings_count": int(
                connection.execute(
                    select(func.count()).select_from(product_embeddings)
                ).scalar_one()
            ),
            "image_count": int(
                connection.execute(select(func.count()).select_from(product_images)).scalar_one()
            ),
            "neighbor_count": int(
                connection.execute(
                    select(func.count()).select_from(product_embedding_neighbors)
                ).scalar_one()
            ),
        }
        snapshot_row = connection.execute(
            select(seed_state.c.version).where(seed_state.c.system_name == POSTGRES_SNAPSHOT_SYSTEM)
        ).fetchone()
    validated_keys = [row[0] for row in embeddings[:100]]
    image_urls_by_key = image_repository.read_image_urls_by_product_keys(
        canonical_product_keys=validated_keys,
        serving_strategy="direct_public_url",
        base_url="https://example.test",
    )
    return {
        "validated_image_lookup_product_count": len(image_urls_by_key),
        "restored_counts": restored_counts,
        "restored_counts_match": restored_counts == expected_counts,
        "snapshot_seed_version": None if snapshot_row is None else str(snapshot_row[0]),
        "snapshot_seed_version_matches": snapshot_row is not None
        and str(snapshot_row[0]) == snapshot_version,
        "typed_embedding_row_count": len(embeddings),
    }


def _migration_head(repo_root: Path) -> str:
    config = Config(str(repo_root / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "migrations"))
    current_head = ScriptDirectory.from_config(config).get_current_head()
    if current_head is None:
        msg = f"Could not resolve the Alembic migration head under {repo_root / 'migrations'}."
        raise RuntimeError(msg)
    return current_head


def _builder_fingerprint(repo_root: Path) -> str:
    return _fingerprint_paths(
        [
            repo_root / "docker" / "compose.postgres.yml",
            repo_root / "migrations",
            repo_root / "scripts" / "docker_deps" / "build_postgres_snapshot.py",
            repo_root / "scripts" / "docker_deps" / "seed_postgres.py",
            repo_root / "src" / "ingest" / "precompute_embedding_neighbors.py",
        ]
    )


def _git_output(repo_root: Path, *args: str) -> str:
    result = _run("git", "-C", str(repo_root), *args, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = stderr or f"git {' '.join(args)} failed with exit code {result.returncode}"
        raise RuntimeError(msg)
    return result.stdout.strip()


def _sha256_for_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _container_id(stack: SnapshotStack) -> str:
    result = _compose_run(stack, "ps", "-q", "postgres")
    container_id = result.stdout.strip()
    if not container_id:
        msg = f"Could not resolve container id for stack {stack.project_name}."
        raise RuntimeError(msg)
    return container_id


def _compose_run(
    stack: SnapshotStack, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return _run(
        "docker",
        "compose",
        "--env-file",
        str(stack.env_file),
        "-f",
        str(stack.compose_file),
        "-p",
        stack.project_name,
        *args,
        check=check,
    )


def _docker_run(*args: str) -> subprocess.CompletedProcess[str]:
    return _run("docker", *args)


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        args,
        capture_output=True,
        check=check,
        text=True,
    )


if __name__ == "__main__":
    main()
