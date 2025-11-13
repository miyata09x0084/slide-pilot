"""テスト用JWT生成ヘルパー

Issue: Supabase Auth統合
"""
import jwt
from datetime import datetime, timedelta


def generate_test_jwt(
    user_id: str = "test-user-uuid",
    secret: str = "test-secret",
    exp_minutes: int = 60
) -> str:
    """テスト用のSupabase風JWTを生成

    Args:
        user_id: ユーザーID（UUID）
        secret: JWT署名用シークレット
        exp_minutes: 有効期限（分）

    Returns:
        JWT文字列
    """
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": datetime.utcnow() + timedelta(minutes=exp_minutes),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, secret, algorithm="HS256")
