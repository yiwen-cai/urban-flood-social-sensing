"""Generate a course analysis briefing from D07 metrics and evidence.

All numbers come from pre-computed metrics. LLM is NOT used to invent facts.
Conclusions are rendered dynamically from metrics / selected model.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = PROJECT_ROOT / "config"
TEMPLATE_NAME = "briefing_template.md.j2"

LABEL_NAME_MAP = {
    "caution_and_advice": "警告与建议",
    "displaced_people_and_evacuations": "流离失所与疏散",
    "infrastructure_and_utility_damage": "基础设施与公用设施损坏",
    "injured_or_dead_people": "伤亡人员",
    "not_humanitarian": "非人道信息",
    "other_relevant_information": "其他相关信息",
    "requests_or_urgent_needs": "紧急需求",
    "rescue_volunteering_or_donation_effort": "救援、志愿与捐赠",
    "sympathy_and_support": "同情与支持",
}
EMOTION_NAME_MAP = {
    "fear_or_anxiety": "恐慌/焦虑",
    "anger": "愤怒",
    "sadness": "悲伤",
    "positive_support": "积极支持",
    "neutral_or_unclear": "中性/无法判断",
}
LABELS = list(LABEL_NAME_MAP)
EMOTIONS = list(EMOTION_NAME_MAP)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def select_model(metrics: dict, model_version: str | None) -> str | None:
    versions = metrics.get("model_versions") or []
    if model_version and model_version in versions:
        return model_version
    for preferred in ("deepseek", "tfidf"):
        for version in versions:
            if preferred in version:
                return version
    return versions[0] if versions else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metrics",
        type=Path,
        default=PROJECT_ROOT / "data" / "output" / "metrics.json",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=PROJECT_ROOT / "data" / "output" / "evidence.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "output" / "briefing.md",
    )
    parser.add_argument("--model-version", type=str, default=None)
    args = parser.parse_args()

    metrics = load_json(args.metrics)
    evidence = load_jsonl(args.evidence) if args.evidence.is_file() else []
    model_version = select_model(metrics, args.model_version)
    model_metrics = (metrics.get("per_model") or {}).get(model_version or "", {})

    seen: set[tuple] = set()
    unique_evidence = []
    for row in evidence:
        if model_version and row.get("model_version") not in (None, model_version):
            continue
        key = (row.get("post_id"), row.get("model_version"), row.get("selection_reason"))
        if key in seen:
            continue
        seen.add(key)
        unique_evidence.append(row)

    ref_dist = metrics.get("reference_label_distribution") or {}
    unique_posts = metrics.get("unique_posts") or sum(ref_dist.values()) or 1
    min_count = min(ref_dist.values()) if ref_dist else 0
    gap_labels = [label for label in LABELS if ref_dist.get(label, 0) == min_count]

    emotion_n = metrics.get("records_with_emotion") or 0
    emotion_dist = metrics.get("emotion_distribution") or {}
    top_emotion = None
    if emotion_dist:
        top_emotion = max(emotion_dist.items(), key=lambda item: item[1])[0]

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(TEMPLATE_NAME)
    briefing = template.render(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        metrics=metrics,
        model_version=model_version,
        model_metrics=model_metrics,
        evidence_records=unique_evidence,
        labels=LABELS,
        emotions=EMOTIONS,
        label_name_map=LABEL_NAME_MAP,
        emotion_name_map=EMOTION_NAME_MAP,
        gap_labels=gap_labels,
        min_count=min_count,
        unique_posts=unique_posts,
        emotion_n=emotion_n,
        top_emotion=top_emotion,
        ref_dist=ref_dist,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(briefing, encoding="utf-8")
    print(f"briefing: {args.output} (model={model_version})")


if __name__ == "__main__":
    main()
