# Source Code

This folder contains the reusable infrastructure and the two forensic knowledge workflows.

| Module | Description |
|:---|:---|
| [**core/**](core/README.md) | LLM facade, provider adapters, response metadata, and logging. |
| [**config/**](config/README.md) | Provider settings, event panel configuration, and repository-relative paths. |
| [**events/**](events/README.md) | ATOMIC event selection, forensic prompts, validation, and evaluation. |
| [**objects/**](objects/README.md) | Entity-based prompts and forensic object-context generation. |

Operational scripts configure their source import path automatically.

Human form creation and comparison code is collected under [`human_validation/events/`](../human_validation/events/README.md), alongside its data and reports.
