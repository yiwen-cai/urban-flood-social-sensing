"""
JSONL Schema 校验工具 —— 每个模块入口处校验输入格式。

用法:
    from src.utils.schema import validate_posts_clean, validate_posts_labeled
    posts = load_jsonl("data/processed/posts_clean.jsonl")
    validate_posts_clean(posts)  # 不合法会报错
"""

from typing import Any


def validate_posts_clean(records: list[dict[str, Any]]) -> None:
    """校验 posts_clean.jsonl 格式（Lab 1 输出 / Lab 2 输入）。"""
    if not records:
        raise ValueError("数据为空")

    required = ["post_id", "text_raw", "text_clean", "timestamp", "location", "source"]
    errors = []

    for i, rec in enumerate(records):
        for field in required:
            if field not in rec:
                errors.append(f"第 {i+1} 条记录缺少必填字段: {field}")

        loc = rec.get("location", {})
        if not isinstance(loc, dict):
            errors.append(f"第 {i+1} 条记录 location 不是对象")
        else:
            for f in ["city", "district", "address", "lat", "lng"]:
                if f not in loc:
                    errors.append(f"第 {i+1} 条记录 location 缺少字段: {f}")

    if errors:
        raise ValueError(f"Schema 校验失败 ({len(errors)} 个错误):\n" + "\n".join(errors[:20]))

    print(f"[OK] posts_clean 校验通过，共 {len(records)} 条记录")


def validate_posts_labeled(records: list[dict[str, Any]]) -> None:
    """校验 posts_labeled.jsonl 格式（Lab 2 输出 / Lab 3 输入）。"""
    if not records:
        raise ValueError("数据为空")

    # 先校验基础字段
    validate_posts_clean(records)

    errors = []
    for i, rec in enumerate(records):
        lab2 = rec.get("_lab2")
        if not isinstance(lab2, dict):
            errors.append(f"第 {i+1} 条记录缺少 _lab2 字段")
            continue

        sentiment = lab2.get("sentiment", {})
        if not isinstance(sentiment, dict) or "primary" not in sentiment:
            errors.append(f"第 {i+1} 条记录 _lab2.sentiment.primary 缺失")

        info_type = lab2.get("information_type", {})
        if not isinstance(info_type, dict) or "primary" not in info_type:
            errors.append(f"第 {i+1} 条记录 _lab2.information_type.primary 缺失")

    if errors:
        raise ValueError(f"Schema 校验失败 ({len(errors)} 个错误):\n" + "\n".join(errors[:20]))

    print(f"[OK] posts_labeled 校验通过，共 {len(records)} 条记录")
