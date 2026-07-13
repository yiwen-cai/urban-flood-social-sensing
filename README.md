# Urban Flood Social Sensing

面向社会计算课程实践的城市暴雨社交媒体信号分析项目。项目以冻结、脱敏的历史事件数据为输入，完成数据清洗、公众信息功能与情绪分类、结构化聚合，以及可追溯的课程分析简报和离线看板。

> 当前状态：总体方案与三人接口契约已完成，工程实现尚未开始。

## 项目边界

- 历史事件复盘型课程技术演示，不是实时灾情监测系统；
- 不发布预警、救援建议或权威灾情结论；
- 主流程只使用一份冻结文本语料，CrowdFlood 等资料仅作独立参照；
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
- [候选方向综述](docs/research/候选方向综述.md)
- [协作规范](CONTRIBUTING.md)

## 计划中的统一验证入口

工程实现完成后，每次正式交接应通过：

```bash
python -m pytest tests/test_schema.py
bash run_pipeline.sh --fixture --offline
```

上述脚本目前属于实施契约，尚未实现。
