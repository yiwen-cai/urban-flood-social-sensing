"""JSON Lines read/write helpers shared across Lab 1-3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


# ---------------------------------------------------------------------------
# Convenience aliases / helpers (not used by Lab 1, safe to add)
# ---------------------------------------------------------------------------

#: Alias for read_jsonl — explicit name for streaming iteration.
iter_jsonl = read_jsonl


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Append records to an existing JSONL file (or create it if absent)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def count_records(path: Path) -> int:
    """Count non-empty lines in a JSONL file (without parsing JSON)."""
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def load_raw_humaid(path: Path) -> list[dict[str, Any]]:
    """Load a raw HumAID JSON file (array-wrapped, not JSONL).

    Raw HumAID files are standard JSON arrays with fields:
        tweet_id, tweet_text, class_label
    """
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}")
    return data
