# Urban Flood Social Sensing

面向社会计算课程实践的 Kerala 2018 洪水社交媒体人道信息分析项目。以 HumAID 单事件冻结语料为输入，完成数据治理、baseline 与 LLM 的 9 类人道信息分类对比、探索性情绪分析、D07 结构化聚合，以及可追溯的中文课程简报和离线看板。

> 当前状态：本地默认 `bash run_pipeline.sh` 会生成完整看板产物（`metrics.json` / `evidence.jsonl` / `briefing.md`）；无 legacy 时回退到 `bash run_pipeline.sh --fixture --offline`。

## 项目边界

- 历史事件复盘型课程技术演示，不是实时灾情监测系统；
- 不发布预警、救援建议或权威灾情结论；
- 主流程固定使用 HumAID `kerala_floods_2018` 官方 test split 的 1,582 条唯一帖子；
- 数据没有逐帖时间和地点，不生成地图或时空推断；
- 原始社交媒体正文与 API 密钥不进入当前 tip；公开 tip 仅含聚合指标与合成样例；
- Git 历史未重写，历史 blob 仍可能含真实正文（见 `docs/project/DATA_GATE.md` §8）；
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
cp .env.example .env               # 真实 DeepSeek 运行才需要；legacy 迁移不需要

# 默认：本地有 legacy 时生成 1,582 条真实完整看板；否则回退 synthetic fixture
bash run_pipeline.sh

# clean clone / CI：仅 synthetic fixture
bash run_pipeline.sh --fixture --offline

streamlit run app.py               # 读取 data/output/metrics.json 等本地产物
```

看板默认读取本地完整 D07 产物：[`data/output/metrics.json`](data/output/metrics.json)、[`data/output/evidence.jsonl`](data/output/evidence.jsonl)、[`data/output/briefing.md`](data/output/briefing.md)。公开仓库 tip 仍只跟踪无正文的 [`data/output/metrics.public.json`](data/output/metrics.public.json)。

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
