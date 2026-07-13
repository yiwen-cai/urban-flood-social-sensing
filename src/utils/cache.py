"""
批次缓存与断点续跑 —— Lab 2 分类专用。

用法:
    from src.utils.cache import CacheManager
    cm = CacheManager("data/cache")
    cached = cm.load_batch("batch_001")
    if cached:
        results = cached
    else:
        results = classify(...)
        cm.save_batch("batch_001", results)
"""

import json
from pathlib import Path
from typing import Any


class CacheManager:
    """管理 LLM 分类结果的批次缓存，支持断点续跑。"""

    def __init__(self, cache_dir: str | Path = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _batch_path(self, batch_id: str) -> Path:
        return self.cache_dir / f"{batch_id}.json"

    def _state_path(self) -> Path:
        return self.cache_dir / "_state.json"

    def has_batch(self, batch_id: str) -> bool:
        return self._batch_path(batch_id).exists()

    def load_batch(self, batch_id: str) -> list[dict[str, Any]] | None:
        """加载已缓存的批次结果。不存在返回 None。"""
        path = self._batch_path(batch_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_batch(self, batch_id: str, results: list[dict[str, Any]]) -> None:
        """保存批次结果到缓存。"""
        with open(self._batch_path(batch_id), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    def save_state(self, state: dict[str, Any]) -> None:
        """保存断点续跑状态（已完成批次、总数等）。"""
        with open(self._state_path(), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self) -> dict[str, Any]:
        """加载断点续跑状态。"""
        path = self._state_path()
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_pending_batches(
        self, total_batches: int, prefix: str = "batch_"
    ) -> list[str]:
        """返回尚未缓存的批次 ID 列表。"""
        all_batches = [f"{prefix}{i:04d}" for i in range(total_batches)]
        return [b for b in all_batches if not self.has_batch(b)]
