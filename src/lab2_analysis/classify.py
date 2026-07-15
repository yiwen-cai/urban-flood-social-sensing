"""Lab 2 — Classification pipeline: baseline + LLM Few-shot.

Produces:
- ``data/analyzed/posts_labeled.jsonl`` — one row per post (labels/emotion only)
- ``data/analyzed/predictions.jsonl`` — one row per (post_id, model_version)

Two classifiers:
1. **TF-IDF + Logistic Regression** — low-complexity, fully reproducible baseline.
2. **DeepSeek Few-shot** — LLM classification with JSON Schema output.

Usage:
    python -m src.lab2_analysis.classify --input data/processed/posts_clean.test.jsonl
    python -m src.lab2_analysis.classify --method baseline --merge-reference
    python -m src.lab2_analysis.classify --from-legacy data/analyzed/posts_labeled.legacy.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "posts_clean.test.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "analyzed" / "posts_labeled.jsonl"
DEFAULT_PREDICTIONS = PROJECT_ROOT / "data" / "analyzed" / "predictions.jsonl"
DEFAULT_ERRORS = PROJECT_ROOT / "data" / "analyzed" / "classification_errors.jsonl"
TRAIN_PATH = PROJECT_ROOT / "data" / "raw" / "humaid" / "kerala_floods_2018" / "train.json"
DEV_PATH = PROJECT_ROOT / "data" / "raw" / "humaid" / "kerala_floods_2018" / "dev.json"
FEW_SHOT_PATH = PROJECT_ROOT / "data" / "seed" / "few_shot_examples.jsonl"

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

BASELINE_MODEL_VERSION = "tfidf-lr-baseline-v1"


class BaselineClassifier:
    """Reproducible TF-IDF + Logistic Regression baseline."""

    def __init__(self, *, max_features: int = 5000, C: float = 1.0):
        self.max_features = max_features
        self.C = C
        self._vectorizer: Any = None
        self._model: Any = None
        self._label_to_idx: dict[str, int] = {}
        self._idx_to_label: dict[int, str] = {}

    def train(self, texts: list[str], labels: list[str]) -> BaselineClassifier:
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
        if self._vectorizer is None or self._model is None:
            raise RuntimeError("Classifier not trained. Call .train() first.")
        X = self._vectorizer.transform(texts)
        proba = self._model.predict_proba(X)
        pred_indices = self._model.predict(X)
        results: list[dict[str, Any]] = []
        for i, idx in enumerate(pred_indices):
            label = self._idx_to_label[idx]
            scores = {
                self._idx_to_label[j]: float(proba[i, j])
                for j in self._idx_to_label
            }
            results.append({"label": label, "scores": scores})
        return results


def _load_humaid_split(path: Path) -> tuple[list[str], list[str]]:
    from src.utils.redact import redact_text

    with path.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    texts = [redact_text(r["tweet_text"]) for r in rows]
    labels = [r["class_label"] for r in rows]
    return texts, labels


def train_baseline() -> BaselineClassifier:
    train_texts, train_labels = _load_humaid_split(TRAIN_PATH)
    clf = BaselineClassifier(max_features=5000, C=1.0)
    clf.train(train_texts, train_labels)
    return clf


def select_few_shot_examples(
    *, samples_per_class: int = 2, random_seed: int = 42
) -> list[dict[str, str]]:
    import random
    from src.utils.redact import redact_text

    random.seed(random_seed)
    train_rows = json.loads(TRAIN_PATH.read_text(encoding="utf-8"))
    dev_rows = json.loads(DEV_PATH.read_text(encoding="utf-8"))
    pool = train_rows + dev_rows

    by_label: dict[str, list[str]] = {lbl: [] for lbl in ALL_LABELS}
    for row in pool:
        label = row["class_label"]
        if label in by_label:
            by_label[label].append(row["tweet_text"])

    examples: list[dict[str, str]] = []
    for label in ALL_LABELS:
        candidates = by_label.get(label, [])
        selected = random.sample(candidates, min(samples_per_class, len(candidates)))
        for text in selected:
            examples.append({"text": redact_text(text), "label": label})
    random.shuffle(examples)
    return examples


def save_few_shot_examples(
    examples: list[dict[str, str]], path: str | Path | None = None
) -> Path:
    path = Path(path or FEW_SHOT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for ex in examples:
            handle.write(json.dumps(ex, ensure_ascii=False) + "\n")
    return path


def load_few_shot_examples(path: str | Path | None = None) -> list[dict[str, str]]:
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


def _post_lab2(
    *,
    reference_label: str | None = None,
    exploratory_emotion: str | None = None,
    evidence_status: str = "dataset_record",
) -> dict[str, Any]:
    return {
        "reference_label": reference_label,
        "exploratory_emotion": exploratory_emotion,
        "evidence_status": evidence_status,
    }


def make_prediction_row(
    *,
    post_id: str,
    model_version: str,
    predicted_label: str | None,
    model_scores: dict[str, float],
    status: str,
    pipeline_run_id: str,
    error_message: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    if confidence is None and predicted_label and predicted_label in model_scores:
        confidence = float(model_scores[predicted_label])
    return {
        "schema_version": "1.0.0",
        "pipeline_run_id": pipeline_run_id,
        "post_id": post_id,
        "model_version": model_version,
        "predicted_label": predicted_label,
        "model_scores": model_scores,
        "status": status,
        "error_message": error_message,
        "confidence": confidence,
    }


def build_unique_posts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one post row per post_id with post-level _lab2 only."""
    posts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        post_id = record["post_id"]
        if post_id in seen:
            continue
        seen.add(post_id)
        post = {k: v for k, v in record.items() if k != "_lab2"}
        source = post.get("source", "humaid_events")
        evidence_status = (
            "human_labeled" if source == "synthetic_fixture" else "dataset_record"
        )
        post["_lab2"] = _post_lab2(evidence_status=evidence_status)
        if post.get("_lab3") is None and "_lab3" not in post:
            post["_lab3"] = None
        posts.append(post)
    return posts


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as tmp:
        for row in rows:
            tmp.write(json.dumps(row, ensure_ascii=False) + "\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def upsert_predictions(
    path: Path,
    new_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Replace any existing (post_id, model_version) rows, then rewrite atomically."""
    existing: dict[tuple[str, str], dict[str, Any]] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            existing[(row["post_id"], row["model_version"])] = row
    for row in new_rows:
        existing[(row["post_id"], row["model_version"])] = row
    merged = list(existing.values())
    write_jsonl_atomic(path, merged)
    return merged


def run_baseline_classification(
    input_path: str | Path,
    clf: BaselineClassifier | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify posts with the TF-IDF baseline.

    Returns (posts, predictions, errors).
    """
    from src.utils.io import read_jsonl

    if clf is None:
        clf = train_baseline()

    records = list(read_jsonl(input_path))
    texts = [r["text_clean"] for r in records]
    preds = clf.predict(texts)
    posts = build_unique_posts(records)
    predictions: list[dict[str, Any]] = []
    for record, pred in zip(records, preds):
        confidence = float(pred["scores"].get(pred["label"], 0.0))
        predictions.append(
            make_prediction_row(
                post_id=record["post_id"],
                model_version=BASELINE_MODEL_VERSION,
                predicted_label=pred["label"],
                model_scores={k: float(v) for k, v in pred["scores"].items()},
                status="ok",
                pipeline_run_id=record.get("pipeline_run_id", "lab2-baseline"),
                confidence=confidence,
            )
        )
    return posts, predictions, []


def run_llm_classification(
    input_path: str | Path,
    *,
    few_shot_examples: list[dict[str, str]] | None = None,
    checkpoint_path: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify posts with DeepSeek. Returns (posts, predictions, errors)."""
    from src.utils.io import read_jsonl
    from src.utils.llm import DEEPSEEK_MODEL, classify_batch

    if few_shot_examples is None:
        few_shot_examples = load_few_shot_examples()

    records = list(read_jsonl(input_path))
    texts = [
        {"post_id": r["post_id"], "text_clean": r["text_clean"]}
        for r in records
    ]
    if checkpoint_path is None:
        checkpoint_path = str(PROJECT_ROOT / "data" / "cache" / "checkpoint_llm.txt")

    batch_results = classify_batch(
        texts,
        few_shot_examples=few_shot_examples,
        checkpoint_path=checkpoint_path,
    )
    result_by_id = {r["post_id"]: r for r in batch_results}
    posts = build_unique_posts(records)
    predictions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for record in records:
        post_id = record["post_id"]
        br = result_by_id.get(post_id, {})
        model_version = br.get("model_version", DEEPSEEK_MODEL)
        if br.get("success"):
            label = br["label"]
            confidence = float(br["confidence"])
            scores = {label: confidence}
            predictions.append(
                make_prediction_row(
                    post_id=post_id,
                    model_version=model_version,
                    predicted_label=label,
                    model_scores=scores,
                    status="ok",
                    pipeline_run_id=record.get("pipeline_run_id", "lab2-llm"),
                    confidence=confidence,
                )
            )
        else:
            err = br.get("error", "unknown")
            predictions.append(
                make_prediction_row(
                    post_id=post_id,
                    model_version=model_version,
                    predicted_label=None,
                    model_scores={},
                    status="error",
                    pipeline_run_id=record.get("pipeline_run_id", "lab2-llm"),
                    error_message=str(err),
                    confidence=None,
                )
            )
            errors.append(
                {
                    "post_id": post_id,
                    "model_version": model_version,
                    "error": err,
                    "source_ref": record.get("source_ref", ""),
                }
            )
    return posts, predictions, errors


def merge_reference_labels(
    posts: list[dict[str, Any]],
    test_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Merge official HumAID test labels into unique post rows."""
    test_path = Path(
        test_path
        or PROJECT_ROOT / "data" / "raw" / "humaid" / "kerala_floods_2018" / "test.json"
    )
    with test_path.open(encoding="utf-8") as handle:
        test_rows = json.load(handle)
    ref_by_id = {str(r["tweet_id"]): r["class_label"] for r in test_rows}

    matched = 0
    for post in posts:
        post_id = post.get("post_id", "")
        tweet_id = post_id.split(":", 1)[-1] if ":" in post_id else post_id
        ref_label = ref_by_id.get(tweet_id)
        if ref_label is None:
            continue
        lab2 = post.setdefault("_lab2", _post_lab2())
        lab2["reference_label"] = ref_label
        lab2["evidence_status"] = "dataset_record"
        matched += 1
    print(f"Merged {matched} reference labels into {len(posts)} posts")
    return posts


def migrate_legacy_labeled(
    legacy_path: str | Path,
    *,
    posts_out: str | Path = DEFAULT_OUTPUT,
    predictions_out: str | Path = DEFAULT_PREDICTIONS,
) -> tuple[int, int]:
    """Split legacy multi-model posts_labeled rows into posts + predictions.

    Reuses prior DeepSeek/baseline results without calling any API.
    """
    legacy_path = Path(legacy_path)
    rows = [
        json.loads(line)
        for line in legacy_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    posts_by_id: dict[str, dict[str, Any]] = {}
    predictions: list[dict[str, Any]] = []
    for row in rows:
        post_id = row["post_id"]
        lab2 = row.get("_lab2") or {}
        if post_id not in posts_by_id:
            post = {k: v for k, v in row.items() if k != "_lab2"}
            post["_lab2"] = _post_lab2(
                reference_label=lab2.get("reference_label"),
                exploratory_emotion=lab2.get("exploratory_emotion"),
                evidence_status=(
                    "dataset_record"
                    if lab2.get("evidence_status") in (None, "dataset_record", "model_prediction")
                    else lab2.get("evidence_status", "dataset_record")
                ),
            )
            if post["_lab2"]["evidence_status"] not in ("dataset_record", "human_labeled"):
                post["_lab2"]["evidence_status"] = "dataset_record"
            posts_by_id[post_id] = post
        else:
            existing = posts_by_id[post_id]["_lab2"]
            if existing.get("reference_label") is None and lab2.get("reference_label"):
                existing["reference_label"] = lab2["reference_label"]
            if existing.get("exploratory_emotion") is None and lab2.get("exploratory_emotion"):
                existing["exploratory_emotion"] = lab2["exploratory_emotion"]

        model_version = lab2.get("model_version")
        if not model_version:
            continue
        pred_label = lab2.get("predicted_label")
        scores = {k: float(v) for k, v in (lab2.get("model_scores") or {}).items()}
        status = "ok" if pred_label else "error"
        predictions.append(
            make_prediction_row(
                post_id=post_id,
                model_version=model_version,
                predicted_label=pred_label,
                model_scores=scores,
                status=status,
                pipeline_run_id=row.get("pipeline_run_id", "legacy-migrate"),
                error_message=None if status == "ok" else "legacy missing prediction",
                confidence=float(scores[pred_label]) if pred_label and pred_label in scores else None,
            )
        )

    # Deduplicate predictions by (post_id, model_version), last wins
    pred_map = {(p["post_id"], p["model_version"]): p for p in predictions}
    posts = list(posts_by_id.values())
    write_jsonl_atomic(Path(posts_out), posts)
    write_jsonl_atomic(Path(predictions_out), list(pred_map.values()))
    return len(posts), len(pred_map)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--errors", type=Path, default=DEFAULT_ERRORS)
    parser.add_argument(
        "--method",
        choices=["baseline", "llm", "both"],
        default="both",
    )
    parser.add_argument("--merge-reference", action="store_true")
    parser.add_argument("--select-few-shot", action="store_true")
    parser.add_argument(
        "--from-legacy",
        type=Path,
        default=None,
        help="Migrate a legacy multi-model posts_labeled.jsonl without API calls",
    )
    args = parser.parse_args()

    if args.select_few_shot:
        examples = select_few_shot_examples(samples_per_class=2)
        saved = save_few_shot_examples(examples)
        print(f"Saved {len(examples)} few-shot examples to {saved}")
        return 0

    if args.from_legacy is not None:
        n_posts, n_preds = migrate_legacy_labeled(
            args.from_legacy,
            posts_out=args.output,
            predictions_out=args.predictions,
        )
        print(
            f"Migrated legacy file → {n_posts} posts, {n_preds} predictions "
            f"({args.output}, {args.predictions})"
        )
        return 0

    if not Path(args.input).is_file():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    posts: list[dict[str, Any]] | None = None
    all_predictions: list[dict[str, Any]] = []
    all_errors: list[dict[str, Any]] = []

    if args.method in ("baseline", "both"):
        print("Training TF-IDF + Logistic Regression baseline...")
        posts, predictions, _ = run_baseline_classification(args.input)
        all_predictions.extend(predictions)
        print(f"  Baseline produced {len(predictions)} predictions")

    if args.method in ("llm", "both"):
        print("Running LLM classification (DeepSeek)...")
        llm_posts, predictions, errors = run_llm_classification(args.input)
        if posts is None:
            posts = llm_posts
        all_predictions.extend(predictions)
        all_errors.extend(errors)
        print(f"  LLM produced {len(predictions)} predictions, {len(errors)} errors")

    assert posts is not None

    if args.merge_reference:
        posts = merge_reference_labels(posts)
    else:
        print(
            "Note: --merge-reference not set. reference_label will be null.",
            file=sys.stderr,
        )

    write_jsonl_atomic(Path(args.output), posts)
    upsert_predictions(Path(args.predictions), all_predictions)
    # Errors are rebuilt atomically every run (never append-only).
    write_jsonl_atomic(Path(args.errors), all_errors)

    print(f"Wrote {len(posts)} unique posts to {args.output}")
    print(f"Wrote predictions to {args.predictions}")
    print(f"Wrote {len(all_errors)} error records to {args.errors}")

    pred_keys = [(p["post_id"], p["model_version"]) for p in all_predictions]
    if len(pred_keys) != len(set(pred_keys)):
        print("ERROR: duplicate (post_id, model_version) in this run", file=sys.stderr)
        return 1

    success = sum(1 for p in all_predictions if p["status"] == "ok")
    print(
        f"Accounting: {len(posts)} posts, {len(all_predictions)} predictions, "
        f"{success} ok, {len(all_errors)} failed"
    )
    return 0 if not all_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
