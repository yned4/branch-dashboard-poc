"""画面4: 売却出口分析（指標 2-1〜2-5）"""
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

st.set_page_config(page_title="売却出口分析", page_icon="🚪", layout="wide")

filters = render_sidebar()
dfs = load_data()
cfg = thr.load()

branch_id = filters["branch_id"]
branch_name = filters["branch_name"]

st.title(f"🚪 売却出口分析 — {branch_name}")
st.caption("**問い**: 法人/個人・現況/再販構成は健全か／再販日数は適正か")

pf_vals = pf.exit_analysis(branch_id)
ym = pf_vals["selected_ym"]
start_ym = pf_vals["start_ym"]
end_ym = pf_vals["end_ym"]
sel_exit = pf_vals["sel_exit"]
sel_corp = pf_vals["sel_corp"]

st.markdown("---")

契約 = dfs["契約"]
出口 = dfs["出口"]
物件 = dfs["物件"]

baikyaku_self = 契約[
    (契約["契約時点支店ID"] == branch_id) &
    (契約["契約種別"] == "売却")
].merge(出口, on="出口ID", how="left")
baikyaku_self = baikyaku_self[baikyaku_self["現況再販区分"].isin(sel_exit) & baikyaku_self["法人個人区分"].isin(sel_corp)]

baikyaku_month = baikyaku_self[baikyaku_self["年月"] == ym]
baikyaku_ly = baikyaku_self[baikyaku_self["年月"] == yoy_ym(ym)]
baikyaku_all = 契約[契約["契約種別"] == "売却"].merge(出口, on="出口ID", how="left")
baikyaku_all_month = baikyaku_all[baikyaku_all["年月"] == ym]

dev_warn = cfg["exit_composition"]["legal_individual_deviation_pct"]["value"]
months_12 = [str(p) for p in pd.period_range(start=pd.Period(start_ym, "M"), end=pd.Period(end_ym, "M"), freq="M")]

# ── 2-1 法人・個人 売却先割合 ────────────────────────────────
st.subheader("2-1 法人・個人 売却先割合")

def pie_chart(data, col, title):
    if data.empty:
        return None
    cnt = data[col].value_counts().reset_index()
    cnt.columns = [col, "件数"]
    fig = px.pie(cnt, names=col, values="件数", hole=0.4, title=title, height=260,
                 color_discrete_sequence=[PRIMARY, PALE])
    fig.update_traces(textposition="inside", textinfo="label+percent",
                      textfont=dict(size=12))
    return fig

c1, c2, c3 = st.columns(3)
for col, (data, title) in zip(
    [c1, c2, c3],
    [(baikyaku_month, f"当月（{ym}）"),
     (baikyaku_ly, f"前年同月（{yoy_ym(ym)}）"),
     (baikyaku_all_month, "全支店平均（当月）")]
):
    f = pie_chart(data, "法人個人区分", title)
    if f:
        col.plotly_chart(f, use_container_width=True)

if not baikyaku_month.empty and not baikyaku_all_month.empty:
    self_corp = (baikyaku_month["法人個人区分"] == "法人").mean() * 100
    all_corp = (baikyaku_all_month["法人個人区分"] == "法人").mean() * 100
    if abs(self_corp - all_corp) > dev_warn:
        thr.next_action_box("warning",
            f"法人/個人比率が全支店平均から {abs(self_corp-all_corp):.1f}% 乖離しています（閾値 {dev_warn}%）。"
            "市況変化か特定営業手法への偏りがないか確認してください。")

# ── 2-2 現況・再販 割合推移 ─────────────────────────────────
st.subheader("2-2 現況販売・リフォーム再販 割合推移（過去12ヶ月）")

bk_12 = baikyaku_self[baikyaku_self["年月"].isin(months_12)]
if not bk_12.empty:
    trend = bk_12.groupby(["年月", "現況再販区分"]).size().reset_index(name="件数")
    fig_trend = px.bar(trend, x="年月", y="件数", color="現況再販区分", barmode="stack",
                       height=300, color_discrete_map={"現況": PALE, "再販": PRIMARY})
    st.plotly_chart(fig_trend, use_container_width=True)

if not baikyaku_month.empty and not baikyaku_all_month.empty:
    dev_warn2 = cfg["exit_composition"]["current_resale_deviation_pct"]["value"]
    self_resale = (baikyaku_month["現況再販区分"] == "再販").mean() * 100
    all_resale = (baikyaku_all_month["現況再販区分"] == "再販").mean() * 100
    if abs(self_resale - all_resale) > dev_warn2:
        thr.next_action_box("warning",
            f"現況/再販比率が全支店平均から {abs(self_resale-all_resale):.1f}% 乖離しています（閾値 {dev_warn2}%）。"
            "粗利率と資金繰りへの影響を確認してください。")

# ── 2-3 リフォーム再販 平均粗利（支店比較） ──────────────────
st.subheader("2-3 リフォーム再販 平均粗利（支店比較）")

resale_gp = 契約[契約["契約種別"] == "売却"].merge(出口, on="出口ID", how="left")
resale_gp_12 = resale_gp[
    (resale_gp["現況再販区分"] == "再販") & resale_gp["年月"].isin(months_12)
].merge(dfs["支店"][["支店ID", "支店名"]], left_on="契約時点支店ID", right_on="支店ID", how="left")

gp_by_branch = resale_gp_12.groupby("支店名")["粗利_確定"].mean().reset_index()
gp_by_branch.columns = ["支店名", "平均粗利"]
gp_by_branch["色"] = gp_by_branch["支店名"].apply(lambda n: PRIMARY if n == branch_name else OTHER)

fig_gp = px.bar(
    gp_by_branch.sort_values("平均粗利", ascending=True),
    x="平均粗利", y="支店名", orientation="h", height=280,
    color="支店名",
    color_discrete_map={n: c for n, c in zip(gp_by_branch["支店名"], gp_by_branch["色"])},
)
fig_gp.update_layout(showlegend=False, xaxis_tickformat=",.0f", xaxis_title="平均粗利（円）")
st.plotly_chart(fig_gp, use_container_width=True)

# ── 2-4 リフォーム再販 平均売却日数 ──────────────────────────
st.subheader("2-4 リフォーム再販 平均売却日数")

inv_warn = cfg["inventory_turnover_days"]["warning"]["value"]
inv_crit = cfg["inventory_turnover_days"]["critical"]["value"]

物件_resale = 物件.merge(
    契約[契約["契約種別"] == "売却"].merge(出口, on="出口ID", how="left")[
        ["物件ID", "現況再販区分", "契約時点支店ID"]
    ],
    on="物件ID", how="inner"
)
物件_resale = 物件_resale[(物件_resale["現況再販区分"] == "再販")].dropna(subset=["在庫日数"])

if not 物件_resale.empty:
    self_days = 物件_resale[物件_resale["契約時点支店ID"] == branch_id]["在庫日数"]
    avg_days = self_days.mean()
    med_days = self_days.median()

    c4, c5 = st.columns(2)
    c4.metric("平均売却日数", f"{avg_days:.0f}日")
    c5.metric("中央値", f"{med_days:.0f}日")

    level, _ = thr.check_breach(avg_days, {
        "direction": "higher_is_bad",
        "warning": {"value": inv_warn},
        "critical": {"value": inv_crit},
    })
    if level != "ok":
        thr.next_action_box(level,
            f"リフォーム再販の平均売却日数が {avg_days:.0f}日 です（警告：{inv_warn}日超）。"
            "工事遅延か販売長期化か、ボトルネックを特定してください。")

    fig_hist = px.histogram(
        物件_resale, x="在庫日数", color="契約時点支店ID",
        color_discrete_map={branch_id: PRIMARY},
        barmode="overlay", nbins=20, height=280,
        title="再販物件 売却日数分布",
    )
    fig_hist.for_each_trace(lambda t: t.update(
        marker_color=PRIMARY if t.name == str(branch_id) else OTHER,
        opacity=0.8,
    ))
    fig_hist.add_vline(x=inv_warn, line_dash="dash", line_color="#e08c00",
                       annotation_text=f"警告 {inv_warn}日")
    fig_hist.add_vline(x=inv_crit, line_dash="dash", line_color="#c0392b",
                       annotation_text=f"要対応 {inv_crit}日")
    st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.info("リフォーム再販データなし。")

# ── 2-5 ──────────────────────────────────────────────────────
st.subheader("2-5 出口別 値引き率")
st.info("⚠️ `想定売価` カラムが未整備のため、現時点では計算不可。データ整備後に有効化。")
