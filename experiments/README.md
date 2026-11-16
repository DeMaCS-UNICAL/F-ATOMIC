# Experiments

This folder owns generated datasets, validation outputs, and experiment results for Events and Objects.

| Folder | Description |
|:---|:---|
| [**events/**](events/README.md) | Event generation/validation outputs and additional Phi-4-mini workflows and model results. |
| [**objects/**](objects/README.md) | Entity extraction/classification results and generated context outputs. |

[`data/`](../data/README.md) contains source inputs and reference resources. The [human validation area](../human_validation/events/README.md) contains form creation, response processing, human-LLM analysis code, form data, and comparison reports. The resulting human-filtered event dataset remains under `events/results/`, where Objects reads it.
