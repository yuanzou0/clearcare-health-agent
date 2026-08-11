"""Deterministic safety and retrieval evaluation harness."""

from __future__ import annotations

import json
import math
import statistics
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .schema import EvaluationCase


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    domain: str
    scenario: str
    expected_route: str
    predicted_emergency: bool | None
    predicted_emergency_category: str | None
    expected_emergency: bool
    expected_emergency_category: str | None
    returned_document_ids: tuple[str, ...]
    relevant_document_ids: tuple[str, ...]
    safety_latency_ms: float | None
    retrieval_latency_ms: float | None
    error: str | None = None


@dataclass(frozen=True)
class EvaluationReport:
    dataset_name: str
    generated_at: str
    case_count: int
    scenario_counts: dict[str, int]
    metrics: dict[str, float | int | None]
    limitations: tuple[str, ...]
    case_results: tuple[CaseResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "generated_at": self.generated_at,
            "case_count": self.case_count,
            "scenario_counts": self.scenario_counts,
            "metrics": self.metrics,
            "limitations": list(self.limitations),
            "case_results": [asdict(result) for result in self.case_results],
        }

    def to_markdown(self) -> str:
        def display(value: float | int | None) -> str:
            if value is None:
                return "not measured"
            if isinstance(value, float):
                return f"{value:.4f}"
            return str(value)

        metric_labels = {
            "emergency_recall": "Emergency recall",
            "emergency_precision": "Emergency precision",
            "emergency_false_positive_rate": "Emergency false-positive rate",
            "emergency_category_accuracy": "Emergency category accuracy",
            "retrieval_recall_at_k": "Retrieval Recall@K",
            "retrieval_mrr": "Retrieval MRR",
            "retrieval_no_hit_accuracy": "Irrelevant-query no-hit accuracy",
            "citation_id_validity": "Returned citation-ID validity",
            "safety_p95_latency_ms": "Safety P95 latency (ms)",
            "retrieval_p95_latency_ms": "Retrieval P95 latency (ms)",
            "case_error_count": "Case errors",
            "planner_route_accuracy": "Planner route accuracy",
            "groundedness": "Groundedness",
            "task_success_rate": "Task success rate",
            "estimated_cost": "Estimated model cost",
        }
        lines = [
            f"# Evaluation report: {self.dataset_name}",
            "",
            f"- Generated: {self.generated_at}",
            f"- Cases: {self.case_count}",
            "- Evaluation mode: deterministic component baseline",
            "",
            "## Scenario coverage",
            "",
            "| Scenario | Cases |",
            "|---|---:|",
        ]
        lines.extend(
            f"| {scenario} | {count} |"
            for scenario, count in sorted(self.scenario_counts.items())
        )
        lines.extend(["", "## Metrics", "", "| Metric | Value |", "|---|---:|"])
        lines.extend(
            f"| {metric_labels.get(key, key)} | {display(value)} |"
            for key, value in self.metrics.items()
        )
        lines.extend(["", "## Limitations", ""])
        lines.extend(f"- {limitation}" for limitation in self.limitations)

        failures = [
            result
            for result in self.case_results
            if result.error
            or (
                result.predicted_emergency is not None
                and result.predicted_emergency != result.expected_emergency
            )
            or (
                result.relevant_document_ids
                and not set(result.relevant_document_ids).intersection(
                    result.returned_document_ids
                )
            )
        ]
        lines.extend(["", "## Failure sample", ""])
        if not failures:
            lines.append("No component-level failures in this run.")
        else:
            lines.extend(
                f"- `{result.case_id}` ({result.scenario}): "
                f"expected route `{result.expected_route}`, "
                f"emergency={result.predicted_emergency}, "
                f"documents={list(result.returned_document_ids)}"
                for result in failures[:20]
            )
        return "\n".join(lines) + "\n"

    def write(self, output_directory: str | Path) -> tuple[Path, Path]:
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        json_path = output / f"{self.dataset_name}.json"
        markdown_path = output / f"{self.dataset_name}.md"
        json_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(self.to_markdown(), encoding="utf-8")
        return json_path, markdown_path


def _safe_ratio(numerator: int | float, denominator: int | float) -> float | None:
    return numerator / denominator if denominator else None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


class EvaluationHarness:
    """Evaluate deterministic components without invoking a generative model."""

    def __init__(self, safety_router: Any, knowledge_base: Any, retrieval_k: int = 3):
        self.safety_router = safety_router
        self.knowledge_base = knowledge_base
        self.retrieval_k = retrieval_k
        self.known_document_ids = {
            document.document_id for document in knowledge_base.documents
        }

    def evaluate_case(self, case: EvaluationCase) -> CaseResult:
        predicted_emergency: bool | None = None
        predicted_category: str | None = None
        returned_ids: tuple[str, ...] = ()
        safety_latency: float | None = None
        retrieval_latency: float | None = None
        error: str | None = None
        try:
            if "safety" in case.checks:
                started = time.perf_counter()
                assessment = self.safety_router.assess(case.user_input)
                safety_latency = (time.perf_counter() - started) * 1000
                predicted_emergency = assessment.is_emergency
                predicted_category = assessment.category

            if "retrieval" in case.checks and predicted_emergency is not True:
                started = time.perf_counter()
                documents = self.knowledge_base.search(
                    case.user_input, limit=self.retrieval_k
                )
                retrieval_latency = (time.perf_counter() - started) * 1000
                returned_ids = tuple(document.document_id for document in documents)
        except Exception as exc:  # keep one bad case from hiding the full report
            error = f"{type(exc).__name__}: {exc}"

        return CaseResult(
            case_id=case.case_id,
            domain=case.domain,
            scenario=case.scenario,
            expected_route=case.expected_route,
            predicted_emergency=predicted_emergency,
            predicted_emergency_category=predicted_category,
            expected_emergency=case.expected_emergency,
            expected_emergency_category=case.expected_emergency_category,
            returned_document_ids=returned_ids,
            relevant_document_ids=case.relevant_document_ids,
            safety_latency_ms=safety_latency,
            retrieval_latency_ms=retrieval_latency,
            error=error,
        )

    def run(
        self, cases: tuple[EvaluationCase, ...], dataset_name: str
    ) -> EvaluationReport:
        results = tuple(self.evaluate_case(case) for case in cases)
        metrics = self._calculate_metrics(cases, results)
        return EvaluationReport(
            dataset_name=dataset_name,
            generated_at=datetime.now(UTC).isoformat(),
            case_count=len(cases),
            scenario_counts=dict(sorted(Counter(case.scenario for case in cases).items())),
            metrics=metrics,
            limitations=(
                "Cases are synthetic and project-reviewed, not clinically or domain-expert validated.",
                "This baseline evaluates deterministic safety routing and local retrieval only.",
                "Planner route accuracy, response groundedness, task success, and model cost require provider predictions and are not measured here.",
                "The current evidence corpus contains three project-authored health summaries, so retrieval coverage is intentionally narrow.",
            ),
            case_results=results,
        )

    def _calculate_metrics(
        self,
        cases: tuple[EvaluationCase, ...],
        results: tuple[CaseResult, ...],
    ) -> dict[str, float | int | None]:
        by_id = {case.case_id: case for case in cases}
        safety_results = [
            result
            for result in results
            if "safety" in by_id[result.case_id].checks
            and result.predicted_emergency is not None
        ]
        true_positive = sum(
            result.expected_emergency and result.predicted_emergency
            for result in safety_results
        )
        false_positive = sum(
            not result.expected_emergency and result.predicted_emergency
            for result in safety_results
        )
        false_negative = sum(
            result.expected_emergency and not result.predicted_emergency
            for result in safety_results
        )
        true_negative = sum(
            not result.expected_emergency and not result.predicted_emergency
            for result in safety_results
        )
        category_candidates = [
            result
            for result in safety_results
            if result.expected_emergency and result.predicted_emergency
        ]
        category_correct = sum(
            result.predicted_emergency_category
            == result.expected_emergency_category
            for result in category_candidates
        )

        retrieval_results = [
            result
            for result in results
            if "retrieval" in by_id[result.case_id].checks
            and result.retrieval_latency_ms is not None
        ]
        relevant_results = [
            result for result in retrieval_results if result.relevant_document_ids
        ]
        empty_results = [
            result for result in retrieval_results if not result.relevant_document_ids
        ]
        recalls: list[float] = []
        reciprocal_ranks: list[float] = []
        for result in relevant_results:
            relevant = set(result.relevant_document_ids)
            returned = list(result.returned_document_ids)
            recalls.append(len(relevant.intersection(returned)) / len(relevant))
            ranks = [
                index + 1 for index, document_id in enumerate(returned)
                if document_id in relevant
            ]
            reciprocal_ranks.append(1 / min(ranks) if ranks else 0.0)

        returned_id_count = sum(
            len(result.returned_document_ids) for result in retrieval_results
        )
        valid_id_count = sum(
            document_id in self.known_document_ids
            for result in retrieval_results
            for document_id in result.returned_document_ids
        )
        no_hit_correct = sum(not result.returned_document_ids for result in empty_results)

        return {
            "emergency_recall": _safe_ratio(
                true_positive, true_positive + false_negative
            ),
            "emergency_precision": _safe_ratio(
                true_positive, true_positive + false_positive
            ),
            "emergency_false_positive_rate": _safe_ratio(
                false_positive, false_positive + true_negative
            ),
            "emergency_category_accuracy": _safe_ratio(
                category_correct, len(category_candidates)
            ),
            "retrieval_recall_at_k": statistics.fmean(recalls) if recalls else None,
            "retrieval_mrr": (
                statistics.fmean(reciprocal_ranks) if reciprocal_ranks else None
            ),
            "retrieval_no_hit_accuracy": _safe_ratio(
                no_hit_correct, len(empty_results)
            ),
            "citation_id_validity": _safe_ratio(valid_id_count, returned_id_count),
            "safety_p95_latency_ms": _percentile(
                [
                    result.safety_latency_ms
                    for result in safety_results
                    if result.safety_latency_ms is not None
                ],
                0.95,
            ),
            "retrieval_p95_latency_ms": _percentile(
                [
                    result.retrieval_latency_ms
                    for result in retrieval_results
                    if result.retrieval_latency_ms is not None
                ],
                0.95,
            ),
            "case_error_count": sum(result.error is not None for result in results),
            "planner_route_accuracy": None,
            "groundedness": None,
            "task_success_rate": None,
            "estimated_cost": None,
        }
