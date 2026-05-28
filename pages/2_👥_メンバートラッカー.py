"""画面2: メンバー個別トラッカー"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data import load_data, yoy_ym, headcount_coefficient
from utils.sidebar import render as render_sidebar
from utils import thresholds as thr
from utils import page_filters as pf
from utils.colors import SELF, PRIMARY, MID, LIGHT, PALE, OTHER, BLUES_5

st.set_page_config(page_title="メンバートラッカー", page_icon="👥", layout="wide")

filters = render_sidebar()
dfs = load_data()
cfg = thr.load()

branch_id = filters["branch_id"]
branch_name = filters["branch_name"]

st.title(f"👥 メンバー個別トラッカー — {branch_name}")
st.caption("**問い**: 各営業の進捗・成長は同期コホート対比でどうか／誰に何を指示すべきか")

pf_vals = pf.member(branch_id)
ym = pf_vals["selected_ym"]
selected_members = pf_vals["selected_members"]

st.markdown("---")

社員 = dfs["社員"]
契約 = dfs["契約"]
案件 = dfs["案件"]

営業 = 社員[(社員["現在支店ID"] == branch_id) & (社員["職種"] == "営業") & (社員["氏名"].isin(selected_members))].copy()
営業["経過月数"] = ((pd.Timestamp(ym + "-01") - 営業["入社年月"]).dt.days / 30).astype(int)

rows = []
for _, emp in 営業.iterrows():
    eid = emp["社員ID"]
    k_this = 契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == ym)]
    k_last = 契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == yoy_ym(ym))]
    a_this = 案件[(案件["登録担当社員ID"] == eid) & (案件["年月"] == ym)]

    gp = int(k_this["粗利_確定"].sum())
    gp_ly = int(k_last["粗利_確定"].sum())
    cnt = len(k_this[k_this["契約種別"].isin(["買取", "仲介"])])
    cr = (a_this["成約フラグ"].sum() / len(a_this) * 100) if len(a_this) > 0 else 0.0

    rows.append({
        "社員ID": eid,
        "氏名": emp["氏名"],
        "入社年月": emp["入社年月"].strftime("%Y-%m"),
        "経過月数": emp["経過月数"],
        "雇用形態": emp["現在雇用形態"],
        "出身業種": emp["出身業種"],
        "契約件数": cnt,
        "粗利_確定": gp,
        "粗利_前年": gp_ly,
        "成約率": round(cr, 1),
    })

df_member = pd.DataFrame(rows)

if df_member.empty:
    st.warning("この支店・月の営業データがありません。")
    st.stop()

# ── KPI 表 ──────────────────────────────────────────────────
st.subheader("メンバー別実績（当月）")

gpp_warn = cfg["gross_profit_per_person"]["warning_q1"]["value"]
cr_warn = cfg["closing_rate"]["warning_q1"]["value"]

display_cols = ["氏名", "経過月数", "出身業種", "雇用形態", "契約件数", "粗利_確定", "成約率"]

def highlight_row(row):
    styles = [""] * len(row)
    col_idx = list(row.index)
    if "粗利_確定" in col_idx and row["粗利_確定"] < gpp_warn:
        styles[col_idx.index("粗利_確定")] = "background-color: #fff3cd"
    if "成約率" in col_idx and row["成約率"] < cr_warn:
        styles[col_idx.index("成約率")] = "background-color: #fff3cd"
    return styles

styled = df_member[display_cols].style.apply(highlight_row, axis=1).format({
    "粗利_確定": "¥{:,.0f}",
    "成約率": "{:.1f}%",
    "経過月数": "{}ヶ月",
})
st.dataframe(styled, use_container_width=True)
st.caption("🟡 黄色ハイライト = 閾値（仮置き）を下回り")

attention = df_member[df_member["粗利_確定"] < gpp_warn]
if not attention.empty:
    names = "、".join(attention["氏名"].tolist())
    thr.next_action_box("warning",
        f"{names} の月次粗利が ¥{gpp_warn:,} を下回っています。情報源ミックスの偏りと案件パイプラインを確認してください。")

# ── 粗利棒グラフ（前年比） ──────────────────────────────────
st.subheader("粗利：当月 vs 前年同月")
fig = go.Figure()
fig.add_bar(x=df_member["氏名"], y=df_member["粗利_確定"],
            name="当月", marker_color=PRIMARY)
fig.add_bar(x=df_member["氏名"], y=df_member["粗利_前年"],
            name="前年同月", marker_color=PALE)
fig.add_hline(y=gpp_warn, line_dash="dash", line_color="#e08c00",
              annotation_text=f"閾値 ¥{gpp_warn:,}")
fig.update_layout(barmode="group", yaxis_tickformat=",.0f", yaxis_title="粗利（円）", height=350)
st.plotly_chart(fig, use_container_width=True)

# ── 経過月数 × 粗利 散布図 ──────────────────────────────────
st.subheader("経過月数 × 粗利（成長軌跡）")
fig2 = px.scatter(
    df_member, x="経過月数", y="粗利_確定",
    size="契約件数", color="出身業種", text="氏名",
    color_discrete_sequence=BLUES_5,
    labels={"経過月数": "入社からの経過月数", "粗利_確定": "月次粗利（円）"},
    height=350,
)
fig2.update_traces(textposition="top center",
                   marker=dict(opacity=0.85, line=dict(width=1, color="white")))
fig2.add_hline(y=gpp_warn, line_dash="dash", line_color="#e08c00",
               annotation_text=f"閾値 ¥{gpp_warn:,}")
st.plotly_chart(fig2, use_container_width=True)

# ── コホート別粗利推移 ───────────────────────────────────────
st.subheader("コホート別 平均粗利推移（過去12ヶ月）")

months_12 = pd.period_range(end=pd.Period(ym, freq="M"), periods=12, freq="M")
cohort_rows = []
for _, emp in 営業.iterrows():
    eid = emp["社員ID"]
    hire_yr = emp["入社年月"].year
    for m in months_12:
        m_str = str(m)
        gp_m = int(契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == m_str)]["粗利_確定"].sum())
        cohort_rows.append({"年月": m_str, "入社年": hire_yr, "粗利_確定": gp_m})

df_cohort = pd.DataFrame(cohort_rows).groupby(["年月", "入社年"])["粗利_確定"].mean().reset_index()
df_cohort["入社年"] = df_cohort["入社年"].astype(str) + "年入社"
fig3 = px.line(
    df_cohort, x="年月", y="粗利_確定", color="入社年",
    color_discrete_sequence=BLUES_5,
    labels={"年月": "月", "粗利_確定": "平均粗利（円）"},
    height=350,
)
fig3.update_traces(line=dict(width=2))
fig3.add_hline(y=gpp_warn, line_dash="dash", line_color="#e08c00",
               annotation_text=f"閾値 ¥{gpp_warn:,}")
st.plotly_chart(fig3, use_container_width=True)
