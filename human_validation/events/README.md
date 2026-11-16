# Events Human Evaluation

This folder contains the human-evaluation workflow, from Google Forms creation to comparison of human and LLM judgments. New evaluations can use their own filenames, form labels, row counts, tribunal logs, and report directories. The supplied original and unified evaluations are examples, not required cohort types.

## `create_form.py`

Creates event annotation forms with reproducible random sampling and optional English-to-Italian translation. `--csv` accepts any event CSV using the event annotation schema; the four displayed relations remain `xIntent`, `xAttr`, `xEffect`, and `oEffect`.

```bash
poetry run python human_validation/events/create_form.py \
  --csv experiments/events/results/forensic_atomic_tribunal_validated.csv \
  --credentials client_secrets.json \
  --output-dir human_validation/events/data/my_evaluation \
  --random-sample --sample-size 50 --seed 14
```

- **Authentication:** Requires a local Google OAuth credentials file. Google SDKs are loaded when authentication starts.
- **Paths:** Relative arguments resolve against the repository root; absolute paths are supported. UTF-8 CSVs with or without a BOM are accepted.
- **Output:** Sampled-event JSON and form metadata are written to `--output-dir`. Use separate directories for separate evaluations to retain samples that share the same seed.

## `analyze_form_responses.ipynb`

Parses a form's response CSV, aggregates human scores and approvals, and joins them to a dataset and an LLM log. Configure paths in the first cell; the `X` filenames are placeholders for local inputs.

| Configuration | Purpose |
|:---|:---|
| `JSON_FILE`, `HUMAN_CSV`, `FORM_NAME` | Sample JSON (`events` list), form response export, and arbitrary form label. |
| `ORIGINAL_DATASET`, `JUDGE_CSV`, `BRIDGE_COLS` | Source dataset, corresponding LLM log, and columns identifying sampled events. Include `event` in the bridge. |
| `RESPONSE_START_COLUMN`, `RESPONSE_COLUMNS_PER_EVENT`, `SCORE_OFFSET`, `DECISION_OFFSET` | Response layout; defaults match the score/vote/reason fields created by `create_form.py`. |
| `HUMAN_SCORE_MULTIPLIER` | `1` for 0–100 scores; `10` for 0–10 scores. |
| `REPORTS`, `COMPARISON_FILES`, `COMPARISON_GLOB` | Per-form report directory and explicit list of comparisons to combine, or a configurable glob. No `FV_*` naming requirement. |
| `AGGREGATE_CSV`, `STATISTICS_JSON`, `DASHBOARD_PATH` | Independent aggregate, summary, and dashboard outputs. |

Existing `original_row_id` values are preserved. `USE_DATASET_ROW_INDEX` is an explicit legacy option: enable it only when source row positions are known to identify the corresponding log. Never reconstruct historical associations from reordered files. Missing or ambiguous matches are reported instead of silently dropping or multiplying evaluations.

Scores are averaged per event; the joint approval rule remains mean score >= 50 and approval percentage >= 50%. Correlations are undefined for insufficient or constant observations and are reported as NaN. Confusion matrices retain both decision classes even for a single-class sample.

## `human_llm_statistics.py`

Compares any number of named human aggregate CSVs. There is no required number of rows, no required filename, and no need to provide both the original and unified evaluations.

```bash
poetry run python human_validation/events/human_llm_statistics.py \
  --human-csv human_validation/events/data/my_evaluation/human_judgments.csv \
  --cohort my_evaluation \
  --judge-csv experiments/events/results/my_tribunal_judgments.csv \
  --output-dir human_validation/events/results/my_comparison
```

Repeat `--human-csv` for multiple cohorts. Labels default to file stems; supply one `--cohort` per CSV to choose distinct labels. `--root` changes the base for relative paths; root discovery otherwise uses the script location and does not depend on an archived CSV being present.

### Input schema

| Input | Required columns / behavior |
|:---|:---|
| Human aggregates | `original_row_id`, `event`, `human_score`, `human_approval_pct`. Scores and percentages use 0–100. Rows may represent distinct events or repeated events evaluated in different forms. |
| LLM decisions | `status` (`APPROVED` or `REJECTED`) and `score_avg_all`, either embedded in the human CSV or joined from `--judge-csv` using `original_row_id` and `event`. A joined log must identify each evaluated event uniquely. |
| Optional form metadata | `form_id` enables per-form comparisons. Alternatively, `individual_responses_json` reconstructs form-event observations. Each response has `form_number` (or `form_id`), `decision`, and `score_0_10` (scaled by 10) or `human_score` (already 0–100). |
| Optional categories | `crime_category` in the human CSV, or `--dataset-csv` pointing to a lookup with `original_row_id`, `event`, and `crime_category`. |
| Optional log metadata | `approvals_count` enables vote/policy reports; `judgeN_provider`, `judgeN_vote`, and `judgeN_score` enable available provider summaries for judge slots 1–3. |

`--llm-source auto` preserves embedded LLM decisions if available, otherwise uses the supplied log. `--llm-source log` explicitly compares against the supplied log even if embedded decisions exist; `--llm-source embedded` requires decisions in the human CSV. If both sources are supplied, the join audit records missing/nonunique matches and disagreements. Missing or ambiguous log matches stop a comparison that relies on the log.

Each cohort produces summary, comparison, join audit, and figures under `<output-dir>/<cohort>/`. Form/category reports are produced only when the corresponding metadata exists. Shared log summaries are written directly under the output directory when a log is supplied. Missing human scores are excluded from the relevant comparisons, whose `n` reports the observations actually used. Thresholds and metric formulas remain unchanged: 50/60 for scores and approval percentages, plus score >= threshold and approval >= 50%.

Python usage exposes the same configuration:

```python
from pathlib import Path
from human_validation.events.human_llm_statistics import run

tables = run(
    human_csvs={"new_forms": Path("human_validation/events/data/new_forms.csv")},
    judge_csv=Path("experiments/events/results/new_judgments.csv"),
    output_dir=Path("human_validation/events/results/new_comparison"),
)
```

Running without `--human-csv` (or calling `run()` without `human_csvs`) selects the supplied archive preset. It preserves the original table keys and output locations: original reports in `results/form_results_v1/`, unified reports in `results/form_results_v2/unified/`, and shared LLM reports in `results/form_results_v2/`. Row counts are calculated from the inputs, never asserted against the documented archive sizes.

## `compare_human_llm_judgments.ipynb`

Provides an interactive view of the same tables and figures. Configure `HUMAN_CSVS`, `JUDGE_CSV`, optional `DATASET_CSV`, `LLM_SOURCE`, and `OUTPUT_DIR` in the first cell. Every display follows the configured cohort mapping. The default examples use the supplied files but write to `results/comparison_run/`, keeping archived reports separate. Existing saved outputs reflect previous executions.

The final cell optionally exports a human-filtered dataset. It is disabled until `FILTER_DATASET_PATH`, `FILTER_HUMAN_CSV`, and `FILTER_OUTPUT_PATH` are configured. Choose matching columns with `FILTER_KEY_COLUMNS` and optional `FILTER_FALLBACK_COLUMNS` (`[]` disables fallback). The supplied scenario-column defaults preserve the original matching policy; datasets with reliable IDs may instead use `['original_row_id', 'event']` without fallback. Only matched scenarios explicitly rejected by score >= 50 and approval >= 50% are removed. Conflicting decisions stop the export, unresolved matches are audited, and source CSVs cannot be selected as the output path.

## Supplied Data and Results

These counts describe the supplied artifacts only.

| Location | Contents |
|:---|:---|
| `data/global_comparison_results.csv` | 550 original form-event judgments. |
| `data/global_statistics_summary.json` | Supplied original comparison statistics. |
| `data/unified_human_judgments.csv` | Subsequent evaluation of 671 distinct events, including individual responses (700 form-event observations). |
| `data/unified_human_judgments.backup.csv` | Retained backup. |
| `results/form_results_v1/` | Original comparison tables, figures, and audits. |
| `results/form_results_v2/` | Shared tribunal summaries and the subsequent comparison under `unified/`. |

Per-form response CSVs, sampled-event JSONs, and Google credentials are local inputs and are not included. Generated datasets and tribunal logs remain under [Events results](../../experiments/events/results/README.md), including the supplied human-filtered dataset used by Objects. New runs do not need to reproduce any archive size or exclusion count.
