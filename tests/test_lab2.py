"""Unit tests for all Lab 2 modules.

Coverage: redact_text, io, cache, llm (constants/prompts), classify
(baseline, few-shot, merge), evaluate (metrics, model versions),
aggregate (metrics, evidence), annotate_seed (sample, export, iaa).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from collections import Counter

import pytest

# ====================================================================
# src/utils/redact.py
# ====================================================================

from src.utils.redact import redact_text


class TestRedactText:
    def test_handle_redaction(self):
        assert redact_text("Hello @user123 how are you?") == "Hello [USER] how are you?"

    def test_email_redaction(self):
        assert redact_text("Contact test@example.com for help") == "Contact [EMAIL] for help"

    def test_url_redaction_https(self):
        assert redact_text("Visit https://example.com/page now") == "Visit [URL] now"

    def test_url_redaction_www(self):
        assert redact_text("See www.example.com for details") == "See [URL] for details"

    def test_long_number_redaction(self):
        assert redact_text("Call 9876543210 for rescue") == "Call [NUMBER] for rescue"

    def test_order_prevents_double_redaction(self):
        """Email containing digits must not have its digits double-redacted."""
        result = redact_text("Email user123@test.com for info")
        assert "[EMAIL]" in result
        assert "[NUMBER]" not in result

    def test_no_false_positive_on_short_numbers(self):
        result = redact_text("The year 2026 was wet; total 50000 affected.")
        assert "[NUMBER]" not in result

    def test_no_false_positive_on_11_digit_border(self):
        """11-digit numbers should be caught, 9-digit should not."""
        assert "[NUMBER]" in redact_text("Call 12345678901 now")
        assert "[NUMBER]" not in redact_text("Call 123456789 now")

    def test_plain_text_unchanged(self):
        assert redact_text("The flood damaged several roads.") == "The flood damaged several roads."

    def test_multiple_patterns(self):
        text = "@help Please donate at https://site.org or call 9876543210"
        result = redact_text(text)
        assert "[USER]" in result
        assert "[URL]" in result
        assert "[NUMBER]" in result

    def test_empty_text(self):
        assert redact_text("") == ""


# ====================================================================
# src/utils/io.py
# ====================================================================

from src.utils import io
from src.utils.io import read_jsonl, write_jsonl, iter_jsonl


class TestIO:
    @pytest.fixture
    def tmp_jsonl(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"a":1}\n{"b":2}\n\n{"c":3}\n')
            path = f.name
        yield Path(path)
        Path(path).unlink(missing_ok=True)

    def test_read_jsonl_as_list(self, tmp_jsonl):
        records = list(read_jsonl(tmp_jsonl))
        assert len(records) == 3
        assert records[0] == {"a": 1}

    def test_iter_jsonl_lazy(self, tmp_jsonl):
        gen = iter_jsonl(tmp_jsonl)
        assert next(gen) == {"a": 1}
        assert next(gen) == {"b": 2}
        assert next(gen) == {"c": 3}

    def test_read_jsonl_iterator_exhausted(self, tmp_jsonl):
        """Verify caller must materialise the iterator."""
        it = read_jsonl(tmp_jsonl)
        first = next(it)
        assert first == {"a": 1}
        # rest still available
        rest = list(it)
        assert len(rest) == 2

    def test_write_jsonl_roundtrip(self, tmp_jsonl):
        records = list(read_jsonl(tmp_jsonl))
        out = tmp_jsonl.parent / "test_write.jsonl"
        write_jsonl(out, records)
        back = list(read_jsonl(out))
        assert back == records
        out.unlink()

    def test_write_jsonl_overwrites(self, tmp_jsonl):
        out = tmp_jsonl.parent / "test_overwrite.jsonl"
        write_jsonl(out, [{"x": 1}])
        write_jsonl(out, [{"x": 2}])  # default overwrite=True
        back = list(read_jsonl(out))
        assert back == [{"x": 2}]
        out.unlink()

    def test_count_records(self, tmp_jsonl):
        assert io.count_records(tmp_jsonl) == 3

    def test_count_records_missing(self):
        assert io.count_records(Path("/tmp/nonexistent_lab2_test.jsonl")) == 0

    def test_load_raw_humaid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([
                {"tweet_id": "1", "tweet_text": "hello", "class_label": "not_humanitarian"},
                {"tweet_id": "2", "tweet_text": "world", "class_label": "sympathy_and_support"},
            ], f)
            path = f.name
        rows = io.load_raw_humaid(Path(path))
        assert len(rows) == 2
        assert rows[0]["tweet_id"] == "1"
        Path(path).unlink()

    def test_load_raw_humaid_rejects_non_array(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"not": "array"}, f)
            path = f.name
        with pytest.raises(ValueError, match="Expected a JSON array"):
            io.load_raw_humaid(Path(path))
        Path(path).unlink()

    def test_append_jsonl(self, tmp_jsonl):
        out = tmp_jsonl.parent / "test_append.jsonl"
        io.append_jsonl(out, [{"x": 1}])
        io.append_jsonl(out, [{"x": 2}, {"x": 3}])
        back = list(read_jsonl(out))
        assert back == [{"x": 1}, {"x": 2}, {"x": 3}]
        out.unlink()


# ====================================================================
# src/utils/cache.py
# ====================================================================

from src.utils.cache import ClassificationCache, Checkpoint


class TestClassificationCache:
    @pytest.fixture
    def cache(self, tmp_path):
        return ClassificationCache(tmp_path / "cache")

    def test_put_and_get(self, cache):
        cache.put(
            "test-model",
            "hello world",
            {"success": True, "label": "caution_and_advice", "confidence": 0.95},
        )
        result = cache.get("test-model", "hello world")
        assert result is not None
        assert result["label"] == "caution_and_advice"

    def test_get_miss_returns_none(self, cache):
        assert cache.get("test-model", "never seen") is None

    def test_same_text_same_key(self, cache):
        """Identical text + model produce identical cache key."""
        cache.put("m", "flood", {"success": True, "x": 1})
        assert cache.get("m", "flood") == {"success": True, "x": 1}

    def test_different_models_separate(self, cache):
        cache.put("baseline", "flood", {"success": True, "label": "A"})
        cache.put("llm", "flood", {"success": True, "label": "B"})
        assert cache.get("baseline", "flood")["label"] == "A"
        assert cache.get("llm", "flood")["label"] == "B"

    def test_config_fingerprint_invalidates_cache(self, cache):
        cache.put("m", "flood", {"success": True, "label": "A"}, config_fp="fp1")
        assert cache.get("m", "flood", config_fp="fp1")["label"] == "A"
        assert cache.get("m", "flood", config_fp="fp2") is None

    def test_failures_are_not_cached(self, cache):
        cache.put("m", "flood", {"success": False, "error": "timeout"})
        assert cache.get("m", "flood") is None
        assert cache.load_all("m") == {}

    def test_load_all(self, cache):
        cache.put("m", "a", {"success": True, "x": 1})
        cache.put("m", "b", {"success": True, "x": 2})
        all_entries = cache.load_all("m")
        assert len(all_entries) == 2

    def test_stats(self, cache):
        cache.put("m", "a", {"success": True, "label": "X"})
        cache.put("m", "b", {"success": True, "label": "Y"})
        s = cache.stats("m")
        assert s["cached_entries"] == 2
        assert s["success_count"] == 2

    def test_put_updates_memory(self, cache):
        """After put, get must return from memory without re-reading file."""
        cache.put("m", "text", {"success": True, "label": "X"})
        result = cache.get("m", "text")
        assert result == {"success": True, "label": "X"}

    def test_persistence_across_instances(self, tmp_path):
        """Cache entries survive re-instantiation (disk-backed)."""
        d = tmp_path / "cache2"
        c1 = ClassificationCache(d)
        c1.put("m", "text", {"success": True, "label": "X"})

        c2 = ClassificationCache(d)
        assert c2.get("m", "text") == {"success": True, "label": "X"}


class TestCheckpoint:
    @pytest.fixture
    def cp_path(self, tmp_path):
        return tmp_path / "checkpoint.txt"

    def test_new_checkpoint_empty(self, cp_path):
        cp = Checkpoint(cp_path)
        assert cp.load() == set()

    def test_mark_done_and_is_done(self, cp_path):
        cp = Checkpoint(cp_path)
        cp.mark_done("post-1")
        assert cp.is_done("post-1")
        assert not cp.is_done("post-2")

    def test_mark_done_batch(self, cp_path):
        cp = Checkpoint(cp_path)
        cp.mark_done_batch(["a", "b", "c"])
        assert cp.is_done("a") and cp.is_done("b") and cp.is_done("c")

    def test_remaining(self, cp_path):
        cp = Checkpoint(cp_path)
        cp.mark_done("a")
        assert cp.remaining(["a", "b", "c"]) == ["b", "c"]

    def test_persistence(self, cp_path):
        cp1 = Checkpoint(cp_path)
        cp1.mark_done("x")

        cp2 = Checkpoint(cp_path)
        assert cp2.load() == {"x"}
        assert cp2.is_done("x")

    def test_failures_are_not_marked_done_by_convention(self, cp_path):
        """Checkpoint only stores successes; failures remain retryable."""
        cp = Checkpoint(cp_path)
        # Simulate success-only marking used by classify_batch
        cp.mark_done("ok-1")
        assert cp.is_done("ok-1")
        assert not cp.is_done("failed-1")


# ====================================================================
# src/utils/llm.py  (constants / schema / smoke-test structure)
# ====================================================================

class TestLLMConstants:
    """Verify label inventories across code, schema, and config are consistent."""

    def test_classification_schema_has_nine_labels(self):
        from src.utils.llm import CLASSIFICATION_JSON_SCHEMA
        labels = CLASSIFICATION_JSON_SCHEMA["schema"]["properties"]["label"]["enum"]
        assert len(labels) == 9
        assert "requests_or_urgent_needs" in labels

    def test_system_prompt_mentions_nine_categories(self):
        from src.utils.llm import SYSTEM_PROMPT
        assert "nine" in SYSTEM_PROMPT.lower()

    def test_few_shot_template_contains_all_labels(self):
        from src.utils.llm import FEW_SHOT_TEMPLATE
        for lbl in [
            "caution_and_advice",
            "requests_or_urgent_needs",
            "sympathy_and_support",
            "not_humanitarian",
        ]:
            assert lbl in FEW_SHOT_TEMPLATE

    def test_env_defaults(self):
        import os
        from src.utils import llm
        assert llm.DEEPSEEK_MODEL == os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        assert llm.DEEPSEEK_BASE_URL == os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    def test_retry_config(self):
        from src.utils.llm import MAX_RETRIES, RETRY_BACKOFF_BASE, RETRYABLE_HTTP_CODES
        assert MAX_RETRIES == 3
        assert RETRY_BACKOFF_BASE == 2.0
        assert 429 in RETRYABLE_HTTP_CODES
        assert 500 in RETRYABLE_HTTP_CODES


# ====================================================================
# src/lab2_analysis/classify.py
# ====================================================================

from src.lab2_analysis.classify import (
    train_baseline,
    BaselineClassifier,
    select_few_shot_examples,
    save_few_shot_examples,
    load_few_shot_examples,
    merge_reference_labels,
    ALL_LABELS,
    TRAIN_PATH,
    DEV_PATH,
)

requires_humaid_raw = pytest.mark.skipif(
    not TRAIN_PATH.is_file() or not DEV_PATH.is_file(),
    reason="HumAID raw train/dev JSON not present locally",
)


class TestBaselineClassifier:
    @pytest.fixture
    def small_train(self):
        """Minimal training data with 2 classes (sklearn requires ≥2)."""
        return (
            [
                "warning flood danger", "advice safety first",
                "help stranded need rescue", "please send supplies urgently",
            ],
            [
                "caution_and_advice", "caution_and_advice",
                "requests_or_urgent_needs", "requests_or_urgent_needs",
            ],
        )

    def test_train_returns_self(self, small_train):
        texts, labels = small_train
        clf = BaselineClassifier(max_features=100)
        result = clf.train(texts, labels)
        assert result is clf

    def test_predict_returns_label_and_scores(self, small_train):
        texts, labels = small_train
        clf = BaselineClassifier(max_features=100).train(texts, labels)
        preds = clf.predict(["warning flood danger"])
        assert len(preds) == 1
        assert "label" in preds[0]
        assert "scores" in preds[0]
        assert clf._label_to_idx[preds[0]["label"]] >= 0

    def test_predict_all_scores_sum_near_one(self, small_train):
        texts, labels = small_train
        clf = BaselineClassifier(max_features=100).train(texts, labels)
        preds = clf.predict(["warning flood danger"])
        total = sum(preds[0]["scores"].values())
        assert 0.99 < total < 1.01

    def test_untrained_raises(self):
        clf = BaselineClassifier()
        with pytest.raises(RuntimeError, match="not trained"):
            clf.predict(["some text"])

    @requires_humaid_raw
    def test_train_on_full_data(self):
        """Sanity: train on real HumAID train split."""
        clf = train_baseline()
        assert len(clf._label_to_idx) == 9
        # Predict on a known pattern
        preds = clf.predict(["Please help stranded families need rescue"])
        assert preds[0]["label"] in ALL_LABELS


class TestFewShotExamples:
    @requires_humaid_raw
    def test_select_covers_all_nine_labels(self, tmp_path):
        examples = select_few_shot_examples(samples_per_class=2, random_seed=42)
        labels = {e["label"] for e in examples}
        assert labels == set(ALL_LABELS)
        assert len(examples) == 18

    @requires_humaid_raw
    def test_examples_are_redacted(self):
        """Regression: few-shot text must be redacted (DATA_GATE compliance)."""
        examples = select_few_shot_examples(samples_per_class=2, random_seed=42)
        for ex in examples:
            assert "@" not in ex["text"] or "[USER]" in ex["text"]

    @requires_humaid_raw
    def test_save_and_load_roundtrip(self, tmp_path):
        examples = select_few_shot_examples(samples_per_class=2, random_seed=42)
        path = tmp_path / "few_shot_test.jsonl"
        saved = save_few_shot_examples(examples, path)
        loaded = load_few_shot_examples(saved)
        assert examples == loaded

    def test_load_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_few_shot_examples("/tmp/nonexistent_few_shot_lab2_test.jsonl")


class TestMergeReferenceLabels:
    @staticmethod
    def _make_test_json(entries: list[dict]) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(entries, f)
            return f.name

    def test_match_with_split_prefix(self):
        p = self._make_test_json([
            {"tweet_id": "1032436206313725953", "tweet_text": "x", "class_label": "requests_or_urgent_needs"},
        ])
        records = [{
            "post_id": "test:1032436206313725953",
            "_lab2": {
                "reference_label": None,
                "exploratory_emotion": None,
                "evidence_status": "dataset_record",
            },
        }]
        merged = merge_reference_labels(records, test_path=Path(p))
        assert merged[0]["_lab2"]["reference_label"] == "requests_or_urgent_needs"
        assert merged[0]["_lab2"]["evidence_status"] == "dataset_record"
        Path(p).unlink()

    def test_match_without_prefix(self):
        p = self._make_test_json([
            {"tweet_id": "123", "tweet_text": "x", "class_label": "caution_and_advice"},
        ])
        records = [{
            "post_id": "123",
            "_lab2": {
                "reference_label": None,
                "exploratory_emotion": None,
                "evidence_status": "dataset_record",
            },
        }]
        merged = merge_reference_labels(records, test_path=Path(p))
        assert merged[0]["_lab2"]["reference_label"] == "caution_and_advice"
        Path(p).unlink()

    def test_no_match_keeps_null(self):
        p = self._make_test_json([
            {"tweet_id": "999", "tweet_text": "x", "class_label": "not_humanitarian"},
        ])
        records = [{
            "post_id": "test:111",
            "_lab2": {
                "reference_label": None,
                "exploratory_emotion": None,
                "evidence_status": "dataset_record",
            },
        }]
        merged = merge_reference_labels(records, test_path=Path(p))
        assert merged[0]["_lab2"]["reference_label"] is None
        Path(p).unlink()

    def test_all_nine_labels_covered(self):
        entries = [
            {"tweet_id": str(i), "tweet_text": "x", "class_label": lbl}
            for i, lbl in enumerate(ALL_LABELS)
        ]
        p = self._make_test_json(entries)
        records = [{
            "post_id": f"test:{i}",
            "_lab2": {
                "reference_label": None,
                "exploratory_emotion": None,
                "evidence_status": "dataset_record",
            },
        } for i in range(9)]
        merged = merge_reference_labels(records, test_path=Path(p))
        labels = {r["_lab2"]["reference_label"] for r in merged}
        assert labels == set(ALL_LABELS)
        Path(p).unlink()


# ====================================================================
# src/lab2_analysis/evaluate.py
# ====================================================================

from src.lab2_analysis.evaluate import (
    compute_metrics,
    evaluate_model,
    find_model_versions,
)


class TestComputeMetrics:
    LABELS = ["caution_and_advice", "displaced_people_and_evacuations", "not_humanitarian"]

    def test_perfect_prediction(self):
        y_true = ["caution_and_advice", "not_humanitarian", "displaced_people_and_evacuations"]
        y_pred = ["caution_and_advice", "not_humanitarian", "displaced_people_and_evacuations"]
        m = compute_metrics(y_true, y_pred, self.LABELS)
        assert m["macro_f1"] == 1.0
        assert m["weighted_f1"] == 1.0
        assert m["accuracy"] == 1.0
        assert m["coverage"] == 1.0

    def test_all_wrong(self):
        y_true = ["caution_and_advice"] * 3
        y_pred = ["not_humanitarian"] * 3
        m = compute_metrics(y_true, y_pred, self.LABELS)
        for pc in m["per_class"]:
            if pc["label"] == "caution_and_advice":
                assert pc["recall"] == 0.0

    def test_excluded_failures_counted(self):
        y_true = ["caution_and_advice", "not_humanitarian", "caution_and_advice"]
        y_pred = ["caution_and_advice", None, "caution_and_advice"]
        m = compute_metrics(y_true, y_pred, self.LABELS)
        assert m.get("excluded_failures", 0) == 1
        # Rounded to 4 decimal places in compute_metrics
        assert m["coverage"] == 0.6667
        assert m["accuracy"] == 0.6667
        assert m["accuracy_on_successful_only"] == 1.0

    def test_all_none_predictions(self):
        y_true = ["caution_and_advice"] * 3
        y_pred = [None] * 3
        m = compute_metrics(y_true, y_pred, self.LABELS)
        assert m["macro_f1"] == 0.0
        assert m["coverage"] == 0.0
        assert m["accuracy"] == 0.0
        assert "No valid predictions" in m["classification_report"]

    def test_confusion_matrix_shape(self):
        y_true = ["caution_and_advice", "not_humanitarian", "displaced_people_and_evacuations"]
        y_pred = ["caution_and_advice", "not_humanitarian", "not_humanitarian"]
        m = compute_metrics(y_true, y_pred, self.LABELS)
        assert m["confusion_matrix"].shape == (3, 3)

    def test_per_class_has_all_fields(self):
        m = compute_metrics(
            ["caution_and_advice"] * 3, ["caution_and_advice"] * 3, self.LABELS
        )
        for pc in m["per_class"]:
            for k in ["label", "precision", "recall", "f1", "support"]:
                assert k in pc


class TestFindModelVersions:
    def test_finds_unique_versions(self):
        predictions = [
            {"model_version": "tfidf-lr-baseline-v1"},
            {"model_version": "deepseek-v4-flash"},
            {"model_version": "tfidf-lr-baseline-v1"},
        ]
        versions = find_model_versions(predictions=predictions)
        assert set(versions) == {"tfidf-lr-baseline-v1", "deepseek-v4-flash"}

    def test_handles_null_lab2(self):
        records = [
            {"_lab2": None},
            {"_lab2": {"model_version": "tfidf-lr-baseline-v1"}},
        ]
        versions = find_model_versions(records)
        assert versions == ["tfidf-lr-baseline-v1"]

    def test_empty_returns_empty(self):
        assert find_model_versions([]) == []


# ====================================================================
# src/lab2_analysis/aggregate.py
# ====================================================================

from src.lab2_analysis.aggregate import (
    build_metrics,
    build_evidence_inventory,
    compute_distribution,
)


def _make_record(post_id, ref_label, pred_label, model_ver, emotion=None):
    return {
        "post_id": post_id,
        "source_ref": f"humaid_events:test:{post_id}",
        "text_clean": f"synthetic text for {post_id}",
        "_lab2": {
            "reference_label": ref_label,
            "predicted_label": pred_label,
            "model_scores": {pred_label: 0.9} if pred_label else {},
            "exploratory_emotion": emotion,
            "evidence_status": "model_prediction",
            "model_version": model_ver,
        },
    }


class TestBuildMetrics:
    def test_total_records(self):
        records = [
            _make_record("1", "caution_and_advice", "caution_and_advice", "tfidf-v1"),
            _make_record("2", "not_humanitarian", "not_humanitarian", "tfidf-v1"),
            _make_record("3", "sympathy_and_support", "sympathy_and_support", "tfidf-v1"),
        ]
        m = build_metrics(records)
        assert m["total_records"] == 3
        assert m["records_with_reference_label"] == 3
        assert m["records_with_prediction"] == 3
        assert m["records_with_emotion"] == 0

    def test_model_versions(self):
        records = [
            _make_record("1", "caution_and_advice", "caution_and_advice", "tfidf-v1"),
            _make_record("2", "not_humanitarian", "not_humanitarian", "deepseek-v4-flash"),
        ]
        m = build_metrics(records)
        assert set(m["model_versions"]) == {"tfidf-v1", "deepseek-v4-flash"}

    def test_reference_label_distribution(self):
        records = [
            _make_record("1", "caution_and_advice", "caution_and_advice", "v1"),
            _make_record("2", "caution_and_advice", "caution_and_advice", "v1"),
            _make_record("3", "not_humanitarian", "not_humanitarian", "v1"),
        ]
        dist = build_metrics(records)["reference_label_distribution"]
        assert dist["caution_and_advice"] == 2
        assert dist["not_humanitarian"] == 1

    def test_emotion_distribution(self):
        records = [
            _make_record("1", "A", "A", "v1", emotion="fear_or_anxiety"),
            _make_record("2", "B", "B", "v1", emotion="fear_or_anxiety"),
            _make_record("3", "C", "C", "v1", emotion="sadness"),
        ]
        dist = build_metrics(records)["emotion_distribution"]
        assert dist["fear_or_anxiety"] == 2
        assert dist["sadness"] == 1


class TestBuildEvidenceInventory:
    def test_respects_max_per_category(self):
        records = [
            _make_record(f"a{i}", "caution_and_advice", "caution_and_advice", "v1")
            for i in range(5)
        ] + [
            _make_record(f"b{i}", "not_humanitarian", "not_humanitarian", "v1")
            for i in range(5)
        ]
        evidence = build_evidence_inventory(records, max_per_category=3)
        labels = Counter(e["reference_label"] for e in evidence)
        assert labels["caution_and_advice"] == 3
        assert labels["not_humanitarian"] == 3

    def test_prefers_correct_predictions(self):
        records = [
            _make_record("a", "caution_and_advice", "caution_and_advice", "v1"),  # correct
            _make_record("b", "caution_and_advice", "not_humanitarian", "v1"),     # wrong
        ]
        evidence = build_evidence_inventory(records, max_per_category=1)
        # Should prefer the correct prediction
        assert evidence[0]["is_correct_prediction"] is True

    def test_skips_no_reference(self):
        records = [
            {
                "post_id": "1",
                "source_ref": "x",
                "text_clean": "t",
                "_lab2": {
                    "reference_label": None, "predicted_label": "X",
                    "model_scores": {}, "exploratory_emotion": None,
                    "evidence_status": "model_prediction", "model_version": "v1",
                },
            },
        ]
        evidence = build_evidence_inventory(records, max_per_category=1)
        assert len(evidence) == 0


# ====================================================================
# src/lab2_analysis/annotate_seed.py
# ====================================================================

from src.lab2_analysis.annotate_seed import (
    sample_stratified,
    export_sample,
    export_csv_for_annotation,
    compute_iaa,
    EMOTION_LABELS,
)


class TestSampleStratified:
    @pytest.fixture
    def mock_records(self):
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

    def test_does_not_exceed_n_total(self, mock_records):
        for n in [3, 6, 10, 20]:
            sample = sample_stratified(mock_records, n_total=n, random_seed=42)
            assert len(sample) == n, f"n_total={n} but got {len(sample)}"

    def test_minimum_one_per_class(self, mock_records):
        sample = sample_stratified(mock_records, n_total=5, random_seed=42)
        counts = Counter(r["class_label"] for r in sample)
        for lbl in ["label_a", "label_b", "label_c"]:
            assert counts[lbl] >= 1

    def test_seed_reproducibility(self, mock_records):
        s1 = sample_stratified(mock_records, n_total=10, random_seed=42)
        s2 = sample_stratified(mock_records, n_total=10, random_seed=42)
        assert [r["tweet_id"] for r in s1] == [r["tweet_id"] for r in s2]

    def test_empty_input(self):
        assert sample_stratified([], n_total=5) == []

    def test_n_total_less_than_classes_returns_exact_n(self, mock_records):
        """When n_total < n_classes, still return exactly n_total items."""
        sample = sample_stratified(mock_records, n_total=2, random_seed=42)
        assert len(sample) == 2

    def test_fewer_records_than_n_total(self):
        """Pool smaller than n_total returns all available."""
        records = [
            {"tweet_id": "1", "tweet_text": "x", "class_label": "A"},
            {"tweet_id": "2", "tweet_text": "x", "class_label": "B"},
        ]
        sample = sample_stratified(records, n_total=100, random_seed=42)
        assert len(sample) == 2


class TestExportSample:
    @pytest.fixture
    def sample(self):
        return [
            {"tweet_id": "1", "tweet_text": "help needed", "class_label": "requests_or_urgent_needs"},
            {"tweet_id": "2", "tweet_text": "stay safe", "class_label": "caution_and_advice"},
        ]

    def test_export_jsonl_creates_file(self, sample, tmp_path):
        path = tmp_path / "emotion.jsonl"
        n = export_sample(sample, path, annotator="tester")
        assert n == 2
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        assert rows[0]["exploratory_emotion"] is None
        assert rows[0]["annotator"] == "tester"

    def test_export_csv_creates_file(self, sample, tmp_path):
        path = tmp_path / "emotion.csv"
        n = export_csv_for_annotation(sample, path)
        assert n == 2
        content = path.read_text()
        assert "tweet_id" in content
        assert "exploratory_emotion" in content


class TestComputeIAA:
    def _write_annotations(self, path, pairs):
        with open(path, "w") as f:
            for tid, emotion in pairs:
                f.write(json.dumps({"tweet_id": tid, "exploratory_emotion": emotion}) + "\n")

    def test_perfect_agreement(self, tmp_path):
        self._write_annotations(tmp_path / "a.jsonl", [("1", "anger"), ("2", "sadness")])
        self._write_annotations(tmp_path / "b.jsonl", [("1", "anger"), ("2", "sadness")])
        result = compute_iaa(tmp_path / "a.jsonl", tmp_path / "b.jsonl")
        assert result["raw_agreement"] == 1.0
        assert result["cohens_kappa"] == 1.0

    def test_no_overlap(self, tmp_path):
        self._write_annotations(tmp_path / "a.jsonl", [("1", "anger")])
        self._write_annotations(tmp_path / "b.jsonl", [("2", "sadness")])
        result = compute_iaa(tmp_path / "a.jsonl", tmp_path / "b.jsonl")
        assert "error" in result

    def test_partial_overlap(self, tmp_path):
        self._write_annotations(tmp_path / "a.jsonl", [("1", "anger"), ("2", "sadness"), ("3", "fear_or_anxiety")])
        self._write_annotations(tmp_path / "b.jsonl", [("1", "fear_or_anxiety"), ("2", "sadness"), ("4", "anger")])
        result = compute_iaa(tmp_path / "a.jsonl", tmp_path / "b.jsonl")
        assert result["n_overlap"] == 2  # only 1 and 2
        assert result["raw_agreement"] == 0.5  # agree on 2, disagree on 1

    def test_incomplete_annotations_raise_by_default(self, tmp_path):
        self._write_annotations(tmp_path / "a.jsonl", [("1", "anger"), ("2", None)])
        self._write_annotations(tmp_path / "b.jsonl", [("1", "anger"), ("2", "sadness")])
        with pytest.raises(ValueError, match="Incomplete"):
            compute_iaa(tmp_path / "a.jsonl", tmp_path / "b.jsonl")

    def test_allow_incomplete_skips_null_emotions(self, tmp_path):
        self._write_annotations(tmp_path / "a.jsonl", [("1", "anger"), ("2", None)])
        self._write_annotations(tmp_path / "b.jsonl", [("1", "anger"), ("2", "sadness")])
        result = compute_iaa(
            tmp_path / "a.jsonl",
            tmp_path / "b.jsonl",
            require_complete=False,
        )
        assert result["raw_agreement"] == 1.0


# ====================================================================
# Round 2: separated posts / predictions contracts
# ====================================================================

from src.lab2_analysis.classify import (
    build_unique_posts,
    make_prediction_row,
    migrate_legacy_labeled,
    upsert_predictions,
    write_jsonl_atomic,
)
from src.lab2_analysis.annotate_seed import (
    merge_emotions_into_posts,
    validate_emotion_annotations,
    write_iaa_report,
)
from src.utils.cache import config_fingerprint, is_finite_unit_interval


class TestPredictionTableContracts:
    def test_dual_model_unique_keys(self, tmp_path):
        posts_in = [
            {
                "schema_version": "1.0.0",
                "pipeline_run_id": "t",
                "post_id": "p1",
                "text_clean": "Synthetic a",
                "event_id": "kerala_floods_2018",
                "time": None,
                "location": None,
                "source": "synthetic_fixture",
                "source_ref": "synthetic_fixture:1",
                "pii_redacted": True,
                "_lab3": None,
                "_lab2": {
                    "reference_label": "caution_and_advice",
                    "predicted_label": "caution_and_advice",
                    "model_scores": {"caution_and_advice": 0.9},
                    "exploratory_emotion": None,
                    "evidence_status": "dataset_record",
                    "model_version": "baseline-v1",
                },
            },
            {
                "schema_version": "1.0.0",
                "pipeline_run_id": "t",
                "post_id": "p1",
                "text_clean": "Synthetic a",
                "event_id": "kerala_floods_2018",
                "time": None,
                "location": None,
                "source": "synthetic_fixture",
                "source_ref": "synthetic_fixture:1",
                "pii_redacted": True,
                "_lab3": None,
                "_lab2": {
                    "reference_label": "caution_and_advice",
                    "predicted_label": "not_humanitarian",
                    "model_scores": {"not_humanitarian": 0.6},
                    "exploratory_emotion": "anger",
                    "evidence_status": "dataset_record",
                    "model_version": "llm-v1",
                },
            },
        ]
        legacy = tmp_path / "legacy.jsonl"
        write_jsonl_atomic(legacy, posts_in)
        posts_out = tmp_path / "posts.jsonl"
        preds_out = tmp_path / "preds.jsonl"
        n_posts, n_preds = migrate_legacy_labeled(
            legacy, posts_out=posts_out, predictions_out=preds_out
        )
        assert n_posts == 1
        assert n_preds == 2
        posts = [json.loads(l) for l in posts_out.read_text().splitlines() if l.strip()]
        preds = [json.loads(l) for l in preds_out.read_text().splitlines() if l.strip()]
        assert len(posts) == 1
        assert "predicted_label" not in posts[0]["_lab2"]
        assert posts[0]["_lab2"]["exploratory_emotion"] == "anger"
        keys = [(p["post_id"], p["model_version"]) for p in preds]
        assert len(keys) == len(set(keys))

    def test_upsert_predictions_replaces_same_key(self, tmp_path):
        path = tmp_path / "predictions.jsonl"
        row1 = make_prediction_row(
            post_id="p1",
            model_version="m1",
            predicted_label="caution_and_advice",
            model_scores={"caution_and_advice": 0.9},
            status="ok",
            pipeline_run_id="r1",
        )
        row2 = make_prediction_row(
            post_id="p1",
            model_version="m1",
            predicted_label="not_humanitarian",
            model_scores={"not_humanitarian": 0.7},
            status="ok",
            pipeline_run_id="r1",
        )
        upsert_predictions(path, [row1])
        upsert_predictions(path, [row2])
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        assert len(rows) == 1
        assert rows[0]["predicted_label"] == "not_humanitarian"

    def test_build_unique_posts_dedupes(self):
        records = [
            {"post_id": "a", "source": "synthetic_fixture", "text_clean": "x", "_lab3": None},
            {"post_id": "a", "source": "synthetic_fixture", "text_clean": "x", "_lab3": None},
            {"post_id": "b", "source": "humaid_events", "text_clean": "y", "_lab3": None},
        ]
        posts = build_unique_posts(records)
        assert [p["post_id"] for p in posts] == ["a", "b"]
        assert posts[0]["_lab2"]["evidence_status"] == "human_labeled"
        assert posts[1]["_lab2"]["evidence_status"] == "dataset_record"


class TestEvaluateJoinedPredictions:
    def test_full_denominator_and_coverage(self):
        posts = [
            {
                "post_id": "1",
                "_lab2": {
                    "reference_label": "caution_and_advice",
                    "exploratory_emotion": None,
                    "evidence_status": "dataset_record",
                },
            },
            {
                "post_id": "2",
                "_lab2": {
                    "reference_label": "not_humanitarian",
                    "exploratory_emotion": None,
                    "evidence_status": "dataset_record",
                },
            },
        ]
        predictions = [
            {
                "post_id": "1",
                "model_version": "m1",
                "predicted_label": "caution_and_advice",
                "status": "ok",
            },
            {
                "post_id": "2",
                "model_version": "m1",
                "predicted_label": None,
                "status": "error",
            },
        ]
        result = evaluate_model(posts, "m1", "m1", predictions=predictions)
        assert result["total_records"] == 2
        assert result["coverage"] == 0.5
        assert result["accuracy"] == 0.5
        assert result["accuracy_on_successful_only"] == 1.0
        assert result["excluded_failures"] == 1


class TestEmotionExactNAndMerge:
    def test_validate_and_merge(self, tmp_path):
        emotions = tmp_path / "emotions.jsonl"
        emotions.write_text(
            json.dumps(
                {
                    "tweet_id": "111",
                    "exploratory_emotion": "anger",
                    "text_clean": "Synthetic",
                    "class_label": "caution_and_advice",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        validate_emotion_annotations(emotions)
        labeled = tmp_path / "posts.jsonl"
        labeled.write_text(
            json.dumps(
                {
                    "post_id": "test:111",
                    "_lab2": {
                        "reference_label": "caution_and_advice",
                        "exploratory_emotion": None,
                        "evidence_status": "dataset_record",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        updated = merge_emotions_into_posts(emotions, labeled)
        assert updated == 1
        row = json.loads(labeled.read_text().splitlines()[0])
        assert row["_lab2"]["exploratory_emotion"] == "anger"

    def test_write_iaa_report(self, tmp_path):
        a = tmp_path / "a.jsonl"
        b = tmp_path / "b.jsonl"
        a.write_text(
            json.dumps({"tweet_id": "1", "exploratory_emotion": "anger"}) + "\n",
            encoding="utf-8",
        )
        b.write_text(
            json.dumps({"tweet_id": "1", "exploratory_emotion": "anger"}) + "\n",
            encoding="utf-8",
        )
        result = compute_iaa(a, b)
        report = write_iaa_report(result, tmp_path / "iaa.md")
        text = report.read_text(encoding="utf-8")
        assert "Cohen's Kappa" in text
        assert "1.0" in text


class TestConfidenceAndFingerprint:
    def test_finite_unit_interval(self):
        assert is_finite_unit_interval(0.0)
        assert is_finite_unit_interval(1.0)
        assert is_finite_unit_interval(0.5)
        assert not is_finite_unit_interval(-0.1)
        assert not is_finite_unit_interval(1.1)
        assert not is_finite_unit_interval(float("nan"))
        assert not is_finite_unit_interval(float("inf"))
        assert not is_finite_unit_interval(None)

    def test_config_fingerprint_stable(self):
        fp1 = config_fingerprint({"a": 1, "b": ["x"]})
        fp2 = config_fingerprint({"b": ["x"], "a": 1})
        assert fp1 == fp2
        assert fp1 != config_fingerprint({"a": 2, "b": ["x"]})
