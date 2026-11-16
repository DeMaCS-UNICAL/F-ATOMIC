# Configuration

`settings.py` reads `.env` from the repository root and resolves configured relative paths against that root. See [`.env.example`](../../.env.example) for the available environment variables.

## Shared LLM Settings

- **Providers:** `openai`, `openrouter`, `anthropic`, `gemini`, and `edenai`.
- **Credentials:** Only the selected clients require API keys.
- **Endpoints:** OpenAI, OpenRouter, and Eden AI have configurable base URLs.
- **Timeout:** `LLM_TIMEOUT_SECONDS` defaults to 120 per attempt.
- **Optional parameters:** `OPENAI_REASONING_EFFORT` and `GEMINI_THINKING_LEVEL` are omitted when empty; configure them for an appropriate model.
- **Logs:** Shared pipeline output goes to `logs/pipeline.log` at the repository root.

## Events Settings

The default panel uses OpenAI, Anthropic, and Gemini with their configured model names. Two alternatives are available:

- Set `USE_SINGLE_JUDGE_PROVIDER=true` to repeat `SINGLE_JUDGE_PROVIDER` and `SINGLE_JUDGE_MODEL` for all three slots.
- Configure all three `JUDGE_1_PROVIDER`/`JUDGE_1_MODEL` through `JUDGE_3_PROVIDER`/`JUDGE_3_MODEL` pairs. Partial panels and combinations with single-provider mode are rejected.

Provider configuration, local credentials, SDK availability, timeout, and positive `JUDGE_SEMAPHORE` are checked before batch evaluation. Remote authentication and model availability require an actual API request.

`JUDGEMENT_FILE` defaults to `experiments/events/results/tribunal_judgments_new.csv`, separately from the supplied historical log. Input ATOMIC sources remain under `data/atomic_dataset/`; event output defaults are under `experiments/events/results/`.

Redis and generation worker settings remain available for `events.state_manager` and standalone pipeline profiles. The batch CLI selects its event concurrency through `--workers`. The current checkout does not include a full generation launcher.

Event prompts and profiles are documented in [`code/events/`](../events/README.md).
