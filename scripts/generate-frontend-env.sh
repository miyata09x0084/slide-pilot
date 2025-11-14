#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Frontend 環境変数生成スクリプト
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 機能:
#   - frontend/.env.schema.json から環境変数を読み込み
#   - .env.production ファイルを動的生成
#   - GitHub Actions環境変数リストを出力
#
# 使用方法:
#   ./scripts/generate-frontend-env.sh [--github-actions]
#
#   オプション:
#     --github-actions: GitHub Actions用の変数リストを出力
#     (省略時): .env.production ファイルを生成
#
# 前提条件:
#   - jq がインストール済み (brew install jq)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

SCHEMA_FILE="frontend/.env.schema.json"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
echo "⚙️  Frontend 環境変数生成" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
echo "" >&2
echo "📄 スキーマファイル: ${SCHEMA_FILE}" >&2
echo "" >&2

# jq のインストールチェック
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is not installed" >&2
    echo "   Install with: brew install jq" >&2
    exit 1
fi

# スキーマファイルの存在チェック
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "❌ Error: Schema file not found: ${SCHEMA_FILE}" >&2
    exit 1
fi

if [ "$1" == "--github-actions" ]; then
    # GitHub Actions用の変数リストを出力
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "📋 GitHub Secrets Required:" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "" >&2

    jq -r '.variables[] | select(.secret == true) | .name' "$SCHEMA_FILE" | while read -r var_name; do
        echo "  - $var_name" >&2
    done

    echo "" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "📋 Public Variables (can be in .env.production):" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "" >&2

    jq -r '.variables[] | select(.secret == false) | .name + "=" + (.production // .example)' "$SCHEMA_FILE"
else
    # .env.production ファイルを生成
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "📝 Generating .env.production..." >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    echo "" >&2

    cat <<EOF
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SlidePilot Frontend - Production Environment
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Auto-generated from frontend/.env.schema.json
# Last updated: $(date +"%Y-%m-%d %H:%M:%S")
#
# ⚠️  WARNING: Do NOT commit this file to git!
#    Secrets should be managed via GitHub Secrets.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

    # 本番環境用の値を出力
    jq -r '.variables[] | .name + "=" + (.production // .example)' "$SCHEMA_FILE"

    echo "" >&2
    echo "✅ .env.production generated successfully!" >&2
    echo "" >&2
    echo "💡 Usage:" >&2
    echo "   ./scripts/generate-frontend-env.sh > frontend/.env.production" >&2
    echo "" >&2
fi
