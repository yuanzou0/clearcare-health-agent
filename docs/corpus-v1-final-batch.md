# Corpus v1 Final Batch: Child Health and Mental-Health Crisis

**Review date:** 2026-08-15

**Mechanical status:** passed and frozen

**Clinical review:** not performed

## Decision summary

The final batch adds five project-authored Chinese summaries: three for
`child_health` and two for `mental_health_crisis`. Together with the existing
WHO suicide-crisis record, the corpus now contains 24/24 governed records
across all eight planned clusters. Every cluster reaches its document target
and contains at least two approved sources.

This is a governance and retrieval milestone, not a clinical-validation claim.
All summaries remain `project_summary_unverified_by_clinician`, evidence grade
remains `not_assessed`, and source reuse remains `source-terms-apply`.

## Selected evidence

| Record | Canonical source | Captured metadata | Intended use | Boundary |
|---|---|---|---|---|
| `nmpa-child-cosmetics-safety-2026-08-review` | [NMPA: consumer notice about children's cosmetics](https://www.nmpa.gov.cn/xxgk/kpzhsh/kpzhshhzhp/20260428093808135.html) | Canonical page reviewed 2026-08-15; publication metadata left `null` because automated access returned HTTP 412 | Meaning of the “Little Golden Shield,” regular-channel purchasing, supervised use, trial use, and misuse prevention | Product safety only; no diagnosis or treatment |
| `who-child-mortality-warning-signs-2026-08-review` | [WHO: Child mortality under 5 years](https://www.who.int/news-room/fact-sheets/detail/child-mortality-under-5-years) | Published 2026-05-01; project reviewed 2026-08-15 | Caregiver recognition of feeding difficulty, reduced activity, breathing difficulty, fever, convulsions, or feeling cold | Risk recognition and help-seeking only; no cause inference or treatment |
| `nhs-baby-toddler-serious-illness-2026-08-review` | [NHS: Is your baby or toddler seriously ill?](https://www.nhs.uk/baby/health/is-your-baby-or-toddler-seriously-ill/) | Page last reviewed 2023-08-24; project reviewed 2026-08-15 | Caregiver recognition of serious-illness and dehydration signals | NHS 111/999/A&E are UK-specific; other jurisdictions use local services |
| `who-depression-crisis-guidance-2026-08-review` | [WHO: Depressive disorder (depression)](https://www.who.int/news-room/fact-sheets/detail/depression) | Published 2025-08-29; project reviewed 2026-08-15 | Recognition of depression-related crisis signals and immediate help-seeking | General information only; no self-diagnosis or treatment selection |
| `nhs-urgent-mental-health-support-2026-08-review` | [NHS: Urgent support](https://www.nhs.uk/every-mind-matters/urgent-support/) | Current page captured 2026-08-15 | Immediate-danger escalation and urgent support for new hallucinations or delusions | UK contact channels are not generalized to other jurisdictions |

The NMPA host returned HTTP 412 during automated review. The selected page's
content was cross-checked through an [official Shanghai regulator
reproduction](https://yjj.sh.gov.cn/yzaq/20260430/2b4563c182eb4c81a0b2a2181c47e5ef.html).
The corpus keeps the canonical NMPA URL and explicitly records the access
limitation in the release manifest.

## Review of additional supplied and discovered links

| Page | Decision | Reason |
|---|---|---|
| [NMPA policy page dated 2026-07-15](https://www.nmpa.gov.cn/zhuanti/zt2025/shenhua/shzcwj/20260715143331192.html) | Quarantine; do not ingest | HTTP 412 prevented direct inspection, exact title/metadata could not be independently verified, and the policy-document path is outside the patient-facing runtime scope |
| [NMPA policy page dated 2026-03-30](https://www.nmpa.gov.cn/zhuanti/zt2025/shenhua/shzcwj/20260330104043134.html) | Quarantine; do not ingest | Same verification and product-scope limitations as above |
| [WHO Child health portal](https://www.who.int/health-topics/child-health#tab=tab_1) | Discovery only | Useful index, but too broad to become one evidence record |
| WHO child-health Q&A URL discovered during review | Reject | Returned 404; a broken page cannot be a governed runtime source |
| [WHO Mental health portal](https://www.who.int/health-topics/mental-health#tab=tab_1) | Discovery only | Useful index; concrete guidance pages were selected instead |

Exclusion is a product-scope and auditability decision, not a claim that the
issuing organization is unreliable.

## Frozen release contract

[`knowledge/corpus_release_v1.json`](../knowledge/corpus_release_v1.json)
records the release date, document count, reviewer/evidence status, exact
evaluation split, SHA-256 hashes for the corpus and governance artifacts, and
known gaps. The checked-in curation validator now rejects a frozen corpus when
the release manifest is missing, paths escape the project, metadata disagrees,
or any recorded artifact hash changes.

## Evaluation impact

Five source-specific retrieval cases were added, advancing the synthetic,
project-reviewed development set from 90 cases / `1.5.0` to 95 cases /
`1.6.0`. The three older general crisis-support labels were expanded to name
all three relevant governed crisis records. Historical provider runs remain
attached to their original dataset versions.

The final 24-document component replay makes no model or API calls:

| Strategy | Recall@3 | MRR | No-hit accuracy |
|---|---:|---:|---:|
| Keyword | 78.86% | 78.05% | 89.66% |
| BM25 (`minimum_score=6.5`) | 76.42% | 78.05% | 89.66% |

Keyword remains the production default. BM25 does not improve recall at the
development-selected threshold and surfaces a different set of false hits.
These are development-set component results, not blind-holdout, answer-quality,
groundedness, or clinical-performance estimates. See the generated
[final retrieval report](../evaluation/reports/corpus-v1-final/retrieval_experiment.md).

---

# 中文摘要：Corpus v1 最终批次

最终批次新增 5 条项目自编中文摘要：儿童健康 3 条，心理健康危机 2 条。加上已有的
WHO 自杀危机记录后，`health_corpus_v1` 达到 24/24 条；8 个主题群全部达到文档数
目标，并且每个主题至少包含两个获准来源。

这次“冻结”只表示语料版本、来源、哈希和评测切分均可复现，不表示临床验证。
全部摘要仍标记为未经临床人员审核，证据等级仍为 `not_assessed`。

开发集从 90 条 / `1.5.0` 升级到 95 条 / `1.6.0`。24 文档组件回放中，Keyword 的
Recall@3 为 78.86%，BM25 为 76.42%；两者 No-hit Accuracy 均为 89.66%。因此
Keyword 继续作为默认检索，下一阶段进入作者隔离的盲测 Holdout，而不是继续在同一
开发集上调参。
