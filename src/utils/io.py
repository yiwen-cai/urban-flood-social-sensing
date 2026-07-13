"""
JSON Lines 读写——全组共用。

用法:
    from src.utils.io import load_jsonl, save_jsonl
    posts = load_jsonl("data/processed/posts_clean.jsonl")
    save_jsonl(posts, "data/processed/posts_clean.jsonl")
"""

import json
import hashlib
from pathlib import Path
from typing import Any


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """从 JSON Lines 文件读取所有记录。空行自动跳过。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"第 {line_num} 行 JSON 解析失败: {e}") from e
    return records


def save_jsonl(records: list[dict[str, Any]], path: str | Path) -> None:
    """将记录列表保存为 UTF-8 JSON Lines 文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def count_records(path: str | Path) -> int:
    """快速统计 JSONL 文件行数（不含空行）。"""
    path = Path(path)
    if not path.exists():
        return 0
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def sha256_hex(path: str | Path) -> str:
    """计算文件的 SHA-256 校验和（16 进制字符串）。"""
    path = Path(path)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_run_consistency(paths: list[str | Path]) -> dict[str, Any]:
    """
    校验多个 JSONL 产物之间的 schema_version、pipeline_run_id 和记录数一致性。
    返回 {"ok": bool, "issues": [...]}
    """
    results: dict[str, Any] = {"ok": True, "issues": [], "counts": {}, "run_ids": {}, "versions": {}}

    for p in paths:
        p = Path(p)
        if not p.exists():
            results["ok"] = False
            results["issues"].append(f"文件缺失: {p}")
            continue
        records = load_jsonl(p)
        results["counts"][str(p)] = len(records)
        if records:
            results["versions"][str(p)] = records[0].get("schema_version")
            results["run_ids"][str(p)] = records[0].get("pipeline_run_id")

    # 检查 schema_version 是否一致
    unique_versions = set(v for v in results["versions"].values() if v)
    if len(unique_versions) > 1:
        results["ok"] = False
        results["issues"].append(f"schema_version 不一致: {results['versions']}")

    # 检查 pipeline_run_id 是否一致
    unique_runs = set(r for r in results["run_ids"].values() if r)
    if len(unique_runs) > 1:
        results["ok"] = False
        results["issues"].append(f"pipeline_run_id 不一致: {results['run_ids']}")

    return results
