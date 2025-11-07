# Firebase Hosting Deployment Guide

このドキュメントは、SlidePilotフロントエンドをFirebase Hostingにデプロイする手順を記載します。

## 前提条件

- Firebase CLI がインストール済み (`npm install -g firebase-tools`)
- Firebase プロジェクト `slide-pilot-474305` へのアクセス権限
- Google アカウント `miyata09x0084@gmail.com` でログイン済み

## デプロイ済み環境

- **Production URL**: https://slide-pilot-474305.web.app
- **Firebase Hosting URL**: https://slide-pilot-474305.firebaseapp.com
- **Project ID**: slide-pilot-474305
- **Region**: asia-northeast1

## アーキテクチャ

```
Frontend (Firebase Hosting)
    ↓
    /api/** → Cloud Run (slide-pilot-api)
              ↓
              FastAPI + LangGraph Proxy
```

Firebase Hosting は静的ファイルを配信し、`/api/**` へのリクエストを Cloud Run にリライトします（`frontend/firebase.json` に設定）。

## デプロイ手順

### 1. フロントエンドのビルド

```bash
cd /Users/miyata_ryo/projects/slide-pilot/frontend
npm run build
```

**確認事項**:
- ビルドが成功すること（通常 8-10秒）
- `dist/` ディレクトリが生成されること
- 警告（chunk size > 500KB）は無視可能

### 2. Firebase へのデプロイ

```bash
firebase deploy --only hosting --project slide-pilot-474305
```

**処理内容**:
1. Firebase プロジェクトの権限確認
2. `dist/` 内のファイルハッシュ計算（通常54ファイル）
3. 変更されたファイルのみアップロード
4. 新バージョンの有効化

**所要時間**: 約 30-60秒

### 3. デプロイ確認

```bash
# ブラウザで開く
open https://slide-pilot-474305.web.app

# または curl でヘルスチェック
curl -I https://slide-pilot-474305.web.app
```

**確認ポイント**:
- フロントエンドが正常に表示される
- Google OAuth ログインが機能する
- API呼び出し（`/api/health`）が Cloud Run に到達する

## トラブルシューティング

### デプロイが失敗する

**症状**: `Permission denied` エラー

**解決方法**:
```bash
# 再ログイン
firebase login --reauth

# プロジェクト確認
firebase projects:list
```

### 古いキャッシュが残る

**症状**: デプロイ後も古いバージョンが表示される

**解決方法**:
```bash
# ブラウザのハードリフレッシュ
# Chrome/Firefox: Cmd+Shift+R (Mac) / Ctrl+Shift+R (Windows)

# または Firebase Hosting キャッシュをクリア
firebase hosting:channel:delete <channel-id> --force
```

### Cloud Run との接続エラー

**症状**: `/api/**` が 404 や 502 を返す

**解決方法**:
1. `frontend/firebase.json` の rewrites 設定を確認
2. Cloud Run サービス `slide-pilot-api` が起動しているか確認:
   ```bash
   curl https://slide-pilot-api-692318722679.asia-northeast1.run.app/api/health
   ```

## デプロイ履歴

| Date       | Version (Short) | Changes                                      |
|------------|-----------------|----------------------------------------------|
| 2025-11-06 | ec3696c         | Feature-first architecture (PR #38)          |
| Previous   | -               | Initial deployment (pre-refactoring version) |

## 関連ファイル

- `frontend/firebase.json` - Firebase Hosting 設定
- `frontend/.firebaserc` - Firebase プロジェクト ID
- `frontend/vite.config.ts` - Vite ビルド設定
- `frontend/dist/` - ビルド成果物（gitignore）

## CI/CD への統合（将来）

現在は手動デプロイですが、GitHub Actions での自動化を検討できます:

```yaml
# .github/workflows/deploy-frontend.yml (例)
name: Deploy Frontend
on:
  push:
    branches: [main]
    paths: ['frontend/**']
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: cd frontend && npm ci && npm run build
      - uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: '${{ secrets.GITHUB_TOKEN }}'
          firebaseServiceAccount: '${{ secrets.FIREBASE_SERVICE_ACCOUNT }}'
          channelId: live
          projectId: slide-pilot-474305
```

## セキュリティ

- **認証**: Firebase Hosting は Google OAuth で保護されていない（公開サイト）
- **API保護**: Cloud Run 側で認証・認可を実装
- **環境変数**: `VITE_GOOGLE_CLIENT_ID` は `frontend/.env.local` に保存（gitignore）
- **シークレット**: Backend の API キーは Secret Manager で管理

## コスト

- **Firebase Hosting**: 無料枠内（10GB/月）
- **Cloud Run**: 従量課金（リクエスト数・実行時間）
- **LangGraph Cloud**: $39/月（Plus Plan）

## 参考資料

- [Firebase Hosting Documentation](https://firebase.google.com/docs/hosting)
- [Cloud Run Integration](https://firebase.google.com/docs/hosting/cloud-run)
- `docs/implementation-plans/DEPLOYMENT_PLAN_FIREBASE_CLOUDRUN.md` - 包括的なデプロイ計画
