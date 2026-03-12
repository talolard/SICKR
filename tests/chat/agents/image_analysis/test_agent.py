from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset

from ikea_agent.chat.agents.image_analysis.agent import TOOL_NAMES, build_image_analysis_agent
from ikea_agent.chat.agents.image_analysis.deps import ImageAnalysisAgentDeps
from ikea_agent.chat.agents.image_analysis.toolset import (
    get_room_detail_details_from_photo,
)
from ikea_agent.chat.agents.state import ImageAnalysisAgentState
from ikea_agent.chat.runtime import ChatRuntime
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.tools.image_analysis.models import (
    RoomDetailDetailsFromPhotoRequest,
    RoomDetailDetailsFromPhotoResult,
)


def test_image_analysis_agent_registers_room_detail_tool() -> None:
    agent = build_image_analysis_agent(explicit_model="gemini-2.0-flash")

    image_toolset = cast("FunctionToolset[object]", agent._user_toolsets[0])
    registered_tools = set(image_toolset.tools.keys())
    assert set(TOOL_NAMES).issubset(registered_tools)
    assert "get_room_detail_details_from_photo" in registered_tools


def test_room_detail_tool_defaults_to_state_attachments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AttachmentStore(tmp_path / "attachments")
    first = store.save_image_bytes(
        content=b"image-a",
        mime_type="image/png",
        filename="a.png",
    )
    second = store.save_image_bytes(
        content=b"image-b",
        mime_type="image/png",
        filename="b.png",
    )
    captured: dict[str, object] = {}

    async def _fake_run(
        *,
        request: RoomDetailDetailsFromPhotoRequest,
        attachment_store: AttachmentStore,
    ) -> RoomDetailDetailsFromPhotoResult:
        captured["request"] = request
        captured["store"] = attachment_store
        return RoomDetailDetailsFromPhotoResult(
            caption="ok",
            room_type="living_room",
            confidence="medium",
            all_images_appear_to_show_rooms=True,
            cross_image_room_relationship="same_room_likely",
        )

    monkeypatch.setattr(
        "ikea_agent.chat.agents.image_analysis.toolset.run_room_detail_details_from_photo",
        _fake_run,
    )
    monkeypatch.setattr(
        "ikea_agent.chat.agents.image_analysis.toolset.analysis_repository",
        lambda _runtime: None,
    )

    deps = ImageAnalysisAgentDeps(
        runtime=cast("ChatRuntime", SimpleNamespace()),
        attachment_store=store,
        state=ImageAnalysisAgentState(
            attachments=[first.ref, second.ref],
            thread_id="thread-image",
            run_id="run-image",
        ),
    )
    ctx = cast("RunContext[ImageAnalysisAgentDeps]", SimpleNamespace(deps=deps))

    result = asyncio.run(get_room_detail_details_from_photo(ctx, None))

    assert result.room_type == "living_room"
    request = cast("RoomDetailDetailsFromPhotoRequest", captured["request"])
    assert [image.attachment_id for image in request.images] == [
        first.ref.attachment_id,
        second.ref.attachment_id,
    ]
    assert captured["store"] is store


def test_room_detail_tool_requires_uploaded_images(tmp_path: Path) -> None:
    deps = ImageAnalysisAgentDeps(
        runtime=cast("ChatRuntime", SimpleNamespace()),
        attachment_store=AttachmentStore(tmp_path / "attachments"),
        state=ImageAnalysisAgentState(attachments=[]),
    )
    ctx = cast("RunContext[ImageAnalysisAgentDeps]", SimpleNamespace(deps=deps))

    with pytest.raises(ValueError, match="No uploaded images available"):
        asyncio.run(get_room_detail_details_from_photo(ctx, None))
