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
