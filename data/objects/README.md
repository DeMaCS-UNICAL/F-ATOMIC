# Objects Reference Data

## `en_conceptnet.json`

An additional supplied ConceptNet resource. Its contents are preserved; it is not read by the current extraction notebook, which uses spaCy and WordNet.

Entity tables, mention tables, physical classification, extraction counters, and generated contexts belong under [`experiments/objects/results/`](../../experiments/objects/results/README.md).

Object extraction reads the human-filtered event dataset from [`experiments/events/results/`](../../experiments/events/results/README.md), without creating another copy. See [`analysis/objects/`](../../analysis/objects/README.md) for the notebook and NLP prerequisites.
