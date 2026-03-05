"""Embedding client wrappers for Gemini APIs."""

from __future__ import annotations

from dataclasses import dataclass

from google import genai
from google.genai import types as genai_types


@dataclass(frozen=True, slots=True)
class EmbeddingClientConfig:
    """Runtime options for embedding client creation."""

    project_id: str
    location: str
    model_name: str
    api_key: str | None = None
    output_dimensions: int | None = None


class VertexGeminiEmbeddingClient:
    """Gemini embedding client backed by Vertex AI credentials."""

    def __init__(self, config: EmbeddingClientConfig) -> None:
        self._model_name = config.model_name
        self._output_dimensions = config.output_dimensions
        if config.api_key:
            self._client = genai.Client(api_key=config.api_key)
        else:
            self._client = genai.Client(
                vertexai=True,
                project=config.project_id,
                location=config.location,
            )

    def embed_many(self, texts: list[str]) -> list[tuple[float, ...]]:
        """Embed a list of texts and return vectors in source order."""

        config: genai_types.EmbedContentConfigDict = {"task_type": "RETRIEVAL_DOCUMENT"}
        if self._output_dimensions is not None:
            config["output_dimensionality"] = self._output_dimensions

        response = self._client.models.embed_content(
            model=self._model_name,
            contents=texts,
            config=config,
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

    def embed_document(self, text: str) -> tuple[float, ...]:
        """Embed one document text using non-batch embedding path."""

        config: genai_types.EmbedContentConfigDict = {"task_type": "RETRIEVAL_DOCUMENT"}
        if self._output_dimensions is not None:
            config["output_dimensionality"] = self._output_dimensions

        response = self._client.models.embed_content(
            model=self._model_name,
            contents=text,
            config=config,
        )
        if response.embeddings is None or not response.embeddings:
            return ()

        values = response.embeddings[0].values
        if values is None:
            return ()

        return tuple(float(value) for value in values)

    def embed_query(self, query_text: str) -> tuple[float, ...]:
        """Embed one query using query-optimized task type."""

        config: genai_types.EmbedContentConfigDict = {"task_type": "RETRIEVAL_QUERY"}
        if self._output_dimensions is not None:
            config["output_dimensionality"] = self._output_dimensions

        response = self._client.models.embed_content(
            model=self._model_name,
            contents=[query_text],
            config=config,
        )
        if response.embeddings is None or not response.embeddings:
            return ()

        values = response.embeddings[0].values
        if values is None:
            return ()

        return tuple(float(value) for value in values)


def build_generation_client(config: EmbeddingClientConfig) -> genai.Client:
    """Build a Gemini client for structured generation calls."""

    if config.api_key:
        return genai.Client(api_key=config.api_key)

    return genai.Client(
        vertexai=True,
        project=config.project_id,
        location=config.location,
    )
