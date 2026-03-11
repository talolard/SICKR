# Image Analysis Tools

## Purpose

Provide attachment-driven image analysis capabilities for room understanding and photo-guided iteration.

These tools are backed by fal.ai model endpoints and are registered directly on the active PydanticAI agent.

## Registered tools

- `detect_objects_in_image`
  - Model: `fal-ai/florence-2-large/object-detection`
  - Returns structured detections and optional overlay image.
- `estimate_depth_map`
  - Model: `fal-ai/imageutils/marigold-depth`
  - Returns relative depth artifacts and parameters used.
- `segment_image_with_prompt`
  - Model: `fal-ai/sam-3/image`
  - Returns prompt-targeted masks; supports `return_multiple_masks` with up to 32 masks.
- `analyze_room_photo`
  - Combined tool that runs object detection and depth estimation in one call.

## Input and output contract

- All requests take `image: AttachmentRefPayload` pointing to an uploaded image.
- All responses include:
  - `caption: str`
  - `images: list[AttachmentRefPayload]`
- Each tool adds typed structured fields:
  - Detections (`label`, pixel + normalized boxes)
  - Depth metadata (`parameters_used`)
  - Masks (`label`, optional `query`, optional `score`, optional `bbox_xyxy_px`, `mask_image`)
  - Segmentation query summary (`queries`, `query_results`)
  - Combined hints (`room_hints`)

### SAM-3 segmentation request shape

`SegmentationRequest` now aligns with the fal SAM-3 API and supports multi-target prompts:

- `prompt: str | None`
- `queries: list[str]` (up to 32 query strings)
- `return_multiple_masks: bool` (default `true`)
- `max_masks: int` (`1..32`, default `32`)
- `include_scores: bool`
- `include_boxes: bool`
- `include_mask_file: bool`
- `apply_mask: bool`
- `output_format: "jpeg" | "png" | "webp"`
- `sync_mode: bool`

Validation rule:

- At least one of `prompt` or non-empty `queries` must be provided.

## Environment and authentication

Set one of:

- `FAI_AI_API_KEY` (repo convention)
- `FAL_KEY` (fal-client native)

Runtime behavior:

- If `FAL_KEY` is missing and `FAI_AI_API_KEY` exists, runtime maps `FAI_AI_API_KEY` to `FAL_KEY`.

## Execution flow

Shared core is implemented in `src/ikea_agent/tools/image_analysis/core.py`:

1. Resolve uploaded attachment via `AttachmentStore`.
2. Upload source file to fal storage (`upload_file_async`) to get `image_url`.
3. Call target model (`subscribe_async`) with typed args.
4. Download returned artifact URLs.
5. Persist outputs back into `AttachmentStore` and return local attachment refs.

This keeps UI rendering stable and avoids dependency on external expiring URLs.

## Notes on reliability

- Object detection and segmentation are best-effort and can return false positives.
- For segmentation runs with multiple queries, mask-to-query attribution may be ambiguous; query summaries may report `unattributed`.
- Depth from marigold is relative unless a real-world scale reference is provided.
- Missing attachments return explicit tool errors (`Attachment not found: ...`).

## Segmentation feedback persistence

- Segmentation results now include `analysis_id` when persistence is enabled.
- UI can persist per-mask user feedback (`confirm`/`reject`/`uncertain`) to:
  - `POST /api/threads/{thread_id}/analyses/{analysis_id}/feedback`
  - `GET /api/threads/{thread_id}/analyses/{analysis_id}/feedback`
- Stored fields include optional `mask_ordinal`, `mask_label`, `query_text`, and freeform `note`.

## UI rendering

Dedicated CopilotKit tool renderers:

- `ObjectDetectionToolRenderer`
- `DepthEstimationToolRenderer`
- `SegmentationToolRenderer`
- `RoomPhotoAnalysisToolRenderer`

Registry: `ui/src/components/copilotkit/CopilotToolRenderers.tsx`
