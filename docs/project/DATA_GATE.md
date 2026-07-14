# DATA GATE — HumAID Kerala 2018

> Status: conditionally passed for local course research
>
> Frozen date: 2026-07-13
>
> Source revision: `2e7ea23332006f075068b90d401b178d847b447a`
>
> Main corpus: `kerala_floods_2018/test.json`, 1,582 records

## 1. Decision

The project uses HumAID `kerala_floods_2018` as its only event corpus. The official `test` split is the frozen main corpus and formal evaluation set. `train` and `dev` are development inputs only: they may be used for the TF-IDF baseline, Few-shot examples, and prompt development, but they must not be mixed into briefing statistics or test metrics.

The project does not wait for the inaccessible `weibo_720` file and does not add CrowdFlood or any other event-level spatial dataset. The Kerala files contain no per-post time, location, or URL, so the pipeline must store `time` and `location` as `null` and must not produce maps or temporal trends.

## 2. Provenance and local verification

| Split | Records | Bytes | SHA-256 | Project role |
|------|--------:|------:|--------|--------------|
| `train` | 5,588 | 1,826,708 | `4571d45d717a2b5d532e0fe0666f74be1950c77b375a6f9bb67086e12c489e11` | Baseline training and Few-shot candidates |
| `dev` | 814 | 264,079 | `139f51547c35f5ada5fc63f7ddf476b2f26f22b87f38afbd935715812e473b36` | Baseline tuning and prompt development |
| `test` | 1,582 | 519,315 | `960a90f8d10daa0fb3611a18c21750a2ae72203d4d64cafb88f9a918f99ab789` | Frozen main corpus and formal evaluation |

All three files contain exactly `tweet_id`, `tweet_text`, and `class_label`. IDs and texts are unique within each split, and no tweet ID is shared across the three local splits. `tweet_id` values must be converted to strings at the adapter boundary because they exceed JavaScript's safe integer range.

The QCRI event table reports 8,056 annotated Kerala records, while the current Hugging Face event repository contains 7,984 records across its three splits. The reason for the 72-record difference is not documented in the downloaded files. This project freezes the exact Hugging Face revision represented by the hashes above and does not claim that the local copy is the complete original QCRI release.

## 3. Labels and imbalance

The local Kerala event contains nine single-label humanitarian categories. It is strongly imbalanced: `rescue_volunteering_or_donation_effort` accounts for 4,294 of 7,984 records, while `displaced_people_and_evacuations` has only 56. Evaluation must therefore report Macro-F1, Weighted-F1, per-class Precision/Recall, and Support; Accuracy alone is not acceptable.

The official `class_label` is a reference label for evaluation, not an input to model prediction and not evidence that the underlying disaster claim was verified. Exploratory emotion labels are course-created metadata and must be stored and reported separately from the official nine-class task.

## 4. Privacy audit

A regex-based audit over all 7,984 local texts found records containing the following patterns:

| Pattern | Matching records | Required handling |
|---------|-----------------:|-------------------|
| Account handles | 3,494 | Replace with `[USER]` before any downstream display or third-party processing |
| 10–12 digit sequences | 221 | Treat as possible contact information; replace with `[NUMBER]` and audit samples |
| Email-like strings | 12 | Replace with `[EMAIL]` |
| Explicit `http(s)` or `www` URL markers | 0 | Continue URL redaction in the generic cleaner |

These counts are pattern matches, not confirmed identities. They establish that redaction is mandatory. The public repository, Slides, dashboard, logs, and demo video must not contain searchable original tweet text, handles, contact details, names, or precise addresses.

## 5. License and redistribution boundary

- Hugging Face metadata labels the dataset `cc-by-nc-sa-4.0`.
- The QCRI terms additionally require research-only use, confidentiality of dataset contents, deletion on request or at the end of the research, and citation of the corresponding paper; tweet IDs may be shared.
- Until the discrepancy is clarified, this project applies the stricter QCRI terms.

Consequences for this repository:

1. Raw and processed real tweet text remain under ignored local data paths.
2. `tests/fixtures/sample_posts.jsonl` contains only synthetic text created for contract testing.
3. Public artifacts may contain aggregate metrics, label names, synthetic examples, code, hashes, and tweet IDs where necessary, but not original tweet text.
4. Sending redacted text to DeepSeek remains subject to the team's course/research approval and the provider's data policy; the API smoke test must use synthetic fixture text until this boundary is confirmed.
5. Derived publications and Slides must cite the HumAID paper and dataset source.

## 6. Data distribution for three-person collaboration

- Members A and B download the official event-wise files independently and run the verifier against `data/frozen/manifest.json`.
- Member C develops against the synthetic fixture and consumes only validated, redacted downstream artifacts during integration.
- Raw text is not sent through GitHub, PR comments, chat attachments, or a public cloud link.
- A mismatch in hash, record count, fields, unique IDs, or label set blocks handoff.

## 7. Gate checklist

- [x] One event and one frozen main split selected
- [x] Source URLs, file sizes, record counts, and SHA-256 values recorded
- [x] Raw fields and nine-label set verified
- [x] Missing time/location fields explicitly documented
- [x] Initial privacy-pattern audit completed
- [x] Synthetic fixture policy established
- [x] DeepSeek selected; default smoke-test model is `deepseek-v4-flash`
- [x] Team confirms whether redacted real text may be sent to the DeepSeek API
- [x] Demonstration machine passes dependency installation and offline fixture test (lightweight pass; see `docs/project/environment_check.md`)

**Team decision (2026-07-14):** the team approves sending redacted real text to the DeepSeek API. This applies only to text that has passed the `src/utils/redact.py` pipeline (`pii_redacted: true` in `posts_clean.*.jsonl`); raw, unredacted text must still never be sent to any third-party API. This unblocks Lab 2 from running real-text classification against `test`/`train`/`dev`, subject to the stricter QCRI research-only and confidentiality terms in section 5.

All gate items are now checked. A full re-check covering Lab 2/3 dependencies and a real offline test is still required before Day 3/4 feature freeze (see `docs/project/environment_check.md` section 3).
