"""
LangGraphエージェントAPIプロキシルーター

LangGraphサーバー (localhost:2024) へのリクエストをプロキシし、
フロントエンドが単一エンドポイント (localhost:8001) で全機能にアクセスできるようにする。
"""

from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
import httpx
from typing import Any, Dict

router = APIRouter()

# LangGraphサーバーのベースURL
LANGGRAPH_BASE_URL = "http://localhost:2024"

# タイムアウト設定（LLM処理が長時間かかる可能性があるため長めに設定）
TIMEOUT = httpx.Timeout(300.0, connect=10.0)


@router.post("/threads")
async def create_thread(request: Request):
    """
    LangGraphスレッドを作成

    LangGraphの /threads エンドポイントへプロキシ
    """
    try:
        body = await request.json()

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{LANGGRAPH_BASE_URL}/threads",
                json=body
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

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{LANGGRAPH_BASE_URL}/assistants/search",
                json=body
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
    x_user_email: str = Header(None, alias="X-User-Email")
):
    """
    LangGraphエージェントをストリーミング実行

    SSE (Server-Sent Events) をプロキシし、リアルタイムで実行状況を転送する。
    非同期ストリーミングによりバッファリング遅延なく転送される。

    Args:
        thread_id: LangGraphスレッドID
        request: リクエストボディ（assistant_id, input, stream_mode含む）
        x_user_email: ユーザー識別子（Emailヘッダー、オプショナル）

    Returns:
        StreamingResponse: SSEストリーム
    """
    try:
        body = await request.json()

        # ──────────────────────────────────────────────────────────────
        # user_id を input に注入（Issue: スライド履歴プレビュー + user_id修正）
        # LangGraph MessagesState の拡張フィールドとして渡す
        # ──────────────────────────────────────────────────────────────
        if x_user_email:
            if "input" not in body:
                body["input"] = {}
            body["input"]["user_id"] = x_user_email
            print(f"[agent] Injected user_id={x_user_email} into input")

        async def stream_generator():
            """LangGraphからのSSEレスポンスをリアルタイムで転送"""
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    async with client.stream(
                        "POST",
                        f"{LANGGRAPH_BASE_URL}/threads/{thread_id}/runs/stream",
                        json=body
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
    """
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            response = await client.get(f"{LANGGRAPH_BASE_URL}/ok")
            response.raise_for_status()
            return {"status": "ok", "langgraph": "connected"}

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="LangGraphサーバーが起動していません。'langgraph dev' を実行してください。"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ヘルスチェックエラー: {str(e)}")
