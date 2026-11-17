# Author-Separated Blind Holdout Protocol

**Status:** preregistered; awaiting an independent author

**Protocol:** `clearcare_retrieval_holdout_v1`

**System under test:** commit `a460ddd`, frozen `health_corpus_v1`, Keyword
baseline, and BM25 candidate with `minimum_score=6.5`, `k1=1.5`, `b=0.75`

## Why this exists

The existing 95-case set is a development set. It has already influenced
corpus selection, BM25 threshold choice, test expectations, and product
decisions. Reusing it to claim generalization would introduce confirmation,
measurement, and reporting bias.

This protocol separates three roles:

1. **System developer:** freezes the corpus, retrieval code, parameters,
   metrics, and promotion gates before seeing holdout prompts or labels.
2. **Holdout author:** writes synthetic cases in an isolated workspace, runs
   structural validation, and shares only a hash commitment.
3. **Reveal operator:** receives the sealed dataset only after the system and
   commitment are frozen, verifies hashes, and performs one fixed-parameter run.

If one person performs all three roles, the result must be called a fresh
development split—not an author-separated blind holdout.

## Preregistered design

The machine-readable contract is
[`evaluation/holdout/protocol_v1.json`](../evaluation/holdout/protocol_v1.json).
It fixes the design before label collection:

- 64 synthetic, non-personal retrieval cases;
- 40 positive cases: 5 for each of the 8 frozen topic clusters;
- 24 expected no-hit cases;
- at least 8 cases tagged for each of paraphrase, synonym, hard negative, and
  jurisdiction difference; tags may overlap;
- one retrieval query and fixed `K=3` for both strategies;
- no BM25 threshold sweep and no parameter changes after reveal;
- no rerun on the same labels after success or failure.

The holdout isolates retrieval. It does not test emergency routing, generated
answer quality, claim groundedness, clinical safety, or user usefulness.

## Promotion rule

BM25 is promoted only if **every** gate passes:

| Gate | Preregistered requirement |
|---|---:|
| Macro Recall@3 improvement | at least +0.03 absolute |
| Paired bootstrap 95% CI lower bound for Recall@3 delta | greater than 0 |
| No-hit accuracy delta | no worse than -0.02 |
| Hard-negative accuracy delta | no worse than -0.05 |
| Worst per-cluster Recall@3 delta | no worse than -0.20 |

MRR and latency remain secondary/descriptive. Passing the table supports a
retrieval-default decision only; it does not support a clinical-performance
claim. If any gate fails, Keyword remains the default. Unexpected findings may
generate a new hypothesis, but validating that hypothesis requires a new
independently authored holdout.

## Independent-author workflow

The author must use a clean checkout at the frozen system commit and must not
inspect the 95-case development dataset, historical case-level reports, or
retriever outputs while writing labels.

1. Copy
   [`holdout_v1.meta.template.json`](../evaluation/holdout/holdout_v1.meta.template.json)
   next to a private `holdout_v1.jsonl` as `holdout_v1.meta.json`.
2. Author all 64 cases using the existing JSONL case schema. Every record must
   declare:
   - `checks: ["retrieval"]`;
   - non-emergency `search_evidence` route;
   - `authoring_method: "author_separated_synthetic"`;
   - `contains_personal_data: false`;
   - exactly one frozen topic-cluster tag for positive cases.
3. Run the commitment creator **inside the author's isolated workspace**:

   ```bash
   python scripts/create_holdout_commitment.py \
     --dataset /private/path/holdout_v1.jsonl \
     --author-id reviewer-a \
     --output /private/path/holdout_v1.commitment.json
   ```

4. Share only `holdout_v1.commitment.json`. Keep prompts, labels, dataset
   metadata, and author notes private.
5. The developer records the commitment hash and confirms there will be no
   further corpus, retrieval, threshold, or gate changes.
6. The author then transfers the unchanged JSONL and metadata for the first
   reveal.

The author ID should be non-identifying. No real patient text, records, or
personal data may be used.

## One-time reveal

The reveal operator runs:

```bash
python scripts/run_blind_holdout.py \
  --dataset /sealed/path/holdout_v1.jsonl \
  --commitment /sealed/path/holdout_v1.commitment.json \
  --output-dir evaluation/reports/holdout-v1-first-reveal \
  --confirm-first-reveal
```

The runner creates an exclusive `holdout_v1.reveal-ledger.json` beside the
commitment, then verifies the protocol, frozen corpus and retrieval-code hashes,
dataset/metadata hashes,
case composition, source IDs, cluster balance, and query-phenomenon counts. It
refuses an existing reveal ledger or output directory, disables threshold
sweeps, and writes a
`reveal_record.json` before evaluation. A runtime failure after reveal consumes
the holdout and is recorded as such; it is not permission to tune and retry.

After reveal, publish the dataset as a **retired holdout** if reuse and privacy
checks allow. It may support reproducibility but cannot be used again as an
unseen confirmatory set.

## Validity and limitations

- Author separation reduces developer confirmation bias but does not make the
  labels clinically expert-reviewed.
- Forty positive cases offer useful paired evidence for a portfolio experiment,
  not a precise population estimate; the paired confidence interval is reported
  to make uncertainty visible.
- Synthetic prompts reduce privacy risk but may not represent real-world query
  distribution, language, prevalence, or severity.
- Cluster quotas support coverage and failure inspection but are not population
  weights; the primary recall is a designed-sample metric.
- A public repository cannot keep committed labels blind. Only the commitment,
  templates, protocol, and tools belong in Git before first reveal.

---

# 中文摘要：作者隔离盲测协议

当前 95 条案例已经参与过语料选择和 BM25 阈值调整，因此只能继续作为开发集，不能
再作为无偏测试集。本协议把系统开发者、Holdout 作者和揭盲执行者分开：开发者先
冻结代码、语料、参数、指标与晋级门槛；独立作者在隔离环境编写 64 条合成案例，只
提前交付哈希承诺；系统冻结后再一次性移交原始案例并揭盲。

盲测包含 40 条正例和 24 条 No-hit，每个主题群 5 条正例，并覆盖 Paraphrase、
Synonym、Hard Negative 和地区差异。BM25 只有在 Recall@3 提升至少 3 个百分点、
配对 Bootstrap 95% CI 下界大于 0，并同时通过 No-hit、Hard Negative 和主题分群
护栏时才能晋级。任何门槛失败都继续使用 Keyword。

目前已经完成协议、模板、哈希承诺工具、一次性揭盲 Runner 和回归测试；尚未创建或
查看真正的 Holdout 案例。下一步必须由另一位作者完成密封数据包。若由本项目开发者
自己写案例，只能称为新开发集，不能称为“作者隔离盲测”。
