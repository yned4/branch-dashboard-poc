"""GET /api/export — レビュー会用エクスポートサマリー（画面7）"""
import pandas as pd
from fastapi import APIRouter, Query
from backend.services.data import load_data, yoy_ym, headcount_coefficient
from backend.services.thresholds import load as load_thresholds

router = APIRouter()


@router.get("/export")
def get_export(
    branch_id: int = Query(...),
    ym: str = Query(...),
):
    dfs = load_data()
    cfg = load_thresholds()

    契約 = dfs["契約"]
    案件 = dfs["案件"]
    物件 = dfs["物件"]
    社員 = dfs["社員"]
    支店 = dfs["支店"]

    branch_row = 支店[支店["支店ID"] == branch_id]
    branch_name = branch_row["支店名"].values[0] if not branch_row.empty else str(branch_id)

    k_self = 契約[契約["契約時点支店ID"] == branch_id]
    k_month = k_self[k_self["年月"] == ym]
    k_last = k_self[k_self["年月"] == yoy_ym(ym)]
    k_all_month = 契約[契約["年月"] == ym]

    a_self = 案件[案件["登録時点支店ID"] == branch_id]
    a_month = a_self[a_self["年月"] == ym]

    hc = headcount_coefficient(dfs, branch_id, cfg)

    gp_this = int(k_month["粗利_確定"].sum())
    gp_last = int(k_last["粗利_確定"].sum())
    gp_all_avg = int(k_all_month.groupby("契約時点支店ID")["粗利_確定"].sum().mean()) if not k_all_month.empty else 0
    gp_yoy_pct = float((gp_this - gp_last) / gp_last * 100) if gp_last > 0 else 0.0
    gp_per_person = float(gp_this / hc) if hc > 0 else 0.0

    buy_cnt = int(len(k_month[k_month["契約種別"] == "買取"]))
    med_cnt = int(len(k_month[k_month["契約種別"] == "仲介"]))
    sell_cnt = int(len(k_month[k_month["契約種別"] == "売却"]))

    close_rate = float(
        a_month["成約フラグ"].sum() / len(a_month) * 100 if len(a_month) > 0 else 0.0
    )
    santame_pct = float(k_month["サンタメフラグ"].mean() * 100) if len(k_month) > 0 else 0.0

    today_approx = pd.Timestamp(ym + "-01") + pd.offsets.MonthEnd(0)
    unsold = 物件[(物件["取得支店ID"] == branch_id) & 物件["売却日"].isna()].copy()
    unsold["現在保有日数"] = (today_approx - unsold["取得日"]).dt.days
    inv_warn = cfg["inventory_turnover_days"]["warning"]["value"]
    long_cnt = int((unsold["現在保有日数"] > inv_warn).sum())

    gpp_warn = cfg["gross_profit_per_person"]["warning_q1"]["value"]
    cr_warn = cfg["closing_rate"]["warning_q1"]["value"]
    st_lo = cfg["santame_ratio"]["normal_range"]["lower_pct"]["value"]
    st_hi = cfg["santame_ratio"]["normal_range"]["upper_pct"]["value"]

    # ── 要注意メンバー ──
    営業 = 社員[(社員["現在支店ID"] == branch_id) & (社員["職種"] == "営業")]
    member_rows = []
    for _, emp in 営業.iterrows():
        eid = emp["社員ID"]
        k_e = 契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == ym)]
        a_e = 案件[(案件["登録担当社員ID"] == eid) & (案件["年月"] == ym)]
        gp_e = int(k_e["粗利_確定"].sum())
        cr_e = float(
            a_e["成約フラグ"].sum() / len(a_e) * 100 if len(a_e) > 0 else 0.0
        )
        score = (1 if gp_e < gpp_warn else 0) + (1 if cr_e < cr_warn else 0)
        member_rows.append(
            {
                "氏名": emp["氏名"],
                "月次粗利": gp_e,
                "成約率(%)": round(cr_e, 1),
                "要注意スコア": score,
                "Next Action": (
                    f"粗利 ¥{gp_e:,} が閾値を下回り。情報源ミックスを確認"
                    if gp_e < gpp_warn
                    else (
                        f"成約率 {cr_e:.1f}% が低下。失注理由の傾向を確認"
                        if cr_e < cr_warn
                        else "異常なし"
                    )
                ),
            }
        )

    watch_members = (
        sorted(member_rows, key=lambda r: r["要注意スコア"], reverse=True)[:3]
    )

    # KPI テーブル
    kpi_table = [
        {
            "指標": "月次粗利",
            "当月": gp_this,
            "前年同月": gp_last,
            "YoY変化(%)": round(gp_yoy_pct, 1),
            "他支店平均": gp_all_avg,
            "判定": "ok" if gp_yoy_pct >= 0 else "warning",
        },
        {"指標": "仕入契約", "当月": buy_cnt, "前年同月": None, "YoY変化(%)": None, "他支店平均": None, "判定": "ok"},
        {"指標": "仲介契約", "当月": med_cnt, "前年同月": None, "YoY変化(%)": None, "他支店平均": None, "判定": "ok"},
        {"指標": "売却契約", "当月": sell_cnt, "前年同月": None, "YoY変化(%)": None, "他支店平均": None, "判定": "ok"},
        {
            "指標": "成約率(%)",
            "当月": round(close_rate, 1),
            "前年同月": None,
            "YoY変化(%)": None,
            "他支店平均": None,
            "判定": "ok" if close_rate >= cr_warn else "warning",
        },
        {
            "指標": "1人当たり粗利",
            "当月": round(gp_per_person),
            "前年同月": None,
            "YoY変化(%)": None,
            "他支店平均": None,
            "判定": "critical" if gp_per_person >= 2_000_000 else ("warning" if gp_per_person < gpp_warn else "ok"),
        },
        {
            "指標": "サンタメ比率(%)",
            "当月": round(santame_pct, 1),
            "前年同月": None,
            "YoY変化(%)": None,
            "他支店平均": None,
            "判定": "warning" if santame_pct < st_lo or santame_pct > st_hi else "ok",
        },
        {
            "指標": f"長期滞留在庫（{inv_warn}日超）",
            "当月": long_cnt,
            "前年同月": None,
            "YoY変化(%)": None,
            "他支店平均": None,
            "判定": "critical" if long_cnt >= 3 else ("warning" if long_cnt > 0 else "ok"),
        },
    ]

    return {
        "branch_name": branch_name,
        "ym": ym,
        "kpis": {
            "monthly_gp": gp_this,
            "monthly_gp_last": gp_last,
            "monthly_gp_all_avg": gp_all_avg,
            "gp_yoy_pct": round(gp_yoy_pct, 1),
            "gp_per_person": round(gp_per_person),
            "close_rate": round(close_rate, 1),
            "santame_pct": round(santame_pct, 1),
            "long_inv_cnt": long_cnt,
            "buy_cnt": buy_cnt,
            "med_cnt": med_cnt,
            "sell_cnt": sell_cnt,
        },
        "kpi_table": kpi_table,
        "watch_members": watch_members,
        "thresholds": {
            "gpp_warn": gpp_warn,
            "cr_warn": cr_warn,
            "st_lo": st_lo,
            "st_hi": st_hi,
            "inv_warn": inv_warn,
        },
    }
