"""JWT検証ミドルウェアのテスト

Issue: Supabase Auth統合
"""
import pytest
from fastapi import HTTPException
from app.auth.middleware import verify_token, optional_verify_token
from tests.fixtures.jwt_helper import generate_test_jwt


# ──────────────────────────────────────────────────────────────
# 正常系テスト
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_token_success(monkeypatch):
    """正常なJWTでuser_idが取得できること"""
    # テスト用JWT生成
    test_jwt = generate_test_jwt(user_id="test-uuid-123")

    # 環境変数モック
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    # HTTPAuthorizationCredentials モック
    from fastapi.security import HTTPAuthorizationCredentials
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=test_jwt
    )

    # 実行
    user_id = await verify_token(credentials)

    # 検証
    assert user_id == "test-uuid-123"


@pytest.mark.asyncio
async def test_optional_verify_token_returns_anonymous_when_no_token():
    """JWT未提供時は"anonymous"を返すこと"""
    user_id = await optional_verify_token(None)
    assert user_id == "anonymous"


# ──────────────────────────────────────────────────────────────
# 異常系テスト
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_token_invalid_signature(monkeypatch):
    """不正な署名のJWTで401エラーが返ること"""
    # 間違ったシークレットで署名
    test_jwt = generate_test_jwt(user_id="test-uuid", secret="wrong-secret")

    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    from fastapi.security import HTTPAuthorizationCredentials
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=test_jwt
    )

    # 実行 → 401エラー
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(credentials)

    assert exc_info.value.status_code == 401
    assert "Invalid token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_token_expired(monkeypatch):
    """有効期限切れJWTで401エラーが返ること"""
    # 有効期限-1分のJWT生成
    test_jwt = generate_test_jwt(user_id="test-uuid", exp_minutes=-1)

    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    from fastapi.security import HTTPAuthorizationCredentials
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=test_jwt
    )

    with pytest.raises(HTTPException) as exc_info:
        await verify_token(credentials)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_token_missing_sub_claim(monkeypatch):
    """subクレーム欠落時に401エラーが返ること"""
    # sub クレームなしのJWT
    import jwt
    from datetime import datetime, timedelta

    payload = {
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(minutes=60),
    }
    test_jwt = jwt.encode(payload, "test-secret", algorithm="HS256")

    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    from fastapi.security import HTTPAuthorizationCredentials
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=test_jwt
    )

    with pytest.raises(HTTPException) as exc_info:
        await verify_token(credentials)

    assert exc_info.value.status_code == 401
    assert "missing user_id" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_token_missing_jwt_secret():
    """環境変数SUPABASE_JWT_SECRET未設定時に503エラー"""
    import os
    # 環境変数を削除
    os.environ.pop("SUPABASE_JWT_SECRET", None)

    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="dummy-token"
    )

    with pytest.raises(HTTPException) as exc_info:
        await verify_token(credentials)

    assert exc_info.value.status_code == 503
    assert "SUPABASE_JWT_SECRET not configured" in exc_info.value.detail
