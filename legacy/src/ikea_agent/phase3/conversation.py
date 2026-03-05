"""Conversation follow-up orchestration for Phase 3 thread UX."""

from __future__ import annotations

from uuid import uuid4

from ikea_agent.ingest.embedding_client import EmbeddingClientConfig, build_generation_client
from ikea_agent.phase3.repository import (
    ConversationMessageEvent,
    ConversationMessageRow,
    Phase3Repository,
)

from ikea_agent.config import get_settings


class ConversationService:
    """Append user follow-up and assistant response messages to a thread."""

    def __init__(self, repository: Phase3Repository) -> None:
        self._repository = repository
        self._settings = get_settings()

    def append_follow_up(
        self,
        *,
        conversation_id: str,
        prompt_run_id: str | None,
        user_message: str,
    ) -> str:
        """Persist follow-up question and generated assistant response."""

        self._repository.insert_conversation_message(
            ConversationMessageEvent(
                message_id=str(uuid4()),
                conversation_id=conversation_id,
                role="user",
                content_text=user_message,
                prompt_run_id=prompt_run_id,
            )
        )
        history = self._repository.list_conversation_messages(
            conversation_id=conversation_id, limit=30
        )
        assistant_response = self._generate_follow_up_response(history, user_message=user_message)
        self._repository.insert_conversation_message(
            ConversationMessageEvent(
                message_id=str(uuid4()),
                conversation_id=conversation_id,
                role="assistant",
                content_text=assistant_response,
                prompt_run_id=prompt_run_id,
            )
        )
        self._repository.touch_conversation_thread(conversation_id=conversation_id)
        return assistant_response

    def _generate_follow_up_response(
        self, history: tuple[ConversationMessageRow, ...], user_message: str
    ) -> str:
        if self._settings.gemini_api_key is None:
            return (
                "Local fallback follow-up: I used existing conversation context to answer "
                f"'{user_message}'. Configure GEMINI_API_KEY for model-backed explanations."
            )

        history_text = "\n".join(
            f"{message.role}: {message.content_text}" for message in history[-10:]
        )
        system_instruction = _build_follow_up_system_instruction(history_text=history_text)
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
            contents=user_message,
            config={"system_instruction": system_instruction},
        )
        if response.text is None:
            return "No follow-up response generated."
        return response.text.strip()


def _build_follow_up_system_instruction(*, history_text: str) -> str:
    """Build system instruction for follow-up replies with clear constraints."""

    return (
        "You are an IKEA shopping assistant.\n"
        "Goal: answer the user's follow-up using only information in the conversation.\n"
        "Rules:\n"
        "1) Be concise and practical (3-6 sentences).\n"
        "2) If information is missing, state uncertainty and ask one clarifying question.\n"
        "3) Prefer concrete tradeoffs: size, budget, style, and placement.\n"
        "4) Do not claim unavailable product facts.\n"
        "5) End with one actionable next step.\n"
        "\n"
        "Conversation history (oldest to newest):\n"
        f"{history_text}\n"
    )
