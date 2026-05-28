"""画面7: レビュー会用エクスポート（本部月次報告サマリー）"""
import streamlit as st
import pandas as pd
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data import load_data, yoy_ym, headcount_coefficient
from utils.sidebar import render as render_sidebar
from utils import thresholds as thr

st.set_page_config(page_title="レビューエクスポート", page_icon="📄", layout="wide")

filters = render_sidebar()
dfs = load_data()
cfg = thr.load()

branch_id = filters["branch_id"]
branch_name = filters["branch_name"]
ym = filters["selected_ym"]

st.title(f"📄 レビュー会用サマリー — {branch_name} / {ym}")
st.caption("**問い**: 本部に何を報告し何を約束するか")
st.markdown("---")

# ── データ集計 ────────────────────────────────────────────────
契約 = dfs["契約"]
案件 = dfs["案件"]
物件 = dfs["物件"]
社員 = dfs["社員"]

k_self = 契約[契約["契約時点支店ID"] == branch_id]
k_month = k_self[k_self["年月"] == ym]
k_last = k_self[k_self["年月"] == yoy_ym(ym)]
k_all_month = 契約[契約["年月"] == ym]

a_self = 案件[案件["登録時点支店ID"] == branch_id]
a_month = a_self[a_self["年月"] == ym]

hc = headcount_coefficient(dfs, branch_id, cfg)

gp_this = int(k_month["粗利_確定"].sum())
gp_last = int(k_last["粗利_確定"].sum())
gp_all_avg = int(k_all_month.groupby("契約時点支店ID")["粗利_確定"].sum().mean())
gp_yoy_pct = ((gp_this - gp_last) / gp_last * 100) if gp_last > 0 else 0
gp_per_person = gp_this / hc if hc > 0 else 0

buy_cnt = len(k_month[k_month["契約種別"] == "買取"])
med_cnt = len(k_month[k_month["契約種別"] == "仲介"])
sell_cnt = len(k_month[k_month["契約種別"] == "売却"])

close_rate = (a_month["成約フラグ"].sum() / len(a_month) * 100) if len(a_month) > 0 else 0.0

santame_pct = k_month["サンタメフラグ"].mean() * 100 if len(k_month) > 0 else 0

today_approx = pd.Timestamp(ym + "-01") + pd.offsets.MonthEnd(0)
unsold = 物件[(物件["取得支店ID"] == branch_id) & 物件["売却日"].isna()].copy()
unsold["現在保有日数"] = (today_approx - unsold["取得日"]).dt.days
inv_warn = cfg["inventory_turnover_days"]["warning"]["value"]
long_cnt = int((unsold["現在保有日数"] > inv_warn).sum())

gpp_warn = cfg["gross_profit_per_person"]["warning_q1"]["value"]
cr_warn = cfg["closing_rate"]["warning_q1"]["value"]
st_lo = cfg["santame_ratio"]["normal_range"]["lower_pct"]["value"]
st_hi = cfg["santame_ratio"]["normal_range"]["upper_pct"]["value"]

# ── 上段: 主要 KPI サマリー ──────────────────────────────────
st.markdown("## 📊 主要 KPI サマリー")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**月次粗利**")
    st.markdown(f"### ¥{gp_this:,.0f}")
    st.markdown(f"前月比: **{gp_yoy_pct:+.1f}%** (YoY) | 他支店平均: ¥{gp_all_avg:,.0f}")

with col2:
    st.markdown("**1人当たり粗利**")
    st.markdown(f"### ¥{gp_per_person:,.0f}")
    status = "🔴 要対応" if gp_per_person >= 2_000_000 else ("🟡 注意" if gp_per_person < gpp_warn else "🟢 正常")
    st.markdown(f"ステータス: {status} | 閾値: ¥{gpp_warn:,}")

with col3:
    st.markdown("**成約率**")
    st.markdown(f"### {close_rate:.1f}%")
    cr_status = "🟡 注意" if close_rate < cr_warn else "🟢 正常"
    st.markdown(f"ステータス: {cr_status} | 閾値: {cr_warn}%")

st.markdown("---")
kpi_table = pd.DataFrame([
    {"指標": "月次粗利", "当月": f"¥{gp_this:,.0f}", "前年同月": f"¥{gp_last:,.0f}",
     "YoY変化": f"{gp_yoy_pct:+.1f}%", "他支店平均": f"¥{gp_all_avg:,.0f}", "判定": "🟢" if gp_yoy_pct >= 0 else "🟡"},
    {"指標": "仕入契約", "当月": f"{buy_cnt}件", "前年同月": "-", "YoY変化": "-", "他支店平均": "-", "判定": "🟢"},
    {"指標": "仲介契約", "当月": f"{med_cnt}件", "前年同月": "-", "YoY変化": "-", "他支店平均": "-", "判定": "🟢"},
    {"指標": "売却契約", "当月": f"{sell_cnt}件", "前年同月": "-", "YoY変化": "-", "他支店平均": "-", "判定": "🟢"},
    {"指標": "成約率", "当月": f"{close_rate:.1f}%", "前年同月": "-", "YoY変化": "-", "他支店平均": "-",
     "判定": "🟢" if close_rate >= cr_warn else "🟡"},
    {"指標": "1人当たり粗利", "当月": f"¥{gp_per_person:,.0f}", "前年同月": "-", "YoY変化": "-", "他支店平均": "-",
     "判定": "🔴" if gp_per_person >= 2_000_000 else ("🟡" if gp_per_person < gpp_warn else "🟢")},
    {"指標": "サンタメ比率", "当月": f"{santame_pct:.1f}%", "前年同月": "-", "YoY変化": "-",
     "他支店平均": "-", "判定": "🟡" if santame_pct < st_lo or santame_pct > st_hi else "🟢"},
    {"指標": f"長期滞留在庫（{inv_warn}日超）", "当月": f"{long_cnt}件", "前年同月": "-",
     "YoY変化": "-", "他支店平均": "-", "判定": "🔴" if long_cnt >= 3 else ("🟡" if long_cnt > 0 else "🟢")},
])
st.dataframe(kpi_table, use_container_width=True, hide_index=True)

# ── 中段: 要注意メンバー ──────────────────────────────────────
st.markdown("## 👥 要注意メンバー（上位3名）")

営業 = 社員[(社員["現在支店ID"] == branch_id) & (社員["職種"] == "営業")]
member_rows = []
for _, emp in 営業.iterrows():
    eid = emp["社員ID"]
    k_e = 契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == ym)]
    a_e = 案件[(案件["登録担当社員ID"] == eid) & (案件["年月"] == ym)]
    gp_e = int(k_e["粗利_確定"].sum())
    cr_e = (a_e["成約フラグ"].sum() / len(a_e) * 100) if len(a_e) > 0 else 0
    score = (1 if gp_e < gpp_warn else 0) + (1 if cr_e < cr_warn else 0)
    member_rows.append({
        "氏名": emp["氏名"],
        "月次粗利": gp_e,
        "成約率(%)": round(cr_e, 1),
        "要注意スコア": score,
        "Next Action": (
            f"粗利 ¥{gp_e:,} が閾値を下回り。情報源ミックスを確認" if gp_e < gpp_warn else
            f"成約率 {cr_e:.1f}% が低下。失注理由の傾向を確認" if cr_e < cr_warn else
            "異常なし"
        ),
    })

df_watch = pd.DataFrame(member_rows).sort_values("要注意スコア", ascending=False).head(3)
st.dataframe(
    df_watch[["氏名", "月次粗利", "成約率(%)", "Next Action"]].assign(
        月次粗利=lambda d: d["月次粗利"].apply(lambda x: f"¥{x:,}")
    ),
    use_container_width=True, hide_index=True,
)

# ── 下段: 本部報告事項 ────────────────────────────────────────
st.markdown("## 📝 本部報告事項・今月のコミットメント")

col_a, col_b = st.columns(2)
with col_a:
    report = st.text_area("報告事項", height=150,
                          placeholder="例）リフォーム再販物件の滞留が増加傾向。工務店との連携強化を実施中。")
with col_b:
    commit = st.text_area("今月のコミットメント", height=150,
                           placeholder="例）粗利目標：¥1,800万達成。長期滞留2件の値下げ交渉を今月中に完了。")

st.markdown("---")

# ── ダウンロード ──────────────────────────────────────────────
st.markdown("## 💾 エクスポート")

export_md = f"""# 本部月次レビュー — {branch_name} / {ym}

## 主要 KPI
| 指標 | 当月 | 判定 |
|------|------|------|
| 月次粗利 | ¥{gp_this:,} ({gp_yoy_pct:+.1f}% YoY) | {"🟢" if gp_yoy_pct >= 0 else "🟡"} |
| 1人当たり粗利 | ¥{gp_per_person:,} | {"🔴 増員検討" if gp_per_person >= 2_000_000 else "🟡 注意" if gp_per_person < gpp_warn else "🟢"} |
| 成約率 | {close_rate:.1f}% | {"🟢" if close_rate >= cr_warn else "🟡"} |
| 長期滞留在庫 | {long_cnt}件 | {"🔴" if long_cnt >= 3 else "🟡" if long_cnt > 0 else "🟢"} |

## 要注意メンバー
{chr(10).join(f"- **{r['氏名']}**: {r['Next Action']}" for _, r in df_watch[["氏名", "Next Action"]].iterrows())}

## 報告事項
{report if report else "（未記入）"}

## コミットメント
{commit if commit else "（未記入）"}

---
*閾値は仮置き（ヒアリング前）。thresholds.yaml で管理。*
"""

st.download_button(
    label="📥 Markdown でダウンロード",
    data=export_md.encode("utf-8"),
    file_name=f"review_{branch_name}_{ym}.md",
    mime="text/markdown",
)

# CSV エクスポート
csv_buf = io.StringIO()
kpi_table.to_csv(csv_buf, index=False, encoding="utf-8-sig")
st.download_button(
    label="📥 KPI サマリー CSV でダウンロード",
    data=csv_buf.getvalue().encode("utf-8-sig"),
    file_name=f"kpi_{branch_name}_{ym}.csv",
    mime="text/csv",
)
