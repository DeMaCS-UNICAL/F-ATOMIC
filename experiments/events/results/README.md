# Events Results

This folder contains the outputs of event generation, cleaning, and evaluation. Selected generation inputs remain in [`data/events/`](../../../data/events/README.md).

## Supplied Datasets and Logs

| File | Description |
|:---|:---|
| `forensic_atomic_generated_raw.csv` | 9,424 raw generated annotations. |
| `forensic_atomic_tribunal_validated.csv` | 9,175 validated annotations with original row identifiers. |
| `forensic_atomic_final.csv` | 9,100 annotations after the unified human evaluation excludes 75 events and final dataset. |
| `tribunal_judgments.csv` | The supplied log of 9,414 judgments, retaining its original schema and IDs. |
| `tribunal_summary.csv` | The supplied historical tribunal statistics. |
| `phi4_mini/` | Saved classification/generation predictions, metrics, and figures. |

The original human comparison covers 550 form-event judgments. The later unified comparison covers 671 distinct events and supports the human-filtered subset. Human inclusion requires both mean score >= 50 and approval percentage >= 50%. Human-analysis code and comparison reports are in [`human_validation/events/`](../../../human_validation/events/README.md).

## New Runs

- [`clean_generated_events.ipynb`](../../../analysis/events/clean_generated_events.ipynb) writes `forensic_atomic_generated_clean.csv`. The supplied raw data yields 9,414 cleaned rows, but their event order differs from the historical log; positions alone cannot reconstruct historical matches.
- [`post_generation_judge.py`](../../../code/events/README.md) writes `tribunal_judgments_new.csv` by default. The current schema records model identifiers and rejects incompatible append operations.
- [`analyze_tribunal_judgments.ipynb`](../../../analysis/events/analyze_tribunal_judgments.ipynb) writes `tribunal_summary_new.csv` by default, preserving the supplied summary.
- [`compare_human_llm_judgments.ipynb`](../../../human_validation/events/compare_human_llm_judgments.ipynb) writes the human-filtered event dataset and any unmatched-event audit in this folder.
