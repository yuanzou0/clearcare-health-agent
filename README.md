# Governed Agent Lab

[English](README.md) | [简体中文](README.zh-CN.md)

An engineering and product portfolio for building **bounded, measurable, and
governed AI agents**. The repository combines an allow-listed agent runtime,
governed evidence, provider-neutral evaluation, failure analysis, and reusable
Codex Skills.

**ClearCare Health / 澄心循证健康智能体 is the first implemented reference
vertical—not the platform identity.** The current web experience, safety router,
evidence corpus, and measured results remain health-specific. A reusable domain
adapter and a second vertical are roadmap items, not completed features.

> [!WARNING]
> The health demo is for research and education only. It does not diagnose,
> prescribe, or replace a clinician. Do not enter real patient identifiers,
> contact details, or other sensitive information.

## What is implemented

| Layer | Current state |
|---|---|
| Bounded agent runtime | Implemented: one plan/tool/respond cycle, allow-listed action/reason pairs, one read-only tool call |
| Governed evidence | Implemented for ClearCare: approved-source registry, provenance, review dates, URL-host binding, freshness and SHA-256 checks |
| Evaluation | Implemented: deterministic and provider-neutral cases, privacy-safe predictions, failure taxonomy, Keyword/BM25 comparison |
| Model providers | Implemented: local Qwen default, optional OpenAI, quarantined legacy GPT-2 baseline |
| Web demo | Implemented for local/single-process use with conversation memory, agent trace, citations, CSRF and abuse controls |
| Cross-domain adapter | Planned; health-specific prompts, safety policy, corpus schema, and UI have not yet been extracted |
| Production multi-user service | Not supported; authentication, distributed rate limiting, encrypted persistence, observability, and compliance controls are absent |

## Architecture

```text
Governed Agent Lab
├── Platform core
│   ├── bounded planner / tool / responder runtime
│   ├── provider-neutral prediction and evaluation contract
│   ├── governed-source validation and retrieval experiments
│   └── security and privacy guardrails
├── ClearCare Health reference vertical
│   ├── emergency routing and clarification policy
│   ├── project-authored health evidence summaries
│   └── local web demo and measured development cases
├── Developer workflows
│   └── curate-health-evidence Codex Skill
└── Legacy baseline
    └── original GPT-2 training/inference code and separately prepared data
```

For a non-emergency ClearCare request, the planner selects exactly one
allow-listed route: ask for essential clarification, search governed evidence,
or respond without a tool. Strong emergency signals are routed to fixed
guidance before any model or rate limit is invoked. The trace exposes actions
and result counts, never hidden chain-of-thought.

## Measured evidence, not benchmark theatre

The committed results are engineering regression measurements on a small,
project-reviewed **health development set**. They are neither independent
benchmarks nor clinical-performance claims.

| Measurement | Keyword baseline | BM25 candidate |
|---|---:|---:|
| Local-Qwen task-success proxy | 72.5% | 78.75% |
| Retrieval Recall@3 | 62.5% | 75.0% |
| Emergency recall | 100% | 100% |
| Citation-ID validity | 100% | 100% |

BM25 remains a candidate because selection and measurement used the same
development set. Promotion requires an independent holdout and regression
gate. See [Evaluation v1](docs/evaluation-v1.md),
[RAG V2](docs/rag-v2-experiment.md), and the
[Evaluation MVP](docs/evaluation-mvp.md).

## Quick start

Python 3.10+ is required. Deterministic tests and evaluation do not download a
model or make paid API calls.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

python scripts/validate_knowledge.py
pytest
python scripts/run_evaluation.py
```

### Run the local Qwen demo

On Apple Silicon, the default MLX configuration uses a quantized Qwen model.
The first run downloads weights and requires sufficient memory.

```bash
python -m pip install -e '.[inference]'
export GOVERNED_AGENT_MODEL_PROVIDER="qwen-local"
export GOVERNED_AGENT_QWEN_MODEL="mlx-community/Qwen3-4B-Instruct-2507-4bit"
export GOVERNED_AGENT_QWEN_REVISION="50d427756c6b1b2fe0c0a10f67fbda1fc8e82c1b"
flask --app app run
```

Open <http://127.0.0.1:5000>. Enter only new information in follow-ups; the
application supplies the latest bounded conversation context. Select **Start a
new consultation** to clear it.

### Optional OpenAI comparison

OpenAI API usage is billed separately from ChatGPT subscriptions. The default
hosted model is the documented [`gpt-5.6-terra`](https://developers.openai.com/api/docs/models/gpt-5.6-terra).
Cloud use is disabled until the server enables it and the user selects it for
that request.

```bash
python -m pip install -e '.[openai]'
export OPENAI_API_KEY="your_api_key"
export GOVERNED_AGENT_OPENAI_MODEL="gpt-5.6-terra"
export GOVERNED_AGENT_CLOUD_ENHANCEMENT_ENABLED=true
flask --app app run
```

API requests set `store=False`, but that alone is not a zero-data-retention or
compliance guarantee. Never commit keys or submit sensitive health data.

## Security and deployment boundary

The local demo now includes CSRF protection, a 16 KiB request limit,
single-process rate limiting, secure cookie defaults, restrictive response
headers, non-persistent conversations, evidence-source binding, bounded input
and corpus sizes, and generic error persistence. Production mode fails closed
without a durable 32+ character secret and secure cookies.

```bash
export GOVERNED_AGENT_DEPLOYMENT_MODE=production
export GOVERNED_AGENT_SECRET_KEY="replace-with-a-random-secret-of-at-least-32-characters"
export GOVERNED_AGENT_SESSION_COOKIE_SECURE=true
```

These controls do **not** make the Flask development server internet-ready.
There is no user authentication, authorization, distributed rate limiter,
encrypted persistent session store, WAF, audit service, or healthcare
compliance certification. Put a production server and reverse proxy in front
only after those controls are designed. See the
[security and risk review](docs/security-and-risk-review.md) and
[SECURITY.md](SECURITY.md).

## Governed evidence and data provenance

`knowledge/medical_guidance.json` contains three project-authored Chinese
summaries linked to CDC, NHS, and WHO pages. They are marked as **not
clinician-reviewed** and must not be represented as validated clinical advice.
`knowledge/source_manifest.json` defines approved issuers, domains, reuse
status, jurisdiction, and review policy. Runtime loading rejects unknown or
impersonated sources, stale reviews, future dates, unsafe URLs, duplicate IDs,
oversized records, and content/hash mismatches.

Adding more documents does not automatically improve reliability. New material
should be added only through a defined coverage gap, governed-source review,
holdout evaluation, and release gate. The included
[`curate-health-evidence`](skills/curate-health-evidence/) Skill automates the
deterministic parts of that workflow; it does not perform clinical review.

## Legacy GPT-2 boundary

The original GPT-2 code is retained as a historical CLI/training baseline and
is not exposed as a web provider or used by the default runtime/evaluation.
Generated Pickle datasets and Python bytecode are no longer tracked. Dataset
loading accepts only bounded lists of integer token IDs and rejects Pickle
globals/classes; checkpoint loading is local-only and Safetensors-only.

The raw legacy text and generated Pickles were removed from the current tree
because their provenance, de-identification quality, and redistribution rights
could not be established. Repository history or upstream snapshots may still
retain earlier artifacts. Supply your own lawfully obtained, de-identified data
outside the repository and prepare it explicitly:

```bash
python -m pip install -e '.[training]'
python data_preprocess/preprocess.py --input /path/to/train.txt --output local_data/train.pkl
python data_preprocess/preprocess.py --input /path/to/valid.txt --output local_data/valid.pkl
```

Raw conversation sample logging is disabled by default. Do not enable it for
real personal or health information.

## Repository map

```text
app.py, web_security.py          Web orchestration and request controls
agent_runtime.py                 Bounded plan/tool/respond runtime
chat_models.py                   Qwen and OpenAI web providers
conversation.py                 Bounded in-memory context
safety.py                        ClearCare emergency routing
knowledge.py, retrieval.py       Governed corpus validation and retrieval
evaluation/, scripts/            Cases, capture, reports, and release checks
skills/curate-health-evidence/   Installable developer-facing Codex Skill
docs/                            Product, evaluation, RAG, brand, and risk records
data_preprocess/, train.py       Quarantined legacy GPT-2 workflow
tests/                           Automated regression and security tests
```

## Product and engineering documents

- [Product case study](docs/product-case-study.md)
- [Portfolio upgrade roadmap](docs/portfolio-upgrade-roadmap.md)
- [Brand architecture](docs/brand-architecture.md)
- [Evaluation MVP](docs/evaluation-mvp.md) and [Evaluation v1](docs/evaluation-v1.md)
- [RAG V2 experiment](docs/rag-v2-experiment.md)
- [Security and risk review](docs/security-and-risk-review.md)

## Roadmap

1. Freeze an independently reviewed holdout and add release regression gates.
2. Add an evaluation dashboard with cohort, failure, latency, and cost slices.
3. Extract a versioned domain adapter interface for policy, corpus, metrics, and UI.
4. Prove that interface with a lower-risk second vertical before claiming a
   general-purpose platform.
5. Add authentication, durable privacy controls, observability, and deployment
   hardening only if an external multi-user product becomes a real goal.

## License and reuse warning

The upstream project does not declare an open-source license, and the provenance
and reuse rights of the legacy training data are unresolved. Do not assume the
code or data may be redistributed or used commercially without explicit
permission. This repository's technical cleanup does not cure that legal risk.
