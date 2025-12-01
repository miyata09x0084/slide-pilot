# 動画生成アーキテクチャ再設計

## 概要

Cloud Run Jobs を使用した非同期動画生成により、タイムアウト問題を根本解決する。

## 背景・課題

### 従来のアーキテクチャ
```
Frontend → FastAPI → LangGraph → render_video node → FastAPI /api/render/video
                                     ↓
                              同期的に5分待機（timeout=300）
                                     ↓
                              Playwright PNG生成 + MoviePy動画生成
```

### 問題点
1. **同期ブロッキング**: ユーザーは動画生成完了まで待機
2. **タイムアウト**: Cloud Run環境でCDN（Google Fonts, Mermaid.js）読み込みが60秒を超過
3. **単一障害点**: 動画生成失敗 = ワークフロー全体失敗
4. **スケーラビリティなし**: 長時間処理がCloud Runインスタンスを占有

---

## 新アーキテクチャ

```
Frontend → FastAPI → LangGraph → render_video node
                                     ↓
                              Cloud Run Job をトリガー（即座にreturn）
                                     ↓
                              video_job_id を返却
                                     ↓
                              Supabase DBにステータス保存
                                     ↓
Frontend ←─────── ポーリングでステータス確認 ────────→ FastAPI /api/video/status/{job_id}

[バックグラウンド]
Cloud Run Job (最大24時間実行可能)
    ↓
Playwright PNG生成（CDN依存なし・ローカルフォント）
    ↓
MoviePy動画生成
    ↓
Supabase Storageアップロード
    ↓
DBステータス更新（completed + video_url）
```

---

## 実装詳細

### 1. CDN依存の削除

**ファイル**: `backend/app/core/slide_renderer.py`

- Google Fonts `@import` を削除
- `'Noto Sans CJK JP'` ローカルフォントを使用（Docker内にインストール済み）
- Mermaid.js をローカルファイル (`app/static/mermaid.min.js`) から読み込み
- `wait_for_load_state('networkidle')` → `'domcontentloaded'` に変更

### 2. Supabase video_jobs テーブル

```sql
CREATE TABLE video_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slide_id UUID REFERENCES slides(id),
  user_id TEXT NOT NULL,
  status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
  video_url TEXT,
  error_message TEXT,
  input_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3. Cloud Run Job

**ファイル**: `backend/jobs/video_render_job.py`

- 環境変数 `JOB_ID` からジョブIDを取得
- `video_jobs` テーブルから入力データを取得
- SlideRenderer + MoviePy で動画生成
- Supabase Storage にアップロード
- ステータスを `completed` / `failed` に更新

**Dockerfile**: `backend/Dockerfile.job`

```dockerfile
CMD ["python", "/app/jobs/video_render_job.py"]
```

### 4. FastAPI エンドポイント

**ファイル**: `backend/app/routers/render.py`

| エンドポイント | 説明 |
|---------------|------|
| `POST /api/render/video/async` | Cloud Run Job をトリガー、job_id を返却 |
| `GET /api/video/status/{job_id}` | ジョブステータスを返却 |

### 5. LangGraph render_video node

**ファイル**: `backend/app/agents/slide_workflow.py`

- 同期HTTP呼び出し → 非同期Jobトリガーに変更
- State に `video_job_id` を追加
- タイムアウトを30秒に短縮（ジョブ作成のみ）

### 6. フロントエンド

**ファイル**: `frontend/src/features/generation/hooks/useReactAgent.ts`

- `video_job_id` を受け取ったらポーリング開始
- 5秒間隔で `/api/video/status/{job_id}` を確認
- `completed` で動画URLを取得、UIに反映

---

## Cloud Run Jobs のメリット

| 特徴 | 詳細 |
|-----|------|
| 最大24時間実行 | 現在の5分制限を解消 |
| 非同期処理 | ユーザーは待機不要 |
| 自動リトライ | 失敗時に再実行可能 |
| コスト効率 | 実行時間のみ課金 |
| 並列処理 | 複数ジョブを同時実行可能 |

---

## デプロイ

### Cloud Run Job のデプロイ

```bash
# イメージビルド
docker build -f Dockerfile.job -t slidepilot-video-job .

# Cloud Run Job 作成
gcloud run jobs create slidepilot-video-job \
  --image=asia-northeast1-docker.pkg.dev/PROJECT_ID/cloud-run-source-deploy/slidepilot-video-job \
  --region=asia-northeast1 \
  --memory=4Gi \
  --cpu=2 \
  --task-timeout=3600
```

### GitHub Actions

`.github/workflows/deploy-video-job.yml` で自動デプロイ。

---

## 修正対象ファイル一覧

### 新規作成
- `backend/jobs/video_render_job.py`
- `backend/Dockerfile.job`
- `backend/migrations/002_create_video_jobs.sql`
- `backend/app/static/mermaid.min.js`
- `.github/workflows/deploy-video-job.yml`
- `frontend/src/features/generation/api/get-video-status.ts`

### 修正
- `backend/app/core/slide_renderer.py` - CDN依存削除
- `backend/app/core/supabase.py` - video_jobs関数追加
- `backend/app/routers/render.py` - 非同期エンドポイント追加
- `backend/app/agents/slide_workflow.py` - Job トリガーに変更
- `frontend/src/types/index.ts` - VideoJobStatus型追加
- `frontend/src/features/generation/hooks/useReactAgent.ts` - ポーリング実装

---

## ローカル開発

### 環境変数

```bash
# backend/.env に追加
LOCAL_VIDEO_JOB=true  # ローカル環境でバックグラウンドスレッド実行
```

### 動作モード

| 環境変数 | 動作 |
|---------|------|
| `LOCAL_VIDEO_JOB=true` | バックグラウンドスレッドで即座に実行 |
| 未設定 or `false` | Cloud Run Job をトリガー（本番用） |

### ローカルテスト手順

```bash
# 1. FastAPIサーバー起動
cd backend/app
LOCAL_VIDEO_JOB=true python3 main.py

# 2. LangGraphサーバー起動
python3.11 -m langgraph_cli dev --host 0.0.0.0 --port 2024

# 3. フロントエンド起動
cd frontend
npm run dev

# 4. ブラウザでテスト → 動画生成が非同期で実行される
```

### 単体テスト（ジョブ処理のみ）

```bash
cd backend
JOB_ID=<job_id> python jobs/video_render_job.py
```

---

## 使用方法

1. Supabaseで `video_jobs` テーブルを作成（SQLは `migrations/002_create_video_jobs.sql`）
2. Cloud Run Job をデプロイ
3. mainブランチにマージ → 自動デプロイ
