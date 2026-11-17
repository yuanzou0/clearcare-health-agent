#!/usr/bin/env python3
"""Create the hash-only commitment shared before holdout labels are revealed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.holdout import HoldoutProtocolError, create_commitment
from knowledge import LocalKnowledgeBase


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an independently authored holdout and emit only its "
            "pre-reveal hash commitment. Run this in the author's isolated workspace."
        )
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--author-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "holdout" / "protocol_v1.json",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        known_ids = {
            document.document_id for document in LocalKnowledgeBase().documents
        }
        commitment = create_commitment(
            args.dataset,
            args.protocol,
            project=PROJECT_ROOT,
            author_id=args.author_id,
            known_document_ids=known_ids,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            json.dump(commitment, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except (HoldoutProtocolError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Commitment created: {args.output}")
    print("Share only this commitment before reveal; retain dataset and labels privately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
