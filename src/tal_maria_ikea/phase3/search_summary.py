"""Auto-summary generation for search results using one configured prompt template."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from uuid import uuid4

from google.genai import types as genai_types
from pydantic import BaseModel, Field, ValidationError

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.ingest.embedding_client import EmbeddingClientConfig, build_generation_client
from tal_maria_ikea.phase3.config_repository import ChatConfigRepository
from tal_maria_ikea.phase3.repository import Phase3Repository, PromptRunEvent, PromptTurnEvent


class SearchSummaryItem(BaseModel):
    """One recommended key and rationale in the auto-summary payload."""

    canonical_product_key: str
    item_name: str = Field(min_length=1)
    why: str


class SearchSummaryResponse(BaseModel):
    """Structured output contract for auto summary rendering."""

    summary: str = Field(min_length=1)
    items: list[SearchSummaryItem] = Field(default_factory=list, min_length=1)


@dataclass(frozen=True, slots=True)
class SearchSummaryExecution:
    """Generated summary payload plus prompt run lineage."""

    prompt_run_id: str
    turn_id: str
    rendered_system_prompt: str
    generation_config_json: str
    response: SearchSummaryResponse


@dataclass(frozen=True, slots=True)
class SummaryCandidateProduct:
    """One product candidate used to build summary model requests."""

    canonical_product_key: str
    item_name: str


@dataclass(frozen=True, slots=True)
class SummaryModelRequest:
    """Normalized payload passed to generation with explicit system/user prompts."""

    system_prompt: str
    user_prompt: str


class SearchSummaryService:
    """Generate one summary for a search request and persist run telemetry."""

    def __init__(
        self, repository: Phase3Repository, config_repository: ChatConfigRepository | None = None
    ) -> None:
        self._repository = repository
        self._settings = get_settings()
        self._config_repository = config_repository

    def generate(
        self,
        *,
        request_id: str,
        query_text: str,
        products: tuple[SummaryCandidateProduct, ...],
        template_key: str,
        template_version: str,
    ) -> SearchSummaryExecution:
        """Render template, generate structured summary, and persist prompt run rows."""

        context: dict[str, object] = {
            "user_query": query_text,
            "candidate_items": [
                {
                    "canonical_product_key": product.canonical_product_key,
                    "item_name": product.item_name,
                }
                for product in products
            ],
        }
        rendered_system_prompt = self._render_template(
            template_key=template_key,
            template_version=template_version,
            context=context,
        )
        summary_request = build_summary_request(
            system_prompt=rendered_system_prompt,
            user_query=query_text,
            products=products,
        )
        generation_config = _search_summary_generation_config(
            system_instruction=summary_request.system_prompt
        )
        generation_config_json = json.dumps(generation_config, sort_keys=True)
        prompt_hash = hashlib.sha256(rendered_system_prompt.encode("utf-8")).hexdigest()
        payload_hash = hashlib.sha256(
            json.dumps(context, sort_keys=True).encode("utf-8")
        ).hexdigest()

        prompt_run_id = str(uuid4())
        response = self._generate_response(
            query_text=query_text,
            request=summary_request,
            products=products,
            generation_config=generation_config,
        )

        self._repository.insert_prompt_run(
            PromptRunEvent(
                prompt_run_id=prompt_run_id,
                request_id=request_id,
                variant_key=template_key,
                variant_version=template_version,
                rendered_system_prompt=rendered_system_prompt,
                rendered_prompt_hash=prompt_hash,
                user_prompt=summary_request.user_prompt,
                context_payload_hash=payload_hash,
                model_name=self._settings.gemini_generation_model,
                status="ok",
                latency_ms=None,
                error_message=None,
                generation_config_json=generation_config_json,
            )
        )
        turn_id = str(uuid4())
        self._repository.insert_prompt_turn(
            PromptTurnEvent(
                turn_id=turn_id,
                prompt_run_id=prompt_run_id,
                conversation_id=f"summary-{request_id}",
                summary_text=response.summary,
                response_json=response.model_dump(),
            )
        )
        return SearchSummaryExecution(
            prompt_run_id=prompt_run_id,
            turn_id=turn_id,
            rendered_system_prompt=rendered_system_prompt,
            generation_config_json=generation_config_json,
            response=response,
        )

    def _render_template(
        self, *, template_key: str, template_version: str, context: dict[str, object]
    ) -> str:
        template_text = _default_template_text()
        if self._config_repository is not None:
            template_row = self._config_repository.get_prompt_template(
                key=template_key,
                version=template_version,
            )
            if template_row is not None:
                template_text = template_row.template_text

        user_query = str(context.get("user_query", ""))
        candidates = context.get("candidate_items", [])
        candidate_lines = "\n".join(
            [
                f"- {item.get('canonical_product_key', '')} | {item.get('item_name', '')}"
                for item in candidates
                if isinstance(item, dict)
            ]
        )
        return template_text.format(
            user_query=user_query,
            candidate_lines=candidate_lines,
        )

    def _generate_response(
        self,
        *,
        query_text: str,
        request: SummaryModelRequest,
        products: tuple[SummaryCandidateProduct, ...],
        generation_config: genai_types.GenerateContentConfigDict,
    ) -> SearchSummaryResponse:
        fallback = _fallback_summary(query_text=query_text, products=products)
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
            contents=request.user_prompt,
            config=generation_config,
        )
        if response.text is None:
            return fallback
        try:
            parsed = SearchSummaryResponse.model_validate_json(response.text)
        except ValidationError:
            return fallback
        sanitized = _sanitize_summary_response(parsed=parsed, products=products)
        return sanitized if sanitized is not None else fallback


def _search_summary_generation_config(
    *, system_instruction: str
) -> genai_types.GenerateContentConfigDict:
    """Return generation config for auto-search summary calls."""

    return {
        "system_instruction": system_instruction,
        "response_mime_type": "application/json",
        "response_json_schema": SearchSummaryResponse.model_json_schema(),
    }


def _fallback_summary(
    *, query_text: str, products: tuple[SummaryCandidateProduct, ...]
) -> SearchSummaryResponse:
    """Return deterministic fallback summary with item IDs and names."""

    top_candidates = products[:3]
    return SearchSummaryResponse(
        summary=(
            f"Top matches for '{query_text}' are ready. "
            "These picks prioritize relevance from the reranked result set."
        ),
        items=[
            SearchSummaryItem(
                canonical_product_key=product.canonical_product_key,
                item_name=product.item_name,
                why="High relevance in reranked results.",
            )
            for product in top_candidates
        ],
    )


def _sanitize_summary_response(
    *, parsed: SearchSummaryResponse, products: tuple[SummaryCandidateProduct, ...]
) -> SearchSummaryResponse | None:
    """Normalize model output to known candidate IDs and names only."""

    candidate_name_by_key = {
        product.canonical_product_key: product.item_name for product in products
    }
    sanitized_items: list[SearchSummaryItem] = []
    for item in parsed.items:
        expected_name = candidate_name_by_key.get(item.canonical_product_key)
        if expected_name is None:
            continue
        sanitized_items.append(
            SearchSummaryItem(
                canonical_product_key=item.canonical_product_key,
                item_name=expected_name,
                why=item.why,
            )
        )
    if not sanitized_items:
        return None
    return SearchSummaryResponse(summary=parsed.summary, items=sanitized_items)


def build_summary_request(
    *,
    system_prompt: str,
    user_query: str,
    products: tuple[SummaryCandidateProduct, ...],
) -> SummaryModelRequest:
    """Build a strongly typed summary request where products are embedded in user prompt."""

    candidate_lines = [
        f"- {product.canonical_product_key} | {product.item_name}" for product in products
    ]
    user_prompt_lines = [
        "Candidate products (ID | name):",
        *candidate_lines,
        "",
        f"User query: {user_query}",
    ]
    return SummaryModelRequest(
        system_prompt=system_prompt,
        user_prompt="\n".join(user_prompt_lines),
    )


def _default_template_text() -> str:
    """Return built-in fallback summary template text."""

    return (
        "You are an IKEA shopping assistant.\n"
        "Return JSON matching the provided schema.\n"
        "Each item must include canonical_product_key and item_name exactly as provided.\n"
        "Use only candidate IDs and names and be concise.\n"
        "User query: {user_query}\n"
        "Candidates (ID | name):\n"
        "{candidate_lines}\n"
        "Return JSON only."
    )
