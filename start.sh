#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ANTHROPIC_API_KEY が未設定の場合は .env から読み込む
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f "$ROOT_DIR/.env" ]; then
  export $(grep -v '^#' "$ROOT_DIR/.env" | xargs)
fi

# バックエンド起動（ポート8001）
cd "$ROOT_DIR"
python3 -m uvicorn backend.main:app --reload --port 8001 &
BACK_PID=$!

# フロントエンド起動（ポート5173）
npm --prefix "$ROOT_DIR/frontend" run dev &
FRONT_PID=$!

echo "Backend  → http://localhost:8001  (API docs: http://localhost:8001/docs)"
echo "Frontend → http://localhost:5173"
echo ""
echo "Ctrl+C で両方停止"
trap "kill $BACK_PID $FRONT_PID" EXIT
wait
