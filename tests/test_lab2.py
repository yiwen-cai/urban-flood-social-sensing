"""Unit tests for Lab 2 core functions — merge_reference_labels,
sample_stratified, and redact_text (as requested in PR review).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.utils.redact import redact_text
from src.lab2_analysis.classify import merge_reference_labels
from src.lab2_analysis.annotate_seed import sample_stratified, EMOTION_LABELS


# ====================================================================
# redact_text
# ====================================================================

class TestRedactText:
    def test_handle_redaction(self):
        assert redact_text("Hello @user123 how are you?") == "Hello [USER] how are you?"

    def test_email_redaction(self):
        assert redact_text("Contact test@example.com for help") == "Contact [EMAIL] for help"

    def test_url_redaction(self):
        assert redact_text("Visit https://example.com/page now") == "Visit [URL] now"

    def test_long_number_redaction(self):
        assert redact_text("Call 9876543210 for rescue") == "Call [NUMBER] for rescue"

    def test_order_prevents_double_redaction(self):
        """Email containing digits must not have its digits double-redacted."""
        text = "Email user123@test.com for info"
        result = redact_text(text)
        assert "[EMAIL]" in result
        assert "[NUMBER]" not in result  # digits in email not separately redacted

    def test_no_false_positive_on_short_numbers(self):
        result = redact_text("The year 2026 was wet; total 50000 affected.")
        assert "[NUMBER]" not in result  # not 10-12 digits

    def test_plain_text_unchanged(self):
        assert redact_text("The flood damaged several roads.") == "The flood damaged several roads."

    def test_multiple_patterns(self):
        text = "@help Please donate at https://site.org or call 9876543210"
        result = redact_text(text)
        assert "[USER]" in result
        assert "[URL]" in result
        assert "[NUMBER]" in result


# ====================================================================
# merge_reference_labels
# ====================================================================

class TestMergeReferenceLabels:
    @staticmethod
    def _make_test_json(tweet_id: str, label: str) -> str:
        """Create a minimal test.json."""
        return json.dumps([
            {"tweet_id": tweet_id, "tweet_text": "dummy", "class_label": label},
        ])

    def test_match_with_split_prefix(self):
        """post_id format 'test:123' should match tweet_id '123'."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write(self._make_test_json("1032436206313725953", "requests_or_urgent_needs"))
            test_path = f.name

        records = [{
            "post_id": "test:1032436206313725953",
            "text_clean": "help needed",
            "_lab2": {
                "reference_label": None,
                "predicted_label": "rescue_volunteering_or_donation_effort",
                "model_scores": {},
                "exploratory_emotion": None,
                "evidence_status": "model_prediction",
                "model_version": "test-v1",
            },
        }]
        merged = merge_reference_labels(records, test_path=Path(test_path))
        assert merged[0]["_lab2"]["reference_label"] == "requests_or_urgent_needs"
        assert merged[0]["_lab2"]["evidence_status"] == "dataset_record"
        Path(test_path).unlink(missing_ok=True)

    def test_match_without_prefix(self):
        """Plain tweet_id without split prefix."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write(self._make_test_json("123", "caution_and_advice"))
            test_path = f.name

        records = [{
            "post_id": "123",
            "_lab2": {
                "reference_label": None,
                "predicted_label": None,
                "model_scores": {},
                "exploratory_emotion": None,
                "evidence_status": "model_prediction",
                "model_version": "test-v1",
            },
        }]
        merged = merge_reference_labels(records, test_path=Path(test_path))
        assert merged[0]["_lab2"]["reference_label"] == "caution_and_advice"
        Path(test_path).unlink(missing_ok=True)

    def test_no_match_keeps_null(self):
        """Records not in test.json keep reference_label = None."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write(self._make_test_json("999", "not_humanitarian"))
            test_path = f.name

        records = [{
            "post_id": "test:111",
            "_lab2": {
                "reference_label": None,
                "predicted_label": "sympathy_and_support",
                "model_scores": {},
                "exploratory_emotion": None,
                "evidence_status": "model_prediction",
                "model_version": "test-v1",
            },
        }]
        merged = merge_reference_labels(records, test_path=Path(test_path))
        assert merged[0]["_lab2"]["reference_label"] is None
        Path(test_path).unlink(missing_ok=True)

    def test_all_nine_labels_covered(self):
        """All 9 labels in the test set should be matched."""
        import tempfile
        entries = [
            {"tweet_id": str(i), "tweet_text": "x", "class_label": lbl}
            for i, lbl in enumerate([
                "caution_and_advice",
                "displaced_people_and_evacuations",
                "infrastructure_and_utility_damage",
                "injured_or_dead_people",
                "not_humanitarian",
                "other_relevant_information",
                "requests_or_urgent_needs",
                "rescue_volunteering_or_donation_effort",
                "sympathy_and_support",
            ])
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(entries, f)
            test_path = f.name

        records = [{
            "post_id": f"test:{i}",
            "_lab2": {
                "reference_label": None,
                "predicted_label": None,
                "model_scores": {},
                "exploratory_emotion": None,
                "evidence_status": "model_prediction",
                "model_version": "test-v1",
            },
        } for i in range(9)]
        merged = merge_reference_labels(records, test_path=Path(test_path))
        labels = {r["_lab2"]["reference_label"] for r in merged}
        assert len(labels) == 9
        Path(test_path).unlink(missing_ok=True)


# ====================================================================
# sample_stratified
# ====================================================================

class TestSampleStratified:
    @pytest.fixture
    def mock_records(self):
        """Create 100 records across 3 labels."""
        records = []
        for i in range(50):
            records.append({"tweet_id": f"a{i}", "tweet_text": f"text {i}", "class_label": "label_a"})
        for i in range(30):
            records.append({"tweet_id": f"b{i}", "tweet_text": f"text {i}", "class_label": "label_b"})
        for i in range(20):
            records.append({"tweet_id": f"c{i}", "tweet_text": f"text {i}", "class_label": "label_c"})
        return records

    def test_every_class_represented(self, mock_records):
        sample = sample_stratified(mock_records, n_total=10, random_seed=42)
        labels = {r["class_label"] for r in sample}
        assert labels == {"label_a", "label_b", "label_c"}

    def test_respects_n_total(self, mock_records):
        sample = sample_stratified(mock_records, n_total=6, random_seed=42)
        assert len(sample) <= 6 + 3  # n_total + up to n_classes extra from rounding

    def test_minimum_one_per_class(self, mock_records):
        sample = sample_stratified(mock_records, n_total=3, random_seed=42)
        from collections import Counter
        counts = Counter(r["class_label"] for r in sample)
        for lbl in ["label_a", "label_b", "label_c"]:
            assert counts[lbl] >= 1

    def test_seed_reproducibility(self, mock_records):
        s1 = sample_stratified(mock_records, n_total=10, random_seed=42)
        s2 = sample_stratified(mock_records, n_total=10, random_seed=42)
        assert [r["tweet_id"] for r in s1] == [r["tweet_id"] for r in s2]

    def test_empty_input(self):
        assert sample_stratified([], n_total=5) == []
