"""Lab 2 — Evaluation: join posts with predictions and compare models.

Primary metrics use the full corpus denominator (posts with a reference
label, typically 1,582) plus coverage. Accuracy/F1 on successful predictions
only are reported as secondary metrics.

Outputs ``docs/project/evaluation.md`` and confusion-matrix PNGs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POSTS = PROJECT_ROOT / "data" / "analyzed" / "posts_labeled.jsonl"
DEFAULT_PREDICTIONS = PROJECT_ROOT / "data" / "analyzed" / "predictions.jsonl"
DEFAULT_EVAL_DOC = PROJECT_ROOT / "docs" / "project" / "evaluation.md"
DEFAULT_FIG_DIR = PROJECT_ROOT / "artifacts" / "figures"

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


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_labeled(path: str | Path) -> list[dict[str, Any]]:
    """Backward-compatible alias for loading posts."""
    return load_jsonl(path)


def compute_metrics(
    y_true: list[str],
    y_pred: list[str | None],
    labels: list[str],
    *,
    full_denominator: bool = True,
) -> dict[str, Any]:
    """Compute classification metrics.

    When ``full_denominator`` is True (default), None predictions remain in
    the denominator for accuracy/coverage accounting and are excluded only
    from sklearn F1/confusion (reported separately via successful-only block).
    """
    from sklearn.metrics import (
        classification_report,
        confusion_matrix,
        f1_score,
        precision_recall_fscore_support,
    )

    n_total = len(y_true)
    excluded = sum(1 for p in y_pred if p is None)
    n_success = n_total - excluded
    coverage = (n_success / n_total) if n_total else 0.0

    correct_full = sum(1 for t, p in zip(y_true, y_pred) if p is not None and t == p)
    accuracy_full = (correct_full / n_total) if n_total else 0.0

    valid = [(t, p) for t, p in zip(y_true, y_pred) if p is not None]
    if not valid:
        return {
            "macro_f1": 0.0,
            "weighted_f1": 0.0,
            "accuracy": round(accuracy_full, 4) if full_denominator else 0.0,
            "accuracy_on_successful_only": None,
            "coverage": round(coverage, 4),
            "per_class": [],
            "classification_report": "No valid predictions.",
            "confusion_matrix": None,
            "excluded_failures": excluded,
            "n_total": n_total,
            "n_success": n_success,
        }

    y_true_f, y_pred_f = zip(*valid)
    correct_success = sum(1 for t, p in zip(y_true_f, y_pred_f) if t == p)
    accuracy_success = correct_success / len(y_true_f)

    macro_f1 = float(f1_score(y_true_f, y_pred_f, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true_f, y_pred_f, average="weighted", zero_division=0))
    prec, rec, f1, support = precision_recall_fscore_support(
        y_true_f, y_pred_f, labels=labels, zero_division=0
    )
    per_class = [
        {
            "label": lbl,
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1": round(float(f), 4),
            "support": int(s),
        }
        for lbl, p, r, f, s in zip(labels, prec, rec, f1, support)
    ]
    cm = confusion_matrix(y_true_f, y_pred_f, labels=labels)
    report = classification_report(y_true_f, y_pred_f, labels=labels, zero_division=0)

    return {
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "accuracy": round(accuracy_full, 4),
        "accuracy_on_successful_only": round(accuracy_success, 4),
        "coverage": round(coverage, 4),
        "per_class": per_class,
        "classification_report": report,
        "confusion_matrix": cm,
        "excluded_failures": excluded,
        "n_total": n_total,
        "n_success": n_success,
    }


def plot_confusion_matrix(
    cm: np.ndarray,
    labels: list[str],
    title: str,
    output_path: str | Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(cm, cmap="Blues")
    short_labels = [lbl.replace("_", "\n").replace("and", "&") for lbl in labels]
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(short_labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(short_labels, fontsize=8)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Reference")
    ax.set_title(title)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(
                j,
                i,
                int(cm[i, j]),
                ha="center",
                va="center",
                color="white" if cm[i, j] > cm.max() / 2 else "black",
                fontsize=7,
            )
    plt.colorbar(im, ax=ax, shrink=0.8)
    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def find_model_versions(
    records: list[dict[str, Any]] | None = None,
    *,
    predictions: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Discover distinct model versions from predictions (preferred) or legacy posts."""
    versions: set[str] = set()
    if predictions is not None:
        for row in predictions:
            ver = row.get("model_version", "")
            if ver:
                versions.add(ver)
        return sorted(versions)
    for r in records or []:
        ver = (r.get("_lab2") or {}).get("model_version", "")
        if ver:
            versions.add(ver)
    return sorted(versions)


def evaluate_model(
    posts: list[dict[str, Any]],
    model_key: str,
    model_label: str,
    *,
    predictions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Join posts with predictions for ``model_key`` and compute metrics."""
    posts_with_ref = {
        p["post_id"]: p
        for p in posts
        if (p.get("_lab2") or {}).get("reference_label") is not None
    }

    if predictions is None:
        # Legacy path: predictions embedded in duplicated post rows
        y_true: list[str] = []
        y_pred: list[str | None] = []
        for r in posts:
            lab2 = r.get("_lab2") or {}
            if lab2.get("model_version") != model_key:
                continue
            ref = lab2.get("reference_label")
            if ref is None:
                continue
            y_true.append(ref)
            y_pred.append(lab2.get("predicted_label"))
    else:
        pred_by_id = {
            row["post_id"]: row
            for row in predictions
            if row.get("model_version") == model_key
        }
        y_true = []
        y_pred = []
        for post_id, post in sorted(posts_with_ref.items()):
            ref = (post.get("_lab2") or {})["reference_label"]
            row = pred_by_id.get(post_id)
            if row is None:
                y_true.append(ref)
                y_pred.append(None)
            elif row.get("status") == "error" or row.get("predicted_label") is None:
                y_true.append(ref)
                y_pred.append(None)
            else:
                y_true.append(ref)
                y_pred.append(row["predicted_label"])

    if not y_true:
        return {
            "model": model_label,
            "model_version": model_key,
            "total_records": 0,
            "error": "No matching records found.",
        }

    metrics = compute_metrics(y_true, y_pred, ALL_LABELS, full_denominator=True)
    return {
        "model": model_label,
        "model_version": model_key,
        "total_records": metrics["n_total"],
        **metrics,
    }


def generate_evaluation_report(
    posts_path: str | Path,
    output_doc: str | Path,
    figures_dir: str | Path,
    *,
    predictions_path: str | Path | None = None,
) -> str:
    posts = load_jsonl(posts_path)
    predictions: list[dict[str, Any]] | None = None
    if predictions_path and Path(predictions_path).is_file():
        predictions = load_jsonl(predictions_path)

    versions = find_model_versions(posts, predictions=predictions)
    unique_posts = len({p["post_id"] for p in posts})
    with_ref = sum(
        1 for p in posts if (p.get("_lab2") or {}).get("reference_label") is not None
    )

    all_results: list[dict[str, Any]] = []
    for ver in versions:
        result = evaluate_model(posts, ver, ver, predictions=predictions)
        all_results.append(result)
        if result.get("confusion_matrix") is not None:
            safe_name = ver.replace("/", "_").replace(" ", "_")
            fig_path = Path(figures_dir) / f"confusion_matrix_{safe_name}.png"
            plot_confusion_matrix(
                result["confusion_matrix"],
                ALL_LABELS,
                f"Confusion Matrix — {ver}",
                fig_path,
            )

    lines = [
        "# Lab 2 — Classification Evaluation Report",
        "",
        f"**Unique posts**: {unique_posts}",
        f"**Posts with reference label**: {with_ref}",
        f"**Model versions found**: {len(versions)}",
        "",
        "Primary metrics use the full reference-labeled denominator and report coverage.",
        "Successful-prediction-only accuracy is secondary.",
        "",
        "---",
        "",
    ]

    for result in all_results:
        lines.append(f"## Model: {result['model']}")
        lines.append("")
        lines.append(f"- **Denominator (with reference)**: {result.get('total_records', 'N/A')}")
        lines.append(f"- **Coverage**: {result.get('coverage', 'N/A')}")
        lines.append(f"- **Accuracy (full denominator)**: {result.get('accuracy', 'N/A')}")
        lines.append(
            f"- **Accuracy (successful only, secondary)**: "
            f"{result.get('accuracy_on_successful_only', 'N/A')}"
        )
        lines.append(f"- **Macro-F1 (successful only)**: {result.get('macro_f1', 'N/A')}")
        lines.append(f"- **Weighted-F1 (successful only)**: {result.get('weighted_f1', 'N/A')}")
        excluded = result.get("excluded_failures", 0)
        if excluded:
            lines.append(f"- **Excluded / failed predictions**: {excluded}")
        lines.append("")

        if result.get("per_class"):
            lines.append("### Per-Class Metrics")
            lines.append("")
            lines.append("| Label | Precision | Recall | F1 | Support |")
            lines.append("|-------|-----------|--------|----|---------|")
            for pc in result["per_class"]:
                lines.append(
                    f"| {pc['label']} | {pc['precision']} | {pc['recall']} "
                    f"| {pc['f1']} | {pc['support']} |"
                )
            lines.append("")

        if result.get("classification_report"):
            lines.append("### Classification Report (sklearn)")
            lines.append("")
            lines.append("```")
            lines.append(result["classification_report"].strip())
            lines.append("```")
            lines.append("")
        lines.append("---")
        lines.append("")

    if len(all_results) >= 2:
        lines.append("## Model Comparison")
        lines.append("")
        lines.append("| Metric | Baseline (TF-IDF+LR) | LLM (DeepSeek) |")
        lines.append("|--------|----------------------|----------------|")

        def _by_model(keyword: str) -> dict:
            for v in all_results:
                if keyword in v.get("model_version", ""):
                    return v
            return {}

        baseline = _by_model("tfidf")
        llm = _by_model("deepseek")

        def _get(key: str, results: dict) -> str:
            return str(results.get(key, "N/A"))

        lines.append(f"| Coverage | {_get('coverage', baseline)} | {_get('coverage', llm)} |")
        lines.append(f"| Accuracy (full) | {_get('accuracy', baseline)} | {_get('accuracy', llm)} |")
        lines.append(
            f"| Accuracy (successful only) | {_get('accuracy_on_successful_only', baseline)} "
            f"| {_get('accuracy_on_successful_only', llm)} |"
        )
        lines.append(f"| Macro-F1 | {_get('macro_f1', baseline)} | {_get('macro_f1', llm)} |")
        lines.append(
            f"| Weighted-F1 | {_get('weighted_f1', baseline)} | {_get('weighted_f1', llm)} |"
        )
        lines.append("")
        lines.append("### Critical Class Recall")
        lines.append("")
        lines.append("| Critical Class | Baseline Recall | LLM Recall |")
        lines.append("|----------------|-----------------|------------|")
        for cc in ("requests_or_urgent_needs", "displaced_people_and_evacuations"):
            b_recall = next(
                (str(pc["recall"]) for pc in baseline.get("per_class", []) if pc["label"] == cc),
                "N/A",
            )
            l_recall = next(
                (str(pc["recall"]) for pc in llm.get("per_class", []) if pc["label"] == cc),
                "N/A",
            )
            lines.append(f"| {cc} | {b_recall} | {l_recall} |")
        lines.append("")

    lines.extend(
        [
            "## Limitations & Usage Notes",
            "",
            "- Metrics are computed on the frozen HumAID Kerala test split (1,582 unique posts).",
            "- Primary accuracy uses the full reference denominator; failures reduce coverage and accuracy.",
            "- Labels are highly imbalanced; rely on Macro-F1, not Accuracy alone.",
            "- `model_scores` / confidence are NOT calibrated probabilities.",
            "- Reference labels are dataset annotations, not verified ground-truth facts.",
            "",
            "---",
            "",
            "*Report auto-generated by `src/lab2_analysis/evaluate.py`.*",
        ]
    )

    markdown = "\n".join(lines)
    output_path = Path(output_doc)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_POSTS, help="posts_labeled.jsonl")
    parser.add_argument(
        "--predictions",
        type=Path,
        default=DEFAULT_PREDICTIONS,
        help="predictions.jsonl keyed by (post_id, model_version)",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_EVAL_DOC)
    parser.add_argument("--figures", type=Path, default=DEFAULT_FIG_DIR)
    args = parser.parse_args()

    if not Path(args.input).is_file():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1

    preds = args.predictions if Path(args.predictions).is_file() else None
    if preds is None:
        print(
            f"Predictions file not found ({args.predictions}); "
            "falling back to legacy embedded _lab2 predictions if present.",
            file=sys.stderr,
        )

    report = generate_evaluation_report(
        args.input,
        args.output,
        args.figures,
        predictions_path=preds,
    )
    print(f"Evaluation report written to {args.output}")
    print()
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
