# Events Experiments

This area contains the outputs of forensic event construction and the additional Phi-4-mini experiments.

## Event Dataset Results

[`results/`](results/README.md) contains the supplied raw annotations, retained pre-judgment copy, tribunal-validated dataset, human-filtered dataset, and historical judgment log/summary. New cleaning and evaluation outputs use this same area, with distinct filenames.

- **Preparation:** [`clean_generated_events.ipynb`](../../analysis/events/clean_generated_events.ipynb).
- **Automated evaluation:** [`post_generation_judge.py`](../../code/events/README.md).
- **Tribunal analysis:** [`analyze_tribunal_judgments.ipynb`](../../analysis/events/analyze_tribunal_judgments.ipynb).
- **Human evaluation:** All form creation, response processing, and comparative analysis are under [`human_validation/events/`](../../human_validation/events/README.md).

Source ATOMIC data and selected generation inputs remain under [`data/`](../../data/README.md).

## Phi-4-mini

- **Training and notebooks:** [`training/phi4_mini/`](training/phi4_mini/README.md).
- **Saved model outputs:** `results/phi4_mini/`, split into classification and generation.
- **Classification:** Baseline and context-safe variants, with saved comparisons for architectures A and C.
- **Generation:** Base/fine-tuned Phi-4-mini and DeepSeek comparisons on 35 selected unseen events.
- **Environment:** The Phi-4 directory has a separate Poetry project; training/inference requires the optional GPU dependencies and a compatible CUDA host.

Adapter weights are not supplied. Saved-result notebooks can inspect available comparisons without retraining. Historical source paths in split reports and signatures remain provenance records; see the [result dataset mapping](results/README.md).
