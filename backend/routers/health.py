"""GET /api/health — ヘルスチェック（画面1）"""
import pandas as pd
from fastapi import APIRouter, Query
from backend.services.data import load_data, yoy_ym, headcount_coefficient
from backend.services.thresholds import load as load_thresholds, check_breach, make_alert

router = APIRouter()


@router.get("/health")
def get_health(
    branch_id: int = Query(...),
    ym: str = Query(...),
):
    dfs = load_data()
    cfg = load_thresholds()

    契約 = dfs["契約"]
    案件 = dfs["案件"]

    ym_k = 契約[契約["契約時点支店ID"] == branch_id]
    this_month = ym_k[ym_k["年月"] == ym]
    last_year_ym = yoy_ym(ym)
    last_year = ym_k[ym_k["年月"] == last_year_ym]

    gp_this = int(this_month["粗利_確定"].sum())
    gp_last = int(last_year["粗利_確定"].sum())
    gp_delta_pct = float((gp_this - gp_last) / gp_last * 100) if gp_last > 0 else 0.0

    cnt_this = int(
        len(this_month[this_month["契約種別"] == "買取"])
        + len(this_month[this_month["契約種別"] == "仲介"])
    )
    cnt_last = int(
        len(last_year[last_year["契約種別"] == "買取"])
        + len(last_year[last_year["契約種別"] == "仲介"])
    )

    ym_a = 案件[案件["登録時点支店ID"] == branch_id]
    this_anken = ym_a[ym_a["年月"] == ym]
    close_rate = float(
        this_anken["成約フラグ"].sum() / len(this_anken) * 100
        if len(this_anken) > 0
        else 0.0
    )

    hc = headcount_coefficient(dfs, branch_id, cfg)
    gp_per_person = float(gp_this / hc) if hc > 0 else 0.0

    # ── 月次粗利トレンド（過去12ヶ月） ──
    months_12 = [
        str(p)
        for p in pd.period_range(end=pd.Period(ym, freq="M"), periods=12, freq="M")
    ]
    trend_data = []
    for m in months_12:
        gp_m = int(ym_k[ym_k["年月"] == m]["粗利_確定"].sum())
        trend_data.append({"年月": m, "月次粗利": gp_m})

    # ── アラート ──
    alerts = []

    gpp_cfg = cfg["gross_profit_per_person"]
    gpp_warn = gpp_cfg["warning_q1"]["value"]
    level_gpp, icon_gpp = check_breach(
        gp_per_person,
        {"direction": "lower_is_bad", "warning": {"value": gpp_warn}},
    )
    if level_gpp != "ok":
        alerts.append(
            make_alert(
                level_gpp,
                f"1人当たり粗利 ¥{gp_per_person:,.0f} → 閾値 ¥{gpp_warn:,} を下回っています。キャパシティまたはメンバー育成を確認してください。",
            )
        )

    cr_warn = cfg["closing_rate"]["warning_q1"]["value"]
    level_cr, _ = check_breach(
        close_rate,
        {"direction": "lower_is_bad", "warning": {"value": cr_warn}},
    )
    if level_cr != "ok":
        alerts.append(
            make_alert(
                level_cr,
                f"成約率 {close_rate:.1f}% → 閾値 {cr_warn}% を下回っています。失注理由と情報源ミックスを確認してください。",
            )
        )

    # 長期在庫
    inv_warn = cfg["inventory_turnover_days"]["warning"]["value"]
    today_approx = pd.Timestamp(ym + "-01") + pd.offsets.MonthEnd(0)
    unsold = dfs["物件"][
        (dfs["物件"]["取得支店ID"] == branch_id) & (dfs["物件"]["売却日"].isna())
    ].copy()
    unsold["現在保有日数"] = (today_approx - unsold["取得日"]).dt.days
    long_cnt = int((unsold["現在保有日数"] > inv_warn).sum())
    if long_cnt > 0:
        alerts.append(
            make_alert(
                "warning",
                f"長期滞留在庫（{inv_warn}日超）が {long_cnt} 件あります。価格見直しまたは出口戦略変更を検討してください。",
            )
        )

    return {
        "kpis": {
            "monthly_gp": gp_this,
            "monthly_gp_delta_pct": round(gp_delta_pct, 1),
            "contract_count": cnt_this,
            "contract_count_delta": cnt_this - cnt_last,
            "closing_rate": round(close_rate, 1),
            "gp_per_person": round(gp_per_person),
        },
        "trend_data": trend_data,
        "alerts": alerts,
    }
