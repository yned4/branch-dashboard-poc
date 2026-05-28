"""閾値ローダー — thresholds.yaml から読み込み、breach チェックを提供"""
import yaml
import streamlit as st
from pathlib import Path

YAML_PATH = Path(__file__).parent.parent / "thresholds.yaml"


@st.cache_data
def load() -> dict:
    with open(YAML_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _check_direction(value: float, threshold: float, direction: str) -> bool:
    """閾値を超過しているか（True = 超過）"""
    if direction == "lower_is_bad":
        return value < threshold
    elif direction == "higher_is_bad":
        return value > threshold
    return False


def check_breach(value: float, cfg: dict) -> tuple[str, str]:
    """
    Returns (level, icon)
      level: 'ok' | 'warning' | 'critical'
    cfg structure: { direction, warning: {value}, critical: {value} }
    """
    direction = cfg.get("direction", "lower_is_bad")
    crit = cfg.get("critical", {}).get("value") if isinstance(cfg.get("critical"), dict) else None
    warn = cfg.get("warning", {}).get("value") if isinstance(cfg.get("warning"), dict) else cfg.get("value")

    if crit is not None and _check_direction(value, crit, direction):
        return "critical", "🔴"
    if warn is not None and _check_direction(value, warn, direction):
        return "warning", "🟡"
    return "ok", "🟢"


def next_action_box(level: str, message: str):
    """閾値超過時に Next Action を表示（streamlit コンポーネント）"""
    import streamlit as st
    if level == "critical":
        st.error(f"🔴 **Next Action（要対応）**: {message}")
    elif level == "warning":
        st.warning(f"🟡 **Next Action（注意）**: {message}")
