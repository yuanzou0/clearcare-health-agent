#!/usr/bin/env python3
"""Run the versioned deterministic Evaluation MVP."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation import (
    EvaluationHarness,
    load_dataset,
    validate_dataset_manifest,
)
from knowledge import LocalKnowledgeBase
from safety import EmergencyRiskRouter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic safety and retrieval components."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "datasets" / "health_mvp_v1.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "reports",
    )
    parser.add_argument("--retrieval-k", type=int, default=3)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.retrieval_k < 1:
        raise SystemExit("--retrieval-k must be at least 1")
    cases = load_dataset(args.dataset)
    validate_dataset_manifest(args.dataset, cases)
    report = EvaluationHarness(
        EmergencyRiskRouter(), LocalKnowledgeBase(), args.retrieval_k
    ).run(cases, args.dataset.stem)
    json_path, markdown_path = report.write(args.output_dir)
    print(f"Evaluated {report.case_count} cases.")
    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
