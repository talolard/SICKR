"""Gemini-backed room-detail extraction for one or more uploaded room photos."""

from __future__ import annotations

from logging import getLogger
from typing import get_args

from pydantic_ai import Agent, BinaryContent
from pydantic_ai.exceptions import UserError
from pydantic_ai.models.google import GoogleModelSettings
from pydantic_ai.models.test import TestModel
from pydantic_ai.output import NativeOutput, PromptedOutput

from ikea_agent.chat.modeling import build_google_or_test_model
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.config import AppSettings, get_settings
from ikea_agent.shared.types import RoomType
from ikea_agent.tools.image_analysis.models import (
    AttachmentRefPayload,
    RoomDetailDetailsFromPhotoRequest,
    RoomDetailDetailsFromPhotoResult,
)

logger = getLogger(__name__)

_ROOM_TYPE_VALUES = ", ".join(get_args(RoomType))
_DISABLED_REASON = (
    "Room-detail photo analysis requires live Gemini model requests. "
    "Set ALLOW_MODEL_REQUESTS=1 and GEMINI_API_KEY/GOOGLE_API_KEY for real responses."
)
_USER_PROMPT = "Analyze the attached room photos for interior-design context."
_EXTRACTION_PROMPT = f"""
You are analyzing a set of user-provided photos for interior-design help.

Return only structured output that matches the provided schema.

Tasks:
- Decide whether each image appears to show an indoor room.
- Infer the most likely overall room type from these allowed values:
  `{_ROOM_TYPE_VALUES}`.
- Decide whether the images most likely show the same room, clearly show different
  rooms, or remain uncertain.
- Only return `different_rooms_confirmed` when you are confident the images are
  definitely different rooms.
- Prefer `unknown` over guessing when the room type is unclear.

Populate `objects_of_interest` with short concrete noun phrases.

Examples for `major_furniture`:
- sofa
- sectional couch
- bed
- bunk bed
- crib
- dining table
- desk
- bookshelf
- wardrobe
- dresser
- nightstand
- coffee table
- tv stand
- kitchen island
- bar stools

Examples for `fixtures`:
- toilet
- sink
- bathtub
- shower
- vanity
- stove
- oven
- refrigerator
- dishwasher
- countertop
- upper cabinets
- fireplace
- radiator
- ceiling fan
- washing machine
- dryer

Examples for `lifestyle_indicators`:
- dog
- cat
- litter box
- diapers
- stroller
- school backpack
- Legos
- toys
- gaming chair
- monitor setup
- laundry basket
- guitar
- bike helmet
- pet bed
- baby gate

Examples for `other_items`:
- rug
- curtains
- wall art
- mirror
- plant
- storage bins
- boxes
- vacuum
- clutter
- shoe rack

Rules:
- Use short concrete labels, not long descriptions.
- Do not duplicate the same object across multiple lists.
- Do not hallucinate unseen objects.
- Do not assume all images show the same room.
- Notes should stay brief, concrete, and uncertainty-aware.
""".strip()


class RoomDetailDetailsError(ValueError):
    """Raised when the Gemini room-detail extraction cannot complete."""


def build_room_detail_details_extractor(
    *,
    settings: AppSettings | None = None,
    prompted_output: bool = False,
) -> Agent[None, RoomDetailDetailsFromPhotoResult]:
    """Build the internal extractor agent used by the room-detail tool."""

    resolved_settings = settings or get_settings()
    model = build_google_or_test_model(
        settings=resolved_settings,
        model_name=resolved_settings.gemini_image_analysis_model,
        google_model_settings=GoogleModelSettings(),
        disabled_reason=_DISABLED_REASON,
    )
    if isinstance(model, TestModel):
        raise RoomDetailDetailsError(_DISABLED_REASON)

    output_type = (
        PromptedOutput(RoomDetailDetailsFromPhotoResult)
        if prompted_output
        else NativeOutput(RoomDetailDetailsFromPhotoResult)
    )
    return Agent[None, RoomDetailDetailsFromPhotoResult](
        model=model,
        output_type=output_type,
        instructions=_EXTRACTION_PROMPT,
        name="room_detail_details_extractor",
    )


class RoomDetailDetailsService:
    """Resolve attachments and run one structured Gemini extraction over the image set."""

    def __init__(self, attachment_store: AttachmentStore) -> None:
        """Store the shared attachment repository used to load uploaded images."""

        self._attachment_store = attachment_store

    async def get_room_detail_details_from_photo(
        self,
        request: RoomDetailDetailsFromPhotoRequest,
    ) -> RoomDetailDetailsFromPhotoResult:
        """Analyze the full uploaded image set in one Gemini multimodal request."""

        user_content = self._build_user_content(request.images)
        result = await self._run_extractor(user_content)
        self._validate_image_indices(result=result, image_count=len(request.images))
        return result

    def _build_user_content(
        self,
        images: list[AttachmentRefPayload],
    ) -> list[str | BinaryContent]:
        contents: list[str | BinaryContent] = [_USER_PROMPT]
        for image in images:
            stored = self._attachment_store.resolve(image.attachment_id)
            if stored is None:
                msg = f"Attachment not found: {image.attachment_id}"
                raise RoomDetailDetailsError(msg)
            if not image.mime_type.startswith("image/"):
                msg = f"Attachment is not an image: {image.attachment_id}"
                raise RoomDetailDetailsError(msg)
            contents.append(
                BinaryContent(
                    data=stored.path.read_bytes(),
                    media_type=image.mime_type,
                    identifier=image.file_name or image.attachment_id,
                )
            )
        return contents

    async def _run_extractor(
        self,
        user_content: list[str | BinaryContent],
    ) -> RoomDetailDetailsFromPhotoResult:
        prompted_output = False
        while True:
            extractor = build_room_detail_details_extractor(prompted_output=prompted_output)
            try:
                run_result = await extractor.run(user_content)
            except UserError as exc:
                error_text = str(exc).lower()
                if (
                    not prompted_output
                    and "native structured output" in error_text
                    and "not supported" in error_text
                ):
                    logger.info("room_detail_details_prompted_output_fallback")
                    prompted_output = True
                    continue
                msg = f"Room-detail photo analysis failed: {exc}"
                raise RoomDetailDetailsError(msg) from exc
            except Exception as exc:
                msg = f"Room-detail photo analysis failed: {exc}"
                raise RoomDetailDetailsError(msg) from exc
            else:
                return run_result.output

    @staticmethod
    def _validate_image_indices(
        *,
        result: RoomDetailDetailsFromPhotoResult,
        image_count: int,
    ) -> None:
        seen_indices: set[int] = set()
        for assessment in result.image_assessments:
            if assessment.image_index >= image_count:
                msg = (
                    "Room-detail photo analysis returned an out-of-range image index: "
                    f"{assessment.image_index}"
                )
                raise RoomDetailDetailsError(msg)
            if assessment.image_index in seen_indices:
                msg = (
                    "Room-detail photo analysis returned duplicate image assessments for index: "
                    f"{assessment.image_index}"
                )
                raise RoomDetailDetailsError(msg)
            seen_indices.add(assessment.image_index)

        for image_index in result.non_room_image_indices:
            if image_index >= image_count:
                msg = (
                    "Room-detail photo analysis returned an out-of-range non-room image index: "
                    f"{image_index}"
                )
                raise RoomDetailDetailsError(msg)


async def get_room_detail_details_from_photo(
    *,
    request: RoomDetailDetailsFromPhotoRequest,
    attachment_store: AttachmentStore,
) -> RoomDetailDetailsFromPhotoResult:
    """Public tool wrapper for Gemini room-detail extraction."""

    service = RoomDetailDetailsService(attachment_store)
    return await service.get_room_detail_details_from_photo(request)
