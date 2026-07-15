"""Streamlit offline dashboard — reads D07 outputs, no live API calls."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
METRICS_PATH = PROJECT_ROOT / "data" / "output" / "metrics.json"
EVIDENCE_PATH = PROJECT_ROOT / "data" / "output" / "evidence.jsonl"
BRIEFING_PATH = PROJECT_ROOT / "data" / "output" / "briefing.md"
EVAL_PATH = PROJECT_ROOT / "docs" / "project" / "evaluation.md"
IAA_PATH = PROJECT_ROOT / "docs" / "project" / "emotion_iaa.md"
DQ_PATH = PROJECT_ROOT / "docs" / "project" / "data_quality.md"
MANIFEST_PATH = PROJECT_ROOT / "data" / "frozen" / "manifest.json"

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
    if not EVIDENCE_PATH.is_file():
        return []
    lines = EVIDENCE_PATH.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


@st.cache_data
def load_briefing():
    return BRIEFING_PATH.read_text(encoding="utf-8") if BRIEFING_PATH.is_file() else ""


@st.cache_data
def load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.is_file() else {}


@st.cache_data
def load_data_quality():
    return DQ_PATH.read_text(encoding="utf-8") if DQ_PATH.is_file() else ""


@st.cache_data
def load_evaluation():
    return EVAL_PATH.read_text(encoding="utf-8") if EVAL_PATH.is_file() else ""


@st.cache_data
def load_iaa():
    return IAA_PATH.read_text(encoding="utf-8") if IAA_PATH.is_file() else ""


if not METRICS_PATH.is_file():
    st.error("metrics.json not found. Run `python -m src.lab3_decision.build_evidence` first.")
    st.stop()

metrics = load_metrics()
evidence = load_evidence()
model_versions = metrics.get("model_versions") or []
selected_model = st.sidebar.selectbox(
    "模型版本",
    options=model_versions or ["（无模型）"],
    index=0,
)
if selected_model == "（无模型）":
    selected_model = None
model_metrics = (metrics.get("per_model") or {}).get(selected_model or "", {})
filtered_evidence = [
    row
    for row in evidence
    if selected_model is None or row.get("model_version") == selected_model
]

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["数据范围与质量", "分类与评估", "代表性记录", "探索性情绪", "课程分析简报"]
)

with tab1:
    st.header("数据范围与质量")
    dq_text = load_data_quality()
    unique_posts = metrics.get("unique_posts", 0)
    with_ref = metrics.get("records_with_reference_label", 0)
    with_emotion = metrics.get("records_with_emotion", 0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("唯一帖子数", unique_posts)
    col2.metric("事件", "kerala_floods_2018")
    col3.metric("有参考标签", f"{with_ref}/{unique_posts}")
    col4.metric("有情绪标注", f"{with_emotion}/{unique_posts}")

    if selected_model and model_metrics:
        c1, c2, c3 = st.columns(3)
        c1.metric("覆盖率", f"{model_metrics.get('coverage', 0):.1%}")
        c2.metric("准确率（全量分母）", f"{model_metrics.get('accuracy', 0):.1%}")
        c3.metric("预测失败", model_metrics.get("n_errors", 0))

    st.markdown("#### 数据质量")
    with st.expander("数据质量报告（Lab 1 产出）"):
        st.markdown(dq_text[:2000] if dq_text else "`docs/project/data_quality.md` 未找到")

with tab2:
    st.header("分类与评估")
    st.caption(f"当前模型：`{selected_model or '（无）'}` — 指标来自全量 metrics，不是 evidence 抽样。")

    if model_versions:
        cols = st.columns(min(len(model_versions), 3))
        for col, version in zip(cols, model_versions):
            mm = metrics["per_model"][version]
            with col:
                st.markdown(f"**{version}**")
                st.metric("Coverage", f"{mm.get('coverage', 0):.3f}")
                st.metric("Accuracy (full)", f"{mm.get('accuracy', 0):.3f}")
                st.metric("Macro-F1", f"{mm.get('macro_f1', 0):.3f}")

    ref_dist = metrics.get("reference_label_distribution") or {}
    st.markdown("#### 九类人道信息分布（唯一帖子）")
    cat_df = pd.DataFrame(
        {
            "类别": [LABEL_NAMES_CN.get(k, k) for k in LABEL_ORDER],
            "数量": [ref_dist.get(k, 0) for k in LABEL_ORDER],
        }
    ).sort_values("数量")
    fig = px.bar(
        cat_df,
        x="数量",
        y="类别",
        orientation="h",
        text_auto=True,
        color="类别",
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig.update_layout(showlegend=False, height=400, yaxis_title="")
    st.plotly_chart(fig, width="stretch")

    st.markdown("#### 逐类指标")
    per_class = model_metrics.get("per_class") or {}
    table_data = []
    for label in LABEL_ORDER:
        stats = per_class.get(label, {})
        table_data.append(
            {
                "类别": LABEL_NAMES_CN.get(label, label),
                "支持": stats.get("support", ref_dist.get(label, 0)),
                "预测数": stats.get("predicted_count", 0),
                "正确": stats.get("correct", 0),
                "精确率": f"{stats.get('precision', 0):.3f}",
                "召回率": f"{stats.get('recall', 0):.3f}",
                "F1": f"{stats.get('f1', 0):.3f}",
            }
        )
    st.dataframe(pd.DataFrame(table_data), width="stretch")

    st.markdown("#### 混淆矩阵（全量指标）")
    cm = model_metrics.get("confusion_matrix") or {}
    matrix = [[cm.get(ref, {}).get(pred, 0) for pred in LABEL_ORDER] for ref in LABEL_ORDER]
    heatmap = go.Heatmap(
        z=matrix,
        x=[LABEL_NAMES_CN[l] for l in LABEL_ORDER],
        y=[LABEL_NAMES_CN[l] for l in LABEL_ORDER],
        colorscale="Blues",
        text=matrix,
        texttemplate="%{text}",
        hovertemplate="参考: %{y}<br>预测: %{x}<br>数量: %{z}<extra></extra>",
    )
    fig_cm = go.Figure(heatmap)
    fig_cm.update_layout(height=520, xaxis_title="预测", yaxis_title="参考", xaxis_tickangle=-45)
    st.plotly_chart(fig_cm, width="stretch")

    st.markdown("#### 关键类别召回率")
    for label_key, label_name in (
        ("rescue_volunteering_or_donation_effort", "救援与捐赠"),
        ("requests_or_urgent_needs", "紧急需求"),
    ):
        stats = per_class.get(label_key, {})
        recall = stats.get("recall", 0)
        support = stats.get("support", 0)
        st.metric(
            f"🆘 {label_name}",
            f"召回率 {recall:.3f}（支持 {support}）",
            delta="⚠️ 低于 0.5" if recall < 0.5 else "✅ 高于 0.5",
            delta_color="off" if recall < 0.5 else "normal",
        )

with tab3:
    st.header("代表性脱敏记录")
    st.caption("真实来源模式不展示正文；合成 fixture 可展示脱敏摘要。紧急需求记录已全量纳入。")
    label_filter = st.selectbox(
        "按类别筛选",
        ["全部"] + [LABEL_NAMES_CN[l] for l in LABEL_ORDER],
    )
    for rec in filtered_evidence:
        label = LABEL_NAMES_CN.get(rec.get("predicted_label"), rec.get("predicted_label"))
        if label_filter != "全部" and label != label_filter:
            continue
        title_body = rec.get("text_clean") or rec.get("post_id", "")
        with st.expander(f"{label} · {str(title_body)[:80]}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**post_id** `{rec.get('post_id')}`")
                st.markdown(f"**来源** `{rec.get('source_ref')}`")
                st.markdown(f"**选择理由** {rec.get('selection_reason')}")
                if rec.get("text_clean"):
                    st.markdown("**原文摘要**")
                    st.text(rec["text_clean"])
                else:
                    st.info("真实数据模式：不展示正文")
            with col2:
                st.metric("置信度", f"{rec.get('confidence') or 0:.3f}")
                st.caption(f"模型: {rec.get('model_version')}")
                emo = rec.get("exploratory_emotion")
                if emo:
                    st.caption(f"情绪: {EMOTION_NAMES_CN.get(emo, emo)}")

with tab4:
    st.header("探索性情绪分析")
    emo_dist = metrics.get("emotion_distribution") or {}
    total_emo = metrics.get("records_with_emotion") or sum(emo_dist.values())
    unique_posts = metrics.get("unique_posts", 0)
    st.info(
        f"情绪分母使用已标注子集：{total_emo} / {unique_posts}。"
        "情绪标签为课程成员人工标注的探索性补充。"
    )
    if total_emo == 0:
        st.info("暂无情绪标注数据。")
    else:
        emo_df = pd.DataFrame(
            {
                "情绪": [EMOTION_NAMES_CN.get(k, k) for k in EMOTION_ORDER],
                "数量": [emo_dist.get(k, 0) for k in EMOTION_ORDER],
            }
        )
        fig = px.bar(
            emo_df,
            x="情绪",
            y="数量",
            text_auto=True,
            color="情绪",
            color_discrete_sequence=["#FF6B6B", "#FF0000", "#4ECDC4", "#45B7D1", "#96CEB4"],
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, width="stretch")
        dominant = max(emo_dist, key=emo_dist.get)
        st.markdown(
            f"**主要情绪**：{EMOTION_NAMES_CN.get(dominant, dominant)}"
            f"（{emo_dist[dominant]} / {total_emo}，{emo_dist[dominant] / total_emo * 100:.1f}%）"
        )

    iaa_text = load_iaa()
    st.markdown("#### 标注一致率（IAA）")
    if iaa_text:
        with st.expander("完整 IAA 报告", expanded=True):
            st.markdown(iaa_text)
    else:
        st.caption("当前 IAA 报告未生成。")

with tab5:
    st.header("课程分析简报")
    briefing = load_briefing()
    if briefing:
        st.markdown(briefing)
    else:
        st.warning(
            "简报文件未生成。运行 "
            "`python -m src.lab3_decision.build_evidence && python -m src.lab3_decision.generate_briefing`"
        )
    st.caption("本简报用于课程技术演示；不发布预警、救援建议或权威灾情结论。")
