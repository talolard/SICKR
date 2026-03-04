"""Bootstrap helpers for local Django config defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tal_maria_ikea.web.models import PromptVariantSet, SystemPromptTemplate


@dataclass(frozen=True, slots=True)
class _PromptTemplateSeed:
    key: str
    version: str
    title: str
    template_text: str


_DEFAULT_PROMPT_TEMPLATES: tuple[_PromptTemplateSeed, ...] = (
    _PromptTemplateSeed(
        key="summary-default",
        version="v1",
        title="Balanced summary",
        template_text=(
            "You are an IKEA shopping assistant.\n"
            "Task: return JSON matching the provided schema with:\n"
            "- summary: short recommendation summary\n"
            "- items: list with canonical_product_key, item_name, and why\n"
            "\n"
            "Rules:\n"
            "1) Use only product IDs and names from the candidate list.\n"
            "2) Keep summary to 2-4 sentences.\n"
            "3) Prefer concrete rationale: size, price, placement, style.\n"
            "4) Do not invent product facts not implied by the query.\n"
            "5) If uncertain, mention uncertainty briefly.\n"
            "6) Every item must include both canonical_product_key and item_name.\n"
            "\n"
            "User query: {{ user_query }}\n"
            "Candidates (ID | name):\n"
            "{% for item in candidate_items %}"
            "- {{ item.canonical_product_key }} | {{ item.item_name }}\n"
            "{% endfor %}"
            "\n"
            "Return JSON only."
        ),
    ),
    _PromptTemplateSeed(
        key="summary-budget",
        version="v1",
        title="Budget-focused summary",
        template_text=(
            "You are an IKEA shopping assistant focused on value-for-money choices.\n"
            "Return JSON matching the provided schema.\n"
            "\n"
            "Rules:\n"
            "1) Prioritize likely budget-fit options first.\n"
            "2) Explain tradeoffs (cost vs. size/style) in plain language.\n"
            "3) Select 2-4 items max from candidate IDs.\n"
            "4) Never return IDs or names not in the provided candidate list.\n"
            "5) Every item must include both canonical_product_key and item_name.\n"
            "\n"
            "User query: {{ user_query }}\n"
            "Candidates (ID | name):\n"
            "{% for item in candidate_items %}"
            "- {{ item.canonical_product_key }} | {{ item.item_name }}\n"
            "{% endfor %}"
            "\n"
            "Return JSON only."
        ),
    ),
    _PromptTemplateSeed(
        key="summary-small-space",
        version="v1",
        title="Small-space summary",
        template_text=(
            "You are an IKEA assistant optimizing recommendations for compact spaces.\n"
            "Return JSON matching the provided schema.\n"
            "\n"
            "Rules:\n"
            "1) Prioritize compact or flexible options when relevant.\n"
            "2) Mention placement guidance in the summary.\n"
            "3) Keep rationale concise and practical.\n"
            "4) Select only from candidate IDs and names.\n"
            "5) Every item must include both canonical_product_key and item_name.\n"
            "\n"
            "User query: {{ user_query }}\n"
            "Candidates (ID | name):\n"
            "{% for item in candidate_items %}"
            "- {{ item.canonical_product_key }} | {{ item.item_name }}\n"
            "{% endfor %}"
            "\n"
            "Return JSON only."
        ),
    ),
)


def ensure_default_prompt_templates() -> None:
    """Create local default Prompt Lab templates and one active variant set."""

    template_manager: Any = SystemPromptTemplate.objects  # pyrefly: ignore[missing-attribute]
    variant_set_manager: Any = PromptVariantSet.objects  # pyrefly: ignore[missing-attribute]

    template_ids: list[int] = []
    for seed in _DEFAULT_PROMPT_TEMPLATES:
        template, _created = template_manager.update_or_create(
            key=seed.key,
            version=seed.version,
            defaults={
                "title": seed.title,
                "template_text": seed.template_text,
                "is_active": True,
            },
        )
        template_ids.append(int(template.id))

    variant_set, _created = variant_set_manager.update_or_create(
        name="default-compare-set",
        defaults={
            "title": "Default Prompt Comparison Set",
            "description": "Balanced, budget, and small-space recommendation variants.",
            "is_active": True,
            "max_variants": min(5, len(template_ids)),
        },
    )
    variant_set.templates.set(template_ids)
