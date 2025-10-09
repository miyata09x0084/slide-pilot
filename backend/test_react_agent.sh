#!/bin/bash
# ReActエージェントのテストスクリプト
#
# 前提条件:
# 1. langgraph devが起動している（別ターミナルで実行）
# 2. credentials.jsonが配置されている
#
# 使い方:
# chmod +x test_react_agent.sh
# ./test_react_agent.sh

set -e  # エラーで停止

echo "========================================="
echo "ReActエージェント curlテスト"
echo "========================================="
echo ""

# スレッド作成
echo "[1] スレッド作成中..."
THREAD_RESPONSE=$(curl -s -X POST http://localhost:2024/threads \
  -H "Content-Type: application/json" \
  -d '{}')

THREAD_ID=$(echo $THREAD_RESPONSE | jq -r '.thread_id')

if [ -z "$THREAD_ID" ] || [ "$THREAD_ID" = "null" ]; then
  echo "❌ エラー: スレッド作成失敗"
  echo "Response: $THREAD_RESPONSE"
  exit 1
fi

echo "✅ Thread ID: $THREAD_ID"
echo ""

# テスト1: スライド生成のみ
echo "[2] テスト1: スライド生成のみ"
echo "----------------------------------------"
curl -N -X POST "http://localhost:2024/threads/${THREAD_ID}/runs/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "react-agent",
    "input": {
      "messages": [
        {"role": "user", "content": "AI最新情報のスライドを作って"}
      ]
    },
    "stream_mode": ["updates"]
  }'

echo ""
echo ""

# テスト2: 無効なメールアドレス（エラーハンドリング）
echo "[3] テスト2: 無効なメールアドレス"
echo "----------------------------------------"
curl -N -X POST "http://localhost:2024/threads/${THREAD_ID}/runs/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "react-agent",
    "input": {
      "messages": [
        {"role": "user", "content": "invalid-emailにメール送って"}
      ]
    },
    "stream_mode": ["updates"]
  }'

echo ""
echo ""
echo "========================================="
echo "✅ テスト完了"
echo "========================================="
echo ""
echo "次のステップ:"
echo "1. Gmail送信テスト（credentials.json配置後）"
echo "2. スライド生成 + Gmail送信の統合テスト"
