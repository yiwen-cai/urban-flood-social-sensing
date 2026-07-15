"""Contract tests for post/prediction/D07 schemas and tip privacy bounds."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
FIXTURES = ROOT / "tests" / "fixtures"

REAL_SOURCE_MARKERS = (
    '"source": "humaid_events"',
    '"source":"humaid_events"',
)


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


class ContractFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.post_v = _validator("post.schema.json")
        cls.pred_v = _validator("prediction.schema.json")
        cls.metrics_v = _validator("metrics.schema.json")
        cls.evidence_v = _validator("evidence.schema.json")
        cls.posts = _load_jsonl(FIXTURES / "sample_posts.jsonl")
        cls.preds = _load_jsonl(FIXTURES / "sample_predictions.jsonl")
        cls.metrics = json.loads((FIXTURES / "sample_metrics.json").read_text(encoding="utf-8"))
        cls.evidence = _load_jsonl(FIXTURES / "sample_evidence.jsonl")

    def test_posts_validate_and_are_one_row_per_post(self) -> None:
        self.assertEqual(len(self.posts), 20)
        ids = [row["post_id"] for row in self.posts]
        self.assertEqual(len(ids), len(set(ids)))
        for row in self.posts:
            self.post_v.validate(row)
            lab2 = row["_lab2"]
            self.assertNotIn("predicted_label", lab2)
            self.assertNotIn("model_scores", lab2)
            self.assertNotIn("model_version", lab2)

    def test_predictions_unique_on_post_id_model_version(self) -> None:
        keys = [(row["post_id"], row["model_version"]) for row in self.preds]
        self.assertEqual(len(keys), len(set(keys)))
        for row in self.preds:
            self.pred_v.validate(row)

    def test_metrics_and_evidence_fixtures_match_d07_schemas(self) -> None:
        self.metrics_v.validate(self.metrics)
        self.assertEqual(self.metrics["unique_posts"], 20)
        for row in self.evidence:
            self.evidence_v.validate(row)

    def test_evidence_privacy_boundary(self) -> None:
        for row in self.evidence:
            if row["source"] == "humaid_events":
                if row["text_clean"] is not None:
                    self.assertIsInstance(row["text_clean"], str)
            else:
                self.assertIsInstance(row["text_clean"], str)
                self.assertTrue(row["text_clean"].startswith("Synthetic"))

    def test_real_mode_evidence_allows_redacted_text(self) -> None:
        allowed = {
            "evidence_version": "1.0.0",
            "post_id": "x",
            "model_version": "m",
            "source": "humaid_events",
            "source_ref": "humaid_events:test:1",
            "predicted_label": "not_humanitarian",
            "reference_label": "not_humanitarian",
            "selection_reason": "local dashboard redacted body",
            "confidence": 0.5,
            "text_clean": "Residents should avoid flooded roads per [USER] guidance.",
            "exploratory_emotion": None,
        }
        self.evidence_v.validate(allowed)

    def test_duplicate_prediction_key_is_detectable(self) -> None:
        keys = [(row["post_id"], row["model_version"]) for row in self.preds]
        dup = keys + [keys[0]]
        self.assertNotEqual(len(dup), len(set(dup)))


class TrackedTreePrivacyTest(unittest.TestCase):
    def test_gitignore_keeps_sensitive_data_dirs_ignored(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (
            "data/analyzed/*",
            "!data/analyzed/.gitkeep",
            "data/output/*",
            "!data/output/.gitkeep",
            "data/seed/*",
            "!data/seed/.gitkeep",
        ):
            self.assertIn(pattern, gitignore)

    def test_gitkeep_placeholders_exist(self) -> None:
        for rel in ("data/analyzed/.gitkeep", "data/output/.gitkeep", "data/seed/.gitkeep"):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_tracked_tree_has_no_real_source_text_products(self) -> None:
        listed = subprocess.check_output(
            ["git", "ls-files", "data/analyzed", "data/output", "data/seed"],
            cwd=ROOT,
            text=True,
        ).splitlines()
        allowed = {
            "data/analyzed/.gitkeep",
            "data/output/.gitkeep",
            "data/output/metrics.public.json",
            "data/seed/.gitkeep",
        }
        self.assertEqual(set(listed), allowed)

        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
        tracked_paths = [p.decode("utf-8", errors="replace") for p in tracked if p]
        for path in tracked_paths:
            if path.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".mp4")):
                continue
            full = ROOT / path
            if not full.is_file():
                continue
            # Skip binary-ish and lockfiles with huge content if needed
            try:
                text = full.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if path.startswith("data/") and any(marker in text for marker in REAL_SOURCE_MARKERS):
                self.fail(f"tracked data path still contains real source marker: {path}")
            if path.startswith("data/") and path.endswith(".jsonl"):
                self.fail(f"tracked data jsonl is forbidden at tip: {path}")

    def test_public_metrics_are_schema_valid_and_body_free(self) -> None:
        path = ROOT / "data" / "output" / "metrics.public.json"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("text_clean", text)
        _validator("metrics.schema.json").validate(json.loads(text))


class DualWriterContractTest(unittest.TestCase):
    """Forbid Lab2/Lab3 writing incompatible shapes to the same D07 paths."""

    def test_shared_output_paths(self) -> None:
        from src.lab2_analysis import aggregate

        self.assertEqual(
            aggregate.DEFAULT_METRICS,
            ROOT / "data" / "output" / "metrics.json",
        )
        self.assertEqual(
            aggregate.DEFAULT_EVIDENCE,
            ROOT / "data" / "output" / "evidence.jsonl",
        )

        be_src = (ROOT / "src" / "lab3_decision" / "build_evidence.py").read_text(encoding="utf-8")
        self.assertIn("metrics.json", be_src)
        self.assertIn("evidence.jsonl", be_src)
        self.assertIn('data" / "output"', be_src.replace("'", '"'))

    def test_legacy_lab2_and_lab3_shapes_fail_frozen_schema(self) -> None:
        metrics_v = _validator("metrics.schema.json")
        evidence_v = _validator("evidence.schema.json")

        legacy_lab2_metrics = {
            "metrics_version": "1.0.0",
            "total_records": 3164,
            "records_with_reference_label": 3164,
            "records_with_prediction": 3014,
            "records_with_emotion": 0,
            "error_records": 150,
            "model_versions": ["a", "b"],
            "reference_label_distribution": {},
            "predicted_label_distribution": {},
            "emotion_distribution": {},
            "evidence_status_distribution": {},
            "generated_at": "x",
        }
        with self.assertRaises(ValidationError):
            metrics_v.validate(legacy_lab2_metrics)

        legacy_lab3_metrics = {
            "total_records": 20,
            "correct_predictions": 10,
            "accuracy": 0.5,
            "category_distribution": {},
            "predicted_distribution": {},
            "per_class_stats": {},
            "emotion_distribution": {},
            "evidence_status_distribution": {},
            "data_quality": {},
        }
        with self.assertRaises(ValidationError):
            metrics_v.validate(legacy_lab3_metrics)

        legacy_lab2_evidence = {
            "post_id": "x",
            "source_ref": "y",
            "reference_label": "not_humanitarian",
            "predicted_label": "not_humanitarian",
            "evidence_status": "dataset_record",
            "text_clean": "body",
            "is_correct_prediction": True,
        }
        with self.assertRaises(ValidationError):
            evidence_v.validate(legacy_lab2_evidence)

        legacy_lab3_evidence = {
            "source_ref": "y",
            "text_clean": "body",
            "predicted_label": "not_humanitarian",
            "reference_label": "not_humanitarian",
            "exploratory_emotion": None,
            "evidence_status": "dataset_record",
            "confidence": 0.9,
            "selection_reason": "top-3",
        }
        with self.assertRaises(ValidationError):
            evidence_v.validate(legacy_lab3_evidence)

    def test_only_one_metrics_and_evidence_schema_file(self) -> None:
        metrics_schemas = list(SCHEMAS.glob("*metrics*.json"))
        evidence_schemas = list(SCHEMAS.glob("*evidence*.json"))
        self.assertEqual([p.name for p in metrics_schemas], ["metrics.schema.json"])
        self.assertEqual([p.name for p in evidence_schemas], ["evidence.schema.json"])


class EnvExampleTest(unittest.TestCase):
    def test_env_example_restored_with_residual_history_warning(self) -> None:
        path = ROOT / ".env.example"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("DEEPSEEK_API_KEY=", text)
        self.assertIn("history was NOT rewritten", text)
        self.assertIn("residual exposure", text.lower())


if __name__ == "__main__":
    unittest.main()
