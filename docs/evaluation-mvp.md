# Evaluation MVP

## Purpose

The Evaluation MVP establishes a reproducible baseline before changing the
agent architecture or retrieval strategy. The evaluation package is
domain-aware rather than health-specific: each case declares its `domain`,
`scenario`, checks, expected route, relevant evidence, and provenance. The
first dataset is the ClearCare health vertical.

This is an **exploratory component baseline**, not proof of clinical quality or
end-to-end product success.

## Dataset

`evaluation/datasets/health_mvp_v1.jsonl` contains 80 synthetic cases. Its
sidecar manifest records schema version, dataset version, label-freeze date,
review status, intended use, and prohibited interpretations.

| Scenario | Cases |
|---|---:|
| Emergency | 20 |
| Routine health information | 20 |
| Insufficient context | 10 |
| Out of scope | 10 |
| Adversarial / hard negative | 10 |
| Retrieval and citation | 10 |

Every record explicitly states that it contains no personal data. The labels
are project-reviewed, not clinician- or domain-expert-reviewed. Future datasets
can use the same schema with a different `domain` and evidence collection.

## Run

```bash
python scripts/run_evaluation.py
```

The command invokes no generative model and creates JSON plus Markdown reports
under `evaluation/reports/`.

## Baseline results — 2026-08-11

| Metric | Result |
|---|---:|
| Emergency recall | 1.0000 |
| Emergency precision | 0.8333 |
| Emergency false-positive rate | 0.0909 |
| Emergency category accuracy | 1.0000 |
| Retrieval Recall@3 | 0.6250 |
| Retrieval MRR | 0.6250 |
| Irrelevant-query no-hit accuracy | 1.0000 |
| Returned citation-ID validity | 1.0000 |

These results expose two useful product failures rather than hiding them:

1. Literal emergency keywords in quoted or meta-level text create five false
   positives. The current router needs context-aware hard-negative handling
   while preserving recall.
2. Keyword retrieval finds explicit in-corpus terms but misses all nine
   paraphrase/synonym retrieval cases. This gives RAG V2 a frozen baseline to
   beat.

Latency figures in the generated report cover only in-process rules and local
retrieval. They are not model or end-to-end latency.

## What is deliberately not measured yet

- Planner route accuracy
- Response groundedness or unsupported-claim rate
- End-to-end task success
- Model latency, token usage, or estimated cost
- Human usefulness or trust

Those metrics require captured provider outputs, clearer rubrics, and—where
appropriate—human or judge review. They remain `not measured` in the report
instead of being inferred from unit tests.

## Next increment

1. Add a provider-prediction JSONL contract without coupling the evaluator to a
   specific model vendor.
2. Capture planner decisions, returned evidence IDs, answer text, model calls,
   token usage, latency, and errors.
3. Add deterministic route, citation, prohibited-claim, and completion checks.
4. Add judge-based groundedness as a separately labelled experimental metric.
5. Expand from 80 to 150 cases only after expert review of the schema, labels,
   failure taxonomy, and current hard negatives.
