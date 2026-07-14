"""Deduplicate, filter, and standardize raw HumAID Kerala splits into posts_clean.jsonl."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.lab1_collection.standardize import standardize_record
from src.utils.io import write_jsonl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "frozen" / "manifest.json"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def default_output_for_split(split: str) -> Path:
    return PROCESSED_DIR / f"posts_clean.{split}.jsonl"


def load_raw_split(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def clean_split(raw_rows: list[dict[str, Any]], split: str, pipeline_run_id: str) -> list[dict[str, Any]]:
    seen_ids: set[str] = set()
    cleaned: list[dict[str, Any]] = []
    for raw in raw_rows:
        tweet_id = str(raw["tweet_id"])
        text = raw["tweet_text"].strip()
        if tweet_id in seen_ids or not text:
            continue
        seen_ids.add(tweet_id)
        record = standardize_record(raw, split=split, pipeline_run_id=pipeline_run_id)
        cleaned.append(record)
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--split", default="test", help="manifest split to clean")
    parser.add_argument("--pipeline-run-id", default="kerala-v1")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = args.output or default_output_for_split(args.split)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    entry = next(e for e in manifest["files"] if e["split"] == args.split)
    raw_rows = load_raw_split(PROJECT_ROOT / entry["path"])

    cleaned = clean_split(raw_rows, split=args.split, pipeline_run_id=args.pipeline_run_id)
    write_jsonl(output, cleaned)
    print(f"cleaned {len(cleaned)} of {len(raw_rows)} raw records -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
