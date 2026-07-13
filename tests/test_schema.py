"""
Schema 校验测试 —— 全组通用。

用法:
    python -m pytest tests/test_schema.py -v
"""

import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.utils.io import load_jsonl

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "post.schema.json"
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_posts.jsonl"


@pytest.fixture(scope="module")
def schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def fixture_records() -> list[dict]:
    return load_jsonl(FIXTURE_PATH)


# ====== Schema 文件存在性 ======

def test_schema_file_exists():
    assert SCHEMA_PATH.exists(), f"Schema 文件不存在: {SCHEMA_PATH}"


def test_fixture_file_exists():
    assert FIXTURE_PATH.exists(), f"Fixture 文件不存在: {FIXTURE_PATH}"


# ====== Fixture 基础 ======

def test_fixture_has_20_records(fixture_records):
    assert len(fixture_records) == 20, f"Fixture 应有 20 条记录，实际 {len(fixture_records)} 条"


def test_fixture_post_ids_unique(fixture_records):
    ids = [r["post_id"] for r in fixture_records]
    assert len(ids) == len(set(ids)), "post_id 不唯一"


def test_fixture_schema_version_consistent(fixture_records):
    versions = {r.get("schema_version") for r in fixture_records}
    assert versions == {"1.0.0"}, f"schema_version 不一致: {versions}"


# ====== 必填字段 ======

REQUIRED_FIELDS = [
    "schema_version", "pipeline_run_id", "post_id", "text_clean",
    "event_id", "source", "source_ref", "pii_redacted",
]


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_required_field_present(fixture_records, field):
    for i, rec in enumerate(fixture_records):
        assert field in rec, f"第 {i+1} 条记录缺少必填字段: {field}"


# ====== 类型检查 ======

def test_pii_redacted_is_boolean(fixture_records):
    for i, rec in enumerate(fixture_records):
        assert isinstance(rec["pii_redacted"], bool), f"第 {i+1} 条 pii_redacted 不是 bool"


def test_schema_version_is_string(fixture_records):
    for rec in fixture_records:
        assert isinstance(rec["schema_version"], str)


def test_event_id_consistent(fixture_records):
    events = {r["event_id"] for r in fixture_records}
    assert len(events) == 1, f"event_id 不一致: {events}"


# ===== 空值覆盖 =====

def test_fixture_covers_null_time(fixture_records):
    null_times = [r for r in fixture_records if r.get("time") is None]
    assert len(null_times) >= 1, "Fixture 必须包含 time 为 null 的记录"


def test_fixture_covers_null_location(fixture_records):
    null_locs = [r for r in fixture_records if r.get("location") is None]
    assert len(null_locs) >= 1, "Fixture 必须包含 location 为 null 的记录"


def test_fixture_covers_null_text_clean(fixture_records):
    null_texts = [r for r in fixture_records if r.get("text_clean") is None]
    assert len(null_texts) >= 1, "Fixture 必须包含 text_clean 为 null 的记录（空文本边界）"


def test_fixture_covers_non_zhengzhou_location(fixture_records):
    """至少有一条记录的 location.city 不是郑州，测试无关文本过滤"""
    non_zz = [
        r for r in fixture_records
        if r.get("location") and r["location"].get("city") != "郑州"
    ]
    assert len(non_zz) >= 1, "Fixture 必须包含非郑州地点记录"


# ====== _lab2 / _lab3 字段 ======

def test_fixture_lab2_lab3_null(fixture_records):
    """Lab 1 输出的 fixture 中 _lab2 和 _lab3 应为 null"""
    for i, rec in enumerate(fixture_records):
        assert rec.get("_lab2") is None, f"第 {i+1} 条 _lab2 应为 null（这是 Lab 1 fixture）"
        assert rec.get("_lab3") is None, f"第 {i+1} 条 _lab3 应为 null（这是 Lab 1 fixture）"


# ====== 证据状态枚举 ======

VALID_EVIDENCE_STATUS = {"dataset_record", "human_labeled", "model_prediction", "external_reference"}


def test_labeled_fixture_evidence_status():
    """
    如果存在有 _lab2 的 fixture 文件，逐条检查 evidence_status。
    这里只检查 sample_posts，它们都应该是 null，所以本测试总是通过。
    实际检查在 Lab 2 输出上运行。
    """
    # 此测试为占位——实际 evidence_status 校验在 Lab 2 产物上执行
    pass
