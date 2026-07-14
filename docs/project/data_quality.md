# Lab 1 数据质量报告 — Kerala floods 2018 (test split)

> 交付物：D03
> 输入：`data/raw/humaid/kerala_floods_2018/test.json`（由 `data/frozen/manifest.json` 锁定并经 `fetch_data.py --verify-only` 校验通过）
> 处理脚本：`src/lab1_collection/clean.py` → `src/lab1_collection/standardize.py`
> 输出：`data/processed/posts_clean.jsonl`
> `pipeline_run_id`：`kerala-v1`
> 生成日期：2026-07-14

## 1. 记录数与去重

| 项 | 数值 |
|---|---|
| 原始记录数（test split） | 1,582 |
| 清洗后记录数 | 1,582 |
| 重复 `tweet_id` 数（原始） | 0 |
| 因文本为空被丢弃 | 0 |
| 净丢弃总数 | 0 |
| 输出 `post_id` 唯一性 | 通过（1,582 个全部唯一） |

本 split 本身不含重复或空文本记录，`clean.py` 的去重与空文本过滤逻辑本次未触发丢弃，但已按 `standardize.py`/`clean.py` 的实现对全量记录执行了检查。

## 2. 字段缺失率（原始输入）

| 字段 | 缺失数 | 缺失率 |
|---|---:|---:|
| `tweet_id` | 0 | 0% |
| `tweet_text` | 0 | 0% |
| `class_label` | 0 | 0% |

原始三字段（`tweet_id`、`tweet_text`、`class_label`）均无缺失，与 `fetch_data.py` 的 schema 校验结果一致。

## 3. 时间与地理覆盖

Kerala floods 2018 数据集不含逐条 `time` 或 `location` 字段（仅有 `tweet_id`、`tweet_text`、`class_label` 三个原始字段），这是数据集本身的限制，已在 [DATA_GATE.md](DATA_GATE.md) 第1节记录。因此：

- 输出记录的 `time`、`location` 字段按 `post.schema.json` 契约固定为 `null`；
- 本报告不提供时间跨度或区县覆盖统计；
- 下游（Lab 2/3）不得基于此语料生成时序趋势图或地图，仅能做类别分布和代表性文本聚合。

## 4. 官方标签分布（九分类，原始 `class_label`）

| 标签 | 记录数 | 占比 |
|---|---:|---:|
| `rescue_volunteering_or_donation_effort` | 851 | 53.8% |
| `other_relevant_information` | 189 | 11.9% |
| `sympathy_and_support` | 165 | 10.4% |
| `requests_or_urgent_needs` | 117 | 7.4% |
| `not_humanitarian` | 90 | 5.7% |
| `injured_or_dead_people` | 72 | 4.6% |
| `infrastructure_and_utility_damage` | 59 | 3.7% |
| `caution_and_advice` | 28 | 1.8% |
| `displaced_people_and_evacuations` | 11 | 0.7% |

与 [DATA_GATE.md](DATA_GATE.md) 第3节一致，标签分布严重不均衡（最大类占比超过一半，最小类不足1%）。Lab 2 评估必须报告 Macro-F1、逐类 Precision/Recall，尤其关注 `requests_or_urgent_needs`（求助/紧急需求）的召回率，不能仅报告 Accuracy。

## 5. 脱敏命中统计

脱敏规则见 [src/utils/redact.py](../../src/utils/redact.py)，按 DATA_GATE.md 第4节的四类模式执行：

| 模式 | 命中记录数 | 占比（1,582条） |
|---|---:|---:|
| 账号 handle → `[USER]` | 708 | 44.8% |
| 10–12位数字序列 → `[NUMBER]` | 43 | 2.7% |
| 邮箱 → `[EMAIL]` | 3 | 0.2% |
| URL → `[URL]` | 0 | 0% |
| 至少命中一类脱敏 | 742 | 46.9% |

**残留复核**：脱敏后仍含 `@` 字符的记录 4 条，人工核查确认均为 `@` 作介词使用（如 "singing @ thz charity event"），`@` 后为空格或非单词字符，不构成账号引用，不含隐私信息。脱敏后未发现残留的 10–12 位数字序列。

DATA_GATE.md 报告的原始语料（train+dev+test 共 7,984 条）account handle 命中数为 3,494、长数字命中数为 221；本报告统计范围仅为 test split（1,582 条），两者基数不同，不可直接比较占比。

## 6. 文本长度

| 项 | 数值 |
|---|---|
| 最短 `text_clean` 长度 | 21 字符 |
| 最长 `text_clean` 长度 | 361 字符 |
| 平均长度 | 184.4 字符 |

均在 `post.schema.json` 的 `text_clean` 长度约束（1–5000字符）范围内。

## 7. Schema 一致性

`data/processed/posts_clean.jsonl` 的全部 1,582 条记录已通过 `schemas/post.schema.json`（Draft 2020-12）程序化校验，0 个 schema 错误。`_lab2`、`_lab3` 字段均为 `null`，符合 Lab 1 阶段的契约（下游只能追加，不能在此阶段预填）。

## 8. 已知限制

- 本报告与 `posts_clean.jsonl` 仅覆盖 `test` split（frozen 主语料，1,582条）；`train`/`dev` split 尚未经过 `clean.py` 清洗流程，其消费方式（是否需要同样清洗后再交给 Lab 2 的 few-shot 候选池）待团队确认。
- 脱敏基于正则模式匹配，不是人工逐条审阅；命中统计反映的是模式命中数，不等同于已排除全部可识别信息的保证。
- `class_label` 为数据集原始参考标签，不代表已核验的真实灾情事实，仅用于 Lab 2 的模型评估基准。
