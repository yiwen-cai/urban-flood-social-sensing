# Lab 2 — Classification Evaluation Report

**Unique posts**: 1582
**Posts with reference label**: 1582
**Model versions found**: 2

Primary metrics use the full reference-labeled denominator and report coverage.
Successful-prediction-only accuracy is secondary.

---

## Model: deepseek-v4-flash

- **Denominator (with reference)**: 1582
- **Coverage**: 0.9052
- **Accuracy (full denominator)**: 0.6403
- **Accuracy (successful only, secondary)**: 0.7074
- **Macro-F1 (successful only)**: 0.5532
- **Weighted-F1 (successful only)**: 0.7199
- **Excluded / failed predictions**: 150

### Per-Class Metrics

| Label | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------|
| caution_and_advice | 0.3889 | 0.5385 | 0.4516 | 26 |
| displaced_people_and_evacuations | 0.1429 | 0.2222 | 0.1739 | 9 |
| infrastructure_and_utility_damage | 0.6 | 0.36 | 0.45 | 50 |
| injured_or_dead_people | 0.8491 | 0.7377 | 0.7895 | 61 |
| not_humanitarian | 0.35 | 0.6747 | 0.4609 | 83 |
| other_relevant_information | 0.4124 | 0.4506 | 0.4307 | 162 |
| requests_or_urgent_needs | 0.7048 | 0.7048 | 0.7048 | 105 |
| rescue_volunteering_or_donation_effort | 0.896 | 0.7982 | 0.8443 | 788 |
| sympathy_and_support | 0.6581 | 0.6892 | 0.6733 | 148 |

### Classification Report (sklearn)

```
precision    recall  f1-score   support

                    caution_and_advice       0.39      0.54      0.45        26
      displaced_people_and_evacuations       0.14      0.22      0.17         9
     infrastructure_and_utility_damage       0.60      0.36      0.45        50
                injured_or_dead_people       0.85      0.74      0.79        61
                      not_humanitarian       0.35      0.67      0.46        83
            other_relevant_information       0.41      0.45      0.43       162
              requests_or_urgent_needs       0.70      0.70      0.70       105
rescue_volunteering_or_donation_effort       0.90      0.80      0.84       788
                  sympathy_and_support       0.66      0.69      0.67       148

                              accuracy                           0.71      1432
                             macro avg       0.56      0.58      0.55      1432
                          weighted avg       0.74      0.71      0.72      1432
```

---

## Model: tfidf-lr-baseline-v1

- **Denominator (with reference)**: 1582
- **Coverage**: 1.0
- **Accuracy (full denominator)**: 0.6985
- **Accuracy (successful only, secondary)**: 0.6985
- **Macro-F1 (successful only)**: 0.4032
- **Weighted-F1 (successful only)**: 0.6551

### Per-Class Metrics

| Label | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------|
| caution_and_advice | 0.5 | 0.0357 | 0.0667 | 28 |
| displaced_people_and_evacuations | 0.0 | 0.0 | 0.0 | 11 |
| infrastructure_and_utility_damage | 0.7368 | 0.2373 | 0.359 | 59 |
| injured_or_dead_people | 0.8696 | 0.5556 | 0.678 | 72 |
| not_humanitarian | 0.3333 | 0.0333 | 0.0606 | 90 |
| other_relevant_information | 0.4785 | 0.4709 | 0.4747 | 189 |
| requests_or_urgent_needs | 0.6761 | 0.4103 | 0.5106 | 117 |
| rescue_volunteering_or_donation_effort | 0.721 | 0.9624 | 0.8244 | 851 |
| sympathy_and_support | 0.8053 | 0.5515 | 0.6547 | 165 |

### Classification Report (sklearn)

```
precision    recall  f1-score   support

                    caution_and_advice       0.50      0.04      0.07        28
      displaced_people_and_evacuations       0.00      0.00      0.00        11
     infrastructure_and_utility_damage       0.74      0.24      0.36        59
                injured_or_dead_people       0.87      0.56      0.68        72
                      not_humanitarian       0.33      0.03      0.06        90
            other_relevant_information       0.48      0.47      0.47       189
              requests_or_urgent_needs       0.68      0.41      0.51       117
rescue_volunteering_or_donation_effort       0.72      0.96      0.82       851
                  sympathy_and_support       0.81      0.55      0.65       165

                              accuracy                           0.70      1582
                             macro avg       0.57      0.36      0.40      1582
                          weighted avg       0.67      0.70      0.66      1582
```

---

## Model Comparison

| Metric | deepseek-v4-flash | tfidf-lr-baseline-v1 |
|--------|---|---|
| Coverage | 0.9052 | 1.0 |
| Accuracy (full) | 0.6403 | 0.6985 |
| Accuracy (successful only) | 0.7074 | 0.6985 |
| Macro-F1 | 0.5532 | 0.4032 |
| Weighted-F1 | 0.7199 | 0.6551 |

### Critical Class Recall

| Critical Class | deepseek-v4-flash | tfidf-lr-baseline-v1 |
|----------------|---|---|
| requests_or_urgent_needs | 0.7048 | 0.4103 |
| displaced_people_and_evacuations | 0.2222 | 0.0 |

## Limitations & Usage Notes

- Metrics are computed on the 1582 unique posts supplied to this evaluation run.
- Primary accuracy uses the full reference denominator; failures reduce coverage and accuracy.
- Labels are highly imbalanced; rely on Macro-F1, not Accuracy alone.
- `model_scores` / confidence are NOT calibrated probabilities.
- Reference labels are dataset annotations, not verified ground-truth facts.

---

*Report auto-generated by `src/lab2_analysis/evaluate.py`.*