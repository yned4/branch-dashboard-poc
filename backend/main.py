"""不動産買取再販ダッシュボード — FastAPI バックエンド"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import meta, health, members, info_source, exit_analysis, contracts, growth, export, chat

app = FastAPI(
    title="不動産買取再販ダッシュボード API",
    version="0.1.0",
)

# CORS（ローカル開発用 — 全オリジン許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(meta.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(members.router, prefix="/api")
app.include_router(info_source.router, prefix="/api")
app.include_router(exit_analysis.router, prefix="/api")
app.include_router(contracts.router, prefix="/api")
app.include_router(growth.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "不動産買取再販ダッシュボード API — /docs でドキュメント確認"}
