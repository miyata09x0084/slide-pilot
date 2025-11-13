"""PDFアップロードエンドポイントのテスト

Issue: Supabase Auth統合
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.fixtures.jwt_helper import generate_test_jwt

client = TestClient(app)


def test_upload_pdf_with_valid_jwt(monkeypatch, mocker):
    """正常なJWTでPDFアップロード成功"""
    test_jwt = generate_test_jwt(user_id="user-123")
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

    pdf_content = b"%PDF-1.4\n%Test PDF"
    files = {"file": ("test.pdf", pdf_content, "application/pdf")}

    response = client.post(
        "/api/upload-pdf",
        files=files,
        headers={"Authorization": f"Bearer {test_jwt}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "user-123" in data["path"]
    assert data["filename"] == "test.pdf"


def test_upload_pdf_without_jwt():
    """JWT未提供時に403エラー"""
    pdf_content = b"%PDF-1.4\n%Test"
    files = {"file": ("test.pdf", pdf_content, "application/pdf")}

    response = client.post("/api/upload-pdf", files=files)
    assert response.status_code == 403


def test_upload_pdf_with_invalid_jwt(monkeypatch):
    """不正なJWTで401エラー"""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    pdf_content = b"%PDF-1.4\n%Test"
    files = {"file": ("test.pdf", pdf_content, "application/pdf")}

    response = client.post(
        "/api/upload-pdf",
        files=files,
        headers={"Authorization": "Bearer invalid-jwt"}
    )

    assert response.status_code == 401
