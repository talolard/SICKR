"""Embedding client wrappers for Gemini APIs."""

from __future__ import annotations

from dataclasses import dataclass

from google import genai


@dataclass(frozen=True, slots=True)
class EmbeddingClientConfig:
    """Runtime options for embedding client creation."""

    project_id: str
    location: str
    model_name: str


class VertexGeminiEmbeddingClient:
    """Gemini embedding client backed by Vertex AI credentials."""

    def __init__(self, config: EmbeddingClientConfig) -> None:
        self._model_name = config.model_name
        self._client = genai.Client(
            vertexai=True,
            project=config.project_id,
            location=config.location,
        )

    def embed_many(self, texts: list[str]) -> list[tuple[float, ...]]:
        """Embed a list of texts and return vectors in source order."""

        response = self._client.models.embed_content(
            model=self._model_name,
            contents=texts,
            config={"task_type": "RETRIEVAL_DOCUMENT"},
        )

        if response.embeddings is None:
            return []

        vectors: list[tuple[float, ...]] = []
        for item in response.embeddings:
            if item.values is None:
                vectors.append(())
                continue
            values = item.values
            vectors.append(tuple(float(value) for value in values))

        return vectors

    def embed_query(self, query_text: str) -> tuple[float, ...]:
        """Embed one query using query-optimized task type."""

        response = self._client.models.embed_content(
            model=self._model_name,
            contents=[query_text],
            config={"task_type": "RETRIEVAL_QUERY"},
        )
        if response.embeddings is None or not response.embeddings:
            return ()

        values = response.embeddings[0].values
        if values is None:
            return ()

        return tuple(float(value) for value in values)
