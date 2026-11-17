import json
import subprocess
import sys
from pathlib import Path

import pytest

from evaluation import load_dataset
from evaluation.retrieval_experiment import run_retrieval_experiment
from knowledge import LocalKnowledgeBase


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "evaluation" / "datasets" / "health_mvp_v1.jsonl"


def test_retrieval_experiment_compares_same_frozen_cases():
    cases = load_dataset(DATASET)
    knowledge_base = LocalKnowledgeBase()

    report = run_retrieval_experiment(
        cases,
        knowledge_base.documents,
        dataset_name="health_mvp_v1",
    )

    assert report.candidate_count == 70
    assert report.relevant_case_count == 41
    assert report.no_hit_case_count == 29
    results = {result.strategy: result for result in report.strategies}
    assert results["keyword"].metrics["recall_at_k"] == pytest.approx(0.7886, abs=1e-4)
    assert results["bm25"].metrics["recall_at_k"] == pytest.approx(0.7642, abs=1e-4)
    assert (
        results["bm25"].metrics["no_hit_accuracy"]
        >= results["keyword"].metrics["no_hit_accuracy"]
    )
    assert "Keep `keyword`" in report.recommendation
    assert len(report.bm25_threshold_sweep) == 16
    assert "development-set threshold sweep" in report.to_markdown()
    assert "`minimum_score=6.5`" in report.to_markdown()


def test_retrieval_experiment_cli_writes_json_and_markdown(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_retrieval_experiment.py"),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads((tmp_path / "retrieval_experiment.json").read_text())
    markdown = (tmp_path / "retrieval_experiment.md").read_text()
    assert payload["candidate_count"] == 70
    assert "Compared 2 strategies" in completed.stdout
    assert "BM25 development-set threshold sweep" in markdown


def test_holdout_mode_does_not_sweep_bm25_thresholds():
    cases = load_dataset(DATASET)
    knowledge_base = LocalKnowledgeBase()

    report = run_retrieval_experiment(
        cases,
        knowledge_base.documents,
        dataset_name="sealed_holdout",
        include_bm25_threshold_sweep=False,
    )

    assert report.bm25_threshold_sweep == ()
    assert "development-set threshold sweep" not in report.to_markdown()
