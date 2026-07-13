"""Download and verify the frozen HumAID event files.

Raw files remain gitignored. The tracked manifest is the collaboration contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "frozen" / "manifest.json"


class VerificationError(RuntimeError):
    """Raised when a local dataset file violates the frozen manifest."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("manifest_version") != "1.0.0":
        raise VerificationError("unsupported or missing manifest_version")
    return manifest


def validate_file(entry: dict[str, Any], allowed_labels: set[str]) -> set[str]:
    path = PROJECT_ROOT / entry["path"]
    if not path.is_file():
        raise VerificationError(f"missing file: {entry['path']}")
    if path.stat().st_size != entry["bytes"]:
        raise VerificationError(f"byte-size mismatch: {entry['path']}")
    if sha256_file(path) != entry["sha256"]:
        raise VerificationError(f"SHA-256 mismatch: {entry['path']}")

    try:
        with path.open(encoding="utf-8") as handle:
            rows = json.load(handle)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"invalid UTF-8 JSON: {entry['path']}") from exc

    if not isinstance(rows, list) or len(rows) != entry["records"]:
        raise VerificationError(f"record-count mismatch: {entry['path']}")

    expected_fields = {"tweet_id", "tweet_text", "class_label"}
    ids: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise VerificationError(f"field mismatch at {entry['path']} row {index}")
        tweet_id = str(row["tweet_id"])
        if not tweet_id or not isinstance(row["tweet_text"], str) or not row["tweet_text"]:
            raise VerificationError(f"invalid id or text at {entry['path']} row {index}")
        if row["class_label"] not in allowed_labels:
            raise VerificationError(f"unknown label at {entry['path']} row {index}")
        ids.append(tweet_id)

    if len(set(ids)) != len(ids):
        raise VerificationError(f"duplicate tweet_id within {entry['path']}")
    return set(ids)


def download_file(entry: dict[str, Any], force: bool) -> None:
    destination = PROJECT_ROOT / entry["path"]
    if destination.exists() and not force:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(
        entry["url"], headers={"User-Agent": "urban-flood-social-sensing/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as out:
            shutil.copyfileobj(response, out)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def verify_manifest(manifest: dict[str, Any]) -> None:
    allowed_labels = set(manifest["allowed_labels"])
    split_ids: dict[str, set[str]] = {}
    for entry in manifest["files"]:
        split_ids[entry["split"]] = validate_file(entry, allowed_labels)
        print(f"verified {entry['split']}: {entry['records']} records")

    split_names = list(split_ids)
    for index, left in enumerate(split_names):
        for right in split_names[index + 1 :]:
            overlap = split_ids[left] & split_ids[right]
            if overlap:
                raise VerificationError(f"tweet_id overlap between {left} and {right}")

    if manifest["main_corpus_split"] != "test" or manifest["main_corpus_records"] != 1582:
        raise VerificationError("main corpus must remain the 1,582-record test split")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--force", action="store_true", help="redownload existing files")
    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest)
        if not args.verify_only:
            for entry in manifest["files"]:
                download_file(entry, force=args.force)
        verify_manifest(manifest)
    except (OSError, VerificationError) as exc:
        print(f"data gate failed: {exc}", file=sys.stderr)
        return 1

    print("data gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
