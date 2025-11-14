#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Secret Manager 同期スクリプト
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 機能:
#   - backend/.env.schema.yml を読み込み
#   - Secret Managerに未登録のシークレットを検出
#   - プレースホルダー値で自動作成
#
# 使用方法:
#   ./scripts/sync-secrets.sh
#
# 前提条件:
#   - yq がインストール済み (brew install yq)
#   - gcloud CLI がインストール済み
#   - GCPプロジェクトにログイン済み
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

PROJECT_ID="slide-pilot-474305"
SCHEMA_FILE="backend/.env.schema.yml"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 Secret Manager 同期スクリプト"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📄 スキーマファイル: ${SCHEMA_FILE}"
echo "☁️  GCPプロジェクト: ${PROJECT_ID}"
echo ""

# yq のインストールチェック
if ! command -v yq &> /dev/null; then
    echo "❌ Error: yq is not installed"
    echo "   Install with: brew install yq"
    exit 1
fi

# スキーマファイルの存在チェック
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "❌ Error: Schema file not found: ${SCHEMA_FILE}"
    exit 1
fi

# GCPプロジェクトの確認
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo "⚠️  Warning: Current GCP project is '$CURRENT_PROJECT'"
    echo "   Expected: '$PROJECT_ID'"
    echo ""
    read -p "   Switch to $PROJECT_ID? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gcloud config set project "$PROJECT_ID"
    else
        echo "❌ Aborted"
        exit 1
    fi
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 既存シークレット一覧"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
gcloud secrets list --format="table(name)" 2>/dev/null | tail -n +2 | sort
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 スキーマから読み込み中..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CREATED_COUNT=0
SKIPPED_COUNT=0

# Parse YAML and create secrets
yq eval '.secrets[] | .name' "$SCHEMA_FILE" | while read -r secret_name; do
  secret_id=$(echo "$secret_name" | tr '[:upper:]' '[:lower:]' | tr '_' '-')

  # Check if secret exists
  if gcloud secrets describe "$secret_id" --project="$PROJECT_ID" &>/dev/null; then
    echo "✅ Secret already exists: $secret_id"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
  else
    echo "📝 Creating secret: $secret_id"

    # Placeholder value - user must update manually
    echo -n "PLACEHOLDER_VALUE" | gcloud secrets create "$secret_id" \
      --project="$PROJECT_ID" \
      --data-file=- \
      --replication-policy="automatic"

    echo "   ⚠️  Please update secret value manually:"
    echo "      echo -n 'ACTUAL_VALUE' | gcloud secrets versions add $secret_id --data-file=-"
    echo ""
    CREATED_COUNT=$((CREATED_COUNT + 1))
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Secret sync complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Summary:"
echo "   - Created: ${CREATED_COUNT} secrets"
echo "   - Skipped: ${SKIPPED_COUNT} secrets (already exist)"
echo ""

if [ "$CREATED_COUNT" -gt 0 ]; then
    echo "⚠️  Next steps:"
    echo "   1. Update placeholder values with actual secrets"
    echo "   2. Verify all secrets are correctly set:"
    echo "      gcloud secrets list --format='table(name)'"
    echo ""
fi
