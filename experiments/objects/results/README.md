# Objects Results

These artifacts are derived from [`forensic_atomic_final.csv`](../../events/results/forensic_atomic_final.csv).

| File | Contents |
|:---|:---|
| `event_entities.csv` | 1,066 distinct entities with mention counts, example events, and governing verbs. |
| `event_entity_mentions.csv` | 3,318 extracted mentions with event and parsing information. |
| `entity_classification.csv` | The 1,066 entities enriched with WordNet-based physical labels and supporting statistics. |
| `extraction_funnel.json` | Counters for 9,100 input rows, 4,648 unique input events, 3,318 kept mentions, and 1,066 entities. |

The classification labels are `yes`, `maybe`, and `no`. The generation command selects `yes`/`maybe` entities and excludes its prompt example entity.

## Generated Contexts

[`generate_contexts.py`](../../../code/objects/README.md) writes its JSONL checkpoint and CSV export here when given the corresponding output prefix. Those generated files are not supplied; extraction candidates are not a completed or validated object-context dataset.

The extraction notebook is documented in [`analysis/objects/`](../../../analysis/objects/README.md). The additional ConceptNet resource remains under `data/objects/` and is not used by that notebook.
