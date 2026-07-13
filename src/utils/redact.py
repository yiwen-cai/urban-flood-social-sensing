"""
敏感信息脱敏 —— Lab 1 数据清洗专用。

用法:
    from src.utils.redact import redact_text, audit_pii
    cleaned, hit_count = redact_text(raw_text)
"""

import re
from typing import Any

# ====== 脱敏规则 ======
# 每个规则 (pattern, replacement, description)

_RULES: list[tuple[str, str, str]] = [
    # 手机号（中国大陆）
    (r"1[3-9]\d{9}", "[手机号已屏蔽]", "手机号"),
    # 身份证号（18 位）
    (r"\d{6}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]",
     "[身份证号已屏蔽]", "身份证号"),
    # 微博 @用户名
    (r"@[\w一-鿿\-]{2,20}", "[用户已匿名]", "微博用户"),
    # 精确住宅地址（XX路XX号XX室、XX小区XX栋XX单元XX号 等模式，保留区县名）
    (r"[一-鿿]{2,6}(?:路|街|大道|巷)(?:\d{1,4}号)(?:\d{1,3}(?:栋|幢|楼|单元|室)){1,3}",
     "[详细地址已屏蔽]", "精确住址"),
    # 小区栋号模式
    (r"[一-鿿]{2,10}(?:小区|花园|苑|公寓)\d{1,3}(?:栋|幢|号楼)\d{1,4}(?:单元)?\d{1,4}(?:室|号)?",
     "[详细住址已屏蔽]", "精确住址"),
    # QQ 号
    (r"[Qq]{2}[:：]\s*\d{5,12}", "[QQ号已屏蔽]", "QQ号"),
    # 电子邮箱
    (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
     "[邮箱已屏蔽]", "邮箱"),
]


def redact_text(text: str) -> tuple[str, dict[str, int]]:
    """
    对文本执行 PII 脱敏。
    返回 (脱敏后文本, {"手机号": 命中次数, ...})
    """
    hits: dict[str, int] = {}
    result = text

    for pattern, replacement, label in _RULES:
        before = result
        result = re.sub(pattern, replacement, result)
        count = len(re.findall(pattern, before))
        if count > 0:
            hits[label] = hits.get(label, 0) + count

    return result, hits


def audit_pii(texts: list[str]) -> dict[str, Any]:
    """
    对一批文本进行 PII 命中统计。
    返回 {"total_hits": N, "by_type": {...}, "affected_count": N, "sample_hits": [...]}
    """
    all_hits: dict[str, int] = {}
    affected = 0
    samples: list[dict[str, Any]] = []

    for i, text in enumerate(texts):
        _, hits = redact_text(text)
        if hits:
            affected += 1
            for label, count in hits.items():
                all_hits[label] = all_hits.get(label, 0) + count
            if len(samples) < 5:
                samples.append({"index": i, "hits": hits, "text_preview": text[:100]})

    return {
        "total_hits": sum(all_hits.values()),
        "by_type": all_hits,
        "affected_count": affected,
        "total_count": len(texts),
        "sample_hits": samples,
    }
