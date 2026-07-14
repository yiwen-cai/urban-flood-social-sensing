"""Lab 2: Humanitarian information classification and emotion analysis.

Modules
-------
classify    — TF-IDF+LR baseline and DeepSeek Few-shot classification.
evaluate    — Compare baseline vs LLM, compute F1, generate confusion matrix.
aggregate   — Category distributions and evidence inventory for Lab 3.
annotate_seed — Exploratory emotion annotation workflow and IAA.

The pipeline reads ``posts_clean.jsonl`` (Lab 1 output) and writes
``posts_labeled.jsonl`` with ``_lab2`` annotations appended.
"""
