# 演示机器安装与断网检查

> 交付物：D01/D02（DATA_GATE.md 第7节 gate checklist）

## 1. 本次检查范围（完整版，2026-07-15）

覆盖：可移植依赖安装、全部单元/契约测试、`run_pipeline.sh --fixture --offline`（Lab 1 fixture → 双模型模拟预测 → evaluation → D07 → briefing → figures → dashboard 数据加载）、公开聚合指标隐私边界。

## 2. 检查记录

| 项 | 结果 |
|---|---|
| 检查日期 | 2026-07-15 |
| Python 版本 | 3.9+ / CI 3.11 |
| 环境 | `python3 -m venv` + `pip install -r requirements.lock` |
| `requirements.lock` | 已重生成为可移植锁文件，无本机 `file://` 路径；含 Streamlit / Plotly / Jinja2 / OpenAI / scikit-learn |
| `pytest tests/` | 通过（HumAID raw 缺失时相关用例 skip） |
| `run_pipeline.sh --fixture --offline` | 通过：无 raw、无 API key、无网络 |
| 公开指标 | `data/output/metrics.public.json` 含 1,582 唯一帖子聚合结果，无 `text_clean` |
| 看板冒烟 | pipeline 末尾加载 metrics/evidence/briefing 并校验 schema |
| 历史风险 | tip 已清理；历史未重写（DATA_GATE §8） |

## 3. 复现命令

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock
bash run_pipeline.sh --fixture --offline
streamlit run app.py
```

## 4. 结论

课程发布级离线验收通过。真实 DeepSeek 重跑不是发布 blocker；本地可用 `--from-legacy` 复用既有预测。
