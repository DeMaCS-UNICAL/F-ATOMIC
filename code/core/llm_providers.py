from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re
from urllib.parse import urlsplit

import aiohttp


def clean_json(text: str) -> str:
    """Remove reasoning tags and markdown fences; the original is kept separately."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL)
    return text.replace("```json", "").replace("```", "").strip()


@dataclass(slots=True)
class LLMResponse:
    provider: str
    model_requested: str
    raw_text: str
    model_returned: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    thinking_tokens: int | None = None
    finish_reason: str | None = None
    text: str = field(init=False)

    def __post_init__(self):
        self.text = clean_json(self.raw_text)


class InvalidLLMResponse(ValueError):
    """A successful API request returned an unusable response; do not retry it."""


class ProviderHTTPError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class BaseProvider(ABC):
    connection_errors: tuple[type[Exception], ...] = ()

    def __init__(self, name: str, api_key: str, timeout: float):
        if not api_key or not api_key.strip():
            raise ValueError(f"Missing API key for provider '{name}'.")
        self.name = name
        self.api_key = api_key
        self.timeout = timeout

    @staticmethod
    def validate_url(value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Provider base URL must be an absolute HTTP(S) URL.")
        return value.rstrip("/")

    @staticmethod
    def validate_options(options: dict, supported: set[str]):
        unknown = options.keys() - supported
        if unknown:
            raise ValueError(f"Unsupported generation options: {', '.join(sorted(unknown))}")
        tokens = options.get("max_tokens")
        if tokens is not None and (type(tokens) is not int or tokens <= 0):
            raise ValueError("max_tokens must be a positive integer.")

    @abstractmethod
    async def generate(self, model: str, messages: list[dict], **options) -> LLMResponse:
        pass

    async def list_models(self) -> list[str]:
        raise ValueError(f"Model listing is not supported for '{self.name}'.")

    @abstractmethod
    async def close(self):
        pass


class OpenAIProvider(BaseProvider):
    """OpenAI chat completions, also used with OpenRouter and Eden AI endpoints."""

    def __init__(self, name: str, api_key: str, timeout: float, base_url: str,
                 reasoning_effort: str | None = None):
        super().__init__(name, api_key, timeout)
        from openai import APIConnectionError, APITimeoutError, AsyncOpenAI

        self.connection_errors = (APIConnectionError, APITimeoutError)
        self.reasoning_effort = reasoning_effort
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=self.validate_url(base_url),
            timeout=timeout, max_retries=0,
        )

    async def generate(self, model: str, messages: list[dict], **options) -> LLMResponse:
        self.validate_options(options, {"temperature", "max_tokens", "seed", "reasoning_effort"})
        native = self.name == "openai"
        token_parameter = "max_completion_tokens" if native else "max_tokens"
        kwargs = {
            "model": model, "messages": messages,
            token_parameter: options.get("max_tokens", 800 if native else 2048),
        }
        for key, value in (
            ("temperature", options.get("temperature", None if native else 0.7)),
            ("seed", options.get("seed")),
            ("reasoning_effort", options.get("reasoning_effort", self.reasoning_effort)),
        ):
            if value is not None:
                kwargs[key] = value
        response = await self.client.chat.completions.create(**kwargs)
        if not response.choices:
            raise InvalidLLMResponse(f"{self.name} returned no choices.")
        choice = response.choices[0]
        raw = choice.message.content or ""
        if not isinstance(raw, str):
            raise InvalidLLMResponse(f"{self.name} returned non-text content.")
        usage = getattr(response, "usage", None)
        details = getattr(usage, "completion_tokens_details", None)
        return LLMResponse(
            provider=self.name, model_requested=model, raw_text=raw,
            model_returned=getattr(response, "model", None),
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            reasoning_tokens=getattr(details, "reasoning_tokens", None),
            finish_reason=getattr(choice, "finish_reason", None),
        )

    async def list_models(self) -> list[str]:
        models = []
        async for model in self.client.models.list():
            models.append(model.id)
        return models

    async def close(self):
        await self.client.close()


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str, timeout: float):
        super().__init__("anthropic", api_key, timeout)
        try:
            from anthropic import APIConnectionError, APITimeoutError, AsyncAnthropic
        except ImportError as exc:
            raise ValueError("The selected provider requires the 'anthropic' package.") from exc
        self.connection_errors = (APIConnectionError, APITimeoutError)
        self.client = AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=0)

    async def generate(self, model: str, messages: list[dict], **options) -> LLMResponse:
        self.validate_options(options, {"temperature", "max_tokens"})
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        conversation = [m for m in messages if m["role"] != "system"]
        response = await self.client.messages.create(
            model=model, system=system, messages=conversation,
            temperature=options.get("temperature", 0.0),
            max_tokens=options.get("max_tokens", 500),
        )
        raw = "".join(block.text for block in response.content if block.type == "text")
        usage = getattr(response, "usage", None)
        details = getattr(usage, "output_tokens_details", None)
        return LLMResponse(
            provider=self.name, model_requested=model, raw_text=raw,
            model_returned=getattr(response, "model", None),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            thinking_tokens=getattr(details, "thinking_tokens", None),
            finish_reason=getattr(response, "stop_reason", None),
        )

    async def close(self):
        await self.client.close()


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str, timeout: float, thinking_level: str | None = None):
        super().__init__("gemini", api_key, timeout)
        self.thinking_level = thinking_level
        self.session: aiohttp.ClientSession | None = None

    async def generate(self, model: str, messages: list[dict], **options) -> LLMResponse:
        self.validate_options(options, {"temperature", "max_tokens", "seed", "thinking_level"})
        model_id = model if model.startswith("models/") else f"models/{model}"
        config = {
            "temperature": options.get("temperature", 0.0),
            "maxOutputTokens": options.get("max_tokens", 800),
        }
        thinking = options.get("thinking_level", self.thinking_level)
        if thinking is not None:
            config["thinkingConfig"] = {"thinkingLevel": thinking}
        if options.get("seed") is not None:
            config["seed"] = options["seed"]
        payload = {
            "contents": [
                {"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [{"text": m["content"]}]}
                for m in messages if m["role"] != "system"
            ],
            "generationConfig": config,
        }
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_id}:generateContent"
        async with self.session.post(url, json=payload, headers={"x-goog-api-key": self.api_key}) as response:
            if response.status != 200:
                raise ProviderHTTPError(response.status, await response.text())
            try:
                result = await response.json()
            except (ValueError, aiohttp.ContentTypeError) as exc:
                raise InvalidLLMResponse("Gemini returned an invalid JSON response.") from exc
        try:
            candidate = result["candidates"][0]
            parts = candidate.get("content", {}).get("parts", [])
            raw = "".join(part["text"] for part in parts if "text" in part and not part.get("thought"))
        except (KeyError, IndexError, TypeError) as exc:
            raise InvalidLLMResponse("Gemini returned no usable candidate.") from exc
        usage = result.get("usageMetadata", {})
        return LLMResponse(
            provider=self.name, model_requested=model, raw_text=raw,
            model_returned=result.get("modelVersion"),
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
            thinking_tokens=usage.get("thoughtsTokenCount"),
            finish_reason=candidate.get("finishReason"),
        )

    async def close(self):
        if self.session is not None:
            await self.session.close()
