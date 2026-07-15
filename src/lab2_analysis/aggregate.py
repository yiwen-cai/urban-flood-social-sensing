"""Lab 2 aggregation compatibility wrapper.

D07 metrics/evidence are owned exclusively by
``src.lab3_decision.build_evidence``. This module keeps the historical
``python -m src.lab2_analysis.aggregate`` entrypoint and re-exports helpers
used by older unit tests.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from src.lab3_decision.build_evidence import (
    DEFAULT_EVIDENCE,
    DEFAULT_METRICS,
    DEFAULT_POSTS,
    DEFAULT_PREDICTIONS,
    build_d07,
    compute_metrics as compute_d07_metrics,
    extract_evidence,
    load_jsonl,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = DEFAULT_POSTS


def load_records(path: str | Path) -> list[dict[str, Any]]:
    return load_jsonl(Path(path))


def compute_distribution(
    records: list[dict[str, Any]],
    field: str,
) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        val = _get_nested(record, field)
        if val is not None:
            counter[str(val)] += 1
    return dict(counter.most_common())


def _get_nested(record: dict, dotted_path: str) -> Any:
    current: Any = record
    for key in dotted_path.split("."):
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def build_metrics(
    records: list[dict[str, Any]],
    predictions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build D07 metrics; accepts optional independent predictions table."""
    return compute_d07_metrics(records, predictions or [])


def build_evidence_inventory(
    records: list[dict[str, Any]],
    *,
    max_per_category: int = 5,
    predictions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Compatibility wrapper around D07 evidence extraction."""
    if predictions is None:
        # Legacy embedded predictions: synthesize prediction rows
        predictions = []
        for record in records:
            lab2 = record.get("_lab2") or {}
            model_version = lab2.get("model_version")
            if not model_version:
                continue
            predictions.append(
                {
                    "post_id": record["post_id"],
                    "model_version": model_version,
                    "predicted_label": lab2.get("predicted_label"),
                    "model_scores": lab2.get("model_scores") or {},
                    "status": "ok" if lab2.get("predicted_label") else "error",
                    "confidence": None,
                }
            )
        # Deduplicate posts for evidence join
        unique: dict[str, dict[str, Any]] = {}
        for record in records:
            unique.setdefault(record["post_id"], record)
        records = list(unique.values())

    return extract_evidence(
        records,
        predictions,
        top_n=max_per_category,
        include_text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--max-per-category", type=int, default=5)
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()

    try:
        metrics, evidence = build_d07(
            args.input,
            args.predictions,
            metrics_output=args.metrics,
            evidence_output=args.evidence,
            top_n=args.max_per_category,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Metrics written to {args.metrics}")
    print(f"Evidence inventory ({len(evidence)} entries) written to {args.evidence}")
    if args.print_summary:
        print()
        print("=== Aggregation Summary ===")
        print(f"Unique posts:           {metrics['unique_posts']}")
        print(f"With reference labels:  {metrics['records_with_reference_label']}")
        print(f"With emotion labels:    {metrics['records_with_emotion']}")
        print(f"Model versions:         {', '.join(metrics['model_versions']) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
