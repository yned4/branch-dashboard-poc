"""GET /api/members — メンバートラッカー（画面2）"""
import pandas as pd
from fastapi import APIRouter, Query
from backend.services.data import load_data, yoy_ym
from backend.services.thresholds import load as load_thresholds, make_alert

router = APIRouter()


@router.get("/members")
def get_members(
    branch_id: int = Query(...),
    ym: str = Query(...),
):
    dfs = load_data()
    cfg = load_thresholds()

    社員 = dfs["社員"]
    契約 = dfs["契約"]
    案件 = dfs["案件"]

    gpp_warn = cfg["gross_profit_per_person"]["warning_q1"]["value"]
    cr_warn = cfg["closing_rate"]["warning_q1"]["value"]

    営業 = 社員[
        (社員["現在支店ID"] == branch_id) & (社員["職種"] == "営業")
    ].copy()
    営業["経過月数"] = (
        (pd.Timestamp(ym + "-01") - 営業["入社年月"]).dt.days / 30
    ).astype(int)

    rows = []
    for _, emp in 営業.iterrows():
        eid = emp["社員ID"]
        k_this = 契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == ym)]
        k_last = 契約[(契約["契約担当社員ID"] == eid) & (契約["年月"] == yoy_ym(ym))]
        a_this = 案件[(案件["登録担当社員ID"] == eid) & (案件["年月"] == ym)]

        gp = int(k_this["粗利_確定"].sum())
        gp_ly = int(k_last["粗利_確定"].sum())
        cnt = int(len(k_this[k_this["契約種別"].isin(["買取", "仲介"])]))
        cr = float(
            a_this["成約フラグ"].sum() / len(a_this) * 100 if len(a_this) > 0 else 0.0
        )

        rows.append(
            {
                "社員ID": int(eid),
                "氏名": emp["氏名"],
                "入社年月": emp["入社年月"].strftime("%Y-%m"),
                "経過月数": int(emp["経過月数"]),
                "雇用形態": str(emp.get("現在雇用形態", "")),
                "出身業種": str(emp.get("出身業種", "")),
                "契約件数": cnt,
                "粗利_確定": gp,
                "粗利_前年": gp_ly,
                "成約率": round(cr, 1),
            }
        )

    df_member = pd.DataFrame(rows)

    # ── コホート別粗利推移（過去12ヶ月） ──
    months_12 = [
        str(p)
        for p in pd.period_range(end=pd.Period(ym, freq="M"), periods=12, freq="M")
    ]
    cohort_rows = []
    for _, emp in 営業.iterrows():
        eid = emp["社員ID"]
        hire_yr = emp["入社年月"].year
        for m in months_12:
            gp_m = int(
                契約[
                    (契約["契約担当社員ID"] == eid) & (契約["年月"] == m)
                ]["粗利_確定"].sum()
            )
            cohort_rows.append({"年月": m, "入社年": hire_yr, "粗利_確定": gp_m})

    cohort_data = []
    if cohort_rows:
        df_cohort = (
            pd.DataFrame(cohort_rows)
            .groupby(["年月", "入社年"])["粗利_確定"]
            .mean()
            .reset_index()
        )
        df_cohort["入社年"] = df_cohort["入社年"].astype(str) + "年入社"
        cohort_data = df_cohort.where(df_cohort.notna(), None).to_dict("records")

    # ── アラート ──
    alerts = []
    if not df_member.empty:
        attention = df_member[df_member["粗利_確定"] < gpp_warn]
        if not attention.empty:
            names = "、".join(attention["氏名"].tolist())
            alerts.append(
                make_alert(
                    "warning",
                    f"{names} の月次粗利が ¥{gpp_warn:,} を下回っています。情報源ミックスの偏りと案件パイプラインを確認してください。",
                )
            )

    member_list = (
        df_member.where(df_member.notna(), None).to_dict("records")
        if not df_member.empty
        else []
    )

    return {
        "members": member_list,
        "cohort_data": cohort_data,
        "thresholds": {"gpp_warn": gpp_warn, "cr_warn": cr_warn},
        "alerts": alerts,
    }
