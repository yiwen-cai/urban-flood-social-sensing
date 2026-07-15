# Lab 2 — Classification Evaluation Report

> 本文件由 `run_pipeline.sh --fixture --offline` / `python -m src.lab2_analysis.evaluate` 可重算生成。
> 公开真实聚合指标（无正文）见 `data/output/metrics.public.json`（1,582 唯一帖子）。
> 下方数字来自合成 fixture 离线跑通结果，用于课程可复现验收。

**Unique posts**: 20
**Posts with reference label**: 20
**Model versions found**: 2

Primary metrics use the full reference-labeled denominator and report coverage.
Successful-prediction-only accuracy is secondary.

---

## Model: fixture-baseline-v1

- **Denominator (with reference)**: 20
- **Coverage**: 0.15
- **Accuracy (full denominator)**: 0.0
- **Accuracy (successful only, secondary)**: 0.0
- **Macro-F1 (successful only)**: 0.0
- **Weighted-F1 (successful only)**: 0.0
- **Excluded / failed predictions**: 17

### Per-Class Metrics

| Label | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------|
| caution_and_advice | 0.0 | 0.0 | 0.0 | 1 |
| displaced_people_and_evacuations | 0.0 | 0.0 | 0.0 | 0 |
| infrastructure_and_utility_damage | 0.0 | 0.0 | 0.0 | 0 |
| injured_or_dead_people | 0.0 | 0.0 | 0.0 | 0 |
| not_humanitarian | 0.0 | 0.0 | 0.0 | 0 |
| other_relevant_information | 0.0 | 0.0 | 0.0 | 0 |
| requests_or_urgent_needs | 0.0 | 0.0 | 0.0 | 1 |
| rescue_volunteering_or_donation_effort | 0.0 | 0.0 | 0.0 | 1 |
| sympathy_and_support | 0.0 | 0.0 | 0.0 | 0 |

### Classification Report (sklearn)

```
precision    recall  f1-score   support

                    caution_and_advice       0.00      0.00      0.00       1.0
      displaced_people_and_evacuations       0.00      0.00      0.00       0.0
     infrastructure_and_utility_damage       0.00      0.00      0.00       0.0
                injured_or_dead_people       0.00      0.00      0.00       0.0
                      not_humanitarian       0.00      0.00      0.00       0.0
            other_relevant_information       0.00      0.00      0.00       0.0
              requests_or_urgent_needs       0.00      0.00      0.00       1.0
rescue_volunteering_or_donation_effort       0.00      0.00      0.00       1.0
                  sympathy_and_support       0.00      0.00      0.00       0.0

                              accuracy                           0.00       3.0
                             macro avg       0.00      0.00      0.00       3.0
                          weighted avg       0.00      0.00      0.00       3.0
```

---

## Model: fixture-v1

- **Denominator (with reference)**: 20
- **Coverage**: 1.0
- **Accuracy (full denominator)**: 1.0
- **Accuracy (successful only, secondary)**: 1.0
- **Macro-F1 (successful only)**: 1.0
- **Weighted-F1 (successful only)**: 1.0

### Per-Class Metrics

| Label | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------|
| caution_and_advice | 1.0 | 1.0 | 1.0 | 2 |
| displaced_people_and_evacuations | 1.0 | 1.0 | 1.0 | 2 |
| infrastructure_and_utility_damage | 1.0 | 1.0 | 1.0 | 2 |
| injured_or_dead_people | 1.0 | 1.0 | 1.0 | 2 |
| not_humanitarian | 1.0 | 1.0 | 1.0 | 2 |
| other_relevant_information | 1.0 | 1.0 | 1.0 | 2 |
| requests_or_urgent_needs | 1.0 | 1.0 | 1.0 | 2 |
| rescue_volunteering_or_donation_effort | 1.0 | 1.0 | 1.0 | 4 |
| sympathy_and_support | 1.0 | 1.0 | 1.0 | 2 |

### Classification Report (sklearn)

```
precision    recall  f1-score   support

                    caution_and_advice       1.00      1.00      1.00         2
      displaced_people_and_evacuations       1.00      1.00      1.00         2
     infrastructure_and_utility_damage       1.00      1.00      1.00         2
                injured_or_dead_people       1.00      1.00      1.00         2
                      not_humanitarian       1.00      1.00      1.00         2
            other_relevant_information       1.00      1.00      1.00         2
              requests_or_urgent_needs       1.00      1.00      1.00         2
rescue_volunteering_or_donation_effort       1.00      1.00      1.00         4
                  sympathy_and_support       1.00      1.00      1.00         2

                              accuracy                           1.00        20
                             macro avg       1.00      1.00      1.00        20
                          weighted avg       1.00      1.00      1.00        20
```

---

## Model Comparison

| Metric | Baseline (TF-IDF+LR) | LLM (DeepSeek) |
|--------|----------------------|----------------|
| Coverage | N/A | N/A |
| Accuracy (full) | N/A | N/A |
| Accuracy (successful only) | N/A | N/A |
| Macro-F1 | N/A | N/A |
| Weighted-F1 | N/A | N/A |

### Critical Class Recall

| Critical Class | Baseline Recall | LLM Recall |
|----------------|-----------------|------------|
| requests_or_urgent_needs | N/A | N/A |
| displaced_people_and_evacuations | N/A | N/A |

## Limitations & Usage Notes

- Metrics are computed on the frozen HumAID Kerala test split (1,582 unique posts).
- Primary accuracy uses the full reference denominator; failures reduce coverage and accuracy.
- Labels are highly imbalanced; rely on Macro-F1, not Accuracy alone.
- `model_scores` / confidence are NOT calibrated probabilities.
- Reference labels are dataset annotations, not verified ground-truth facts.

---

*Report auto-generated by `src/lab2_analysis/evaluate.py`.*