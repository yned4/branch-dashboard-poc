"""画面3: 情報入口分析（指標 1-1〜1-6）"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data import load_data, yoy_ym
from utils.sidebar import render as render_sidebar
from utils import thresholds as thr
from utils import page_filters as pf
from utils.colors import SELF, PRIMARY, MID, LIGHT, PALE, OTHER, BLUES_5

st.set_page_config(page_title="情報入口分析", page_icon="📊", layout="wide")

filters = render_sidebar()
dfs = load_data()
cfg = thr.load()

branch_id = filters["branch_id"]
branch_name = filters["branch_name"]

st.title(f"📊 情報入口分析 — {branch_name}")
st.caption("**問い**: どの情報源が効率高いか／メンバー別に偏りはないか／経過月数で変化しているか")

pf_vals = pf.info_source(branch_id)
ym = pf_vals["selected_ym"]
start_ym = pf_vals["start_ym"]
end_ym = pf_vals["end_ym"]
selected_src = pf_vals["selected_src"]

st.markdown("---")

案件 = dfs["案件"]
契約 = dfs["契約"]
情報源 = dfs["情報源"]
社員 = dfs["社員"]

a_self = 案件[案件["登録時点支店ID"] == branch_id].copy()
a_month = a_self[a_self["年月"] == ym].copy()

a_self = a_self.merge(情報源, on="情報源ID", how="left")
a_month = a_month.merge(情報源, on="情報源ID", how="left")
a_self = a_self[a_self["情報源名"].isin(selected_src)]
a_month = a_month[a_month["情報源名"].isin(selected_src)]

# ── 1-1 情報源別 月間案件数 ──────────────────────────────────
st.subheader("1-1 情報源別 月間案件数")
all_ym_list = [str(p) for p in pd.period_range(start=pd.Period(start_ym, "M"), end=pd.Period(end_ym, "M"), freq="M")]
months_12 = all_ym_list
a_12 = a_self[a_self["年月"].isin(months_12)]
src_count = a_12.groupby("情報源名").size().div(12).round(1).reset_index()
src_count.columns = ["情報源名", "月間平均案件数"]
src_count = src_count.sort_values("月間平均案件数", ascending=True)

dep_warn = cfg["info_source_efficiency"]["dependency_max_pct"]["value"]

c1, c2 = st.columns(2)
with c1:
    fig = px.bar(src_count, x="月間平均案件数", y="情報源名", orientation="h",
                 color="月間平均案件数", color_continuous_scale=["#b8d9f7", "#1a3a6b"],
                 height=300)
    fig.update_coloraxes(showscale=False)
    fig.update_layout(yaxis_title="", xaxis_title="月間平均件数（過去12ヶ月）")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    if not a_month.empty:
        dep = a_month["情報源名"].value_counts(normalize=True).mul(100).reset_index()
        dep.columns = ["情報源名", "依存度(%)"]
        fig2 = px.pie(dep, names="情報源名", values="依存度(%)", height=300, hole=0.4,
                      color_discrete_sequence=BLUES_5,
                      title=f"情報源ポートフォリオ（{ym}）")
        fig2.update_traces(textposition="inside", textinfo="label+percent")
        st.plotly_chart(fig2, use_container_width=True)

top_src = a_month["情報源名"].value_counts(normalize=True).mul(100)
if not top_src.empty and top_src.iloc[0] > dep_warn:
    thr.next_action_box("warning",
        f"情報源「{top_src.index[0]}」の依存度が {top_src.iloc[0]:.1f}% と集中しています（閾値 {dep_warn}%）。"
        "情報源の多様化を指導してください。")

# ── 1-2 & 1-3 情報源別 成約率 & 平均粗利 ────────────────────
st.subheader("1-2/1-3 情報源別 成約率 & 平均粗利")

a_joined = a_self.merge(
    契約[["案件ID", "粗利_確定"]].groupby("案件ID")["粗利_確定"].sum().reset_index(),
    on="案件ID", how="left"
)
src_stats = a_joined.groupby("情報源名").agg(
    案件数=("案件ID", "count"),
    成約数=("成約フラグ", "sum"),
    平均粗利=("粗利_確定", "mean"),
).reset_index()
src_stats["成約率(%)"] = (src_stats["成約数"] / src_stats["案件数"] * 100).round(1)

cr_avg = src_stats["成約率(%)"].mean()
cr_warn_src = cfg["info_source_efficiency"]["closing_rate_vs_avg_pct"]["value"] / 100 * cr_avg

c3, c4 = st.columns(2)
with c3:
    s = src_stats.sort_values("成約率(%)", ascending=True)
    fig3 = px.bar(s, x="成約率(%)", y="情報源名", orientation="h",
                  color="成約率(%)", color_continuous_scale=["#b8d9f7", "#1a3a6b"],
                  height=300, title="情報源別 成約率")
    fig3.update_coloraxes(showscale=False)
    fig3.add_vline(x=cr_avg, line_dash="dash", line_color="#b0b8c8",
                   annotation_text=f"平均 {cr_avg:.1f}%", annotation_position="top right")
    fig3.add_vline(x=cr_warn_src, line_dash="dot", line_color="#e08c00",
                   annotation_text=f"閾値 {cr_warn_src:.1f}%", annotation_position="bottom right")
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    s2 = src_stats.sort_values("平均粗利", ascending=True)
    fig4 = px.bar(s2, x="平均粗利", y="情報源名", orientation="h",
                  color="平均粗利", color_continuous_scale=["#b8d9f7", "#1a3a6b"],
                  height=300, title="情報源別 平均粗利")
    fig4.update_coloraxes(showscale=False)
    gp_avg = src_stats["平均粗利"].mean()
    fig4.add_vline(x=gp_avg * 0.5, line_dash="dot", line_color="#e08c00",
                   annotation_text="閾値（平均50%）", annotation_position="bottom right")
    fig4.update_layout(xaxis_tickformat=",.0f")
    st.plotly_chart(fig4, use_container_width=True)

low_cr_src = src_stats[src_stats["成約率(%)"] < cr_warn_src]["情報源名"].tolist()
if low_cr_src:
    thr.next_action_box("warning",
        f"情報源 {', '.join(low_cr_src)} の成約率が自支店平均の50%未満です。追客工数の最適化を検討してください。")

# ── 1-4 入社経過月数別 情報源ポートフォリオ ──────────────────
st.subheader("1-4 入社経過月数別 情報源ポートフォリオ推移")

営業 = 社員[(社員["現在支店ID"] == branch_id) & (社員["職種"] == "営業")]
a_with_tenure = a_self.copy()
a_with_tenure = a_with_tenure.merge(
    営業[["社員ID", "入社年月"]].rename(columns={"社員ID": "登録担当社員ID"}),
    on="登録担当社員ID", how="left"
)
a_with_tenure["経過月数"] = ((a_with_tenure["登録日"] - a_with_tenure["入社年月"]).dt.days / 30).fillna(-1).astype(int)
a_with_tenure = a_with_tenure[a_with_tenure["経過月数"] >= 0]
a_with_tenure["経験年次"] = (a_with_tenure["経過月数"] // 12).astype(str) + "年目"

tenure_src = a_with_tenure.groupby(["経験年次", "情報源名"]).size().reset_index(name="案件数")
if not tenure_src.empty:
    fig5 = px.bar(tenure_src, x="経験年次", y="案件数", color="情報源名",
                  barmode="stack", height=320,
                  color_discrete_sequence=BLUES_5,
                  title="経験年次別 情報源構成")
    st.plotly_chart(fig5, use_container_width=True)

# ── 1-5 案件化〜初回契約 リードタイム ────────────────────────
st.subheader("1-5 案件化〜初回契約 リードタイム（情報源別）")

lt_src = a_self.dropna(subset=["リードタイム日数"]).groupby("情報源名")["リードタイム日数"].agg(
    平均日数="mean", 中央値="median"
).reset_index()

fig6 = go.Figure()
fig6.add_bar(x=lt_src["情報源名"], y=lt_src["平均日数"],
             name="平均", marker_color=PRIMARY)
fig6.add_bar(x=lt_src["情報源名"], y=lt_src["中央値"],
             name="中央値", marker_color=PALE)
fig6.add_hline(y=30, line_dash="dash", line_color="#e08c00",
               annotation_text="目安 30日（仮置き）")
fig6.update_layout(barmode="group", yaxis_title="日数", height=300)
st.plotly_chart(fig6, use_container_width=True)

# ── 1-6 情報源別 コスト調整後 ROI ───────────────────────────
st.subheader("1-6 情報源別 コスト調整後 ROI")

roi_data = a_joined.dropna(subset=["コスト係数"])
roi = roi_data.groupby("情報源名").apply(
    lambda g: (g["粗利_確定"].sum() / (len(g) * g["コスト係数"].iloc[0])) if g["コスト係数"].iloc[0] > 0 else 0
).reset_index()
roi.columns = ["情報源名", "ROI"]
roi = roi.sort_values("ROI", ascending=True)
roi_avg = roi["ROI"].mean()

fig7 = px.bar(roi, x="ROI", y="情報源名", orientation="h",
              color="ROI", color_continuous_scale=["#b8d9f7", "#1a3a6b"],
              height=280, title="情報源別 コスト調整後ROI（粗利 ÷ コスト係数×案件数）")
fig7.update_coloraxes(showscale=False)
fig7.add_vline(x=roi_avg, line_dash="dash", line_color="#b0b8c8",
               annotation_text="平均", annotation_position="top right")
fig7.update_layout(xaxis_tickformat=",.0f")
st.plotly_chart(fig7, use_container_width=True)
