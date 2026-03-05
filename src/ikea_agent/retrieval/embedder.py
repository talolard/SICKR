"""PydanticAI embedding adapter for query and document vectors."""

from __future__ import annotations

from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings

from ikea_agent.config import AppSettings


class PydanticAIEmbeddingClient:
    """Typed embedding adapter wrapping pydantic-ai providers.

    The runtime uses this adapter to keep embedding behavior explicit while
    avoiding provider-specific SDK client code in the retrieval layer.
    """

    def __init__(self, settings: AppSettings) -> None:
        model = settings.embedding_model_uri
        embedding_settings = EmbeddingSettings(dimensions=settings.embedding_dimensions)
        self._embedder = Embedder(model, settings=embedding_settings)

    async def embed_query(self, query_text: str) -> tuple[float, ...]:
        """Return one query embedding with configured dimensions."""

        response = await self._embedder.embed_query(query_text)
        if not response.embeddings:
            return ()
        return tuple(float(value) for value in response.embeddings[0])
