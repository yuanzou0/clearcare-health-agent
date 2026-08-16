#!/usr/bin/env python3
"""Perform the one permitted fixed-parameter holdout reveal and decision."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.holdout import (
    HoldoutProtocolError,
    decision_markdown,
    evaluate_promotion,
    file_sha256,
    verify_commitment,
)
from evaluation.retrieval_experiment import run_retrieval_experiment
from knowledge import LocalKnowledgeBase


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the one-time author-separated retrieval holdout."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--commitment", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "holdout" / "protocol_v1.json",
    )
    parser.add_argument(
        "--confirm-first-reveal",
        action="store_true",
        help="Confirm that this is the first and only evaluation of these labels.",
    )
    return parser


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = build_parser().parse_args()
    if not args.confirm_first_reveal:
        print("ERROR: --confirm-first-reveal is required")
        return 1
    if args.output_dir.exists():
        print("ERROR: output directory already exists; holdout reruns are prohibited")
        return 1
    for label, path in (("dataset", args.dataset), ("commitment", args.commitment)):
        if not path.is_file():
            print(f"ERROR: {label} file does not exist: {path}")
            return 1

    args.output_dir.mkdir(parents=True)
    started_at = datetime.now(UTC).isoformat()
    ledger_path = args.commitment.with_suffix(".reveal-ledger.json")
    ledger = {
        "schema_version": 1,
        "status": "first_reveal_reserved",
        "started_at": started_at,
        "commitment_sha256": file_sha256(args.commitment),
    }
    try:
        with ledger_path.open("x", encoding="utf-8") as file:
            json.dump(ledger, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except FileExistsError:
        print(
            "ERROR: reveal ledger already exists; this commitment has already "
            "been reserved or consumed"
        )
        return 1
    except OSError as exc:
        print(f"ERROR: cannot create reveal ledger beside commitment: {exc}")
        return 1

    reveal_record = {
        "schema_version": 1,
        "status": "reveal_verification_started",
        "started_at": started_at,
        "commitment_sha256": file_sha256(args.commitment),
        "revealed_dataset_sha256": file_sha256(args.dataset),
    }
    _write_json(args.output_dir / "reveal_record.json", reveal_record)
    knowledge_base = LocalKnowledgeBase()
    known_ids = {document.document_id for document in knowledge_base.documents}
    try:
        cases, protocol, commitment = verify_commitment(
            args.dataset,
            args.commitment,
            args.protocol,
            project=PROJECT_ROOT,
            known_document_ids=known_ids,
        )
    except (HoldoutProtocolError, OSError, ValueError) as exc:
        reveal_record["status"] = "reveal_validation_failed_consumed"
        reveal_record["completed_at"] = datetime.now(UTC).isoformat()
        reveal_record["error_type"] = type(exc).__name__
        _write_json(args.output_dir / "reveal_record.json", reveal_record)
        ledger.update(reveal_record)
        _write_json(ledger_path, ledger)
        print(
            "ERROR: revealed labels failed validation and are now consumed; "
            f"do not repair and rerun this set. Failure: {type(exc).__name__}: {exc}"
        )
        return 1

    reveal_record.update(
        {
            "protocol_id": protocol["protocol_id"],
            "status": "reveal_evaluation_started",
            "dataset_sha256": commitment["dataset_sha256"],
            "system_freeze_commit": commitment["system_freeze_commit"],
        }
    )
    _write_json(args.output_dir / "reveal_record.json", reveal_record)

    try:
        report = run_retrieval_experiment(
            cases,
            knowledge_base.documents,
            dataset_name=commitment["dataset_id"],
            strategies=("keyword", "bm25"),
            retrieval_k=protocol["experiment"]["retrieval_k"],
            include_bm25_threshold_sweep=False,
        )
        report.write(args.output_dir / "component_report")
        decision = evaluate_promotion(report, cases, protocol)
        _write_json(args.output_dir / "promotion_decision.json", decision)
        (args.output_dir / "promotion_decision.md").write_text(
            decision_markdown(decision), encoding="utf-8"
        )
    except Exception as exc:
        reveal_record["status"] = "reveal_failed_consumed"
        reveal_record["completed_at"] = datetime.now(UTC).isoformat()
        reveal_record["error_type"] = type(exc).__name__
        _write_json(args.output_dir / "reveal_record.json", reveal_record)
        ledger.update(reveal_record)
        _write_json(ledger_path, ledger)
        print(
            "ERROR: the holdout was revealed and is now consumed; do not rerun it. "
            f"Failure: {type(exc).__name__}: {exc}"
        )
        return 1

    reveal_record["status"] = "reveal_completed"
    reveal_record["completed_at"] = datetime.now(UTC).isoformat()
    reveal_record["decision"] = decision["decision"]
    _write_json(args.output_dir / "reveal_record.json", reveal_record)
    ledger.update(reveal_record)
    _write_json(ledger_path, ledger)
    print(f"Holdout decision: {decision['decision']}")
    print(f"Report directory: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
