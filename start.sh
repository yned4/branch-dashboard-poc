#!/bin/bash
# ANTHROPIC_API_KEY が未設定の場合は .env から読み込む
if [ -z "$ANTHROPIC_API_KEY" ] && [ -f "$(dirname "$0")/.env" ]; then
  export $(grep -v '^#' "$(dirname "$0")/.env" | xargs)
fi

# バックエンド起動（ポート8000）
cd "$(dirname "$0")/backend"
python3 -m uvicorn main:app --reload --port 8000 &
BACK_PID=$!

# フロントエンド起動（ポート5173）
cd "$(dirname "$0")/frontend"
npm run dev &
FRONT_PID=$!

echo "Backend  → http://localhost:8000  (API docs: http://localhost:8000/docs)"
echo "Frontend → http://localhost:5173"
echo ""
echo "Ctrl+C で両方停止"
trap "kill $BACK_PID $FRONT_PID" EXIT
wait
