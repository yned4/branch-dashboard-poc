"""ページ固有フィルターパネル — 各ページ上部で呼ぶ"""
import streamlit as st
import pandas as pd
from .data import load_data

def _all_months() -> list[str]:
    dfs = load_data()
    return sorted(dfs["契約"]["年月"].dropna().unique().tolist())


# ─────────────────────────────────────────────
# 共通部品
# ─────────────────────────────────────────────

def _month_single(months: list[str], key: str) -> str:
    return st.select_slider("集計月", options=months, value=months[-1], key=key)


def _month_range(months: list[str], key: str) -> tuple[str, str]:
    start, end = st.select_slider(
        "集計期間",
        options=months,
        value=(months[-12] if len(months) >= 12 else months[0], months[-1]),
        key=key,
    )
    return start, end


# ─────────────────────────────────────────────
# ページ別フィルター
# ─────────────────────────────────────────────

def health(branch_id: int) -> dict:
    """app.py — ヘルスチェック用"""
    months = _all_months()
    with st.expander("🔧 フィルター", expanded=True):
        ym = _month_single(months, "hc_ym")
    return {"selected_ym": ym}


def member(branch_id: int) -> dict:
    """画面2 — メンバートラッカー用"""
    dfs = load_data()
    months = _all_months()
    営業 = dfs["社員"][
        (dfs["社員"]["現在支店ID"] == branch_id) & (dfs["社員"]["職種"] == "営業")
    ]
    all_names = 営業["氏名"].tolist()

    with st.expander("🔧 フィルター", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            ym = _month_single(months, "mb_ym")
        with c2:
            selected_members = st.multiselect(
                "メンバー絞り込み（空 = 全員）",
                options=all_names,
                default=[],
                key="mb_members",
            )
    return {
        "selected_ym": ym,
        "selected_members": selected_members if selected_members else all_names,
    }


def info_source(branch_id: int) -> dict:
    """画面3 — 情報入口分析用"""
    dfs = load_data()
    months = _all_months()
    src_names = dfs["情報源"]["情報源名"].tolist()

    with st.expander("🔧 フィルター", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            start, end = _month_range(months, "is_range")
        with c2:
            selected_src = st.multiselect(
                "情報源絞り込み（空 = 全件）",
                options=src_names,
                default=[],
                key="is_src",
            )
    return {
        "start_ym": start,
        "end_ym": end,
        "selected_ym": end,  # 単月指標用（期間末月）
        "selected_src": selected_src if selected_src else src_names,
    }


def exit_analysis(branch_id: int) -> dict:
    """画面4 — 売却出口分析用"""
    dfs = load_data()
    months = _all_months()
    exit_types = dfs["出口"]["現況再販区分"].dropna().unique().tolist()
    corp_types = dfs["出口"]["法人個人区分"].dropna().unique().tolist()

    with st.expander("🔧 フィルター", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            start, end = _month_range(months, "ea_range")
        with c2:
            sel_exit = st.multiselect(
                "現況/再販",
                options=exit_types,
                default=[],
                key="ea_exit",
            )
            sel_corp = st.multiselect(
                "法人/個人",
                options=corp_types,
                default=[],
                key="ea_corp",
            )
    return {
        "start_ym": start,
        "end_ym": end,
        "selected_ym": end,
        "sel_exit": sel_exit if sel_exit else exit_types,
        "sel_corp": sel_corp if sel_corp else corp_types,
    }


def contract(branch_id: int) -> dict:
    """画面5 — 契約・在庫分析用"""
    dfs = load_data()
    months = _all_months()
    prop_types = dfs["物件"]["種別"].dropna().unique().tolist()
    areas = dfs["物件"]["エリア"].dropna().unique().tolist()
    keiyaku_types = ["買取", "仲介", "売却"]

    with st.expander("🔧 フィルター", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            start, end = _month_range(months, "ct_range")
        with c2:
            sel_type = st.multiselect(
                "契約種別",
                options=keiyaku_types,
                default=[],
                key="ct_ktype",
            )
        with c3:
            sel_prop = st.multiselect(
                "物件種別",
                options=prop_types,
                default=[],
                key="ct_prop",
            )
        with c4:
            sel_area = st.multiselect(
                "エリア",
                options=areas,
                default=[],
                key="ct_area",
            )
    return {
        "start_ym": start,
        "end_ym": end,
        "selected_ym": end,
        "sel_keiyaku_types": sel_type if sel_type else keiyaku_types,
        "sel_prop_types": sel_prop if sel_prop else prop_types,
        "sel_areas": sel_area if sel_area else areas,
    }


def growth(branch_id: int) -> dict:
    """画面6 — 成長分析用"""
    dfs = load_data()
    months = _all_months()
    industries = dfs["社員"]["出身業種"].dropna().unique().tolist()

    with st.expander("🔧 フィルター", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            start, end = _month_range(months, "gr_range")
        with c2:
            sel_ind = st.multiselect(
                "出身業種（成長分析用）",
                options=industries,
                default=[],
                key="gr_industry",
            )
    return {
        "start_ym": start,
        "end_ym": end,
        "selected_ym": end,
        "sel_industries": sel_ind if sel_ind else industries,
    }
