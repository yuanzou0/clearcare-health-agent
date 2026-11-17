import json
from pathlib import Path

import pytest

from evaluation.holdout import (
    HoldoutProtocolError,
    create_commitment,
    evaluate_promotion,
    file_sha256,
    load_protocol,
    verify_commitment,
)
from evaluation.retrieval_experiment import run_retrieval_experiment
from evaluation.schema import load_dataset
from knowledge import KnowledgeDocument


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_preregistered_protocol_matches_frozen_artifacts():
    protocol = load_protocol(
        PROJECT_ROOT / "evaluation" / "holdout" / "protocol_v1.json",
        project=PROJECT_ROOT,
    )

    assert protocol["system_freeze_commit"] == "a460ddd"
    assert protocol["experiment"]["threshold_sweep_allowed"] is False


def write_protocol(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    knowledge = project / "knowledge"
    knowledge.mkdir(parents=True)
    release = knowledge / "release.json"
    corpus = knowledge / "corpus.json"
    retrieval = project / "retrieval.py"
    release.write_text("{}\n", encoding="utf-8")
    corpus.write_text("[]\n", encoding="utf-8")
    retrieval.write_text("# frozen retrieval\n", encoding="utf-8")
    protocol = {
        "schema_version": 1,
        "protocol_id": "test_holdout_v1",
        "status": "preregistered",
        "system_freeze_commit": "abc1234",
        "system_artifacts": {
            "retrieval_path": "retrieval.py",
            "retrieval_sha256": file_sha256(retrieval),
        },
        "corpus": {
            "release_manifest_path": "knowledge/release.json",
            "release_manifest_sha256": file_sha256(release),
            "corpus_path": "knowledge/corpus.json",
            "corpus_sha256": file_sha256(corpus),
        },
        "dataset_requirements": {
            "case_count": 2,
            "positive_case_count": 1,
            "no_hit_case_count": 1,
            "minimum_positive_cases_per_cluster": 1,
            "topic_clusters": ["test_cluster"],
            "minimum_tag_counts": {"hard_negative": 1},
        },
        "experiment": {
            "retrieval_k": 3,
            "baseline": {"strategy": "keyword", "parameters": {}},
            "candidate": {
                "strategy": "bm25",
                "parameters": {"minimum_score": 6.5, "k1": 1.5, "b": 0.75},
            },
            "threshold_sweep_allowed": False,
            "rerun_after_reveal_allowed": False,
        },
        "promotion_gates": {
            "minimum_recall_at_3_delta": 0.03,
            "minimum_paired_bootstrap_ci_lower": 0.0,
            "minimum_no_hit_accuracy_delta": -0.02,
            "minimum_hard_negative_accuracy_delta": -0.05,
            "minimum_cluster_recall_delta": -0.2,
            "bootstrap_confidence": 0.95,
            "bootstrap_resamples": 100,
            "bootstrap_seed": 7,
        },
    }
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    return project, protocol_path


def write_dataset(tmp_path: Path, *, authoring_method="author_separated_synthetic"):
    dataset = tmp_path / "holdout.jsonl"
    provenance = {
        "authoring_method": authoring_method,
        "reviewer_status": "project_reviewed",
        "contains_personal_data": False,
    }
    cases = [
        {
            "case_id": "positive-001",
            "domain": "health",
            "scenario": "retrieval_citation",
            "user_input": "胸痛资料",
            "checks": ["retrieval"],
            "expected": {
                "route": "search_evidence",
                "emergency": False,
                "relevant_document_ids": ["doc-1"],
            },
            "tags": ["test_cluster"],
            "provenance": provenance,
        },
        {
            "case_id": "no-hit-001",
            "domain": "health",
            "scenario": "retrieval_citation",
            "user_input": "Python 单元测试",
            "checks": ["retrieval"],
            "expected": {
                "route": "search_evidence",
                "emergency": False,
                "relevant_document_ids": [],
            },
            "tags": ["hard_negative"],
            "provenance": provenance,
        },
    ]
    dataset.write_text(
        "\n".join(json.dumps(case, ensure_ascii=False) for case in cases) + "\n",
        encoding="utf-8",
    )
    metadata = {
        "schema_version": 1,
        "dataset_id": "test_holdout",
        "dataset_version": "1.0.0",
        "case_count": 2,
        "contains_personal_data": False,
        "split_type": "author_separated_blind_holdout",
        "author_separated": True,
        "labels_exposure": "sealed_until_system_freeze",
    }
    dataset.with_suffix(".meta.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    return dataset


def test_commitment_verifies_exact_sealed_dataset_without_exposing_prompts(tmp_path):
    project, protocol_path = write_protocol(tmp_path)
    dataset = write_dataset(tmp_path)

    commitment = create_commitment(
        dataset,
        protocol_path,
        project=project,
        author_id="reviewer-a",
        known_document_ids={"doc-1"},
        committed_at="2026-08-16T00:00:00+00:00",
    )
    commitment_path = tmp_path / "commitment.json"
    commitment_path.write_text(json.dumps(commitment), encoding="utf-8")
    cases, protocol, verified = verify_commitment(
        dataset,
        commitment_path,
        protocol_path,
        project=project,
        known_document_ids={"doc-1"},
    )

    assert len(cases) == 2
    assert protocol["protocol_id"] == "test_holdout_v1"
    assert verified["labels_exposed_to_developer"] is False
    assert "胸痛" not in json.dumps(commitment, ensure_ascii=False)


def test_commitment_rejects_any_post_commitment_label_change(tmp_path):
    project, protocol_path = write_protocol(tmp_path)
    dataset = write_dataset(tmp_path)
    commitment = create_commitment(
        dataset,
        protocol_path,
        project=project,
        author_id="reviewer-a",
        known_document_ids={"doc-1"},
    )
    commitment_path = tmp_path / "commitment.json"
    commitment_path.write_text(json.dumps(commitment), encoding="utf-8")
    dataset.write_text(
        dataset.read_text(encoding="utf-8").replace("胸痛资料", "胸闷资料"),
        encoding="utf-8",
    )

    with pytest.raises(HoldoutProtocolError, match="dataset_sha256"):
        verify_commitment(
            dataset,
            commitment_path,
            protocol_path,
            project=project,
            known_document_ids={"doc-1"},
        )


def test_holdout_rejects_cases_authored_by_the_system_developer(tmp_path):
    project, protocol_path = write_protocol(tmp_path)
    dataset = write_dataset(tmp_path, authoring_method="synthetic")

    with pytest.raises(HoldoutProtocolError, match="author_separated_synthetic"):
        create_commitment(
            dataset,
            protocol_path,
            project=project,
            author_id="reviewer-a",
            known_document_ids={"doc-1"},
        )


def test_fixed_parameter_holdout_applies_all_promotion_gates(tmp_path):
    project, protocol_path = write_protocol(tmp_path)
    dataset = write_dataset(tmp_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    cases = load_dataset(dataset)
    document = KnowledgeDocument(
        document_id="doc-1",
        title="胸痛资料",
        content="胸痛信息",
        source_url="https://example.test/doc-1",
        keywords=("胸痛",),
    )
    report = run_retrieval_experiment(
        cases,
        (document,),
        dataset_name="test_holdout",
        include_bm25_threshold_sweep=False,
    )

    decision = evaluate_promotion(report, cases, protocol)

    assert report.bm25_threshold_sweep == ()
    assert decision["decision"] == "keep_keyword"
    assert decision["all_gates_passed"] is False
