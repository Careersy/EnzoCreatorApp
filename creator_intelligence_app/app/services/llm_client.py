"""LLM wrapper with local deterministic fallback."""

from __future__ import annotations

from typing import Any

from creator_intelligence_app.app.config.settings import SETTINGS, parse_model_options

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover
    OpenAI = None

try:
    from anthropic import Anthropic  # type: ignore
except ImportError:  # pragma: no cover
    Anthropic = None


class LLMClient:
    def __init__(self) -> None:
        self.openai_client = None
        self.anthropic_client = None
        if OpenAI is not None and SETTINGS.openai_api_key:
            kwargs = {"api_key": SETTINGS.openai_api_key}
            if SETTINGS.openai_base_url:
                kwargs["base_url"] = SETTINGS.openai_base_url
            self.openai_client = OpenAI(**kwargs)
        if Anthropic is not None and SETTINGS.anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=SETTINGS.anthropic_api_key)

        self.default_openai_model = SETTINGS.openai_model
        self.default_anthropic_model = SETTINGS.anthropic_model
        self.provider_policy = str(SETTINGS.llm_provider or "auto").lower()

    @staticmethod
    def _is_anthropic_model(model: str) -> bool:
        m = str(model or "").lower()
        return m.startswith("claude")

    def _resolve(self, requested_model: str | None) -> tuple[str, str]:
        model = str(requested_model or "").strip()
        if not model:
            if self.provider_policy == "anthropic":
                model = self.default_anthropic_model
            else:
                model = self.default_openai_model

        if self.provider_policy == "openai":
            return "openai", model
        if self.provider_policy == "anthropic":
            return "anthropic", model
        return ("anthropic", model) if self._is_anthropic_model(model) else ("openai", model)

    def complete(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
        provider, target_model = self._resolve(model)

        if provider == "anthropic":
            if self.anthropic_client is None:
                return self._fallback(system_prompt, user_prompt, target_model, provider)
            try:
                response = self.anthropic_client.messages.create(
                    model=target_model,
                    max_tokens=1800,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                text_blocks = [getattr(part, "text", "") for part in getattr(response, "content", [])]
                return "\n".join([t for t in text_blocks if t]).strip()
            except Exception:
                return self._fallback(system_prompt, user_prompt, target_model, provider)

        if self.openai_client is None:
            return self._fallback(system_prompt, user_prompt, target_model, provider)
        try:
            response = self.openai_client.responses.create(
                model=target_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.output_text
        except Exception:
            return self._fallback(system_prompt, user_prompt, target_model, provider)

    @staticmethod
    def _fallback(system_prompt: str, user_prompt: str, model: str, provider: str) -> str:
        return (
            "[Local Fallback Draft]\n"
            "Remote model unavailable (missing config or network/API error). "
            "This is a deterministic local preview.\n\n"
            f"Provider requested: {provider}\n"
            f"Model requested: {model}\n\n"
            f"System:\n{system_prompt[:350]}\n\n"
            f"Prompt:\n{user_prompt[:1800]}"
        )

    def status(self) -> dict[str, Any]:
        default_provider = "anthropic" if self.provider_policy == "anthropic" else "openai"
        if self.provider_policy == "auto":
            default_provider = "openai"
        return {
            "provider_policy": self.provider_policy,
            "provider": default_provider,
            "connected": (self.openai_client is not None) or (self.anthropic_client is not None),
            "openai_connected": self.openai_client is not None,
            "anthropic_connected": self.anthropic_client is not None,
            "default_openai_model": self.default_openai_model,
            "default_anthropic_model": self.default_anthropic_model,
            "available_models": parse_model_options(SETTINGS.available_models),
            "base_url": SETTINGS.openai_base_url or "https://api.openai.com/v1",
        }


def build_generation_prompt(
    mode: str,
    platform: str,
    goal: str,
    input_text: str,
    blueprint: dict[str, Any],
    audience: str,
) -> tuple[str, str]:
    system = (
        "You are a content strategist. Preserve user voice first, then apply creator structure, "
        "then platform optimization. Avoid generic AI language."
    )
    user = (
        f"Mode: {mode}\n"
        f"Platform: {platform}\n"
        f"Goal: {goal}\n"
        f"Audience: {audience}\n\n"
        f"Blueprint (Use/Prefer/Avoid/Unclear):\n{blueprint}\n\n"
        f"Input:\n{input_text}\n\n"
        "Return final draft, 3 alternate hooks, and 2 CTA options."
    )
    return system, user
