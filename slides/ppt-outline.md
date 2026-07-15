# 项目汇报 Slides 大纲 v2.1

> **用途**：课堂现场投影（非公开再分发 deck）。不含演讲稿，仅页面布局、文案要点、图表与分工。
>
> **叙事主线（方向 2）**：为什么选 DeepSeek → 评估结论 → Lab 3 决策支持产物（简报 + 离线看板）。
>
> **合规依据**：[`docs/project/DATA_GATE.md`](../docs/project/DATA_GATE.md) §4（三层面隐私）、§5.6（可分享 vs 课堂 Slides）；[`docs/project/实施方案.md`](../docs/project/实施方案.md) DoD L633–634。
>
> **指标锁定**：[`data/output/metrics.public.json`](../data/output/metrics.public.json)（`generated_at`: 2026-07-15T09:53:50Z，1,582 条 test 帖子）。

---

## 全局约束

| 项 | 约定 |
|----|------|
| 页数 | **10 页**（含封面与收尾） |
| 分发 | **仅课堂投影**；若上传课程平台，改用聚合表 + `tests/fixtures/` 合成样例，不含可搜索真实正文 |
| 正文样例 | 允许展示经 `redact.py` 脱敏的 `text_clean`（`pii_redacted: true`，无裸 `@handle`） |
| 图表 | 优先仓库内 `artifacts/figures/`；缺失时由成员 B 在汇报前从 `evaluate.py` 再生成 |
| 三人分工 | A = Lab 1 / 数据与隐私；B = Lab 2 / 评估与模型；C = Lab 3 / 简报与看板 |

---

## 第 1 页 — 封面

**布局**：全幅标题居中；副标题与三人姓名横排于页脚。

**文案要点**

- 标题：*社交媒体人道信息分析：Kerala 2018 洪水课程演示流水线*
- 副标题：社会计算课程实践 · 三人小组 · 2026
- 脚注：HumAID 数据集引用（论文 + Hugging Face 事件页）；**非权威灾情系统，仅供课程演示**

**视觉**：浅色底 + 单张示意洪水/社交媒体图标（可用 CC 图标或自制线框，勿用未授权新闻图）。

**讲解人**：三人轮流一句自我介绍（无稿：姓名 + 负责 Lab）。

---

## 第 2 页 — 问题与决策支持定位

**布局**：左 60% 文字要点；右 40% 一张「信息过载 → 结构化简报」示意箭头图。

**文案要点**

- **背景**：2018 Kerala 洪水期间，社交媒体涌现大量求助、救援协调与人道信息
- **课程问题**：如何在**无实时时空字段**的前提下，从英文推文识别人道类别并生成**可追溯**的中文分析简报？
- **边界声明**（小字）：历史复盘演示；不发布预警；不替代官方救灾渠道
- **本组产出**：分类对比 → D07 指标与证据 → Streamlit 离线看板

**数据锚点**：主语料 HumAID `kerala_floods_2018` **test**，**1,582** 条（见 DATA_GATE §2）。

**讲解人**：C（30s）→ A 接数据边界（20s）。

---

## 第 3 页 — 流水线与三人分工

**布局**：横向三列 Lab 卡片 + 顶部一条数据流箭头（raw 本地 → clean → labeled/predictions → D07 → 看板）。

**文案要点**

| Lab | 负责人 | 核心产出 |
|-----|--------|----------|
| Lab 1 | A | 适配、脱敏、`posts_clean`、质量报告 |
| Lab 2 | B | TF-IDF baseline + DeepSeek Few-shot、`predictions.jsonl`、评估 |
| Lab 3 | C | `metrics.json`、`evidence.jsonl`、`briefing.md`、`app.py` |

- 统一 schema：`post_id` / `text_clean` / `_lab2` / 独立 `predictions.jsonl`
- 协作节奏：B/C 用 fixture 并行开发；每日 `--fixture --offline` 回归

**视觉**：可复用实施方案 §3 架构图简化版（方框 + 箭头即可）。

**讲解人**：A 讲 Lab1 接口（40s）；B、C 各补一句下游依赖（各 15s）。

---

## 第 4 页 — Lab 1：数据门禁与脱敏

**布局**：上：DATA_GATE 检查清单 4 项打勾；下：脱敏前后对比小卡（合成或脱敏真实各一行）。

**文案要点**

- 冻结 split：train/dev 仅开发；**test = 正式评估**
- 隐私审计（DATA_GATE §4）：账号句柄 3,494 / 数字串 221 / 邮箱 12 → 占位符 `[USER]` `[NUMBER]` `[EMAIL]`
- **三层面**（必念一句）：公开 tip 无正文；**课堂 Slides 可展示脱敏正文**；raw 仅本地
- 质量：9 类分布极不均衡 → 评估必须报 Macro-F1（不只 Accuracy）

**表格（可选，来自 `metrics.public.json` `reference_label_distribution` 摘要）**

| 类别（示意） | 条数 |
|--------------|-----:|
| rescue_volunteering… | 851 |
| requests_or_urgent_needs | 117 |
| … | … |

**讲解人**：A。

---

## 第 5 页 — Lab 2：为什么选 DeepSeek

**布局**：左：模型选型对比表；右：Few-shot / 覆盖与失败处理要点。

**文案要点**

- **对比对象**：`tfidf-lr-baseline-v1`（全量覆盖）vs `deepseek-v4-flash`（Few-shot LLM）
- **选型理由**（方向 2 核心页）：
  1. 英文灾害推文表述多样，词袋模型易偏向高频类「救援志愿」
  2. LLM 在**稀缺类**与**语义边界**上更灵活（配合下一页数字）
  3. 课程约束：可复用已跑批预测，离线演示不依赖 API
- **合规**：仅发送 `pii_redacted: true` 文本至 API（DATA_GATE §7 团队决议）

**讲解人**：B。

---

## 第 6 页 — Lab 2：评估结果（单图）

**布局**：**整页仅一张图**，图下 3 行指标-caption；无第二张子图。

**嵌入资源（锁定）**

```
artifacts/figures/accuracy_chart.png
```

**图下数字（锁定，四舍五入展示）**

| 模型 | Coverage | Accuracy | Macro-F1 | 备注 |
|------|----------|----------|----------|------|
| deepseek-v4-flash | **90.5%** | **64.0%** | **0.553** | 成功子集 Acc **70.7%** |
| tfidf-lr-baseline-v1 | 100% | **69.9%** | **0.403** | 高频类 Acc 占优 |

**口述钩子（无稿，要点）**：整体 Accuracy baseline 更高，但 Macro-F1 与 **requests_or_urgent_needs 召回 70.5%** 显示 LLM 对**决策相关稀缺类**更均衡——故 Lab 3 以 DeepSeek 预测为主证据源。

**讲解人**：B。

---

## 第 7 页 — Lab 3：证据卡与决策支持

**布局**：左侧一张**证据卡**（大卡）；右侧 4 条简报字段 bullet；底部局限性一行。

**证据卡（锁定 `post_id`）**

| 字段 | 值 |
|------|-----|
| `post_id` | `test:1030734738028355584` |
| `text_clean` | `Current Status: Need food and water. water level arround 5 feet. require rescue #KeralaFloods #KeralaSOS #KeralaFloodsHelpNeeded #SOSKerala [USER] [USER] [USER]` |
| `reference_label` | `requests_or_urgent_needs` |
| `predicted_label` (DeepSeek) | `requests_or_urgent_needs` |
| `pii_redacted` | `true` |
| `evidence_status` | `dataset_record` |

**右侧要点**

- D07：`metrics.json` + `evidence.jsonl` 可追溯到 `source_ref`
- 简报：模板约束生成，20 条断言可审计（`briefing_audit.md`）
- 看板：质量 / 分布 / 脱敏样例 / 简报 四 Tab，**断网可用**
- 局限：无时间地点 → 不做地图与实时趋势

**合规脚注**：本页正文来自 tracked `posts_labeled.jsonl` 脱敏行；**勿将本页导出上传公开平台**（DATA_GATE §5.6）。

**讲解人**：C。

---

## 第 8 页 — 系统演示（看板）

**布局**：一张 Streamlit 截图占位（16:9），标注四个 Tab 名称；右下角放启动命令框。

**文案要点**

- 演示路径：`bash run_pipeline.sh` → `streamlit run app.py`
- 展示顺序建议：① 数据质量 ② 标签分布（可用 `category_distribution.png` 缩略图）③ 脱敏文本样例 ④ 简报摘要
- 兜底：`artifacts/demo/demo.mp4` 录屏（若投屏失败）

**讲解人**：C 操作；A 核对脱敏字段；B 核对指标与图表一致。

---

## 第 9 页 — 局限与风险

**布局**：两列 bullet；底栏引用 DATA_GATE §8。

**文案要点**

- **数据**：单事件、英文、无时空；HumAID 本地 7,984 vs QCRI 表 8,056 差异未文档化
- **模型**：DeepSeek 150 条失败（coverage 90.5%）；类别不平衡下 Accuracy 误导
- **隐私**：tip 已清理；**Git 历史或未重写**，旧 blob 仍可能含历史正文
- **许可**：CC-BY-NC-SA vs QCRI 研究专用 — 按更严口径，raw 不公开

**讲解人**：A（隐私）+ B（评估）各半页。

---

## 第 10 页 — 总结与 Q&A

**布局**：左：三行「我们做到了」；右：三行「若继续做」；底部大字 Q&A。

**我们做到了**

1. 可复现离线流水线（clean clone 可重建看板）
2. Baseline vs LLM 可解释对比（Macro-F1 + 稀缺类召回）
3. 可追溯决策支持产物（证据卡 + 简报 + 看板）

**若继续做**

- 补时间/地点或多事件泛化
- 校准 LLM 失败样本与成本
- 探索性情绪与 9 类人道功能分离汇报

**讲解人**：三人各一句收尾 → Q&A。

---

## 资产清单

| 资产 | 路径 | 用于页码 | 状态 |
|------|------|----------|------|
| 准确率对比图 | `artifacts/figures/accuracy_chart.png` | 6 | 汇报前由 B 生成/确认 |
| 类别分布图 | `artifacts/figures/category_distribution.png` | 8（可选缩略） | 同上 |
| 公开指标 | `data/output/metrics.public.json` | 4、6 | ✅ 已入库 |
| 脱敏帖子 | `data/analyzed/posts_labeled.jsonl` | 7 | ✅ tip 跟踪 |
| 预测 | `data/analyzed/predictions.jsonl` | 7 | ✅ tip 跟踪 |
| 合成样例 | `tests/fixtures/sample_*.jsonl` | 公开版 deck 备用 | ✅ |
| 看板 | `app.py` | 8 | ✅ |
| 录屏 | `artifacts/demo/demo.mp4` | 8 兜底 | 待录制 |

---

## 页码—讲解人速查

| 页 | 主题 | 主讲 |
|----|------|------|
| 1 | 封面 | 三人 |
| 2 | 问题定位 | C → A |
| 3 | 分工架构 | A |
| 4 | Lab 1 | A |
| 5 | 模型选型 | B |
| 6 | 评估图 | B |
| 7 | 证据卡 | C |
| 8 | 看板演示 | C |
| 9 | 局限 | A + B |
| 10 | 总结 Q&A | 三人 |

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.1 | 2026-07-15 | 锁定 10 页、方向 2、第 6 页单图、第 7 页证据卡 `test:1030734738028355584`、DATA_GATE 三层面合规 |
| v2.0 | 2026-07-15 | 访谈定稿：课堂投影、无演讲稿、允许脱敏真实正文 |
| v1.x | — | 头脑风暴草案（已 supersede） |
