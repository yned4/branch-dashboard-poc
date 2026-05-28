"""画面5: 契約・在庫分析（指標 3-1〜3-11）"""
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

st.set_page_config(page_title="契約・在庫分析", page_icon="📋", layout="wide")

filters = render_sidebar()
dfs = load_data()
cfg = thr.load()

branch_id = filters["branch_id"]
branch_name = filters["branch_name"]

st.title(f"📋 契約・在庫分析 — {branch_name}")
st.caption("**問い**: 買取/仲介比率・サンタメ・在庫回転は適正か／現金投下粗利率は")

pf_vals = pf.contract(branch_id)
ym = pf_vals["selected_ym"]
start_ym = pf_vals["start_ym"]
end_ym = pf_vals["end_ym"]
sel_keiyaku_types = pf_vals["sel_keiyaku_types"]
sel_prop_types = pf_vals["sel_prop_types"]
sel_areas = pf_vals["sel_areas"]

st.markdown("---")

契約 = dfs["契約"]
物件 = dfs["物件"]

months_12 = [str(p) for p in pd.period_range(start=pd.Period(start_ym, "M"), end=pd.Period(end_ym, "M"), freq="M")]
k_self = 契約[契約["契約時点支店ID"] == branch_id]
k_month = k_self[k_self["年月"] == ym]
k_12 = k_self[k_self["年月"].isin(months_12)]
k_all_month = 契約[契約["年月"] == ym]

# ── 3-1 買取・仲介比率 ─────────────────────────────────────
st.subheader("3-1 買取・仲介比率")

def type_ratio(df_k):
    total = len(df_k[df_k["契約種別"].isin(["買取", "仲介"])])
    if total == 0:
        return 0, 0
    buy = len(df_k[df_k["契約種別"] == "買取"])
    med = len(df_k[df_k["契約種別"] == "仲介"])
    return buy / total * 100, med / total * 100

buy_pct, med_pct = type_ratio(k_month)
buy_pct_all, med_pct_all = type_ratio(k_all_month)

c1, c2 = st.columns(2)
with c1:
    fig = go.Figure(go.Bar(
        x=["買取", "仲介"], y=[buy_pct, med_pct],
        name=branch_name, marker_color=[PRIMARY, LIGHT],
    ))
    fig.add_bar(x=["買取", "仲介"], y=[buy_pct_all, med_pct_all],
                name="全支店平均", marker_color=[PALE, OTHER])
    fig.update_layout(barmode="group", yaxis_title="%", height=280,
                      title="買取・仲介比率（当月）")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # 推移
    trend = k_12.groupby(["年月", "契約種別"]).size().reset_index(name="件数")
    trend = trend[trend["契約種別"].isin(["買取", "仲介"])]
    fig2 = px.bar(trend, x="年月", y="件数", color="契約種別", barmode="stack",
                  height=280, title="買取・仲介件数推移（過去12ヶ月）")
    st.plotly_chart(fig2, use_container_width=True)

# ── 3-2 サンタメ比率 ──────────────────────────────────────
st.subheader("3-2 サンタメ比率")

st_lo = cfg["santame_ratio"]["normal_range"]["lower_pct"]["value"]
st_hi = cfg["santame_ratio"]["normal_range"]["upper_pct"]["value"]

santame_pct = k_month["サンタメフラグ"].mean() * 100 if len(k_month) > 0 else 0
level = "ok"
if santame_pct < st_lo or santame_pct > st_hi:
    level = "warning"

col1, col2, col3 = st.columns(3)
col1.metric("サンタメ比率（当月）", f"{santame_pct:.1f}%")
col2.metric("正常レンジ（仮置き）", f"{st_lo}〜{st_hi}%")
col3.metric("ステータス", "🟡 注意" if level != "ok" else "🟢 正常")

if level != "ok":
    thr.next_action_box("warning",
        f"サンタメ比率が {santame_pct:.1f}% と正常レンジ（{st_lo}〜{st_hi}%）から逸脱しています。"
        "契約スキームの構成を確認してください。")

# ── 3-3 契約件数 種別別 ───────────────────────────────────
st.subheader("3-3 契約件数（仕入・仲介・売却）月次推移")

cnt_trend = k_12.groupby(["年月", "契約種別"]).size().reset_index(name="件数")
fig3 = px.line(cnt_trend, x="年月", y="件数", color="契約種別", markers=True,
               height=280)
st.plotly_chart(fig3, use_container_width=True)

# ── 3-4 & 3-5 支店別 1人当たり契約数・粗利 ──────────────────
st.subheader("3-4/3-5 支店別 1人当たり契約数・粗利（当月）")

支店_all = dfs["支店"]
rows_branch = []
for _, b in 支店_all.iterrows():
    bid = b["支店ID"]
    k_b = 契約[(契約["契約時点支店ID"] == bid) & (契約["年月"] == ym)]
    hc = headcount_coefficient(dfs, bid, cfg)
    total_gp = k_b["粗利_確定"].sum()
    total_cnt = len(k_b[k_b["契約種別"].isin(["買取", "仲介"])])
    rows_branch.append({
        "支店名": b["支店名"],
        "1人当たり粗利": total_gp / hc if hc > 0 else 0,
        "1人当たり契約数": total_cnt / hc if hc > 0 else 0,
        "is_self": bid == branch_id,
    })

df_branch = pd.DataFrame(rows_branch)
colors = ["#1f77b4" if r else "#d3d3d3" for r in df_branch["is_self"]]

gpp_warn = cfg["gross_profit_per_person"]["warning_q1"]["value"]

c3, c4 = st.columns(2)
with c3:
    fig4 = px.bar(df_branch, x="支店名", y="1人当たり粗利",
                  color="is_self", color_discrete_map={True: "#1f77b4", False: "#d3d3d3"},
                  height=280, title="1人当たり月次粗利")
    fig4.add_hline(y=gpp_warn, line_dash="dash", line_color="orange",
                   annotation_text=f"閾値 ¥{gpp_warn:,}")
    fig4.add_hline(y=2_000_000, line_dash="dot", line_color="red",
                   annotation_text="増員アラート 200万円")
    fig4.update_layout(showlegend=False, yaxis_tickformat=",.0f")
    st.plotly_chart(fig4, use_container_width=True)

with c4:
    fig5 = px.bar(df_branch, x="支店名", y="1人当たり契約数",
                  color="is_self", color_discrete_map={True: PRIMARY, False: OTHER},
                  height=280, title="1人当たり契約件数")
    fig5.update_layout(showlegend=False)
    st.plotly_chart(fig5, use_container_width=True)

self_gpp = df_branch[df_branch["is_self"]]["1人当たり粗利"].values[0] if not df_branch[df_branch["is_self"]].empty else 0
if self_gpp >= 2_000_000:
    thr.next_action_box("critical",
        f"1人当たり粗利が ¥{self_gpp:,.0f} で200万円を超過しています。"
        "支店のキャパシティ上限に達している可能性が高いため、新規採用・増員計画をスケジュールしてください。")
elif self_gpp < gpp_warn:
    thr.next_action_box("warning",
        f"1人当たり粗利が ¥{self_gpp:,.0f} と閾値 ¥{gpp_warn:,} を下回っています。"
        "業務効率化や人員スキル底上げを検討してください。")

# ── 3-6 在庫回転日数 ──────────────────────────────────────
st.subheader("3-6 在庫回転日数（分布）")

buk_self = 物件[(物件["取得支店ID"] == branch_id)].dropna(subset=["在庫日数"])
buk_all = 物件.dropna(subset=["在庫日数"])

inv_warn = cfg["inventory_turnover_days"]["warning"]["value"]
inv_crit = cfg["inventory_turnover_days"]["critical"]["value"]

if not buk_self.empty:
    med_inv = buk_self["在庫日数"].median()
    avg_inv = buk_self["在庫日数"].mean()
    c5, c6 = st.columns(2)
    c5.metric("在庫日数 中央値", f"{med_inv:.0f}日")
    c6.metric("在庫日数 平均", f"{avg_inv:.0f}日")

    fig6 = px.histogram(buk_self, x="在庫日数", nbins=25, height=280,
                        title=f"在庫回転日数分布（{branch_name}）",
                        color_discrete_sequence=[PRIMARY])
    fig6.add_vline(x=inv_warn, line_dash="dash", line_color="orange",
                   annotation_text=f"警告 {inv_warn}日")
    fig6.add_vline(x=inv_crit, line_dash="dash", line_color="red",
                   annotation_text=f"要対応 {inv_crit}日")
    st.plotly_chart(fig6, use_container_width=True)

    long_cnt = (buk_self["在庫日数"] > inv_warn).sum()
    if long_cnt > 0:
        thr.next_action_box("warning",
            f"在庫日数 {inv_warn}日超の物件が {long_cnt} 件あります。価格見直しか出口戦略変更を検討してください。")

# ── 3-7 在庫回転金額（回転率） ────────────────────────────
st.subheader("3-7 在庫回転金額（回転率）— 過去12ヶ月")

sold_12 = 物件[(物件["取得支店ID"] == branch_id) & 物件["売却日"].notna()]
sold_12["売却年月"] = sold_12["売却日"].dt.to_period("M").astype(str)
sold_12 = sold_12[sold_12["売却年月"].isin(months_12)]
cogs = sold_12["取得価格"].sum()

unsold = 物件[(物件["取得支店ID"] == branch_id) & 物件["売却日"].isna()]
avg_inv_val = unsold["取得価格"].mean() if len(unsold) > 0 else 0
turnover_rate = (cogs / (avg_inv_val * 12)) if avg_inv_val > 0 else 0

st.metric("年間在庫回転率（12ヶ月）", f"{turnover_rate:.2f}回転")

# ── 3-8 現金投下粗利率 ────────────────────────────────────
st.subheader("3-8 現金投下粗利率")

k_baitori = k_12[k_12["契約種別"] == "買取"].dropna(subset=["投下現金額"])
k_baitori = k_baitori[k_baitori["投下現金額"] > 0]

cim_warn = cfg["cash_invested_margin"]["warning_q1"]["value"]

if not k_baitori.empty:
    # 売却粗利を案件IDでひも付け
    売却 = k_self[(k_self["契約種別"] == "売却") & k_self["年月"].isin(months_12)]
    gp_per_anken = 売却.groupby("案件ID")["粗利_確定"].sum().reset_index()
    k_merged = k_baitori.merge(gp_per_anken, on="案件ID", how="left", suffixes=("_buy", "_sell"))
    k_merged["粗利_確定_sell"] = k_merged["粗利_確定_sell"].fillna(0)
    k_merged["現金投下粗利率"] = k_merged["粗利_確定_sell"] / k_merged["投下現金額"] * 100
    cim_avg = k_merged["現金投下粗利率"].mean()
    cim_med = k_merged["現金投下粗利率"].median()

    c7, c8 = st.columns(2)
    c7.metric("現金投下粗利率 平均", f"{cim_avg:.1f}%")
    c8.metric("中央値", f"{cim_med:.1f}%")

    level_cim, _ = thr.check_breach(cim_avg, {"direction": "lower_is_bad", "value": cim_warn})
    if level_cim != "ok":
        thr.next_action_box("warning",
            f"現金投下粗利率が {cim_avg:.1f}% と閾値 {cim_warn}% を下回っています。"
            "仕入価格の妥当性と融資レバレッジの活用状況を確認してください。")

# ── 3-9 買取契約〜決済リードタイム ──────────────────────────
st.subheader("3-9 買取契約〜決済リードタイム")

k_buy_lt = k_12[(k_12["契約種別"] == "買取") & k_12["決済日"].notna()].copy()
k_buy_lt["リードタイム"] = (k_buy_lt["決済日"] - k_buy_lt["契約日"]).dt.days

if not k_buy_lt.empty:
    avg_lt = k_buy_lt["リードタイム"].mean()
    med_lt = k_buy_lt["リードタイム"].median()
    c9, c10 = st.columns(2)
    c9.metric("平均リードタイム", f"{avg_lt:.0f}日")
    c10.metric("中央値", f"{med_lt:.0f}日")

    fig7 = px.histogram(k_buy_lt, x="リードタイム", nbins=15, height=250,
                        color_discrete_sequence=[MID])
    fig7.add_vline(x=60, line_dash="dash", line_color="orange", annotation_text="警告 60日")
    fig7.add_vline(x=90, line_dash="dash", line_color="red", annotation_text="要対応 90日")
    st.plotly_chart(fig7, use_container_width=True)

    if avg_lt > 90:
        thr.next_action_box("critical",
            f"買取契約〜決済リードタイムが平均 {avg_lt:.0f}日 です（要対応 90日超）。"
            "法務・金融手続きの停滞要因を特定し早期解消を図ってください。")
    elif avg_lt > 60:
        thr.next_action_box("warning",
            f"買取契約〜決済リードタイムが平均 {avg_lt:.0f}日 です（警告 60日超）。"
            "停滞要因を確認してください。")

# ── 3-10 種別・エリア別 在庫回転日数 × 粗利率 ───────────────
st.subheader("3-10 種別・エリア別 在庫回転日数 × 粗利率")

buk_w_gp = 物件[(物件["取得支店ID"] == branch_id) & (物件["種別"].isin(sel_prop_types)) & (物件["エリア"].isin(sel_areas))].dropna(subset=["在庫日数", "売却価格", "取得価格"]).copy()
buk_w_gp["粗利率(%)"] = (buk_w_gp["売却価格"] - buk_w_gp["取得価格"]) / buk_w_gp["取得価格"] * 100

if not buk_w_gp.empty:
    # ① 種別別 バー比較（在庫日数 vs 粗利率）
    by_type = buk_w_gp.groupby("種別").agg(
        平均在庫日数=("在庫日数", "mean"),
        中央値在庫日数=("在庫日数", "median"),
        平均粗利率=("粗利率(%)", "mean"),
        件数=("物件ID", "count"),
    ).reset_index()

    c_bar1, c_bar2 = st.columns(2)
    with c_bar1:
        fig_bar1 = go.Figure()
        fig_bar1.add_bar(x=by_type["種別"], y=by_type["平均在庫日数"],
                         name="平均", marker_color=PRIMARY,
                         text=by_type["平均在庫日数"].round(0).astype(int).astype(str) + "日",
                         textposition="auto")
        fig_bar1.add_bar(x=by_type["種別"], y=by_type["中央値在庫日数"],
                         name="中央値", marker_color=PALE,
                         text=by_type["中央値在庫日数"].round(0).astype(int).astype(str) + "日",
                         textposition="auto")
        fig_bar1.add_hline(y=inv_warn, line_dash="dash", line_color="orange",
                           annotation_text=f"警告 {inv_warn}日",
                           annotation_position="bottom right")
        fig_bar1.update_layout(barmode="group", yaxis_title="在庫日数",
                               yaxis_range=[0, by_type["平均在庫日数"].max() * 1.2],
                               title="種別別 平均在庫日数", height=320, showlegend=True)
        st.plotly_chart(fig_bar1, use_container_width=True)

    with c_bar2:
        fig_bar2 = px.bar(by_type, x="種別", y="平均粗利率", text="平均粗利率",
                          color="種別", height=320, title="種別別 平均粗利率（%）",
                          color_discrete_sequence=BLUES_5)
        fig_bar2.update_traces(texttemplate="%{text:.1f}%", textposition="auto")
        fig_bar2.update_layout(showlegend=False, yaxis_title="粗利率（%）",
                               yaxis_range=[0, by_type["平均粗利率"].max() * 1.2])
        st.plotly_chart(fig_bar2, use_container_width=True)

    # ② 種別×エリア 集計散布図（平均値プロット）
    st.caption("▼ 種別×エリア 平均値散布図（ホバーで詳細確認 / 右上が「得意ゾーン」）")
    by_type_area = buk_w_gp.groupby(["種別", "エリア"]).agg(
        平均在庫日数=("在庫日数", "mean"),
        平均粗利率=("粗利率(%)", "mean"),
        件数=("物件ID", "count"),
    ).reset_index()

    x_mid = by_type_area["平均在庫日数"].median()

    fig_sc = px.scatter(
        by_type_area, x="平均在庫日数", y="平均粗利率",
        color="種別", size="件数",
        hover_name="エリア",
        hover_data={"種別": True, "件数": True,
                    "平均在庫日数": ":.0f", "平均粗利率": ":.1f"},
        size_max=40, height=440,
        labels={"平均在庫日数": "平均在庫日数（日）", "平均粗利率": "平均粗利率（%）"},
        color_discrete_sequence=BLUES_5,
    )
    fig_sc.update_traces(marker=dict(opacity=0.85, line=dict(width=1.5, color="white")))

    # 警告ライン
    fig_sc.add_vline(x=inv_warn, line_dash="dash", line_color="orange",
                     annotation_text=f"警告 {inv_warn}日", annotation_position="top right")

    # 象限ラベル（paper 座標で固定配置 → データ範囲によらず重ならない）
    for (xref_val, yref_val, label, color) in [
        (0.02, 0.97, "高粗利・短期回転（得意ゾーン）", "green"),
        (0.72, 0.97, "高粗利・長期滞留（価格見直し）", "orange"),
        (0.02, 0.06, "低粗利・短期回転（仕入見直し）", "steelblue"),
        (0.72, 0.06, "低粗利・長期滞留（要優先対応）", "red"),
    ]:
        fig_sc.add_annotation(
            xref="paper", yref="paper",
            x=xref_val, y=yref_val,
            text=label, showarrow=False,
            font=dict(size=9, color=color),
            align="left", opacity=0.6,
        )

    fig_sc.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60),
    )
    st.plotly_chart(fig_sc, use_container_width=True)

# ── 3-11 長期滞留在庫の評価額比率 ────────────────────────────
st.subheader("3-11 長期滞留在庫 評価額比率（月末スナップショット）")

today_approx = pd.Timestamp(ym + "-01") + pd.offsets.MonthEnd(0)
unsold_all = 物件[(物件["取得支店ID"] == branch_id) & 物件["売却日"].isna()].copy()
unsold_all["現在保有日数"] = (today_approx - unsold_all["取得日"]).dt.days

if not unsold_all.empty:
    long_val = unsold_all[unsold_all["現在保有日数"] > inv_warn]["取得価格"].sum()
    total_val = unsold_all["取得価格"].sum()
    long_pct = (long_val / total_val * 100) if total_val > 0 else 0

    c11, c12 = st.columns(2)
    c11.metric(f"長期滞留在庫（{inv_warn}日超）評価額", f"¥{long_val:,.0f}")
    c12.metric("全在庫に占める比率", f"{long_pct:.1f}%")

    if long_pct > 20:
        level_li = "critical" if long_pct > 30 else "warning"
        thr.next_action_box(level_li,
            f"{inv_warn}日超の長期滞留在庫が全在庫の {long_pct:.1f}% を占めています。"
            "対象物件の価格改定または損切りを経営判断として早急に実施してください。")
