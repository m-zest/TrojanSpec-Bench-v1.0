"""Unified LLM client interface.

Primary backend:

* **Fireworks** - one key, four independent model families (DeepSeek, Kimi,
  GPT-OSS, GLM). This is the only backend used in the default workflows.

Optional fallbacks (present but never called by default workflows):

* **OpenRouter** - one key, many model families.
* **Anthropic**  - Claude as elicitor / monitor.
* **OpenAI**     - GPT-4o as elicitor / monitor.
* **Ollama**     - local models on your own GPU, free.

Cross-family diversity is required for the monitor-consensus ablations, so the
factory deliberately exposes several independent families.
"""

from __future__ import annotations

import asyncio
import os
import random
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

from trojanspec.utils.logging import get_logger

load_dotenv()

log = get_logger("llm")

# Retry policy for transient backend failures (HTTP 429 / 5xx / transport).
_MAX_RETRIES = 3
_BASE_DELAY_SEC = 2.0


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or 500 <= code < 600
    return isinstance(exc, (httpx.TransportError, httpx.TimeoutException))


async def _with_retry(coro_factory, *, label: str):
    """Await ``coro_factory()`` with exponential backoff on 429/5xx/transport.

    Up to ``_MAX_RETRIES`` retries, delay ``_BASE_DELAY_SEC * 2**attempt``
    plus jitter. Non-retryable errors propagate immediately.
    """
    attempt = 0
    while True:
        try:
            return await coro_factory()
        except Exception as exc:  # noqa: BLE001 - classified by _is_retryable
            if not _is_retryable(exc) or attempt >= _MAX_RETRIES:
                raise
            delay = _BASE_DELAY_SEC * (2**attempt) + random.uniform(0, 1)
            log.warning(
                "%s: retryable error (%s), retry %d/%d in %.1fs",
                label,
                type(exc).__name__,
                attempt + 1,
                _MAX_RETRIES,
                delay,
            )
            await asyncio.sleep(delay)
            attempt += 1


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    raw: dict


class LLMClient:
    """Abstract base for all backends."""

    family: str = "abstract"

    def __init__(self, model: str, temperature: float = 0.7, max_tokens: int = 2048):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def complete(self, system: str, user: str) -> LLMResponse:  # pragma: no cover
        raise NotImplementedError


class _OpenAICompatibleClient(LLMClient):
    """Shared logic for OpenAI-style ``/chat/completions`` endpoints."""

    base_url: str
    api_key_env: str
    extra_headers: dict[str, str] = {}
    request_timeout: float = 300.0

    def _headers(self) -> dict[str, str]:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(
                f"{self.api_key_env} is not set. Add it to your .env "
                f"(see .env.example) to use the {self.family} backend."
            )
        return {"Authorization": f"Bearer {key}", **self.extra_headers}

    def _extra_payload(self) -> dict:
        """Backend-specific request fields. Default: none."""
        return {}

    async def complete(self, system: str, user: str) -> LLMResponse:
        async def _post() -> dict:
            # 300s: GLM/DeepSeek reasoning chains exceed 180s; retry/backoff
            # still handles hard failures above this ceiling.
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                        **self._extra_payload(),
                    },
                )
                r.raise_for_status()
                return r.json()

        data = await _with_retry(_post, label=f"{self.family}:{self.model}")
        usage = data.get("usage", {}) or {}
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            model=self.model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            raw=data,
        )


class OpenRouterClient(_OpenAICompatibleClient):
    """OpenRouter: a single key fronting many model families."""

    family = "openrouter"
    base_url = "https://openrouter.ai/api/v1"
    api_key_env = "OPENROUTER_API_KEY"
    extra_headers = {
        "HTTP-Referer": "https://github.com/m-zest/trojanspec-bench",
        "X-Title": "TrojanSpec-Bench",
    }

    def __init__(self, model: str = "meta-llama/llama-3.3-70b-instruct", **kwargs):
        super().__init__(model, **kwargs)


class FireworksClient(_OpenAICompatibleClient):
    """Fireworks AI: OpenAI-compatible endpoint, primary backend.

    Model ids are fully qualified (``accounts/fireworks/models/<name>``) and
    supplied by the factory below.
    """

    family = "fireworks"
    base_url = "https://api.fireworks.ai/inference/v1"
    api_key_env = "FIREWORKS_API_KEY"

    def __init__(self, model: str, **kwargs):
        super().__init__(model, **kwargs)

    def _extra_payload(self) -> dict:
        # gpt-oss reliably honours Fireworks structured output; deepseek/kimi
        # may reject the parameter, so it is enabled for gpt-oss only.
        if "gpt-oss" in self.model:
            return {"response_format": {"type": "json_object"}}
        return {}


class OpenAIClient(_OpenAICompatibleClient):
    """OpenAI native endpoint."""

    family = "openai"
    base_url = "https://api.openai.com/v1"
    api_key_env = "OPENAI_API_KEY"

    def __init__(self, model: str = "gpt-4o", **kwargs):
        super().__init__(model, **kwargs)


class AnthropicClient(LLMClient):
    """Anthropic Messages API (system prompt is a top-level field)."""

    family = "anthropic"
    base_url = "https://api.anthropic.com/v1"

    def __init__(self, model: str = "claude-3-5-sonnet-latest", **kwargs):
        super().__init__(model, **kwargs)

    async def complete(self, system: str, user: str) -> LLMResponse:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env "
                "(see .env.example) to use the anthropic backend."
            )
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                },
            )
            r.raise_for_status()
            data = r.json()
            usage = data.get("usage", {}) or {}
            return LLMResponse(
                text="".join(
                    block.get("text", "")
                    for block in data.get("content", [])
                    if block.get("type") == "text"
                ),
                model=self.model,
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                raw=data,
            )


class OllamaClient(_OpenAICompatibleClient):
    """Local Ollama via its OpenAI-compatible ``/v1/chat/completions``.

    Free, runs on the local GPU. No auth, no ``response_format`` (Ollama does
    not support structured output reliably). 600s timeout for large local
    models; shares the same retry/backoff as the Fireworks client.
    """

    family = "ollama"
    api_key_env = "OLLAMA_API_KEY"  # unused; _headers is overridden
    request_timeout = 600.0

    def __init__(self, model: str = "qwen2.5:32b", **kwargs):
        kwargs.setdefault("max_tokens", 4096)
        super().__init__(model, **kwargs)
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.base_url = f"{host.rstrip('/')}/v1"

    def _headers(self) -> dict[str, str]:
        # Ollama ignores auth; send none.
        return {"Content-Type": "application/json"}


# Logical family name -> (class, kwargs). Keeps call sites backend-agnostic.
# Fireworks families are listed first: they are the primary, default backend.
# The four elicitor families below are four independent model families
# (DeepSeek, Moonshot Kimi, OpenAI GPT-OSS, Zhipu GLM) for cross-family
# diversity in generation and monitor consensus.
_FW = "accounts/fireworks/models"
_FAMILIES: dict[str, tuple[type[LLMClient], dict]] = {
    "fireworks-deepseek": (FireworksClient, {"model": f"{_FW}/deepseek-v4-pro"}),
    "fireworks-kimi": (FireworksClient, {"model": f"{_FW}/kimi-k2p6"}),
    "fireworks-gptoss": (FireworksClient, {"model": f"{_FW}/gpt-oss-120b"}),
    "fireworks-glm": (FireworksClient, {"model": f"{_FW}/glm-5p1"}),
    "fireworks-kimi-k2p5": (FireworksClient, {"model": f"{_FW}/kimi-k2p5"}),
    "openrouter-llama": (OpenRouterClient, {"model": "meta-llama/llama-3.3-70b-instruct"}),
    "openrouter-claude": (OpenRouterClient, {"model": "anthropic/claude-3.5-sonnet"}),
    "openrouter-gpt4o": (OpenRouterClient, {"model": "openai/gpt-4o"}),
    "openrouter-deepseek": (OpenRouterClient, {"model": "deepseek/deepseek-chat"}),
    "openrouter-qwen": (OpenRouterClient, {"model": "qwen/qwen-2.5-72b-instruct"}),
    # Local Ollama (primary backend after the Fireworks rate-limit pivot).
    # Note: qwen2.5:32b substitutes for 72b - the A100 here is 40GB and 72b
    # (~47GB Q4) does not fit; 32b is same Qwen family and fits comfortably.
    "ollama-qwen": (OllamaClient, {"model": "qwen2.5:32b"}),
    "ollama-qwen-coder": (OllamaClient, {"model": "qwen2.5-coder:32b"}),
    "ollama-deepseek-coder": (OllamaClient, {"model": "deepseek-coder-v2:16b"}),
    "ollama-llama": (OllamaClient, {"model": "llama3.3:70b"}),
    "anthropic": (AnthropicClient, {"model": "claude-3-5-sonnet-latest"}),
    "openai": (OpenAIClient, {"model": "gpt-4o"}),
}


def available_families() -> list[str]:
    """Logical family names accepted by :func:`get_client`."""
    return sorted(_FAMILIES)


def get_client(family: str, **kwargs) -> LLMClient:
    """Construct a client for a logical family.

    ``kwargs`` (e.g. ``temperature``, ``max_tokens``) override defaults.
    """
    if family not in _FAMILIES:
        raise ValueError(
            f"Unknown family {family!r}. Available: {', '.join(available_families())}"
        )
    cls, defaults = _FAMILIES[family]
    return cls(**{**defaults, **kwargs})
