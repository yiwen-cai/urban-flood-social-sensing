#!/usr/bin/env bash
# Full synthetic offline course pipeline.
# Requires no raw HumAID files, no API key, and no network.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

FIXTURE_MODE=0
OFFLINE_MODE=0

for arg in "$@"; do
  case "$arg" in
    --fixture) FIXTURE_MODE=1 ;;
    --offline) OFFLINE_MODE=1 ;;
    *)
      echo "unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ "$FIXTURE_MODE" -ne 1 || "$OFFLINE_MODE" -ne 1 ]]; then
  echo "only 'run_pipeline.sh --fixture --offline' is currently supported" >&2
  exit 1
fi

PYTHON="${PYTHON:-python3}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

echo "== unit / schema / contract tests =="
"$PYTHON" -m pytest tests/ -q

echo "== stage Lab 1 fixture posts =="
mkdir -p data/processed data/analyzed data/output artifacts/figures data/cache
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
    # Primary "LLM-like" model: exact match to reference
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
    # Baseline model: deliberately weaker / partial coverage
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

echo "== Lab 2 evaluation =="
"$PYTHON" -m src.lab2_analysis.evaluate \
  --input data/analyzed/posts_labeled.jsonl \
  --predictions data/analyzed/predictions.jsonl \
  --output docs/project/evaluation.md \
  --figures artifacts/figures

echo "== D07 metrics + evidence =="
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
"$PYTHON" - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator

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
assert metrics["unique_posts"] == 20
assert metrics["model_versions"]
assert "选用模型" in briefing or "model" in briefing.lower() or "fixture-v1" in briefing
assert Path("artifacts/figures/category_distribution.png").is_file()
print(
    f"dashboard smoke ok: {metrics['unique_posts']} posts, "
    f"{len(metrics['model_versions'])} models, {len(evidence)} evidence rows"
)
PY

echo "pipeline (fixture, offline) passed"
