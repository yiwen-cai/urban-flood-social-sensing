"""Generate static figures from D07 metrics.json (v2.0.0)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LABEL_NAMES = {
    "caution_and_advice": "Caution & Advice",
    "displaced_people_and_evacuations": "Displaced & Evacuations",
    "infrastructure_and_utility_damage": "Infrastructure Damage",
    "injured_or_dead_people": "Injured or Dead",
    "not_humanitarian": "Not Humanitarian",
    "other_relevant_information": "Other Relevant",
    "requests_or_urgent_needs": "Urgent Needs",
    "rescue_volunteering_or_donation_effort": "Rescue & Donation",
    "sympathy_and_support": "Sympathy & Support",
}
EMOTION_NAMES = {
    "fear_or_anxiety": "Fear/Anxiety",
    "anger": "Anger",
    "sadness": "Sadness",
    "positive_support": "Positive Support",
    "neutral_or_unclear": "Neutral/Unclear",
}
COLORS = [
    "#4C72B0",
    "#55A868",
    "#C44E52",
    "#8172B2",
    "#CCB974",
    "#64B5CD",
    "#DD8452",
    "#8C8C8C",
    "#937860",
]
EMO_COLORS = ["#FF6B6B", "#FF0000", "#4ECDC4", "#45B7D1", "#96CEB4"]


def _selected_model(metrics: dict, model_version: str | None = None) -> str | None:
    versions = metrics.get("model_versions") or []
    if model_version and model_version in versions:
        return model_version
    if not versions:
        return None
    # Prefer LLM then baseline when present
    for preferred in ("deepseek", "tfidf"):
        for version in versions:
            if preferred in version:
                return version
    return versions[0]


def category_distribution(metrics: dict, output: Path) -> None:
    labels = list(LABEL_NAMES)
    dist = metrics.get("reference_label_distribution") or {}
    counts = [dist.get(label, 0) for label in labels]
    names = [LABEL_NAMES[label] for label in labels]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(names, counts, color=COLORS)
    ax.set_xlabel("Count")
    ax.set_title("Humanitarian Category Distribution (unique posts)")
    ax.invert_yaxis()
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            va="center",
            fontsize=9,
        )
    fig.subplots_adjust(left=0.25, right=0.95, top=0.95, bottom=0.08)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"figure: {output}")


def emotion_distribution(metrics: dict, output: Path) -> None:
    emotions = list(EMOTION_NAMES)
    dist = metrics.get("emotion_distribution") or {}
    counts = [dist.get(emotion, 0) for emotion in emotions]
    if sum(counts) == 0:
        return
    names = [EMOTION_NAMES[emotion] for emotion in emotions]
    filtered = [(n, c, col) for n, c, col in zip(names, counts, EMO_COLORS) if c > 0]
    if not filtered:
        return
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        [f[1] for f in filtered],
        labels=[f[0] for f in filtered],
        colors=[f[2] for f in filtered],
        autopct="%1.1f%%",
        startangle=90,
    )
    ax.set_title("Exploratory Emotion Distribution (annotated subset)")
    fig.subplots_adjust(left=0.12, right=0.95, top=0.93, bottom=0.12)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"figure: {output}")


def emotion_bar(metrics: dict, output: Path) -> None:
    emotions = list(EMOTION_NAMES)
    dist = metrics.get("emotion_distribution") or {}
    counts = [dist.get(emotion, 0) for emotion in emotions]
    if sum(counts) == 0:
        return
    names = [EMOTION_NAMES[emotion] for emotion in emotions]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(names, counts, color=EMO_COLORS)
    ax.set_ylabel("Count")
    ax.set_title("Exploratory Emotion Distribution (annotated subset)")
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(count),
            ha="center",
            fontsize=10,
        )
    fig.subplots_adjust(left=0.1, right=0.95, top=0.93, bottom=0.12)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"figure: {output}")


def accuracy_chart(
    metrics: dict,
    output: Path,
    *,
    model_version: str | None = None,
) -> None:
    version = _selected_model(metrics, model_version)
    if version is None:
        return
    per_class = (metrics.get("per_model") or {}).get(version, {}).get("per_class") or {}
    labels = list(LABEL_NAMES)
    precs = [per_class.get(label, {}).get("precision", 0) for label in labels]
    recs = [per_class.get(label, {}).get("recall", 0) for label in labels]
    f1s = [per_class.get(label, {}).get("f1", 0) for label in labels]
    names = [LABEL_NAMES[label] for label in labels]

    x = range(len(names))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar([i - width for i in x], precs, width, label="Precision", color="#4C72B0")
    ax.bar(x, recs, width, label="Recall", color="#55A868")
    ax.bar([i + width for i in x], f1s, width, label="F1", color="#C44E52")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Score")
    ax.set_title(f"Per-Class Precision / Recall / F1 — {version}")
    ax.legend()
    ax.set_ylim(0, 1.1)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"figure: {output}")


def confusion_matrix_chart(
    metrics: dict,
    output: Path,
    *,
    model_version: str | None = None,
) -> None:
    version = _selected_model(metrics, model_version)
    if version is None:
        return
    cm = (metrics.get("per_model") or {}).get(version, {}).get("confusion_matrix") or {}
    if not cm:
        return
    labels = list(LABEL_NAMES)
    matrix = [[cm.get(ref, {}).get(pred, 0) for pred in labels] for ref in labels]
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(matrix, cmap="Blues")
    short = [LABEL_NAMES[label].replace(" ", "\n") for label in labels]
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(short, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(short, fontsize=8)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Reference")
    ax.set_title(f"Confusion Matrix — {version}")
    vmax = max((max(row) for row in matrix), default=0)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(
                j,
                i,
                matrix[i][j],
                ha="center",
                va="center",
                color="white" if matrix[i][j] > vmax / 2 else "black",
                fontsize=7,
            )
    plt.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"figure: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metrics",
        type=Path,
        default=PROJECT_ROOT / "data" / "output" / "metrics.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "figures",
    )
    parser.add_argument("--model-version", type=str, default=None)
    args = parser.parse_args()

    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    category_distribution(metrics, args.output_dir / "category_distribution.png")
    emotion_distribution(metrics, args.output_dir / "emotion_distribution.png")
    emotion_bar(metrics, args.output_dir / "emotion_bar.png")
    accuracy_chart(
        metrics,
        args.output_dir / "accuracy_chart.png",
        model_version=args.model_version,
    )
    confusion_matrix_chart(
        metrics,
        args.output_dir / "confusion_matrix.png",
        model_version=args.model_version,
    )


if __name__ == "__main__":
    main()
