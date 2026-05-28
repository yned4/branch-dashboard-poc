"""画面6: 成長分析（指標 4-1〜4-4）"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data import load_data
from utils.sidebar import render as render_sidebar
from utils import thresholds as thr
from utils import page_filters as pf
from utils.colors import SELF, PRIMARY, MID, LIGHT, PALE, OTHER, BLUES_5

st.set_page_config(page_title="成長分析", page_icon="📈", layout="wide")

filters = render_sidebar()
dfs = load_data()
cfg = thr.load()

branch_id = filters["branch_id"]
branch_name = filters["branch_name"]

st.title(f"📈 成長分析 — {branch_name}")
st.caption("**問い**: メンバーの成長カーブ／自支店の成熟段階／採用判断材料")

pf_vals = pf.growth(branch_id)
ym = pf_vals["selected_ym"]
start_ym = pf_vals["start_ym"]
end_ym = pf_vals["end_ym"]
sel_industries = pf_vals["sel_industries"]

st.markdown("---")

契約 = dfs["契約"]
社員 = dfs["社員"]
支店 = dfs["支店"]
案件 = dfs["案件"]
情報源 = dfs["情報源"]

all_months = [str(p) for p in pd.period_range(start=pd.Period(start_ym, "M"), end=pd.Period(end_ym, "M"), freq="M")]
gpp_warn = cfg["gross_profit_per_person"]["warning_q1"]["value"]

# ── 4-1 支店フェーズ別 成長分析 ────────────────────────────
st.subheader("4-1 支店フェーズ別 成長分析")

def phase_label(opened: pd.Timestamp, ref: pd.Timestamp) -> str:
    months = int((ref - opened).days / 30)
    if months <= 12:
        return "新規出店（1年目）"
    elif months <= 36:
        return "成長期（2〜3年目）"
    return "成熟期（4年目〜）"

# フェーズメトリック表示
ref_ts = pd.Timestamp(ym + "-01")
phase_cols = st.columns(len(支店))
for col, (_, b) in zip(phase_cols, 支店.iterrows()):
    ph = phase_label(b["開設年月"], ref_ts)
    elapsed_mo = int((ref_ts - b["開設年月"]).days / 30)
    col.metric(
        b["支店名"] + ("（自支店）" if b["支店ID"] == branch_id else ""),
        ph,
        f"開設 {elapsed_mo} ヶ月目",
    )

# 月次粗利トレンド（x軸 = カレンダー月で揃える）
branch_gp = []
for _, b in 支店.iterrows():
    bid = b["支店ID"]
    for m in all_months:
        gp = 契約[(契約["契約時点支店ID"] == bid) & (契約["年月"] == m)]["粗利_確定"].sum()
        branch_gp.append({"支店名": b["支店名"], "年月": m,
                           "月次粗利": int(gp), "is_self": bid == branch_id})

df_bt = pd.DataFrame(branch_gp)
avg_by_month = df_bt.groupby("年月")["月次粗利"].mean().reset_index()

fig1 = go.Figure()
fig1.add_scatter(x=avg_by_month["年月"], y=avg_by_month["月次粗利"],
                 mode="lines", name="全支店平均",
                 line=dict(color=OTHER, dash="dash", width=1.5))

for _, b in 支店.iterrows():
    is_self = b["支店ID"] == branch_id
    sub = df_bt[df_bt["支店名"] == b["支店名"]]
    fig1.add_scatter(
        x=sub["年月"], y=sub["月次粗利"],
        mode="lines+markers", name=b["支店名"],
        line=dict(color=SELF if is_self else LIGHT,
                  width=3 if is_self else 1.5,
                  dash="solid" if is_self else "dot"),
        marker=dict(size=5 if is_self else 3),
    )

fig1.update_layout(
    height=380, yaxis_tickformat=",.0f",
    xaxis_title="年月", yaxis_title="月次粗利（円）",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    xaxis=dict(tickangle=-45),
)
st.plotly_chart(fig1, use_container_width=True)
st.caption("※ x軸はカレンダー月。各支店のフェーズはメトリックカードに表示。")

# ── 4-2 入社期別 コホート成長分析 ──────────────────────────
st.subheader("4-2 入社期別 コホート成長分析")

営業 = 社員[(社員["現在支店ID"] == branch_id) & (社員["職種"] == "営業")].copy()
cohort_rows = []
for _, emp in 営業.iterrows():
    eid = emp["社員ID"]
    hire = emp["入社年月"]
    hire_yr = str(hire.year) + "年入社"
    for m in all_months:
        elapsed = max(0, int((pd.Timestamp(m + "-01") - hire).days / 30))
        gp = int(契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == m)]["粗利_確定"].sum())
        cohort_rows.append({"入社期": hire_yr, "経過月数": elapsed, "粗利_確定": gp})

df_cohort = pd.DataFrame(cohort_rows).groupby(["入社期", "経過月数"])["粗利_確定"].mean().reset_index()

fig2 = px.line(df_cohort, x="経過月数", y="粗利_確定", color="入社期",
               color_discrete_sequence=BLUES_5, height=350,
               labels={"経過月数": "入社からの経過月数", "粗利_確定": "月次粗利 平均（円）"})
fig2.update_traces(line=dict(width=2))
fig2.add_hline(y=gpp_warn, line_dash="dash", line_color="#e08c00",
               annotation_text=f"閾値 ¥{gpp_warn:,}")
st.plotly_chart(fig2, use_container_width=True)

# ── 4-3 出身業種別 成長傾向 ──────────────────────────────
st.subheader("4-3 出身業種別 成長傾向（採用ターゲット参考）")

industry_rows = []
for _, emp in 社員[(社員["職種"] == "営業") & (社員["出身業種"].isin(sel_industries))].iterrows():
    eid = emp["社員ID"]
    hire = emp["入社年月"]
    for m in all_months:
        elapsed = max(0, int((pd.Timestamp(m + "-01") - hire).days / 30))
        if elapsed > 48:
            continue
        gp = int(契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == m)]["粗利_確定"].sum())
        industry_rows.append({"出身業種": emp["出身業種"], "経過月数": elapsed, "粗利_確定": gp})

df_ind = pd.DataFrame(industry_rows).groupby(["出身業種", "経過月数"])["粗利_確定"].mean().reset_index()
fig3 = px.line(df_ind, x="経過月数", y="粗利_確定", color="出身業種",
               color_discrete_sequence=BLUES_5, height=350,
               labels={"経過月数": "入社からの経過月数", "粗利_確定": "月次粗利 平均（円）"})
fig3.update_traces(line=dict(width=2))
fig3.add_hline(y=gpp_warn, line_dash="dash", line_color="#e08c00",
               annotation_text=f"閾値 ¥{gpp_warn:,}")
st.plotly_chart(fig3, use_container_width=True)
st.caption("⚠️ HR向け参考指標。採用ターゲット選定の補助データとして活用。")

# ── 4-4 成長フェーズ × 情報源ポートフォリオ ─────────────────
st.subheader("4-4 成長フェーズと情報源ポートフォリオ推移")

a_w = 案件[案件["登録時点支店ID"] == branch_id].copy()
a_w = a_w.merge(社員[["社員ID", "入社年月"]].rename(columns={"社員ID": "登録担当社員ID"}),
                on="登録担当社員ID", how="left")
a_w = a_w.merge(情報源, on="情報源ID", how="left")
a_w["経過月数"] = ((a_w["登録日"] - a_w["入社年月"]).dt.days / 30).fillna(-1).astype(int)
a_w = a_w[a_w["経過月数"] >= 0]
a_w["経験年次"] = (a_w["経過月数"] // 12 + 1).clip(upper=5).astype(str) + "年目"

tenure_src = a_w.groupby(["経験年次", "情報源名"]).size().reset_index(name="案件数")
tenure_total = tenure_src.groupby("経験年次")["案件数"].transform("sum")
tenure_src["割合(%)"] = (tenure_src["案件数"] / tenure_total * 100).round(1)

if not tenure_src.empty:
    fig4 = px.bar(tenure_src, x="経験年次", y="割合(%)", color="情報源名",
                  barmode="stack", height=350,
                  color_discrete_sequence=BLUES_5,
                  title="経験年次別 情報源構成比（育成マイルストーン確認用）")
    fig4.update_layout(yaxis_title="割合（%）")
    st.plotly_chart(fig4, use_container_width=True)

    dep_warn = cfg["info_source_efficiency"]["dependency_max_pct"]["value"]
    for yr in tenure_src["経験年次"].unique():
        yr_int = int(yr.replace("年目", ""))
        if yr_int < 2:
            continue
        top = tenure_src[tenure_src["経験年次"] == yr].sort_values("割合(%)", ascending=False)
        if not top.empty and top.iloc[0]["割合(%)"] > dep_warn:
            thr.next_action_box("warning",
                f"{yr} の「{top.iloc[0]['情報源名']}」依存度が {top.iloc[0]['割合(%)']:.1f}% と"
                f" {dep_warn}% を超えています。より高粗利の情報源への開拓を指導してください。")
            break
