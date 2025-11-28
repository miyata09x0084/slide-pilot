"""
動画生成 API ルーター

Cloud Tasks から呼び出される動画生成エンドポイント。
LangGraph Cloud からオフロードされた重い処理を実行する。
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio

router = APIRouter()


class VideoGenerationRequest(BaseModel):
    """動画生成リクエスト"""
    slide_id: str
    user_id: str
    slide_md: str
    title: str


class VideoGenerationResponse(BaseModel):
    """動画生成レスポンス"""
    success: bool
    video_url: Optional[str] = None
    error: Optional[str] = None


@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    動画生成ジョブを実行

    Cloud Tasks から呼び出されることを想定。
    処理が長時間かかるため、バックグラウンドで実行し即座にレスポンスを返す。

    Args:
        request: 動画生成リクエスト
        background_tasks: FastAPI バックグラウンドタスク

    Returns:
        VideoGenerationResponse
    """
    from app.jobs.video_generator import main as video_generator_main

    payload = {
        "slide_id": request.slide_id,
        "user_id": request.user_id,
        "slide_md": request.slide_md,
        "title": request.title
    }

    # バックグラウンドで実行（Cloud Tasks のタイムアウトを回避）
    def run_video_generation():
        try:
            result = video_generator_main(payload)
            if "error" in result:
                print(f"[video_api] Generation failed: {result['error']}")
            else:
                print(f"[video_api] Generation completed: {result.get('video_url')}")
        except Exception as e:
            print(f"[video_api] Exception: {str(e)}")

    background_tasks.add_task(run_video_generation)

    # 即座にレスポンスを返す（処理はバックグラウンドで継続）
    return VideoGenerationResponse(
        success=True,
        video_url=None,  # バックグラウンド処理のため、URLはDBから取得
        error=None
    )


@router.post("/generate-sync", response_model=VideoGenerationResponse)
async def generate_video_sync(request: VideoGenerationRequest):
    """
    動画生成ジョブを同期実行（デバッグ用）

    処理完了まで待機してからレスポンスを返す。
    Cloud Run Job のタイムアウト（15分）内に完了する必要がある。

    Args:
        request: 動画生成リクエスト

    Returns:
        VideoGenerationResponse
    """
    from app.jobs.video_generator import main as video_generator_main

    payload = {
        "slide_id": request.slide_id,
        "user_id": request.user_id,
        "slide_md": request.slide_md,
        "title": request.title
    }

    try:
        # ブロッキング処理を別スレッドで実行
        result = await asyncio.to_thread(video_generator_main, payload)

        if "error" in result:
            return VideoGenerationResponse(
                success=False,
                error=result["error"]
            )

        return VideoGenerationResponse(
            success=True,
            video_url=result.get("video_url")
        )

    except Exception as e:
        return VideoGenerationResponse(
            success=False,
            error=str(e)
        )
