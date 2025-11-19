#!/usr/bin/env python3
"""
サンプルスライドを最新フォーマットに更新するスクリプト

Supabaseから最新の良質なスライドを取得し、
サンプルユーザーIDで再登録する
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートを sys.path に追加
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# .env ファイルを読み込み
load_dotenv(backend_dir / ".env")

from app.core.supabase import get_supabase_client

# サンプルユーザーID
SAMPLE_USER_ID = "00000000-0000-0000-0000-000000000000"

# 固定サンプルスライドID
SAMPLE_SLIDE_IDS = [
    "11111111-1111-1111-1111-111111111111",  # サンプル1
    "22222222-2222-2222-2222-222222222222",  # サンプル2
]

# Supabaseから取得する良質なスライド
SOURCE_SLIDES = [
    {
        "source_id": "b9292261-3510-4fd1-8b1c-1409d22d7b5f",  # 「速いAIの秘密」
        "new_id": SAMPLE_SLIDE_IDS[0],
    },
    {
        "source_id": "9a0e6237-7b28-455b-a2f8-2c6071603fe4",  # 「AIアートの革命」
        "new_id": SAMPLE_SLIDE_IDS[1],
    },
]


def main():
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Failed to initialize Supabase client")
        return

    print("🚀 サンプルスライド更新開始\n")

    for source in SOURCE_SLIDES:
        print(f"📄 Processing source: {source['source_id']}")

        # 1. ソーススライドを取得
        response = supabase.table("slides").select("*").eq("id", source["source_id"]).execute()

        if not response.data:
            print(f"  ❌ Source slide not found: {source['source_id']}")
            continue

        source_slide = response.data[0]
        print(f"  ✅ Source loaded: {source_slide['title']}")

        # 2. 既存サンプルを削除
        try:
            supabase.table("slides").delete().eq("id", source["new_id"]).execute()
            print(f"  ✅ Old sample deleted: {source['new_id']}")
        except Exception as e:
            print(f"  ⚠️  Delete failed (ok): {e}")

        # 3. 新しいサンプルとして登録
        new_sample = {
            "id": source["new_id"],
            "user_id": SAMPLE_USER_ID,
            "title": source_slide["title"],
            "topic": source_slide["topic"],
            "slide_md": source_slide["slide_md"],
            "pdf_url": source_slide.get("pdf_url"),
            "created_at": source_slide["created_at"],
        }

        try:
            supabase.table("slides").insert(new_sample).execute()
            print(f"  ✅ New sample inserted: {source_slide['title']}")
        except Exception as e:
            print(f"  ❌ Insert failed: {e}")

        print()

    print("✅ サンプルスライド更新完了！\n")
    print("📋 更新されたサンプルスライド:")
    for i, source in enumerate(SOURCE_SLIDES, 1):
        response = supabase.table("slides").select("title").eq("id", source["new_id"]).execute()
        if response.data:
            print(f"  {i}. {response.data[0]['title']} (UUID: {source['new_id']})")


if __name__ == "__main__":
    main()
