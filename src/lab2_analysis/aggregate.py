"""Lab 2 — Aggregation: category distributions and evidence inventory for Lab 3.

Produces:
- ``data/output/metrics.json`` — structured, recalculable statistics.
- ``data/output/evidence.jsonl`` — representative records with source_ref for
  briefing traceability.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "analyzed" / "posts_labeled.jsonl"
DEFAULT_METRICS = PROJECT_ROOT / "data" / "output" / "metrics.json"
DEFAULT_EVIDENCE = PROJECT_ROOT / "data" / "output" / "evidence.jsonl"


def load_records(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def compute_distribution(
    records: list[dict[str, Any]],
    field: str,
) -> dict[str, int]:
    """Count frequency of a field value across records."""
    counter: Counter[str] = Counter()
    for r in records:
        val = _get_nested(r, field)
        if val is not None:
            counter[str(val)] += 1
    return dict(counter.most_common())


def _get_nested(record: dict, dotted_path: str) -> Any:
    """Get a nested value like '_lab2.predicted_label'."""
    keys = dotted_path.split(".")
    current: Any = record
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return None
    return current


def build_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the comprehensive metrics.json payload."""

    # Split stats
    total = len(records)
    with_ref = sum(
        1 for r in records
        if (r.get("_lab2") or {}).get("reference_label") is not None
    )
    with_pred = sum(
        1 for r in records
        if (r.get("_lab2") or {}).get("predicted_label") is not None
    )
    with_emotion = sum(
        1 for r in records
        if (r.get("_lab2") or {}).get("exploratory_emotion") is not None
    )

    # Reference label distribution (official HumAID labels)
    ref_dist = compute_distribution(records, "_lab2.reference_label")

    # Predicted label distribution (per model)
    predicted_dist: dict[str, dict[str, int]] = {}
    for r in records:
        lab2 = r.get("_lab2") or {}
        model_ver = lab2.get("model_version", "unknown")
        label = lab2.get("predicted_label")
        if label:
            if model_ver not in predicted_dist:
                predicted_dist[model_ver] = {}
            predicted_dist[model_ver][label] = (
                predicted_dist[model_ver].get(label, 0) + 1
            )

    # Emotion distribution
    emotion_dist = compute_distribution(records, "_lab2.exploratory_emotion")

    # Evidence status distribution
    evidence_status_dist = compute_distribution(records, "_lab2.evidence_status")

    # Model versions present
    model_versions = list(predicted_dist.keys())

    # Error record count (separate file)
    error_path = PROJECT_ROOT / "data" / "analyzed" / "classification_errors.jsonl"
    error_count = 0
    if error_path.is_file():
        error_count = sum(
            1 for line in error_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    return {
        "metrics_version": "1.0.0",
        "total_records": total,
        "records_with_reference_label": with_ref,
        "records_with_prediction": with_pred,
        "records_with_emotion": with_emotion,
        "error_records": error_count,
        "model_versions": model_versions,
        "reference_label_distribution": ref_dist,
        "predicted_label_distribution": predicted_dist,
        "emotion_distribution": emotion_dist,
        "evidence_status_distribution": evidence_status_dist,
        "generated_at": None,  # populated at write time
    }


def build_evidence_inventory(
    records: list[dict[str, Any]],
    *,
    max_per_category: int = 5,
) -> list[dict[str, Any]]:
    """Select representative records for each label for briefing traceability.

    Selection criteria:
    - Has a reference label (is from the official test split)
    - Preference for records where predicted == reference (correctly classified)
    - Limit ``max_per_category`` per label to keep inventory manageable
    """
    from collections import defaultdict

    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for r in records:
        lab2 = r.get("_lab2") or {}
        ref = lab2.get("reference_label")
        pred = lab2.get("predicted_label")
        if ref is None:
            continue
        # Score: 1 if correct prediction, 0 otherwise — sort by this
        score = 1 if ref == pred else 0
        by_label[ref].append((score, r))

    evidence: list[dict[str, Any]] = []
    for label in sorted(by_label):
        # Sort by score descending, take top N
        scored = sorted(by_label[label], key=lambda x: (-x[0]))
        for score, record in scored[:max_per_category]:
            lab2 = record.get("_lab2") or {}
            evidence.append({
                "post_id": record["post_id"],
                "source_ref": record["source_ref"],
                "reference_label": lab2.get("reference_label"),
                "predicted_label": lab2.get("predicted_label"),
                "evidence_status": lab2.get("evidence_status"),
                "text_clean": record.get("text_clean", ""),
                "is_correct_prediction": lab2.get("reference_label") == lab2.get("predicted_label"),
            })

    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to posts_labeled.jsonl",
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=DEFAULT_METRICS,
        help="Path for metrics.json output",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=DEFAULT_EVIDENCE,
        help="Path for evidence.jsonl output",
    )
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=5,
        help="Max representative records per label (default: 5)",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print a summary to stdout",
    )
    args = parser.parse_args()

    if not Path(args.input).is_file():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1

    records = load_records(args.input)

    # Build and write metrics
    metrics = build_metrics(records)
    metrics["generated_at"] = __import__("datetime").datetime.now().isoformat()
    metrics_path = Path(args.metrics)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Metrics written to {metrics_path}")

    # Build and write evidence inventory
    evidence = build_evidence_inventory(
        records, max_per_category=args.max_per_category
    )
    evidence_path = Path(args.evidence)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    with evidence_path.open("w", encoding="utf-8") as handle:
        for entry in evidence:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Evidence inventory ({len(evidence)} entries) written to {evidence_path}")

    if args.print_summary:
        print()
        print("=== Aggregation Summary ===")
        print(f"Total records:          {metrics['total_records']}")
        print(f"With reference labels:  {metrics['records_with_reference_label']}")
        print(f"With predictions:       {metrics['records_with_prediction']}")
        print(f"With emotion labels:    {metrics['records_with_emotion']}")
        print(f"Error records:          {metrics['error_records']}")
        print()
        print("Reference Label Distribution:")
        for lbl, cnt in metrics["reference_label_distribution"].items():
            pct = cnt / metrics["total_records"] * 100 if metrics["total_records"] else 0
            print(f"  {lbl}: {cnt} ({pct:.1f}%)")
        print()
        for ver, dist in metrics["predicted_label_distribution"].items():
            print(f"Predicted Distribution ({ver}):")
            for lbl, cnt in sorted(dist.items(), key=lambda x: -x[1]):
                print(f"  {lbl}: {cnt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
