#!/usr/bin/env python3
"""
既存スライドをサンプルスライドに設定するスクリプト

指定したスライドIDのuser_idをサンプル用ID (00000000-...) に更新し、
全ユーザーがアクセス可能にする。

Usage:
    cd backend
    python scripts/seed_sample_slides.py
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

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
# 注意: このスクリプトは既存スライドのuser_idを更新するモードに変更
# 新規作成ではなく、既にSupabaseに存在するスライドをサンプル化する
SAMPLE_SLIDE_IDS = [
    "862ae7f8-793f-4a39-9c7c-a003659b213c",  # 疑似科学を見抜く力
    "743cb44b-8546-47f9-bd91-2caebb423dab",  # 映画制作の未来
    "91997e40-ff18-45fc-b106-e5d568fd5725",  # 未来予測AI
]


def update_slide_to_sample(slide_id: str):
    """既存スライドのuser_idをサンプル用IDに更新"""
    result = (
        supabase.table("slides")
        .update({"user_id": SAMPLE_USER_ID})
        .eq("id", slide_id)
        .execute()
    )
    return result


def main():
    print("🚀 サンプルスライド設定スクリプト開始\n")
    print(f"サンプルユーザーID: {SAMPLE_USER_ID}\n")

    updated = []
    failed = []

    for slide_id in SAMPLE_SLIDE_IDS:
        print(f"📄 Processing: {slide_id}")

        # スライドが存在するか確認
        result = supabase.table("slides").select("id, title").eq("id", slide_id).execute()

        if not result.data:
            print(f"  ❌ Error: スライドが見つかりません")
            failed.append(slide_id)
            continue

        title = result.data[0]["title"]

        # user_idを更新
        update_slide_to_sample(slide_id)
        print(f"  ✅ Updated: {title}")
        updated.append({"id": slide_id, "title": title})
        print()

    print("=" * 50)
    print(f"✅ 更新完了: {len(updated)}件")
    for item in updated:
        print(f"  - {item['title']} ({item['id']})")

    if failed:
        print(f"\n❌ 失敗: {len(failed)}件")
        for slide_id in failed:
            print(f"  - {slide_id}")


if __name__ == "__main__":
    main()
