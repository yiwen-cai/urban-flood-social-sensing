"""Lab 2 — Emotion annotation helper for exploratory sentiment analysis.

Supports stratified exact-N sampling, full annotation validation, IAA report
generation, and merging emotions into unique posts_labeled rows.
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
DEFAULT_IAA_DOC = PROJECT_ROOT / "docs" / "project" / "emotion_iaa.md"

EMOTION_LABELS = [
    "fear_or_anxiety",
    "anger",
    "sadness",
    "positive_support",
    "neutral_or_unclear",
]


def sample_stratified(
    records: list[dict[str, Any]],
    n_total: int,
    label_field: str = "class_label",
    random_seed: int = 42,
) -> list[dict[str, Any]]:
    """Stratified sample of exactly ``n_total`` records when the pool allows.

    Each class gets at least 1 sample when ``n_total >= n_classes``. Remaining
    slots are filled proportionally, then topped up from leftovers so the
    returned length is exact.
    """
    rng = random.Random(random_seed)

    by_label: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        lbl = r.get(label_field, "unknown")
        by_label.setdefault(lbl, []).append(r)

    if not by_label:
        return []

    n_classes = len(by_label)
    target = min(n_total, len(records))
    if target < n_classes:
        # Still return exactly target items when fewer slots than classes
        pool = list(records)
        rng.shuffle(pool)
        return pool[:target]

    allocation: dict[str, int] = {lbl: 1 for lbl in by_label}
    remaining = target - n_classes
    total_records = len(records)
    for lbl in sorted(by_label, key=lambda x: -len(by_label[x])):
        if remaining <= 0:
            break
        capacity = len(by_label[lbl]) - allocation[lbl]
        if capacity <= 0:
            continue
        extra = max(0, int(len(by_label[lbl]) / total_records * remaining))
        take = min(extra, capacity, remaining)
        allocation[lbl] += take
        remaining -= take

    # Top up any leftover slots from classes with remaining capacity
    if remaining > 0:
        for lbl in sorted(by_label, key=lambda x: -len(by_label[x])):
            if remaining <= 0:
                break
            capacity = len(by_label[lbl]) - allocation[lbl]
            if capacity <= 0:
                continue
            take = min(capacity, remaining)
            allocation[lbl] += take
            remaining -= take

    sample: list[dict[str, Any]] = []
    leftovers: list[dict[str, Any]] = []
    for lbl, n in allocation.items():
        pool = list(by_label[lbl])
        rng.shuffle(pool)
        sample.extend(pool[:n])
        leftovers.extend(pool[n:])

    if len(sample) < target and leftovers:
        rng.shuffle(leftovers)
        sample.extend(leftovers[: target - len(sample)])

    rng.shuffle(sample)
    return sample[:target]


def export_sample(
    records: list[dict[str, Any]],
    output_path: str | Path,
    *,
    annotator: str | None = None,
) -> int:
    from src.utils.redact import redact_text

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for r in records:
            entry = {
                "tweet_id": str(r.get("tweet_id", "")),
                "text_clean": redact_text(r.get("tweet_text", "")),
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
    from src.utils.redact import redact_text

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["tweet_id", "text_clean", "class_label", "exploratory_emotion"])
        for r in records:
            writer.writerow(
                [
                    str(r.get("tweet_id", "")),
                    redact_text(r.get("tweet_text", "")),
                    r.get("class_label", ""),
                    "",
                ]
            )
    return len(records)


def validate_emotion_annotations(
    path: str | Path,
    *,
    require_complete: bool = True,
) -> dict[str, Any]:
    """Validate emotion JSONL rows. Raise ValueError if incomplete/invalid."""
    path = Path(path)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    missing: list[str] = []
    invalid: list[str] = []
    ids: list[str] = []
    for row in rows:
        tid = str(row.get("tweet_id", ""))
        ids.append(tid)
        emotion = row.get("exploratory_emotion")
        if emotion is None or emotion == "":
            missing.append(tid)
        elif emotion not in EMOTION_LABELS:
            invalid.append(f"{tid}:{emotion}")
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate tweet_id values in {path}")
    if invalid:
        raise ValueError(f"Invalid emotion labels in {path}: {invalid[:5]}")
    if require_complete and missing:
        raise ValueError(
            f"Incomplete annotations in {path}: {len(missing)} rows missing "
            f"exploratory_emotion (e.g. {missing[:3]})"
        )
    return {
        "n_rows": len(rows),
        "n_missing": len(missing),
        "n_invalid": len(invalid),
        "complete": len(missing) == 0 and len(invalid) == 0,
    }


def compute_iaa(
    file_a: str | Path,
    file_b: str | Path,
    *,
    require_complete: bool = True,
) -> dict[str, Any]:
    """Compute Cohen's Kappa between two fully annotated JSONL files."""
    validate_emotion_annotations(file_a, require_complete=require_complete)
    validate_emotion_annotations(file_b, require_complete=require_complete)

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
    raw_agreement = sum(1 for a, b in zip(y_a, y_b) if a == b) / len(y_a)

    try:
        from sklearn.metrics import cohen_kappa_score

        kappa = float(cohen_kappa_score(y_a, y_b, labels=EMOTION_LABELS))
    except ImportError:
        kappa = None

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
        "file_a": str(file_a),
        "file_b": str(file_b),
    }


def write_iaa_report(result: dict[str, Any], output_path: str | Path = DEFAULT_IAA_DOC) -> Path:
    """Persist IAA results to the project emotion_iaa markdown report."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Exploratory Emotion — Inter-Annotator Agreement",
        "",
        f"- **File A**: `{result.get('file_a', '')}`",
        f"- **File B**: `{result.get('file_b', '')}`",
        f"- **Overlap**: {result.get('n_overlap')}",
        f"- **Raw agreement**: {result.get('raw_agreement')}",
        f"- **Cohen's Kappa**: {result.get('cohens_kappa')}",
        "",
        "## Per-label agreement",
        "",
        "| Emotion | Total | Agree | Agreement |",
        "|---------|------:|------:|----------:|",
    ]
    for lbl, stats in (result.get("per_label") or {}).items():
        lines.append(
            f"| {lbl} | {stats['total']} | {stats['agree']} | {stats['agreement']} |"
        )
    lines.extend(
        [
            "",
            "---",
            "",
            "*Report auto-generated by `src/lab2_analysis/annotate_seed.py iaa`.*",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def merge_emotions_into_posts(
    emotions_path: str | Path,
    labeled_path: str | Path,
    output_path: str | Path | None = None,
    *,
    require_complete: bool = True,
) -> int:
    """Merge validated emotion labels into unique posts_labeled rows."""
    validate_emotion_annotations(emotions_path, require_complete=require_complete)

    emotion_map: dict[str, str] = {}
    with Path(emotions_path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            entry = json.loads(line)
            tid = str(entry.get("tweet_id", ""))
            emotion = entry.get("exploratory_emotion")
            if tid and emotion:
                emotion_map[tid] = emotion

    labeled_path = Path(labeled_path)
    records = [
        json.loads(line)
        for line in labeled_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # Guard: posts file must be unique by post_id
    ids = [r.get("post_id") for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError(
            f"posts_labeled must have unique post_id rows; found duplicates in {labeled_path}"
        )

    updated = 0
    for r in records:
        pid = r.get("post_id", "")
        tid = pid.split(":", 1)[-1] if ":" in pid else pid
        lab2 = r.setdefault(
            "_lab2",
            {
                "reference_label": None,
                "exploratory_emotion": None,
                "evidence_status": "dataset_record",
            },
        )
        if tid in emotion_map and isinstance(lab2, dict):
            lab2["exploratory_emotion"] = emotion_map[tid]
            updated += 1

    out = Path(output_path) if output_path else labeled_path
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for r in records:
            handle.write(json.dumps(r, ensure_ascii=False) + "\n")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    sample_parser = sub.add_parser("sample", help="Extract stratified emotion samples")
    sample_parser.add_argument("--source", choices=["train", "test", "dev"], default="train")
    sample_parser.add_argument("--n", type=int, default=20)
    sample_parser.add_argument("--output", type=Path, default=None)
    sample_parser.add_argument("--csv", type=Path, default=None)
    sample_parser.add_argument("--annotator", type=str, default=None)
    sample_parser.add_argument("--seed", type=int, default=42)

    iaa_parser = sub.add_parser("iaa", help="Compute inter-annotator agreement")
    iaa_parser.add_argument("file_a", type=Path)
    iaa_parser.add_argument("file_b", type=Path)
    iaa_parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_IAA_DOC,
        help="Write markdown IAA report to this path",
    )
    iaa_parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Do not require every row to have exploratory_emotion",
    )

    merge_parser = sub.add_parser("merge", help="Merge emotion annotations into posts_labeled.jsonl")
    merge_parser.add_argument("--emotions", type=Path, required=True)
    merge_parser.add_argument(
        "--labeled",
        type=Path,
        default=PROJECT_ROOT / "data" / "analyzed" / "posts_labeled.jsonl",
    )
    merge_parser.add_argument("--output", type=Path, default=None)
    merge_parser.add_argument("--allow-incomplete", action="store_true")

    validate_parser = sub.add_parser("validate", help="Validate emotion annotation completeness")
    validate_parser.add_argument("file", type=Path)

    args = parser.parse_args()

    if args.command == "sample":
        source_map = {"train": TRAIN_PATH, "dev": DEV_PATH, "test": TEST_PATH}
        with source_map[args.source].open(encoding="utf-8") as handle:
            all_records = json.load(handle)
        sample = sample_stratified(all_records, n_total=args.n, random_seed=args.seed)
        if len(sample) != min(args.n, len(all_records)):
            print(
                f"ERROR: expected exact sample size {min(args.n, len(all_records))}, "
                f"got {len(sample)}",
                file=sys.stderr,
            )
            return 1
        output = args.output
        if output is None:
            output = DEFAULT_DEV_OUT if args.source in ("train", "dev") else DEFAULT_TEST_OUT
        n = export_sample(sample, output, annotator=args.annotator)
        print(f"Exported {n} records to {output}")
        for lbl, cnt in Counter(r["class_label"] for r in sample).most_common():
            print(f"  {lbl}: {cnt}")
        if args.csv:
            export_csv_for_annotation(sample, Path(args.csv))
            print(f"CSV export: {args.csv}")
        return 0

    if args.command == "iaa":
        result = compute_iaa(
            args.file_a,
            args.file_b,
            require_complete=not args.allow_incomplete,
        )
        report_path = write_iaa_report(result, args.report)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"IAA report written to {report_path}")
        return 0

    if args.command == "merge":
        updated = merge_emotions_into_posts(
            args.emotions,
            args.labeled,
            args.output,
            require_complete=not args.allow_incomplete,
        )
        out = args.output or args.labeled
        print(f"Merged {updated} emotion labels into {out}")
        return 0

    if args.command == "validate":
        result = validate_emotion_annotations(args.file, require_complete=True)
        print(json.dumps(result, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
