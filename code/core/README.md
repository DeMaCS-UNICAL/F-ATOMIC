# Shared Core

This folder provides the common infrastructure available to the Events and Objects workflows. It contains no event-specific prompts or annotation schemas.

## `generator.py`

`UnifiedGenerator` selects and reuses clients, logs response metadata, and manages transient API retries.

- **Text interface:** `generate(provider, model, prompt, system_prompt=..., **options)` returns cleaned text.
- **Complete response:** `generate_response(provider, model, messages, **options)` also exposes original text, model identifiers, token usage, and finish reason.


## `llm_providers.py`

Keeps all API adapters together, independently of project settings and logging.

| Class | Purpose |
|:---|:---|
| `OpenAIProvider` | Native OpenAI and compatible OpenRouter/Eden AI endpoints. |
| `AnthropicProvider` | Asynchronous Anthropic messages. |
| `GeminiProvider` | Gemini REST requests through a reusable `aiohttp` session. |
| `LLMResponse` | Original/cleaned text, requested/returned model, optional token counts, and finish reason. |

Defaults are OpenRouter/Eden AI 2048 tokens and temperature 0.7, OpenAI 800 tokens with no explicit temperature, Anthropic 500 tokens and temperature 0.0, and Gemini 800 tokens and temperature 0.0. Reasoning/thinking options are omitted unless configured. Missing metadata is `None`.

`clean_json` removes markdown fences and `<think>` blocks while the original response remains available.

## `logger.py`

Configures tqdm-compatible console output and the shared `logs/pipeline.log` file at the repository root, independently of the working directory.

The [Events tribunal](../events/README.md) uses these modules. 
