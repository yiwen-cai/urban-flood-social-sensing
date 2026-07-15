"""Generate static figures from metrics.json for offline use in dashboard and slides.

Labels use English (DejaVu Sans covers ASCII) to avoid CJK font dependencies.
"""
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
COLORS = ["#4C72B0", "#55A868", "#C44E52", "#8172B2", "#CCB974", "#64B5CD",
          "#DD8452", "#8C8C8C", "#937860"]
EMO_COLORS = ["#FF6B6B", "#FF0000", "#4ECDC4", "#45B7D1", "#96CEB4"]


def category_distribution(metrics: dict, output: Path) -> None:
    labels = list(LABEL_NAMES)
    counts = [metrics["category_distribution"].get(l, 0) for l in labels]
    names = [LABEL_NAMES[l] for l in labels]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(names, counts, color=COLORS)
    ax.set_xlabel("Count")
    ax.set_title("Humanitarian Category Distribution")
    ax.invert_yaxis()
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(count), va="center", fontsize=9)
    fig.subplots_adjust(left=0.25, right=0.95, top=0.95, bottom=0.08)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"figure: {output}")


def emotion_distribution(metrics: dict, output: Path) -> None:
    emotions = list(EMOTION_NAMES)
    counts = [metrics["emotion_distribution"].get(e, 0) for e in emotions]
    if sum(counts) == 0:
        return  # no emotion data available
    names = [EMOTION_NAMES[e] for e in emotions]

    filtered = [(n, c, col) for n, c, col in zip(names, counts, EMO_COLORS) if c > 0]
    if not filtered:
        return

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie([f[1] for f in filtered], labels=[f[0] for f in filtered],
           colors=[f[2] for f in filtered], autopct="%1.1f%%", startangle=90)
    ax.set_title("Exploratory Emotion Distribution")
    fig.subplots_adjust(left=0.12, right=0.95, top=0.93, bottom=0.12)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"figure: {output}")


def emotion_bar(metrics: dict, output: Path) -> None:
    emotions = list(EMOTION_NAMES)
    counts = [metrics["emotion_distribution"].get(e, 0) for e in emotions]
    if sum(counts) == 0:
        return  # no emotion data available
    names = [EMOTION_NAMES[e] for e in emotions]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(names, counts, color=EMO_COLORS)
    ax.set_ylabel("Count")
    ax.set_title("Exploratory Emotion Distribution")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(count), ha="center", fontsize=10)
    fig.subplots_adjust(left=0.1, right=0.95, top=0.93, bottom=0.12)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"figure: {output}")


def evidence_status_chart(metrics: dict, output: Path) -> None:
    dist = metrics.get("evidence_status_distribution", {})
    if not dist:
        return

    names_map = {"dataset_record": "Dataset", "human_labeled": "Human",
                 "model_prediction": "Model"}
    names = [names_map.get(k, k) for k in dist]
    counts = list(dist.values())

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(names, counts, color=["#55A868", "#4C72B0", "#C44E52"])
    ax.set_ylabel("Count")
    ax.set_title("Evidence Status Distribution")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(count), ha="center", fontsize=10)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"figure: {output}")


def accuracy_chart(metrics: dict, output: Path) -> None:
    labels = list(LABEL_NAMES)
    precs = [metrics["per_class_stats"].get(l, {}).get("precision", 0) for l in labels]
    recs = [metrics["per_class_stats"].get(l, {}).get("recall", 0) for l in labels]
    f1s = [metrics["per_class_stats"].get(l, {}).get("f1", 0) for l in labels]
    names = [LABEL_NAMES[l] for l in labels]

    x = range(len(names))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar([i - width for i in x], precs, width, label="Precision", color="#4C72B0")
    ax.bar(x, recs, width, label="Recall", color="#55A868")
    ax.bar([i + width for i in x], f1s, width, label="F1", color="#C44E52")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Score")
    ax.set_title("Per-Class Precision / Recall / F1")
    ax.legend()
    ax.set_ylim(0, 1.1)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"figure: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path,
                        default=PROJECT_ROOT / "data" / "output" / "metrics.json")
    parser.add_argument("--output-dir", type=Path,
                        default=PROJECT_ROOT / "artifacts" / "figures")
    args = parser.parse_args()

    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    category_distribution(metrics, args.output_dir / "category_distribution.png")
    emotion_distribution(metrics, args.output_dir / "emotion_distribution.png")
    emotion_bar(metrics, args.output_dir / "emotion_bar.png")
    evidence_status_chart(metrics, args.output_dir / "evidence_status.png")
    accuracy_chart(metrics, args.output_dir / "accuracy_chart.png")


if __name__ == "__main__":
    main()
