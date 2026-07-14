"""DeepSeek API wrapper — OpenAI-compatible chat completions with JSON output.

Features:
- OpenAI-compatible client (DeepSeek base URL)
- JSON Schema constrained output via ``response_format``
- Exponential backoff retry on rate-limit / transient errors
- Optional ClassificationCache integration
- Graceful error records instead of crashing the pipeline
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

# DeepSeek is OpenAI-compatible — use the official openai package.
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Configuration from environment (matches .env.example)
# ---------------------------------------------------------------------------

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60"))
DEEPSEEK_BATCH_SIZE = int(os.getenv("DEEPSEEK_BATCH_SIZE", "20"))

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0   # seconds — doubled each retry
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a humanitarian information classifier for disaster-related social media posts. "
    "Your task is to assign exactly ONE label from the nine humanitarian categories "
    "defined below.  Do NOT invent labels.  Respond with valid JSON only."
)

FEW_SHOT_TEMPLATE = """Classify the following social media post into exactly ONE of these nine humanitarian information categories:

1. caution_and_advice — safety warnings, official advice, evacuation instructions
2. displaced_people_and_evacuations — people displaced, evacuations, shelter status
3. infrastructure_and_utility_damage — damaged roads, bridges, power, water, communications
4. injured_or_dead_people — casualties, injuries, missing persons, medical emergencies
5. not_humanitarian — unrelated to disaster response (ads, entertainment, etc.)
6. other_relevant_information — flood-related but not fitting other categories (weather, context)
7. requests_or_urgent_needs — requests for food, water, medicine, shelter, transport
8. rescue_volunteering_or_donation_effort — rescue operations, volunteering, donations, fundraising
9. sympathy_and_support — emotional support, prayers, solidarity (no concrete action)

{examples}

Now classify this post:
Post: "{text}"

Respond with a JSON object:
{{"label": "<one of the nine labels>", "confidence": <0.0-1.0>}}"""


# ====================================================================
# JSON Schema for structured output (DeepSeek JSON Output feature)
# ====================================================================

CLASSIFICATION_JSON_SCHEMA = {
    "name": "humanitarian_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["label", "confidence"],
        "properties": {
            "label": {
                "type": "string",
                "enum": [
                    "caution_and_advice",
                    "displaced_people_and_evacuations",
                    "infrastructure_and_utility_damage",
                    "injured_or_dead_people",
                    "not_humanitarian",
                    "other_relevant_information",
                    "requests_or_urgent_needs",
                    "rescue_volunteering_or_donation_effort",
                    "sympathy_and_support",
                ],
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
        },
    },
}

# ====================================================================
# Client factory (lazy init — only when actually called)
# ====================================================================

_client: Any = None


def _get_client() -> Any:
    """Return a cached OpenAI client pointed at DeepSeek."""
    global _client
    if _client is not None:
        return _client
    if OpenAI is None:
        raise ImportError(
            "The 'openai' package is required for LLM classification. "
            "Install it with: pip install openai"
        )
    if not DEEPSEEK_API_KEY:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set. "
            "Copy .env.example to .env and fill in your key."
        )
    _client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=DEEPSEEK_TIMEOUT,
    )
    return _client


# ====================================================================
# Core API call
# ====================================================================

def classify_text(
    text: str,
    *,
    few_shot_examples: list[dict[str, str]] | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 256,
) -> dict[str, Any]:
    """Classify a single text into one of the 9 humanitarian labels.

    Args:
        text: The tweet text to classify (must already be redacted).
        few_shot_examples: Optional list of {"text": ..., "label": ...} dicts.
        model: Override the default model.
        temperature: Sampling temperature (0 = deterministic).
        max_tokens: Max response tokens.

    Returns:
        A dict with at least:
        - ``success``: bool
        - ``label``: str | None (the predicted label)
        - ``confidence``: float | None
        - ``error``: str | None (on failure)
        - ``raw_response``: str | None (for debugging)
    """
    client = _get_client()
    model_name = model or DEEPSEEK_MODEL

    # Build few-shot examples string
    examples_str = ""
    if few_shot_examples:
        parts = []
        for ex in few_shot_examples:
            parts.append(
                f'Example:\nPost: "{ex["text"]}"\nResponse: {{"label": "{ex["label"]}", "confidence": 1.0}}'
            )
        examples_str = "\n".join(parts)

    user_message = FEW_SHOT_TEMPLATE.format(
        examples=examples_str, text=text
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    last_error: str | None = None

    # Prefer json_schema (stricter), fall back to json_object for older
    # DeepSeek endpoints that only support {"type": "json_object"}.
    _use_json_schema = True  # set False if smoke test fails

    for attempt in range(MAX_RETRIES + 1):
        try:
            if _use_json_schema:
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={
                            "type": "json_schema",
                            "json_schema": CLASSIFICATION_JSON_SCHEMA,
                        },
                    )
                except Exception as exc:
                    if "json_schema" in str(exc).lower() or "400" in str(exc):
                        _use_json_schema = False
                        response = client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            response_format={"type": "json_object"},
                        )
                    else:
                        raise
            else:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )

            raw = response.choices[0].message.content

            # Parse and validate
            parsed = json.loads(raw)
            label = parsed.get("label")
            confidence = parsed.get("confidence")

            # Validate label is in the enum
            valid_labels = CLASSIFICATION_JSON_SCHEMA["schema"]["properties"]["label"]["enum"]
            if label not in valid_labels:
                return {
                    "success": False,
                    "label": None,
                    "confidence": None,
                    "error": f"Model returned invalid label: {label!r}",
                    "raw_response": raw,
                }

            return {
                "success": True,
                "label": label,
                "confidence": float(confidence) if confidence is not None else None,
                "error": None,
                "raw_response": raw,
            }

        except Exception as exc:
            last_error = str(exc)
            # Check if retryable
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in RETRYABLE_HTTP_CODES and attempt < MAX_RETRIES:
                delay = RETRY_BACKOFF_BASE ** (attempt + 1)
                time.sleep(delay)
                continue
            # Non-retryable or exhausted retries
            if attempt < MAX_RETRIES and _is_retryable_exception(exc):
                delay = RETRY_BACKOFF_BASE ** (attempt + 1)
                time.sleep(delay)
                continue
            break

    return {
        "success": False,
        "label": None,
        "confidence": None,
        "error": last_error,
        "raw_response": None,
    }


def _is_retryable_exception(exc: Exception) -> bool:
    """Heuristic: is this exception likely transient?"""
    msg = str(exc).lower()
    retryable_keywords = [
        "timeout", "connection", "rate limit", "too many requests",
        "server error", "service unavailable", "try again",
    ]
    return any(kw in msg for kw in retryable_keywords)


def classify_batch(
    texts: list[dict[str, str]],
    *,
    few_shot_examples: list[dict[str, str]] | None = None,
    model: str | None = None,
    checkpoint_path: str | None = None,
) -> list[dict[str, Any]]:
    """Classify a batch of texts with caching and checkpointing.

    Args:
        texts: List of {"post_id": ..., "text_clean": ...} dicts.
        few_shot_examples: Optional few-shot examples.
        model: Model override.
        checkpoint_path: Optional path for Checkpoint (resume support).

    Returns:
        List of results with at least ``post_id``, ``label``, ``confidence``,
        ``error``, and ``model_version``.
    """
    from .cache import ClassificationCache, Checkpoint

    cache = ClassificationCache()
    checkpoint = Checkpoint(checkpoint_path) if checkpoint_path else None
    if checkpoint:
        checkpoint.load()

    model_name = model or DEEPSEEK_MODEL
    results: list[dict[str, Any]] = []

    for entry in texts:
        post_id = entry["post_id"]
        text_clean = entry["text_clean"]

        # Skip already processed
        if checkpoint and checkpoint.is_done(post_id):
            # Try to recover from cache
            cached = cache.get(model_name, text_clean)
            if cached:
                results.append({"post_id": post_id, **cached})
                continue

        # Check cache first
        cached = cache.get(model_name, text_clean)
        if cached:
            results.append({"post_id": post_id, **cached})
            if checkpoint:
                checkpoint.mark_done(post_id)
            continue

        # Call API
        api_result = classify_text(
            text_clean,
            few_shot_examples=few_shot_examples,
            model=model_name,
        )

        result = {
            "post_id": post_id,
            "label": api_result["label"],
            "confidence": api_result["confidence"],
            "success": api_result["success"],
            "error": api_result.get("error"),
            "model_version": model_name,
        }

        # Cache and checkpoint (even failures, so we don't retry forever)
        cache.put(model_name, text_clean, result)
        if checkpoint:
            checkpoint.mark_done(post_id)

        results.append(result)

    return results


def smoke_test() -> dict[str, Any]:
    """Run a minimal smoke test using synthetic text.

    Returns a dict with ``ok``, ``latency_ms``, ``label``, and ``error``.
    """
    test_text = (
        "Synthetic notice: residents should avoid flooded roads "
        "and follow verified safety instructions."
    )
    t0 = time.perf_counter()
    result = classify_text(test_text)
    elapsed = (time.perf_counter() - t0) * 1000

    return {
        "ok": result["success"],
        "latency_ms": round(elapsed, 1),
        "label": result["label"],
        "confidence": result["confidence"],
        "error": result.get("error"),
    }
