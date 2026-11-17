"""One-time, author-separated retrieval holdout contracts and decision gates."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from .retrieval_experiment import RetrievalExperimentReport
from .schema import EvaluationCase, load_dataset, validate_dataset_manifest


class HoldoutProtocolError(ValueError):
    """Raised when a holdout package violates its preregistered contract."""


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_object(path: str | Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HoldoutProtocolError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise HoldoutProtocolError(f"{label} must be a JSON object")
    return value


def _project_path(project: Path, relative_path: object, label: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise HoldoutProtocolError(f"{label} must be a non-empty relative path")
    root = project.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HoldoutProtocolError(f"{label} escapes the project root") from exc
    if not candidate.is_file():
        raise HoldoutProtocolError(f"{label} does not exist: {candidate}")
    return candidate


def load_protocol(
    protocol_path: str | Path,
    *,
    project: str | Path,
) -> dict[str, Any]:
    """Load a preregistered protocol and verify the frozen system artifacts."""
    protocol = _load_object(protocol_path, "holdout protocol")
    if protocol.get("schema_version") != 1:
        raise HoldoutProtocolError("unsupported holdout protocol schema_version")
    if protocol.get("status") != "preregistered":
        raise HoldoutProtocolError("holdout protocol status must be preregistered")
    if not isinstance(protocol.get("protocol_id"), str):
        raise HoldoutProtocolError("holdout protocol requires protocol_id")
    experiment = protocol.get("experiment")
    requirements = protocol.get("dataset_requirements")
    gates = protocol.get("promotion_gates")
    corpus = protocol.get("corpus")
    system_artifacts = protocol.get("system_artifacts")
    if not all(
        isinstance(value, dict)
        for value in (experiment, requirements, gates, corpus, system_artifacts)
    ):
        raise HoldoutProtocolError(
            "protocol requires frozen system/corpus artifacts, dataset requirements, "
            "experiment, and promotion gates"
        )
    if experiment.get("threshold_sweep_allowed") is not False:
        raise HoldoutProtocolError("blind holdout must prohibit threshold sweeps")
    if experiment.get("rerun_after_reveal_allowed") is not False:
        raise HoldoutProtocolError("blind holdout must prohibit reruns after reveal")
    if experiment.get("baseline", {}).get("strategy") != "keyword":
        raise HoldoutProtocolError("preregistered baseline must be keyword")
    if experiment.get("candidate", {}).get("strategy") != "bm25":
        raise HoldoutProtocolError("preregistered candidate must be bm25")

    root = Path(project)
    for name, path_field, hash_field in (
        ("corpus release", "release_manifest_path", "release_manifest_sha256"),
        ("corpus", "corpus_path", "corpus_sha256"),
    ):
        artifact = _project_path(root, corpus.get(path_field), name)
        if file_sha256(artifact) != corpus.get(hash_field):
            raise HoldoutProtocolError(f"{name} hash does not match preregistration")
    retrieval = _project_path(
        root, system_artifacts.get("retrieval_path"), "retrieval implementation"
    )
    if file_sha256(retrieval) != system_artifacts.get("retrieval_sha256"):
        raise HoldoutProtocolError(
            "retrieval implementation hash does not match preregistration"
        )
    return protocol


def validate_author_dataset(
    dataset_path: str | Path,
    protocol: dict[str, Any],
    *,
    known_document_ids: Iterable[str] | None = None,
) -> tuple[tuple[EvaluationCase, ...], dict[str, Any]]:
    """Validate the sealed author package without evaluating a retriever."""
    cases = load_dataset(dataset_path)
    metadata = validate_dataset_manifest(dataset_path, cases)
    requirements = protocol["dataset_requirements"]
    expected_count = requirements["case_count"]
    if len(cases) != expected_count:
        raise HoldoutProtocolError(
            f"holdout requires exactly {expected_count} cases; received {len(cases)}"
        )
    expected_metadata = {
        "split_type": "author_separated_blind_holdout",
        "author_separated": True,
        "labels_exposure": "sealed_until_system_freeze",
        "contains_personal_data": False,
    }
    for field, expected in expected_metadata.items():
        if metadata.get(field) != expected:
            raise HoldoutProtocolError(
                f"holdout metadata {field} must be {expected!r}"
            )

    prompts = [" ".join(case.user_input.split()).casefold() for case in cases]
    duplicates = sorted(prompt for prompt, count in Counter(prompts).items() if count > 1)
    if duplicates:
        raise HoldoutProtocolError("holdout contains duplicate normalized prompts")
    if any(
        case.domain != "health"
        or "retrieval" not in case.checks
        or case.expected_emergency
        or case.expected_route != "search_evidence"
        for case in cases
    ):
        raise HoldoutProtocolError(
            "holdout cases must isolate non-emergency health retrieval"
        )
    if any(case.authoring_method != "author_separated_synthetic" for case in cases):
        raise HoldoutProtocolError(
            "every holdout case must declare author_separated_synthetic"
        )

    positive = tuple(case for case in cases if case.relevant_document_ids)
    no_hit = tuple(case for case in cases if not case.relevant_document_ids)
    if len(positive) != requirements["positive_case_count"]:
        raise HoldoutProtocolError("positive-case count violates preregistration")
    if len(no_hit) != requirements["no_hit_case_count"]:
        raise HoldoutProtocolError("no-hit case count violates preregistration")

    known_ids = set(known_document_ids or ())
    if known_ids:
        unknown_ids = sorted(
            {
                document_id
                for case in positive
                for document_id in case.relevant_document_ids
                if document_id not in known_ids
            }
        )
        if unknown_ids:
            raise HoldoutProtocolError(
                "holdout references unknown governed documents: "
                + ", ".join(unknown_ids)
            )

    clusters = set(requirements["topic_clusters"])
    cluster_counts: Counter[str] = Counter()
    for case in positive:
        tagged_clusters = clusters.intersection(case.tags)
        if len(tagged_clusters) != 1:
            raise HoldoutProtocolError(
                f"positive case {case.case_id} must declare exactly one topic cluster tag"
            )
        cluster_counts.update(tagged_clusters)
    minimum_cluster = requirements["minimum_positive_cases_per_cluster"]
    below_target = sorted(
        cluster for cluster in clusters if cluster_counts[cluster] < minimum_cluster
    )
    if below_target:
        raise HoldoutProtocolError(
            "holdout topic clusters below preregistered minimum: "
            + ", ".join(below_target)
        )

    tag_counts = Counter(tag for case in cases for tag in case.tags)
    missing_tags = sorted(
        tag
        for tag, minimum in requirements["minimum_tag_counts"].items()
        if tag_counts[tag] < minimum
    )
    if missing_tags:
        raise HoldoutProtocolError(
            "holdout query phenomena below preregistered minimum: "
            + ", ".join(missing_tags)
        )
    return cases, metadata


def create_commitment(
    dataset_path: str | Path,
    protocol_path: str | Path,
    *,
    project: str | Path,
    author_id: str,
    known_document_ids: Iterable[str] | None = None,
    committed_at: str | None = None,
) -> dict[str, Any]:
    """Create the hash-only artifact shared before labels are revealed."""
    if not author_id.strip():
        raise HoldoutProtocolError("author_id must be non-empty and non-identifying")
    protocol = load_protocol(protocol_path, project=project)
    cases, metadata = validate_author_dataset(
        dataset_path,
        protocol,
        known_document_ids=known_document_ids,
    )
    dataset = Path(dataset_path)
    metadata_path = dataset.with_suffix(".meta.json")
    return {
        "schema_version": 1,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": file_sha256(protocol_path),
        "dataset_id": metadata["dataset_id"],
        "dataset_version": metadata["dataset_version"],
        "case_count": len(cases),
        "dataset_sha256": file_sha256(dataset),
        "metadata_sha256": file_sha256(metadata_path),
        "committed_at": committed_at or datetime.now(UTC).isoformat(),
        "author_id": author_id.strip(),
        "author_separated": True,
        "labels_exposed_to_developer": False,
        "system_freeze_commit": protocol["system_freeze_commit"],
    }


def verify_commitment(
    dataset_path: str | Path,
    commitment_path: str | Path,
    protocol_path: str | Path,
    *,
    project: str | Path,
    known_document_ids: Iterable[str] | None = None,
) -> tuple[tuple[EvaluationCase, ...], dict[str, Any], dict[str, Any]]:
    """Verify that revealed labels exactly match the pre-reveal commitment."""
    protocol = load_protocol(protocol_path, project=project)
    cases, metadata = validate_author_dataset(
        dataset_path,
        protocol,
        known_document_ids=known_document_ids,
    )
    commitment = _load_object(commitment_path, "holdout commitment")
    expected = {
        "schema_version": 1,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": file_sha256(protocol_path),
        "dataset_id": metadata["dataset_id"],
        "dataset_version": metadata["dataset_version"],
        "case_count": len(cases),
        "dataset_sha256": file_sha256(dataset_path),
        "metadata_sha256": file_sha256(Path(dataset_path).with_suffix(".meta.json")),
        "author_separated": True,
        "labels_exposed_to_developer": False,
        "system_freeze_commit": protocol["system_freeze_commit"],
    }
    for field, expected_value in expected.items():
        if commitment.get(field) != expected_value:
            raise HoldoutProtocolError(
                f"holdout commitment mismatch for {field}"
            )
    for field in ("committed_at", "author_id"):
        if not isinstance(commitment.get(field), str) or not commitment[field].strip():
            raise HoldoutProtocolError(f"holdout commitment requires {field}")
    try:
        datetime.fromisoformat(commitment["committed_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise HoldoutProtocolError("commitment committed_at must be ISO-8601") from exc
    return cases, protocol, commitment


def _case_recall(relevant: Sequence[str], returned: Sequence[str]) -> float:
    return len(set(relevant).intersection(returned)) / len(relevant)


def _paired_bootstrap_interval(
    baseline: Sequence[float],
    candidate: Sequence[float],
    *,
    confidence: float,
    resamples: int,
    seed: int,
) -> tuple[float, float]:
    if not baseline or len(baseline) != len(candidate):
        raise HoldoutProtocolError("paired bootstrap requires aligned positive cases")
    generator = random.Random(seed)
    deltas: list[float] = []
    for _ in range(resamples):
        indices = [generator.randrange(len(baseline)) for _ in baseline]
        deltas.append(
            sum(candidate[index] - baseline[index] for index in indices)
            / len(indices)
        )
    deltas.sort()
    tail = (1.0 - confidence) / 2.0
    lower_index = max(0, math.floor(tail * resamples))
    upper_index = min(resamples - 1, math.ceil((1.0 - tail) * resamples) - 1)
    return deltas[lower_index], deltas[upper_index]


def evaluate_promotion(
    report: RetrievalExperimentReport,
    cases: Sequence[EvaluationCase],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    """Apply only the preregistered fixed-parameter promotion gates."""
    experiment = protocol["experiment"]
    baseline_name = experiment["baseline"]["strategy"]
    candidate_name = experiment["candidate"]["strategy"]
    results = {result.strategy: result for result in report.strategies}
    if set(results) != {baseline_name, candidate_name}:
        raise HoldoutProtocolError("holdout report strategies differ from protocol")
    if report.bm25_threshold_sweep:
        raise HoldoutProtocolError("holdout report contains a prohibited threshold sweep")

    case_lookup = {case.case_id: case for case in cases}
    result_lookup = {
        strategy: {result.case_id: result for result in strategy_result.case_results}
        for strategy, strategy_result in results.items()
    }
    positive = [case for case in cases if case.relevant_document_ids]
    no_hit = [case for case in cases if not case.relevant_document_ids]
    baseline_recalls = [
        _case_recall(
            case.relevant_document_ids,
            result_lookup[baseline_name][case.case_id].returned_document_ids,
        )
        for case in positive
    ]
    candidate_recalls = [
        _case_recall(
            case.relevant_document_ids,
            result_lookup[candidate_name][case.case_id].returned_document_ids,
        )
        for case in positive
    ]
    recall_delta = sum(candidate_recalls) / len(candidate_recalls) - sum(
        baseline_recalls
    ) / len(baseline_recalls)
    gates = protocol["promotion_gates"]
    ci_lower, ci_upper = _paired_bootstrap_interval(
        baseline_recalls,
        candidate_recalls,
        confidence=gates["bootstrap_confidence"],
        resamples=gates["bootstrap_resamples"],
        seed=gates["bootstrap_seed"],
    )

    def no_hit_accuracy(strategy: str, cohort: Sequence[EvaluationCase]) -> float:
        return sum(
            not result_lookup[strategy][case.case_id].returned_document_ids
            for case in cohort
        ) / len(cohort)

    baseline_no_hit = no_hit_accuracy(baseline_name, no_hit)
    candidate_no_hit = no_hit_accuracy(candidate_name, no_hit)
    hard_negatives = [case for case in no_hit if "hard_negative" in case.tags]
    baseline_hard_negative = no_hit_accuracy(baseline_name, hard_negatives)
    candidate_hard_negative = no_hit_accuracy(candidate_name, hard_negatives)

    cluster_deltas: dict[str, float] = {}
    for cluster in protocol["dataset_requirements"]["topic_clusters"]:
        indices = [index for index, case in enumerate(positive) if cluster in case.tags]
        cluster_deltas[cluster] = sum(
            candidate_recalls[index] - baseline_recalls[index] for index in indices
        ) / len(indices)
    worst_cluster_delta = min(cluster_deltas.values())
    gate_results = {
        "recall_delta": recall_delta >= gates["minimum_recall_at_3_delta"],
        "paired_bootstrap_ci_lower": (
            ci_lower > gates["minimum_paired_bootstrap_ci_lower"]
        ),
        "no_hit_accuracy_delta": (
            candidate_no_hit - baseline_no_hit
            >= gates["minimum_no_hit_accuracy_delta"]
        ),
        "hard_negative_accuracy_delta": (
            candidate_hard_negative - baseline_hard_negative
            >= gates["minimum_hard_negative_accuracy_delta"]
        ),
        "cluster_recall_floor": (
            worst_cluster_delta >= gates["minimum_cluster_recall_delta"]
        ),
    }
    promote = all(gate_results.values())
    return {
        "protocol_id": protocol["protocol_id"],
        "decision": "promote_bm25" if promote else "keep_keyword",
        "all_gates_passed": promote,
        "metrics": {
            "baseline_recall_at_3": results[baseline_name].metrics["recall_at_k"],
            "candidate_recall_at_3": results[candidate_name].metrics["recall_at_k"],
            "recall_at_3_delta": recall_delta,
            "recall_delta_paired_bootstrap_ci": [ci_lower, ci_upper],
            "baseline_no_hit_accuracy": baseline_no_hit,
            "candidate_no_hit_accuracy": candidate_no_hit,
            "no_hit_accuracy_delta": candidate_no_hit - baseline_no_hit,
            "baseline_hard_negative_accuracy": baseline_hard_negative,
            "candidate_hard_negative_accuracy": candidate_hard_negative,
            "hard_negative_accuracy_delta": (
                candidate_hard_negative - baseline_hard_negative
            ),
            "cluster_recall_deltas": cluster_deltas,
            "worst_cluster_recall_delta": worst_cluster_delta,
        },
        "gates": gate_results,
        "case_count": len(case_lookup),
    }


def decision_markdown(decision: dict[str, Any]) -> str:
    metrics = decision["metrics"]
    lines = [
        "# Author-separated blind holdout decision",
        "",
        f"- Protocol: `{decision['protocol_id']}`",
        f"- Cases: {decision['case_count']}",
        f"- Decision: **{decision['decision']}**",
        f"- All gates passed: {decision['all_gates_passed']}",
        "",
        "## Primary and guardrail metrics",
        "",
        f"- Recall@3 delta: {metrics['recall_at_3_delta']:.4f}",
        "- Paired bootstrap CI: "
        f"[{metrics['recall_delta_paired_bootstrap_ci'][0]:.4f}, "
        f"{metrics['recall_delta_paired_bootstrap_ci'][1]:.4f}]",
        f"- No-hit accuracy delta: {metrics['no_hit_accuracy_delta']:.4f}",
        "- Hard-negative accuracy delta: "
        f"{metrics['hard_negative_accuracy_delta']:.4f}",
        "- Worst cluster Recall@3 delta: "
        f"{metrics['worst_cluster_recall_delta']:.4f}",
        "",
        "## Gate results",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} — `{name}`"
        for name, passed in decision["gates"].items()
    )
    lines.extend(
        [
            "",
            "This is a one-time component holdout decision. It does not measure "
            "answer groundedness, clinical safety, or end-to-end model quality.",
        ]
    )
    return "\n".join(lines) + "\n"
