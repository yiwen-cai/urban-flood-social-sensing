"""Dashboard regression tests for the unified full-information view."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

METRICS_PATH = Path("data/output/metrics.json")


def _expected_posts() -> str:
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    return str(metrics["unique_posts"])


def _expected_default_model() -> str:
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    versions = metrics.get("model_versions") or []
    for keyword in ("deepseek", "fixture-v1", "tfidf"):
        for version in versions:
            if keyword in version:
                return version
    return versions[0]


def test_dashboard_loads_local_metrics_json() -> None:
    app = AppTest.from_file("app.py").run(timeout=20)

    assert METRICS_PATH.is_file()
    assert not app.exception
    assert app.metric[0].value == _expected_posts()
    assert app.sidebar.selectbox[0].value == _expected_default_model()


def test_dashboard_shows_evidence_tab_for_generated_outputs() -> None:
    app = AppTest.from_file("app.py").run(timeout=20)

    assert not app.exception
    assert any("代表性脱敏记录" in header.value for header in app.header)
