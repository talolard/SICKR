# Search Product Images Runtime And UI

## Summary

Add local IKEA product image support to both search result cards and expanded bundle cards.
The backend serves cataloged images from the shared local image-catalog root, enriches
search and bundle payloads with ranked image URLs, and the UI renders clickable
thumbnails plus a gallery popover when multiple images are available.

## Decisions

- Use the existing canonical product key in agent/tool payloads.
- Derive raw `product_id` internally by splitting the canonical key on the last `-`.
- Read completed image-catalog outputs from `/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog`.
- Prefer `catalog.parquet` when present for a run and fall back to `catalog.jsonl`.
- Rank images by `is_og_image`, then `image_rank`, then canonical URL.
- Expose image bytes from FastAPI routes keyed by `product_id` and ordinal.
- Keep persisted bundle proposal storage unchanged and let richer item JSON round-trip.

## Implementation Notes

- Add a typed image-catalog service to runtime startup.
- Extend `ShortRetrievalResult` and `BundleProposalLineItem` with `image_urls`.
- Add a dedicated `run_search_graph` renderer instead of falling back to the generic tool card.
- Reuse one shared thumbnail plus gallery component for search and bundle surfaces.
- Show a neutral placeholder tile when no image is available.

## Validation

- Unit-test catalog indexing and product-id parsing.
- Unit-test the new FastAPI image routes.
- Update search toolset and persistence tests for `image_urls`.
- Update UI component tests for thumbnails, placeholder tiles, and gallery navigation.
