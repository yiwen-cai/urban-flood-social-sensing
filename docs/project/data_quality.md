# Lab 1 数据质量报告 — Kerala floods 2018

> 交付物：D03
> 输入：`data/raw/humaid/kerala_floods_2018/{test,train,dev}.json`（由 `data/frozen/manifest.json` 锁定并经 `fetch_data.py --verify-only` 校验通过）
> 处理脚本：`src/lab1_collection/clean.py` → `src/lab1_collection/standardize.py`
> 输出：`data/processed/posts_clean.test.jsonl`、`posts_clean.train.jsonl`、`posts_clean.dev.jsonl`
> `pipeline_run_id`：`kerala-v1`
> 生成日期：2026-07-14

## 0. 决策记录：train/dev 是否清洗

**决策**：train、dev 与 test 一样，全部经过相同的 `clean.py` 清洗（去重、空文本过滤、脱敏、字段映射），输出为三个独立文件（`posts_clean.{split}.jsonl`），不合并为单一文件。

理由：

- Lab 2 唯一正式输入应为清洗后的 `posts_clean.*.jsonl`，避免出现"部分 split 走清洗流程、部分 split 直接读原始 JSON"两套输入契约并存的情况（[实施方案.md](实施方案.md) 第499行模块契约表要求单一正式输入）。
- 未清洗即意味着未脱敏；若 train/dev 原始文本被直接用于 few-shot prompt，将违反 [DATA_GATE.md](DATA_GATE.md) 第5节"脱敏文本才可发送至 DeepSeek API"的边界。
- 分文件而非合并，是为了保持 [DATA_GATE.md](DATA_GATE.md) 第1节的约束：`test` 是唯一冻结主语料和正式评估集，`train`/`dev` 仅用于 few-shot 候选池和 prompt 调参，混合存放容易导致 Lab 2 无意间将训练/调参数据混入评估统计。
- `clean.py` 已支持 `--split` 参数，且各 split 的 `post_id` 前缀（`test:`/`train:`/`dev:`）天然不重叠，跨文件不存在 ID 碰撞（已验证：0 处重叠）。

`clean.py` 默认输出路径已改为按 split 自动命名（`default_output_for_split`），避免未显式传 `--output` 时误覆盖其他 split 的产物。

## 1. 记录数与去重

| Split | 原始记录数 | 清洗后记录数 | 重复 `tweet_id`（原始） | 因文本为空被丢弃 | 净丢弃总数 |
|---|---:|---:|---:|---:|---:|
| test | 1,582 | 1,582 | 0 | 0 | 0 |
| train | 5,588 | 5,588 | 0 | 0 | 0 |
| dev | 814 | 814 | 0 | 0 | 0 |

三个 split 均不含重复或空文本记录，`clean.py` 的去重与空文本过滤逻辑本次未触发丢弃，但已按 `standardize.py`/`clean.py` 的实现对全量记录执行了检查。输出 `post_id` 在各 split 内部及跨 split 均唯一（`test:`/`train:`/`dev:` 前缀天然不重叠，已验证 0 处交叉重复）。

## 2. 字段缺失率（原始输入）

| Split | `tweet_id` 缺失 | `tweet_text` 缺失 | `class_label` 缺失 |
|---|---:|---:|---:|
| test | 0 (0%) | 0 (0%) | 0 (0%) |
| train | 0 (0%) | 0 (0%) | 0 (0%) |
| dev | 0 (0%) | 0 (0%) | 0 (0%) |

原始三字段（`tweet_id`、`tweet_text`、`class_label`）在全部三个 split 均无缺失，与 `fetch_data.py` 的 schema 校验结果一致。

## 3. 时间与地理覆盖

Kerala floods 2018 数据集不含逐条 `time` 或 `location` 字段（仅有 `tweet_id`、`tweet_text`、`class_label` 三个原始字段），这是数据集本身的限制，已在 [DATA_GATE.md](DATA_GATE.md) 第1节记录。因此：

- 输出记录的 `time`、`location` 字段按 `post.schema.json` 契约固定为 `null`；
- 本报告不提供时间跨度或区县覆盖统计；
- 下游（Lab 2/3）不得基于此语料生成时序趋势图或地图，仅能做类别分布和代表性文本聚合。

## 4. 官方标签分布（九分类，原始 `class_label`）

| 标签 | test | train | dev |
|---|---:|---:|---:|
| `rescue_volunteering_or_donation_effort` | 851 (53.8%) | 3,005 (53.8%) | 438 (53.8%) |
| `other_relevant_information` | 189 (11.9%) | 669 (12.0%) | 97 (11.9%) |
| `sympathy_and_support` | 165 (10.4%) | 585 (10.5%) | 85 (10.4%) |
| `requests_or_urgent_needs` | 117 (7.4%) | 413 (7.4%) | 60 (7.4%) |
| `not_humanitarian` | 90 (5.7%) | 319 (5.7%) | 47 (5.8%) |
| `injured_or_dead_people` | 72 (4.6%) | 254 (4.5%) | 37 (4.5%) |
| `infrastructure_and_utility_damage` | 59 (3.7%) | 207 (3.7%) | 30 (3.7%) |
| `caution_and_advice` | 28 (1.8%) | 97 (1.7%) | 14 (1.7%) |
| `displaced_people_and_evacuations` | 11 (0.7%) | 39 (0.7%) | 6 (0.7%) |

三个 split 的标签比例几乎一致（分层抽样痕迹明显），与 [DATA_GATE.md](DATA_GATE.md) 第3节一致，标签分布严重不均衡（最大类占比超过一半，最小类不足1%）。Lab 2 评估必须报告 Macro-F1、逐类 Precision/Recall，尤其关注 `requests_or_urgent_needs`（求助/紧急需求）的召回率，不能仅报告 Accuracy。

## 5. 脱敏命中统计

脱敏规则见 [src/utils/redact.py](../../src/utils/redact.py)，按 DATA_GATE.md 第4节的四类模式执行：

| 模式 | test (1,582) | train (5,588) | dev (814) |
|---|---:|---:|---:|
| 账号 handle → `[USER]` | 708 (44.8%) | 2,423 (43.4%) | 356 (43.7%) |
| 10–12位数字序列 → `[NUMBER]` | 43 (2.7%) | 158 (2.8%) | 18 (2.2%) |
| 邮箱 → `[EMAIL]` | 3 (0.2%) | 9 (0.2%) | 0 (0%) |
| URL → `[URL]` | 0 (0%) | 0 (0%) | 0 (0%) |
| 至少命中一类脱敏 | 742 (46.9%) | 2,552 (45.7%) | 370 (45.5%) |

**残留复核**：脱敏后仍含 `@` 字符的记录 test 4 条、train 24 条、dev 4 条，逐条人工核查确认均为 `@` 作介词使用（如 "singing @ thz charity event"），`@` 后为空格或非单词字符，不构成账号引用，不含隐私信息；用账号正则重新扫描这些残留文本确认 0 处漏判。脱敏后三个 split 均未发现残留的 10–12 位数字序列。

DATA_GATE.md 报告的原始语料（train+dev+test 共 7,984 条）account handle 命中数为 3,494、长数字命中数为 221，与本报告三个 split 命中数之和（handle 3,487、number 219）基本一致，差异在个位数范围内，可能源于统计口径（DATA_GATE.md 为全量7,984条模式扫描，本报告基于清洗后文本重新统计）。

## 6. 文本长度

| Split | 最短 | 最长 | 平均 |
|---|---:|---:|---:|
| test | 21 | 361 | 184.4 |
| train | 17 | 610 | 183.4 |
| dev | 20 | 314 | 181.4 |

均在 `post.schema.json` 的 `text_clean` 长度约束（1–5000字符）范围内。

## 7. Schema 一致性

`posts_clean.test.jsonl`（1,582条）、`posts_clean.train.jsonl`（5,588条）、`posts_clean.dev.jsonl`（814条）已全部通过 `schemas/post.schema.json`（Draft 2020-12）程序化校验，0 个 schema 错误。`_lab2`、`_lab3` 字段在三个文件中均为 `null`，符合 Lab 1 阶段的契约（下游只能追加，不能在此阶段预填）。

## 8. 已知限制

- 脱敏基于正则模式匹配，不是人工逐条审阅；命中统计反映的是模式命中数，不等同于已排除全部可识别信息的保证。
- `class_label` 为数据集原始参考标签，不代表已核验的真实灾情事实，仅用于 Lab 2 的模型评估基准。
- `train`/`dev` 按方案仅作为 few-shot 候选池和 prompt 调参输入，不得混入 briefing 统计或正式评估指标（唯一冻结主语料和评估集仍为 `test`，见第0节决策记录与 [DATA_GATE.md](DATA_GATE.md) 第1节）。
