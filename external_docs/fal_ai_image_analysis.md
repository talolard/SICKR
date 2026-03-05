# fal.ai notes for image analysis tools

## Python client usage
- Library: `fal-client` (import as `fal_client`)
- Auth: client expects `FAL_KEY` in environment.
- We additionally support `FAI_AI_API_KEY` and copy it to `FAL_KEY` at runtime for compatibility.

## Call pattern used in this repo
1. Resolve uploaded image from local attachment store.
2. Upload file to fal storage (`upload_file_async`) to get `image_url`.
3. Invoke model (`subscribe_async`) with typed arguments.
4. Download returned artifact URLs and persist as local attachments.

## Model IDs currently used
- Object detection: `fal-ai/florence-2-large/object-detection`
- Depth estimation: `fal-ai/imageutils/marigold-depth`
- Segmentation: `fal-ai/sam-3/image`

## Notes
- Tool wrappers are intentionally tolerant of slight response-shape differences and normalize to stable typed outputs.
- Depth outputs are treated as relative depth only unless a known real-world scale reference is provided.
