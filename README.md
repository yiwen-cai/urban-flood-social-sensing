# Urban Flood Social Sensing

面向社会计算课程实践的 Kerala 2018 洪水社交媒体人道信息分析项目。项目以 HumAID 单事件冻结语料为输入，完成数据治理、传统 baseline 与 LLM 的 9 类人道信息分类对比、探索性情绪分析、结构化聚合，以及可追溯的中文课程简报和离线看板。

> 当前状态：总体方案与三人接口契约已完成；数据清单、下载校验器、JSON Schema 和 20 条合成契约样例已经落地，其余流水线模块尚待实现。

## 项目边界

- 历史事件复盘型课程技术演示，不是实时灾情监测系统；
- 不发布预警、救援建议或权威灾情结论；
- 主流程固定使用 HumAID `kerala_floods_2018` 官方 test split 的 1,582 条记录；
- 数据没有逐帖时间和地点，不生成地图、时间趋势或时空推断；
- 原始社交媒体数据、个人信息和 API 密钥不进入仓库；
- 核心演示必须支持断网运行。

## 三个模块

| 模块 | 负责人 | 输入 | 输出 |
|------|--------|------|------|
| Lab 1 数据采集与清洗 | 成员 A | 冻结原始数据 | `posts_clean.jsonl`、数据质量报告 |
| Lab 2 情感与观点分析 | 成员 B | Lab 1 清洗结果 | `posts_labeled.jsonl`、评估报告 |
| Lab 3 生成式信息支持 | 成员 C | Lab 2 标签结果 | 课程分析简报、离线看板与演示包 |

详细数据契约、交接节点和验收标准见[项目实施方案](docs/project/实施方案.md)。

## 仓库结构

```text
.
├── config/              # Taxonomy、标签与简报模板
├── schemas/             # JSON Schema 数据契约
├── src/                 # Lab 1–3 与共享工具
├── tests/fixtures/      # 可提交的脱敏契约样例
├── data/                # 本地数据和生成产物，默认不提交
├── artifacts/           # 静态图、运行记录与演示材料
├── slides/              # 最终汇报材料
└── docs/
    ├── course/          # 原始课程任务书
    ├── project/         # 当前有效实施方案
    └── research/        # 选题调研与候选方向
```

## 重要文档

- [课程实践任务书](docs/course/课程实践任务书.md)
- [项目实施方案](docs/project/实施方案.md)
- [数据准入与合规边界](docs/project/DATA_GATE.md)
- [候选方向综述](docs/research/候选方向综述.md)
- [协作规范](CONTRIBUTING.md)

## 当前可执行步骤

安装当前最小依赖：

```bash
python -m pip install -r requirements.txt
```

成员 A、B 可各自下载并校验冻结数据；原始文本不会进入 Git：

```bash
python -m src.lab1_collection.fetch_data
python -m src.lab1_collection.fetch_data --verify-only
```

所有成员都可以只使用合成样例验证接口契约：

```bash
python -m pytest tests/test_schema.py
```

完整流水线实现后，正式交接还应通过：

```bash
bash run_pipeline.sh --fixture --offline
```

`run_pipeline.sh` 目前仍是实施契约，尚未实现。DeepSeek API 冒烟测试只允许使用 20 条合成样例；真实 HumAID 文本在团队确认数据条款和第三方处理边界前不得上传。
