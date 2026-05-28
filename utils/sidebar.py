"""サイドバー — 支店選択のみ（グローバル共通）"""
import streamlit as st
from .data import load_data


def render() -> dict:
    dfs = load_data()
    branches: dict[int, str] = dfs["支店"].set_index("支店ID")["支店名"].to_dict()

    with st.sidebar:
        st.markdown("### 🏢 自支店")
        branch_id: int = st.selectbox(
            "支店を選択",
            options=list(branches.keys()),
            format_func=lambda x: branches[x],
            key="sidebar_branch_id",
        )
        st.markdown("---")
        st.caption("各ページ上部の\n**フィルター欄**で期間・条件を絞り込めます")

    return {
        "branch_id": branch_id,
        "branch_name": branches[branch_id],
        "other_branch_ids": [b for b in branches.keys() if b != branch_id],
        "branches": branches,
    }
