"""
ヘルスチェックルーター
"""

from fastapi import APIRouter, Depends
from pathlib import Path
from app.dependencies import get_upload_dir

router = APIRouter()


@router.get("/health")
async def health_check(upload_dir: Path = Depends(get_upload_dir)):
    """ヘルスチェックエンドポイント"""
    return {
        "status": "ok",
        "upload_dir": str(upload_dir),
        "upload_dir_exists": upload_dir.exists()
    }
