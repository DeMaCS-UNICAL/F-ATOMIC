import asyncio
import math

import aiohttp

from config.settings import settings
from core.llm_providers import AnthropicProvider, BaseProvider, GeminiProvider, LLMResponse, OpenAIProvider
from core.logger import log


LOG_USAGE = True
PRINT_SYSP = False
PRINT_USP = False
PRINT_OUT = True


class UnifiedGenerator:
    """API clients shared by generation and the three-judge tribunal."""

    def __init__(self):
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("LLM_TIMEOUT_SECONDS must be a finite positive number.")
        self._providers: dict[str, BaseProvider] = {}
        self._closed = False

    def _get_provider(self, provider: str) -> BaseProvider:
        if self._closed:
            raise RuntimeError("UnifiedGenerator has already been closed.")
        provider = provider.strip().lower()
        if provider not in self._providers:
            compatible = {
                "openai": (settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL),
                "openrouter": (settings.OPENROUTER_API_KEY, settings.OPENROUTER_BASE_URL),
                "edenai": (settings.EDENAI_API_KEY, settings.EDENAI_BASE_URL),
            }
            if provider in compatible:
                key, url = compatible[provider]
                adapter = OpenAIProvider(
                    provider, key, self.timeout, url,
                    reasoning_effort=settings.OPENAI_REASONING_EFFORT if provider == "openai" else None,
                )
            elif provider == "anthropic":
                adapter = AnthropicProvider(settings.ANTHROPIC_API_KEY, self.timeout)
            elif provider == "gemini":
                adapter = GeminiProvider(settings.GEMINI_API_KEY, self.timeout, settings.GEMINI_THINKING_LEVEL)
            else:
                raise ValueError(f"Unknown LLM provider: {provider!r}")
            self._providers[provider] = adapter
        return self._providers[provider]

    def validate_configuration(self, provider: str, model: str):
        """Check credentials and SDK availability locally, without an API call."""
        if not isinstance(model, str) or not model.strip():
            raise ValueError("A non-empty model identifier is required for each judge.")
        self._get_provider(provider)

    async def _with_retry(self, adapter: BaseProvider, operation):
        for attempt in range(1, 4):
            try:
                async with asyncio.timeout(self.timeout):
                    return await operation()
            except Exception as exc:
                status = getattr(exc, "status_code", getattr(exc, "status", None))
                if status is not None:
                    transient = status == 429 or isinstance(status, int) and 500 <= status < 600
                else:
                    transient = isinstance(
                        exc, (TimeoutError, ConnectionError, aiohttp.ClientConnectionError)
                        + adapter.connection_errors,
                    )
                if not transient or attempt == 3:
                    log.error("%s request failed after %d attempt(s): %s", adapter.name, attempt, exc)
                    raise
                delay = 2 ** attempt
                log.warning("%s API error, attempt %d/3; retrying in %ds: %s",
                            adapter.name, attempt, delay, exc)
                await asyncio.sleep(delay)

    async def generate(self, provider: str, model: str, prompt: str,
                       system_prompt: str = "You are a Forensic Analyst.", **options) -> str:
        response = await self.generate_response(provider, model, [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ], **options)
        return response.text

    async def generate_response(self, provider: str, model: str,
                                messages: list[dict], **options) -> LLMResponse:
        self.validate_configuration(provider, model)
        if not messages or not any(m.get("role") != "system" for m in messages):
            raise ValueError("At least one conversation message is required.")
        if any(m.get("role") not in {"system", "user", "assistant"}
               or not isinstance(m.get("content"), str) for m in messages):
            raise ValueError("Messages must contain a supported role and text content.")
        adapter = self._get_provider(provider)
        response = await self._with_retry(adapter, lambda: adapter.generate(model, messages, **options))
        if LOG_USAGE:
            log.info("LLM %s/%s returned=%s input=%s output=%s reasoning=%s thinking=%s finish=%s",
                     response.provider, response.model_requested, response.model_returned,
                     response.input_tokens, response.output_tokens, response.reasoning_tokens,
                     response.thinking_tokens, response.finish_reason)
            for message in messages:
                if (message["role"] == "system" and PRINT_SYSP) or (message["role"] != "system" and PRINT_USP):
                    log.info("%s prompt: %s", message["role"], message["content"])
            if PRINT_OUT:
                log.info("LLM output: %s", response.raw_text)
        return response

    async def list_models(self, provider: str = "edenai", contains: str = "") -> list[str]:
        adapter = self._get_provider(provider)
        models = await self._with_retry(adapter, adapter.list_models)
        return [model for model in models if contains.casefold() in model.casefold()]

    async def close(self):
        adapters = list(self._providers.values())
        self._providers.clear()
        self._closed = True
        if adapters:
            outcomes = await asyncio.gather(*(adapter.close() for adapter in adapters), return_exceptions=True)
            for outcome in outcomes:
                if isinstance(outcome, BaseException):
                    log.warning("Could not close an LLM client: %s", outcome)

    async def __aenter__(self):
        if self._closed:
            raise RuntimeError("UnifiedGenerator has already been closed.")
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        await self.close()
