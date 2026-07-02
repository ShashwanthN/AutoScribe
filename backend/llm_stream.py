from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI, BadRequestError, RateLimitError

logger = logging.getLogger("writer.llm_stream")

_MAX_RETRIES = 6
_RETRY_DELAY = 2
_RATE_LIMIT_BASE = 30


class TruncatedResponseError(Exception):
    def __init__(self, partial: str) -> None:
        self.partial = partial
        super().__init__(f"Model response truncated at {len(partial)} chars")


@dataclass
class LLMStreamEvent:
    type: str
    text: str = ""
    finish_reason: str | None = None


class StreamingLLM:
    """Async OpenAI-compatible streaming client for HTTP/SSE use."""

    def __init__(self, model_override: str | None = None, provider: str | None = None) -> None:
        resolved_provider = provider or os.environ.get("LLM_PROVIDER", "openai")

        if resolved_provider == "opencode":
            self.base_url = os.environ.get("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1")
            api_key = os.environ.get("OPENCODE_API_KEY", "")
            if not api_key:
                raise ValueError("OPENCODE_API_KEY is not set. Add it to your environment.")
            default_model = "deepseek-v4-flash-free"
        elif resolved_provider == "nvidia":
            self.base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
            api_key = os.environ.get("NVIDIA_API_KEY", "")
            if not api_key:
                raise ValueError("NVIDIA_API_KEY is not set. Add it to your environment.")
            default_model = "meta/llama-3.1-405b-instruct"
        else:
            self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            api_key = os.environ.get("OPENAI_API_KEY", "none")
            default_model = "z-ai/glm-5.1"

        self.client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)
        self.model = model_override or os.environ.get("MODEL_NAME", default_model)
        self.max_tokens = int(os.environ.get("MAX_TOKENS", "8192"))

        def flag(name: str, default: str) -> bool:
            return os.environ.get(name, default).lower() in ("true", "1", "yes")

        self.enable_thinking = flag("ENABLE_THINKING", "true")
        self.reasoning_effort = os.environ.get("REASONING_EFFORT", "").strip() or None
        reasoning_budget = os.environ.get("REASONING_BUDGET", "").strip()
        self.reasoning_budget = int(reasoning_budget) if reasoning_budget.isdigit() else None
        self.show_reasoning = flag("SHOW_REASONING", "true")
        self._thinking_supported = True

    def _extra_body(self) -> dict[str, Any]:
        extra_body: dict[str, Any] = {}
        if self.reasoning_effort:
            extra_body["reasoning_effort"] = self.reasoning_effort
        elif self.reasoning_budget and self._thinking_supported:
            extra_body["chat_template_kwargs"] = {"enable_thinking": True}
            extra_body["reasoning_budget"] = self.reasoning_budget
        elif self.enable_thinking and self._thinking_supported:
            extra_body["chat_template_kwargs"] = {
                "enable_thinking": True,
                "clear_thinking": False,
            }
        return extra_body

    async def _create_stream(self, messages: list[dict], temperature: float):
        extra_body = self._extra_body()

        async def create(eb: dict[str, Any]):
            return await self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                max_tokens=self.max_tokens,
                top_p=1,
                messages=messages,
                stream=True,
                **({"extra_body": eb} if eb else {}),
            )

        try:
            return await create(extra_body)
        except BadRequestError as exc:
            if extra_body and "chat_template" in str(exc):
                self._thinking_supported = False
                return await create({})
            raise

    async def stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        label: str = "content",
    ) -> AsyncIterator[LLMStreamEvent]:
        del label

        for attempt in range(1, _MAX_RETRIES + 1):
            if attempt > 1:
                await asyncio.sleep(_RETRY_DELAY)

            content_parts: list[str] = []
            finish_reason: str | None = None
            # A retry re-issues the ENTIRE request from scratch. If we've
            # already yielded tokens (content or reasoning) to the caller
            # during this attempt, they're already displayed/logged and
            # can't be un-sent — silently retrying at that point would
            # append a second, independent generation's tokens right after
            # the first attempt's partial output, which reads as garbled
            # duplicate text and is also a real second outbound API call
            # that never shows up as a second llm_call activity event. So
            # once any token has gone out, a failure aborts instead of
            # retrying — retries only cover the "nothing streamed yet" case
            # (e.g. the provider's 503 "service too busy" errors), which is
            # exactly the case they were added for.
            emitted_any_token = False

            try:
                stream = await self._create_stream(messages, temperature)
                async for chunk in stream:
                    if not getattr(chunk, "choices", None):
                        continue
                    if not chunk.choices or getattr(chunk.choices[0], "delta", None) is None:
                        continue

                    choice = chunk.choices[0]
                    if getattr(choice, "finish_reason", None):
                        finish_reason = choice.finish_reason

                    delta = choice.delta
                    reasoning = getattr(delta, "reasoning_content", None)
                    if reasoning and self.show_reasoning:
                        emitted_any_token = True
                        yield LLMStreamEvent(type="reasoning", text=reasoning)

                    text = getattr(delta, "content", None)
                    if text:
                        content_parts.append(text)
                        emitted_any_token = True
                        yield LLMStreamEvent(type="token", text=text)

                result = "".join(content_parts)
                if not result.strip():
                    raise ValueError("Model returned empty content")
                if finish_reason == "length":
                    raise TruncatedResponseError(result)
                yield LLMStreamEvent(type="done", text=result, finish_reason=finish_reason)
                return

            except RateLimitError:
                if emitted_any_token or attempt == _MAX_RETRIES:
                    raise
                logger.warning("LLM rate-limited before any output, retrying (attempt %s/%s)", attempt, _MAX_RETRIES)
                await asyncio.sleep(_RATE_LIMIT_BASE * (2 ** (attempt - 1)))
            except (BadRequestError, TruncatedResponseError):
                raise
            except Exception:
                if emitted_any_token or attempt == _MAX_RETRIES:
                    raise
                logger.warning("LLM call failed before any output, retrying (attempt %s/%s)", attempt, _MAX_RETRIES)

    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        label: str = "content",
    ) -> str:
        parts: list[str] = []
        async for event in self.stream(messages, temperature, label):
            if event.type == "token":
                parts.append(event.text)
        return "".join(parts)
