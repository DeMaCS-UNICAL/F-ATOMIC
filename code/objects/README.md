# Objects Workflow

This folder generates forensic contexts for physical entities extracted from the Events dataset. Entity extraction itself is in [`analysis/objects/`](../../analysis/objects/README.md).

## `prompts.py`

Defines the forensic taxonomy, entity prompt, response schema, and content checks.

- **Input:** An entity, with optional sense and event context.
- **Generation:** Requests up to two forensic contexts.
- **Relations:** `IsA`, `UsedFor`, `AtLocation`, `MadeOf`, `PartOf`, `HasProperty`, and `HasA`.
- **Validation:** Parses contexts into Pydantic objects and reports content problems separately.
- **Example handling:** Excludes the prompt's example entity from generation.

## `generate_contexts.py`

Queries Eden AI for the selected entities using its existing standalone OpenAI-compatible client.

- **Input:** A CSV containing `entity` and `physical` columns. Rows labelled `yes` or `maybe` are eligible.
- **Output:** A JSONL call log/checkpoint and a CSV with one row per entity/context.
- **Resume:** Skips entities whose last JSONL record is `ok`; unsuccessful entities can be retried on a later run.
- **Metadata:** Records raw response, parsed contexts, problems, token usage, model identifiers, timestamp, and latency.
- **Parameters:** Temperature 0.7, seed 42, maximum 2048 tokens, concurrency 5, and application retry setting `MAX_ATTEMPTS=5`.

The command reads `EDENAI_API_KEY` from the environment or root `.env`. It keeps its current client, endpoint, parsing, parameters, and retry behavior; integration with the shared LLM facade remains a later step.

### Usage

List models and select an ID in the `provider/model` format:

```bash
poetry run python code/objects/generate_contexts.py --list-models deepseek
```

Generate contexts for a pilot batch from the supplied classification table:

```bash
poetry run python code/objects/generate_contexts.py \
  --input experiments/objects/results/entity_classification.csv \
  --out experiments/objects/results/generated_contexts \
  --model YOUR_PROVIDER/YOUR_MODEL --limit 20
```

Relative `--input` and `--out` paths resolve against the working directory. The example writes `generated_contexts.jsonl` and `generated_contexts.csv`. Those generated outputs are not supplied; the current artifacts describe extraction and classification.
