"""GET /api/meta — マスターデータ一覧"""
from fastapi import APIRouter
from backend.services.data import load_data

router = APIRouter()


@router.get("/meta")
def get_meta():
    dfs = load_data()

    支店 = dfs["支店"]
    契約 = dfs["契約"]
    案件 = dfs["案件"]
    社員 = dfs["社員"]
    情報源 = dfs["情報源"]
    出口 = dfs["出口"]
    物件 = dfs["物件"]

    # 月リスト（契約・案件の年月を合わせてソート）
    months_set = set(契約["年月"].dropna().tolist()) | set(案件["年月"].dropna().tolist())
    months = sorted(months_set)

    branches = (
        支店[["支店ID", "支店名"]]
        .dropna(subset=["支店ID"])
        .assign(支店ID=lambda d: d["支店ID"].astype(int))
        .to_dict("records")
    )

    info_sources = 情報源["情報源名"].dropna().unique().tolist()

    exit_types = 出口["現況再販区分"].dropna().unique().tolist() if "現況再販区分" in 出口.columns else []
    corp_types = 出口["法人個人区分"].dropna().unique().tolist() if "法人個人区分" in 出口.columns else []

    industries = 社員["出身業種"].dropna().unique().tolist() if "出身業種" in 社員.columns else []

    areas = 物件["エリア"].dropna().unique().tolist() if "エリア" in 物件.columns else []
    prop_types = 物件["種別"].dropna().unique().tolist() if "種別" in 物件.columns else []

    return {
        "branches": branches,
        "months": months,
        "info_sources": info_sources,
        "exit_types": exit_types,
        "corp_types": corp_types,
        "industries": industries,
        "areas": areas,
        "prop_types": prop_types,
    }
