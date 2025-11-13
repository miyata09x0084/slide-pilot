"""Supabase JWT検証ミドルウェア

Issue: Supabase Auth統合
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional
import os

# HTTPBearer スキーマ
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


def get_supabase_jwt_secret() -> str:
    """Supabase JWT Secretを取得

    Returns:
        JWT Secret（環境変数SUPABASE_JWT_SECRET）

    Raises:
        HTTPException: 環境変数未設定時503エラー
    """
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPABASE_JWT_SECRET not configured"
        )
    return jwt_secret


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Supabase JWTを検証してuser_idを返す

    Args:
        credentials: Authorization ヘッダーから取得したJWT

    Returns:
        user_id (UUID文字列)

    Raises:
        HTTPException: JWT検証失敗時401エラー
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )

    token = credentials.credentials
    jwt_secret = get_supabase_jwt_secret()

    try:
        # JWT検証・デコード
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )

        # user_id取得（Supabaseは"sub"クレームにUUIDを格納）
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )

        return user_id

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


async def optional_verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> str:
    """JWT検証（オプショナル）、未認証時は"anonymous"を返す

    Args:
        credentials: Authorization ヘッダー（オプショナル）

    Returns:
        user_id (UUID) または "anonymous"
    """
    if not credentials:
        return "anonymous"

    try:
        return await verify_token(credentials)
    except HTTPException:
        return "anonymous"
