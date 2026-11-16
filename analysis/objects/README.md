# Objects Analysis

## `extract_objects.ipynb`

Extracts entity candidates from human-filtered forensic events and classifies their physical senses.

- **Input:** `experiments/events/results/forensic_atomic_final.csv` with 9,100 event annotations.
- **Processing:** Normalizes event placeholders, extracts candidates with spaCy, applies structural filters, and classifies physical senses using WordNet.
- **Tables:** Writes `event_entities.csv`, `event_entity_mentions.csv`, and `entity_classification.csv` under `experiments/objects/results/`.
- **Counters:** Writes `experiments/objects/results/extraction_funnel.json`.
- **Supplied results:** 1,066 distinct entities and 3,318 mentions.


### Requirements

Use a Python kernel providing pandas, **spaCy**, the **`en_core_web_sm`** model, **NLTK**, and the **WordNet** corpus. The extra NLP packages and resources are not bundled in the main Poetry environment. The notebook contains a WordNet download request during initialization when run.

The supplied `data/objects/en_conceptnet.json` is a separate resource and is not used by this notebook.

After extraction, use [`generate_contexts.py`](../../code/objects/README.md) to generate forensic contexts for the eligible entities. Context generation is separate from the extraction artifacts already present.
