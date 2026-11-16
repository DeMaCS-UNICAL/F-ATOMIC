# Source Data

This folder contains source knowledge and reference inputs for the two workflows.

| Folder | Description |
|:---|:---|
| **atomic_dataset/** | Original ATOMIC CSVs. |
| [**events/**](events/README.md) | Selected event inputs used by the generation pipeline and the 35 selected generation inputs for Phi4-mini. |
| [**objects/**](objects/README.md) | The supplied ConceptNet reference resource. |

Generated, cleaned, and validated event datasets belong under [`experiments/events/results/`](../experiments/events/results/README.md). Entity extraction/classification tables and object contexts belong under [`experiments/objects/results/`](../experiments/objects/results/README.md).

The [human validation area](../human_validation/events/README.md) contains form creation, human-analysis code, form data, and comparison reports. The human-filtered event dataset remains an Events result and is read directly by Objects.
