from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from ikea_agent.chat_app.attachment_storage import (
    S3AttachmentStorageBackend,
    StorageObjectDescriptor,
)


def test_s3_attachment_storage_backend_persists_and_materializes_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
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
