"""LangGraphエージェントプロキシのテスト

Issue: Supabase Auth統合
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.fixtures.jwt_helper import generate_test_jwt

client = TestClient(app)


def test_stream_run_injects_user_id(monkeypatch, mocker):
    """JWTからuser_idを抽出してLangGraph inputに注入"""
    test_jwt = generate_test_jwt(user_id="user-789")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")

    # LangGraph APIモック（SSEストリーム）
    captured_json = {}

    # モックレスポンス
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = mocker.MagicMock()

    async def mock_aiter_bytes():
        yield b'data: {"event": "updates"}\n\n'

    mock_response.aiter_bytes = mock_aiter_bytes

    # streamコンテキストマネージャーをモック
    class MockStreamContext:
        def __init__(self, response):
            self.response = response

        async def __aenter__(self):
            return self.response

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    # AsyncClientをモック
    def mock_stream_factory(method, url, **kwargs):
        captured_json.update(kwargs)
        return MockStreamContext(mock_response)

    mock_async_client = mocker.MagicMock()
    mock_async_client.stream = mock_stream_factory
    mock_async_client.__aenter__ = mocker.AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = mocker.AsyncMock()

    mocker.patch("httpx.AsyncClient", return_value=mock_async_client)

    response = client.post(
        "/api/agent/threads/test-thread/runs/stream",
        json={"assistant_id": "test", "input": {"topic": "AI"}},
        headers={"Authorization": f"Bearer {test_jwt}"}
    )

    assert response.status_code == 200

    # user_idがinputに注入されていることを確認
    assert captured_json["json"]["input"]["user_id"] == "user-789"
    assert captured_json["json"]["input"]["topic"] == "AI"


def test_stream_run_anonymous(mocker):
    """JWT未提供時はanonymousでLangGraph実行"""
    # LangGraph APIモック（SSEストリーム）
    captured_json = {}

    # モックレスポンス
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = mocker.MagicMock()

    async def mock_aiter_bytes():
        yield b'data: {"event": "updates"}\n\n'

    mock_response.aiter_bytes = mock_aiter_bytes

    # streamコンテキストマネージャーをモック
    class MockStreamContext:
        def __init__(self, response):
            self.response = response

        async def __aenter__(self):
            return self.response

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    # AsyncClientをモック
    def mock_stream_factory(method, url, **kwargs):
        captured_json.update(kwargs)
        return MockStreamContext(mock_response)

    mock_async_client = mocker.MagicMock()
    mock_async_client.stream = mock_stream_factory
    mock_async_client.__aenter__ = mocker.AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = mocker.AsyncMock()

    mocker.patch("httpx.AsyncClient", return_value=mock_async_client)

    response = client.post(
        "/api/agent/threads/test-thread/runs/stream",
        json={"assistant_id": "test", "input": {"topic": "AI"}}
    )

    assert response.status_code == 200

    # user_idが"anonymous"として注入されていることを確認
    assert captured_json["json"]["input"]["user_id"] == "anonymous"
    assert captured_json["json"]["input"]["topic"] == "AI"
