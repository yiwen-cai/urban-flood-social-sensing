"""Streamlit offline dashboard — reads frozen outputs, no live API calls."""

import json
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

PROJECT_ROOT = Path(__file__).resolve().parent
METRICS_PATH = PROJECT_ROOT / "data" / "output" / "metrics.json"
EVIDENCE_PATH = PROJECT_ROOT / "data" / "output" / "evidence.jsonl"
BRIEFING_PATH = PROJECT_ROOT / "data" / "output" / "briefing.md"
EVAL_PATH = PROJECT_ROOT / "docs" / "project" / "evaluation.md"
IAA_PATH = PROJECT_ROOT / "docs" / "project" / "emotion_iaa.md"
DQ_PATH = PROJECT_ROOT / "docs" / "project" / "data_quality.md"
MANIFEST_PATH = PROJECT_ROOT / "data" / "frozen" / "manifest.json"
FIGURES_DIR = PROJECT_ROOT / "artifacts" / "figures"

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
    return BRIEFING_PATH.read_text(encoding="utf-8") if BRIEFING_PATH.is_file() else ""


@st.cache_data
def load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "数据范围与质量", "分类与评估", "代表性记录", "探索性情绪", "课程分析简报",
])

# ============================================================
# Tab 1: Data Scope & Quality
# ============================================================
with tab1:
    st.header("数据范围与质量")

    manifest = load_manifest()
    dq_text = load_data_quality()

    dq = metrics.get("data_quality", {})
    total = metrics["total_records"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("冻结记录数", total)
    col2.metric("事件", "kerala_floods_2018")
    col3.metric("数据来源", "HumAID test split")
    ref_missing = dq.get("missing_reference_label", 0)
    col4.metric("有参考标签", f"{total - ref_missing}/{total}")

    col_a, col_b, col_c = st.columns(3)
    missing_text = dq.get("missing_text_clean", 0)
    missing_pred = dq.get("missing_predicted_label", 0)
    dupes = dq.get("duplicate_ids", 0)
    col_a.metric("记录缺失率", f"{missing_text}/{total}" if missing_text else "0%",
                 help=f"text_clean 为空: {missing_text} 条")
    col_b.metric("模型预测缺失", f"{missing_pred}/{total}" if missing_pred else "0%",
                 help=f"predicted_label 为空: {missing_pred} 条")
    col_c.metric("重复 post_id", f"{dupes} 条" if dupes else "0 条",
                 help=f"唯一 post_id: {dq.get('unique_post_ids', total)}")

    st.markdown("#### 数据字段与处理说明")
    st.markdown("""
    | 字段 | 处理说明 |
    |------|----------|
    | `tweet_id` → `post_id` | 无损转为字符串 |
    | `tweet_text` → `text_clean` | 脱敏：账号→`[USER]`，号码→`[NUMBER]`，邮箱→`[EMAIL]` |
    | `class_label` → `_lab2.reference_label` | 官方参考标签，不进入模型输入 |
    | `time` / `location` | 数据无逐帖时间地点，固定为 `null` |
    """)

    st.markdown("#### 数据质量")
    with st.expander("数据质量报告（Lab 1 产出）"):
        if dq_text:
            st.markdown(dq_text[:2000])
        else:
            st.info("`docs/project/data_quality.md` 未找到，请先运行 Lab 1")

    status_dist = metrics.get("evidence_status_distribution", {})
    if status_dist:
        st.markdown("#### 证据类型分布")
        df = pd.DataFrame({
            "类型": [EVIDENCE_STATUS_CN.get(k, k) for k in status_dist],
            "数量": list(status_dist.values()),
        })
        fig = px.bar(df, x="类型", y="数量", text_auto=True, color="类型",
                     color_discrete_sequence=["#55A868", "#4C72B0", "#C44E52"])
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, width="stretch")


# ============================================================
# Tab 2: Classification & Evaluation
# ============================================================
with tab2:
    st.header("分类与评估")

    st.markdown("#### 模型对比")
    eval_text = load_evaluation()
    model_info = {}
    if eval_text:
        for line in eval_text.splitlines():
            if "Macro-F1" in line or "Weighted-F1" in line:
                key, _, val = line.replace("*", "").partition(":")
                key = key.strip()
                try:
                    model_info[key] = val.strip()
                except Exception:
                    pass

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("**TF-IDF + LR (baseline)**")
        if model_info:
            st.metric("Macro-F1", model_info.get("Macro-F1", "N/A"))
            st.metric("Weighted-F1", model_info.get("Weighted-F1", "N/A"))
        else:
            st.info("待运行 Lab 2 evaluate")
    with col_m2:
        st.markdown("**LLM Few-shot (DeepSeek)**")
        st.info("待 LLM 分类完成（需配置 .env 中的 DEEPSEEK_API_KEY）")

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

    st.markdown("#### 混淆矩阵（Lab 2 产出）")
    cm_path = FIGURES_DIR / "confusion_matrix_tfidf-lr-baseline-v1.png"
    if cm_path.is_file():
        st.image(str(cm_path), caption="Confusion Matrix (TF-IDF+LR baseline)")
    else:
        st.info("混淆矩阵未生成，请先运行 Lab 2 evaluate")

    st.divider()
    st.markdown("#### 关键类别召回率")
    critical = [
        ("requests_or_urgent_needs", "紧急需求"),
        ("displaced_people_and_evacuations", "流离失所与疏散"),
    ]
    for label_key, label_name in critical:
        stats = per_class.get(label_key, {})
        recall = stats.get("recall", 0)
        support = stats.get("reference_count", 0)
        st.metric(
            f"🆘 {label_name}",
            f"召回率 {recall:.3f}（{support} 条）",
            delta="⚠️ 低于 0.5" if recall < 0.5 else "✅ 高于 0.5",
            delta_color="off" if recall < 0.5 else "normal",
        )

    st.divider()
    st.caption("评估报告与 `docs/project/evaluation.md` 和 `data/output/metrics.json` 一致。")


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
    emo_dist = metrics.get("emotion_distribution", {})
    total_emo = sum(emo_dist.values())
    st.info(f"当前样本规模：{total} 条记录；其中含情绪标注：{total_emo} 条。情绪标签为课程成员人工标注的探索性补充。")

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
    st.markdown("#### 标注一致率（IAA）")

    iaa_text = load_iaa()
    if iaa_text:
        kappa_values = []
        for line in iaa_text.splitlines():
            for pair in ["A ↔ B", "B ↔ C", "A ↔ C"]:
                if pair in line and "κ" in line:
                    try:
                        parts = line.split("|")
                        kappa_values.append((pair, parts[-2].strip() if len(parts) > 2 else ""))
                    except Exception:
                        pass
        if kappa_values:
            for pair, val in kappa_values:
                try:
                    kv = float(val)
                    st.metric(f"Cohen's κ ({pair})", f"{kv:.2f}",
                              delta="✅ ≥ 0.6 通过" if kv >= 0.6 else "⚠️ < 0.6")
                except ValueError:
                    st.caption(f"{pair}: {val}")
        else:
            st.info("IAA 数据未找到。请运行 Lab 2 `annotate_seed iaa`")
        with st.expander("完整 IAA 报告"):
            st.markdown(iaa_text)
    else:
        st.caption(
            "一致率为两人重叠标注时的一致性度量（Cohen's Kappa）。"
            "当前 IAA 报告未生成，待 Lab 2 产出 `docs/project/emotion_iaa.md` 后自动展示。"
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


# ============================================================
# Tab 5: Briefing
# ============================================================
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

    st.divider()
    st.caption(
        "本简报用于社会计算与生成决策智能课程技术演示。"
        "所有数字由程序从冻结数据中计算得出，不可外推为灾区总体状况或权威灾情评估。"
        "不发布预警、救援建议或权威灾情结论。"
    )
