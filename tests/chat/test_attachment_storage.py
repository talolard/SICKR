from __future__ import annotations

from io import BytesIO
from pathlib import Path, PurePosixPath

import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from ikea_agent.chat_app.attachment_storage import (
    AttachmentStorageError,
    LegacyPathStorageLocator,
    LocalAttachmentStorageBackend,
    LocalStorageLocator,
    S3AttachmentStorageBackend,
    StorageObjectDescriptor,
    build_local_storage_locator,
    parse_storage_locator,
)


def test_s3_attachment_storage_backend_persists_and_materializes_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_PROFILE", raising=False)
    backend = S3AttachmentStorageBackend(
        root_dir=tmp_path / "artifacts",
        bucket="private-artifacts",
        prefix="dev",
        region_name="eu-central-1",
    )
    expected_key = "dev/attachments/generated/thread-1/run-1/asset-1.png"

    with Stubber(backend._client) as stubber:
        stubber.add_response(
            "put_object",
            {},
            {
                "Body": b"png-data",
                "Bucket": "private-artifacts",
                "Key": expected_key,
                "ContentType": "image/png",
            },
        )
        stubber.add_response(
            "get_object",
            {"Body": StreamingBody(BytesIO(b"png-data"), len(b"png-data"))},
            {
                "Bucket": "private-artifacts",
                "Key": expected_key,
            },
        )

        saved = backend.save_attachment(
            descriptor=StorageObjectDescriptor(
                attachment_id="asset-1",
                thread_id="thread-1",
                run_id="run-1",
                file_name="mask.png",
                mime_type="image/png",
                kind="analysis_output",
            ),
            content=b"png-data",
        )
        assert (
            saved.locator
            == "s3://private-artifacts/dev/attachments/generated/thread-1/run-1/asset-1.png"
        )
        assert saved.materialized_path.read_bytes() == b"png-data"

        saved.materialized_path.unlink()
        materialized_path = backend.materialize_locator(
            locator=saved.locator,
            attachment_id="asset-1",
            file_name="mask.png",
            mime_type="image/png",
        )

    assert materialized_path.read_bytes() == b"png-data"


def test_parse_storage_locator_handles_local_legacy_and_invalid_s3_paths(
    tmp_path: Path,
) -> None:
    local_locator = parse_storage_locator("local://attachments/user-upload/thread-1/example.png")
    assert isinstance(local_locator, LocalStorageLocator)
    assert local_locator.relative_path.as_posix() == "attachments/user-upload/thread-1/example.png"

    legacy_path = tmp_path / "legacy.bin"
    legacy_path.write_bytes(b"legacy")
    legacy_locator = parse_storage_locator(str(legacy_path))
    assert isinstance(legacy_locator, LegacyPathStorageLocator)
    assert legacy_locator.path == legacy_path

    with pytest.raises(AttachmentStorageError, match="Invalid S3 storage locator"):
        parse_storage_locator("s3://missing-key")


def test_local_attachment_storage_backend_materializes_local_and_legacy_paths(
    tmp_path: Path,
) -> None:
    backend = LocalAttachmentStorageBackend(root_dir=tmp_path / "artifacts")
    relative_path = PurePosixPath("attachments/user-upload/thread-1/example.png")
    persisted_path = backend._root_dir / relative_path
    persisted_path.parent.mkdir(parents=True, exist_ok=True)
    persisted_path.write_bytes(b"local")

    resolved_local = backend.materialize_locator(
        locator=build_local_storage_locator(relative_path),
        attachment_id="asset-local",
        file_name="example.png",
        mime_type="image/png",
    )
    assert resolved_local == persisted_path

    legacy_path = tmp_path / "legacy.png"
    legacy_path.write_bytes(b"legacy")
    resolved_legacy = backend.materialize_locator(
        locator=str(legacy_path),
        attachment_id="asset-legacy",
        file_name="legacy.png",
        mime_type="image/png",
    )
    assert resolved_legacy == legacy_path

    with pytest.raises(AttachmentStorageError, match="cannot resolve S3 locator"):
        backend.materialize_locator(
            locator="s3://bucket/path/example.png",
            attachment_id="asset-s3",
            file_name="example.png",
            mime_type="image/png",
        )


def test_s3_attachment_storage_backend_handles_cached_local_and_missing_remote_objects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_PROFILE", raising=False)
    backend = S3AttachmentStorageBackend(
        root_dir=tmp_path / "artifacts",
        bucket="private-artifacts",
        prefix="dev",
        region_name="eu-central-1",
    )

    local_relative_path = PurePosixPath("attachments/user-upload/thread-1/local.png")
    local_path = backend._root_dir / local_relative_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(b"local-bytes")
    assert (
        backend.materialize_locator(
            locator=build_local_storage_locator(local_relative_path),
            attachment_id="asset-local",
            file_name="local.png",
            mime_type="image/png",
        )
        == local_path
    )

    cached_path = backend._materialized_root / "asset-cached.png"
    cached_path.parent.mkdir(parents=True, exist_ok=True)
    cached_path.write_bytes(b"cached")
    cached_locator = (
        "s3://private-artifacts/dev/attachments/generated/thread-1/run-1/asset-cached.png"
    )
    assert (
        backend.materialize_locator(
            locator=cached_locator,
            attachment_id="asset-cached",
            file_name="asset-cached.png",
            mime_type="image/png",
        )
        == cached_path
    )

    with Stubber(backend._client) as stubber:
        stubber.add_client_error(
            "get_object",
            service_error_code="NoSuchKey",
            expected_params={
                "Bucket": "private-artifacts",
                "Key": "dev/attachments/generated/thread-1/run-1/asset-missing.png",
            },
        )
        with pytest.raises(FileNotFoundError, match="asset-missing"):
            backend.materialize_locator(
                locator="s3://private-artifacts/dev/attachments/generated/thread-1/run-1/asset-missing.png",
                attachment_id="asset-missing",
                file_name="asset-missing.png",
                mime_type="image/png",
            )

    assert backend.find_local_path(attachment_id="asset-missing") is None
