from __future__ import annotations
import json
import os
import re
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import IO, Optional, Type, TypeVar

from openai import BadRequestError, RateLimitError, OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# ── Terminal colors (stderr so they don't pollute piped output) ───────────────
_USE_COLOR = sys.stderr.isatty() and os.getenv("NO_COLOR") is None
_DIM    = "\033[90m"    if _USE_COLOR else ""
_CYAN   = "\033[36m"    if _USE_COLOR else ""
_YELLOW = "\033[33m"    if _USE_COLOR else ""
_GREEN  = "\033[32m"    if _USE_COLOR else ""
_RED    = "\033[31m"    if _USE_COLOR else ""
_BOLD   = "\033[1m"     if _USE_COLOR else ""
_RESET  = "\033[0m"     if _USE_COLOR else ""

_MAX_RETRIES = 6
_RETRY_DELAY = 2        # seconds between retries (generic errors)
_RATE_LIMIT_BASE = 30   # seconds for first 429 retry; doubles each attempt


class TruncatedResponseError(Exception):
    """Raised when finish_reason == 'length' — the model hit max_tokens mid-response."""
    def __init__(self, partial: str) -> None:
        self.partial = partial
        super().__init__(f"Model response truncated at {len(partial)} chars (max_tokens hit)")


# ── Detailed file logger (module-level so all LLMClient instances share it) ───

_detail_log_file: Optional[IO[str]] = None
_detail_log_lock = threading.Lock()


def enable_detailed_log(path: Path) -> None:
    """Open the detailed log file. Call once before the pipeline run starts."""
    global _detail_log_file
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _detail_log_file = open(path, "w", encoding="utf-8", buffering=1)
    _detail_log_file.write(
        f"Writter Detailed LLM Log\n"
        f"Started: {datetime.utcnow().isoformat()}\n"
        f"{'=' * 80}\n\n"
    )


def close_detailed_log() -> None:
    """Flush and close the detailed log file."""
    global _detail_log_file
    if _detail_log_file:
        _detail_log_file.write(f"\n{'=' * 80}\nLog closed: {datetime.utcnow().isoformat()}\n")
        _detail_log_file.close()
        _detail_log_file = None


def _write_detail(entry: str) -> None:
    if _detail_log_file:
        with _detail_log_lock:
            _detail_log_file.write(entry)


def _log(msg: str) -> None:
    """Print a log line to stderr so it doesn't mix with piped content output."""
    print(msg, file=sys.stderr, flush=True)


class LLMClient:
    """
    Single point of entry for all LLM calls.
    Works with any OpenAI-compatible API.

    Provider selection:
        LLM_PROVIDER            — "openai" (default) or "opencode"

    OpenAI provider env vars:
        OPENAI_API_KEY          — API key
        OPENAI_BASE_URL         — Base URL (default: https://api.openai.com/v1)
        MODEL_NAME              — Model identifier (default: z-ai/glm-5.1)

    OpenCode provider env vars:
        OPENCODE_API_KEY        — API key (required)
        OPENCODE_BASE_URL       — Base URL (default: https://opencode.ai/zen/v1)
        MODEL_NAME              — Model identifier (default: deepseek-v4-flash-free)

    Shared env vars:
        ENABLE_THINKING         — Pass enable_thinking=True via chat_template_kwargs (vLLM; default: true)
        REASONING_EFFORT        — Pass reasoning_effort=<value> directly (none/high/medium/low; overrides ENABLE_THINKING)
        REASONING_BUDGET        — Pass reasoning_budget=<int> + enable_thinking=True (Nvidia Nemotron style; overrides ENABLE_THINKING)
        SHOW_REASONING          — Stream reasoning tokens to stderr (default: true)
        USE_STRUCTURED_OUTPUT   — Use OpenAI beta.parse() — only for real OpenAI gpt-4o+ (default: false)
        MAX_TOKENS              — Max tokens for completion (default: 8192)
    """

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

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
        )
        self.model = model_override or os.environ.get("MODEL_NAME", default_model)
        self.max_tokens = int(os.environ.get("MAX_TOKENS", "8192"))

        def _flag(name: str, default: str) -> bool:
            return os.environ.get(name, default).lower() in ("true", "1", "yes")

        self.enable_thinking    = _flag("ENABLE_THINKING", "true")
        self.reasoning_effort   = os.environ.get("REASONING_EFFORT", "").strip() or None
        _rb = os.environ.get("REASONING_BUDGET", "").strip()
        self.reasoning_budget   = int(_rb) if _rb.isdigit() else None
        self.show_reasoning     = _flag("SHOW_REASONING", "true")
        self.use_structured_output = _flag("USE_STRUCTURED_OUTPUT", "false")
        self._thinking_supported: bool = True  # set False on first chat_template error

    # ── Public interface ──────────────────────────────────────────────────────

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """Plain text completion — streams tokens live to stderr."""
        return self._stream(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            label="text",
            print_content=True,
        )

    def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.3,
    ) -> T:
        """Structured JSON completion — streams tokens live, then parses."""
        if self.use_structured_output:
            try:
                return self._parse_structured(
                    system_prompt, user_prompt, response_model, temperature
                )
            except Exception as e:
                _log(f"{_YELLOW}[llm] beta.parse() failed ({e}), falling back to JSON extraction{_RESET}")

        return self._extract_json(system_prompt, user_prompt, response_model, temperature)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        label: str = "",
        print_content: bool = False,
    ) -> str:
        """
        Streams a response with full live logging.
        - Logs the request (endpoint, model, prompt sizes) before sending
        - Streams reasoning tokens dimly to stderr if SHOW_REASONING=true
        - Streams content tokens to stderr always (and stdout if print_content=True)
        - Retries up to MAX_RETRIES times on connection drops
        """
        extra_body: dict = {}
        if self.reasoning_effort:
            extra_body["reasoning_effort"] = self.reasoning_effort
        elif self.reasoning_budget and self._thinking_supported:
            # Nvidia Nemotron style: enable_thinking + reasoning_budget together
            extra_body["chat_template_kwargs"] = {"enable_thinking": True}
            extra_body["reasoning_budget"] = self.reasoning_budget
        elif self.enable_thinking and self._thinking_supported:
            extra_body["chat_template_kwargs"] = {
                "enable_thinking": True,
                "clear_thinking": False,
            }

        sys_chars  = len(system_prompt)
        user_chars = len(user_prompt)
        _log(
            f"\n{_BOLD}{_CYAN}[llm →]{_RESET} "
            f"{self.base_url}  model={self.model}  "
            f"temp={temperature}  max_tokens={self.max_tokens}  "
            f"label={label or 'structured'}"
        )
        _log(f"{_DIM}[llm]  system={sys_chars} chars  user={user_chars} chars{_RESET}")

        for attempt in range(1, _MAX_RETRIES + 1):
            if attempt > 1:
                _log(f"{_YELLOW}[llm]  retry {attempt}/{_MAX_RETRIES} in {_RETRY_DELAY}s...{_RESET}")
                time.sleep(_RETRY_DELAY)

            try:
                def _create(eb: dict):
                    return self.client.chat.completions.create(
                        model=self.model,
                        temperature=temperature,
                        max_tokens=self.max_tokens,
                        top_p=1,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user",   "content": user_prompt},
                        ],
                        stream=True,
                        **({"extra_body": eb} if eb else {}),
                    )
                try:
                    stream = _create(extra_body)
                except BadRequestError as e:
                    if extra_body and "chat_template" in str(e):
                        _log(f"{_YELLOW}[llm]  model doesn't support chat_template_kwargs — disabling thinking{_RESET}")
                        self._thinking_supported = False
                        extra_body = {}
                        stream = _create(extra_body)
                    else:
                        raise

                content_parts: list[str] = []
                reasoning_chars = 0
                content_chars   = 0
                first_token     = True
                finish_reason: str | None = None

                for chunk in stream:
                    if not getattr(chunk, "choices", None):
                        continue
                    if not chunk.choices or getattr(chunk.choices[0], "delta", None) is None:
                        continue

                    choice = chunk.choices[0]
                    if getattr(choice, "finish_reason", None):
                        finish_reason = choice.finish_reason

                    delta = choice.delta

                    # Reasoning tokens — always stream to stderr (dimmed)
                    reasoning = getattr(delta, "reasoning_content", None)
                    if reasoning:
                        reasoning_chars += len(reasoning)
                        if self.show_reasoning:
                            if first_token:
                                _log(f"{_DIM}[llm]  thinking...{_RESET}")
                                first_token = False
                            print(f"{_DIM}{reasoning}{_RESET}", end="", flush=True, file=sys.stderr)

                    # Content tokens — stream to stderr always, stdout if requested
                    text = getattr(delta, "content", None)
                    if text:
                        content_chars += len(text)
                        content_parts.append(text)
                        if first_token:
                            _log(f"{_DIM}[llm]  receiving content...{_RESET}")
                            first_token = False
                        if print_content:
                            # Print to stdout only — avoids duplicate output in terminal
                            # where stderr and stdout both render to the same display
                            print(text, end="", flush=True)
                        else:
                            # Structured-output calls: stream dimly to stderr for progress
                            print(f"{_DIM}{text}{_RESET}", end="", flush=True, file=sys.stderr)

                if print_content:
                    print()

                result = "".join(content_parts)
                _log(
                    f"\n{_GREEN}[llm ←]{_RESET} "
                    f"done  reasoning={reasoning_chars} chars  content={content_chars} chars"
                    + (f"  finish={finish_reason}" if finish_reason and finish_reason != "stop" else "")
                )

                # ── Detailed file log ────────────────────────────────────────
                _write_detail(
                    f"{'=' * 80}\n"
                    f"{datetime.utcnow().isoformat()}  |  {label or 'unknown'}  |  "
                    f"model={self.model}  temp={temperature}\n"
                    f"{'=' * 80}\n\n"
                    f"[SYSTEM PROMPT — {sys_chars} chars]\n"
                    f"{'-' * 80}\n"
                    f"{system_prompt}\n\n"
                    f"[USER PROMPT — {user_chars} chars]\n"
                    f"{'-' * 80}\n"
                    f"{user_prompt}\n\n"
                    f"[RESPONSE — {content_chars} chars"
                    + (f"  TRUNCATED finish={finish_reason}" if finish_reason == "length" else "")
                    + f"]\n"
                    f"{'-' * 80}\n"
                    f"{result}\n\n"
                )

                if not result.strip():
                    raise ValueError(
                        f"Model returned empty content (reasoning={reasoning_chars} chars). "
                        f"Prompt may be too large ({sys_chars + user_chars} chars total). "
                        f"Try reducing MAX_TOKENS or shortening the input."
                    )
                if finish_reason == "length":
                    raise TruncatedResponseError(result)
                return result

            except BadRequestError as e:
                _log(f"\n{_RED}[llm]  BadRequestError: {e}{_RESET}")
                raise
            except RateLimitError as e:
                if attempt == _MAX_RETRIES:
                    _log(f"{_RED}[llm]  all {_MAX_RETRIES} attempts failed — raising{_RESET}")
                    raise
                wait = _RATE_LIMIT_BASE * (2 ** (attempt - 1))
                _log(f"\n{_YELLOW}[llm]  429 rate limit (attempt {attempt}/{_MAX_RETRIES}) — waiting {wait}s{_RESET}")
                time.sleep(wait)
            except Exception as e:
                err_type = type(e).__name__
                _log(f"\n{_RED}[llm]  {err_type}: {e}{_RESET}")
                if attempt == _MAX_RETRIES:
                    _log(f"{_RED}[llm]  all {_MAX_RETRIES} attempts failed — raising{_RESET}")
                    raise

        return ""  # unreachable

    _CONCISENESS_CONSTRAINT = (
        "\n\nRESPONSE LENGTH CONSTRAINT: Keep your JSON response under 5000 characters total. "
        "To achieve this: holistic_assessment max 2 sentences; voice_breaks max 3 items (most "
        "severe only) with each text field under 15 words; missing_moves max 2 items; "
        "dimension_notes notes max 12 words each."
    )

    def _extract_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float,
    ) -> T:
        schema = json.dumps(response_model.model_json_schema(), indent=2)
        field_names = ", ".join(response_model.model_fields.keys())
        augmented_system = (
            system_prompt
            + "\n\n---\n"
            + "OUTPUT FORMAT: Respond with ONLY a single valid JSON object. "
            + "Do not include any explanation, markdown, or text outside the JSON.\n"
            + f"The JSON object must contain exactly these top-level keys: {field_names}\n"
            + f"Full schema for reference:\n{schema}"
        )

        try:
            raw = self._stream(
                system_prompt=augmented_system,
                user_prompt=user_prompt,
                temperature=temperature,
                label=f"json:{response_model.__name__}",
                print_content=False,
            )
        except TruncatedResponseError:
            _log(f"{_YELLOW}[llm]  response truncated — retrying with conciseness constraint{_RESET}")
            raw = self._stream(
                system_prompt=augmented_system + self._CONCISENESS_CONSTRAINT,
                user_prompt=user_prompt,
                temperature=temperature,
                label=f"json:{response_model.__name__}:concise",
                print_content=False,
            )

        try:
            data = self._clean_json(raw)
        except json.JSONDecodeError as e:
            _log(f"{_RED}[llm]  JSON parse failed: {e}{_RESET}")
            _log(f"{_DIM}[llm]  raw response (first 500 chars):\n{raw[:500]}{_RESET}")
            raise

        return response_model.model_validate(data)

    def _parse_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float,
    ) -> T:
        """OpenAI-only: uses beta.chat.completions.parse() (non-streaming)."""
        _log(f"{_CYAN}[llm →]{_RESET} beta.parse()  model={self.model}  schema={response_model.__name__}")
        response = self.client.beta.chat.completions.parse(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format=response_model,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Structured output returned None.")
        _log(f"{_GREEN}[llm ←]{_RESET} beta.parse() done")
        return parsed

    @staticmethod
    def _clean_json(raw: str) -> dict:
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
        if fence:
            text = fence.group(1).strip()
        if not text.startswith("{"):
            start = text.find("{")
            end   = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start : end + 1]
        return json.loads(text)
