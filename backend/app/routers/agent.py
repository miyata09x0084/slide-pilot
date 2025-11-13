"""
LangGraphエージェントAPIプロキシルーター

LangGraphサーバー (localhost:2024) へのリクエストをプロキシし、
フロントエンドが単一エンドポイント (localhost:8001) で全機能にアクセスできるようにする。

Issue: Supabase Auth統合
"""

from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import StreamingResponse
import httpx
import asyncio
import os
from typing import Any, Dict

from app.auth.middleware import optional_verify_token

router = APIRouter()

# LangGraph Cloud設定
DEPLOYMENT_ID = os.getenv("LANGGRAPH_DEPLOYMENT_ID", "local")

# ローカル開発との切り替え
if DEPLOYMENT_ID == "local":
    # ローカル開発: langgraph dev使用
    LANGGRAPH_API_URL = "http://localhost:2024"
    print("[agent] Using local LangGraph dev server: http://localhost:2024")
else:
    # 本番: LangSmith Cloud使用（完全なDeployment URLを環境変数から取得）
    LANGGRAPH_API_URL = os.getenv("LANGGRAPH_CLOUD_URL")
    if not LANGGRAPH_API_URL:
        raise ValueError("LANGGRAPH_CLOUD_URL environment variable must be set for production deployment")
    print(f"[agent] Using LangSmith Cloud: {LANGGRAPH_API_URL}")

# 認証ヘッダー
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")

# タイムアウト設定（LLM処理が長時間かかる可能性があるため長めに設定）
TIMEOUT = httpx.Timeout(300.0, connect=10.0)

# リトライ設定（LangSmith Cloudでは不要だが、ローカル用に残す）
MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds


async def wait_for_langgraph(max_retries: int = MAX_RETRIES, retry_delay: float = RETRY_DELAY) -> bool:
    """
    LangGraphサーバーの起動を待つ

    起動直後のコンテナで、LangGraphが完全起動するまで待機する。
    最大10秒（5回 × 2秒）待機し、起動完了後にTrueを返す。

    Args:
        max_retries: 最大リトライ回数
        retry_delay: リトライ間隔（秒）

    Returns:
        bool: 起動成功時True

    Raises:
        HTTPException: タイムアウト時503エラー
    """
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{LANGGRAPH_API_URL}/ok")
                if response.status_code == 200:
                    return True
        except (httpx.ConnectError, httpx.TimeoutException):
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"LangGraphサーバーが起動していません。{max_retries * retry_delay}秒待機しましたが、接続できませんでした。"
                )
    return False


@router.post("/threads")
async def create_thread(request: Request):
    """
    LangGraphスレッドを作成

    LangGraphの /threads エンドポイントへプロキシ
    """
    try:
        # ローカル開発の場合のみLangGraphの起動を待機
        if DEPLOYMENT_ID == "local":
            await wait_for_langgraph()

        body = await request.json()

        # 認証ヘッダー準備
        headers = {}
        if LANGCHAIN_API_KEY and DEPLOYMENT_ID != "local":
            headers["X-Api-Key"] = LANGCHAIN_API_KEY

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{LANGGRAPH_API_URL}/threads",
                json=body,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"LangGraphサーバーに接続できません: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thread作成エラー: {str(e)}")


@router.post("/assistants/search")
async def search_assistants(request: Request):
    """
    LangGraph Assistantを検索

    LangGraphの /assistants/search エンドポイントへプロキシ
    """
    try:
        body = await request.json()

        # 認証ヘッダー準備
        headers = {}
        if LANGCHAIN_API_KEY and DEPLOYMENT_ID != "local":
            headers["X-Api-Key"] = LANGCHAIN_API_KEY

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{LANGGRAPH_API_URL}/assistants/search",
                json=body,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"LangGraphサーバーに接続できません: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assistant検索エラー: {str(e)}")


@router.post("/threads/{thread_id}/runs/stream")
async def stream_run(
    thread_id: str,
    request: Request,
    user_id: str = Depends(optional_verify_token)
):
    """
    LangGraphエージェントをストリーミング実行

    認証: オプショナル（未認証時は "anonymous"）

    SSE (Server-Sent Events) をプロキシし、リアルタイムで実行状況を転送する。
    非同期ストリーミングによりバッファリング遅延なく転送される。

    Args:
        thread_id: LangGraphスレッドID
        request: リクエストボディ（assistant_id, input, stream_mode含む）
        user_id: JWT検証で取得したユーザーID（オプショナル、デフォルト: "anonymous"）

    Returns:
        StreamingResponse: SSEストリーム
    """
    try:
        body = await request.json()

        # ──────────────────────────────────────────────────────────────
        # user_id を input に注入（Issue: Supabase Auth統合）
        # LangGraph MessagesState の拡張フィールドとして渡す
        # JWT検証済みのuser_idを使用（改ざん不可）
        # ──────────────────────────────────────────────────────────────
        if "input" not in body:
            body["input"] = {}
        body["input"]["user_id"] = user_id
        print(f"[agent] Injected user_id={user_id} into input (from JWT)")

        # 認証ヘッダー準備
        headers = {}
        if LANGCHAIN_API_KEY and DEPLOYMENT_ID != "local":
            headers["X-Api-Key"] = LANGCHAIN_API_KEY

        async def stream_generator():
            """LangGraphからのSSEレスポンスをリアルタイムで転送"""
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    async with client.stream(
                        "POST",
                        f"{LANGGRAPH_API_URL}/threads/{thread_id}/runs/stream",
                        json=body,
                        headers=headers
                    ) as response:
                        response.raise_for_status()

                        # チャンクを受信次第、即座に転送（バッファリングなし）
                        async for chunk in response.aiter_bytes():
                            yield chunk

            except httpx.HTTPStatusError as e:
                error_msg = f"data: {{\"error\": \"LangGraphエラー (status {e.response.status_code})\"}}\n\n"
                yield error_msg.encode()
            except httpx.RequestError as e:
                error_msg = f"data: {{\"error\": \"LangGraphサーバーに接続できません: {str(e)}\"}}\n\n"
                yield error_msg.encode()
            except Exception as e:
                error_msg = f"data: {{\"error\": \"ストリーミングエラー: {str(e)}\"}}\n\n"
                yield error_msg.encode()

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Nginxのバッファリング無効化
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ストリーミング開始エラー: {str(e)}")


@router.get("/ok")
async def health_check():
    """
    LangGraphサーバーのヘルスチェック（プロキシ経由）

    ローカル開発: リトライロジックを使用してLangGraphの起動を待機
    本番環境: LangSmith Cloudに接続確認
    """
    try:
        # ローカル開発の場合のみLangGraphの起動を待機
        if DEPLOYMENT_ID == "local":
            await wait_for_langgraph()
            return {"status": "ok", "langgraph": "connected", "mode": "local"}
        else:
            # LangSmith Cloud接続確認
            headers = {}
            if LANGCHAIN_API_KEY:
                headers["X-Api-Key"] = LANGCHAIN_API_KEY

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{LANGGRAPH_API_URL}/ok",
                    headers=headers
                )
                response.raise_for_status()
                return {
                    "status": "ok",
                    "langgraph": "connected",
                    "mode": "cloud",
                    "deployment_id": DEPLOYMENT_ID
                }

    except HTTPException:
        # wait_for_langgraph が投げる 503 エラーをそのまま再送
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LangGraphサーバーに接続できません: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ヘルスチェックエラー: {str(e)}")
