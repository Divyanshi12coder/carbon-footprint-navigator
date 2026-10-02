"""LLM provider adapter. Only the backend talks to the provider; the API key never leaves the server."""

import logging
from dataclasses import dataclass

import anthropic

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Models that accept the server-side refusal fallback ("fallbacks": "default").
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ProviderError(RuntimeError):
    pass


@dataclass
class Completion:
    text: str
    model: str


class AnthropicProvider:
    def __init__(self, settings: Settings):
        self.model = settings.ai_model
        self.client = anthropic.Anthropic(api_key=settings.ai_api_key, timeout=settings.ai_timeout_seconds, max_retries=2)

    def complete(self, system: str, messages: list[dict[str, str]], max_tokens: int = 2000) -> Completion:
        try:
            if self.model in _FALLBACK_MODELS:
                response = self.client.beta.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                    output_config={"effort": "low"},
                    betas=[_FALLBACK_BETA],
                    fallbacks="default",
                )
            else:
                response = self.client.messages.create(model=self.model, max_tokens=max_tokens, system=system, messages=messages)
        except anthropic.AuthenticationError as exc:
            raise ProviderError("The AI provider rejected the configured API key.") from exc
        except anthropic.RateLimitError as exc:
            raise ProviderError("The AI provider is rate limiting requests. Try again shortly.") from exc
        except anthropic.APIStatusError as exc:
            logger.warning("AI provider error %s: %s", exc.status_code, exc.message)
            raise ProviderError(f"The AI provider returned an error ({exc.status_code}).") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError("Could not reach the AI provider.") from exc

        if response.stop_reason == "refusal":
            raise ProviderError("The AI provider declined to answer this request.")
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            raise ProviderError("The AI provider returned an empty response.")
        return Completion(text=text, model=response.model)


def get_provider(settings: Settings) -> AnthropicProvider | None:
    if settings.ai_provider == "anthropic" and settings.ai_api_key:
        return AnthropicProvider(settings)
    return None
