# 简报事实断言审计

> 审计对象：`data/output/briefing.md`（由 `generate_briefing.py` 从 D07 metrics/evidence 动态生成）  
> 审计基准：`schemas/metrics.schema.json` v2.0.0 + `schemas/evidence.schema.json` v1.0.0  
> 审计时间：2026-07-15

## 结论

- Fixture 离线流水线生成的简报数字与同次 `metrics.json` / `evidence.jsonl` 一致，可重算。
- 真实公开聚合见 `data/output/metrics.public.json`（1,582 唯一帖子，无 `text_clean`）。
- 真实来源 evidence 不复制正文；合成 fixture evidence 才包含 `text_clean`。
- 情绪占比分母为 `records_with_emotion`（已标注子集），不是全部唯一帖子。
- 紧急需求 evidence 通过 `selection_reason = urgent needs: all records included` 进入简报。

## 抽查清单

| 断言 | 验证方式 | 结果 |
|------|----------|------|
| 唯一帖子数来自 metrics | `metrics.unique_posts` | ✅ |
| 模型指标来自 per_model | `metrics.per_model[model].accuracy/coverage/F1` | ✅ |
| 混淆矩阵来自全量指标 | `per_model.*.confusion_matrix`，非 evidence 抽样 | ✅ |
| 真实模式无正文 | `source=humaid_events ⇒ text_clean=null` | ✅ |
| 历史残余风险已记录 | `DATA_GATE.md` §8、`.env.example` | ✅ |

重新审计命令：

```bash
bash run_pipeline.sh --fixture --offline
# 然后对照 data/output/briefing.md 与 data/output/metrics.json
```
