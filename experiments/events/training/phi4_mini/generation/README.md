# Event Generation Experiment

The main comparison uses 35 unseen events from `data/events/selected_events_for_phi4.csv` and compares base/fine-tuned Phi-4-mini with supplied DeepSeek outputs.

## Notebooks

| Notebook | Purpose |
|:---|:---|
| `01_train.ipynb` | Train the Phi-4-mini adapter. |
| `02_generate.ipynb` | Generate base or fine-tuned outputs; select the variant before running. |
| `03_validate.ipynb` | Apply the shared notebook validation rules to the supplied model outputs. |
| `04_clean_compare.ipynb` | Normalize outputs and export paired event statistics and figures. |
| `05_audit_supplied_outputs.ipynb` | Check prompt-variant coverage and DeepSeek judgment records. |

## Saved Results

All paths below are relative to `experiments/events/results/phi4_mini/generation/`.

- **`raw/`:** Original supplied base/fine-tuned JSONL outputs and DeepSeek event annotations.
- **`validated/`:** Structural validation outputs, rejected interpretations, and event/branch traces.
- **`cleaned/`:** Normalized annotations, paired event comparisons, distributions, and figures.
- **`judged/`:** DeepSeek judgments and their summary. The log has 70 approved records for 70 generated branches.
- **`prompt_variants/`:** Additional supplied outputs, failure records, and coverage/label-agreement summaries.

The `with_extra_examples` variant contains 63 successful branches from 33 events and two failed events. `without_extra_examples` contains 38 successful branches from 19 events and 16 failed events. Each success/failure pair covers all 35 selected inputs.

## Comparison Limits

The supplied prompt-variant files do not identify the exact checkpoint, alternate prompt text, generation settings, or seed. The current `prompt.py` contains one example, rather than the stated two extra examples.

Training/inference uses the separate [Phi-4 environment](../README.md); adapter weights are not included. The saved-output analysis notebooks can be used without retraining.
