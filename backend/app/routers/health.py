"""
ヘルスチェックルーター

Issue #29: Supabase Storage移行対応
"""

from fastapi import APIRouter
from app.config import settings
from app.core.supabase import get_supabase_client

router = APIRouter()


@router.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    # Supabase接続確認
    supabase_status = "connected" if get_supabase_client() else "not configured"

    return {
        "status": "ok",
        "supabase": supabase_status,
        "tokens_dir": str(settings.TOKENS_DIR),
        "tokens_dir_exists": settings.TOKENS_DIR.exists()
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    詳細ヘルスチェックエンドポイント

    Supabase DB/Storageの疎通確認を行い、障害時はdegraded_mode=trueを返す
    """
    client = get_supabase_client()

    # Supabase DB疎通確認
    supabase_db_ok = False
    supabase_db_error = None
    if client:
        try:
            # slidesテーブルから1件取得して疎通確認
            result = client.table("slides").select("id").limit(1).execute()
            supabase_db_ok = True
        except Exception as e:
            supabase_db_error = str(e)[:100]

    # Supabase Storage疎通確認
    supabase_storage_ok = False
    supabase_storage_error = None
    if client:
        try:
            # バケット一覧を取得して疎通確認
            buckets = client.storage.list_buckets()
            supabase_storage_ok = True
        except Exception as e:
            supabase_storage_error = str(e)[:100]

    # 全体の状態判定
    all_ok = supabase_db_ok and supabase_storage_ok

    return {
        "status": "ok" if all_ok else "degraded",
        "supabase_configured": client is not None,
        "supabase_db": {
            "status": "ok" if supabase_db_ok else "down",
            "error": supabase_db_error
        },
        "supabase_storage": {
            "status": "ok" if supabase_storage_ok else "down",
            "error": supabase_storage_error
        },
        "degraded_mode": not all_ok
    }
