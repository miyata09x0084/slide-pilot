"""認証フロー全体のE2Eテスト

Issue: Supabase Auth統合
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.fixtures.jwt_helper import generate_test_jwt

client = TestClient(app)


def test_full_auth_flow(monkeypatch, mocker):
    """認証フロー全体が正常動作"""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    # Supabaseクライアントをモック（storage.pyで使用される）
    mock_storage = mocker.MagicMock()
    mock_storage.upload.return_value = None
    mock_storage.create_signed_url.return_value = {"signedURL": "https://test-url"}

    mock_from = mocker.MagicMock()
    mock_from.return_value = mock_storage

    mock_storage_client = mocker.MagicMock()
    mock_storage_client.from_ = mock_from

    mock_supabase = mocker.MagicMock()
    mock_supabase.storage = mock_storage_client

    # storage.py内で呼ばれるget_supabase_clientをモック
    mocker.patch("app.core.storage.get_supabase_client", return_value=mock_supabase)

    # slides.py内で呼ばれるget_supabase_clientとget_slides_by_userをモック
    mocker.patch("app.routers.slides.get_supabase_client", return_value=mock_supabase)
    mocker.patch("app.routers.slides.get_slides_by_user", return_value=[])

    # ユーザーA: PDFアップロード
    jwt_a = generate_test_jwt(user_id="user-a")
    response = client.post(
        "/api/upload-pdf",
        files={"file": ("test.pdf", b"%PDF", "application/pdf")},
        headers={"Authorization": f"Bearer {jwt_a}"}
    )
    assert response.status_code == 200
    assert "user-a" in response.json()["path"]

    # ユーザーB: 別のスライド一覧取得
    jwt_b = generate_test_jwt(user_id="user-b")
    response = client.get(
        "/api/slides",
        headers={"Authorization": f"Bearer {jwt_b}"}
    )
    assert response.status_code == 200
    assert response.json()["slides"] == []  # RLSで分離（モックでは空配列）


def test_auth_me_endpoint(monkeypatch):
    """JWT検証テストエンドポイント動作確認"""
    test_jwt = generate_test_jwt(user_id="test-user-123")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {test_jwt}"}
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == "test-user-123"
