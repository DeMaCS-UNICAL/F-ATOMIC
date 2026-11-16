# F-ATOMIC: Forensic Commonsense Knowledge

This project constructs and explores a forensic commonsense knowledge graph. It reinterprets everyday **events** from ATOMIC within criminal contexts and validates the generated annotations.

## Contributions

- **Events:** Generation, cleaning, and Multi-Judge validation of forensic interpretations with 16 ATOMIC relations.
- **Human evaluation:** Comparison between automated judgments and human assessments, including an additional human-filtered dataset.
- **Model experiments:** Phi-4-mini classification and generation experiments on forensic events.
- **Symbolic reasoning:** An Answer Set Programming example for criminal plan reconstruction.

---

## Dataset and Results

The tribunal-validated event dataset contains **9,175 annotations** across six crime categories.

| Crime Category | Instances | Percentage |
|:---|---:|---:|
| Financial Crimes | 2,894 | 31.5% |
| Organized Crimes | 2,072 | 22.6% |
| Violent Crimes | 1,877 | 20.5% |
| Property Crimes | 1,254 | 13.7% |
| Cyber Crimes | 844 | 9.2% |
| Public Order / Justice | 234 | 2.6% |
| **Total** | **9,175** | **100.0%** |

The original human comparison covers **550 form-event judgments**. A subsequent unified evaluation covers **671 distinct events**. The supplied human-filtered dataset contains **9,100 annotations**, excluding 75 events not approved under the joint human score/approval-percentage rule. These are separate evaluation cohorts.

---

## Project Structure

| Folder | Description |
|:---|:---|
| [**code/core/**](code/core/README.md) | Shared LLM facade, provider adapters, and logging. |
| [**code/config/**](code/config/README.md) | Provider credentials, execution settings, and repository paths. |
| [**code/events/**](code/events/README.md) | Event filtering, prompts, automated validation, tribunal, and ASP example. |
| [**data/**](data/README.md) | ATOMIC sources, selected event inputs, and reference resources. |
| [**analysis/**](analysis/README.md) | Event cleaning and automated tribunal analysis notebooks. |
| [**experiments/**](experiments/README.md) | Generated/validated datasets and event model experiments. |
| [**human_validation/**](human_validation/README.md) | Form creation, human-analysis code, form inputs, and evaluation reports. |

Generated event datasets and tribunal artifacts are stored directly in [`experiments/events/results/`](experiments/events/results/README.md), beside the `phi4_mini/` model results. `data/` contains only source inputs and reference resources.

## Installation

- **Python 3.11–3.13** and **Poetry** for the main environment.
- **Redis** when using the event state manager.
- **CUDA GPU** for Phi-4 training and inference; its dependencies use a separate Poetry environment.

```bash
poetry install --no-root
cp .env.example .env
```

Fill the selected providers' credentials in `.env` at the repository root. See [configuration](code/config/README.md) for provider and three-judge settings. For interactive imports, run `export PYTHONPATH="$PWD/code:$PWD"` from the repository root. `code/` is a source directory, not a Python package.

## Workflow

### 1. Events

Source selection, prompts, structural validation, and Redis state management are in [`code/events/`](code/events/README.md). This checkout includes the components and supplied datasets, but no complete generation launcher.

Use [`clean_generated_events.ipynb`](analysis/events/clean_generated_events.ipynb) to clean a new raw dataset, then run the tribunal:

```bash
poetry run python code/events/post_generation_judge.py \
  --input experiments/events/results/forensic_atomic_generated_clean.csv \
  --output experiments/events/results/forensic_atomic_tribunal_validated_new.csv \
  --judgement_log experiments/events/results/tribunal_judgments_new.csv \
  --workers 3
```

The current tribunal approves an unchanged annotation when at least two judges approve and the mean score across all three is at least 50. Transient API failures receive three total attempts for the affected judge, with waits of 2 and 4 seconds; after exhaustion that judge contributes score zero. Invalid verdicts are not retried.

### 2. Human Evaluation and Phi-4-mini

Form creation, response processing, human-LLM comparison notebooks, and the statistics helper are all in [`human_validation/events/`](human_validation/events/README.md), together with form data and reports. The resulting human-filtered event dataset remains in `experiments/events/results/`.

Classification and generation notebooks are in [`experiments/events/training/phi4_mini/`](experiments/events/training/phi4_mini/README.md), with saved predictions and figures under `experiments/events/results/phi4_mini/`. The generation comparison uses 35 selected unseen events. Adapter weights are not included.

### 3. Plan Reconstruction

[`plan_reconstruction.asp`](code/events/plan_reconstruction.asp) illustrates how temporal relations from an event interpretation can support reconstruction of a criminal plan from partial observations.
