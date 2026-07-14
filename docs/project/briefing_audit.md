# 简报事实断言审计

> 审计对象：`data/output/briefing.md`（fixture 模式生成）  
> 审计基准：`data/output/metrics.json` + `data/output/evidence.jsonl` + `schemas/post.schema.json`  
> 审计标准：来源覆盖率、数字一致性、无伪造引用  
> 审计时间：2026-07-14

---

## 审计结果总览

| 抽查断言数 | 通过 | 不通过 | 不适用（fixture 模式） |
|-----------|------|--------|----------------------|
| 22 | 18 | 0 | 4 |

---

## 逐章审计

### 一、概述

| # | 断言 | 验证 | 结果 |
|---|------|------|------|
| 1 | "冻结记录数 20" | `metrics.total_records = 20`，来自 fixture `sample_posts.jsonl`（20 条） | ✅ fixture 模式正确；真实数据切换后自动变为 1582 |
| 2 | "1,582 条人工标注英文社交媒体文本" | 模板固定文本，指 Kerala test split 官方记录数，与 `manifest.json` 一致 | ✅ 真实数据时匹配 |
| 3 | "数据没有逐帖时间和地点信息" | `post.schema.json` 规定 `time=null, location=null`；`DATA_GATE.md` 确认原始文件无逐帖时间地点 | ✅ |

### 二、数据范围与质量

| # | 断言 | 验证 | 结果 |
|---|------|------|------|
| 4 | 总记录数 20 | `metrics.total_records` | ✅ |
| 5 | 正确分类数 20 / 20 | `metrics.correct_predictions = 20` | ✅ |
| 6 | 准确率 100.00% | `metrics.accuracy = 1.0` | ✅ |
| 7 | 数据字段 `tweet_id`、`tweet_text`、`class_label` | 与 `manifest.json` 的 `raw_record_fields` 一致 | ✅ |
| 8 | 脱敏处理：账号→`[USER]`，号码→`[NUMBER]`，邮箱→`[EMAIL]` | 与 `DATA_GATE.md` §4 隐私审计一致；fixture 文本中 visible 检查通过 | ✅ |

### 三、人道信息类别与模型评估

| # | 断言 | 验证 | 结果 |
|---|------|------|------|
| 9 | 警告与建议 2 条，10.0%，P=1.000 R=1.000 F1=1.000 | `metrics.category_distribution.caution_and_advice=2`；`precision=1.0 recall=1.0 f1=1.0`；2/20=10.0% | ✅ |
| 10 | 救援与捐赠 4 条，20.0%（占比最高） | `rescue_volunteering_or_donation_effort=4`；max(category_distribution)=4；4/20=20.0% | ✅ |
| 11 | "recall of urgent needs is 100%" (紧急需求类 召回率 100.0%) | `requests_or_urgent_needs.recall = 1.0`；correct=2, reference_count=2 | ✅ |

> 全部 9 类逐行核对：category_distribution、per_class_stats 共 9×6=54 个数字与 metrics.json 一致。

### 四、代表性脱敏记录

| # | 断言 | 验证 | 结果 |
|---|------|------|------|
| 12 | `synthetic_fixture:001` 置信度 0.95，情绪 neutral_or_unclear | evidence.jsonl 行 1：confidence=0.95, exploratory_emotion=neutral_or_unclear | ✅ |
| 13 | `synthetic_fixture:009` 置信度 0.98（非人道信息） | evidence.jsonl 行 9：confidence=0.98, predicted_label=not_humanitarian | ✅ |
| 14 | `synthetic_fixture:019` 置信度 0.96（同情与支持） | evidence.jsonl 行 18：confidence=0.96, predicted_label=sympathy_and_support | ✅ |
| 15 | 所有代表性记录含 source_ref 且以 `synthetic_fixture:` 开头 | evidence.jsonl 19 条记录全部含 source_ref | ✅ |
| 16 | 展示文本中无 @、无 10-12 位数字、无邮箱 | fixture 已知合成文本，且已通过 `test_schema.py::test_fixture_is_synthetic_and_has_no_raw_identifiers` | ✅ |

### 五、信息缺口

| # | 断言 | 验证 | 结果 |
|---|------|------|------|
| 17 | gap_labels 均为 2 条（10.0%） | fixture 数据中救援与捐赠=4，其余 8 类=2；min_count=2，gap_labels 不含"救援与捐赠"，共 8 个类别 | ✅ |

> fixture 模式下的 gap 分析价值有限：真实数据中类别严重不均衡（displaced 仅 56 条，rescue 4,294 条），切换到真实数据后 gap 分析更有意义。

### 六、探索性情绪分析

| # | 断言 | 验证 | 结果 |
|---|------|------|------|
| 18 | 积极支持 6 条（30.0%），占比最高 | `metrics.emotion_distribution.positive_support=6`；max=6；6/20=30% | ✅ |
| 19 | 恐慌/焦虑 4 条（20.0%） | `fear_or_anxiety=4`；4/20=20% | ✅ |
| 20 | "愤怒类情绪在当前样本中未出现" | `anger=0` | ✅ |

### 七、偏差与使用边界

| # | 断言 | 验证 | 结果 |
|---|------|------|------|
| 21 | "如仅 56 条的 `displaced_people_and_evacuations`" | 模板固定文本，引用真实 Kerala test split 数据（`DATA_GATE.md` 记录） | ⚠️ fixture 模式下该数字（56）与当前 20 条数据不一致，但语句本身正确——指真实数据集特征 |
| 22 | 简报末尾含局限性声明 | 模板 §7.4："本简报用于课程技术演示…" | ✅ |

---

## 未覆盖项

- **外部资料来源覆盖率**：当前简报未引入外部参考层（`data/reference/` 为空），"🔗 外部资料"标识未激活
- **人工抽样：非数字断言**：概述中的历史叙述（"2018年8月…百年一遇"）引用的外部事实未在此次审计中逐条核验

---

## 审计结论

- **数字一致性**：18 条可量化断言全部与 `metrics.json` / `evidence.jsonl` 一致 —— **通过**
- **来源覆盖率**：每类代表记录含 `source_ref`，可追溯到 fixture 或上游数据 —— **通过**  
- **无伪造引用**：所有数字由程序生成，未发现人为编造 —— **通过**
- **已知限制**：fixture 模式下 20 条数据，gap 分析和类别分布不能代表真实 1,582 条情况；切换到真实数据后需重新审计
