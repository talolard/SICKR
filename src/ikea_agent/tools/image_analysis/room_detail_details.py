"""PydanticAI-backed room-detail extraction for multi-image room photos."""

from __future__ import annotations

from logging import getLogger

from pydantic_ai import Agent, BinaryContent, NativeOutput, PromptedOutput
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.google import GoogleModelSettings
from pydantic_ai.models.test import TestModel

from ikea_agent.chat.modeling import build_google_or_test_model
from ikea_agent.chat_app.attachments import AttachmentStore
from ikea_agent.config import AppSettings, get_settings
from ikea_agent.tools.image_analysis.models import (
    RoomDetailDetailsExtraction,
    RoomDetailDetailsFromPhotoRequest,
    RoomDetailDetailsFromPhotoResult,
    RoomDetailObjectsOfInterest,
    RoomPhotoImageAssessment,
)

logger = getLogger(__name__)

ROOM_DETAIL_DETAILS_PROMPT = """
You analyze user-provided room photos for an interior-design assistant.

Return structured room observations for the full image set.

Tasks:
- Decide whether each image appears to show an indoor room.
- Infer the most likely room type from the allowed enum values.
- Determine the cross-image relationship:
  - `same_room_likely` if the images likely show the same room from different angles.
  - `different_rooms_confirmed` only if you are confident the images show different rooms.
  - `uncertain` if you cannot tell reliably.
- Populate grouped object lists using short noun phrases only.

Object grouping examples:
- `major_furniture`: sofa, sectional couch, bed, bunk bed, crib, dining table, desk,
  bookshelf, wardrobe, dresser, nightstand, coffee table, tv stand, kitchen island,
  bar stools.
- `fixtures`: toilet, sink, bathtub, shower, vanity, stove, oven, refrigerator,
  dishwasher, countertop, upper cabinets, fireplace, radiator, ceiling fan,
  washing machine, dryer.
- `lifestyle_indicators`: dog, cat, litter box, diapers, stroller, school backpack,
  Legos, toys, gaming chair, monitor setup, laundry basket, guitar, bike helmet,
  pet bed, baby gate.
- `other_items`: rug, curtains, wall art, mirror, plant, storage bins, boxes,
  vacuum, clutter, shoe rack.

Rules:
- Prefer `unknown` over guessing when room type evidence is weak.
- Do not hallucinate objects that are not visible.
- Use short concrete labels, not long descriptions.
- Do not duplicate one item across multiple object groups.
- Keep notes brief and concrete.
- If an image does not look like an indoor room, mark that image accordingly.
""".strip()

ROOM_DETAIL_DETAILS_CAPTION = "Room detail analysis complete."


class RoomDetailDetailsError(ValueError):
    """Raised when room-detail extraction cannot complete successfully."""


class RoomDetailDetailsExtractorService:
    """Orchestrate one structured multimodal extraction over an uploaded image set."""

    def __init__(
        self,
        *,
        attachment_store: AttachmentStore,
        settings: AppSettings | None = None,
    ) -> None:
        """Store runtime dependencies shared by one extraction run."""

        self._attachment_store = attachment_store
        self._settings = settings or get_settings()

    async def get_room_detail_details_from_photo(
        self,
        request: RoomDetailDetailsFromPhotoRequest,
    ) -> RoomDetailDetailsFromPhotoResult:
        """Run room-detail extraction and enrich the structured result with attachments."""

        contents = self._build_contents(request)
        extraction = await self._run_extractor(contents)
        return self._build_result(request=request, extraction=extraction)

    def _build_contents(
        self, request: RoomDetailDetailsFromPhotoRequest
    ) -> list[str | BinaryContent]:
        contents: list[str | BinaryContent] = ["Analyze these room photos as one image set."]
        for image in request.images:
            stored = self._attachment_store.resolve(image.attachment_id)
            if stored is None:
                msg = f"Attachment not found: {image.attachment_id}"
                raise RoomDetailDetailsError(msg)
            contents.append(
                BinaryContent(data=stored.path.read_bytes(), media_type=image.mime_type)
            )
        return contents

    async def _run_extractor(
        self,
        contents: list[str | BinaryContent],
    ) -> RoomDetailDetailsExtraction:
        try:
            native_agent = build_room_detail_details_extractor(
                settings=self._settings,
                use_native_output=True,
            )
            native_result = await native_agent.run(contents)
        except UnexpectedModelBehavior:
            logger.info("room_detail_details_native_output_failed_fallback_to_prompted")
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            msg = f"Room detail extraction failed before fallback: {exc}"
            raise RoomDetailDetailsError(msg) from exc
        else:
            return native_result.output

        try:
            prompted_agent = build_room_detail_details_extractor(
                settings=self._settings,
                use_native_output=False,
            )
            prompted_result = await prompted_agent.run(contents)
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            msg = f"Room detail extraction failed: {exc}"
            raise RoomDetailDetailsError(msg) from exc
        else:
            return prompted_result.output

    def _build_result(
        self,
        *,
        request: RoomDetailDetailsFromPhotoRequest,
        extraction: RoomDetailDetailsExtraction,
    ) -> RoomDetailDetailsFromPhotoResult:
        image_count = len(request.images)
        normalized_assessments = _normalize_image_assessments(
            extraction.image_assessments,
            image_count=image_count,
        )
        normalized_non_room_indices = _normalize_non_room_image_indices(
            extraction.non_room_image_indices,
            image_assessments=normalized_assessments,
            image_count=image_count,
        )
        return RoomDetailDetailsFromPhotoResult(
            caption=ROOM_DETAIL_DETAILS_CAPTION,
            images=request.images,
            room_type=extraction.room_type,
            confidence=extraction.confidence,
            all_images_appear_to_show_rooms=_resolve_all_images_are_rooms(
                extraction.all_images_appear_to_show_rooms,
                non_room_image_indices=normalized_non_room_indices,
                image_assessments=normalized_assessments,
            ),
            non_room_image_indices=normalized_non_room_indices,
            cross_image_room_relationship=extraction.cross_image_room_relationship,
            objects_of_interest=_normalize_objects_of_interest(extraction.objects_of_interest),
            image_assessments=normalized_assessments,
            notes=_normalize_string_list(extraction.notes),
        )


def build_room_detail_details_extractor(
    *,
    settings: AppSettings,
    use_native_output: bool,
) -> Agent[None, RoomDetailDetailsExtraction]:
    """Build the internal structured-output extractor used by the tool wrapper."""

    model = build_google_or_test_model(
        settings=settings,
        model_name=settings.gemini_image_analysis_model,
        google_model_settings=GoogleModelSettings(),
        disabled_reason=(
            "Live model requests are disabled. "
            "Set ALLOW_MODEL_REQUESTS=1 and GEMINI_API_KEY/GOOGLE_API_KEY for real responses."
        ),
    )
    if isinstance(model, TestModel):
        msg = model.custom_output_text or "Room detail extraction requires a live Gemini model."
        raise RoomDetailDetailsError(msg)

    output_type = (
        NativeOutput(
            RoomDetailDetailsExtraction,
            name="RoomDetailDetailsExtraction",
            description="Structured room-photo extraction for one image set.",
        )
        if use_native_output
        else PromptedOutput(RoomDetailDetailsExtraction)
    )
    return Agent[None, RoomDetailDetailsExtraction](
        model=model,
        output_type=output_type,
        name="room_detail_details_extractor",
        instructions=ROOM_DETAIL_DETAILS_PROMPT,
    )


async def get_room_detail_details_from_photo(
    *,
    request: RoomDetailDetailsFromPhotoRequest,
    attachment_store: AttachmentStore,
    settings: AppSettings | None = None,
) -> RoomDetailDetailsFromPhotoResult:
    """Public helper used by the image-analysis toolset."""

    service = RoomDetailDetailsExtractorService(
        attachment_store=attachment_store,
        settings=settings,
    )
    return await service.get_room_detail_details_from_photo(request)


def _normalize_image_assessments(
    image_assessments: list[RoomPhotoImageAssessment],
    *,
    image_count: int,
) -> list[RoomPhotoImageAssessment]:
    assessments_by_index: dict[int, RoomPhotoImageAssessment] = {}
    for assessment in image_assessments:
        if assessment.image_index < 0 or assessment.image_index >= image_count:
            continue
        assessments_by_index[assessment.image_index] = assessment.model_copy(
            update={"notes": _normalize_string_list(assessment.notes)}
        )
    return [
        assessments_by_index.get(index, RoomPhotoImageAssessment(image_index=index))
        for index in range(image_count)
    ]


def _normalize_non_room_image_indices(
    non_room_image_indices: list[int],
    *,
    image_assessments: list[RoomPhotoImageAssessment],
    image_count: int,
) -> list[int]:
    derived = {
        assessment.image_index
        for assessment in image_assessments
        if assessment.appears_to_show_room is False
    }
    requested = {index for index in non_room_image_indices if 0 <= index < image_count}
    return sorted(requested | derived)


def _resolve_all_images_are_rooms(
    declared_value: bool | None,
    *,
    non_room_image_indices: list[int],
    image_assessments: list[RoomPhotoImageAssessment],
) -> bool | None:
    if declared_value is not None:
        return declared_value
    if non_room_image_indices:
        return False
    if image_assessments and all(
        assessment.appears_to_show_room is True for assessment in image_assessments
    ):
        return True
    if any(assessment.appears_to_show_room is False for assessment in image_assessments):
        return False
    return None


def _normalize_objects_of_interest(
    objects_of_interest: RoomDetailObjectsOfInterest,
) -> RoomDetailObjectsOfInterest:
    return RoomDetailObjectsOfInterest(
        major_furniture=_normalize_string_list(objects_of_interest.major_furniture),
        fixtures=_normalize_string_list(objects_of_interest.fixtures),
        lifestyle_indicators=_normalize_string_list(objects_of_interest.lifestyle_indicators),
        other_items=_normalize_string_list(objects_of_interest.other_items),
    )


def _normalize_string_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip()
        if not stripped:
            continue
        folded = stripped.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        normalized.append(stripped)
    return normalized
