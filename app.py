"""Streamlit offline dashboard — reads frozen outputs, no live API calls."""

import json
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parent
METRICS_PATH = PROJECT_ROOT / "data" / "output" / "metrics.json"
EVIDENCE_PATH = PROJECT_ROOT / "data" / "output" / "evidence.jsonl"
BRIEFING_PATH = PROJECT_ROOT / "data" / "output" / "briefing.md"

LABEL_NAMES_CN = {
    "caution_and_advice": "警告与建议",
    "displaced_people_and_evacuations": "流离失所与疏散",
    "infrastructure_and_utility_damage": "基础设施损坏",
    "injured_or_dead_people": "伤亡人员",
    "not_humanitarian": "非人道信息",
    "other_relevant_information": "其他相关信息",
    "requests_or_urgent_needs": "紧急需求",
    "rescue_volunteering_or_donation_effort": "救援与捐赠",
    "sympathy_and_support": "同情与支持",
}
EMOTION_NAMES_CN = {
    "fear_or_anxiety": "恐慌/焦虑",
    "anger": "愤怒",
    "sadness": "悲伤",
    "positive_support": "积极支持",
    "neutral_or_unclear": "中性/无法判断",
}
EVIDENCE_STATUS_CN = {
    "dataset_record": "📄 数据集记录",
    "human_labeled": "👤 人工标签",
    "model_prediction": "🤖 模型预测",
}
LABEL_ORDER = list(LABEL_NAMES_CN)
EMOTION_ORDER = list(EMOTION_NAMES_CN)


st.set_page_config(page_title="Kerala Flood Social Sensing", layout="wide")
st.title("Kerala 2018 洪水社交媒体分析看板")
st.caption("课程技术演示 — 不构成实时监测或权威灾情结论")


@st.cache_data
def load_metrics():
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


@st.cache_data
def load_evidence():
    lines = EVIDENCE_PATH.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


@st.cache_data
def load_briefing():
    return BRIEFING_PATH.read_text(encoding="utf-8")


if not METRICS_PATH.is_file():
    st.error("metrics.json not found. Run `python -m src.lab3_decision.build_evidence` first.")
    st.stop()

metrics = load_metrics()
evidence = load_evidence()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "数据范围与质量", "分类与评估", "代表性记录", "探索性情绪", "课程分析简报",
])

# ============================================================
# Tab 1: Data Scope & Quality
# ============================================================
with tab1:
    st.header("数据范围与质量")

    col1, col2, col3 = st.columns(3)
    col1.metric("冻结记录数", metrics["total_records"])
    col2.metric("事件", "kerala_floods_2018")
    col3.metric("数据来源", "HumAID test split")

    st.markdown("#### 数据字段")
    st.markdown("""
    | 字段 | 处理说明 |
    |------|----------|
    | `tweet_id` → `post_id` | 无损转为字符串 |
    | `tweet_text` → `text_clean` | 脱敏：账号→`[USER]`，号码→`[NUMBER]`，邮箱→`[EMAIL]` |
    | `class_label` → `_lab2.reference_label` | 官方参考标签，不进入模型输入 |
    | `time` / `location` | 数据无逐帖时间地点，固定为 `null` |
    """)

    status_dist = metrics.get("evidence_status_distribution", {})
    if status_dist:
        st.markdown("#### 证据类型分布")
        df = pd.DataFrame({
            "类型": [EVIDENCE_STATUS_CN.get(k, k) for k in status_dist],
            "数量": list(status_dist.values()),
        })
        fig = px.bar(df, x="类型", y="数量", text_auto=True, color="类型",
                     color_discrete_sequence=["#55A868", "#4C72B0", "#C44E52"])
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, width="stretch")


# ============================================================
# Tab 2: Classification & Evaluation
# ============================================================
with tab2:
    st.header("分类与评估")

    st.markdown("#### 九类人道信息分布")
    cat_dist = metrics["category_distribution"]
    cat_df = pd.DataFrame({
        "类别": [LABEL_NAMES_CN.get(k, k) for k in cat_dist],
        "数量": [cat_dist[k] for k in cat_dist],
    }).sort_values("数量")
    fig = px.bar(cat_df, x="数量", y="类别", orientation="h", text_auto=True,
                 color="类别", color_discrete_sequence=px.colors.qualitative.Set3)
    fig.update_layout(showlegend=False, height=400, yaxis_title="")
    st.plotly_chart(fig, width="stretch")

    st.markdown("#### 逐类指标")
    per_class = metrics["per_class_stats"]
    table_data = []
    for label in LABEL_ORDER:
        stats = per_class.get(label, {})
        table_data.append({
            "类别": LABEL_NAMES_CN.get(label, label),
            "参考数": stats.get("reference_count", 0),
            "预测数": stats.get("predicted_count", 0),
            "正确": stats.get("correct", 0),
            "精确率": f"{stats.get('precision', 0):.3f}",
            "召回率": f"{stats.get('recall', 0):.3f}",
            "F1": f"{stats.get('f1', 0):.3f}",
        })
    st.dataframe(pd.DataFrame(table_data), width="stretch")

    st.markdown("#### 混淆矩阵")
    # Build confusion matrix from evidence records
    ref_labels = LABEL_ORDER
    pred_labels = LABEL_ORDER
    n = len(ref_labels)
    ref_idx = {l: i for i, l in enumerate(ref_labels)}
    matrix = [[0] * n for _ in range(n)]
    for rec in evidence:
        ref = rec.get("reference_label", "")
        pred = rec.get("predicted_label", "")
        if ref in ref_idx and pred in ref_idx:
            matrix[ref_idx[ref]][ref_idx[pred]] += 1

    heatmap = go.Heatmap(
        z=matrix,
        x=[LABEL_NAMES_CN[l] for l in pred_labels],
        y=[LABEL_NAMES_CN[l] for l in ref_labels],
        colorscale="Blues", text=matrix, texttemplate="%{text}",
        textfont={"color": "white"},
        hovertemplate="参考: %{y}<br>预测: %{x}<br>数量: %{z}<extra></extra>",
    )
    fig_cm = go.Figure(heatmap)
    fig_cm.update_layout(height=500, xaxis_title="预测", yaxis_title="参考",
                         xaxis_tickangle=-45)
    fig_cm.update_traces(showscale=False)
    st.plotly_chart(fig_cm, width="stretch")

    st.markdown("#### Precision / Recall / F1")
    precs = [per_class.get(l, {}).get("precision", 0) for l in LABEL_ORDER]
    recs = [per_class.get(l, {}).get("recall", 0) for l in LABEL_ORDER]
    f1s = [per_class.get(l, {}).get("f1", 0) for l in LABEL_ORDER]
    names = [LABEL_NAMES_CN[l] for l in LABEL_ORDER]
    fig_pr = go.Figure([
        go.Bar(name="Precision", x=names, y=precs, marker_color="#4C72B0"),
        go.Bar(name="Recall", x=names, y=recs, marker_color="#55A868"),
        go.Bar(name="F1", x=names, y=f1s, marker_color="#C44E52"),
    ])
    fig_pr.update_layout(height=400, yaxis_range=[0, 1.1], xaxis_tickangle=-45)
    st.plotly_chart(fig_pr, width="stretch")


# ============================================================
# Tab 3: Representative Records
# ============================================================
with tab3:
    st.header("代表性脱敏记录")
    st.caption("各类别中置信度最高的代表记录。原始联系方式、姓名、账号已脱敏。")

    label_filter = st.selectbox(
        "按类别筛选", ["全部"] + [LABEL_NAMES_CN[l] for l in cat_dist]
    )

    for rec in evidence:
        if rec.get("selection_reason", "").startswith("urgent"):
            continue
        label = LABEL_NAMES_CN.get(rec["predicted_label"], rec["predicted_label"])
        if label_filter != "全部" and label != label_filter:
            continue

        with st.expander(f"{label} · {rec['text_clean'][:80]}..."):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("**原文摘要**")
                st.text(rec["text_clean"])
                st.markdown(f"**来源** `{rec['source_ref']}`")
            with col2:
                st.metric("置信度", f"{rec.get('confidence', 0):.3f}")
                status_display = EVIDENCE_STATUS_CN.get(
                    rec.get("evidence_status", ""), rec.get("evidence_status", ""))
                st.caption(f"证据状态: {status_display}")
                emo = rec.get("exploratory_emotion")
                if emo:
                    st.caption(f"情绪: {EMOTION_NAMES_CN.get(emo, emo)}")


# ============================================================
# Tab 4: Exploratory Emotion
# ============================================================
with tab4:
    st.header("探索性情绪分析")
    st.caption("小样本探索性实验，不声称为官方 HumAID 标签，不推广为全体事件结论。")

    total = metrics["total_records"]
    st.info(f"当前样本规模：{total} 条记录。情绪标签为课程成员人工标注的探索性补充。")

    emo_dist = metrics.get("emotion_distribution", {})
    total_emo = sum(emo_dist.values())
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 情绪分布")

        if total_emo == 0:
            st.info("暂无情绪标注数据。情绪标签为探索性补充，需 Lab 2 完成 `annotate_seed.py` 产出后方可展示。")
        else:
            emo_df = pd.DataFrame({
                "情绪": [EMOTION_NAMES_CN.get(k, k) for k in EMOTION_ORDER],
                "数量": [emo_dist.get(k, 0) for k in EMOTION_ORDER],
            })
            fig = px.bar(emo_df, x="情绪", y="数量", text_auto=True, color="情绪",
                         color_discrete_sequence=["#FF6B6B", "#FF0000", "#4ECDC4", "#45B7D1", "#96CEB4"])
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, width="stretch")

            # Pie chart
            pie_df = emo_df[emo_df["数量"] > 0]
            fig_pie = px.pie(pie_df, values="数量", names="情绪",
                             color_discrete_sequence=["#FF6B6B", "#FF0000", "#4ECDC4", "#45B7D1", "#96CEB4"])
            fig_pie.update_traces(textinfo="percent+value")
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, width="stretch")

            if emo_dist:
                dominant = max(emo_dist, key=emo_dist.get)
                st.markdown(
                    f"**主要情绪**：{EMOTION_NAMES_CN.get(dominant, dominant)}"
                    f"（{emo_dist[dominant]} 条，{emo_dist[dominant]/total*100:.1f}%）"
                )

    with col2:
        st.markdown("#### 情绪 × 类别交叉")
        cross: dict[str, dict[str, int]] = {}
        for rec in evidence:
            cat = rec.get("predicted_label", "")
            emo = rec.get("exploratory_emotion") or "无"
            cross.setdefault(cat, {}).setdefault(emo, 0)
            cross[cat][emo] += 1

        cross_table = []
        for cat in LABEL_ORDER:
            for emo in EMOTION_ORDER:
                cross_table.append({
                    "类别": LABEL_NAMES_CN.get(cat, cat),
                    "情绪": EMOTION_NAMES_CN.get(emo, emo),
                    "数量": cross.get(cat, {}).get(emo, 0),
                })
        cross_df = pd.DataFrame(cross_table)
        if not cross_df.empty:
            st.dataframe(
                cross_df.pivot(index="类别", columns="情绪", values="数量").fillna(0).astype(int),
                width="stretch",
            )

    st.divider()
    st.markdown("#### 标注一致率")
    st.caption(
        "一致率为两人重叠标注时的一致性度量（Cohen's Kappa 或百分比一致率）。"
        "当前 fixture 模式下无可用的双人标注数据，待 Lab 2 产出真实情绪样本后填入。"
    )

    st.divider()
    st.markdown("#### 代表性差异与局限性")
    st.markdown("""
    - **样本偏差**：情绪标签仅覆盖小样本（方案建议控制在 ~100 条），不代表全体 1,582 条测试记录
    - **文化差异**：英文社交媒体上的情绪表达方式和文化背景与中文语境不同
    - **灾害特有情绪**：恐慌/焦虑和积极支持在灾害场景下比通用场景（如商品评论）更突出；
      通用场景中常见的"满意/不满意"二元框架不适合描述灾害信息中的情绪
    - **与主任务独立**：情绪分析为探索性补充，与 9 类人道信息分类分开存储、分开评估、分开报告
    """)

    st.caption(
        "本部分情绪标签为课程成员人工标注的小样本探索性实验，不声称为官方 HumAID 标签。"
        "样本规模和标注方式决定了发现无可推广为总体事件情绪结论。"
    )


# ============================================================
# Tab 5: Briefing
# ============================================================
with tab5:
    st.header("课程分析简报")

    if BRIEFING_PATH.is_file():
        st.markdown(load_briefing())
    else:
        st.warning(
            "简报文件未生成。运行 "
            "`python -m src.lab3_decision.build_evidence && python -m src.lab3_decision.generate_briefing`"
        )

    st.divider()
    st.caption(
        "本简报用于社会计算与生成决策智能课程技术演示。"
        "所有数字由程序从冻结数据中计算得出，不可外推为灾区总体状况或权威灾情评估。"
        "不发布预警、救援建议或权威灾情结论。"
    )
