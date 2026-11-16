# Events Analysis

These notebooks prepare generated annotations and examine the automated tribunal. Human evaluation code and notebooks are collected separately under [`human_validation/events/`](../../human_validation/events/README.md).

## `clean_generated_events.ipynb`

Applies the existing Latin-character filter and forensic taxonomy mapping.

- **Input:** `experiments/events/results/forensic_atomic_generated_raw.csv`.
- **Output:** `experiments/events/results/forensic_atomic_generated_clean.csv`.
- **Configuration:** Set `INPUT_CSV` and `OUTPUT_CSV` in the first cell.
- **Provenance:** This creates a new cleaning run, not a verified reconstruction of the historical tribunal input. The supplied raw data yields 9,414 rows, but event order differs from the historical judgment log. Supplied validated datasets are protected from overwrite.

## `analyze_tribunal_judgments.ipynb`

Calculates approval, agreement, provider score distributions, and rejection statistics.

- **Input:** `experiments/events/results/tribunal_judgments.csv` by default; `JUDGE_LOG` can select a new run's log.
- **Output:** `experiments/events/results/tribunal_summary_new.csv`, configurable with `SUMMARY_CSV`.
- **Compatibility:** Reads historical and current schemas by column name without requiring legacy-only fields.

The operational command is [`code/events/post_generation_judge.py`](../../code/events/README.md). Supplied datasets and logs are documented under [`experiments/events/results/`](../../experiments/events/results/README.md).
