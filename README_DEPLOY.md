## デプロイ手順（Vercel単体で完結）

このリポジトリは **フロント: Vite(React)** と **バックエンド: FastAPI** を、Vercel上では同一ドメインで配信します。
`/` はフロント（静的ファイル）、`/api/*` はPython（FastAPI）です。

> 重要: `.env` はコミットしないでください（APIキーはホスティング側の環境変数で設定）。

### 1) Vercel にデプロイ

#### 必須の環境変数（Vercel Project Settings）
- `ANTHROPIC_API_KEY`: Claude APIキー（必須。`/api/chat` を使う場合）

#### デプロイ手順
- VercelでリポジトリをImport（Rootはこのリポジトリのルートのまま）
- Environment Variables に `ANTHROPIC_API_KEY` を追加
- Deploy

#### 動作確認URL
- フロント: `https://<your-app>.vercel.app/`
- API docs: `https://<your-app>.vercel.app/api/docs`

