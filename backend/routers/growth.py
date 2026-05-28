"""GET /api/growth — 成長分析（画面6）"""
import pandas as pd
from fastapi import APIRouter, Query
from typing import List, Optional
from services.data import load_data
from services.thresholds import load as load_thresholds, make_alert

router = APIRouter()


def _phase_label(opened: pd.Timestamp, ref: pd.Timestamp) -> str:
    months = int((ref - opened).days / 30)
    if months <= 12:
        return "新規出店（1年目）"
    elif months <= 36:
        return "成長期（2〜3年目）"
    return "成熟期（4年目〜）"


@router.get("/growth")
def get_growth(
    branch_id: int = Query(...),
    start_ym: str = Query(...),
    end_ym: str = Query(...),
    sel_industries: Optional[List[str]] = Query(default=None),
):
    dfs = load_data()
    cfg = load_thresholds()

    契約 = dfs["契約"]
    社員 = dfs["社員"]
    支店 = dfs["支店"]
    案件 = dfs["案件"]
    情報源 = dfs["情報源"]

    all_industries = 社員["出身業種"].dropna().unique().tolist() if "出身業種" in 社員.columns else []
    if not sel_industries:
        sel_industries = all_industries

    all_months = [
        str(p)
        for p in pd.period_range(
            start=pd.Period(start_ym, "M"), end=pd.Period(end_ym, "M"), freq="M"
        )
    ]
    ym = all_months[-1] if all_months else end_ym
    gpp_warn = cfg["gross_profit_per_person"]["warning_q1"]["value"]

    # ── 4-1 支店フェーズ ──
    ref_ts = pd.Timestamp(ym + "-01")
    branch_phases = []
    for _, b in 支店.iterrows():
        ph = _phase_label(b["開設年月"], ref_ts)
        elapsed_mo = int((ref_ts - b["開設年月"]).days / 30)
        branch_phases.append(
            {
                "支店ID": int(b["支店ID"]),
                "支店名": b["支店名"],
                "フェーズ": ph,
                "経過月数": elapsed_mo,
                "is_self": bool(b["支店ID"] == branch_id),
            }
        )

    # 月次粗利トレンド（全支店）
    branch_gp_rows = []
    for _, b in 支店.iterrows():
        bid = b["支店ID"]
        for m in all_months:
            gp = int(
                契約[(契約["契約時点支店ID"] == bid) & (契約["年月"] == m)][
                    "粗利_確定"
                ].sum()
            )
            branch_gp_rows.append(
                {
                    "支店名": b["支店名"],
                    "年月": m,
                    "月次粗利": gp,
                    "is_self": bool(bid == branch_id),
                }
            )

    # 全支店平均
    df_bt = pd.DataFrame(branch_gp_rows)
    avg_by_month = []
    if not df_bt.empty:
        avg = df_bt.groupby("年月")["月次粗利"].mean().reset_index()
        avg_by_month = avg.to_dict("records")

    branch_gp_trend = branch_gp_rows

    # ── 4-2 コホート成長分析 ──
    営業 = 社員[(社員["現在支店ID"] == branch_id) & (社員["職種"] == "営業")].copy()
    cohort_rows = []
    for _, emp in 営業.iterrows():
        eid = emp["社員ID"]
        hire = emp["入社年月"]
        hire_yr = str(hire.year) + "年入社"
        for m in all_months:
            elapsed = max(0, int((pd.Timestamp(m + "-01") - hire).days / 30))
            gp = int(
                契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == m)][
                    "粗利_確定"
                ].sum()
            )
            cohort_rows.append({"入社期": hire_yr, "経過月数": elapsed, "粗利_確定": gp})

    cohort_data = []
    if cohort_rows:
        df_cohort = (
            pd.DataFrame(cohort_rows)
            .groupby(["入社期", "経過月数"])["粗利_確定"]
            .mean()
            .reset_index()
        )
        cohort_data = df_cohort.where(df_cohort.notna(), None).to_dict("records")

    # ── 4-3 出身業種別 成長傾向 ──
    industry_rows = []
    for _, emp in 社員[
        (社員["職種"] == "営業") & (社員["出身業種"].isin(sel_industries))
    ].iterrows():
        eid = emp["社員ID"]
        hire = emp["入社年月"]
        for m in all_months:
            elapsed = max(0, int((pd.Timestamp(m + "-01") - hire).days / 30))
            if elapsed > 48:
                continue
            gp = int(
                契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == m)][
                    "粗利_確定"
                ].sum()
            )
            industry_rows.append(
                {"出身業種": emp["出身業種"], "経過月数": elapsed, "粗利_確定": gp}
            )

    industry_data = []
    if industry_rows:
        df_ind = (
            pd.DataFrame(industry_rows)
            .groupby(["出身業種", "経過月数"])["粗利_確定"]
            .mean()
            .reset_index()
        )
        industry_data = df_ind.where(df_ind.notna(), None).to_dict("records")

    # ── 4-4 成長フェーズ × 情報源ポートフォリオ ──
    dep_warn = cfg["info_source_efficiency"]["dependency_max_pct"]["value"]
    a_w = 案件[案件["登録時点支店ID"] == branch_id].copy()
    a_w = a_w.merge(
        社員[["社員ID", "入社年月"]].rename(columns={"社員ID": "登録担当社員ID"}),
        on="登録担当社員ID",
        how="left",
    )
    a_w = a_w.merge(情報源, on="情報源ID", how="left")
    a_w["経過月数"] = (
        (a_w["登録日"] - a_w["入社年月"]).dt.days / 30
    ).fillna(-1).astype(int)
    a_w = a_w[a_w["経過月数"] >= 0]
    a_w["経験年次"] = (
        (a_w["経過月数"] // 12 + 1).clip(upper=5).astype(str) + "年目"
    )

    tenure_src_data = []
    if not a_w.empty:
        tenure_src = (
            a_w.groupby(["経験年次", "情報源名"]).size().reset_index(name="案件数")
        )
        tenure_total = tenure_src.groupby("経験年次")["案件数"].transform("sum")
        tenure_src["割合(%)"] = (
            tenure_src["案件数"] / tenure_total * 100
        ).round(1)
        tenure_src_data = tenure_src.to_dict("records")

    # ── アラート ──
    alerts = []
    if tenure_src_data:
        df_ts = pd.DataFrame(tenure_src_data)
        for yr in df_ts["経験年次"].unique():
            yr_int = int(yr.replace("年目", ""))
            if yr_int < 2:
                continue
            top = df_ts[df_ts["経験年次"] == yr].sort_values("割合(%)", ascending=False)
            if not top.empty and top.iloc[0]["割合(%)"] > dep_warn:
                alerts.append(
                    make_alert(
                        "warning",
                        f"{yr} の「{top.iloc[0]['情報源名']}」依存度が {top.iloc[0]['割合(%)']:.1f}% と {dep_warn}% を超えています。より高粗利の情報源への開拓を指導してください。",
                    )
                )
                break

    return {
        "branch_phases": branch_phases,
        "branch_gp_trend": branch_gp_trend,
        "avg_by_month": avg_by_month,
        "cohort_data": cohort_data,
        "industry_data": industry_data,
        "tenure_src": tenure_src_data,
        "thresholds": {"gpp_warn": gpp_warn, "dep_warn": dep_warn},
        "alerts": alerts,
    }
