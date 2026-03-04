from __future__ import annotations

import os
from dataclasses import dataclass
from typing import cast

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tal_maria_ikea.web.project.settings")
django.setup()

from tal_maria_ikea.phase3.prompt_lab import (
    PromptLabRepository,
    PromptLabService,
    PromptTemplateRow,
    SummaryItem,
    SummaryResponse,
)
from tal_maria_ikea.phase3.repository import (
    ConversationMessageEvent,
    ConversationThreadEvent,
    PromptRunEvent,
    PromptTurnEvent,
)


@dataclass(frozen=True, slots=True)
class _TemplateRow:
    id: int
    key: str
    version: str
    template_text: str


class _RepoStub:
    def __init__(self) -> None:
        self.prompt_runs = 0
        self.prompt_turns = 0
        self.threads = 0
        self.messages = 0

    def insert_prompt_run(self, _event: PromptRunEvent) -> None:
        self.prompt_runs += 1

    def insert_prompt_turn(self, _event: PromptTurnEvent) -> None:
        self.prompt_turns += 1

    def upsert_conversation_thread(self, _event: ConversationThreadEvent) -> None:
        self.threads += 1

    def insert_conversation_message(self, _event: ConversationMessageEvent) -> None:
        self.messages += 1


class _ServiceUnderTest(PromptLabService):
    def _generate_summary(  # type: ignore[override]
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        product_keys: tuple[str, ...],
        generation_config: dict[str, object],
    ) -> SummaryResponse | None:
        _ = (user_prompt, generation_config)
        if "fail" in system_prompt:
            return None
        return SummaryResponse(
            summary="ok",
            items=[
                SummaryItem(
                    canonical_product_key=product_keys[0],
                    why="matched",
                )
            ],
        )


def test_prompt_lab_runs_variants_in_parallel_and_persists_events() -> None:
    repository = _RepoStub()
    service = _ServiceUnderTest(repository=cast("PromptLabRepository", repository))
    templates = (
        _TemplateRow(1, "summary", "v1", "query={{ user_query }}"),
        _TemplateRow(2, "summary", "v2", "query={{ user_query }}"),
    )

    results = service.run_compare(
        request_id="req-1",
        user_query="hallway lamps",
        product_keys=("1-DE", "2-DE"),
        template_rows=cast("tuple[PromptTemplateRow, ...]", templates),
    )

    assert len(results) == 2
    assert repository.prompt_runs == 2
    assert repository.prompt_turns == 2
    assert repository.threads == 1
    assert repository.messages == 2
    assert all(result.status == "ok" for result in results)


def test_prompt_lab_partial_failure_is_isolated_per_variant() -> None:
    repository = _RepoStub()
    service = _ServiceUnderTest(repository=cast("PromptLabRepository", repository))
    templates = (
        _TemplateRow(1, "summary", "v1", "query={{ user_query }}"),
        _TemplateRow(2, "summary", "v2", "fail {{ user_query }}"),
    )

    results = service.run_compare(
        request_id="req-2",
        user_query="desk lamps",
        product_keys=("1-DE",),
        template_rows=cast("tuple[PromptTemplateRow, ...]", templates),
    )

    by_version = {result.variant_version: result for result in results}
    assert by_version["v1"].status == "ok"
    assert by_version["v2"].status == "error"
    assert repository.prompt_runs == 2
    assert repository.prompt_turns == 2
    assert repository.threads == 1
