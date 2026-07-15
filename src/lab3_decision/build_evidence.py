"""Compute structured metrics and extract evidence records from labeled posts.

Reads posts_labeled.jsonl → metrics.json + evidence.jsonl.
All numbers are computed by code, never handed to an LLM to calculate.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LABELS = [
    "caution_and_advice",
    "displaced_people_and_evacuations",
    "infrastructure_and_utility_damage",
    "injured_or_dead_people",
    "not_humanitarian",
    "other_relevant_information",
    "requests_or_urgent_needs",
    "rescue_volunteering_or_donation_effort",
    "sympathy_and_support",
]
EMOTIONS = ["fear_or_anxiety", "anger", "sadness", "positive_support", "neutral_or_unclear"]


def load_posts(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_metrics(posts: list[dict]) -> dict:
    total = len(posts)
    cat_counts: dict[str, int] = dict.fromkeys(LABELS, 0)
    pred_counts: dict[str, int] = dict.fromkeys(LABELS, 0)
    correct_per_class: dict[str, int] = dict.fromkeys(LABELS, 0)
    emotion_counts: dict[str, int] = dict.fromkeys(EMOTIONS, 0)
    evidence_status_counts: dict[str, int] = Counter()
    correct = 0

    # Data quality counters
    missing_text = 0
    missing_ref = 0
    missing_pred = 0
    post_ids: set[str] = set()
    duplicates = 0

    for p in posts:
        lab2 = p.get("_lab2")
        if not lab2:
            continue

        # Data quality
        if not p.get("text_clean"):
            missing_text += 1
        if not lab2.get("reference_label"):
            missing_ref += 1
        if not lab2.get("predicted_label"):
            missing_pred += 1
        pid = p.get("post_id", "")
        if pid in post_ids:
            duplicates += 1
        post_ids.add(pid)

        ref = lab2.get("reference_label")
        pred = lab2.get("predicted_label")
        emotion = lab2.get("exploratory_emotion")
        status = lab2.get("evidence_status", "model_prediction")

        if ref in cat_counts:
            cat_counts[ref] += 1
        if pred in pred_counts:
            pred_counts[pred] += 1
        if ref and pred and ref == pred:
            correct += 1
            correct_per_class[ref] += 1
        if emotion in emotion_counts:
            emotion_counts[emotion] += 1
        evidence_status_counts[status] += 1

    accuracy = correct / total if total else 0
    per_class_stats = {}
    for label in LABELS:
        support = cat_counts[label]
        prec = correct_per_class[label] / pred_counts[label] if pred_counts[label] else 0
        rec = correct_per_class[label] / support if support else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        per_class_stats[label] = {
            "reference_count": support,
            "predicted_count": pred_counts[label],
            "correct": correct_per_class[label],
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
        }

    return {
        "total_records": total,
        "correct_predictions": correct,
        "accuracy": round(accuracy, 4),
        "category_distribution": cat_counts,
        "predicted_distribution": pred_counts,
        "per_class_stats": per_class_stats,
        "emotion_distribution": emotion_counts,
        "evidence_status_distribution": dict(evidence_status_counts),
        "data_quality": {
            "unique_post_ids": len(post_ids),
            "duplicate_ids": duplicates,
            "missing_text_clean": missing_text,
            "missing_reference_label": missing_ref,
            "missing_predicted_label": missing_pred,
            "time_null": total,   # all records — by design per DATA_GATE.md
            "location_null": total,
        },
    }


def extract_evidence(posts: list[dict], top_n: int = 3) -> list[dict]:
    by_class: dict[str, list[dict]] = defaultdict(list)
    all_urgent: list[dict] = []

    for p in posts:
        lab2 = p.get("_lab2")
        if not lab2:
            continue
        pred = lab2.get("predicted_label")
        if not pred:
            continue

        evidence = {
            "source_ref": p["source_ref"],
            "text_clean": p["text_clean"],
            "predicted_label": pred,
            "reference_label": lab2.get("reference_label"),
            "exploratory_emotion": lab2.get("exploratory_emotion"),
            "evidence_status": lab2.get("evidence_status", "model_prediction"),
            "confidence": lab2.get("model_scores", {}).get(pred, 0),
        }
        by_class[pred].append(evidence)
        if pred == "requests_or_urgent_needs":
            all_urgent.append(evidence)

    records: list[dict] = []
    for label in LABELS:
        ranked = sorted(by_class.get(label, []), key=lambda x: x["confidence"], reverse=True)
        for e in ranked[:top_n]:
            e["selection_reason"] = f"top-{top_n} high-confidence {label}"
            records.append(e)
    for e in all_urgent:
        e["selection_reason"] = "urgent needs: all records included"
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path,
        default=PROJECT_ROOT / "data" / "analyzed" / "posts_labeled.jsonl",
        help="path to posts_labeled.jsonl",
    )
    parser.add_argument(
        "--metrics-output", type=Path,
        default=PROJECT_ROOT / "data" / "output" / "metrics.json",
    )
    parser.add_argument(
        "--evidence-output", type=Path,
        default=PROJECT_ROOT / "data" / "output" / "evidence.jsonl",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        import sys
        print(f"not found: {args.input} — run against fixture first", file=sys.stderr)
        raise SystemExit(1)

    posts = load_posts(args.input)
    metrics = compute_metrics(posts)
    evidence = extract_evidence(posts)

    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
    with args.evidence_output.open("w", encoding="utf-8") as f:
        for e in evidence:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"metrics: {args.metrics_output} ({metrics['total_records']} records, accuracy={metrics['accuracy']})")
    print(f"evidence: {args.evidence_output} ({len(evidence)} records)")


if __name__ == "__main__":
    main()
