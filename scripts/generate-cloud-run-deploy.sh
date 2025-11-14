#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cloud Run デプロイコマンド生成スクリプト
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 機能:
#   - backend/.env.schema.yml から環境変数を読み込み
#   - gcloud run deploy コマンドを動的生成
#   - Secret Manager連携とenv_varsを自動設定
#
# 使用方法:
#   ./scripts/generate-cloud-run-deploy.sh [--execute]
#
#   オプション:
#     --execute: コマンドを生成して即座に実行
#     (省略時): コマンドを標準出力に表示のみ
#
# 前提条件:
#   - yq がインストール済み (brew install yq)
#   - gcloud CLI がインストール済み
#   - Docker イメージがビルド済み
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

PROJECT_ID="slide-pilot-474305"
SERVICE_NAME="slidepilot-api"
REGION="asia-northeast1"
SCHEMA_FILE="backend/.env.schema.yml"
IMAGE_NAME="asia-northeast1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
echo "🚀 Cloud Run デプロイコマンド生成" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
echo "" >&2
echo "📄 スキーマファイル: ${SCHEMA_FILE}" >&2
echo "☁️  GCPプロジェクト: ${PROJECT_ID}" >&2
echo "🐳 イメージ: ${IMAGE_NAME}:latest" >&2
echo "" >&2

# yq のインストールチェック
if ! command -v yq &> /dev/null; then
    echo "❌ Error: yq is not installed" >&2
    echo "   Install with: brew install yq" >&2
    exit 1
fi

# スキーマファイルの存在チェック
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "❌ Error: Schema file not found: ${SCHEMA_FILE}" >&2
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
echo "🔐 Secrets 読み込み中..." >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

# Generate --set-secrets flag
SECRETS=$(yq eval '.secrets[] | .name' "$SCHEMA_FILE" | while read -r name; do
  secret_id=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
  echo "${name}=${secret_id}:latest"
done | paste -sd ",")

echo "✅ Secrets: $(echo "$SECRETS" | tr ',' '\n' | wc -l | tr -d ' ') items" >&2
echo "" >&2

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
echo "⚙️  Environment Variables 読み込み中..." >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

# Generate --set-env-vars flag
ENV_VARS=$(yq eval '.env_vars[] | .name + "=" + .value' "$SCHEMA_FILE" | paste -sd ",")

echo "✅ Env Vars: $(echo "$ENV_VARS" | tr ',' '\n' | wc -l | tr -d ' ') items" >&2
echo "" >&2

# Generate full command
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
  --image=\"${IMAGE_NAME}:latest\" \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300 \
  --max-instances=100 \
  --min-instances=0 \
  --set-secrets=\"$SECRETS\" \
  --set-env-vars=\"$ENV_VARS\""

# Output or execute
if [ "$1" == "--execute" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "🚢 Deploying to Cloud Run..." >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "" >&2
    eval "$DEPLOY_CMD"
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "📋 Generated Deploy Command:" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "" >&2
    echo "$DEPLOY_CMD"
    echo "" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "💡 To execute this command, run:" >&2
    echo "   ./scripts/generate-cloud-run-deploy.sh --execute" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
fi
