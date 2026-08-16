# ClearCare Health Portfolio Upgrade Roadmap

Last updated: 2026-08-15

ClearCare Health is a vertical, evidence-backed product case for three related
roles:

- **AI Product Manager:** problem framing, risk decisions, user journey,
  prioritization, guardrail metrics, and trade-offs;
- **Data Analyst:** evaluation design, metric definitions, paired experiments,
  dashboards, and failure segmentation;
- **Applied AI / LLM Application Engineer:** bounded orchestration, governed
  RAG, provider integration, security controls, and reproducible evaluation.

The goal is not to maximize feature count or present one vertical as a generic
platform. The goal is to show a coherent evidence chain: **what user problem is
bounded, what was built, how it was measured, where it fails, and which product
decision follows from the result.**

## Status legend

- [x] Implemented and verified
- [ ] Not yet complete

## Phase 0 — Current closeout

- [x] Merge Corpus v1 Batch 3 into `main`.
- [x] Synchronize the local `main` branch with `fork/main`.
- [x] Re-run 94 tests plus corpus validation and coverage checks on merged
  `main`.
- [x] Reconcile current README, roadmap, and evaluation figures while
  preserving versioned historical snapshots.

## Current foundation

- [x] Establish ClearCare Health as the repository and product identity.
- [x] Describe reusable runtime/evaluation code as internal domain-extensible
  architecture, not a validated horizontal platform.
- [x] Publish an explicit “implemented / inherited / removed” ownership boundary.
- [x] Use local Qwen by default and make OpenAI an explicit per-request option.
- [x] Route strong emergency signals deterministically before model generation.
- [x] Bound the agent to one allow-listed plan/tool/respond cycle and one
  read-only tool call.
- [x] Maintain bounded multi-turn context and a visible reset action.
- [x] Separate generated answers, source links, and inspectable action traces.
- [x] Govern evidence records with source metadata, approved domains, review
  status, content hashes, and freshness rules.
- [x] Ship the installable `curate-health-evidence` developer Skill.
- [x] Remove raw legacy datasets and generated artifacts from the current tree.
- [x] Publish the product case study, security review, Evaluation MVP/v1, and
  Keyword/BM25 experiment.
- [x] Pass 107 automated regression and security tests as of 2026-08-16.

## P0 — Corpus v1 before further retrieval architecture

### 1. Coverage specification

- [x] Define 6–8 health-information topic clusters and explicit inclusion/
  exclusion boundaries.
- [x] Create a coverage matrix for ordinary information, warning signs,
  clarification needs, paraphrases, synonyms, no-hit cases, hard negatives,
  and jurisdiction differences.
- [x] Define approved issuer/domain and reuse requirements before collecting
  content.
- [x] Keep project-authored summaries separate from clinical review and
  evidence grading.

Coverage design is now versioned in
[`knowledge/coverage_plan.json`](../knowledge/coverage_plan.json) and explained
in the bilingual
[`Health Corpus v1 Coverage Specification`](corpus-v1-coverage-spec.md). The
live report now shows 24/24 records, 8/8 clusters at target, and a frozen
release contract with exact hashes. This is a reproducibility milestone, not a
clinical-validation claim.

### 2. Governed corpus expansion

- [x] Expand from 19 summaries to 24 governed documents against named coverage
  gaps and source-diversity requirements.
- [x] Add stable document IDs, applicability,
  version, review owner/status, and content hashes.
- [x] Run the evidence Skill, corpus validation, coverage report, duplicate
  detection, and stale-review checks.
- [x] Freeze `health_corpus_v1` with artifact hashes, the exact development
  split, known gaps, and a release date.

**Definition of done:** each document fills a named coverage gap, passes
governance validation, has traceable reuse metadata, and belongs to a frozen
corpus version. Document count alone is not a quality claim.

## P0 — Author-separated blind holdout

### 3. Evaluation protocol

- [x] Define the versioned, privacy-safe development schema and 80-case MVP.
- [x] Implement deterministic safety/retrieval checks and provider-neutral
  prediction capture.
- [x] Capture a complete local-Qwen development run and segmented report.
- [x] Pre-register retrieval promotion metrics and guardrail thresholds.
- [ ] Ask a separate author/reviewer to create or review unseen cases; if that
  is not possible, call the process “author-separated blind holdout,” not fully
  independent evaluation.
- [ ] Receive the independently authored holdout commitment, then freeze its
  input/label hashes and reviewer status before first reveal. The commitment,
  one-time runner, and reveal policy are implemented.
- [x] Prevent parameter changes and threshold sweeps in the holdout runner;
  any post-reveal retuning requires a new independently authored test set.

### 4. Paired Keyword/BM25 replay

- [x] Freeze the development-selected BM25 threshold at 6.5; holdout tuning is
  prohibited.
- [x] Run the exact same frozen retrieval queries for both strategies so
  planner randomness cannot masquerade as a retrieval gain.
- [ ] Compare Recall@3, MRR, no-hit accuracy, citation coverage, latency, and
  failure segments on the blind holdout.
- [ ] Promote BM25 only if it passes pre-registered quality and safety gates.

**Historical end-to-end result (dataset v1.0.0):** BM25 improved the development
proxy from 72.5% to 78.75%, but Keyword remains the default because the result
has not passed a blind holdout.

The frozen 24-document component replay keeps the previously selected BM25
development threshold of 6.5. Keyword achieved 78.86% Recall@3 and BM25
76.42%; both achieved 89.66% no-hit accuracy. Keyword therefore remains the
default. This does not complete the paired blind-holdout task.

## P0 — Claim-level groundedness

### 5. Human-reviewed sample

- [ ] Define an atomic claim annotation guide:
  `supported / partially supported / unsupported / not verifiable`.
- [ ] Sample 20–30 answers across safety routes, retrieval outcomes, providers,
  and known failure cohorts.
- [ ] Label citation entailment: does the cited material support the associated
  claim?
- [ ] Label claim groundedness and calculate unsupported-claim rate.
- [ ] Label human usefulness separately from factual support.
- [ ] Require zero unsupported safety-critical claims in the reviewed release
  sample.

### 6. Secondary LLM judge

- [ ] Add an LLM judge only after the human rubric and anchor examples exist.
- [ ] Measure agreement with human labels and report disagreements by failure
  type.
- [ ] Never use the judge as the sole medical-safety or release gate.

**Definition of done:** the report distinguishes valid IDs, citation
entailment, claim groundedness, unsupported-claim rate, and usefulness instead
of collapsing them into one proxy.

## P1 — Product analytics and dashboard

- [ ] Define privacy-safe events: consultation started, route selected,
  clarification requested, source opened, answer completed, reset selected,
  and provider error; never log raw health text by default.
- [ ] Define the North Star as **safe, evidence-supported task completion** and
  publish its operational proxy and limitations.
- [ ] Build a local dashboard with scenario, model, retrieval, and failure
  filters plus latency/cost slices.
- [ ] Show guardrail metrics beside task-success metrics so aggregate quality
  cannot hide safety regressions.

**Definition of done:** a recruiter can identify the largest failure cohort and
trace a product decision back to measured evidence in under two minutes.

## P1 — Skills and recruiter demonstration

- [ ] Add a before/after evidence Skill demo: candidate source, metadata check,
  dry run, SHA-256, corpus update, validation, and coverage report.
- [ ] Record sanitized terminal output or a short walkthrough.
- [ ] Create `evaluate-health-agent` only after holdout and report contracts are
  stable.
- [ ] Make the evaluation Skill run a selected dataset, classify failures,
  calculate metrics, compare with a baseline, and produce a release report.

We will not add a separate audit Skill until release auditing has distinct
inputs, owners, or compliance gates.

## P2 — Demo and deployment

- [x] Provide a professional local web demo with multi-turn memory, source
  links, safety routing, and an inspectable trace.
- [ ] Add a development-only evaluation view; keep it separate from the
  user-facing health experience.
- [ ] Add an architecture diagram, screenshots, and a 60–90 second walkthrough.
- [ ] Containerize with a production WSGI server only if public deployment is
  still a portfolio goal.
- [ ] Before public access, add authentication/access policy, distributed abuse
  controls, redacted observability, retention policy, and synthetic prompts.

## P2 — Provenance and clean-room decision

- [x] Identify inherited GPT-2 code and remove unneeded legacy data/artifacts.
- [x] State that upstream has no declared open-source license and do not present
  inherited work as original.
- [ ] Request explicit permission from the upstream author, including the scope
  of code allowed for modification and redistribution.
- [ ] If permission is unavailable, build a clean-room ClearCare repository
  from product/behavioral specifications without copying unlicensed code.
- [ ] Add a license only to code/content that the repository owner has the
  right to license.

## Six-week working timeline

| Dates | Milestone | Deliverable / acceptance signal |
|---|---|---|
| Aug 14–20 | Brand, ownership, corpus design | Vertical-first README, ownership boundary, coverage specification |
| Aug 21–Sep 3 | Governed corpus v1 | ~~24 governed records, coverage report, frozen manifest/hash~~ Completed 2026-08-15 |
| Sep 4–10 | Blind holdout | Frozen unseen cases, preregistered gates, paired Keyword/BM25 replay |
| Sep 11–17 | Groundedness | Human-reviewed claims, entailment and unsupported-claim report |
| Sep 18–24 | Analytics | Evaluation dashboard and segmented product recommendation |
| Sep 25–30 | Portfolio packaging | Skill demo, walkthrough, role-specific resume bullets, clean-room decision |

## Product decisions to preserve

- Keep emergency routing deterministic: generative variability is not justified
  for the narrow strong-signal route.
- Keep autonomy bounded: more loops and tools add failure surfaces without a
  measured user benefit.
- Keep citations separate from generated prose so provenance stays inspectable.
- Keep local-first inference as the default for privacy, cost, and offline
  reproducibility; measure it rather than calling it universally superior.
- Keep project-authored summaries explicitly separate from clinical review.

## Explicit non-goals

- Diagnosing users, choosing treatment, prescribing medication, or replacing
  clinicians
- Claiming medical-device status, clinical validation, or regulatory compliance
- Collecting real patient data for training or evaluation
- Adding Embedding, a vector database, autonomous write tools, multi-agent
  complexity, or streaming solely to make the architecture look advanced
- Claiming a horizontal platform before a second domain proves the abstractions
