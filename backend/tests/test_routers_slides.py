"""スライドエンドポイントのテスト

Issue: Supabase Auth統合
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.fixtures.jwt_helper import generate_test_jwt

client = TestClient(app)


def test_list_slides_with_valid_jwt(monkeypatch, mocker):
    """正常なJWTでスライド一覧取得成功"""
    test_jwt = generate_test_jwt(user_id="user-456")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    # slides.py内で呼ばれるget_supabase_clientとget_slides_by_userをモック
    mocker.patch(
        "app.routers.slides.get_supabase_client",
        return_value=mocker.MagicMock()
    )
    mocker.patch(
        "app.routers.slides.get_slides_by_user",
        return_value=[{"id": "1", "title": "Test", "user_id": "user-456"}]
    )

    response = client.get(
        "/api/slides",
        headers={"Authorization": f"Bearer {test_jwt}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["slides"]) > 0
    assert data["slides"][0]["user_id"] == "user-456"


def test_list_slides_without_jwt():
    """JWT未提供時に403エラー"""
    response = client.get("/api/slides")
    assert response.status_code == 403


def test_download_slide_user_id_mismatch(monkeypatch, mocker):
    """user_id不一致時に403エラー"""
    test_jwt = generate_test_jwt(user_id="user-789")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    # slides.py内で呼ばれるget_supabase_clientをモック
    mocker.patch(
        "app.routers.slides.get_supabase_client",
        return_value=mocker.MagicMock()
    )

    response = client.get(
        "/api/slides/other-user/test.pdf",
        headers={"Authorization": f"Bearer {test_jwt}"}
    )

    assert response.status_code == 403
    assert "他のユーザーのファイルにはアクセスできません" in response.json()["detail"]
