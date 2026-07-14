"""Lab 2 — Evaluation: compare baseline vs LLM on the frozen test split.

Computes:
- Macro-F1, Weighted-F1
- Per-class Precision, Recall, F1, Support
- Confusion matrix (saved as PNG)
- Critical-class recall (requests_or_urgent_needs, displaced_people_and_evacuations)

Outputs ``docs/project/evaluation.md`` and ``artifacts/figures/confusion_matrix.png``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "analyzed" / "posts_labeled.jsonl"
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


def load_labeled(path: str | Path) -> list[dict[str, Any]]:
    """Load posts_labeled.jsonl."""
    path = Path(path)
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def compute_metrics(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str],
) -> dict[str, Any]:
    """Compute classification metrics.

    Returns a dict with macro_f1, weighted_f1, per_class (list of dicts),
    and a full classification_report string.
    """
    from sklearn.metrics import (
        classification_report,
        confusion_matrix,
        f1_score,
        precision_recall_fscore_support,
    )

    # Filter out None predictions (LLM parse failures)
    excluded = sum(1 for p in y_pred if p is None)
    valid = [(t, p) for t, p in zip(y_true, y_pred) if p is not None]
    if not valid:
        return {
            "macro_f1": 0.0,
            "weighted_f1": 0.0,
            "per_class": [],
            "classification_report": "No valid predictions.",
            "confusion_matrix": None,
            "excluded_failures": excluded,
        }
    y_true_f, y_pred_f = zip(*valid)

    macro_f1 = float(f1_score(y_true_f, y_pred_f, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true_f, y_pred_f, average="weighted", zero_division=0))

    prec, rec, f1, support = precision_recall_fscore_support(
        y_true_f, y_pred_f, labels=labels, zero_division=0
    )

    per_class = []
    for lbl, p, r, f, s in zip(labels, prec, rec, f1, support):
        per_class.append({
            "label": lbl,
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1": round(float(f), 4),
            "support": int(s),
        })

    cm = confusion_matrix(y_true_f, y_pred_f, labels=labels)

    report = classification_report(
        y_true_f, y_pred_f, labels=labels, zero_division=0
    )

    return {
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_class": per_class,
        "classification_report": report,
        "confusion_matrix": cm,
        "excluded_failures": excluded,
    }


def plot_confusion_matrix(
    cm: np.ndarray,
    labels: list[str],
    title: str,
    output_path: str | Path,
) -> None:
    """Save a confusion matrix as a PNG figure."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(cm, cmap="Blues")

    # Label abbreviations for readability
    short_labels = [
        lbl.replace("_", "\n").replace("and", "&")
        for lbl in labels
    ]

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(short_labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(short_labels, fontsize=8)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Reference")
    ax.set_title(title)

    # Annotate with counts
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(
                j, i, int(cm[i, j]),
                ha="center", va="center",
                color="white" if cm[i, j] > cm.max() / 2 else "black",
                fontsize=7,
            )

    plt.colorbar(im, ax=ax, shrink=0.8)
    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def evaluate_model(
    records: list[dict[str, Any]],
    model_key: str,
    model_label: str,
) -> dict[str, Any]:
    """Extract y_true/y_pred for a specific model and compute metrics.

    ``model_key`` is the value in ``_lab2.model_version`` to filter by
    (e.g., "tfidf-lr-baseline-v1" or the DeepSeek model name). Use the
    ``predicted_label`` approach: we assume the records with non-null
    predicted_label belong to this model.
    """
    y_true: list[str] = []
    y_pred: list[str] = []

    for r in records:
        lab2 = r.get("_lab2", {}) or {}
        ref = lab2.get("reference_label")
        pred = lab2.get("predicted_label")
        model_ver = lab2.get("model_version", "")

        # Only include records that match this model version exactly
        if model_ver != model_key:
            continue
        if ref is None:
            continue  # skip records without reference labels

        y_true.append(ref)
        y_pred.append(pred)

    if not y_true:
        return {
            "model": model_label,
            "model_version": model_key,
            "total_records": 0,
            "error": "No matching records found.",
        }

    metrics = compute_metrics(y_true, y_pred, ALL_LABELS)
    return {
        "model": model_label,
        "model_version": model_key,
        "total_records": len(y_true),
        **metrics,
    }


def find_model_versions(records: list[dict[str, Any]]) -> list[str]:
    """Discover distinct model versions present in the records."""
    versions: set[str] = set()
    for r in records:
        ver = (r.get("_lab2") or {}).get("model_version", "")
        if ver:
            versions.add(ver)
    return sorted(versions)


def generate_evaluation_report(
    input_path: str | Path,
    output_doc: str | Path,
    figures_dir: str | Path,
) -> str:
    """Run full evaluation and write the markdown report.

    Returns the markdown string.
    """
    records = load_labeled(input_path)

    # Group records by model_version
    versions = find_model_versions(records)

    all_results: list[dict[str, Any]] = []
    for ver in versions:
        result = evaluate_model(records, ver, ver)
        all_results.append(result)

        # Generate confusion matrix figure if data available
        if result.get("confusion_matrix") is not None:
            safe_name = ver.replace("/", "_").replace(" ", "_")
            fig_path = Path(figures_dir) / f"confusion_matrix_{safe_name}.png"
            plot_confusion_matrix(
                result["confusion_matrix"],
                ALL_LABELS,
                f"Confusion Matrix — {ver}",
                fig_path,
            )

    # Build markdown report
    lines = [
        "# Lab 2 — Classification Evaluation Report",
        "",
        f"**Records evaluated**: {len(records)}",
        f"**Model versions found**: {len(versions)}",
        "",
        "---",
        "",
    ]

    for result in all_results:
        lines.append(f"## Model: {result['model']}")
        lines.append("")
        lines.append(f"- **Records**: {result.get('total_records', 'N/A')}")
        lines.append(f"- **Macro-F1**: {result.get('macro_f1', 'N/A')}")
        lines.append(f"- **Weighted-F1**: {result.get('weighted_f1', 'N/A')}")
        lines.append("")

        if result.get("per_class"):
            lines.append("### Per-Class Metrics")
            lines.append("")
            lines.append(
                "| Label | Precision | Recall | F1 | Support |"
            )
            lines.append(
                "|-------|-----------|--------|----|---------|"
            )
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

    # Comparison section if two models
    if len(all_results) >= 2:
        lines.append("## Model Comparison")
        lines.append("")
        lines.append("| Metric | Baseline (TF-IDF+LR) | LLM (DeepSeek) |")
        lines.append("|--------|----------------------|----------------|")

        # Match by model_version, not list index (alphabetical order is unreliable)
        def _by_model(versions: list[dict], keyword: str) -> dict:
            for v in versions:
                if keyword in v.get("model_version", ""):
                    return v
            return {}

        baseline = _by_model(all_results, "tfidf")
        llm = _by_model(all_results, "deepseek")

        def _get(key: str, results: dict) -> str:
            val = results.get(key, "N/A")
            return str(val)

        lines.append(
            f"| Macro-F1 | {_get('macro_f1', baseline)} | {_get('macro_f1', llm)} |"
        )
        lines.append(
            f"| Weighted-F1 | {_get('weighted_f1', baseline)} | {_get('weighted_f1', llm)} |"
        )

        # Critical class recall
        lines.append("")
        lines.append("### Critical Class Recall")
        lines.append("")
        lines.append("| Critical Class | Baseline Recall | LLM Recall |")
        lines.append("|----------------|-----------------|------------|")

        critical = [
            "requests_or_urgent_needs",
            "displaced_people_and_evacuations",
        ]
        for cc in critical:
            b_recall = "N/A"
            l_recall = "N/A"
            for pc in baseline.get("per_class", []):
                if pc["label"] == cc:
                    b_recall = str(pc["recall"])
            for pc in llm.get("per_class", []):
                if pc["label"] == cc:
                    l_recall = str(pc["recall"])
            lines.append(f"| {cc} | {b_recall} | {l_recall} |")

        lines.append("")

    # Limitations
    lines.extend([
        "## Limitations & Usage Notes",
        "",
        "- Metrics are computed on the frozen HumAID Kerala test split (1,582 records).",
        "- Labels are highly imbalanced; rely on Macro-F1, not Accuracy.",
        "- `model_scores` are NOT calibrated probabilities.",
        "- Reference labels are dataset annotations, not verified ground-truth facts.",
        "- Results do not generalize to other events, languages, or time periods.",
        "",
        "---",
        "",
        "*Report auto-generated by `src/lab2_analysis/evaluate.py`.*",
    ])

    markdown = "\n".join(lines)

    # Write to file
    output_path = Path(output_doc)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    return markdown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to posts_labeled.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_EVAL_DOC,
        help="Path for evaluation.md",
    )
    parser.add_argument(
        "--figures",
        type=Path,
        default=DEFAULT_FIG_DIR,
        help="Directory for confusion matrix figures",
    )
    args = parser.parse_args()

    if not Path(args.input).is_file():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1

    report = generate_evaluation_report(args.input, args.output, args.figures)
    print(f"Evaluation report written to {args.output}")
    print()
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
