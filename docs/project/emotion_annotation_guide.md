# 探索性情绪标注 — 操作指南

> 交付物：D04（情绪标注部分）  
> 负责人：成员 B（工具 + IAA）  
> 标注人：成员 A + 成员 B（两人独立标注同一批数据）  
> 截止：Day 2 上午

---

## 一、背景

本项目在 HumAID 官方 9 类人道信息标签之外，增加了**探索性情绪分析**作为课程补充实验。情绪标签为 5 类单标签：

| 标签 | 含义 | 典型特征 |
|------|------|----------|
| `fear_or_anxiety` | 恐慌/焦虑 | 担心安全、求助紧迫感、未来不确定性、警示语气 |
| `anger` | 愤怒 | 指责、不满、批评政府/机构/个人、攻击性言论 |
| `sadness` | 悲伤 | 哀悼伤亡、同情受灾者、对困境的无奈或惋惜 |
| `positive_support` | 积极支持 | 鼓励、感恩、团结、行动号召、建设性态度 |
| `neutral_or_unclear` | 中性/无法判断 | 客观陈述事实、转发信息、政策公告、无法从文本判断情绪 |

**重要**：情绪标签与 9 类人道信息标签是**不同维度**——例如"求助紧急需求"可以带有恐慌情绪，也可以带有积极求助的态度。请根据文本语气而非人道信息类别来判断。

---

## 二、操作步骤

### 2.1 拉取最新代码

```bash
cd urban-flood-social-sensing
git checkout lab2/analysis-baseline-llm
git pull origin lab2/analysis-baseline-llm
```

### 2.2 打开标注文件

标注文件位于 `data/seed/emotion_dev_member_a.jsonl`，已包含 14 条待标注记录。每条记录格式如下：

```json
{
  "tweet_id": "1032238513146617857",
  "text_clean": "已脱敏的推文文本",
  "class_label": "rescue_volunteering_or_donation_effort",
  "exploratory_emotion": null,
  "annotator": "member_a"
}
```

**你需要做的**：将每条记录的 `"exploratory_emotion": null` 替换为五个标签之一，例如：

```json
"exploratory_emotion": "fear_or_anxiety"
```

### 2.3 标注方法

在 IDE（VS Code）中直接打开 `data/seed/emotion_dev_member_a.jsonl`，逐行编辑 `exploratory_emotion` 字段。

或者在 Python 中交互式标注：

```bash
python3 -c "
import json

path = 'data/seed/emotion_dev_member_a.jsonl'
records = [json.loads(l) for l in open(path) if l.strip()]

LABELS = ['fear_or_anxiety','anger','sadness','positive_support','neutral_or_unclear']
for i, r in enumerate(records):
    print(f'\n--- Record {i+1}/14 ---')
    print(f'class_label: {r[\"class_label\"]}')
    print(f'text: {r[\"text_clean\"][:200]}')
    print(f'Labels: {\" | \".join(LABELS)}')
    label = input('Your label: ').strip()
    while label not in LABELS:
        label = input(f'Invalid. Must be one of {LABELS}: ').strip()
    r['exploratory_emotion'] = label

with open(path, 'w') as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print(f'\nSaved {len(records)} annotations to {path}')
"
```

### 2.4 标注原则

1. **基于文本语气**，不要仅根据 `class_label`（人道信息类别）推断情绪
2. **优先判断显性情绪**：有明显情感词的选对应标签，纯客观信息选 `neutral_or_unclear`
3. **单标签**：每条记录选最突出的一个情绪
4. **独立标注**：不要与成员 B 讨论，标注完成后再比较

### 2.5 推送标注结果

```bash
git add data/seed/emotion_dev_member_a.jsonl
git commit -m "annotate(emotion): member A completes 14 dev annotations"
git push origin lab2/analysis-baseline-llm
```

---

## 三、验收标准（IAA）

标注完成后，成员 B 运行 IAA 计算：

```bash
python -m src.lab2_analysis.annotate_seed iaa \
  data/seed/emotion_dev_member_b.jsonl \
  data/seed/emotion_dev_member_a.jsonl
```

**合格标准**：Cohen's κ ≥ 0.6

若 κ < 0.6，两人讨论分歧记录后修正，重新计算。

---

## 四、标注完成后

IAA 通过后，由成员 B 统一将情绪标签合并到 `posts_labeled.jsonl`，并锁定评估样本（从 test 中抽取，不参与 Prompt 调整）。

---

## 附录：情绪标签判断参考

| 文本特征 | 建议标签 |
|----------|----------|
| "please help", "urgent", "stranded", "trapped" | `fear_or_anxiety` |
| "failure", "inaction", "shame", 攻击性词汇 | `anger` |
| "killed", "died", "lost everything", "homeless" | `sadness` |
| "donate", "volunteer", "proud", "thank", "together" | `positive_support` |
| 纯事实陈述、转发、统计数据、政策公告 | `neutral_or_unclear` |
