# Phi-4-mini Events Experiments

This folder contains separate category-classification and forensic-generation experiments on the Events dataset. Saved predictions, metrics, and figures are under `experiments/events/results/phi4_mini/`.

## Classification

- **Baseline:** `classification/baseline/01_prepare.ipynb` prepares the seed-42 split. `02_train_evaluate.ipynb` trains and evaluates architectures A and C.
- **Context-safe:** `classification/context_safe/01_prepare.ipynb` prepares the seed-123 split. `02_train_evaluate.ipynb` trains and evaluates the corresponding architectures.
- **Summary:** `classification/03_results_summary.ipynb` displays saved test comparisons without requiring a GPU.

The source is `experiments/events/results/forensic_atomic_tribunal_validated.csv`. Supplied splits, checksums, signatures, and dataset identifiers are retained.

## Generation

Run `generation/01_train.ipynb`, `02_generate.ipynb`, `03_validate.ipynb`, and `04_clean_compare.ipynb` in sequence. Training and inference share `generation/prompt.py`. The training split uses seed 321; training uses seed 42. The 35 unseen inputs remain in `data/events/selected_events_for_phi4.csv`.

`generation/05_audit_supplied_outputs.ipynb` inspects additional prompt variants and the DeepSeek judge log on a CPU.

## Environment and Outputs

This directory has its own Poetry project. From the repository root:

```bash
cd experiments/events/training/phi4_mini
poetry install
```

Use `poetry install --with gpu` on a compatible CUDA host for training and inference. The adapter weights are not supplied; new weights and checkpoints go to experiment-local `adapters/` folders ignored by Git.

Notebooks locate the repository root from the current working directory and can be started from the root or their own subdirectory.
