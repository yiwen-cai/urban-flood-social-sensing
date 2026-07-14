"""Lab 2 — Classification pipeline: baseline + LLM Few-shot.

Produces ``data/analyzed/posts_labeled.jsonl`` by reading Lab 1's
``posts_clean.jsonl`` and appending ``_lab2`` annotations.

Two classifiers:
1. **TF-IDF + Logistic Regression** — low-complexity, fully reproducible baseline.
2. **DeepSeek Few-shot** — LLM classification with JSON Schema output.

Usage:
    python -m src.lab2_analysis.classify --input data/processed/posts_clean.test.jsonl
    python -m src.lab2_analysis.classify --input data/processed/posts_clean.test.jsonl --method baseline
    python -m src.lab2_analysis.classify --input data/processed/posts_clean.test.jsonl --method llm
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "posts_clean.test.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "analyzed" / "posts_labeled.jsonl"
DEFAULT_ERRORS = PROJECT_ROOT / "data" / "analyzed" / "classification_errors.jsonl"
TRAIN_PATH = PROJECT_ROOT / "data" / "raw" / "humaid" / "kerala_floods_2018" / "train.json"
DEV_PATH = PROJECT_ROOT / "data" / "raw" / "humaid" / "kerala_floods_2018" / "dev.json"
FEW_SHOT_PATH = PROJECT_ROOT / "data" / "seed" / "few_shot_examples.jsonl"

# ====================================================================
# Label inventory
# ====================================================================

ALL_LABELS: list[str] = [
    "caution_and_advice",
    "displaced_people_and_evacuations",
    "infrastructure_and_utility_damage",
    "injured_or_dead_people",
    "not_humanitarian",
    "other_relevant_information",
    "requests_or_urgent_needs",
    "rescue_volunteering_or_donation_effort",
    "sympathy_and_support",
]


# ====================================================================
# Baseline: TF-IDF + Logistic Regression
# ====================================================================

class BaselineClassifier:
    """Reproducible TF-IDF + Logistic Regression baseline.

    Trained on HumAID train split, optionally tuned on dev split.
    """

    def __init__(self, *, max_features: int = 5000, C: float = 1.0):
        self.max_features = max_features
        self.C = C
        self._vectorizer: Any = None
        self._model: Any = None
        self._label_to_idx: dict[str, int] = {}
        self._idx_to_label: dict[int, str] = {}

    def train(
        self, texts: list[str], labels: list[str]
    ) -> BaselineClassifier:
        """Fit vectorizer and classifier on training data."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression

        self._label_to_idx = {lbl: i for i, lbl in enumerate(sorted(set(labels)))}
        self._idx_to_label = {i: lbl for lbl, i in self._label_to_idx.items()}

        self._vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=(1, 2),
            stop_words="english",
        )

        X = self._vectorizer.fit_transform(texts)
        y = np.array([self._label_to_idx[lbl] for lbl in labels])

        self._model = LogisticRegression(
            C=self.C,
            max_iter=1000,
            solver="lbfgs",
            random_state=42,
        )
        self._model.fit(X, y)
        return self

    def predict(self, texts: list[str]) -> list[dict[str, Any]]:
        """Return list of {label, scores} dicts for each text."""
        if self._vectorizer is None or self._model is None:
            raise RuntimeError("Classifier not trained. Call .train() first.")

        X = self._vectorizer.transform(texts)
        proba = self._model.predict_proba(X)
        pred_indices = self._model.predict(X)

        results: list[dict[str, Any]] = []
        for i, idx in enumerate(pred_indices):
            label = self._idx_to_label[idx]
            scores: dict[str, float] = {}
            for j, lbl in self._idx_to_label.items():
                scores[lbl] = float(proba[i, j])
            results.append({"label": label, "scores": scores})
        return results


def _load_humaid_split(path: Path) -> tuple[list[str], list[str]]:
    """Load a HumAID JSON file and return (texts, labels)."""
    with path.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    texts = [r["tweet_text"] for r in rows]
    labels = [r["class_label"] for r in rows]
    return texts, labels


def train_baseline() -> BaselineClassifier:
    """Train a baseline classifier on the official train split."""
    train_texts, train_labels = _load_humaid_split(TRAIN_PATH)
    dev_texts, dev_labels = _load_humaid_split(DEV_PATH)

    # Train on train; optionally use dev to guide C selection
    # (simplified: fixed C=1.0 for reproducibility)
    clf = BaselineClassifier(max_features=5000, C=1.0)
    clf.train(train_texts, train_labels)
    return clf


# ====================================================================
# Few-shot example selection
# ====================================================================

def select_few_shot_examples(
    *, samples_per_class: int = 2, random_seed: int = 42
) -> list[dict[str, str]]:
    """Select few-shot examples from train+dev, NOT from test.

    Args:
        samples_per_class: Number of examples per label.
        random_seed: Fixed seed for reproducibility.

    Returns:
        List of {"text": ..., "label": ...} dicts, frozen for Prompt use.
    """
    import random
    from src.utils.redact import redact_text

    random.seed(random_seed)

    # Pool from train and dev only — NEVER from test
    train_rows = json.loads(TRAIN_PATH.read_text(encoding="utf-8"))
    dev_rows = json.loads(DEV_PATH.read_text(encoding="utf-8"))
    pool = train_rows + dev_rows

    # Group by label
    by_label: dict[str, list[str]] = {lbl: [] for lbl in ALL_LABELS}
    for row in pool:
        label = row["class_label"]
        if label in by_label:
            by_label[label].append(row["tweet_text"])

    examples: list[dict[str, str]] = []
    for label in ALL_LABELS:
        candidates = by_label.get(label, [])
        selected = random.sample(
            candidates, min(samples_per_class, len(candidates))
        )
        for text in selected:
            examples.append({"text": redact_text(text), "label": label})

    random.shuffle(examples)
    return examples


def save_few_shot_examples(
    examples: list[dict[str, str]], path: str | Path | None = None
) -> Path:
    """Persist selected few-shot examples to JSONL."""
    path = Path(path or FEW_SHOT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for ex in examples:
            handle.write(json.dumps(ex, ensure_ascii=False) + "\n")
    return path


def load_few_shot_examples(path: str | Path | None = None) -> list[dict[str, str]]:
    """Load frozen few-shot examples from JSONL."""
    path = Path(path or FEW_SHOT_PATH)
    if not path.is_file():
        raise FileNotFoundError(
            f"Few-shot examples not found at {path}. "
            "Run select_few_shot_examples() and save_few_shot_examples() first."
        )
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ====================================================================
# Main classification runner
# ====================================================================

def run_baseline_classification(
    input_path: str | Path,
    clf: BaselineClassifier | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify all posts in ``input_path`` using the TF-IDF baseline.

    Returns:
        (annotated_records, error_records) — error_records is empty for
        the baseline (deterministic local inference), but kept for
        interface consistency.
    """
    from src.utils.io import read_jsonl

    if clf is None:
        clf = train_baseline()

    records = list(read_jsonl(input_path))
    texts = [r["text_clean"] for r in records]
    predictions = clf.predict(texts)

    annotated: list[dict[str, Any]] = []
    for record, pred in zip(records, predictions):
        record["_lab2"] = {
            "reference_label": None,  # Lab 1 doesn't carry this
            "predicted_label": pred["label"],
            "model_scores": pred["scores"],
            "exploratory_emotion": None,
            "evidence_status": "model_prediction",
            "model_version": "tfidf-lr-baseline-v1",
        }
        annotated.append(record)

    return annotated, []


def run_llm_classification(
    input_path: str | Path,
    *,
    few_shot_examples: list[dict[str, str]] | None = None,
    checkpoint_path: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify all posts using the DeepSeek LLM with few-shot prompting.

    Args:
        input_path: Path to posts_clean.jsonl.
        few_shot_examples: Few-shot examples (auto-loaded if None).
        checkpoint_path: Path for resume checkpoint file.

    Returns:
        (annotated_records, error_records)
    """
    from src.utils.io import read_jsonl
    from src.utils.llm import classify_batch, DEEPSEEK_MODEL

    if few_shot_examples is None:
        few_shot_examples = load_few_shot_examples()

    records = list(read_jsonl(input_path))
    texts = [
        {"post_id": r["post_id"], "text_clean": r["text_clean"]}
        for r in records
    ]

    # Checkpoint defaults
    if checkpoint_path is None:
        checkpoint_path = str(
            PROJECT_ROOT / "data" / "cache" / "checkpoint_llm.txt"
        )

    batch_results = classify_batch(
        texts,
        few_shot_examples=few_shot_examples,
        checkpoint_path=checkpoint_path,
    )

    # Map batch results back to records
    result_by_id = {r["post_id"]: r for r in batch_results}

    annotated: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for record in records:
        post_id = record["post_id"]
        br = result_by_id.get(post_id, {})

        if br.get("success"):
            label = br["label"]
            confidence = br.get("confidence", 1.0)
            scores = {label: float(confidence)} if label else {}
            record["_lab2"] = {
                "reference_label": None,
                "predicted_label": label,
                "model_scores": scores,
                "exploratory_emotion": None,
                "evidence_status": "model_prediction",
                "model_version": br.get("model_version", DEEPSEEK_MODEL),
            }
            annotated.append(record)
        else:
            # Classification failed — record error and set predicted_label to None
            record["_lab2"] = {
                "reference_label": None,
                "predicted_label": None,
                "model_scores": {},
                "exploratory_emotion": None,
                "evidence_status": "model_prediction",
                "model_version": br.get("model_version", DEEPSEEK_MODEL),
            }
            annotated.append(record)
            errors.append({
                "post_id": post_id,
                "error": br.get("error", "unknown"),
                "source_ref": record.get("source_ref", ""),
            })

    return annotated, errors


def merge_reference_labels(
    records: list[dict[str, Any]],
    test_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Merge official reference labels from HumAID test.json into _lab2.

    This is called AFTER classification so that reference labels are only
    used for evaluation and never leak into the model input.

    Lab 1's ``post_id`` format is ``{split}:{tweet_id}`` (e.g.
    ``"test:1032436206313725953"``), so we strip the split prefix before
    looking up the raw tweet_id in HumAID's reference labels.
    """
    test_path = Path(
        test_path
        or PROJECT_ROOT / "data" / "raw" / "humaid" / "kerala_floods_2018" / "test.json"
    )
    with test_path.open(encoding="utf-8") as handle:
        test_rows = json.load(handle)

    ref_by_id = {str(r["tweet_id"]): r["class_label"] for r in test_rows}

    matched = 0
    for record in records:
        post_id = record.get("post_id", "")
        # Strip the split prefix added by Lab 1 (e.g. "test:123" → "123")
        tweet_id = post_id.split(":", 1)[-1] if ":" in post_id else post_id

        ref_label = ref_by_id.get(tweet_id)
        if ref_label is not None and "_lab2" in record:
            record["_lab2"]["reference_label"] = ref_label
            record["_lab2"]["evidence_status"] = "dataset_record"
            matched += 1

    print(f"Merged {matched} reference labels into {len(records)} records")
    return records


# ====================================================================
# CLI
# ====================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to posts_clean.jsonl (Lab 1 output)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path for posts_labeled.jsonl",
    )
    parser.add_argument(
        "--errors",
        type=Path,
        default=DEFAULT_ERRORS,
        help="Path for classification_errors.jsonl",
    )
    parser.add_argument(
        "--method",
        choices=["baseline", "llm", "both"],
        default="both",
        help="Which classifier to run (default: both)",
    )
    parser.add_argument(
        "--merge-reference",
        action="store_true",
        help="Merge official reference labels after classification",
    )
    parser.add_argument(
        "--select-few-shot",
        action="store_true",
        help="Select and save few-shot examples, then exit",
    )
    args = parser.parse_args()

    # Few-shot selection mode
    if args.select_few_shot:
        examples = select_few_shot_examples(samples_per_class=2)
        saved = save_few_shot_examples(examples)
        print(f"Saved {len(examples)} few-shot examples to {saved}")
        return 0

    from src.utils.io import write_jsonl

    if not Path(args.input).is_file():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        print(
            "Run Lab 1 first to produce posts_clean.jsonl, or use --input to "
            "point to a fixture file.",
            file=sys.stderr,
        )
        return 1

    all_annotated: list[dict[str, Any]] = []
    all_errors: list[dict[str, Any]] = []
    baseline_written = False

    # --- Baseline ---
    if args.method in ("baseline", "both"):
        print("Training TF-IDF + Logistic Regression baseline...")
        annotated, _ = run_baseline_classification(args.input)
        if args.method == "baseline":
            all_annotated = annotated
        else:
            # both mode: keep a copy of the baseline result for side-by-side eval
            bl_path = Path(str(args.output).replace(".jsonl", ".baseline.jsonl"))
            if args.merge_reference:
                annotated = merge_reference_labels(annotated)
            write_jsonl(bl_path, annotated)
            baseline_written = True
            print(f"  Baseline classified {len(annotated)} records → {bl_path}")
            # reuse the baseline texts for LLM (same input)
        print(f"  Baseline classified {len(annotated)} records")

    # --- LLM ---
    if args.method in ("llm", "both"):
        print("Running LLM classification (DeepSeek)...")
        annotated, errors = run_llm_classification(args.input)
        all_annotated = annotated
        all_errors = errors
        print(f"  LLM classified {len(annotated)} records, {len(errors)} errors")

    # --- Merge reference labels ---
    if args.merge_reference and all_annotated:
        all_annotated = merge_reference_labels(all_annotated)

    # --- Write outputs ---
    if all_annotated:
        write_jsonl(Path(args.output), all_annotated)
        print(f"Wrote {len(all_annotated)} records to {args.output}")

    if all_errors:
        write_jsonl(Path(args.errors), all_errors)
        print(f"Wrote {len(all_errors)} error records to {args.errors}")

    # --- Accounting ---
    input_count = sum(
        1 for _ in Path(args.input).read_text(encoding="utf-8").splitlines()
        if _.strip()
    )
    success_count = len(all_annotated) - len(all_errors)
    print(
        f"Accounting: {input_count} input, {success_count} success, "
        f"{len(all_errors)} failed, {input_count - len(all_annotated)} skipped"
    )
    return 0 if len(all_errors) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
