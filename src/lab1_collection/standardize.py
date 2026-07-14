"""Map raw HumAID Kerala records onto the frozen post.schema.json contract."""

from __future__ import annotations

from typing import Any

from src.utils.redact import redact_text

SCHEMA_VERSION = "1.0.0"
EVENT_ID = "kerala_floods_2018"
SOURCE = "humaid_events"


def standardize_record(raw: dict[str, Any], split: str, pipeline_run_id: str) -> dict[str, Any]:
    tweet_id = str(raw["tweet_id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_run_id": pipeline_run_id,
        "post_id": f"{split}:{tweet_id}",
        "text_clean": redact_text(raw["tweet_text"]),
        "event_id": EVENT_ID,
        "time": None,
        "location": None,
        "source": SOURCE,
        "source_ref": f"humaid_events:{split}:{tweet_id}",
        "pii_redacted": True,
        "_lab2": None,
        "_lab3": None,
    }
