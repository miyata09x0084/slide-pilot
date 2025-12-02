"""認証テスト用エンドポイント

Issue: Supabase Auth統合
"""

from fastapi import APIRouter, Depends
from app.auth.middleware import verify_token

router = APIRouter()


@router.get("/auth/me")
async def get_current_user(authenticated_user_id: str = Depends(verify_token)):
    """現在の認証ユーザー情報を取得（JWT検証テスト用）

    Args:
        authenticated_user_id: JWT検証で取得したユーザーID

    Returns:
        {"authenticated_user_id": str}
    """
    return {"authenticated_user_id": authenticated_user_id}
