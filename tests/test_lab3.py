"""Lab 3 / D07 unit and contract integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from src.lab3_decision.build_evidence import (
    build_d07,
    compute_metrics,
    extract_evidence,
)
from src.lab3_decision.generate_briefing import select_model
from src.lab2_analysis.aggregate import build_metrics as aggregate_build_metrics

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture
def fixture_posts():
    return _load_jsonl(FIXTURES / "sample_posts.jsonl")


@pytest.fixture
def fixture_predictions():
    return _load_jsonl(FIXTURES / "sample_predictions.jsonl")


class TestD07UnifiedWriter:
    def test_fixture_metrics_match_schema(self, fixture_posts, fixture_predictions):
        metrics = compute_metrics(fixture_posts, fixture_predictions)
        _validator("metrics.schema.json").validate(metrics)
        assert metrics["unique_posts"] == 20
        assert "fixture-v1" in metrics["model_versions"]

    def test_aggregate_wrapper_matches_build_evidence(
        self, fixture_posts, fixture_predictions
    ):
        a = aggregate_build_metrics(fixture_posts, fixture_predictions)
        b = compute_metrics(fixture_posts, fixture_predictions)
        assert a["unique_posts"] == b["unique_posts"]
        assert a["model_versions"] == b["model_versions"]
        assert a["metrics_version"] == b["metrics_version"] == "2.0.0"

    def test_synthetic_evidence_includes_text(
        self, fixture_posts, fixture_predictions, tmp_path
    ):
        evidence = extract_evidence(
            fixture_posts,
            fixture_predictions,
            model_version="fixture-v1",
            include_text=True,
        )
        assert evidence
        assert any(e["selection_reason"].startswith("urgent") for e in evidence)
        for row in evidence:
            _validator("evidence.schema.json").validate(row)
            if row["source"] == "synthetic_fixture":
                assert isinstance(row["text_clean"], str)

    def test_real_mode_evidence_omits_text(self, fixture_posts, fixture_predictions):
        posts = []
        for row in fixture_posts:
            cloned = dict(row)
            cloned["source"] = "humaid_events"
            posts.append(cloned)
        evidence = extract_evidence(
            posts,
            fixture_predictions,
            model_version="fixture-v1",
            include_text=False,
        )
        for row in evidence:
            assert row["text_clean"] is None
            _validator("evidence.schema.json").validate(row)

    def test_partial_model_failure_still_builds(self, fixture_posts):
        predictions = [
            {
                "schema_version": "1.0.0",
                "pipeline_run_id": "t",
                "post_id": fixture_posts[0]["post_id"],
                "model_version": "only-model",
                "predicted_label": None,
                "model_scores": {},
                "status": "error",
                "error_message": "timeout",
                "confidence": None,
            }
        ]
        metrics = compute_metrics(fixture_posts, predictions)
        assert metrics["per_model"]["only-model"]["coverage"] == 0.0
        assert metrics["per_model"]["only-model"]["n_errors"] >= 1

    def test_missing_emotion_and_single_model_ok(self, fixture_posts, tmp_path):
        posts = []
        for row in fixture_posts:
            cloned = dict(row)
            lab2 = dict(cloned["_lab2"])
            lab2["exploratory_emotion"] = None
            cloned["_lab2"] = lab2
            posts.append(cloned)
        predictions = [
            {
                "schema_version": "1.0.0",
                "pipeline_run_id": "t",
                "post_id": p["post_id"],
                "model_version": "solo",
                "predicted_label": p["_lab2"]["reference_label"],
                "model_scores": {p["_lab2"]["reference_label"]: 0.9},
                "status": "ok",
                "error_message": None,
                "confidence": 0.9,
            }
            for p in posts
        ]
        metrics_path = tmp_path / "metrics.json"
        evidence_path = tmp_path / "evidence.jsonl"
        posts_path = tmp_path / "posts.jsonl"
        preds_path = tmp_path / "preds.jsonl"
        posts_path.write_text(
            "\n".join(json.dumps(p, ensure_ascii=False) for p in posts) + "\n",
            encoding="utf-8",
        )
        preds_path.write_text(
            "\n".join(json.dumps(p, ensure_ascii=False) for p in predictions) + "\n",
            encoding="utf-8",
        )
        metrics, evidence = build_d07(
            posts_path,
            preds_path,
            metrics_output=metrics_path,
            evidence_output=evidence_path,
        )
        assert metrics["records_with_emotion"] == 0
        assert metrics["model_versions"] == ["solo"]
        assert evidence_path.is_file()
        assert select_model(metrics, None) == "solo"


class TestBriefingDynamic:
    def test_select_model_prefers_deepseek(self):
        metrics = {
            "model_versions": ["tfidf-lr-baseline-v1", "deepseek-v4-flash"],
            "per_model": {},
        }
        assert select_model(metrics, None) == "deepseek-v4-flash"
        assert select_model(metrics, "tfidf-lr-baseline-v1") == "tfidf-lr-baseline-v1"

    def test_select_model_prefers_higher_coverage_fixture(self):
        metrics = {
            "model_versions": ["fixture-baseline-v1", "fixture-v1"],
            "per_model": {
                "fixture-baseline-v1": {"coverage": 0.15, "accuracy": 0.0},
                "fixture-v1": {"coverage": 1.0, "accuracy": 1.0},
            },
        }
        assert select_model(metrics, None) == "fixture-v1"
