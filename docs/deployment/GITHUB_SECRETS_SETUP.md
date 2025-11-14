# GitHub Secrets セットアップガイド

**作成日**: 2025-11-14
**対象**: SlidePilot CI/CD自動化
**所要時間**: 約30分

---

## 概要

GitHub ActionsでCI/CDを実行するために必要なSecretsの設定手順を記載します。

---

## 前提条件

- GitHubリポジトリへの管理者権限
- GCPプロジェクト `slide-pilot-474305` へのアクセス権限
- Firebase プロジェクトへのアクセス権限

---

## 必要なGitHub Secrets一覧

### Backend (Cloud Run) 用

| Secret名 | 説明 | 取得方法 |
|---------|------|---------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Provider ID | [手順1](#手順1-gcp-workload-identity連携設定) |
| `GCP_SERVICE_ACCOUNT` | サービスアカウントメールアドレス | [手順1](#手順1-gcp-workload-identity連携設定) |

### Frontend (Firebase Hosting) 用

| Secret名 | 説明 | 取得方法 |
|---------|------|---------|
| `FIREBASE_SERVICE_ACCOUNT` | Firebase Service Account JSON | [手順2](#手順2-firebase-service-account作成) |
| `VITE_API_URL` | Backend API URL | 既知の値 |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth Client ID | 既知の値 |
| `VITE_SUPABASE_URL` | Supabase プロジェクトURL | 既知の値 |
| `VITE_SUPABASE_ANON_KEY` | Supabase Anonymous Key | 既知の値 |

---

## 手順1: GCP Workload Identity連携設定

### 1-1. Workload Identity Pool作成

```bash
gcloud iam workload-identity-pools create "github-actions-pool" \
  --project="slide-pilot-474305" \
  --location="global" \
  --display-name="GitHub Actions Pool"
```

### 1-2. Workload Identity Provider作成

```bash
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="slide-pilot-474305" \
  --location="global" \
  --workload-identity-pool="github-actions-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

### 1-3. サービスアカウント作成

```bash
gcloud iam service-accounts create github-actions-sa \
  --project=slide-pilot-474305 \
  --display-name="GitHub Actions Service Account"
```

### 1-4. 権限付与

```bash
# Cloud Run管理者権限
gcloud projects add-iam-policy-binding slide-pilot-474305 \
  --member="serviceAccount:github-actions-sa@slide-pilot-474305.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Secret Manager アクセス権限
gcloud projects add-iam-policy-binding slide-pilot-474305 \
  --member="serviceAccount:github-actions-sa@slide-pilot-474305.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Cloud Build権限
gcloud projects add-iam-policy-binding slide-pilot-474305 \
  --member="serviceAccount:github-actions-sa@slide-pilot-474305.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"

# Artifact Registry権限
gcloud projects add-iam-policy-binding slide-pilot-474305 \
  --member="serviceAccount:github-actions-sa@slide-pilot-474305.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Service Account User権限
gcloud projects add-iam-policy-binding slide-pilot-474305 \
  --member="serviceAccount:github-actions-sa@slide-pilot-474305.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### 1-5. Workload Identity連携

```bash
gcloud iam service-accounts add-iam-policy-binding \
  github-actions-sa@slide-pilot-474305.iam.gserviceaccount.com \
  --project=slide-pilot-474305 \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/692318722679/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/miyata09x0084/slide-pilot"
```

### 1-6. Provider IDとService Account取得

```bash
# Workload Identity Provider ID取得
gcloud iam workload-identity-pools providers describe github-provider \
  --project=slide-pilot-474305 \
  --location=global \
  --workload-identity-pool=github-actions-pool \
  --format="value(name)"
```

**出力例**:
```
projects/692318722679/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider
```

この値を `GCP_WORKLOAD_IDENTITY_PROVIDER` としてGitHub Secretsに設定。

```bash
# Service Account Email取得
echo "github-actions-sa@slide-pilot-474305.iam.gserviceaccount.com"
```

この値を `GCP_SERVICE_ACCOUNT` としてGitHub Secretsに設定。

---

## 手順2: Firebase Service Account作成

### 2-1. Firebase CLIでトークン生成（推奨）

```bash
firebase login:ci
```

実行すると、ブラウザでGoogleログインが開きます。認証後、トークンが表示されます。

**出力例**:
```
✔  Success! Use this token to login on a CI server:

1//0gABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz
```

このトークンを `FIREBASE_SERVICE_ACCOUNT` としてGitHub Secretsに設定。

### 2-2. または、Service Account JSONダウンロード（代替方法）

1. Firebase Console → プロジェクト設定 → サービスアカウント
2. 「新しい秘密鍵の生成」をクリック
3. ダウンロードしたJSONファイルの内容をminify化:
   ```bash
   cat ~/Downloads/slide-pilot-474305-*.json | jq -c . | pbcopy
   ```
4. クリップボードの内容を `FIREBASE_SERVICE_ACCOUNT` に設定

---

## 手順3: Frontend環境変数取得

### 3-1. 既存の環境変数ファイルから取得

```bash
cd /Users/miyata_ryo/projects/slide-pilot/frontend

# API URL
echo "VITE_API_URL=https://slidepilot-api-692318722679.asia-northeast1.run.app/api"

# Google Client ID（既存の.env.localから）
grep VITE_GOOGLE_CLIENT_ID .env.local

# Supabase URL（既存の.env.localから）
grep VITE_SUPABASE_URL .env.local

# Supabase Anon Key（既存の.env.localから）
grep VITE_SUPABASE_ANON_KEY .env.local
```

これらの値をそれぞれGitHub Secretsに設定。

---

## 手順4: GitHub Secretsへの登録

### 4-1. GitHubリポジトリ設定画面へアクセス

1. https://github.com/miyata09x0084/slide-pilot にアクセス
2. **Settings** タブをクリック
3. 左メニューから **Secrets and variables** → **Actions** をクリック
4. **New repository secret** をクリック

### 4-2. 各Secretを登録

以下の7つのSecretsを登録:

| Name | Value | 取得元 |
|------|-------|--------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/692318722679/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider` | 手順1-6 |
| `GCP_SERVICE_ACCOUNT` | `github-actions-sa@slide-pilot-474305.iam.gserviceaccount.com` | 手順1-6 |
| `FIREBASE_SERVICE_ACCOUNT` | (Firebase CLIトークンまたはJSON) | 手順2 |
| `VITE_API_URL` | `https://slidepilot-api-692318722679.asia-northeast1.run.app/api` | 手順3-1 |
| `VITE_GOOGLE_CLIENT_ID` | `692318722679-j74jo1d8gecscbsr970cnuuun176pblv.apps.googleusercontent.com` | 手順3-1 |
| `VITE_SUPABASE_URL` | `https://smcgphoiyhroeqdwbvpr.supabase.co` | 手順3-1 |
| `VITE_SUPABASE_ANON_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` | 手順3-1 |

---

## 手順5: Secret Manager同期（Backend環境変数）

### 5-1. 不足しているSecretsを追加

```bash
cd /Users/miyata_ryo/projects/slide-pilot

# yqをインストール（まだの場合）
brew install yq

# Secret Manager同期スクリプト実行
./scripts/sync-secrets.sh
```

### 5-2. プレースホルダー値を実際の値で更新

スクリプトが新規作成したSecretsは、プレースホルダー値 `PLACEHOLDER_VALUE` が設定されています。
以下のコマンドで実際の値に更新してください。

```bash
# Supabase Anon Key
echo -n 'eyJhbGc...' | gcloud secrets versions add supabase-anon-key --data-file=-

# Supabase JWT Secret
echo -n 'your-jwt-secret' | gcloud secrets versions add supabase-jwt-secret --data-file=-

# 他の新規Secretsも同様に更新
```

**注意**: 既に値が設定されている既存Secretsは更新不要です（スクリプトがスキップします）。

---

## 手順6: 動作確認

### 6-1. テストコミット（Backend）

```bash
cd /Users/miyata_ryo/projects/slide-pilot

# 軽微な変更を追加
echo "# CI/CD test" >> backend/README.md
git add backend/README.md
git commit -m "test: Backend CI/CD pipeline"
git push origin main
```

### 6-2. GitHub Actions確認

1. https://github.com/miyata09x0084/slide-pilot/actions にアクセス
2. 「Deploy Backend to Cloud Run」ワークフローが実行中であることを確認
3. 緑色のチェックマークが表示されれば成功

### 6-3. テストコミット（Frontend）

```bash
# 軽微な変更を追加
echo "<!-- CI/CD test -->" >> frontend/README.md
git add frontend/README.md
git commit -m "test: Frontend CI/CD pipeline"
git push origin main
```

### 6-4. デプロイ確認

```bash
# Backend
curl https://slidepilot-api-692318722679.asia-northeast1.run.app/api/health

# Frontend
open https://slide-pilot-474305.web.app
```

---

## トラブルシューティング

### Workload Identity連携エラー

**症状**: `Permission denied` エラー

**解決方法**:
```bash
# Service Accountのバインディング確認
gcloud iam service-accounts get-iam-policy \
  github-actions-sa@slide-pilot-474305.iam.gserviceaccount.com

# リポジトリ名が正しいか確認（miyata09x0084/slide-pilot）
```

### Firebase デプロイエラー

**症状**: `HTTP Error: 403, The caller does not have permission`

**解決方法**:
```bash
# 新しいトークン生成
firebase login:ci --reauth

# GitHub Secretsを更新
```

### Secret Manager アクセスエラー

**症状**: `Secret not found` または `Permission denied`

**解決方法**:
```bash
# Secretの存在確認
gcloud secrets list

# 権限確認
gcloud secrets get-iam-policy <secret-name>

# 必要に応じて権限追加
gcloud secrets add-iam-policy-binding <secret-name> \
  --member="serviceAccount:692318722679-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 参考資料

- [GitHub Actions - Workload Identity連携](https://github.com/google-github-actions/auth)
- [Firebase Hosting GitHub Actions](https://github.com/FirebaseExtended/action-hosting-deploy)
- [Cloud Run デプロイガイド](https://cloud.google.com/run/docs/deploying)

---

**最終更新**: 2025-11-14
**作成者**: Claude Code
