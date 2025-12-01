"""
動画レンダリングエンドポイント

LangGraphのブロッキング処理を回避するため、重い処理をFastAPI側で実行する。
asyncio.to_thread()でブロッキング処理を別スレッドで実行し、
LangGraphはHTTP呼び出しのみを行う。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import tempfile
import shutil
from pathlib import Path
import re

router = APIRouter(tags=["render"])


class VideoRenderRequest(BaseModel):
    """動画レンダリングリクエスト"""
    slides_json: List[Dict[str, Any]]
    audio_files: List[str]
    title: str
    user_id: str
    slide_id: Optional[str] = ""


class VideoRenderResponse(BaseModel):
    """動画レンダリングレスポンス"""
    video_url: str
    log: List[str]


def _slugify_en(title: str) -> str:
    """タイトルを英語スラッグに変換"""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug or "ai-slide"


def _render_video_blocking(
    slides_json: List[Dict],
    audio_files: List[str],
    title: str,
    user_id: str,
    slide_id: str
) -> Dict:
    """
    ブロッキング動画生成処理

    この関数はasyncio.to_thread()経由で呼び出され、
    FastAPIのイベントループをブロックしない。
    """
    print(f"[render] Starting video rendering: {len(slides_json)} slides, {len(audio_files)} audio files")

    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    from app.core.slide_renderer import SlideRenderer
    from app.core.storage import upload_to_storage
    from app.core.supabase import update_slide_video_url
    from app.prompts.slide_prompts import get_slug_prompt
    from app.core.llm import llm

    temp_dir = Path(tempfile.mkdtemp())
    log_entries = []

    try:
        # 1. ファイル名の英語表記を生成
        slug_prompt = get_slug_prompt(title=title)
        try:
            emsg = llm.invoke(slug_prompt)
            file_stem = _slugify_en(emsg.content.strip()) or _slugify_en(title)
        except Exception:
            file_stem = _slugify_en(title) or "ai-slide"

        # 2. SlideRenderer で PNG 画像生成（HTML/CSS + Playwright）
        png_dir = temp_dir / "slides_png"
        print(f"[render] Rendering slides with SlideRenderer to {png_dir}")

        renderer = SlideRenderer()
        png_files = renderer.render_all(slides_json, png_dir)
        log_entries.append(f"[video] rendered {len(png_files)} PNG images")
        print(f"[render] Generated {len(png_files)} PNG files")

        if not png_files:
            return {
                "video_url": "",
                "log": log_entries + ["[video] ERROR: SlideRenderer produced no images"]
            }

        # 3. 音声ファイル数とPNGファイル数を合わせる
        audio_files_local = list(audio_files)
        if len(png_files) != len(audio_files_local):
            print(f"[render] WARNING: PNG count ({len(png_files)}) != audio count ({len(audio_files_local)})")
            min_count = min(len(png_files), len(audio_files_local))
            png_files = png_files[:min_count]
            audio_files_local = audio_files_local[:min_count]

        # 4. MoviePyで画像+音声を合成
        clips = []
        for i, (png_path, audio_path) in enumerate(zip(png_files, audio_files_local)):
            try:
                img_clip = ImageClip(str(png_path))
                audio_clip = AudioFileClip(audio_path)
                video_clip = img_clip.with_duration(audio_clip.duration).with_audio(audio_clip)
                clips.append(video_clip)
            except Exception as e:
                print(f"[render] WARNING: Failed to process slide {i}: {str(e)[:100]}")
                continue

        if not clips:
            return {
                "video_url": "",
                "log": log_entries + ["[video] ERROR: all clips failed"]
            }

        # 5. 全スライドを結合
        print(f"[render] Concatenating {len(clips)} video clips")
        final_video = concatenate_videoclips(clips, method="compose")
        video_path = temp_dir / f"{file_stem}_video.mp4"

        final_video.write_videofile(
            str(video_path),
            fps=2,
            codec="libx264",
            audio_codec="aac",
            bitrate="2000k",
            preset="ultrafast"
        )
        print(f"[render] Video written to {video_path}")

        # 6. Supabase Storageにアップロード
        video_url = None
        try:
            storage_path = f"{user_id}/{file_stem}_video.mp4"
            video_url = upload_to_storage(
                bucket="slide-files",
                file_path=storage_path,
                file_data=video_path.read_bytes(),
                content_type="video/mp4"
            )
            video_size_mb = video_path.stat().st_size / 1024 / 1024
            log_msg = f"[video] rendered {len(clips)} slides -> MP4 ({video_size_mb:.1f}MB, {final_video.duration:.1f}sec)"
            log_msg += f" | uploaded to {video_url}"
            log_entries.append(log_msg)
            print(f"[render] Uploaded to {video_url}")
        except Exception as e:
            log_msg = f"[video] rendered locally but upload failed: {str(e)[:100]}"
            log_entries.append(log_msg)
            video_url = str(video_path)
            print(f"[render] Upload failed: {e}")

        # 7. Supabase DBにvideo_urlを保存
        if video_url and slide_id:
            try:
                update_result = update_slide_video_url(slide_id, video_url)
                if "success" in update_result:
                    log_entries.append(f"[video] DB updated (slide_id={slide_id})")
                elif "error" in update_result:
                    log_entries.append(f"[video] DB update failed: {update_result['error'][:50]}")
            except Exception as e:
                log_entries.append(f"[video] DB update exception: {str(e)[:50]}")

        return {"video_url": video_url or "", "log": log_entries}

    except Exception as e:
        print(f"[render] ERROR: {e}")
        return {
            "video_url": "",
            "log": log_entries + [f"[video] EXCEPTION {str(e)[:100]}"]
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/render/video", response_model=VideoRenderResponse)
async def render_video(request: VideoRenderRequest):
    """
    動画生成エンドポイント（同期版 - 後方互換性のため残す）

    asyncio.to_thread()でブロッキング処理を別スレッドで実行し、
    FastAPIのイベントループをブロックしない。
    """
    print(f"[render] Received video render request: {request.title}")

    try:
        result = await asyncio.to_thread(
            _render_video_blocking,
            request.slides_json,
            request.audio_files,
            request.title,
            request.user_id,
            request.slide_id or ""
        )

        if not result.get("video_url"):
            raise HTTPException(
                status_code=500,
                detail="Video rendering failed: " + "; ".join(result.get("log", []))
            )

        return VideoRenderResponse(
            video_url=result["video_url"],
            log=result["log"]
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[render] Unhandled error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 非同期動画生成（Cloud Run Job版）
# ============================================================

class AsyncVideoRenderRequest(BaseModel):
    """非同期動画レンダリングリクエスト"""
    slides_json: List[Dict[str, Any]]
    audio_files: List[str]
    title: str
    user_id: str
    slide_id: str  # 必須


class AsyncVideoRenderResponse(BaseModel):
    """非同期動画レンダリングレスポンス"""
    job_id: str
    status: str


class VideoJobStatusResponse(BaseModel):
    """動画ジョブステータスレスポンス"""
    job_id: str
    status: str
    video_url: Optional[str] = None
    error_message: Optional[str] = None


@router.post("/render/video/async", response_model=AsyncVideoRenderResponse)
async def render_video_async(request: AsyncVideoRenderRequest):
    """
    非同期動画生成エンドポイント

    Cloud Run Jobをトリガーし、job_idを即座に返す。
    クライアントは /video/status/{job_id} でステータスを確認する。
    """
    from app.core.supabase import create_video_job
    import subprocess
    import os

    print(f"[render] Received async video render request: {request.title}")

    # 1. video_jobsテーブルにジョブを作成
    result = create_video_job(
        slide_id=request.slide_id,
        user_id=request.user_id,
        slides_json=request.slides_json,
        audio_files=request.audio_files,
        title=request.title
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    job_id = result["job_id"]
    print(f"[render] Created video job: {job_id}")

    # 2. Cloud Run Jobをトリガー（非同期）
    try:
        project_id = os.environ.get("GCP_PROJECT_ID", "slide-pilot-474305")
        region = os.environ.get("GCP_REGION", "asia-northeast1")
        job_name = "slidepilot-video-job"

        # gcloud run jobs execute コマンドを非同期で実行
        cmd = [
            "gcloud", "run", "jobs", "execute", job_name,
            f"--region={region}",
            f"--update-env-vars=JOB_ID={job_id}",
            "--async"
        ]

        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"[render] Triggered Cloud Run Job: {job_name} with JOB_ID={job_id}")

    except Exception as e:
        print(f"[render] WARNING: Failed to trigger Cloud Run Job: {e}")
        # ジョブトリガー失敗してもエラーにはしない（ジョブはpending状態のまま）

    return AsyncVideoRenderResponse(
        job_id=job_id,
        status="pending"
    )


@router.get("/video/status/{job_id}", response_model=VideoJobStatusResponse)
async def get_video_status(job_id: str):
    """
    動画生成ジョブのステータスを取得

    クライアントはこのエンドポイントをポーリングして完了を待つ。
    """
    from app.core.supabase import get_video_job

    job = get_video_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return VideoJobStatusResponse(
        job_id=job_id,
        status=job["status"],
        video_url=job.get("video_url"),
        error_message=job.get("error_message")
    )
