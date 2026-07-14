#!/usr/bin/env bash
# Vertical-slice pipeline entry point. Currently supports the fixture/offline
# path required for Day 1 handoff (D02); real-data stages are wired in as
# Lab 1-3 land.
set -euo pipefail

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

echo "== schema tests =="
python -m pytest tests/test_schema.py

echo "== data gate verification (offline, no download) =="
python src/lab1_collection/fetch_data.py --verify-only

echo "== fixture vertical slice =="
python - <<'PY'
import json
from pathlib import Path

fixture = Path("tests/fixtures/sample_posts.jsonl")
rows = [json.loads(line) for line in fixture.read_text().splitlines() if line.strip()]
assert len(rows) == 20, f"expected 20 fixture rows, got {len(rows)}"
print(f"fixture vertical slice loaded {len(rows)} records")
PY

echo "pipeline (fixture, offline) passed"
