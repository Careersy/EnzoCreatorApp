"""LLM client wrapper with graceful fallback."""

from __future__ import annotations

from content_ai_system.config import SETTINGS

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover
    OpenAI = None


class LLMClient:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or SETTINGS.default_model
        self.client = None
        if OpenAI is not None and SETTINGS.openai_api_key:
            self.client = OpenAI(api_key=SETTINGS.openai_api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.client is None:
            return self._local_fallback(system_prompt, user_prompt)

        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.output_text

    @staticmethod
    def _local_fallback(system_prompt: str, user_prompt: str) -> str:
        return (
            "[Local fallback output]\n"
            "No API key configured.\n\n"
            "System instructions:\n"
            f"{system_prompt[:500]}\n\n"
            "User request:\n"
            f"{user_prompt[:1200]}"
        )
