"""POST /api/chat — Claude へのストリーミングチャット"""
import os
from typing import List

import anthropic
from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.data import load_data
from backend.services.thresholds import load as load_thresholds

router = APIRouter()
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    branch_id: int
    ym: str
    messages: List[ChatMessage]
    page: str = ""


def _build_context(branch_id: int, ym: str) -> str:
    """現在の支店データを簡易サマリー化してコンテキストに渡す"""
    try:
        dfs = load_data()
        cfg = load_thresholds()

        支店 = dfs["支店"]
        契約 = dfs["契約"]
        社員 = dfs["社員"]

        branch_row = 支店[支店["支店ID"] == branch_id]
        branch_name = branch_row["支店名"].iloc[0] if not branch_row.empty else f"支店ID={branch_id}"

        # 当月KPI
        c = 契約[契約["年月"] == ym]
        c_self = c[c["契約時点支店ID"] == branch_id]
        monthly_gp = int(c_self["粗利_確定"].sum())
        contract_cnt = len(c_self)

        # 1人当たり粗利
        emp_cnt = len(社員[(社員["現在支店ID"] == branch_id) & (社員["職種"] == "営業")])
        gpp = monthly_gp // emp_cnt if emp_cnt else 0

        gpp_warn = cfg["gross_profit_per_person"]["warning_q1"]["value"]

        lines = [
            f"支店名: {branch_name}",
            f"集計月: {ym}",
            f"月次粗利: ¥{monthly_gp:,}",
            f"契約件数: {contract_cnt}件",
            f"営業人数: {emp_cnt}名",
            f"1人当たり粗利: ¥{gpp:,}（閾値 ¥{gpp_warn:,}）",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"（データ取得エラー: {e}）"


def _system_prompt(context: str, page: str) -> str:
    page_label = {
        "health":    "ヘルスチェック",
        "members":   "メンバートラッカー",
        "info":      "情報入口分析",
        "exit":      "売却出口分析",
        "contracts": "契約・在庫分析",
        "growth":    "成長分析",
        "export":    "レビューエクスポート",
    }.get(page, page)

    return f"""あなたは不動産買取再販ダッシュボードの分析アシスタントです。
支店マネージャーがダッシュボードを見ながら質問します。
現在表示中のページ: {page_label or '（不明）'}

【現在のデータサマリー】
{context}

回答ルール:
- 日本語で簡潔に答える（長くても3〜5文程度）
- データに基づき具体的な行動提案を含める
- データにない情報は推測と明記する
- ダッシュボードの操作方法も案内できる
"""


@router.post("/chat")
async def chat(req: ChatRequest):
    context = _build_context(req.branch_id, req.ym)
    system = _system_prompt(context, req.page)
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    try:
        res = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=system,
            messages=messages,
        )
        text = ""
        for block in getattr(res, "content", []) or []:
            if getattr(block, "type", None) == "text":
                text += getattr(block, "text", "") or ""
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}
