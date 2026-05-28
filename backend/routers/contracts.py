"""GET /api/contracts — 契約・在庫分析（画面5）"""
import pandas as pd
from fastapi import APIRouter, Query
from typing import List, Optional
from backend.services.data import load_data, headcount_coefficient
from backend.services.thresholds import load as load_thresholds, check_breach, make_alert

router = APIRouter()


@router.get("/contracts")
def get_contracts(
    branch_id: int = Query(...),
    start_ym: str = Query(...),
    end_ym: str = Query(...),
    sel_keiyaku_types: Optional[List[str]] = Query(default=None),
    sel_prop_types: Optional[List[str]] = Query(default=None),
    sel_areas: Optional[List[str]] = Query(default=None),
):
    dfs = load_data()
    cfg = load_thresholds()

    契約 = dfs["契約"]
    物件 = dfs["物件"]
    支店_all = dfs["支店"]

    # デフォルト値
    all_keiyaku = 契約["契約種別"].dropna().unique().tolist()
    all_prop = 物件["種別"].dropna().unique().tolist() if "種別" in 物件.columns else []
    all_areas = 物件["エリア"].dropna().unique().tolist() if "エリア" in 物件.columns else []
    if not sel_keiyaku_types:
        sel_keiyaku_types = all_keiyaku
    if not sel_prop_types:
        sel_prop_types = all_prop
    if not sel_areas:
        sel_areas = all_areas

    months = [
        str(p)
        for p in pd.period_range(
            start=pd.Period(start_ym, "M"), end=pd.Period(end_ym, "M"), freq="M"
        )
    ]
    ym = months[-1] if months else end_ym

    k_self = 契約[契約["契約時点支店ID"] == branch_id]
    k_month = k_self[k_self["年月"] == ym]
    k_12 = k_self[k_self["年月"].isin(months)]
    k_all_month = 契約[契約["年月"] == ym]

    inv_warn = cfg["inventory_turnover_days"]["warning"]["value"]
    inv_crit = cfg["inventory_turnover_days"]["critical"]["value"]
    gpp_warn = cfg["gross_profit_per_person"]["warning_q1"]["value"]
    st_lo = cfg["santame_ratio"]["normal_range"]["lower_pct"]["value"]
    st_hi = cfg["santame_ratio"]["normal_range"]["upper_pct"]["value"]
    cim_warn = cfg["cash_invested_margin"]["warning_q1"]["value"]

    # ── 3-1 買取・仲介比率 ──
    def type_ratio(df_k):
        total = len(df_k[df_k["契約種別"].isin(["買取", "仲介"])])
        if total == 0:
            return 0.0, 0.0
        buy = len(df_k[df_k["契約種別"] == "買取"])
        med = len(df_k[df_k["契約種別"] == "仲介"])
        return float(buy / total * 100), float(med / total * 100)

    buy_pct, med_pct = type_ratio(k_month)
    buy_pct_all, med_pct_all = type_ratio(k_all_month)

    # 推移
    trend = k_12.groupby(["年月", "契約種別"]).size().reset_index(name="件数")
    trend = trend[trend["契約種別"].isin(["買取", "仲介"])]
    trend_data = trend.to_dict("records")

    # 契約種別全体推移
    cnt_trend = k_12.groupby(["年月", "契約種別"]).size().reset_index(name="件数")
    cnt_trend_data = cnt_trend.to_dict("records")

    # ── 3-2 サンタメ比率 ──
    santame_pct = float(k_month["サンタメフラグ"].mean() * 100) if len(k_month) > 0 else 0.0
    santame_level = "ok"
    if santame_pct < st_lo or santame_pct > st_hi:
        santame_level = "warning"

    # ── 3-4/3-5 支店別 1人当たり契約数・粗利 ──
    rows_branch = []
    for _, b in 支店_all.iterrows():
        bid = b["支店ID"]
        k_b = 契約[(契約["契約時点支店ID"] == bid) & (契約["年月"] == ym)]
        hc = headcount_coefficient(dfs, bid, cfg)
        total_gp = float(k_b["粗利_確定"].sum())
        total_cnt = int(len(k_b[k_b["契約種別"].isin(["買取", "仲介"])]))
        rows_branch.append(
            {
                "支店名": b["支店名"],
                "1人当たり粗利": round(total_gp / hc) if hc > 0 else 0,
                "1人当たり契約数": round(total_cnt / hc, 2) if hc > 0 else 0,
                "is_self": bool(bid == branch_id),
            }
        )

    self_gpp = next(
        (r["1人当たり粗利"] for r in rows_branch if r["is_self"]), 0
    )

    # ── 3-6 在庫回転日数 ──
    buk_self = 物件[(物件["取得支店ID"] == branch_id)].dropna(subset=["在庫日数"])
    inv_days_stats = {}
    inv_hist_data = []
    if not buk_self.empty:
        inv_days_stats = {
            "中央値": float(buk_self["在庫日数"].median()),
            "平均": float(buk_self["在庫日数"].mean()),
        }
        # histogram bins
        inv_hist_data = buk_self[["在庫日数"]].to_dict("records")

    # ── 3-7 在庫回転金額 ──
    sold_12 = 物件[(物件["取得支店ID"] == branch_id) & 物件["売却日"].notna()].copy()
    sold_12["売却年月"] = sold_12["売却日"].dt.to_period("M").astype(str)
    sold_12 = sold_12[sold_12["売却年月"].isin(months)]
    cogs = float(sold_12["取得価格"].sum())

    unsold = 物件[(物件["取得支店ID"] == branch_id) & 物件["売却日"].isna()]
    avg_inv_val = float(unsold["取得価格"].mean()) if len(unsold) > 0 else 0.0
    turnover_rate = float(cogs / (avg_inv_val * 12)) if avg_inv_val > 0 else 0.0

    # ── 3-8 現金投下粗利率 ──
    k_baitori = k_12[k_12["契約種別"] == "買取"].dropna(subset=["投下現金額"])
    k_baitori = k_baitori[k_baitori["投下現金額"] > 0]
    cim_avg = None
    cim_med = None
    if not k_baitori.empty:
        売却 = k_self[(k_self["契約種別"] == "売却") & k_self["年月"].isin(months)]
        gp_per_anken = (
            売却.groupby("案件ID")["粗利_確定"].sum().reset_index()
        )
        k_merged = k_baitori.merge(
            gp_per_anken, on="案件ID", how="left", suffixes=("_buy", "_sell")
        )
        k_merged["粗利_確定_sell"] = k_merged["粗利_確定_sell"].fillna(0)
        k_merged["現金投下粗利率"] = (
            k_merged["粗利_確定_sell"] / k_merged["投下現金額"] * 100
        )
        cim_avg = float(k_merged["現金投下粗利率"].mean())
        cim_med = float(k_merged["現金投下粗利率"].median())

    # ── 3-9 買取契約〜決済リードタイム ──
    k_buy_lt = k_12[(k_12["契約種別"] == "買取") & k_12["決済日"].notna()].copy()
    k_buy_lt["リードタイム"] = (k_buy_lt["決済日"] - k_buy_lt["契約日"]).dt.days
    lt_avg = None
    lt_med = None
    lt_hist_data = []
    if not k_buy_lt.empty:
        lt_avg = float(k_buy_lt["リードタイム"].mean())
        lt_med = float(k_buy_lt["リードタイム"].median())
        lt_hist_data = k_buy_lt[["リードタイム"]].to_dict("records")

    # ── 3-10 種別・エリア別 在庫回転日数 × 粗利率 ──
    by_type_data = []
    by_type_area_data = []
    buk_w_gp = 物件[
        (物件["取得支店ID"] == branch_id)
        & (物件["種別"].isin(sel_prop_types))
        & (物件["エリア"].isin(sel_areas))
    ].dropna(subset=["在庫日数", "売却価格", "取得価格"]).copy()
    buk_w_gp["粗利率(%)"] = (
        (buk_w_gp["売却価格"] - buk_w_gp["取得価格"]) / buk_w_gp["取得価格"] * 100
    )
    if not buk_w_gp.empty:
        by_type = (
            buk_w_gp.groupby("種別")
            .agg(
                平均在庫日数=("在庫日数", "mean"),
                中央値在庫日数=("在庫日数", "median"),
                平均粗利率=("粗利率(%)", "mean"),
                件数=("物件ID", "count"),
            )
            .reset_index()
        )
        by_type_data = by_type.where(by_type.notna(), None).to_dict("records")

        by_type_area = (
            buk_w_gp.groupby(["種別", "エリア"])
            .agg(
                平均在庫日数=("在庫日数", "mean"),
                平均粗利率=("粗利率(%)", "mean"),
                件数=("物件ID", "count"),
            )
            .reset_index()
        )
        by_type_area_data = by_type_area.where(by_type_area.notna(), None).to_dict("records")

    # ── 3-11 長期滞留在庫 ──
    today_approx = pd.Timestamp(ym + "-01") + pd.offsets.MonthEnd(0)
    unsold_all = 物件[(物件["取得支店ID"] == branch_id) & 物件["売却日"].isna()].copy()
    unsold_all["現在保有日数"] = (today_approx - unsold_all["取得日"]).dt.days
    long_inv_val = 0.0
    total_inv_val = 0.0
    long_pct = 0.0
    if not unsold_all.empty:
        long_inv_val = float(unsold_all[unsold_all["現在保有日数"] > inv_warn]["取得価格"].sum())
        total_inv_val = float(unsold_all["取得価格"].sum())
        long_pct = float(long_inv_val / total_inv_val * 100) if total_inv_val > 0 else 0.0

    # ── アラート ──
    alerts = []

    if santame_level != "ok":
        alerts.append(
            make_alert(
                "warning",
                f"サンタメ比率が {santame_pct:.1f}% と正常レンジ（{st_lo}〜{st_hi}%）から逸脱しています。契約スキームの構成を確認してください。",
            )
        )

    if self_gpp >= 2_000_000:
        alerts.append(
            make_alert(
                "critical",
                f"1人当たり粗利が ¥{self_gpp:,.0f} で200万円を超過しています。支店のキャパシティ上限に達している可能性が高いため、新規採用・増員計画をスケジュールしてください。",
            )
        )
    elif self_gpp < gpp_warn:
        alerts.append(
            make_alert(
                "warning",
                f"1人当たり粗利が ¥{self_gpp:,.0f} と閾値 ¥{gpp_warn:,} を下回っています。業務効率化や人員スキル底上げを検討してください。",
            )
        )

    if buk_self is not None and not buk_self.empty:
        long_cnt_inv = int((buk_self["在庫日数"] > inv_warn).sum())
        if long_cnt_inv > 0:
            alerts.append(
                make_alert(
                    "warning",
                    f"在庫日数 {inv_warn}日超の物件が {long_cnt_inv} 件あります。価格見直しか出口戦略変更を検討してください。",
                )
            )

    if cim_avg is not None:
        level_cim, _ = check_breach(
            cim_avg, {"direction": "lower_is_bad", "value": cim_warn}
        )
        if level_cim != "ok":
            alerts.append(
                make_alert(
                    "warning",
                    f"現金投下粗利率が {cim_avg:.1f}% と閾値 {cim_warn}% を下回っています。仕入価格の妥当性と融資レバレッジの活用状況を確認してください。",
                )
            )

    if lt_avg is not None:
        if lt_avg > 90:
            alerts.append(
                make_alert(
                    "critical",
                    f"買取契約〜決済リードタイムが平均 {lt_avg:.0f}日 です（要対応 90日超）。法務・金融手続きの停滞要因を特定し早期解消を図ってください。",
                )
            )
        elif lt_avg > 60:
            alerts.append(
                make_alert(
                    "warning",
                    f"買取契約〜決済リードタイムが平均 {lt_avg:.0f}日 です（警告 60日超）。停滞要因を確認してください。",
                )
            )

    if long_pct > 20:
        level_li = "critical" if long_pct > 30 else "warning"
        alerts.append(
            make_alert(
                level_li,
                f"{inv_warn}日超の長期滞留在庫が全在庫の {long_pct:.1f}% を占めています。対象物件の価格改定または損切りを経営判断として早急に実施してください。",
            )
        )

    return {
        "type_ratio": {
            "self": {"買取": round(buy_pct, 1), "仲介": round(med_pct, 1)},
            "all": {"買取": round(buy_pct_all, 1), "仲介": round(med_pct_all, 1)},
        },
        "trend": trend_data,
        "cnt_trend": cnt_trend_data,
        "santame": {
            "pct": round(santame_pct, 1),
            "level": santame_level,
            "range": {"lower": st_lo, "upper": st_hi},
        },
        "branch_comparison": rows_branch,
        "inv_days": inv_days_stats,
        "inv_hist": inv_hist_data,
        "turnover_rate": round(turnover_rate, 2),
        "cim": {"avg": cim_avg, "median": cim_med},
        "leadtime": {"avg": lt_avg, "median": lt_med},
        "lt_hist": lt_hist_data,
        "by_type": by_type_data,
        "by_type_area": by_type_area_data,
        "long_inventory": {
            "long_val": round(long_inv_val),
            "total_val": round(total_inv_val),
            "long_pct": round(long_pct, 1),
        },
        "thresholds": {
            "inv_warn": inv_warn,
            "inv_crit": inv_crit,
            "gpp_warn": gpp_warn,
            "cim_warn": cim_warn,
        },
        "alerts": alerts,
    }
