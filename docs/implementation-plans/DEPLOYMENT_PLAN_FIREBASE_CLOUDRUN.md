# SlidePilot デプロイ計画（Firebase Hosting + Cloud Run）

## 📋 概要

**目的**: ローカル開発環境から本番環境（Firebase Hosting + Cloud Run）へのデプロイ

**技術スタック**:
- **フロントエンド**: Firebase Hosting
- **バックエンド**: Google Cloud Run
- **ストレージ**: Supabase Storage + DB
- **CI/CD**: GitHub Actions

**想定コスト**: 月間1000PV、100回生成で **$0/月**（無料枠内）

---

## 🎯 技術選定の理由

### Firebase Hosting を選んだ理由

| 項目 | Firebase Hosting | Cloudflare Pages | 判断 |
|------|------------------|------------------|------|
| **Cloud Run統合** | 同一ドメイン、`firebase.json`で設定 | 別ドメイン、CORS設定必要 | 🥇 Firebase |
| **GCP統一** | Cloud Runと同一コンソール | 別管理 | 🥇 Firebase |
| **無料枠** | 10GB/月 | 無制限 | 🥇 Cloudflare |
| **デプロイ** | GitHub Actions設定必要 | 自動 | 🥇 Cloudflare |
| **プレビュー** | 7-30日で削除 | 永続 | 🥇 Cloudflare |

**決定的な理由**:
1. **Cloud Run統合が圧倒的に楽**
   ```json
   // firebase.json（これだけでAPIプロキシ設定完了）
   {
     "rewrites": [{
       "source": "/api/**",
       "run": { "serviceId": "slidepilot-api" }
     }]
   }
   ```

2. **単一ドメイン構成**
   ```
   https://your-app.web.app/         → Firebase Hosting（フロント）
   https://your-app.web.app/api/*   → Cloud Run（バック）
   ```

3. **GCP統一管理**
   - Cloud Run、Firebase Hosting、IAMを単一コンソールで管理
   - ログ統合（Cloud Logging）
   - 請求統合

4. **コスト試算**
   - 月間1000PV: 2GB転送 → **$0**（無料枠内）
   - 月間10000PV: 20GB転送 → **$1.5/月**

---

## ⚠️ 重要：LangGraphアーキテクチャの修正

### 現在の問題

**ローカル開発環境**:
```
FastAPI (port 8001) ─ httpx proxy ─→ LangGraph Dev Server (port 2024)
        ↑                                      ↑
   ユーザーリクエスト                    別プロセス（langgraph dev）
                                          ↑
                                    インメモリモード
                                    （永続化なし）
```

**Cloud Run環境（現状のままデプロイした場合）**:
```
Cloud Run Container
├── FastAPI (port 8001) ─ httpx proxy ─→ localhost:2024 ❌
│                                               ↑
│                                        langgraph dev が必要
│                                        しかし起動していない！
│                                        → 503 Service Unavailable
```

**問題点**:
- `langgraph dev` はインメモリモードで**本番環境では使用不可**
- Cloud Runでは複数プロセス起動が可能だが、`langgraph dev`は永続化ストレージがない
- 現在のプロキシ構成は正しいが、バックエンドサーバーの起動方法が間違っている

### 解決策：LangGraph Server + PostgreSQL（本番構成）

**正しい本番アーキテクチャ**:
```
Cloud Run Container
├── LangGraph Server (port 2024) + PostgreSQL 永続化 ✅
│         ↑
│   langgraph server コマンド使用
│   （本番モード、永続化ストレージ接続）
│
└── FastAPI (port 8001) ─ httpx proxy ─→ localhost:2024 ✅
            ↑
      プロキシは維持（正しい設計）
```

**変更点**:
1. ✅ **プロキシは維持**: 現在の設計は正しい
2. ✅ **LangGraph Server起動**: `langgraph dev` → `langgraph server` に変更
3. ✅ **永続化追加**: PostgreSQL（Cloud SQL or Supabase DB）接続
4. ✅ **マルチプロセス起動**: SupervisorでFastAPIとLangGraph Serverを両方起動
5. ✅ **langgraph.json修正**: `slide-workflow`グラフを追加

**修正ファイル**:
- ✏️ `backend/langgraph.json` - `slide-workflow`グラフ追加
- 🆕 `backend/Dockerfile` - マルチプロセス起動設定
- 🆕 `backend/supervisord.conf` - プロセス管理設定
- ✏️ `backend/.env` - PostgreSQL接続情報追加
- 📚 **ドキュメント更新**: CLAUDE.mdのアーキテクチャ図修正

---

## 🚀 デプロイ計画（全4 Phase）

### Phase 0: 前提条件（Supabase Storage移行 + LangGraph設定修正）

#### Phase 0-1: langgraph.json修正

**所要時間**: 5分

**目的**: `slide-workflow`グラフを登録し、LangGraph Serverが両方のグラフを認識できるようにする

**修正ファイル**: `backend/langgraph.json`

**変更前**:
```json
{
  "dependencies": ["langgraph==0.5.2"],
  "graphs": {
    "react-agent": {
      "path": "./app/agents/react_agent.py:graph",
      "description": "ReAct agent for Gmail sending and slide generation"
    }
  },
  "env": ".env"
}
```

**変更後**:
```json
{
  "dependencies": ["langgraph==0.5.2"],
  "graphs": {
    "react-agent": {
      "path": "./app/agents/react_agent.py:graph",
      "description": "ReAct agent for Gmail sending and slide generation"
    },
    "slide-workflow": {
      "path": "./app/agents/slide_workflow.py:graph",
      "description": "AI news slide generation workflow with quality evaluation"
    }
  },
  "env": ".env"
}
```

**成功基準**:
- [ ] `langgraph.json`修正完了
- [ ] `langgraph dev`で両方のグラフが起動確認

**ローカルテスト**:
```bash
cd backend
langgraph dev

# 別ターミナルで確認
curl -X POST http://localhost:2024/assistants/search \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'

# 両方のグラフが返ってくることを確認
```

---

#### Phase 0-2: Supabase Storage移行（PDFのみ）

**実装計画**: [SUPABASE_STORAGE_MIGRATION.md](./SUPABASE_STORAGE_MIGRATION.md)

**重要な修正**:
- ❌ Markdownは**移行不要**（既にSupabase DBの`slides.slide_md`カラムに保存済み）
- ✅ **PDFのみ**をSupabase Storageに移行

**確認事項**:
- [ ] Supabase Storageバケット作成（`uploads`, `slides`）
- [ ] バックエンドコード修正完了（**5ファイル**に簡略化）
- [ ] ローカルテスト成功（PDF保存・ダウンロード）

**修正ファイル数**: 7ファイル → **5ファイル**（Markdown保存削除により簡略化）

---

#### Phase 0-3: PostgreSQL設定（本番環境用）

**所要時間**: 20分

**目的**: LangGraph Serverの永続化ストレージを設定（Cloud Run本番環境で必要）

**選択肢**:

| オプション | メリット | デメリット | 推奨 |
|-----------|---------|----------|------|
| **Supabase DB（PostgreSQL）** | 既存のDBを流用、設定簡単 | LangGraph専用スキーマ必要 | ✅ **推奨** |
| **Cloud SQL（PostgreSQL）** | GCP統合、高性能 | 追加コスト（$10/月〜） | △ 将来検討 |

**実装手順**（Supabase DB使用）:

1. **環境変数追加**

**修正ファイル**: `backend/.env`

```bash
# 既存の設定
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# 新規追加（LangGraph永続化用）
POSTGRES_URI=postgresql://postgres:your-password@db.your-project.supabase.co:5432/postgres
```

2. **LangGraph Server起動時に環境変数を使用**

LangGraph Serverは`POSTGRES_URI`環境変数を自動認識し、永続化ストレージとして使用します。

**成功基準**:
- [ ] `POSTGRES_URI`環境変数設定完了
- [ ] ローカルでの動作確認（`langgraph dev`は永続化しないが、Cloud Runでは必要）

**注意事項**:
- `langgraph dev`コマンドはインメモリモードのため、この設定は**Cloud Run本番環境でのみ有効**
- ローカル開発では引き続き`langgraph dev`を使用（永続化不要）

---

#### Phase 0-4: スレッドのユーザー識別対応

**所要時間**: 15分

**目的**: スレッド作成時にユーザー情報を`metadata`として保存し、将来的なユーザーフィルタリングとアクセス制御を可能にする

**現状の問題**:
```typescript
// frontend/src/hooks/useReactAgent.ts:44
body: JSON.stringify({})  // ← metadata が空！
```

```sql
-- PostgreSQL threads テーブル（現状）
thread_id | created_at           | metadata
----------|----------------------|----------
550e8400..| 2025-11-03 10:00:00 | {}  ← 誰のスレッドか不明
```

**影響**:
- ❌ ユーザーごとの会話履歴取得が不可能
- ❌ スレッドアクセス制御ができない
- ❌ セキュリティリスク（誰でも任意のスレッドにアクセス可能）

---

**修正内容**:

**修正ファイル**: `frontend/src/hooks/useReactAgent.ts`

**変更箇所**: `createThread` 関数（39-57行目）

**変更前**:
```typescript
const createThread = useCallback(async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/threads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})  // ← 空
    });

    if (!res.ok) throw new Error(`Thread creation failed: ${res.statusText}`);

    const data = await res.json();
    setThreadId(data.thread_id);
    setError(null);
    return data.thread_id;
  } catch (err: any) {
    setError(err.message);
    throw err;
  }
}, []);
```

**変更後**:
```typescript
const createThread = useCallback(async () => {
  try {
    // ──────────────────────────────────────────────────────────────
    // ユーザー情報取得（localStorage から）
    // ──────────────────────────────────────────────────────────────
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const userEmail = user.email || 'anonymous@example.com';

    const res = await fetch(`${API_BASE_URL}/threads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        metadata: {
          user_email: userEmail,          // ユーザー識別子
          created_from: 'web_ui',         // 作成元
          created_at: new Date().toISOString()  // 作成日時
        }
      })
    });

    if (!res.ok) throw new Error(`Thread creation failed: ${res.statusText}`);

    const data = await res.json();
    setThreadId(data.thread_id);
    setError(null);
    return data.thread_id;
  } catch (err: any) {
    setError(err.message);
    throw err;
  }
}, []);
```

---

**バックエンド（変更不要）**:

現在の実装が既にmetadataを正しく転送しています:

```python
# backend/app/routers/agent.py:30-38
body = await request.json()  # ← metadata を含む

async with httpx.AsyncClient(timeout=TIMEOUT) as client:
    response = await client.post(
        f"{LANGGRAPH_BASE_URL}/threads",
        json=body  # ← そのまま LangGraph Server に転送
    )
    response.raise_for_status()
    return response.json()
```

---

**PostgreSQL（自動保存）**:

LangGraph Serverが自動的にmetadataを保存:

```sql
-- threads テーブル（修正後）
INSERT INTO threads (thread_id, created_at, metadata)
VALUES (
  '550e8400-e29b-41d4-a716-446655440000',
  '2025-11-03 10:00:00',
  '{
    "user_email": "tanaka@example.com",
    "created_from": "web_ui",
    "created_at": "2025-11-03T10:00:00.000Z"
  }'
);
```

---

**成功基準**:
- [ ] フロントエンド修正完了（1ファイル）
- [ ] スレッド作成時に`metadata`が保存される
- [ ] PostgreSQL `threads.metadata`に`user_email`が含まれる
- [ ] 既存機能に影響なし（スライド生成、メール送信が正常動作）

**ローカルテスト**:
```bash
# 1. フロントエンド起動
cd frontend
npm run dev

# 2. バックエンド起動
cd backend
langgraph dev &
python3 app/main.py

# 3. ブラウザでテスト
# - Google OAuth でログイン
# - 新しいスレッド作成
# - スライド生成実行

# 4. データベース確認（Supabase Dashboard or psql）
SELECT thread_id, created_at, metadata
FROM threads
ORDER BY created_at DESC
LIMIT 5;

# 結果例:
# thread_id | created_at           | metadata
# ----------|----------------------|---------------------------------------
# 550e8400..| 2025-11-03 10:00:00 | {"user_email": "your-email@gmail.com", ...}
```

**将来の機能拡張（準備完了）**:

この修正により、以下の機能実装が可能になります:

1. **ユーザーごとの会話履歴取得**
   ```python
   # 将来の実装例
   @router.get("/threads")
   async def list_threads(x_user_email: str = Header(...)):
       params = {"metadata": {"user_email": x_user_email}}
       response = await client.get(f"{LANGGRAPH_BASE_URL}/threads", params=params)
       return response.json()
   ```

2. **スレッドアクセス制御**
   ```python
   # 将来の実装例
   thread = await get_thread(thread_id)
   if thread["metadata"]["user_email"] != current_user_email:
       raise HTTPException(403, "Access denied")
   ```

3. **スレッド検索・フィルタリング**
   - ユーザーごとのスレッド一覧
   - 日付範囲でのフィルタリング
   - キーワード検索

---

### Phase 1: Cloud Runデプロイ

**所要時間**: 90分

#### 1-1. マルチプロセス起動設定

**目的**: Cloud RunでLangGraph ServerとFastAPIを両方起動する

**選択肢**:

| オプション | 実装方法 | メリット | デメリット |
|-----------|---------|---------|----------|
| **Supervisor** | supervisord設定ファイル | 安定、ログ管理容易 | 依存関係増加 |
| **Shell Script** | `&`でバックグラウンド起動 | シンプル | プロセス管理が脆弱 |

**推奨**: Supervisor（本番環境で安定）

**新規ファイル**: `backend/supervisord.conf`

```ini
[supervisord]
nodaemon=true
logfile=/dev/stdout
logfile_maxbytes=0
loglevel=info

[program:langgraph]
command=langgraph server --host 0.0.0.0 --port 2024
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
environment=POSTGRES_URI="%(ENV_POSTGRES_URI)s"

[program:fastapi]
command=uvicorn app.main:app --host 0.0.0.0 --port %(ENV_PORT)s --workers 1
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

**成功基準**:
- [ ] `supervisord.conf`作成完了
- [ ] 両方のプロセスが起動することを確認

---

#### 1-2. Dockerfile作成

**新規ファイル**: `backend/Dockerfile`

```dockerfile
# ──────────────────────────────────────────────────────────────
# Stage 1: ベースイメージ（Python 3.11）
# ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /app

# システム依存関係（Playwright/Chromium + Supervisor用）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    supervisor \
    && rm -rf /var/lib/apt/lists/*


# ──────────────────────────────────────────────────────────────
# Stage 2: Node.js + Slidev インストール
# ──────────────────────────────────────────────────────────────
FROM base AS nodejs

# Node.js 20.xインストール
RUN wget -qO- https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Slidev CLI + Playwright グローバルインストール
RUN npm install -g @slidev/cli@latest playwright-chromium

# Chromiumインストール
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx playwright-chromium install chromium --with-deps


# ──────────────────────────────────────────────────────────────
# Stage 3: Python依存関係インストール
# ──────────────────────────────────────────────────────────────
FROM nodejs AS dependencies

WORKDIR /app

# requirements.txtコピー
COPY requirements.txt .

# Python依存関係インストール（supervisor追加）
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir supervisor


# ──────────────────────────────────────────────────────────────
# Stage 4: アプリケーションコード
# ──────────────────────────────────────────────────────────────
FROM dependencies AS application

WORKDIR /app

# アプリケーションコードコピー
COPY ./app /app/app
COPY langgraph.json /app/
COPY supervisord.conf /app/

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV PORT=8001
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8001/api/health')" && \
      python -c "import requests; requests.get('http://localhost:2024/ok')"

# Supervisorで起動（LangGraph Server + FastAPI）
CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
```

**重要な変更点**:
1. ✅ `supervisor`パッケージ追加
2. ✅ `langgraph.json`と`supervisord.conf`をコピー
3. ✅ ヘルスチェックで両方のサーバーを確認
4. ✅ CMDで`supervisord`起動

**成功基準**:
- [ ] Dockerfileビルド成功
- [ ] ローカルでコンテナ起動確認
- [ ] 両方のエンドポイント（`/api/health`, `/ok`）で200 OK

**ローカルテスト**:
```bash
cd backend

# ビルド
docker build -t slidepilot-api .

# 起動（環境変数を.envから読み込み）
docker run -p 8001:8001 -p 2024:2024 --env-file .env slidepilot-api

# 別ターミナルで確認
curl http://localhost:8001/api/health
curl http://localhost:2024/ok
```

---

#### 1-3. .dockerignore作成

**新規ファイル**: `backend/.dockerignore`

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/

# OS
.DS_Store

# Data（ローカルファイル不要）
data/

# Git
.git/
.gitignore
```

**成功基準**:
- [ ] `.dockerignore`作成完了

---

#### 1-4. Cloud Runデプロイ（手動）

**前提条件**:
- Google Cloud SDK (`gcloud`) インストール済み
- GCPプロジェクト作成済み
- Artifact Registry有効化済み

**手順**:

```bash
# 1. GCPプロジェクト設定
export PROJECT_ID="your-gcp-project-id"
export REGION="asia-northeast1"
export SERVICE_NAME="slidepilot-api"

gcloud config set project $PROJECT_ID

# 2. Artifact Registry作成（初回のみ）
gcloud artifacts repositories create cloud-run-source-deploy \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for Cloud Run"

# 3. gcloud認証設定
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 4. Dockerイメージビルド＆プッシュ
cd backend
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}

# 5. Cloud Runデプロイ
gcloud run deploy ${SERVICE_NAME} \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars "SLIDE_FORMAT=pdf" \
    --set-secrets "OPENAI_API_KEY=openai-api-key:latest,TAVILY_API_KEY=tavily-api-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_KEY=supabase-service-key:latest,POSTGRES_URI=postgres-uri:latest,LANGCHAIN_API_KEY=langchain-api-key:latest"

# 6. デプロイURL取得
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
```

**Secret Manager設定（初回のみ）**:

```bash
# Secret Manager API有効化
gcloud services enable secretmanager.googleapis.com

# シークレット作成
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-tavily-api-key" | gcloud secrets create tavily-api-key --data-file=-
echo -n "your-supabase-url" | gcloud secrets create supabase-url --data-file=-
echo -n "your-supabase-service-key" | gcloud secrets create supabase-service-key --data-file=-
echo -n "postgresql://..." | gcloud secrets create postgres-uri --data-file=-
echo -n "your-langchain-api-key" | gcloud secrets create langchain-api-key --data-file=-

# Cloud RunサービスアカウントにSecret Manager権限付与
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in openai-api-key tavily-api-key supabase-url supabase-service-key postgres-uri langchain-api-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
done
```

**成功基準**:
- [ ] Cloud Runサービス起動成功
- [ ] デプロイURL取得
- [ ] `curl https://slidepilot-api-xxxxx-an.a.run.app/api/health`で200 OK
- [ ] スライド生成テスト成功

---

### Phase 2: Firebase Hostingセットアップ

**所要時間**: 30分

#### 2-1. Firebase CLI初期設定

**手順**:

```bash
# 1. Firebase CLIインストール（グローバル）
npm install -g firebase-tools

# 2. Firebaseログイン
firebase login

# 3. フロントエンドディレクトリに移動
cd frontend

# 4. Firebase初期化
firebase init hosting

# 質問に回答:
# ────────────────────────────────────────────────────
# ? Please select an option: (Use arrow keys)
#   ❯ Use an existing project
#
# ? Select a default Firebase project for this directory:
#   ❯ your-gcp-project-id (your-project-name)
#
# ? What do you want to use as your public directory?
#   ❯ dist
#
# ? Configure as a single-page app (rewrite all urls to /index.html)?
#   ❯ Yes
#
# ? Set up automatic builds and deploys with GitHub?
#   ❯ Yes
#
# ? For which GitHub repository would you like to set up a GitHub workflow?
#   ❯ your-username/slide-pilot
#
# ? Set up the workflow to run a build script before every deploy?
#   ❯ Yes
#
# ? What script should be run before every deploy?
#   ❯ npm ci && npm run build
#
# ? Set up automatic deployment to your site's live channel when a PR is merged?
#   ❯ Yes
#
# ? What is the name of the GitHub branch associated with your site's live channel?
#   ❯ main
# ────────────────────────────────────────────────────
```

**生成されるファイル**:
- `frontend/.firebaserc`
- `frontend/firebase.json`
- `.github/workflows/firebase-hosting-merge.yml`
- `.github/workflows/firebase-hosting-pull-request.yml`

**成功基準**:
- [ ] Firebase CLI初期化完了
- [ ] 設定ファイル生成確認

---

#### 2-2. firebase.json設定

**修正ファイル**: `frontend/firebase.json`

**変更前（自動生成）**:
```json
{
  "hosting": {
    "public": "dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

**変更後（Cloud Run統合）**:
```json
{
  "hosting": {
    "public": "dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],

    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "slidepilot-api",
          "region": "asia-northeast1"
        }
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],

    "headers": [
      {
        "source": "**",
        "headers": [
          {
            "key": "X-Content-Type-Options",
            "value": "nosniff"
          },
          {
            "key": "X-Frame-Options",
            "value": "SAMEORIGIN"
          },
          {
            "key": "X-XSS-Protection",
            "value": "1; mode=block"
          },
          {
            "key": "Referrer-Policy",
            "value": "strict-origin-when-cross-origin"
          }
        ]
      },
      {
        "source": "**/*.@(js|css)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable"
          }
        ]
      },
      {
        "source": "**/*.@(jpg|jpeg|gif|png|svg|webp|ico)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable"
          }
        ]
      },
      {
        "source": "index.html",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "no-cache, no-store, must-revalidate"
          }
        ]
      }
    ]
  }
}
```

**重要ポイント**:
1. **Cloud Runプロキシ設定**
   ```json
   {
     "source": "/api/**",
     "run": {
       "serviceId": "slidepilot-api",
       "region": "asia-northeast1"
     }
   }
   ```
   - `/api/*`へのリクエストをCloud Runに転送
   - CORS設定不要
   - 同一ドメインで動作

2. **SPAフォールバック**
   ```json
   {
     "source": "**",
     "destination": "/index.html"
   }
   ```
   - React Routerの動的ルーティング対応

3. **セキュリティヘッダー**
   - XSS, Clickjacking対策
   - Content-Type Sniffing防止

4. **キャッシュ戦略**
   - 静的アセット（JS/CSS/画像）: 1年キャッシュ
   - index.html: キャッシュ無効

**成功基準**:
- [ ] `firebase.json`修正完了
- [ ] Cloud Run統合設定確認

---

#### 2-3. 環境変数設定

**修正ファイル**: `frontend/.env.production`

**変更前**:
```bash
VITE_API_URL=http://localhost:8001
VITE_GOOGLE_CLIENT_ID=your-google-oauth-client-id
```

**変更後**:
```bash
# Cloud Run統合（相対パス）
VITE_API_URL=/api

# Google OAuth（本番用Client ID）
VITE_GOOGLE_CLIENT_ID=your-production-google-oauth-client-id.apps.googleusercontent.com
```

**Google OAuth Client ID更新**:
1. https://console.cloud.google.com/apis/credentials にアクセス
2. 既存のOAuth 2.0クライアントIDを編集
3. 承認済みのJavaScript生成元に追加:
   - `https://your-project-id.web.app`
   - `https://your-project-id.firebaseapp.com`
4. 承認済みのリダイレクトURIに追加:
   - `https://your-project-id.web.app`
   - `https://your-project-id.firebaseapp.com`

**成功基準**:
- [ ] `.env.production`修正完了
- [ ] Google OAuth設定更新完了

---

#### 2-4. フロントエンドコード修正

**修正ファイル**: `frontend/src/hooks/useReactAgent.ts`

**変更箇所**: API URL取得部分

```typescript
// 変更前
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

// 変更後（環境変数のデフォルト値変更）
const API_URL = import.meta.env.VITE_API_URL || '/api';
```

**理由**: Firebase Hostingの場合、デフォルトで相対パス`/api`を使用

**成功基準**:
- [ ] `useReactAgent.ts`修正完了

---

#### 2-5. 手動デプロイテスト

**手順**:

```bash
cd frontend

# 1. ビルド
npm run build

# 2. デプロイ（本番）
firebase deploy --only hosting

# 3. デプロイURL確認
# 出力例:
# ✔  Deploy complete!
#
# Project Console: https://console.firebase.google.com/project/your-project-id/overview
# Hosting URL: https://your-project-id.web.app
```

**動作確認**:
```bash
# ブラウザで確認
open https://your-project-id.web.app

# 確認項目:
# - トップページ表示
# - Google OAuthログイン
# - スライド生成
# - スライドダウンロード
# - /api/* がCloud Runに転送されているか
```

**成功基準**:
- [ ] デプロイ成功
- [ ] Hosting URL取得
- [ ] 動作確認完了

---

### Phase 3: GitHub Actions自動デプロイ

**所要時間**: 20分

#### 3-1. GitHub Actionsワークフロー確認

Firebase初期化時に自動生成されたワークフローを確認します。

**生成ファイル**: `.github/workflows/firebase-hosting-merge.yml`

```yaml
# mainブランチへのpush時に本番デプロイ
name: Deploy to Firebase Hosting on merge
'on':
  push:
    branches:
      - main
jobs:
  build_and_deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm ci && npm run build
        working-directory: frontend
      - uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: '${{ secrets.GITHUB_TOKEN }}'
          firebaseServiceAccount: '${{ secrets.FIREBASE_SERVICE_ACCOUNT_YOUR_PROJECT_ID }}'
          channelId: live
          projectId: your-project-id
```

**生成ファイル**: `.github/workflows/firebase-hosting-pull-request.yml`

```yaml
# PRオープン時にプレビューデプロイ
name: Deploy to Firebase Hosting on PR
'on': pull_request
jobs:
  build_and_preview:
    if: '${{ github.event.pull_request.head.repo.full_name == github.repository }}'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm ci && npm run build
        working-directory: frontend
      - uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: '${{ secrets.GITHUB_TOKEN }}'
          firebaseServiceAccount: '${{ secrets.FIREBASE_SERVICE_ACCOUNT_YOUR_PROJECT_ID }}'
          projectId: your-project-id
```

**確認ポイント**:
- `working-directory: frontend` が正しく設定されているか
- `projectId` がGCPプロジェクトIDと一致しているか

**成功基準**:
- [ ] GitHub Actionsワークフロー確認完了

---

#### 3-2. GitHub Secrets設定確認

Firebase初期化時に自動設定されたSecretsを確認します。

**GitHub リポジトリ設定**:
```
Settings → Secrets and variables → Actions
```

**確認すべきSecret**:
- `FIREBASE_SERVICE_ACCOUNT_YOUR_PROJECT_ID`: Firebase Service Account JSON（自動生成）

**追加で必要なSecret（オプション）**:
- `GCP_PROJECT_ID`: GCPプロジェクトID（Cloud Runデプロイ用）

**成功基準**:
- [ ] `FIREBASE_SERVICE_ACCOUNT_*`が存在することを確認

---

#### 3-3. 自動デプロイテスト

**手順**:

```bash
# 1. 軽微な変更をコミット
echo "# Test" >> README.md
git add README.md
git commit -m "test: GitHub Actions自動デプロイテスト"

# 2. mainブランチにpush
git push origin main

# 3. GitHub Actionsの実行確認
# https://github.com/your-username/slide-pilot/actions
```

**確認項目**:
- [ ] GitHub Actionsワークフローが自動起動
- [ ] ビルド成功
- [ ] Firebase Hostingデプロイ成功
- [ ] デプロイURL確認
- [ ] 動作確認

**プレビューデプロイテスト**:

```bash
# 1. 新規ブランチ作成
git checkout -b feature/test-preview

# 2. 変更コミット
echo "# Preview Test" >> README.md
git add README.md
git commit -m "feat: プレビューデプロイテスト"

# 3. プッシュ
git push origin feature/test-preview

# 4. GitHub上でPR作成
# 5. PRページでプレビューURLを確認
#    → コメントに自動投稿される
#    例: https://your-project-id--pr-123-abc.web.app
```

**成功基準**:
- [ ] mainブランチ自動デプロイ成功
- [ ] PRプレビューデプロイ成功
- [ ] プレビューURL取得・動作確認

---

### Phase 4: カスタムドメイン設定（オプション）

**所要時間**: 30分

#### 4-1. Firebase Hostingカスタムドメイン

**前提条件**:
- 独自ドメイン所有（例: `example.com`）

**手順**:

```bash
# 1. Firebase Consoleでカスタムドメイン追加
# https://console.firebase.google.com/project/your-project-id/hosting/sites

# 2. ドメイン入力
# 例: app.example.com

# 3. DNS設定
# Firebase Consoleに表示されるTXTレコードとAレコードを追加

# TXTレコード（所有権確認）
# ホスト名: app
# 値: google-site-verification=xxxxxxxxxxxx

# Aレコード（IPv4）
# ホスト名: app
# 値: 199.36.158.100

# Aレコード（IPv4）
# ホスト名: app
# 値: 199.36.158.101

# AAAAレコード（IPv6）
# ホスト名: app
# 値: 2001:4860:4802:32::64

# AAAAレコード（IPv6）
# ホスト名: app
# 値: 2001:4860:4802:34::64

# 4. SSL証明書自動発行（24時間以内）
```

**成功基準**:
- [ ] カスタムドメイン設定完了
- [ ] DNS設定完了
- [ ] SSL証明書発行確認
- [ ] `https://app.example.com`でアクセス可能

---

#### 4-2. Cloud Runカスタムドメイン（オプション）

**注意**: Firebase Hostingで`/api/*`をCloud Runにプロキシしているため、Cloud Run用のカスタムドメインは**不要**です。

フロントエンドとバックエンドで別々のドメインを使いたい場合のみ設定してください。

**手順**（参考）:

```bash
# 1. Cloud Runドメインマッピング
gcloud run domain-mappings create \
    --service slidepilot-api \
    --domain api.example.com \
    --region asia-northeast1

# 2. DNS設定
# 表示されたCNAMEレコードを追加

# 3. SSL証明書自動発行
```

---

## 📊 デプロイ後の確認チェックリスト

### バックエンド（Cloud Run）

- [ ] Cloud Runサービスが起動している
- [ ] `https://slidepilot-api-xxxxx-an.a.run.app/api/health`で200 OK
- [ ] Secret Managerから環境変数が正しく読み込まれている
- [ ] スライド生成テスト成功
- [ ] Supabase Storageへのアップロード成功
- [ ] ログ確認（Cloud Logging）

### フロントエンド（Firebase Hosting）

- [ ] Firebase Hostingにデプロイ成功
- [ ] `https://your-project-id.web.app`でアクセス可能
- [ ] Google OAuthログイン成功
- [ ] `/api/*`がCloud Runに正しくプロキシされている
- [ ] スライド生成フロー全体の動作確認
- [ ] スライドダウンロード成功
- [ ] プレビューデプロイ動作確認（PR作成時）

### GitHub Actions

- [ ] mainブランチpush時に自動デプロイ成功
- [ ] PR作成時にプレビューデプロイ成功
- [ ] デプロイ失敗時にSlack通知（オプション）

### 監視・ログ

- [ ] Cloud Logging設定確認
- [ ] Cloud Monitoring設定確認（オプション）
- [ ] アラート設定（オプション）

---

## 💰 コスト試算（本番運用）

### 月間1000PV、100回生成の場合

| サービス | 使用量 | 無料枠 | 超過コスト | 月額 |
|---------|--------|--------|----------|------|
| **Firebase Hosting** | 2GB転送 | 10GB/月 | - | **$0** |
| **Cloud Run** | 8h CPU, 1GB転送 | 18万vCPU秒, 1GB | - | **$0** |
| **Supabase** | 1GB Storage | 1GB | - | **$0** |
| **Secret Manager** | 5シークレット | 6シークレット | - | **$0** |
| **合計** | - | - | - | **$0/月** |

### 月間10000PV、1000回生成の場合

| サービス | 使用量 | 無料枠 | 超過コスト | 月額 |
|---------|--------|--------|----------|------|
| **Firebase Hosting** | 20GB転送 | 10GB/月 | 10GB × $0.15 | **$1.5** |
| **Cloud Run** | 80h CPU, 10GB転送 | 18万vCPU秒 | - | **$0** |
| **Supabase** | 5GB Storage | 1GB | 4GB × $0.021/GB | **$0.08** |
| **合計** | - | - | - | **$1.58/月** |

---

## 🚨 トラブルシューティング

### Cloud Runデプロイエラー

**エラー**: `ERROR: (gcloud.run.deploy) PERMISSION_DENIED`

**原因**: サービスアカウントに権限がない

**解決策**:
```bash
# Cloud Runデプロイ権限付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/run.admin"
```

---

**エラー**: `Container failed to start. Failed to start and then listen on the port defined by the PORT environment variable.`

**原因**: アプリケーションが$PORTで起動していない

**解決策**:
```dockerfile
# Dockerfile内で$PORTを使用
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
```

---

**エラー**: `Playwright browser not found`

**原因**: Chromiumがインストールされていない

**解決策**:
```dockerfile
# Dockerfileに追加
RUN npx playwright-chromium install chromium --with-deps
```

---

### Firebase Hostingデプロイエラー

**エラー**: `Error: HTTP Error: 403, The caller does not have permission`

**原因**: Firebase Service Accountに権限がない

**解決策**:
```bash
# Firebase Hosting管理者権限付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com" \
    --role="roles/firebasehosting.admin"
```

---

**エラー**: `/api/*`がCloud Runに転送されない

**原因**: `firebase.json`の設定ミス

**解決策**:
```json
{
  "hosting": {
    "rewrites": [
      {
        "source": "/api/**",  // ** を忘れずに
        "run": {
          "serviceId": "slidepilot-api",
          "region": "asia-northeast1"
        }
      }
    ]
  }
}
```

---

### GitHub Actionsエラー

**エラー**: `Error: Unable to find service account key`

**原因**: `FIREBASE_SERVICE_ACCOUNT_*`が設定されていない

**解決策**:
```bash
# GitHub SecretsにFirebase Service Account JSONを追加
# Settings → Secrets and variables → Actions → New repository secret
```

---

## 📚 参考資料

- [Cloud Run公式ドキュメント](https://cloud.google.com/run/docs)
- [Firebase Hosting公式ドキュメント](https://firebase.google.com/docs/hosting)
- [Firebase Hosting + Cloud Run統合](https://firebase.google.com/docs/hosting/cloud-run)
- [GitHub Actions for Firebase](https://github.com/marketplace/actions/deploy-to-firebase-hosting)
- [Secret Manager公式ドキュメント](https://cloud.google.com/secret-manager/docs)
- [Supabase Storage公式ドキュメント](https://supabase.com/docs/guides/storage)

---

## 🎉 デプロイ完了後の次のステップ

1. **カスタムドメイン設定**（オプション）
2. **Cloud Monitoringアラート設定**（オプション）
3. **Cloud Loggingログ保存期間設定**（オプション）
4. **Cloud Armorセキュリティポリシー設定**（オプション）
5. **パフォーマンスチューニング**（必要に応じて）
6. **ユーザーフィードバック収集**

---

## 📝 デプロイ完了報告テンプレート

```markdown
## デプロイ完了報告

### 環境情報
- **プロジェクトID**: your-project-id
- **バックエンドURL**: https://slidepilot-api-xxxxx-an.a.run.app
- **フロントエンドURL**: https://your-project-id.web.app
- **デプロイ日時**: 2025-xx-xx xx:xx

### デプロイ内容
- [ ] Cloud Runデプロイ完了
- [ ] Firebase Hostingデプロイ完了
- [ ] GitHub Actions自動デプロイ設定完了
- [ ] Supabase Storage移行完了

### 動作確認
- [ ] ヘルスチェック正常
- [ ] Google OAuthログイン成功
- [ ] スライド生成成功
- [ ] スライドダウンロード成功

### 課題・TODO
- [ ] カスタムドメイン設定
- [ ] モニタリング設定
- [ ] パフォーマンスチューニング
```
