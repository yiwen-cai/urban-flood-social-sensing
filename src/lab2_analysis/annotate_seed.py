"""Lab 2 — Emotion annotation helper for exploratory sentiment analysis.

This module supports the manual annotation workflow for the exploratory
emotion task (5-class: fear/anxiety, anger, sadness, positive_support,
neutral/unclear).

Workflow:
1. Extract a stratified sample from the available pool (train for dev,
   test for locked evaluation).
2. Overlap-annotate a small dev set (e.g., 20 records) to compute IAA.
3. Annotate the locked test sample for exploratory reporting.

All emotion labels are stored separately from the 9-class humanitarian
labels and are clearly marked as exploratory course metadata.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_PATH = PROJECT_ROOT / "data" / "raw" / "humaid" / "kerala_floods_2018" / "train.json"
DEV_PATH = PROJECT_ROOT / "data" / "raw" / "humaid" / "kerala_floods_2018" / "dev.json"
TEST_PATH = PROJECT_ROOT / "data" / "raw" / "humaid" / "kerala_floods_2018" / "test.json"
DEFAULT_DEV_OUT = PROJECT_ROOT / "data" / "seed" / "emotion_dev.jsonl"
DEFAULT_TEST_OUT = PROJECT_ROOT / "data" / "seed" / "emotion_test.jsonl"

EMOTION_LABELS = [
    "fear_or_anxiety",
    "anger",
    "sadness",
    "positive_support",
    "neutral_or_unclear",
]

EMOTION_LABELS_ZH = {
    "fear_or_anxiety": "恐慌/焦虑",
    "anger": "愤怒",
    "sadness": "悲伤",
    "positive_support": "积极支持",
    "neutral_or_unclear": "中性/无法判断",
}


def sample_stratified(
    records: list[dict[str, Any]],
    n_total: int,
    label_field: str = "class_label",
    random_seed: int = 42,
) -> list[dict[str, Any]]:
    """Stratified sample across HumAID labels, preserving rare classes.

    Each class gets at least 1 sample; the remainder is distributed
    proportionally.
    """
    random.seed(random_seed)

    by_label: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        lbl = r.get(label_field, "unknown")
        by_label.setdefault(lbl, []).append(r)

    n_classes = len(by_label)
    if n_total < n_classes:
        n_total = n_classes

    # Allocate at least 1 per class
    allocation: dict[str, int] = {lbl: 1 for lbl in by_label}
    remaining = n_total - n_classes

    # Distribute remaining proportionally
    total_records = len(records)
    for lbl in by_label:
        if remaining <= 0:
            break
        extra = max(0, int(len(by_label[lbl]) / total_records * remaining))
        allocation[lbl] += min(extra, len(by_label[lbl]) - 1)

    # Sample
    sample: list[dict[str, Any]] = []
    for lbl, n in allocation.items():
        pool = by_label[lbl]
        selected = random.sample(pool, min(n, len(pool)))
        sample.extend(selected)

    random.shuffle(sample)
    return sample


def export_sample(
    records: list[dict[str, Any]],
    output_path: str | Path,
    *,
    annotator: str | None = None,
) -> int:
    """Export a sample to JSONL with empty emotion placeholder.

    Each line:
        {"tweet_id": ..., "tweet_text": ..., "class_label": ...,
         "exploratory_emotion": null, "annotator": "..."}
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for r in records:
            entry = {
                "tweet_id": str(r.get("tweet_id", "")),
                "tweet_text": r.get("tweet_text", ""),
                "class_label": r.get("class_label", ""),
                "exploratory_emotion": None,
            }
            if annotator:
                entry["annotator"] = annotator
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return len(records)


def export_csv_for_annotation(
    records: list[dict[str, Any]],
    output_path: str | Path,
) -> int:
    """Export a sample as CSV for external annotation (e.g., in Excel/Sheets).

    Columns: tweet_id, tweet_text, class_label, exploratory_emotion
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["tweet_id", "tweet_text", "class_label", "exploratory_emotion"])
        for r in records:
            writer.writerow([
                str(r.get("tweet_id", "")),
                r.get("tweet_text", ""),
                r.get("class_label", ""),
                "",  # to be filled in manually
            ])

    return len(records)


def compute_iaa(
    file_a: str | Path,
    file_b: str | Path,
) -> dict[str, Any]:
    """Compute inter-annotator agreement between two annotators' JSONL files.

    Each file must have the same tweet_ids with ``exploratory_emotion`` filled.
    Returns Cohen's Kappa and raw agreement percentage.
    """
    def _load_annotations(path: Path) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            tid = entry.get("tweet_id", "")
            emotion = entry.get("exploratory_emotion")
            if emotion:
                mapping[tid] = emotion
        return mapping

    ann_a = _load_annotations(Path(file_a))
    ann_b = _load_annotations(Path(file_b))

    common_ids = set(ann_a) & set(ann_b)
    if not common_ids:
        return {"error": "No overlapping tweet_ids found.", "kappa": None, "agreement": None}

    y_a = [ann_a[tid] for tid in sorted(common_ids)]
    y_b = [ann_b[tid] for tid in sorted(common_ids)]

    # Raw agreement
    raw_agreement = sum(1 for a, b in zip(y_a, y_b) if a == b) / len(y_a)

    # Cohen's Kappa
    try:
        from sklearn.metrics import cohen_kappa_score
        kappa = float(cohen_kappa_score(y_a, y_b, labels=EMOTION_LABELS))
    except ImportError:
        kappa = None  # sklearn not available

    # Per-label agreement
    per_label: dict[str, dict[str, Any]] = {}
    for lbl in EMOTION_LABELS:
        indices = [i for i, (a, b) in enumerate(zip(y_a, y_b)) if a == lbl or b == lbl]
        if indices:
            agree = sum(1 for i in indices if y_a[i] == y_b[i])
            per_label[lbl] = {
                "total": len(indices),
                "agree": agree,
                "agreement": round(agree / len(indices), 4),
            }

    return {
        "n_overlap": len(common_ids),
        "raw_agreement": round(raw_agreement, 4),
        "cohens_kappa": round(kappa, 4) if kappa is not None else None,
        "per_label": per_label,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    # === sample ===
    sample_parser = sub.add_parser("sample", help="Extract stratified emotion samples")
    sample_parser.add_argument(
        "--source",
        choices=["train", "test", "dev"],
        default="train",
        help="Which split to sample from (default: train for dev set)",
    )
    sample_parser.add_argument(
        "--n", type=int, default=20,
        help="Number of records to sample (default: 20)",
    )
    sample_parser.add_argument(
        "--output", type=Path, default=None,
        help="Output JSONL path",
    )
    sample_parser.add_argument(
        "--csv", type=Path, default=None,
        help="Also export as CSV for external annotation",
    )
    sample_parser.add_argument(
        "--annotator", type=str, default=None,
        help="Annotator identifier",
    )
    sample_parser.add_argument("--seed", type=int, default=42)

    # === iaa ===
    iaa_parser = sub.add_parser("iaa", help="Compute inter-annotator agreement")
    iaa_parser.add_argument("file_a", type=Path)
    iaa_parser.add_argument("file_b", type=Path)

    # === merge ===
    merge_parser = sub.add_parser(
        "merge",
        help="Merge emotion annotations into posts_labeled.jsonl",
    )
    merge_parser.add_argument(
        "--emotions", type=Path, required=True,
        help="Emotion annotation JSONL file",
    )
    merge_parser.add_argument(
        "--labeled", type=Path,
        default=PROJECT_ROOT / "data" / "analyzed" / "posts_labeled.jsonl",
        help="posts_labeled.jsonl to update",
    )
    merge_parser.add_argument(
        "--output", type=Path,
        default=None,
        help="Output path (default: overwrite --labeled)",
    )

    args = parser.parse_args()

    if args.command == "sample":
        # Load source
        source_map = {
            "train": TRAIN_PATH,
            "dev": DEV_PATH,
            "test": TEST_PATH,
        }
        source_path = source_map[args.source]
        with source_path.open(encoding="utf-8") as handle:
            all_records = json.load(handle)

        sample = sample_stratified(
            all_records, n_total=args.n, random_seed=args.seed
        )

        # Default output
        output = args.output
        if output is None:
            output = DEFAULT_DEV_OUT if args.source in ("train", "dev") else DEFAULT_TEST_OUT

        n = export_sample(sample, output, annotator=args.annotator)
        print(f"Exported {n} records to {output}")

        label_counts = Counter(r["class_label"] for r in sample)
        print("Label distribution:")
        for lbl, cnt in label_counts.most_common():
            print(f"  {lbl}: {cnt}")

        if args.csv:
            csv_path = Path(args.csv)
            export_csv_for_annotation(sample, csv_path)
            print(f"CSV export: {csv_path}")

        return 0

    elif args.command == "iaa":
        result = compute_iaa(args.file_a, args.file_b)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    elif args.command == "merge":
        # Load emotion annotations
        emotion_map: dict[str, str] = {}
        with Path(args.emotions).open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                entry = json.loads(line)
                tid = entry.get("tweet_id", "")
                emotion = entry.get("exploratory_emotion")
                if tid and emotion:
                    emotion_map[tid] = emotion

        # Load posts_labeled.jsonl
        labeled_path = Path(args.labeled)
        records = [
            json.loads(line)
            for line in labeled_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        # Merge
        updated = 0
        for r in records:
            pid = r.get("post_id", "")
            # Strip Lab 1 split prefix: "test:103243..." → "103243..."
            tid = pid.split(":", 1)[-1] if ":" in pid else pid
            lab2 = r.get("_lab2")
            if tid in emotion_map and isinstance(lab2, dict):
                lab2["exploratory_emotion"] = emotion_map[tid]
                updated += 1

        output_path = Path(args.output) if args.output else labeled_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for r in records:
                handle.write(json.dumps(r, ensure_ascii=False) + "\n")

        print(f"Merged {updated} emotion labels into {output_path}")
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
