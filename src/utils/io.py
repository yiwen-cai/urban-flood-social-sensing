"""
JSON Lines 读写工具 —— 全组共用。

用法:
    from src.utils.io import load_jsonl, save_jsonl
    posts = load_jsonl("data/processed/posts_clean.jsonl")
    save_jsonl(posts, "data/processed/posts_clean.jsonl")
"""

import json
from pathlib import Path
from typing import Any


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """从 JSON Lines 文件读取所有记录。"""
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
                print(f"[WARNING] 第 {line_num} 行 JSON 解析失败: {e}")
    return records


def save_jsonl(records: list[dict[str, Any]], path: str | Path) -> None:
    """将记录列表保存为 JSON Lines 文件。"""
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
