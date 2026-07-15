"""Batch cache and checkpoint/resume support for model classification runs.

Caches LLM responses keyed by (model, text_hash) so that re-running the
pipeline does not re-invoke the API for already-classified posts.  Supports
incremental resume when a large batch is interrupted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ClassificationCache:
    """File-backed cache for model classification results.

    Each cache entry is stored as a JSONL line:
        {"key": "<model>:<sha256>", "result": {...}}

    The in-memory dict avoids O(n²) file reads during batch processing.
    """

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        if cache_dir is None:
            from pathlib import Path as _Path
            cache_dir = _Path(__file__).resolve().parents[2] / "data" / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._loaded: dict[str, dict[str, dict[str, Any]]] = {}

    def _cache_path(self, model_version: str) -> Path:
        safe = model_version.replace("/", "_").replace(" ", "_")
        return self.cache_dir / f"classify_{safe}.jsonl"

    def _make_key(self, model_version: str, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
        return f"{model_version}:{digest}"

    def _ensure_loaded(self, model_version: str) -> dict[str, dict[str, Any]]:
        """Load cache into memory once per model version."""
        if model_version in self._loaded:
            return self._loaded[model_version]
        cache_path = self._cache_path(model_version)
        if not cache_path.is_file():
            self._loaded[model_version] = {}
            return {}
        loaded: dict[str, dict[str, Any]] = {}
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            loaded[entry.get("key", "")] = entry.get("result", {})
        self._loaded[model_version] = loaded
        return loaded

    def get(self, model_version: str, text: str) -> dict[str, Any] | None:
        """Return cached result or None (O(1) after first load)."""
        loaded = self._ensure_loaded(model_version)
        return loaded.get(self._make_key(model_version, text))

    def put(
        self, model_version: str, text: str, result: dict[str, Any]
    ) -> None:
        """Store a classification result in the cache (disk + memory)."""
        key = self._make_key(model_version, text)
        entry = {"key": key, "result": result}
        cache_path = self._cache_path(model_version)
        with cache_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if model_version not in self._loaded:
            self._ensure_loaded(model_version)
        self._loaded[model_version][key] = result

    def load_all(
        self, model_version: str
    ) -> dict[str, dict[str, Any]]:
        """Return all cached entries for a model version (from memory)."""
        return dict(self._ensure_loaded(model_version))

    def stats(self, model_version: str) -> dict[str, int]:
        """Return basic stats about the cache."""
        all_entries = self.load_all(model_version)
        return {
            "cached_entries": len(all_entries),
            "success_count": sum(
                1 for v in all_entries.values() if v.get("success", True)
            ),
            "error_count": sum(
                1 for v in all_entries.values() if not v.get("success", True)
            ),
        }


class Checkpoint:
    """Track which records have been processed in a batch run.

    Stores only the set of post_ids that have been successfully processed.
    This allows resuming an interrupted batch without re-processing.
    """

    def __init__(self, checkpoint_path: str | Path) -> None:
        self.path = Path(checkpoint_path)
        self._ids: set[str] = set()

    def load(self) -> set[str]:
        """Load already-processed post_ids from the checkpoint file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.is_file():
            return set()
        ids = set()
        for line in self.path.read_text(encoding="utf-8").splitlines():
            pid = line.strip()
            if pid:
                ids.add(pid)
        self._ids = ids
        return ids

    def mark_done(self, post_id: str) -> None:
        """Record a post_id as successfully processed."""
        self._ids.add(post_id)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(post_id + "\n")

    def mark_done_batch(self, post_ids: list[str]) -> None:
        """Record multiple post_ids at once."""
        new_ids = set(post_ids) - self._ids
        if not new_ids:
            return
        self._ids.update(new_ids)
        with self.path.open("a", encoding="utf-8") as handle:
            for pid in new_ids:
                handle.write(pid + "\n")

    def is_done(self, post_id: str) -> bool:
        return post_id in self._ids

    def remaining(self, all_ids: list[str]) -> list[str]:
        return [pid for pid in all_ids if pid not in self._ids]
