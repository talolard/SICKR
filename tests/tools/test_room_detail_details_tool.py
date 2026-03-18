from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from PIL import Image
from pydantic_ai import BinaryContent, RunContext
from pydantic_ai.exceptions import UnexpectedModelBehavior

from ikea_agent.chat.agents.image_analysis.deps import ImageAnalysisAgentDeps
from ikea_agent.chat.agents.image_analysis.toolset import get_room_detail_details_from_photo
from ikea_agent.chat.agents.state import ImageAnalysisAgentState
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.shared.types import AttachmentRef
from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    RoomDetailDetailsExtraction,
    RoomDetailDetailsFromPhotoRequest,
    RoomDetailDetailsFromPhotoResult,
    RoomDetailObjectsOfInterest,
)
from ikea_agent.tools.image_analysis.room_detail_details import (
    RoomDetailDetailsError,
)
from ikea_agent.tools.image_analysis.room_detail_details import (
    get_room_detail_details_from_photo as run_room_detail_details_from_photo,
)


def _make_image_bytes() -> bytes:
    image = Image.new("RGB", (320, 240), color=(240, 240, 240))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _store_attachment(
    store: AttachmentStore,
    *,
    filename: str = "room.png",
) -> AttachmentRefPayload:
    stored = store.save_image_bytes(
        content=_make_image_bytes(),
        mime_type="image/png",
        filename=filename,
    )
    return AttachmentRefPayload.from_ref(stored.ref)


class _FakeRunResult:
    def __init__(self, output: RoomDetailDetailsExtraction) -> None:
        self.output = output


class _FakeAgent:
    def __init__(
        self,
        *,
        output: RoomDetailDetailsExtraction | None = None,
        error: Exception | None = None,
        seen_contents: list[list[str | BinaryContent]] | None = None,
    ) -> None:
        self._output = output
        self._error = error
        self._seen_contents = seen_contents

    async def run(self, contents: list[str | BinaryContent]) -> _FakeRunResult:
        if self._seen_contents is not None:
            self._seen_contents.append(contents)
        if self._error is not None:
            raise self._error
        assert self._output is not None
        return _FakeRunResult(self._output)


def test_room_detail_service_preserves_source_images_and_grouped_objects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AttachmentStore(tmp_path / "attachments")
    first = _store_attachment(store, filename="room-1.png")
    second = _store_attachment(store, filename="room-2.png")
    seen_contents: list[list[str | BinaryContent]] = []

    def _build_extractor(*, use_native_output: bool, **_: object) -> _FakeAgent:
        assert use_native_output is True
        return _FakeAgent(
            output=RoomDetailDetailsExtraction(
                room_type="living_room",
                confidence="high",
                cross_image_room_relationship="same_room_likely",
                objects_of_interest=RoomDetailObjectsOfInterest(
                    major_furniture=["sofa", "coffee table"],
                    fixtures=["radiator"],
                    lifestyle_indicators=["cat", "cat"],
                    other_items=["rug"],
                ),
                image_assessments=[],
                notes=["Likely the same room.", "Likely the same room."],
            ),
            seen_contents=seen_contents,
        )

    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.room_detail_details.build_room_detail_details_extractor",
        _build_extractor,
    )

    result = asyncio.run(
        run_room_detail_details_from_photo(
            request=RoomDetailDetailsFromPhotoRequest(images=[first, second]),
            attachment_store=store,
        )
    )

    assert len(seen_contents) == 1
    assert seen_contents[0][0] == "Analyze these room photos as one image set."
    assert isinstance(seen_contents[0][1], BinaryContent)
    assert [image.attachment_id for image in result.images] == [
        first.attachment_id,
        second.attachment_id,
    ]
    assert result.room_type == "living_room"
    assert result.objects_of_interest.major_furniture == ["sofa", "coffee table"]
    assert result.objects_of_interest.lifestyle_indicators == ["cat"]
    assert result.notes == ["Likely the same room."]
    assert [assessment.image_index for assessment in result.image_assessments] == [0, 1]


def test_room_detail_service_falls_back_to_prompted_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AttachmentStore(tmp_path / "attachments")
    payload = _store_attachment(store)
    native_calls: list[bool] = []

    def _build_extractor(*, use_native_output: bool, **_: object) -> _FakeAgent:
        native_calls.append(use_native_output)
        if use_native_output:
            return _FakeAgent(error=UnexpectedModelBehavior("native failed"))
        return _FakeAgent(output=RoomDetailDetailsExtraction(room_type="bedroom"))

    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.room_detail_details.build_room_detail_details_extractor",
        _build_extractor,
    )

    result = asyncio.run(
        run_room_detail_details_from_photo(
            request=RoomDetailDetailsFromPhotoRequest(images=[payload]),
            attachment_store=store,
        )
    )

    assert native_calls == [True, False]
    assert result.room_type == "bedroom"


def test_toolset_room_detail_defaults_to_all_uploaded_images(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AttachmentStore(tmp_path / "attachments")
    first = _store_attachment(store, filename="room-1.png")
    second = _store_attachment(store, filename="room-2.png")
    captured_ids: list[str] = []

    async def _fake_run_room_detail_details_from_photo(
        *,
        request: RoomDetailDetailsFromPhotoRequest,
        attachment_store: AttachmentStore,
        settings: object | None = None,
    ) -> RoomDetailDetailsFromPhotoResult:
        _ = (attachment_store, settings)
        captured_ids.extend(image.attachment_id for image in request.images)
        return RoomDetailDetailsFromPhotoResult(
            caption="Room detail analysis complete.",
            images=request.images,
            room_type="living_room",
            confidence="high",
            all_images_appear_to_show_rooms=True,
            non_room_image_indices=[],
            cross_image_room_relationship="same_room_likely",
            objects_of_interest=RoomDetailObjectsOfInterest(major_furniture=["sofa"]),
            image_assessments=[],
            notes=[],
        )

    monkeypatch.setattr(
        "ikea_agent.chat.agents.image_analysis.toolset.run_room_detail_details_from_photo",
        _fake_run_room_detail_details_from_photo,
    )

    ctx = cast(
        "RunContext[ImageAnalysisAgentDeps]",
        SimpleNamespace(
            deps=SimpleNamespace(
                attachment_store=store,
                runtime=object(),
                state=ImageAnalysisAgentState(
                    attachments=[
                        AttachmentRef(
                            attachment_id=first.attachment_id,
                            mime_type=first.mime_type,
                            uri=first.uri,
                            width=first.width,
                            height=first.height,
                            file_name=first.file_name,
                        ),
                        AttachmentRef(
                            attachment_id=second.attachment_id,
                            mime_type=second.mime_type,
                            uri=second.uri,
                            width=second.width,
                            height=second.height,
                            file_name=second.file_name,
                        ),
                    ]
                ),
            )
        ),
    )

    asyncio.run(get_room_detail_details_from_photo(ctx, None))

    assert captured_ids == [first.attachment_id, second.attachment_id]


def test_room_detail_service_raises_clean_error_when_extractor_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AttachmentStore(tmp_path / "attachments")
    payload = _store_attachment(store)

    def _build_extractor(*, use_native_output: bool, **kwargs: object) -> _FakeAgent:
        del kwargs
        _use_native_output = use_native_output
        assert isinstance(_use_native_output, bool)
        return _FakeAgent(error=RuntimeError("structured output parse failed"))

    monkeypatch.setattr(
        "ikea_agent.tools.image_analysis.room_detail_details.build_room_detail_details_extractor",
        _build_extractor,
    )

    with pytest.raises(RoomDetailDetailsError, match="Room detail extraction failed"):
        asyncio.run(
            run_room_detail_details_from_photo(
                request=RoomDetailDetailsFromPhotoRequest(images=[payload]),
                attachment_store=store,
            )
        )
