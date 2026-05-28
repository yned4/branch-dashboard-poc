"""GET /api/exit-analysis — 売却出口分析（画面4）"""
import pandas as pd
from fastapi import APIRouter, Query
from typing import List, Optional
from services.data import load_data, yoy_ym
from services.thresholds import load as load_thresholds, check_breach, make_alert

router = APIRouter()


@router.get("/exit-analysis")
def get_exit_analysis(
    branch_id: int = Query(...),
    start_ym: str = Query(...),
    end_ym: str = Query(...),
    sel_exit: Optional[List[str]] = Query(default=None),
    sel_corp: Optional[List[str]] = Query(default=None),
):
    dfs = load_data()
    cfg = load_thresholds()

    契約 = dfs["契約"]
    出口 = dfs["出口"]
    物件 = dfs["物件"]
    支店 = dfs["支店"]

    # デフォルト値（全選択）
    all_exit = 出口["現況再販区分"].dropna().unique().tolist() if "現況再販区分" in 出口.columns else []
    all_corp = 出口["法人個人区分"].dropna().unique().tolist() if "法人個人区分" in 出口.columns else []
    if not sel_exit:
        sel_exit = all_exit
    if not sel_corp:
        sel_corp = all_corp

    months = [
        str(p)
        for p in pd.period_range(
            start=pd.Period(start_ym, "M"), end=pd.Period(end_ym, "M"), freq="M"
        )
    ]
    ym = months[-1] if months else end_ym

    baikyaku_self = (
        契約[
            (契約["契約時点支店ID"] == branch_id)
            & (契約["契約種別"] == "売却")
        ]
        .merge(出口, on="出口ID", how="left")
    )
    baikyaku_self = baikyaku_self[
        baikyaku_self["現況再販区分"].isin(sel_exit)
        & baikyaku_self["法人個人区分"].isin(sel_corp)
    ]

    baikyaku_month = baikyaku_self[baikyaku_self["年月"] == ym]
    baikyaku_ly = baikyaku_self[baikyaku_self["年月"] == yoy_ym(ym)]
    baikyaku_all = 契約[契約["契約種別"] == "売却"].merge(出口, on="出口ID", how="left")
    baikyaku_all_month = baikyaku_all[baikyaku_all["年月"] == ym]

    dev_warn = cfg["exit_composition"]["legal_individual_deviation_pct"]["value"]
    dev_warn2 = cfg["exit_composition"]["current_resale_deviation_pct"]["value"]

    # ── 2-1 法人・個人 売却先割合（3パターン） ──
    def pie_counts(df, col):
        if df.empty or col not in df.columns:
            return []
        cnt = df[col].value_counts().reset_index()
        cnt.columns = [col, "件数"]
        return cnt.to_dict("records")

    corp_pie_this = pie_counts(baikyaku_month, "法人個人区分")
    corp_pie_ly = pie_counts(baikyaku_ly, "法人個人区分")
    corp_pie_all = pie_counts(baikyaku_all_month, "法人個人区分")

    # ── 2-2 現況・再販 割合推移（過去12ヶ月） ──
    bk_12 = baikyaku_self[baikyaku_self["年月"].isin(months)]
    trend_data = []
    if not bk_12.empty:
        trend = bk_12.groupby(["年月", "現況再販区分"]).size().reset_index(name="件数")
        trend_data = trend.to_dict("records")

    # ── 2-3 リフォーム再販 平均粗利（支店比較） ──
    resale_gp = 契約[契約["契約種別"] == "売却"].merge(出口, on="出口ID", how="left")
    resale_gp_12 = resale_gp[
        (resale_gp["現況再販区分"] == "再販") & resale_gp["年月"].isin(months)
    ].merge(支店[["支店ID", "支店名"]], left_on="契約時点支店ID", right_on="支店ID", how="left")

    branch_gp_data = []
    if not resale_gp_12.empty:
        gp_by_branch = (
            resale_gp_12.groupby("支店名")["粗利_確定"].mean().reset_index()
        )
        gp_by_branch.columns = ["支店名", "平均粗利"]
        gp_by_branch["is_self"] = gp_by_branch["支店名"].apply(
            lambda n: n == 支店[支店["支店ID"] == branch_id]["支店名"].values[0]
            if len(支店[支店["支店ID"] == branch_id]) > 0
            else False
        )
        branch_gp_data = (
            gp_by_branch.sort_values("平均粗利", ascending=True)
            .where(gp_by_branch.notna(), None)
            .to_dict("records")
        )

    # ── 2-4 リフォーム再販 平均売却日数 ──
    inv_warn = cfg["inventory_turnover_days"]["warning"]["value"]
    inv_crit = cfg["inventory_turnover_days"]["critical"]["value"]

    物件_resale = 物件.merge(
        契約[契約["契約種別"] == "売却"]
        .merge(出口, on="出口ID", how="left")[["物件ID", "現況再販区分", "契約時点支店ID"]],
        on="物件ID",
        how="inner",
    )
    物件_resale = 物件_resale[物件_resale["現況再販区分"] == "再販"].dropna(subset=["在庫日数"])

    avg_days = None
    med_days = None
    hist_data = []
    if not 物件_resale.empty:
        self_days = 物件_resale[物件_resale["契約時点支店ID"] == branch_id]["在庫日数"]
        if not self_days.empty:
            avg_days = float(self_days.mean())
            med_days = float(self_days.median())

        # ヒストグラム用データ（支店ラベル付き）
        hist_df = 物件_resale[["在庫日数", "契約時点支店ID"]].copy()
        hist_df["is_self"] = hist_df["契約時点支店ID"] == branch_id
        hist_data = hist_df.where(hist_df.notna(), None).to_dict("records")

    # ── アラート ──
    alerts = []

    if not baikyaku_month.empty and not baikyaku_all_month.empty:
        self_corp = float((baikyaku_month["法人個人区分"] == "法人").mean() * 100)
        all_corp = float((baikyaku_all_month["法人個人区分"] == "法人").mean() * 100)
        if abs(self_corp - all_corp) > dev_warn:
            alerts.append(
                make_alert(
                    "warning",
                    f"法人/個人比率が全支店平均から {abs(self_corp-all_corp):.1f}% 乖離しています（閾値 {dev_warn}%）。市況変化か特定営業手法への偏りがないか確認してください。",
                )
            )

        self_resale = float((baikyaku_month["現況再販区分"] == "再販").mean() * 100)
        all_resale = float((baikyaku_all_month["現況再販区分"] == "再販").mean() * 100)
        if abs(self_resale - all_resale) > dev_warn2:
            alerts.append(
                make_alert(
                    "warning",
                    f"現況/再販比率が全支店平均から {abs(self_resale-all_resale):.1f}% 乖離しています（閾値 {dev_warn2}%）。粗利率と資金繰りへの影響を確認してください。",
                )
            )

    if avg_days is not None:
        level, _ = check_breach(
            avg_days,
            {
                "direction": "higher_is_bad",
                "warning": {"value": inv_warn},
                "critical": {"value": inv_crit},
            },
        )
        if level != "ok":
            alerts.append(
                make_alert(
                    level,
                    f"リフォーム再販の平均売却日数が {avg_days:.0f}日 です（警告：{inv_warn}日超）。工事遅延か販売長期化か、ボトルネックを特定してください。",
                )
            )

    return {
        "corp_pie_this": corp_pie_this,
        "corp_pie_ly": corp_pie_ly,
        "corp_pie_all": corp_pie_all,
        "resale_trend": trend_data,
        "branch_gp": branch_gp_data,
        "avg_days": avg_days,
        "med_days": med_days,
        "days_histogram": hist_data,
        "thresholds": {"inv_warn": inv_warn, "inv_crit": inv_crit, "dev_warn": dev_warn},
        "alerts": alerts,
    }
