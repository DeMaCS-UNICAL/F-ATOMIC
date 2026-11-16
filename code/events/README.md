# Events Workflow

This folder contains the components used to construct and evaluate forensic interpretations of ATOMIC events.

## Generation Components

| Module | Description |
|:---|:---|
| `filter.py` | Selects candidate source events using forensic trigger-word patterns. |
| `prompts.py` | Defines generation and tribunal prompts and constructs the user prompt for an event. |
| `validator.py` | Validates and normalizes event annotations with Pydantic. |
| `state_manager.py` | Provides Redis queues, deduplication, and result buffering. |
| `presets.py` | Retains standalone generation/evaluation profiles and synthetic category definitions. |

The generation prompt requests one or two criminal interpretations from the forensic taxonomy. Each interpretation includes category, subcategory, context, and 16 ATOMIC relations. These reusable components are supplied without a complete generation launcher.

## `judge.py`

Evaluates the compact event annotation with three configured judges in parallel.

- **Decision:** At least two approvals and a mean score of at least 50 across all three judges.
- **API failures:** The shared generator retries only the affected judge's transient API call, up to three total attempts. An exhausted or permanent error contributes `vote=error`, `score=0`.
- **Response validation:** Unusable responses or malformed verdicts contribute an error without another API call. A valid rejection is a completed decision.
- **Output:** Returns `(True, data)` or `(False, None)`, leaving the annotation unchanged. The CSV records each judge's provider, requested model, vote, score, and reason.

Existing incompatible log headers are rejected before evaluation. Historical logs remain readable by the analysis notebooks.

## `post_generation_judge.py`

Batch command for an existing event CSV. Run from the repository root:

```bash
poetry run python code/events/post_generation_judge.py \
  --input experiments/events/results/forensic_atomic_generated_clean.csv \
  --output experiments/events/results/forensic_atomic_tribunal_validated_new.csv \
  --judgement_log experiments/events/results/tribunal_judgments_new.csv \
  --workers 3
```

The CLI preserves supplied `original_row_id` values, otherwise using the input CSV row index. Relative CLI arguments resolve against the working directory. Provider credentials come from the root `.env`; clients are closed after evaluation. Only approved rows enter the output dataset.

Use [`clean_generated_events.ipynb`](../../analysis/events/clean_generated_events.ipynb) to prepare a new cleaned input. The supplied pre-judgment file is a retained duplicate of the validated dataset, not a verified reconstruction of the original tribunal input.

## Human Evaluation

Form creation, response processing, and human-LLM analyses are collected under [`human_validation/events/`](../../human_validation/events/README.md), together with their data and reports.

## `plan_reconstruction.asp`

An ASP example that combines a criminal event's temporal relations with observed actions and minimizes the additional inferred steps. It is a standalone symbolic use case, separate from the API-based generation workflow.
