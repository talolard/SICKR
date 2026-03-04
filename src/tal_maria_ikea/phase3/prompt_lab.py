"""Prompt-lab orchestration for parallel variant comparison runs."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol
from uuid import uuid4

from django.db.utils import OperationalError, ProgrammingError
from django.template import Context, Template
from google.genai import types as genai_types
from pydantic import BaseModel, Field, ValidationError

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.ingest.embedding_client import EmbeddingClientConfig, build_generation_client
from tal_maria_ikea.phase3.repository import (
    ConversationMessageEvent,
    ConversationThreadEvent,
    PromptRunEvent,
    PromptTurnEvent,
)
from tal_maria_ikea.web.models import SystemPromptTemplate


class SummaryItem(BaseModel):
    """One recommended item from model output."""

    canonical_product_key: str
    item_name: str = Field(min_length=1)
    why: str


class SummaryResponse(BaseModel):
    """Structured output contract for prompt-lab summaries."""

    summary: str = Field(min_length=1)
    items: list[SummaryItem] = Field(default_factory=list, min_length=1)


@dataclass(frozen=True, slots=True)
class VariantRunResult:
    """One prompt variant execution result payload for display."""

    prompt_run_id: str
    turn_id: str
    variant_key: str
    variant_version: str
    status: str
    latency_ms: int
    summary: str
    items: tuple[SummaryItem, ...]
    error_message: str | None
    rendered_system_prompt: str


class PromptTemplateRow(Protocol):
    """Structural type used for prompt template execution rows."""

    id: int
    key: str
    version: str
    template_text: str


class PromptLabRepository(Protocol):
    """Repository methods used by prompt-lab service."""

    def insert_prompt_run(self, event: PromptRunEvent) -> None:
        """Persist one prompt run metadata row."""

    def insert_prompt_turn(self, event: PromptTurnEvent) -> None:
        """Persist one assistant turn response row."""

    def upsert_conversation_thread(self, event: ConversationThreadEvent) -> None:
        """Create or update one conversation thread row."""

    def insert_conversation_message(self, event: ConversationMessageEvent) -> None:
        """Persist one conversation message row."""


class PromptLabService:
    """Execute prompt variants in parallel and persist run lineage."""

    def __init__(self, repository: PromptLabRepository) -> None:
        self._repository = repository
        self._settings = get_settings()

    def run_compare(
        self,
        *,
        request_id: str,
        user_query: str,
        candidates: tuple[tuple[str, str], ...],
        variant_ids: tuple[int, ...] | None = None,
        template_rows: tuple[PromptTemplateRow, ...] | None = None,
        max_variants: int = 5,
    ) -> tuple[VariantRunResult, ...]:
        """Run active prompt variants in parallel and persist events."""

        templates: tuple[PromptTemplateRow, ...]
        if template_rows is None:
            templates = self._load_templates(variant_ids=variant_ids, max_variants=max_variants)
        else:
            templates = template_rows[:max_variants]
        if not templates:
            return ()
        conversation_id = f"compare-{request_id}"
        self._repository.upsert_conversation_thread(
            ConversationThreadEvent(
                conversation_id=conversation_id,
                request_id=request_id,
                user_ref=None,
                session_ref=None,
                title=f"Prompt compare for {user_query[:40]}",
                is_active=True,
            )
        )

        with ThreadPoolExecutor(max_workers=max(1, min(max_variants, len(templates)))) as executor:
            futures = [
                executor.submit(
                    self._run_single_variant,
                    request_id=request_id,
                    user_query=user_query,
                    candidates=candidates,
                    template_row=template_row,
                )
                for template_row in templates
            ]
            completed = [future.result() for future in as_completed(futures)]

        completed.sort(key=lambda result: (result.variant_key, result.variant_version))
        return tuple(completed)

    def _load_templates(
        self, *, variant_ids: tuple[int, ...] | None, max_variants: int
    ) -> tuple[PromptTemplateRow, ...]:
        try:
            manager: Any = SystemPromptTemplate.objects  # pyrefly: ignore[missing-attribute]
            queryset = manager.filter(is_active=True).order_by("key", "version")
            if variant_ids:
                queryset = queryset.filter(id__in=variant_ids)
            return tuple(queryset[:max_variants])
        except (OperationalError, ProgrammingError):
            return ()

    def _run_single_variant(
        self,
        *,
        request_id: str,
        user_query: str,
        candidates: tuple[tuple[str, str], ...],
        template_row: PromptTemplateRow,
    ) -> VariantRunResult:
        start = monotonic()
        context = {
            "user_query": user_query,
            "candidate_items": [
                {"canonical_product_key": key, "item_name": item_name}
                for key, item_name in candidates
            ],
        }
        rendered = Template(str(template_row.template_text)).render(Context(context))
        prompt_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        payload_hash = hashlib.sha256(
            json.dumps(context, sort_keys=True).encode("utf-8")
        ).hexdigest()
        prompt_run_id = str(uuid4())

        status = "ok"
        error_message: str | None = None
        generation_config = _summary_generation_config(system_instruction=rendered)
        response = self._generate_summary(
            system_prompt=rendered,
            user_prompt=user_query,
            candidates=candidates,
            generation_config=generation_config,
        )
        if response is None:
            status = "error"
            error_message = "No summary response generated."
            response = _fallback_summary(user_query=user_query, candidates=candidates)

        latency_ms = int((monotonic() - start) * 1000)
        self._repository.insert_prompt_run(
            PromptRunEvent(
                prompt_run_id=prompt_run_id,
                request_id=request_id,
                variant_key=str(template_row.key),
                variant_version=str(template_row.version),
                rendered_system_prompt=rendered,
                rendered_prompt_hash=prompt_hash,
                user_prompt=user_query,
                context_payload_hash=payload_hash,
                model_name=self._settings.gemini_generation_model,
                status=status,
                latency_ms=latency_ms,
                error_message=error_message,
                generation_config_json=json.dumps(generation_config, sort_keys=True),
            )
        )
        turn_id = str(uuid4())
        self._repository.insert_prompt_turn(
            PromptTurnEvent(
                turn_id=turn_id,
                prompt_run_id=prompt_run_id,
                conversation_id=f"compare-{request_id}",
                summary_text=response.summary,
                response_json=response.model_dump(),
            )
        )
        self._repository.insert_conversation_message(
            ConversationMessageEvent(
                message_id=str(uuid4()),
                conversation_id=f"compare-{request_id}",
                role="assistant",
                content_text=response.summary,
                prompt_run_id=prompt_run_id,
            )
        )
        return VariantRunResult(
            prompt_run_id=prompt_run_id,
            turn_id=turn_id,
            variant_key=str(template_row.key),
            variant_version=str(template_row.version),
            status=status,
            latency_ms=latency_ms,
            summary=response.summary,
            items=tuple(response.items),
            error_message=error_message,
            rendered_system_prompt=rendered,
        )

    def _generate_summary(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        candidates: tuple[tuple[str, str], ...],
        generation_config: genai_types.GenerateContentConfigDict,
    ) -> SummaryResponse | None:
        _ = system_prompt
        fallback = _fallback_summary(user_query=user_prompt, candidates=candidates)
        if self._settings.gemini_api_key is None:
            return fallback

        client = build_generation_client(
            EmbeddingClientConfig(
                project_id=self._settings.gcp_project_id,
                location=self._settings.gcp_region,
                model_name=self._settings.gemini_model,
                api_key=self._settings.gemini_api_key,
            )
        )
        response = client.models.generate_content(
            model=self._settings.gemini_generation_model,
            contents=user_prompt,
            config=generation_config,
        )
        if response.text is None:
            return fallback
        try:
            parsed = SummaryResponse.model_validate_json(response.text)
        except ValidationError:
            return fallback
        sanitized = _sanitize_summary_response(parsed=parsed, candidates=candidates)
        return sanitized if sanitized is not None else fallback


def _summary_generation_config(*, system_instruction: str) -> genai_types.GenerateContentConfigDict:
    """Return serializable generation config for prompt lab summary runs."""

    return {
        "system_instruction": system_instruction,
        "response_mime_type": "application/json",
        "response_json_schema": SummaryResponse.model_json_schema(),
    }


def _fallback_summary(
    *, user_query: str, candidates: tuple[tuple[str, str], ...]
) -> SummaryResponse:
    """Return deterministic summary payload when model output is unavailable/invalid."""

    return SummaryResponse(
        summary=f"Top matches for '{user_query}' from the current reranked candidate set.",
        items=[
            SummaryItem(
                canonical_product_key=key,
                item_name=item_name,
                why="Selected as a relevant candidate from the current result set.",
            )
            for key, item_name in candidates[:3]
        ],
    )


def _sanitize_summary_response(
    *, parsed: SummaryResponse, candidates: tuple[tuple[str, str], ...]
) -> SummaryResponse | None:
    """Normalize model output to known candidate IDs and names only."""

    candidate_name_by_key = dict(candidates)
    sanitized_items: list[SummaryItem] = []
    for item in parsed.items:
        expected_name = candidate_name_by_key.get(item.canonical_product_key)
        if expected_name is None:
            continue
        sanitized_items.append(
            SummaryItem(
                canonical_product_key=item.canonical_product_key,
                item_name=expected_name,
                why=item.why,
            )
        )
    if not sanitized_items:
        return None
    return SummaryResponse(summary=parsed.summary, items=sanitized_items)
