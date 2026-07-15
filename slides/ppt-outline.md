# PPT 盲生成规格（唯一输入）

> **版本**：v3.1 · **日期**：2026-07-15  
> **给 PPT 生成 Agent 的唯一输入文件**：仅凭本文生成完整 10 页 `.pptx`。  
> **禁止**：向用户索要仓库路径、截图、指标文件、姓名或其他补充材料。缺姓名时用「成员 A / 成员 B / 成员 C」。缺图时按本文数据现场绘图。  
> **输出**：一份可课堂投影的完整 PPT（16:9），文件名建议 `项目汇报.pptx`。  
> **不含**：演讲逐字稿。

---

## AGENT BRIEF（必须先读）

### 任务

根据下文逐页规格生成 **正好 10 页** 幻灯片。每一页的标题、正文、表格、图表数据、脚注均已给出；按「幻灯片上的文字（逐字）」誊写，不要改数字、不要发明内容。

### 叙事主线（全 deck 一条线）

**为什么选 DeepSeek → 评估数字如何支持 → Lab 3 如何变成可追溯简报与离线看板。**

### 画布与视觉（写死）

| 项 | 值 |
|----|-----|
| 比例 | 16:9 |
| 页数 | 10 |
| 背景 | 白 `#FFFFFF` |
| 主色 | 深蓝 `#0B3D5C`（标题、强调条） |
| 辅色 | 灰字 `#333333` / 浅分隔线 `#D0D7DE` |
| 强调 | 青绿 `#1F7A6B`（仅用于「结论/选型」短句，不用紫色渐变） |
| 字体 | 中文优先「思源黑体 / Noto Sans SC / 微软雅黑」；英文可用同族无衬线。禁止 Inter/Roboto 作为展示标题的唯一选择时，可用 Calibri 或 Noto。 |
| 禁止 | 紫色渐变主题；奶油底+terracotta；卡片堆叠英雄区；浮层徽章；emoji |

每页底部统一页脚（除封面可略小）：

```
HumAID · Kerala 2018 · 课程技术演示，非权威灾情系统 · 课堂投影专用 · {页码}/10
```

### 角色默认名（无真实姓名时原样使用）

| 显示名 | 模块 |
|--------|------|
| 成员 A | Lab 1 数据与隐私 |
| 成员 B | Lab 2 模型与评估 |
| 成员 C | Lab 3 简报与看板 |

### 隐私（生成时遵守）

- 本 deck 为 **课堂投影**：第 7 页使用文中脱敏真实正文。
- 页面上不得出现裸 `@handle`、完整手机号、API Key。
- 若输出用途标注为「公开上传」，则第 7 页改用 §0.9 合成文案（默认按课堂投影生成）。

### 图表生成规则（禁止依赖外部文件）

**不要**去找 `artifacts/figures/*.png`。所有图由 Agent 按本文数据现场绘制并嵌入。

1. **第 6 页唯一图**：DeepSeek 逐类 Precision / Recall / F1 分组柱状图（数据见 §0.7）。
2. **第 8 页**：用本文提供的看板线框 UI 示意（不是真实截图），勿留「截图占位」空白。
3. **第 2、3 页**：简单流程箭头/三列模块，矢量形状即可。

### 验收（生成后自检，全部满足才算完成）

- [ ] 正好 10 页，16:9
- [ ] 第 6 页仅 1 张评估图 + 其下对比表 + 一句话结论
- [ ] 所有百分比/ F1 与 §0.5、§0.7 一致（禁止四舍五入成与表冲突的数）
- [ ] 第 7 页正文含三个 `[USER]`，无裸 `@`
- [ ] 第 8 页含五个 Tab 名与启动命令
- [ ] 封面含 HumAID 署名与「非权威」声明
- [ ] 未向用户追问任何补充信息

---

## 0. 冻结数据字典（全 deck 唯一真值）

### 0.1 语料

- 数据集：HumAID（Alam et al., ICWSM 2021）
- 事件：`kerala_floods_2018`
- 评估 split：官方 **test**，**1,582** 条
- 本地事件合计（train+dev+test）：7,984 条（文献表常见 8,056；差异未文档化，不宣称全集）
- 字段现实：无逐帖时间/地点 → `time`/`location` = null；不做地图与时间趋势
- 指标快照：`2026-07-15T09:53:50Z`

### 0.2 模型总表（第 5、6 页共用）

| 模型 | Coverage | Accuracy | Macro-F1 | Weighted-F1 | 成功子集 Accuracy | 备注 |
|------|----------|----------|----------|-------------|-------------------|------|
| deepseek-v4-flash | 90.5% | 64.0% | 0.553 | 0.720 | 70.7% | 失败 150 条；Coverage 精确值 0.9052 |
| tfidf-lr-baseline-v1 | 100% | 69.9% | 0.403 | 0.655 | 69.9% | 无失败 |

展示用一位小数百分比与三位小数 F1（如上表）。精确值仅供校验：acc 0.6403 / 0.6985；macro_f1 0.5532 / 0.4032。

### 0.3 紧急求助类（选型论据）

类别：`requests_or_urgent_needs`

| | Precision | Recall | F1 |
|--|----------:|-------:|---:|
| deepseek-v4-flash | 70.5% | **70.5%** | 0.705 |
| tfidf-lr-baseline-v1 | 67.6% | **41.0%** | 0.511 |

### 0.4 参考标签分布（test，第 4 页全表）

| 类别（上屏可用短名） | 完整类名 | 条数 |
|----------------------|----------|-----:|
| Rescue & Donation | rescue_volunteering_or_donation_effort | 851 |
| Other Relevant | other_relevant_information | 189 |
| Sympathy & Support | sympathy_and_support | 165 |
| Urgent Needs | requests_or_urgent_needs | 117 |
| Not Humanitarian | not_humanitarian | 90 |
| Injured or Dead | injured_or_dead_people | 72 |
| Infrastructure Damage | infrastructure_and_utility_damage | 59 |
| Caution & Advice | caution_and_advice | 28 |
| Displaced & Evacuations | displaced_people_and_evacuations | 11 |
| **合计** | | **1582** |

### 0.5 隐私审计计数（第 4 页）

全事件 7,984 条模式匹配：账号句柄 **3,494**；10–12 位数字串 **221**；邮箱样 **12**。占位符：`[USER]` / `[NUMBER]` / `[EMAIL]`。

### 0.6 证据卡（第 7 页唯一正文，逐字）

| 字段 | 值 |
|------|-----|
| post_id | `test:1030734738028355584` |
| text_clean | `Current Status: Need food and water. water level arround 5 feet. require rescue #KeralaFloods #KeralaSOS #KeralaFloodsHelpNeeded #SOSKerala [USER] [USER] [USER]` |
| reference_label | `requests_or_urgent_needs` |
| predicted_label (DeepSeek) | `requests_or_urgent_needs` |
| pii_redacted | `true` |
| evidence_status | `dataset_record` |
| source_ref | `humaid_events:test:1030734738028355584` |

### 0.7 第 6 页图：DeepSeek 逐类 P / R / F1（现场绘制）

**图题**：`Per-Class Precision / Recall / F1 — deepseek-v4-flash`

**类型**：分组柱状图；Y 轴 Score 0.0–1.0；X 轴 9 类（用短名）；图例三色：Precision / Recall / F1。

| X 轴短名 | Precision | Recall | F1 |
|----------|----------:|-------:|---:|
| Caution & Advice | 0.389 | 0.538 | 0.452 |
| Displaced & Evacuations | 0.143 | 0.222 | 0.174 |
| Infrastructure Damage | 0.600 | 0.360 | 0.450 |
| Injured or Dead | 0.849 | 0.738 | 0.790 |
| Not Humanitarian | 0.350 | 0.675 | 0.461 |
| Other Relevant | 0.412 | 0.451 | 0.431 |
| Urgent Needs | 0.705 | 0.705 | 0.705 |
| Rescue & Donation | 0.896 | 0.798 | 0.844 |
| Sympathy & Support | 0.658 | 0.689 | 0.673 |

X 轴顺序按上表固定（与常见评估输出一致即可；若需按 F1 排序，仍须保留全部 9 类与上表数值）。

### 0.8 署名（封面脚注）

```
数据：HumAID (Alam et al., ICWSM 2021) · Event: kerala_floods_2018
来源页：https://crisisnlp.qcri.org/humaid_dataset.html · HF: QCRI/HumAID-events
许可口径：按较严研究专用/保密条款；原始正文不公开再分发
```

### 0.9 公开上传替身（仅当用户明确要求公开版时）

```
Synthetic: Need food and water near flooded area; require rescue assistance. [USER]
post_id: fixture:demo-urgent-01 · source: synthetic_fixture
```

---

## 第 1 页 — 封面

### 布局线框

```
[可选简线图标]
主标题（大）
副标题
成员 A（Lab 1） · 成员 B（Lab 2） · 成员 C（Lab 3）
────────────
署名脚注（§0.8）
非权威灾情系统，仅供课程演示 · 课堂投影专用
```

### 幻灯片上的文字（逐字）

- 主标题：`社交媒体人道信息分析：Kerala 2018 洪水课程演示流水线`
- 副标题：`社会计算课程实践 · 三人小组 · 2026`
- 姓名行：`成员 A（Lab 1） · 成员 B（Lab 2） · 成员 C（Lab 3）`
- 脚注：§0.8 全文 + `非权威灾情系统，仅供课程演示 · 课堂投影专用`

### 视觉

白底；主标题用主色；最多一个线框图标；无统计条、无徽章。

---

## 第 2 页 — 问题与定位

### 标题

`问题：无时空字段时，如何做可追溯的人道信息分析？`

### 布局

左 60% bullets；右 40% 三框箭头：`海量社媒帖子 → 9 类人道标签 → 中文可追溯简报 + 离线看板`

### 正文（逐字，5 条）

1. **背景**：2018 年 Kerala 洪水期间，社交媒体出现大量求助、救援协调与人道相关信息。
2. **课程问题**：在没有逐帖时间与地点的前提下，如何从英文推文识别人道类别，并生成可追溯的中文课程分析简报？
3. **边界**：历史事件复盘型技术演示；不发布预警；不替代官方救灾结论。
4. **本组交付链**：分类对比（baseline vs LLM）→ 结构化指标与证据 → Streamlit 离线看板。
5. **数据锚点**：HumAID `kerala_floods_2018` 官方 test，**1,582** 条。

### 主讲标注（小字角落可选）

`主讲：成员 C → 成员 A`

---

## 第 3 页 — 流水线与分工

### 标题

`系统流水线与三人分工`

### 顶栏数据流（逐字）

`本地 raw（不入库） → 清洗脱敏 posts_clean → posts_labeled + predictions → D07 metrics/evidence → briefing + Streamlit`

### 三列模块（逐字）

**Lab 1 · 成员 A**

- 输入：冻结 HumAID / fixture
- 做什么：适配、标准化、脱敏、质量报告
- 产出：`posts_clean*.jsonl`、`data_quality.md`

**Lab 2 · 成员 B**

- 输入：清洗后帖子
- 做什么：TF-IDF baseline + DeepSeek Few-shot；正式评估
- 产出：`posts_labeled.jsonl`、`predictions.jsonl`、评估图

**Lab 3 · 成员 C**

- 输入：标签与预测
- 做什么：聚合指标、证据清单、中文简报、离线看板
- 产出：`metrics.json`、`evidence.jsonl`、`briefing.md`、`app.py`

### 页脚两行

- 接口字段：`post_id`、`text_clean`、`pii_redacted`、`_lab2.reference_label`；预测在 `predictions.jsonl`（键：`post_id` + `model_version`）。
- 协作：B/C 用 20 条合成 fixture 并行；回归：`bash run_pipeline.sh --fixture --offline`。

---

## 第 4 页 — Lab 1 数据门禁

### 标题

`Lab 1：数据门禁、冻结语料与脱敏`

### 上半四条打勾清单（逐字）

1. 单一事件：`kerala_floods_2018`；**test = 正式评估集**；train/dev 仅开发，不混入 test 指标。
2. 每条仅有 tweet_id / tweet_text / class_label → `time`、`location` 为 null；**不做地图、不做时间趋势**。
3. 隐私审计（7,984 条）：句柄 **3,494** · 数字串 **221** · 邮箱 **12** → `[USER]` / `[NUMBER]` / `[EMAIL]`。
4. 类别极度不平衡（见下表）→ 必须报告 **Macro-F1**，不能只报 Accuracy。

### 中部表

粘贴 §0.4 全表（短名 + 条数即可；完整类名可作鼠标提示或省略）。

### 强调框（逐字）

`公开材料无正文；课堂投影可展示脱敏正文；原始下载仅本地。`

### 脱敏示例一行

`规则后示例：… require rescue #KeralaFloods … [USER] [USER] [USER]`

---

## 第 5 页 — 为何选 DeepSeek

### 标题

`Lab 2：模型选型 — 为何主路径用 DeepSeek`

### 左表（逐字）

| 维度 | tfidf-lr-baseline-v1 | deepseek-v4-flash |
|------|----------------------|-------------------|
| 类型 | TF-IDF + 逻辑回归 | LLM Few-shot 分类 |
| 覆盖率 | 100% | 90.5%（150 条失败） |
| 优势 | 稳定、可复现、零 API | 语义边界与稀缺类更灵活 |
| 风险 | 易偏向高频「救援志愿」类 | 需处理失败样本与成本 |
| 课程演示 | 始终可离线重跑 | 复用已跑批预测，演示可不调 API |

### 右三条（逐字）

1. **表述多样**：灾害推文同义表达多，纯词袋易被多数类淹没。
2. **决策相关类**：DeepSeek 在 Urgent Needs 上 Recall **70.5%**（baseline **41.0%**）；Macro-F1 **0.553 vs 0.403**。
3. **可交付**：预测已落盘；`bash run_pipeline.sh` 重建看板，不依赖现场密钥。

### 页脚

`仅发送 pii_redacted=true 的脱敏文本至 API；原始正文永不外发。`

---

## 第 6 页 — 评估结果（单图）

### 标题

`Lab 2：正式 test（1,582）评估 — DeepSeek 逐类表现`

### 布局（强制）

1. 上方 ~65%：按 §0.7 **现场绘制**分组柱状图（本页唯一图）。
2. 下方表：模型总对比。
3. 最下一句结论。

**禁止**再贴第二张图。

### 图下表（逐字）

| 模型 | Coverage | Accuracy | Macro-F1 |
|------|----------|----------|----------|
| deepseek-v4-flash | 90.5% | 64.0% | 0.553 |
| tfidf-lr-baseline-v1 | 100% | 69.9% | 0.403 |

小字：`DeepSeek 成功子集 Acc 70.7%；Urgent Needs Recall 70.5%（baseline 41.0%）`

### 结论句（逐字，青绿强调）

`Baseline 整体 Accuracy 更高，但 DeepSeek 的 Macro-F1 与紧急求助类召回更均衡，因此 Lab 3 以 DeepSeek 预测作为主证据源。`

---

## 第 7 页 — 证据卡与 Lab 3

### 标题

`Lab 3：从预测到可追溯决策支持`

### 左：证据卡

标题：`Evidence · test:1030734738028355584`

正文（等宽，允许自动换行，内容不得改）：

```
Current Status: Need food and water. water level arround 5 feet. require rescue #KeralaFloods #KeralaSOS #KeralaFloodsHelpNeeded #SOSKerala [USER] [USER] [USER]
```

元数据：

- `reference: requests_or_urgent_needs`
- `DeepSeek: requests_or_urgent_needs`
- `pii_redacted: true · evidence_status: dataset_record`
- `source_ref: humaid_events:test:1030734738028355584`

### 右：四条（逐字）

1. **D07 聚合**：`metrics.json` + `evidence.jsonl` 可追溯到 `source_ref`。
2. **中文简报**：`briefing.md` 模板约束；关键数字可审计。
3. **离线看板**：Streamlit；断网可演示。
4. **使用边界**：数据集记录与模型输出，**不是**现场核实灾情结论。

### 底栏

`无时间/地点 → 不做地图与实时趋势。本页含脱敏真实正文，仅课堂投影，勿公开上传。`

---

## 第 8 页 — 系统演示（看板示意）

### 标题

`系统演示：离线看板与启动方式`

### 主视觉：看板线框（Agent 必须画成 UI 示意，勿留空白）

按真实产品五个 Tab 绘制（名称逐字）：

```
┌─ Kerala 2018 洪水社交媒体分析看板 ─────────────────────┐
│ [数据范围与质量] [分类与评估] [代表性记录] [探索性情绪] [课程分析简报] │
│ ★ 当前选中：数据范围与质量                                      │
│                                                          │
│  唯一帖子数：1,582                                          │
│  模型：deepseek-v4-flash · tfidf-lr-baseline-v1            │
│  说明：完整本地看板；脱敏正文；断网可用                        │
│                                                          │
│  ┌ 质量摘要 ──────────────────────────────────────────┐   │
│  │ pii_redacted = true · time/location = null         │   │
│  └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### 命令框（逐字）

```bash
bash run_pipeline.sh
streamlit run app.py
```

`clean clone 用已脱敏 posts/predictions 重建看板，无需 API。`

### 演示顺序（上屏）

1. 数据范围与质量 → 确认 1,582 与脱敏  
2. 分类与评估 → 对照第 6 页数字  
3. 代表性记录 → 指出 `[USER]`  
4. 课程分析简报 → 强调可追溯  

（探索性情绪 Tab 可在示意中画出但不作为演示重点。）

---

## 第 9 页 — 局限与风险

### 标题

`局限、风险与合规边界`

### 左列「数据与许可」

- 单事件、英文、无逐帖时空字段。
- 本地 7,984 vs 文献常见 8,056：差异未说明；冻结本地版本，不宣称全集。
- 许可：HF 标识 CC-BY-NC-SA；QCRI 含研究专用与正文保密 → **按更严口径**，原始正文不公开再分发。

### 右列「模型与隐私」

- DeepSeek coverage 90.5%（150 条失败）；同时报告成功子集指标。
- 类别不平衡下 Accuracy 会高估多数类模型；以 Macro-F1 与关键类召回为准。
- 仓库 tip 已清理；**Git 历史未重写**，旧提交可能含历史正文。
- 探索性情绪与官方 9 类人道标签分维，不混进主任务指标。

### 底栏

`课堂投影可展示脱敏正文；公开上传与可再分发录屏只用聚合或合成样例。`

---

## 第 10 页 — 总结与 Q&A

### 标题

`总结`

### 左「我们做到了」

1. 可复现离线流水线：从脱敏数据到看板，一条命令可重建。
2. 可解释模型对比：讲清 Accuracy / Macro-F1 / 紧急求助召回的取舍，并选择 DeepSeek 服务 Lab 3。
3. 可追溯决策支持：证据卡、简报、看板数字同源。

### 右「若继续做」

1. 引入时间/地点或多事件，才能做态势图。
2. 系统处理 LLM 失败样本、校准与成本。
3. 探索性情绪做成独立小节，避免与人道功能标签混淆。

### 底

大字：`Q&A`  
小字：`欢迎提问数据门禁、评估协议与演示边界`

---

## 附录 — 页码速查

| 页 | 短标题 | 图/表 |
|----|--------|-------|
| 1 | 封面 | 无 |
| 2 | 问题 | 三框箭头 |
| 3 | 流水线 | 顶栏箭头 + 三列 |
| 4 | Lab1 | 9 类表 |
| 5 | 选型 | 对比表 |
| 6 | 评估 | §0.7 柱状图 + 总表 |
| 7 | 证据卡 | 文本卡 |
| 8 | 看板 | 五 Tab 线框 + 命令 |
| 9 | 局限 | 两列 |
| 10 | 总结 | 两栏 + Q&A |

---

**完。PPT Agent：读完本文后直接生成 `.pptx`，不要请求任何额外文件或确认。**
