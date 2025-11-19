#!/usr/bin/env python3
"""
サンプルスライドをSupabaseに投入するスクリプト

Usage:
    cd backend
    python scripts/seed_sample_slides.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import uuid
from datetime import datetime

# プロジェクトルートを sys.path に追加
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# .env ファイルを読み込み
load_dotenv(backend_dir / ".env")

# Supabase クライアント初期化（app.core.supabaseを使用）
from app.core.supabase import get_supabase_client

supabase = get_supabase_client()
if not supabase:
    raise ValueError("Failed to initialize Supabase client")

# サンプルユーザーID（固定UUID）
SAMPLE_USER_ID = "00000000-0000-0000-0000-000000000000"

# サンプルスライドの定義
SAMPLE_SLIDES = [
    {
        "id": "11111111-1111-1111-1111-111111111111",  # 固定UUID
        "title": "多言語AIで文書解析",
        "md_file": "multilingual-ai-document-analysis_slidev.md",
        "pdf_file": "multilingual-ai-document-analysis_slidev.pdf",
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",  # 固定UUID
        "title": "2Dと3Dで学ぶ空間理解",
        "md_file": "learning-spatial-understanding-2d-3d_slidev.md",
        "pdf_file": "learning-spatial-understanding-2d-3d_slidev.pdf",
    },
]


def upload_pdf_to_storage(local_path: str, storage_path: str):
    """PDFファイルをSupabase Storageにアップロード"""
    with open(local_path, "rb") as f:
        pdf_data = f.read()

    try:
        # 既存ファイルを削除（エラー無視）
        supabase.storage().from_("slide-files").remove([storage_path])
    except Exception as e:
        print(f"  ⚠️  Delete failed (ok): {e}")

    # アップロード
    result = supabase.storage().from_("slide-files").upload(
        storage_path, pdf_data, {"content-type": "application/pdf"}
    )
    print(f"  ✅ PDF uploaded: {storage_path}")
    return result


def insert_slide_to_db(slide_id: str, title: str, slide_md: str, pdf_url: str):
    """スライドメタデータをSupabaseテーブルに挿入"""
    data = {
        "id": slide_id,
        "user_id": SAMPLE_USER_ID,
        "title": title,
        "topic": title,  # topicはtitleと同じ値を設定
        "slide_md": slide_md,
        "pdf_url": pdf_url,
        "created_at": datetime.utcnow().isoformat(),
    }

    # 既存レコードを削除（エラー無視）
    try:
        supabase.table("slides").delete().eq("id", slide_id).execute()
    except Exception:
        pass

    # 挿入
    result = supabase.table("slides").insert(data).execute()
    print(f"  ✅ Slide inserted: {title} (id: {slide_id})")
    return result


def main():
    print("🚀 サンプルスライド投入スクリプト開始\n")

    samples_dir = backend_dir / "data" / "samples"

    for sample in SAMPLE_SLIDES:
        print(f"📄 Processing: {sample['title']}")

        # 1. Markdownファイル読み込み
        md_path = samples_dir / sample["md_file"]
        if not md_path.exists():
            print(f"  ❌ Error: {md_path} not found")
            continue

        with open(md_path, "r", encoding="utf-8") as f:
            slide_md = f.read()
        print(f"  ✅ Markdown loaded: {len(slide_md)} chars")

        # 2. PDFファイルをStorageにアップロード
        pdf_path = samples_dir / sample["pdf_file"]
        if not pdf_path.exists():
            print(f"  ❌ Error: {pdf_path} not found")
            continue

        storage_path = f"{SAMPLE_USER_ID}/{sample['pdf_file']}"
        upload_pdf_to_storage(str(pdf_path), storage_path)

        # 公開URLを取得
        pdf_url = supabase.storage().from_("slide-files").get_public_url(storage_path)
        print(f"  ✅ Public URL: {pdf_url}")

        # 3. slidesテーブルに挿入
        insert_slide_to_db(sample["id"], sample["title"], slide_md, pdf_url)

        print()

    print("✅ サンプルスライド投入完了！\n")
    print("📋 投入されたスライド:")
    for sample in SAMPLE_SLIDES:
        print(f"  - {sample['title']} (UUID: {sample['id']})")


if __name__ == "__main__":
    main()
