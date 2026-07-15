# Urban Flood Social Sensing

面向社会计算课程实践的 Kerala 2018 洪水社交媒体人道信息分析项目。以 HumAID 单事件冻结语料为输入，完成数据治理、baseline 与 LLM 的 9 类人道信息分类对比、探索性情绪分析、D07 结构化聚合，以及可追溯的中文课程简报和离线看板。

> 当前状态：clean clone 后执行 `bash run_pipeline.sh` 即可用仓库内脱敏真实 posts/predictions 生成完整看板；无需 API、无需 raw HumAID。`--fixture --offline` 仍可用于 20 条合成演示。

## 项目边界

- 历史事件复盘型课程技术演示，不是实时灾情监测系统；
- 不发布预警、救援建议或权威灾情结论；
- 主流程固定使用 HumAID `kerala_floods_2018` 官方 test split 的 1,582 条唯一帖子；
- 数据没有逐帖时间和地点，不生成地图或时空推断；
- tip 跟踪脱敏后的 `posts_labeled.jsonl` / `predictions.jsonl`（含正文）；raw 与 API 密钥仍不入库；
- Git 历史未重写，历史 blob 仍可能含未清理正文（见 `docs/project/DATA_GATE.md` §8）；
- 核心演示必须支持断网运行。

## 三个模块

| 模块 | 输入 | 输出 |
|------|------|------|
| Lab 1 数据采集与清洗 | 冻结原始数据 / fixture | `posts_clean*.jsonl`、数据质量报告 |
| Lab 2 分类与评估 | Lab 1 清洗结果 | `posts_labeled.jsonl` + `predictions.jsonl`、评估报告 |
| Lab 3 决策支持 | Lab 2 结果 | D07 `metrics.json` / `evidence.jsonl`、简报、离线看板 |

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock   # 或 requirements.txt
cp .env.example .env               # 仅在需要重新调用 DeepSeek 时填写

# clean clone 默认：复用仓库内 1,582 条脱敏真实预测，生成完整看板（无 API）
bash run_pipeline.sh
streamlit run app.py

# 可选：仅 synthetic fixture（20 条）
bash run_pipeline.sh --fixture --offline
```

看板读取流水线产物：`data/output/metrics.json`、`evidence.jsonl`、`briefing.md`。公开聚合指标副本仍见 [`data/output/metrics.public.json`](data/output/metrics.public.json)。

## 复用已有 DeepSeek 结果（可选，本地）

若本地仍保留 PR6 时代的多模型 `posts_labeled` 长表，可无 API 迁移：

```bash
python -m src.lab2_analysis.classify --from-legacy path/to/legacy_posts_labeled.jsonl
python -m src.lab3_decision.build_evidence
python -m src.lab2_analysis.evaluate
```

## 重要文档

- [项目实施方案](docs/project/实施方案.md)
- [数据准入与合规边界](docs/project/DATA_GATE.md)
- [环境检查](docs/project/environment_check.md)
- [评估报告](docs/project/evaluation.md)
- [协作规范](CONTRIBUTING.md)
