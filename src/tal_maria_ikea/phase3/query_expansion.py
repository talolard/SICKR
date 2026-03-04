"""Query expansion pipeline with heuristic gating and optional Gemini enrichment."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from tal_maria_ikea.config import get_settings
from tal_maria_ikea.ingest.embedding_client import EmbeddingClientConfig, build_generation_client
from tal_maria_ikea.shared.types import QueryExpansionMode

_WIDTH_PATTERNS = (
    re.compile(r"(\d+(?:[.,]\d+)?)\s*cm\s*(?:wide|width)", flags=re.IGNORECASE),
    re.compile(r"(?:width|wide)\s*(\d+(?:[.,]\d+)?)\s*cm", flags=re.IGNORECASE),
)
_PRICE_PATTERNS = (
    re.compile(
        r"(?:under|below|less than)\s*(\d+(?:[.,]\d+)?)\s*(?:€|eur|euro)?", flags=re.IGNORECASE
    ),
    re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(?:€|eur|euro)\s*(?:max|maximum|or less)?", flags=re.IGNORECASE
    ),
)
_CATEGORY_HINTS: tuple[tuple[str, str], ...] = (
    ("couch", "sofas-armchairs"),
    ("sofa", "sofas-armchairs"),
    ("lamp", "lighting"),
    ("curtain", "home-textiles"),
    ("desk", "tables-desks"),
    ("table", "tables-desks"),
)
_AUTO_MIN_CONFIDENCE = 0.70


class GeminiExpansionOutput(BaseModel):
    """Structured Gemini output contract for expansion extraction."""

    expanded_query_text: str | None = None
    category: str | None = None
    include_keyword: str | None = None
    exclude_keyword: str | None = None
    width_max_cm: float | None = None
    min_price_eur: float | None = None
    max_price_eur: float | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    rationale: str | None = None


@dataclass(frozen=True, slots=True)
class ExpansionOutcome:
    """Result of expansion decision + extracted filter proposal payload."""

    expanded_query_text: str | None
    extracted_filters: dict[str, Any]
    confidence: float
    heuristic_reason: str
    applied: bool
    provider: str


class QueryExpansionService:
    """Infer structured filters from query text for `auto|on|off` expansion modes."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def expand(self, query_text: str, mode: QueryExpansionMode) -> ExpansionOutcome:
        """Return expansion proposal and whether filters should be applied."""

        if mode == "off":
            return ExpansionOutcome(
                expanded_query_text=None,
                extracted_filters={},
                confidence=0.0,
                heuristic_reason="mode_off",
                applied=False,
                provider="none",
            )

        heuristic_filters, signal_count = _heuristic_extract(query_text)
        heuristic_confidence = min(1.0, 0.4 + (signal_count * 0.2))
        heuristic_reason = (
            "heuristic_constraints_detected" if signal_count > 0 else "no_constraints_detected"
        )

        if mode == "auto" and signal_count == 0:
            return ExpansionOutcome(
                expanded_query_text=None,
                extracted_filters={},
                confidence=0.0,
                heuristic_reason=heuristic_reason,
                applied=False,
                provider="heuristic",
            )

        gemini_output = self._maybe_gemini_expand(query_text=query_text)
        if gemini_output is None:
            applied = bool(mode == "on" or signal_count > 0)
            return ExpansionOutcome(
                expanded_query_text=None,
                extracted_filters=heuristic_filters,
                confidence=heuristic_confidence,
                heuristic_reason=heuristic_reason,
                applied=applied and bool(heuristic_filters),
                provider="heuristic",
            )

        merged_filters = dict(heuristic_filters)
        gemini_filters = _filters_from_gemini(gemini_output)
        merged_filters.update(gemini_filters)
        applied = bool(
            mode == "on" or signal_count > 0 or gemini_output.confidence >= _AUTO_MIN_CONFIDENCE
        )
        return ExpansionOutcome(
            expanded_query_text=gemini_output.expanded_query_text,
            extracted_filters=merged_filters,
            confidence=max(heuristic_confidence, gemini_output.confidence),
            heuristic_reason=gemini_output.rationale or heuristic_reason,
            applied=applied and bool(merged_filters),
            provider="gemini",
        )

    def _maybe_gemini_expand(self, query_text: str) -> GeminiExpansionOutput | None:
        if not _gemini_available():
            return None

        system_instruction = _build_expansion_system_instruction()
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
            contents=query_text,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "response_json_schema": GeminiExpansionOutput.model_json_schema(),
            },
        )
        if response.text is None:
            return None
        return GeminiExpansionOutput.model_validate_json(response.text)


def _build_expansion_system_instruction() -> str:
    """Build a deterministic system instruction for structured expansion extraction."""

    return (
        "You are a structured extraction assistant for IKEA e-commerce search.\n"
        "Task: extract normalized filters from one user query.\n"
        "Output requirements:\n"
        "1) Output must match the provided JSON schema.\n"
        "2) Use null for unknown or missing fields.\n"
        "3) Keep expanded_query_text short and faithful to user intent.\n"
        "4) confidence must be between 0 and 1.\n"
        "5) rationale should be one short sentence.\n"
        "6) Do not invent unsupported constraints.\n"
        "\n"
        "Valid category examples: lighting, sofas-armchairs, tables-desks, "
        "beds, storage-organisation, home-textiles.\n"
        "\n"
        "Few-shot examples:\n"
        'Input: "tall lamp under 100 eur"\n'
        "Output idea: {"
        '"expanded_query_text":"tall floor lamp under 100 eur",'
        '"category":"lighting",'
        '"include_keyword":"floor lamp",'
        '"exclude_keyword":null,'
        '"width_max_cm":null,'
        '"min_price_eur":null,'
        '"max_price_eur":100.0,'
        '"confidence":0.88,'
        '"rationale":"User specifies lamp category and price ceiling."}\n'
        "\n"
        'Input: "white desk 120 cm wide"\n'
        "Output idea: {"
        '"expanded_query_text":"white desk width 120 cm",'
        '"category":"tables-desks",'
        '"include_keyword":"white",'
        '"exclude_keyword":null,'
        '"width_max_cm":120.0,'
        '"min_price_eur":null,'
        '"max_price_eur":null,'
        '"confidence":0.84,'
        '"rationale":"User specifies desk category and width constraint."}\n'
    )


def _filters_from_gemini(output: GeminiExpansionOutput) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if output.category is not None:
        result["category"] = output.category
    if output.include_keyword is not None:
        result["include_keyword"] = output.include_keyword
    if output.exclude_keyword is not None:
        result["exclude_keyword"] = output.exclude_keyword
    if output.width_max_cm is not None:
        result["width_max_cm"] = output.width_max_cm
    if output.min_price_eur is not None:
        result["min_price_eur"] = output.min_price_eur
    if output.max_price_eur is not None:
        result["max_price_eur"] = output.max_price_eur
    return result


def _heuristic_extract(query_text: str) -> tuple[dict[str, Any], int]:
    filters: dict[str, Any] = {}
    signal_count = 0
    normalized = query_text.lower()

    width_match = _find_first_number(_WIDTH_PATTERNS, normalized)
    if width_match is not None:
        filters["width_max_cm"] = width_match
        signal_count += 1

    price_match = _find_first_number(_PRICE_PATTERNS, normalized)
    if price_match is not None:
        filters["max_price_eur"] = price_match
        signal_count += 1

    for keyword, category in _CATEGORY_HINTS:
        if keyword in normalized:
            filters["category"] = category
            signal_count += 1
            break

    return filters, signal_count


def _find_first_number(patterns: tuple[re.Pattern[str], ...], text: str) -> float | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match is None:
            continue
        value = match.group(1).replace(",", ".")
        return float(value)
    return None


def _gemini_available() -> bool:
    api_key = get_settings().gemini_api_key
    if api_key:
        return True
    return bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))


def serialize_expansion_outcome(outcome: ExpansionOutcome) -> str:
    """Return deterministic JSON for logging/debug snapshots."""

    return json.dumps(
        {
            "expanded_query_text": outcome.expanded_query_text,
            "extracted_filters": outcome.extracted_filters,
            "confidence": outcome.confidence,
            "heuristic_reason": outcome.heuristic_reason,
            "applied": outcome.applied,
            "provider": outcome.provider,
        },
        sort_keys=True,
    )
