"""LLM wrapper with local deterministic fallback."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(slots=True)
class CompletionResult:
    text: str
    provider: str
    requested_model: str | None
    resolved_model: str
    fallback_used: bool = False
    error: str | None = None


class LLMClient:
    MODEL_ALIASES = {
        "claude-3-5-sonnet-latest": "claude-sonnet-4-6",
        "claude-3-7-sonnet-latest": "claude-sonnet-4-6",
        "claude-3-5-haiku-latest": "claude-haiku-4-5-20251001",
    }

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

        model = self.MODEL_ALIASES.get(model, model)

        if self.provider_policy == "openai":
            return "openai", model
        if self.provider_policy == "anthropic":
            return "anthropic", model
        return ("anthropic", model) if self._is_anthropic_model(model) else ("openai", model)

    def _candidate_models(self, provider: str, model: str) -> list[str]:
        base: list[str] = [model]
        if provider == "anthropic":
            base.extend([self.default_anthropic_model, "claude-sonnet-4-6", "claude-opus-4-6"])
        else:
            base.extend([self.default_openai_model])
        out: list[str] = []
        seen: set[str] = set()
        for item in base:
            m = self.MODEL_ALIASES.get(str(item), str(item))
            if not m or m in seen:
                continue
            seen.add(m)
            out.append(m)
        return out

    def complete_with_meta(self, system_prompt: str, user_prompt: str, model: str | None = None) -> CompletionResult:
        provider, target_model = self._resolve(model)
        requested_model = model
        candidates = self._candidate_models(provider=provider, model=target_model)
        last_error: str | None = None

        if provider == "anthropic":
            if self.anthropic_client is None:
                return self._fallback(
                    provider=provider,
                    requested_model=requested_model,
                    resolved_model=target_model,
                    error="Anthropic API key/client not configured",
                )
            for candidate in candidates:
                try:
                    response = self.anthropic_client.messages.create(
                        model=candidate,
                        max_tokens=1800,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                    )
                    text_blocks = [getattr(part, "text", "") for part in getattr(response, "content", [])]
                    text = "\n".join([t for t in text_blocks if t]).strip()
                    if text:
                        return CompletionResult(
                            text=text,
                            provider=provider,
                            requested_model=requested_model,
                            resolved_model=candidate,
                            fallback_used=False,
                            error=None,
                        )
                except Exception as exc:
                    last_error = str(exc)
                    continue
            return self._fallback(
                provider=provider,
                requested_model=requested_model,
                resolved_model=target_model,
                error=last_error,
            )

        if self.openai_client is None:
            return self._fallback(
                provider=provider,
                requested_model=requested_model,
                resolved_model=target_model,
                error="OpenAI API key/client not configured",
            )
        for candidate in candidates:
            try:
                response = self.openai_client.responses.create(
                    model=candidate,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return CompletionResult(
                    text=response.output_text,
                    provider=provider,
                    requested_model=requested_model,
                    resolved_model=candidate,
                    fallback_used=False,
                    error=None,
                )
            except Exception as exc:
                last_error = str(exc)
                continue
        return self._fallback(
            provider=provider,
            requested_model=requested_model,
            resolved_model=target_model,
            error=last_error,
        )

    def complete(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
        return self.complete_with_meta(system_prompt, user_prompt, model=model).text

    @staticmethod
    def _fallback(
        provider: str,
        requested_model: str | None,
        resolved_model: str,
        error: str | None = None,
    ) -> CompletionResult:
        requested = requested_model or "(default)"
        text = (
            "[Local Fallback Draft]\n"
            "Remote model unavailable. Please choose another model or check network/API access.\n\n"
            f"Provider: {provider}\n"
            f"Requested model: {requested}\n"
            f"Resolved model: {resolved_model}\n"
        )
        if error:
            text += f"\nError: {error[:280]}"
        return CompletionResult(
            text=text,
            provider=provider,
            requested_model=requested_model,
            resolved_model=resolved_model,
            fallback_used=True,
            error=error,
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
