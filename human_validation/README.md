# Human Validation

This area owns the human-evaluation workflow: creating forms, processing responses, comparing human and LLM judgments, and storing form inputs and reports.

The [Events workflow](events/README.md) contains all currently supplied human-evaluation code and results.

The Events scripts and notebooks also support new evaluations: input CSVs, form labels, LLM logs, and report destinations are configurable. The documented archive sizes describe the supplied files; they are not execution requirements. See the workflow README for the required CSV columns and CLI examples.

The resulting human-filtered event dataset is kept with the other [Events results](../experiments/events/results/README.md).
