"""共有データローダー — 全ページで import して使う"""
import pandas as pd
import duckdb
import streamlit as st
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent


@st.cache_data
def load_data() -> dict[str, pd.DataFrame]:
    def _read(fname: str) -> pd.DataFrame:
        df = pd.read_csv(DATA_DIR / fname)
        str_cols = df.select_dtypes("object").columns
        df[str_cols] = df[str_cols].replace("", pd.NA)
        return df

    社員 = _read("dim_社員.csv")
    社員["入社年月"] = pd.to_datetime(社員["入社年月"])

    支店 = _read("dim_支店.csv")
    支店["開設年月"] = pd.to_datetime(支店["開設年月"])

    情報源 = _read("dim_情報源.csv")
    出口 = _read("dim_出口.csv")

    物件 = _read("dim_物件.csv")
    for col in ["取得日", "売却契約日", "売却日"]:
        物件[col] = pd.to_datetime(物件[col], errors="coerce")
    物件["取得価格"] = pd.to_numeric(物件["取得価格"], errors="coerce")
    物件["売却価格"] = pd.to_numeric(物件["売却価格"], errors="coerce")
    物件["在庫日数"] = (物件["売却日"] - 物件["取得日"]).dt.days

    案件 = _read("fact_案件.csv")
    案件["登録日"] = pd.to_datetime(案件["登録日"])
    案件["年月"] = 案件["登録日"].dt.to_period("M").astype(str)
    案件["成約フラグ"] = 案件["成約フラグ"].astype(str).str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    ).fillna(False)

    契約 = _read("fact_契約.csv")
    契約["契約日"] = pd.to_datetime(契約["契約日"])
    契約["決済日"] = pd.to_datetime(契約["決済日"], errors="coerce")
    契約["粗利_確定"] = pd.to_numeric(契約["粗利_確定"], errors="coerce").fillna(0)
    契約["投下現金額"] = pd.to_numeric(契約["投下現金額"], errors="coerce")
    契約["年月"] = 契約["契約日"].dt.to_period("M").astype(str)
    契約["サンタメフラグ"] = 契約["サンタメフラグ"].astype(str).str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    ).fillna(False)

    # 案件に契約日を結合（1-5 リードタイム用）
    first_keiyaku = 契約.sort_values("契約日").groupby("案件ID")["契約日"].first().reset_index()
    first_keiyaku.columns = ["案件ID", "初回契約日"]
    案件 = 案件.merge(first_keiyaku, on="案件ID", how="left")
    案件["リードタイム日数"] = (案件["初回契約日"] - 案件["登録日"]).dt.days

    return {
        "社員": 社員, "支店": 支店, "情報源": 情報源,
        "出口": 出口, "物件": 物件, "案件": 案件, "契約": 契約,
    }


def get_con(dfs: dict) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for name, df in dfs.items():
        con.register(name, df)
    return con


def filter_branch(df: pd.DataFrame, branch_id: int, branch_col: str = "契約時点支店ID") -> pd.DataFrame:
    return df[df[branch_col] == branch_id]


def filter_ym(df: pd.DataFrame, ym: str, col: str = "年月") -> pd.DataFrame:
    return df[df[col] == ym]


def yoy_ym(ym: str) -> str:
    """'2025-03' → '2024-03'"""
    p = pd.Period(ym, freq="M")
    return str(p - 12)


def sales_employees(dfs: dict, branch_id: int) -> pd.DataFrame:
    return dfs["社員"][
        (dfs["社員"]["現在支店ID"] == branch_id) &
        (dfs["社員"]["職種"] == "営業") &
        (~dfs["社員"]["退職フラグ"].astype(str).str.lower().isin(["true", "1"]))
    ]


def headcount_coefficient(dfs: dict, branch_id: int, thresholds: dict) -> float:
    """営業人員の係数換算合計"""
    coef = thresholds["gross_profit_per_person"]["employee_coefficient"]
    emp = sales_employees(dfs, branch_id)
    total = 0.0
    for _, row in emp.iterrows():
        et = str(row.get("現在雇用形態", ""))
        if "正社員" in et:
            total += coef["sales_fulltime"]
        elif "派遣" in et:
            total += coef["sales_dispatch"]
        elif "クルー" in et:
            total += coef["sales_crew"]
        else:
            total += coef["sales_fulltime"]
    return max(total, 1.0)
