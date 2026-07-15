"""D07 single writer: corpus metrics + privacy-bounded evidence.

Reads posts_labeled.jsonl + predictions.jsonl and writes:
- data/output/metrics.json  (schemas/metrics.schema.json v2.0.0)
- data/output/evidence.jsonl (schemas/evidence.schema.json v1.0.0)

Lab 2 ``aggregate.py`` is a compatibility wrapper around this module.
Real humaid_events evidence never copies tweet bodies.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POSTS = PROJECT_ROOT / "data" / "analyzed" / "posts_labeled.jsonl"
DEFAULT_PREDICTIONS = PROJECT_ROOT / "data" / "analyzed" / "predictions.jsonl"
DEFAULT_METRICS = PROJECT_ROOT / "data" / "output" / "metrics.json"
DEFAULT_EVIDENCE = PROJECT_ROOT / "data" / "output" / "evidence.jsonl"

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
EMOTIONS = [
    "fear_or_anxiety",
    "anger",
    "sadness",
    "positive_support",
    "neutral_or_unclear",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as tmp:
        for row in rows:
            tmp.write(json.dumps(row, ensure_ascii=False) + "\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _posts_by_id(posts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for post in posts:
        pid = post["post_id"]
        if pid in out:
            raise ValueError(f"duplicate post_id in posts file: {pid}")
        out[pid] = post
    return out


def _per_model_metrics(
    posts_by_id: dict[str, dict[str, Any]],
    predictions: list[dict[str, Any]],
    model_version: str,
) -> dict[str, Any]:
    from src.lab2_analysis.evaluate import compute_metrics

    model_preds = [p for p in predictions if p.get("model_version") == model_version]
    pred_by_id = {p["post_id"]: p for p in model_preds}

    y_true: list[str] = []
    y_pred: list[str | None] = []
    predicted_dist: Counter[str] = Counter()
    n_errors = 0

    for post_id, post in sorted(posts_by_id.items()):
        ref = (post.get("_lab2") or {}).get("reference_label")
        if ref is None:
            continue
        row = pred_by_id.get(post_id)
        if row is None:
            y_true.append(ref)
            y_pred.append(None)
            n_errors += 1
            continue
        if row.get("status") == "error" or row.get("predicted_label") is None:
            y_true.append(ref)
            y_pred.append(None)
            n_errors += 1
            continue
        label = row["predicted_label"]
        y_true.append(ref)
        y_pred.append(label)
        predicted_dist[label] += 1

    metrics = compute_metrics(y_true, y_pred, LABELS, full_denominator=True)
    cm = metrics.get("confusion_matrix")
    cm_dict: dict[str, dict[str, int]] = {}
    if cm is not None:
        for i, ref_label in enumerate(LABELS):
            row_counts: dict[str, int] = {}
            for j, pred_label in enumerate(LABELS):
                count = int(cm[i, j])
                if count:
                    row_counts[pred_label] = count
            if row_counts:
                cm_dict[ref_label] = row_counts

    per_class: dict[str, dict[str, Any]] = {}
    for pc in metrics.get("per_class") or []:
        label = pc["label"]
        correct = 0
        if cm is not None:
            idx = LABELS.index(label)
            correct = int(cm[idx, idx])
        per_class[label] = {
            "support": pc["support"],
            "predicted_count": predicted_dist.get(label, 0),
            "correct": correct,
            "precision": pc["precision"],
            "recall": pc["recall"],
            "f1": pc["f1"],
        }

    return {
        "n_predictions": len(model_preds),
        "n_errors": n_errors,
        "coverage": metrics["coverage"],
        "accuracy": metrics["accuracy"],
        "macro_f1": metrics["macro_f1"],
        "weighted_f1": metrics["weighted_f1"],
        "accuracy_on_successful_only": metrics.get("accuracy_on_successful_only"),
        "predicted_label_distribution": dict(predicted_dist),
        "per_class": per_class,
        "confusion_matrix": cm_dict,
    }


def compute_metrics(
    posts: list[dict[str, Any]],
    predictions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build D07 metrics.json payload (metrics_version 2.0.0)."""
    if predictions is None:
        predictions = []

    posts_by_id = _posts_by_id(posts)
    unique_posts = len(posts_by_id)
    ref_dist: Counter[str] = Counter()
    emotion_dist: Counter[str] = Counter()
    with_ref = 0
    with_emotion = 0

    for post in posts_by_id.values():
        lab2 = post.get("_lab2") or {}
        ref = lab2.get("reference_label")
        emotion = lab2.get("exploratory_emotion")
        if ref is not None:
            with_ref += 1
            ref_dist[ref] += 1
        if emotion is not None:
            with_emotion += 1
            emotion_dist[emotion] += 1

    model_versions = sorted(
        {p.get("model_version") for p in predictions if p.get("model_version")}
    )
    per_model = {
        version: _per_model_metrics(posts_by_id, predictions, version)
        for version in model_versions
    }

    return {
        "metrics_version": "2.0.0",
        "unique_posts": unique_posts,
        "records_with_reference_label": with_ref,
        "records_with_emotion": with_emotion,
        "model_versions": model_versions,
        "reference_label_distribution": dict(ref_dist),
        "emotion_distribution": dict(emotion_dist),
        "per_model": per_model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "notes": None,
    }


def extract_evidence(
    posts: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    top_n: int = 3,
    model_version: str | None = None,
    include_text: bool | None = None,
) -> list[dict[str, Any]]:
    """Select representative evidence rows with privacy bounds."""
    posts_by_id = _posts_by_id(posts)
    if include_text is None:
        sources = {p.get("source") for p in posts}
        include_text = sources == {"synthetic_fixture"}

    selected_models = (
        [model_version]
        if model_version
        else sorted({p.get("model_version") for p in predictions if p.get("model_version")})
    )

    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for version in selected_models:
        by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
        urgent: list[dict[str, Any]] = []
        for pred in predictions:
            if pred.get("model_version") != version:
                continue
            if pred.get("status") != "ok" or not pred.get("predicted_label"):
                continue
            post = posts_by_id.get(pred["post_id"])
            if post is None:
                continue
            label = pred["predicted_label"]
            source = post.get("source", "humaid_events")
            text = post.get("text_clean") if include_text and source == "synthetic_fixture" else None
            if source == "humaid_events":
                text = None
            confidence = pred.get("confidence")
            if confidence is None and label in (pred.get("model_scores") or {}):
                confidence = pred["model_scores"][label]
            evidence = {
                "evidence_version": "1.0.0",
                "post_id": post["post_id"],
                "model_version": version,
                "source": source,
                "source_ref": post.get("source_ref", ""),
                "predicted_label": label,
                "reference_label": (post.get("_lab2") or {}).get("reference_label"),
                "selection_reason": "",
                "confidence": confidence,
                "text_clean": text,
                "exploratory_emotion": (post.get("_lab2") or {}).get("exploratory_emotion"),
            }
            by_class[label].append(evidence)
            if label == "requests_or_urgent_needs":
                urgent.append(evidence)

        for label in LABELS:
            ranked = sorted(
                by_class.get(label, []),
                key=lambda x: (x["confidence"] is not None, x["confidence"] or 0.0),
                reverse=True,
            )
            for row in ranked[:top_n]:
                item = dict(row)
                item["selection_reason"] = f"top-{top_n} high-confidence {label}"
                key = (item["post_id"], item["model_version"], item["selection_reason"])
                if key not in seen:
                    seen.add(key)
                    records.append(item)

        for row in urgent:
            item = dict(row)
            item["selection_reason"] = "urgent needs: all records included"
            key = (item["post_id"], item["model_version"], item["selection_reason"])
            if key not in seen:
                seen.add(key)
                records.append(item)

    return records


def build_d07(
    posts_path: Path,
    predictions_path: Path,
    *,
    metrics_output: Path = DEFAULT_METRICS,
    evidence_output: Path = DEFAULT_EVIDENCE,
    top_n: int = 3,
    model_version: str | None = None,
    include_text: bool | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not posts_path.is_file():
        raise FileNotFoundError(f"posts not found: {posts_path}")
    posts = load_jsonl(posts_path)
    predictions = load_jsonl(predictions_path) if predictions_path.is_file() else []
    metrics = compute_metrics(posts, predictions)
    evidence = extract_evidence(
        posts,
        predictions,
        top_n=top_n,
        model_version=model_version,
        include_text=include_text,
    )
    write_json_atomic(metrics_output, metrics)
    write_jsonl_atomic(evidence_output, evidence)
    return metrics, evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posts", type=Path, default=DEFAULT_POSTS)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--metrics-output", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--evidence-output", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--model-version", type=str, default=None)
    parser.add_argument(
        "--include-text",
        action="store_true",
        help="Force include text_clean (synthetic fixtures only still enforced for humaid)",
    )
    # Compatibility aliases used by older aggregate CLI / docs
    parser.add_argument("--input", type=Path, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()

    posts_path = args.input or args.posts
    try:
        metrics, evidence = build_d07(
            posts_path,
            args.predictions,
            metrics_output=args.metrics_output,
            evidence_output=args.evidence_output,
            top_n=args.top_n,
            model_version=args.model_version,
            include_text=True if args.include_text else None,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"metrics: {args.metrics_output} "
        f"({metrics['unique_posts']} unique posts, "
        f"{len(metrics['model_versions'])} models)"
    )
    print(f"evidence: {args.evidence_output} ({len(evidence)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
