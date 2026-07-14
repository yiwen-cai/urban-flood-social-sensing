# 演示机器安装与断网检查

> 交付物：D01/D02（DATA_GATE.md 第7节 gate checklist 最后一项）

## 1. 本次检查范围（轻量版）

本次检查在 Lab 1 骨架完成、Lab 2/3 尚未开始时执行，覆盖当前已冻结的部分：依赖安装、`run_pipeline.sh --fixture --offline`、`clean.py`。不覆盖 Lab 2（DeepSeek API 调用）和 Lab 3（Streamlit 看板）的依赖，这两部分完成后需要补一次完整版检查（见第3节）。

## 2. 检查记录

| 项 | 结果 |
|---|---|
| 检查日期 | 2026-07-14 |
| Python 版本 | 3.12.4 |
| 环境 | 全新 `python3 -m venv`（非项目现有 `.venv`），零手动干预 |
| 依赖安装命令 | `pip install -r requirements.txt` |
| 依赖安装结果 | 成功，无报错 |
| `run_pipeline.sh --fixture --offline` | 通过，耗时约 0.25 秒，退出码 0 |
| `src/lab1_collection/clean.py --split test` | 通过，1,582 条全部清洗成功 |
| 断网模拟 | `--fixture --offline` 模式不触发任何网络请求（不调用 `fetch_data.py` 的下载逻辑，仅 `--verify-only` 路径读本地文件） |

## 3. 已知缺口（Lab 2/3 完成后需重新检查）

- 当前 `requirements.txt` 仅含 `jsonschema`、`pytest`，尚未包含 Lab 2 所需的 DeepSeek SDK/HTTP 客户端、Lab 3 所需的 `streamlit`、`pandas`、`jinja2` 等依赖；这些依赖到位后需重新执行本检查的完整版本。
- 本次检查未测试真正断开网络连接（仅验证离线路径不发起请求），建议 Day 3/4 完整版检查时在物理断网环境下实测。
- `config/labeling_schema.yaml`、`config/taxonomy.yaml` 目前不被任何 Python 代码读取（无 `pyyaml` 依赖需求）；一旦 Lab 2 开始解析这两个文件，需将 `pyyaml` 加入 `requirements.txt` 并重新走一遍本检查。

## 4. 结论

DATA_GATE.md 第7节最后一项检查通过（轻量版，范围见第1节）。不阻塞 Lab 1/2 继续开发；Day 3/4 功能冻结前需补充完整版检查，覆盖全部依赖和真实断网场景。
