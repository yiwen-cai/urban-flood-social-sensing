"""Generate a course analysis briefing from metrics and evidence.

Reads metrics.json + evidence.jsonl → Jinja2 template → briefing.md.
All numbers come from pre-computed metrics. LLM is NOT used to invent facts.
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
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metrics", type=Path,
        default=PROJECT_ROOT / "data" / "output" / "metrics.json",
    )
    parser.add_argument(
        "--evidence", type=Path,
        default=PROJECT_ROOT / "data" / "output" / "evidence.jsonl",
    )
    parser.add_argument(
        "--output", type=Path,
        default=PROJECT_ROOT / "data" / "output" / "briefing.md",
    )
    args = parser.parse_args()

    metrics = load_json(args.metrics)
    evidence = load_jsonl(args.evidence)
    # Deduplicate evidence records (urgent records appear twice: top-N + all-urgent)
    seen = set()
    unique_evidence = []
    for e in evidence:
        key = (e["source_ref"], e["selection_reason"])
        if key not in seen:
            seen.add(key)
            unique_evidence.append(e)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(TEMPLATE_NAME)

    cat_dist = metrics["category_distribution"]
    min_count = min(cat_dist.values()) if cat_dist else 0
    gap_labels = [l for l in LABELS if cat_dist.get(l, 0) == min_count]

    briefing = template.render(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        metrics=metrics,
        evidence_records=unique_evidence,
        labels=LABELS,
        emotions=EMOTIONS,
        label_name_map=LABEL_NAME_MAP,
        emotion_name_map=EMOTION_NAME_MAP,
        gap_labels=gap_labels,
        min_count=min_count,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(briefing, encoding="utf-8")
    print(f"briefing: {args.output}")


if __name__ == "__main__":
    main()
