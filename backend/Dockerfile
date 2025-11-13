# ──────────────────────────────────────────────────────────────
# SlidePilot Backend - LangGraph Cloud版 Dockerfile
#
# 変更内容（2025-11-03）:
# - LangGraph devサーバーを削除（LangSmith Cloudを使用）
# - Supervisorを削除（単一プロセス）
# - Node.js/Slidev/Playwrightを削除（不要）
# - イメージサイズ: 3.82GB → 500MB（85%削減）
#
# 変更内容（2025-11-10）:
# - Supabase Storage対応（Issue #29完全統合）
# ──────────────────────────────────────────────────────────────

FROM python:3.11-slim

WORKDIR /app

# 最小限のシステム依存関係
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Python依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションコード
COPY ./app /app/app

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# FastAPIのみ起動（単一プロセス）
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
