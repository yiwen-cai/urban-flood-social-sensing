"""Batch cache and checkpoint/resume support for model classification runs.

Caches LLM responses keyed by (model, config_fingerprint, text_hash) so that
re-running the pipeline does not re-invoke the API for already-classified
posts when the prompt/few-shot/config is unchanged. Supports incremental
resume when a large batch is interrupted — only successful IDs are
checkpointed so failures remain retryable.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


def config_fingerprint(payload: dict[str, Any]) -> str:
    """Stable short hash of prompt/few-shot/config used in the cache key."""
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def is_finite_unit_interval(value: Any) -> bool:
    """Return True iff value is a finite number in [0, 1]."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and 0.0 <= number <= 1.0


class ClassificationCache:
    """File-backed cache for model classification results.

    Each cache entry is stored as a JSONL line:
        {"key": "<model>:<config_fp>:<sha256>", "result": {...}}

    The in-memory dict avoids O(n²) file reads during batch processing.
    Failed API results are never stored, so retries stay possible.
    """

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        if cache_dir is None:
            cache_dir = Path(__file__).resolve().parents[2] / "data" / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._loaded: dict[str, dict[str, dict[str, Any]]] = {}

    def _cache_path(self, model_version: str) -> Path:
        safe = model_version.replace("/", "_").replace(" ", "_")
        return self.cache_dir / f"classify_{safe}.jsonl"

    def _make_key(
        self,
        model_version: str,
        text: str,
        *,
        config_fp: str = "",
    ) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
        if config_fp:
            return f"{model_version}:{config_fp}:{digest}"
        return f"{model_version}:{digest}"

    def _ensure_loaded(self, model_version: str) -> dict[str, dict[str, Any]]:
        """Load cache into memory once per model version."""
        if model_version in self._loaded:
            return self._loaded[model_version]
        cache_path = self._cache_path(model_version)
        if not cache_path.is_file():
            self._loaded[model_version] = {}
            return self._loaded[model_version]
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

    def get(
        self,
        model_version: str,
        text: str,
        *,
        config_fp: str = "",
    ) -> dict[str, Any] | None:
        """Return cached successful result or None (O(1) after first load)."""
        loaded = self._ensure_loaded(model_version)
        result = loaded.get(self._make_key(model_version, text, config_fp=config_fp))
        if result is None:
            return None
        if result.get("success") is False:
            return None
        return result

    def put(
        self,
        model_version: str,
        text: str,
        result: dict[str, Any],
        *,
        config_fp: str = "",
    ) -> None:
        """Store a successful classification result (disk + memory)."""
        if result.get("success") is False:
            return
        key = self._make_key(model_version, text, config_fp=config_fp)
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
    """Track which records have been successfully processed in a batch run.

    Only successful post_ids are stored so failed calls remain retryable.
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
