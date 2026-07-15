# 探索性情绪标注 — 标注者间一致率报告 (IAA)

> 交付物：D04（情绪标注部分）  
> 日期：2026-07-15  
> 标注人数：3 人（成员 A、B、C）  
> 样本来源：HumAID Kerala 2018 train split，分层抽样 14 条  
> 说明：本报告仅含聚合一致率，不含推文正文。可用 `python -m src.lab2_analysis.annotate_seed iaa` 在本地标注文件上重算并覆盖写入。

---

## 一、标注流程

1. 成员 B 从 train split 分层抽样 14 条（覆盖全部 9 个人道信息类别）
2. 三人独立标注，每人从 5 个情绪标签中为每条记录选择一个标签
3. 标注完成后计算三组两两 Cohen's κ

## 二、标注分布

| 情绪标签 | 成员 A | 成员 B | 成员 C |
|----------|:---:|:---:|:---:|
| `fear_or_anxiety` | 3 | 2 | 3 |
| `anger` | 1 | 1 | 1 |
| `sadness` | 0 | 2 | 3 |
| `positive_support` | 4 | 5 | 5 |
| `neutral_or_unclear` | 6 | 4 | 2 |
| **合计** | **14** | **14** | **14** |

## 三、两两 IAA

| 配对 | Raw Agreement | Cohen's κ | 判定 |
|------|:---:|:---:|:---:|
| A ↔ B | 78.6% | 0.71 | ✅ |
| B ↔ C | 78.6% | 0.72 | ✅ |
| A ↔ C | 71.4% | 0.64 | ✅ |
| **平均** | **76.2%** | **0.69** | ✅ |

**合格标准**：每组 κ ≥ 0.6 → **全部通过**。

## 四、逐标签一致率

| 情绪标签 | A↔B | B↔C | A↔C | 平均 | 评价 |
|----------|:---:|:---:|:---:|:---:|------|
| `anger` | 100% | 100% | 100% | **100%** | 完全一致 |
| `positive_support` | 80% | 100% | 80% | **87%** | 高度一致 |
| `fear_or_anxiety` | 67% | 67% | 100% | **78%** | 较一致 |
| `neutral_or_unclear` | 67% | 50% | 33% | **50%** | 中等分歧 |
| `sadness` | 0% | 25% | 0% | **8%** | 严重分歧 |

## 五、主要分歧分析

**`sadness` 是分歧最大的标签**。分歧主要源于：

1. **sadness vs fear_or_anxiety 边界模糊**：描述受灾者困境的文本（如 "homeless"、"trapped"、"pray for us"），有人判为悲伤（关注已发生的损失），有人判为恐慌/焦虑（关注未来的不确定性）
2. **sadness vs neutral_or_unclear 边界模糊**：客观报道伤亡数字的文本（如 "91 persons killed, toll rose to 164"），有人判为悲伤（隐含对伤亡的哀悼），有人判为中性（纯事实陈述）

**建议**：在评估报告和最终简报中，`sadness` 类别的结论需标注"标注者间一致率偏低（κ 维度 <0.25）"，`positive_support` 和 `anger` 的结论可信度较高。

## 六、最终标签

采用成员 B 的标注结果作为最终开发样本标签（B 为 Lab 2 负责人）：

| # | tweet_id | class_label | emotion (final) |
|---|----------|-------------|-----------------|
| 1 | ...46617857 | rescue_volunteering_or_donation_effort | neutral_or_unclear |
| 2 | ...70611457 | rescue_volunteering_or_donation_effort | fear_or_anxiety |
| 3 | ...15658752 | requests_or_urgent_needs | positive_support |
| 4 | ...48679939 | infrastructure_and_utility_damage | neutral_or_unclear |
| 5 | ...81212675 | displaced_people_and_evacuations | sadness |
| 6 | ...24590592 | caution_and_advice | fear_or_anxiety |
| 7 | ...87976448 | rescue_volunteering_or_donation_effort | positive_support |
| 8 | ...33150720 | not_humanitarian | anger |
| 9 | ...95650560 | injured_or_dead_people | neutral_or_unclear |
| 10 | ...42787072 | rescue_volunteering_or_donation_effort | positive_support |
| 11 | ...08158213 | rescue_volunteering_or_donation_effort | positive_support |
| 12 | ...12305152 | other_relevant_information | neutral_or_unclear |
| 13 | ...04259585 | rescue_volunteering_or_donation_effort | positive_support |
| 14 | ...00064007 | sympathy_and_support | sadness |
