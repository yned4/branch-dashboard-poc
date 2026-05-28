"""GET /api/info-source — 情報入口分析（画面3）"""
import pandas as pd
from fastapi import APIRouter, Query
from typing import List, Optional
from backend.services.data import load_data
from backend.services.thresholds import load as load_thresholds, make_alert

router = APIRouter()


@router.get("/info-source")
def get_info_source(
    branch_id: int = Query(...),
    start_ym: str = Query(...),
    end_ym: str = Query(...),
    sel_src: Optional[List[str]] = Query(default=None),
):
    dfs = load_data()
    cfg = load_thresholds()

    案件 = dfs["案件"]
    契約 = dfs["契約"]
    情報源 = dfs["情報源"]
    社員 = dfs["社員"]

    all_src = 情報源["情報源名"].dropna().unique().tolist()
    if not sel_src:
        sel_src = all_src

    months = [
        str(p)
        for p in pd.period_range(
            start=pd.Period(start_ym, "M"), end=pd.Period(end_ym, "M"), freq="M"
        )
    ]
    n_months = max(len(months), 1)

    a_self = 案件[案件["登録時点支店ID"] == branch_id].copy()
    a_self = a_self.merge(情報源, on="情報源ID", how="left")
    a_self = a_self[a_self["情報源名"].isin(sel_src)]

    end_ym_last = months[-1] if months else end_ym
    a_month = a_self[a_self["年月"] == end_ym_last].copy()

    a_12 = a_self[a_self["年月"].isin(months)]

    dep_warn = cfg["info_source_efficiency"]["dependency_max_pct"]["value"]

    # ── 1-1 情報源別 月間案件数 ──
    src_count = (
        a_12.groupby("情報源名").size().div(n_months).round(1).reset_index()
    )
    src_count.columns = ["情報源名", "月間平均案件数"]
    src_count_data = src_count.sort_values("月間平均案件数", ascending=True).to_dict("records")

    # 当月ポートフォリオ
    dep_data = []
    if not a_month.empty:
        dep = (
            a_month["情報源名"].value_counts(normalize=True).mul(100).reset_index()
        )
        dep.columns = ["情報源名", "依存度(%)"]
        dep_data = dep.to_dict("records")

    # ── 1-2/1-3 情報源別 成約率 & 平均粗利 ──
    a_joined = a_self.merge(
        契約[["案件ID", "粗利_確定"]]
        .groupby("案件ID")["粗利_確定"]
        .sum()
        .reset_index(),
        on="案件ID",
        how="left",
    )
    src_stats = (
        a_joined.groupby("情報源名")
        .agg(
            案件数=("案件ID", "count"),
            成約数=("成約フラグ", "sum"),
            平均粗利=("粗利_確定", "mean"),
        )
        .reset_index()
    )
    src_stats["成約率(%)"] = (
        src_stats["成約数"] / src_stats["案件数"] * 100
    ).round(1)

    cr_avg = float(src_stats["成約率(%)"].mean()) if not src_stats.empty else 0.0
    cr_warn_src = float(cfg["info_source_efficiency"]["closing_rate_vs_avg_pct"]["value"]) / 100 * cr_avg
    gp_avg = float(src_stats["平均粗利"].mean()) if not src_stats.empty else 0.0

    src_stats_data = (
        src_stats.where(src_stats.notna(), None).to_dict("records")
        if not src_stats.empty
        else []
    )

    # ── 1-4 入社経過月数別 情報源ポートフォリオ ──
    営業 = 社員[(社員["現在支店ID"] == branch_id) & (社員["職種"] == "営業")]
    a_with_tenure = a_self.copy()
    a_with_tenure = a_with_tenure.merge(
        営業[["社員ID", "入社年月"]].rename(columns={"社員ID": "登録担当社員ID"}),
        on="登録担当社員ID",
        how="left",
    )
    a_with_tenure["経過月数"] = (
        (a_with_tenure["登録日"] - a_with_tenure["入社年月"]).dt.days / 30
    ).fillna(-1).astype(int)
    a_with_tenure = a_with_tenure[a_with_tenure["経過月数"] >= 0]
    a_with_tenure["経験年次"] = (
        (a_with_tenure["経過月数"] // 12).astype(str) + "年目"
    )

    tenure_src_data = []
    if not a_with_tenure.empty:
        tenure_src = (
            a_with_tenure.groupby(["経験年次", "情報源名"]).size().reset_index(name="案件数")
        )
        tenure_src_data = tenure_src.to_dict("records")

    # ── 1-5 リードタイム（情報源別） ──
    lt_src = (
        a_self.dropna(subset=["リードタイム日数"])
        .groupby("情報源名")["リードタイム日数"]
        .agg(平均日数="mean", 中央値="median")
        .reset_index()
    )
    lt_src_data = lt_src.where(lt_src.notna(), None).to_dict("records")

    # ── 1-6 情報源別 コスト調整後 ROI ──
    roi_data_list = []
    if "コスト係数" in a_joined.columns:
        roi_data = a_joined.dropna(subset=["コスト係数"])
        if not roi_data.empty:
            roi = (
                roi_data.groupby("情報源名")
                .apply(
                    lambda g: (
                        g["粗利_確定"].sum() / (len(g) * g["コスト係数"].iloc[0])
                        if g["コスト係数"].iloc[0] > 0
                        else 0
                    )
                )
                .reset_index()
            )
            roi.columns = ["情報源名", "ROI"]
            roi_avg = float(roi["ROI"].mean())
            roi_data_list = roi.sort_values("ROI", ascending=True).where(roi.notna(), None).to_dict("records")
        else:
            roi_avg = 0.0
    else:
        roi_avg = 0.0

    # ── アラート ──
    alerts = []
    top_src = (
        a_month["情報源名"].value_counts(normalize=True).mul(100)
        if not a_month.empty
        else pd.Series(dtype=float)
    )
    if not top_src.empty and top_src.iloc[0] > dep_warn:
        alerts.append(
            make_alert(
                "warning",
                f"情報源「{top_src.index[0]}」の依存度が {top_src.iloc[0]:.1f}% と集中しています（閾値 {dep_warn}%）。情報源の多様化を指導してください。",
            )
        )

    low_cr_src = (
        src_stats[src_stats["成約率(%)"] < cr_warn_src]["情報源名"].tolist()
        if not src_stats.empty
        else []
    )
    if low_cr_src:
        alerts.append(
            make_alert(
                "warning",
                f"情報源 {', '.join(low_cr_src)} の成約率が自支店平均の50%未満です。追客工数の最適化を検討してください。",
            )
        )

    return {
        "src_count": src_count_data,
        "portfolio": dep_data,
        "src_stats": src_stats_data,
        "tenure_src": tenure_src_data,
        "leadtime": lt_src_data,
        "roi": roi_data_list,
        "summary": {
            "cr_avg": round(cr_avg, 1),
            "cr_warn_src": round(cr_warn_src, 1),
            "gp_avg": round(gp_avg),
            "roi_avg": round(roi_avg, 2),
            "dep_warn": dep_warn,
        },
        "alerts": alerts,
    }
