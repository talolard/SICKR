"""FastAPI routes for serving local product images from the sidecar catalog."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import FileResponse

from ikea_agent.chat.product_images import ProductImageLookup


def _register_product_image_routes(
    app: FastAPI,
    *,
    product_image_catalog: ProductImageLookup,
) -> None:
    @app.get("/static/product-images/{product_id}")
    async def get_primary_product_image(product_id: str) -> FileResponse:
        image_path = product_image_catalog.resolve_image_path(product_id=product_id)
        if image_path is None:
            raise HTTPException(status_code=404, detail="Product image not found.")
        return FileResponse(image_path)

    @app.get("/static/product-images/{product_id}/{ordinal}")
    async def get_ranked_product_image(
        product_id: str,
        ordinal: int = Path(ge=1),
    ) -> FileResponse:
        image_path = product_image_catalog.resolve_image_path(
            product_id=product_id,
            ordinal=ordinal,
        )
        if image_path is None:
            raise HTTPException(status_code=404, detail="Product image not found.")
        return FileResponse(image_path)
