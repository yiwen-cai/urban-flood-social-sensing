#!/usr/bin/env bash
# Unified offline pipeline for the full dashboard.
# Default: real legacy migration when available, else synthetic fixture.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MODE="auto"
FIXTURE_MODE=0
OFFLINE_MODE=0
LEGACY_PATH="$ROOT/data/analyzed/posts_labeled.legacy.jsonl"

for arg in "$@"; do
  case "$arg" in
    --fixture) FIXTURE_MODE=1 ;;
    --offline) OFFLINE_MODE=1 ;;
    --real) MODE="real" ;;
    *)
      echo "unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ "$FIXTURE_MODE" -eq 1 ]]; then
  MODE="fixture"
elif [[ "$MODE" == "auto" ]]; then
  if [[ -f "$LEGACY_PATH" ]]; then
    MODE="real"
  else
    MODE="fixture"
  fi
fi

if [[ "$MODE" == "fixture" && "$OFFLINE_MODE" -ne 1 ]]; then
  echo "fixture mode requires --offline" >&2
  exit 1
fi

if [[ "$MODE" == "real" && ! -f "$LEGACY_PATH" ]]; then
  echo "real mode requires $LEGACY_PATH" >&2
  exit 1
fi

PYTHON="${PYTHON:-python3}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

export MPLCONFIGDIR="${MPLCONFIGDIR:-$ROOT/data/cache/matplotlib}"
mkdir -p "$MPLCONFIGDIR" data/processed data/analyzed data/output artifacts/figures data/cache

echo "== unit / schema / contract tests =="
"$PYTHON" -m pytest tests/ -q

if [[ "$MODE" == "real" ]]; then
  echo "== migrate legacy posts + predictions (no API) =="
  "$PYTHON" -m src.lab2_analysis.classify --from-legacy "$LEGACY_PATH"
else
  echo "== stage Lab 1 fixture posts =="
  cp tests/fixtures/sample_posts.jsonl data/processed/posts_clean.fixture.jsonl
  cp tests/fixtures/sample_posts.jsonl data/analyzed/posts_labeled.jsonl

  echo "== simulate two-model predictions (offline, no API) =="
  "$PYTHON" - <<'PY'
from pathlib import Path
import json
from src.lab2_analysis.classify import make_prediction_row, write_jsonl_atomic

posts = [
    json.loads(line)
    for line in Path("data/analyzed/posts_labeled.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
predictions = []
for post in posts:
    ref = (post.get("_lab2") or {}).get("reference_label") or "other_relevant_information"
    predictions.append(
        make_prediction_row(
            post_id=post["post_id"],
            model_version="fixture-v1",
            predicted_label=ref,
            model_scores={ref: 0.93},
            status="ok",
            pipeline_run_id=post.get("pipeline_run_id", "fixture-offline"),
            confidence=0.93,
        )
    )
    if post["post_id"] in {"fixture-001", "fixture-013", "fixture-015"}:
        alt = "other_relevant_information" if ref != "other_relevant_information" else "not_humanitarian"
        predictions.append(
            make_prediction_row(
                post_id=post["post_id"],
                model_version="fixture-baseline-v1",
                predicted_label=alt,
                model_scores={alt: 0.55},
                status="ok",
                pipeline_run_id=post.get("pipeline_run_id", "fixture-offline"),
                confidence=0.55,
            )
        )
    elif post["post_id"] == "fixture-020":
        predictions.append(
            make_prediction_row(
                post_id=post["post_id"],
                model_version="fixture-baseline-v1",
                predicted_label=None,
                model_scores={},
                status="error",
                pipeline_run_id=post.get("pipeline_run_id", "fixture-offline"),
                error_message="synthetic timeout",
                confidence=None,
            )
        )
write_jsonl_atomic(Path("data/analyzed/predictions.jsonl"), predictions)
print(f"wrote {len(posts)} posts and {len(predictions)} predictions")
PY
fi

echo "== Lab 2 evaluation =="
"$PYTHON" -m src.lab2_analysis.evaluate \
  --input data/analyzed/posts_labeled.jsonl \
  --predictions data/analyzed/predictions.jsonl \
  --output docs/project/evaluation.md \
  --figures artifacts/figures

echo "== D07 metrics + evidence (full dashboard) =="
"$PYTHON" -m src.lab3_decision.build_evidence \
  --posts data/analyzed/posts_labeled.jsonl \
  --predictions data/analyzed/predictions.jsonl \
  --metrics-output data/output/metrics.json \
  --evidence-output data/output/evidence.jsonl \
  --include-text

echo "== briefing + figures =="
"$PYTHON" -m src.lab3_decision.generate_briefing \
  --metrics data/output/metrics.json \
  --evidence data/output/evidence.jsonl \
  --output data/output/briefing.md
"$PYTHON" -m src.lab3_decision.figures \
  --metrics data/output/metrics.json \
  --output-dir artifacts/figures

echo "== dashboard data load smoke =="
MODE="$MODE" "$PYTHON" - <<'PY'
import json
import os
from pathlib import Path
from jsonschema import Draft202012Validator

mode = os.environ["MODE"]
metrics = json.loads(Path("data/output/metrics.json").read_text(encoding="utf-8"))
evidence = [
    json.loads(line)
    for line in Path("data/output/evidence.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
briefing = Path("data/output/briefing.md").read_text(encoding="utf-8")
mv = Draft202012Validator(json.loads(Path("schemas/metrics.schema.json").read_text(encoding="utf-8")))
ev = Draft202012Validator(json.loads(Path("schemas/evidence.schema.json").read_text(encoding="utf-8")))
mv.validate(metrics)
for row in evidence:
    ev.validate(row)

unique_posts = metrics["unique_posts"]
assert metrics["model_versions"]
assert briefing.strip()
assert Path("artifacts/figures/category_distribution.png").is_file()
assert evidence, "dashboard requires non-empty evidence"

if mode == "real":
    assert unique_posts == 1582
    assert "deepseek-v4-flash" in metrics["model_versions"]
    assert any(row.get("text_clean") for row in evidence)
else:
    assert unique_posts == 20
    assert all(row.get("text_clean") for row in evidence)

print(
    f"dashboard smoke ok ({mode}): {unique_posts} posts, "
    f"{len(metrics['model_versions'])} models, {len(evidence)} evidence rows"
)
PY

echo "pipeline ($MODE) passed"
