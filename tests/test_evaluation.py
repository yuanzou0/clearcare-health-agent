import json
import subprocess
import sys
from pathlib import Path

import pytest

from evaluation import (
    EvaluationDatasetError,
    EvaluationHarness,
    load_dataset,
    validate_dataset_manifest,
)
from evaluation.schema import parse_case
from knowledge import KnowledgeDocument
from safety import SafetyAssessment


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "evaluation" / "datasets" / "health_mvp_v1.jsonl"


def valid_payload(**overrides):
    payload = {
        "case_id": "case-001",
        "domain": "test-domain",
        "scenario": "retrieval",
        "user_input": "find the governed record",
        "checks": ["safety", "retrieval"],
        "expected": {
            "route": "search_evidence",
            "emergency": False,
            "relevant_document_ids": ["doc-1"],
        },
        "tags": ["smoke"],
        "provenance": {
            "authoring_method": "synthetic",
            "reviewer_status": "project_reviewed",
            "contains_personal_data": False,
        },
    }
    payload.update(overrides)
    return payload


def test_health_mvp_dataset_is_versioned_privacy_safe_and_has_80_cases():
    cases = load_dataset(DATASET)
    manifest = validate_dataset_manifest(DATASET, cases)

    assert len(cases) == 80
    assert len({case.case_id for case in cases}) == 80
    assert all(not case.contains_personal_data for case in cases)
    assert manifest["dataset_version"] == "1.0.0"
    assert manifest["expert_reviewed"] is False
    assert {case.scenario for case in cases} == {
        "emergency",
        "routine_health",
        "insufficient_context",
        "out_of_scope",
        "adversarial",
        "retrieval_citation",
    }


def test_dataset_rejects_records_marked_as_containing_personal_data():
    payload = valid_payload()
    payload["provenance"]["contains_personal_data"] = True

    with pytest.raises(EvaluationDatasetError, match="personal_data"):
        parse_case(payload)


def test_dataset_loader_reports_duplicate_case_ids(tmp_path):
    dataset = tmp_path / "duplicate.jsonl"
    line = json.dumps(valid_payload())
    dataset.write_text(f"{line}\n{line}\n", encoding="utf-8")

    with pytest.raises(EvaluationDatasetError, match="duplicate case_id"):
        load_dataset(dataset)


def test_harness_calculates_safety_and_retrieval_metrics():
    class Router:
        def assess(self, text):
            return SafetyAssessment(text == "urgent", "test" if text == "urgent" else None)

    document = KnowledgeDocument(
        document_id="doc-1",
        title="Test",
        content="Content",
        source_url="https://example.test",
        keywords=("find",),
    )

    class KnowledgeBase:
        documents = (document,)

        def search(self, query, limit=3):
            return [document] if "find" in query else []

    emergency = valid_payload(
        case_id="urgent",
        user_input="urgent",
        checks=["safety"],
        expected={
            "route": "emergency",
            "emergency": True,
            "emergency_category": "test",
            "relevant_document_ids": [],
        },
    )
    retrieval = valid_payload(case_id="retrieval")
    cases = (parse_case(emergency), parse_case(retrieval))

    report = EvaluationHarness(Router(), KnowledgeBase()).run(cases, "test")

    assert report.metrics["emergency_recall"] == 1.0
    assert report.metrics["retrieval_recall_at_k"] == 1.0
    assert report.metrics["retrieval_mrr"] == 1.0
    assert report.metrics["citation_id_validity"] == 1.0
    assert report.metrics["planner_route_accuracy"] is None
    assert "not measured" in report.to_markdown()


def test_evaluation_cli_writes_json_and_markdown_reports(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_evaluation.py"),
            "--dataset",
            str(DATASET),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads((tmp_path / "health_mvp_v1.json").read_text())
    markdown = (tmp_path / "health_mvp_v1.md").read_text()
    assert payload["case_count"] == 80
    assert "Evaluated 80 cases" in completed.stdout
    assert "deterministic component baseline" in markdown
