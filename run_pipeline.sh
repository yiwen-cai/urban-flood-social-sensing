#!/bin/bash
# 一键流水线脚本：Lab 1 → Lab 2 → Lab 3
# 用法：bash run_pipeline.sh

set -e
echo "========================================="
echo "  城市暴雨内涝社会感知流水线"
echo "========================================="

# 检查环境
if [ -z "$DEEPSEEK_API_KEY" ] && [ -z "$QWEN_API_KEY" ]; then
    echo "[WARNING] 未设置 LLM API Key，Lab 2/3 可能无法运行"
    echo "  export DEEPSEEK_API_KEY='sk-xxx'"
fi

# Lab 1: 数据采集与清洗
echo ""
echo "[1/3] Lab 1 — 数据采集与清洗..."
cd src/lab1_collection
python main.py
cd ../..
echo "[OK] Lab 1 完成 → data/processed/posts_clean.jsonl"

# Lab 2: 情感与观点分析
echo ""
echo "[2/3] Lab 2 — 情感与观点分析..."
cd src/lab2_analysis
python main.py
cd ../..
echo "[OK] Lab 2 完成 → data/analyzed/posts_labeled.jsonl"

# Lab 3: 生成式决策支持
echo ""
echo "[3/3] Lab 3 — 生成式决策支持..."
cd src/lab3_decision
python main.py
cd ../..
echo "[OK] Lab 3 完成 → data/output/briefing.md"

echo ""
echo "========================================="
echo "  流水线完成！"
echo "  - 帖子数据: data/processed/posts_clean.jsonl"
echo "  - 分析数据: data/analyzed/posts_labeled.jsonl"
echo "  - 态势简报: data/output/briefing.md"
echo ""
echo "  启动看板: streamlit run app.py"
echo "========================================="
