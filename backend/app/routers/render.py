"""
動画レンダリングエンドポイント

LangGraphのブロッキング処理を回避するため、重い処理をFastAPI側で実行する。
asyncio.to_thread()でブロッキング処理を別スレッドで実行し、
LangGraphはHTTP呼び出しのみを行う。
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.auth.middleware import verify_token
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
async def render_video(
    request: VideoRenderRequest,
    authenticated_user_id: str = Depends(verify_token)
):
    """
    動画生成エンドポイント（同期版 - 後方互換性のため残す）

    認証: 必須（JWT）

    asyncio.to_thread()でブロッキング処理を別スレッドで実行し、
    FastAPIのイベントループをブロックしない。
    """
    print(f"[render] Received video render request: {request.title}")

    # リクエストボディのuser_idと認証済みuser_idが一致するか検証
    if request.user_id != authenticated_user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only render videos for your own account"
        )

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


def _download_audio_file(url: str, dest_path: Path) -> bool:
    """URLから音声ファイルをダウンロード

    Args:
        url: 音声ファイルのURL（Supabase Storage公開URL）
        dest_path: 保存先パス

    Returns:
        成功: True、失敗: False
    """
    import requests

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        dest_path.write_bytes(response.content)
        return True
    except Exception as e:
        print(f"[local-job] Failed to download audio: {e}")
        return False


def _run_video_job_local(job_id: str):
    """
    ローカル環境用：video_render_job.pyと同等の処理をスレッドで実行

    Cloud Run Jobの代わりにバックグラウンドスレッドで動画生成を行う。
    音声ファイルはSupabase Storage URLからダウンロードする。
    """
    import json
    from app.core.supabase import get_video_job, update_video_job, update_slide_video_url
    from app.core.storage import upload_to_storage
    from app.core.slide_renderer import SlideRenderer
    import tempfile
    from pathlib import Path

    print(f"[local-job] Starting video render job: {job_id}")

    # 1. ジョブデータを取得
    job = get_video_job(job_id)
    if not job:
        print(f"[local-job] ERROR: Job not found: {job_id}")
        return

    if job["status"] != "pending":
        print(f"[local-job] WARNING: Job status is {job['status']}, skipping")
        return

    # 2. ステータスを processing に更新
    update_video_job(job_id, "processing")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        # 3. 入力データをパース
        input_data = json.loads(job["input_data"]) if isinstance(job["input_data"], str) else job["input_data"]
        slides_json = input_data["slides_json"]
        audio_urls = input_data["audio_files"]  # 今はSupabase Storage URL
        title = input_data["title"]
        user_id = job["user_id"]
        slide_id = job["slide_id"]

        print(f"[local-job] Processing: {len(slides_json)} slides, {len(audio_urls)} audio files")

        # 4. 音声ファイルをダウンロード（URLの場合）
        audio_dir = temp_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_files = []

        for i, audio_url in enumerate(audio_urls):
            if audio_url.startswith("http"):
                # URLからダウンロード
                local_path = audio_dir / f"narration_{i:03d}.mp3"
                print(f"[local-job] Downloading audio {i}: {audio_url[:80]}...")
                if not _download_audio_file(audio_url, local_path):
                    raise Exception(f"Failed to download audio file {i}")
                audio_files.append(str(local_path))
            else:
                # ローカルパス（後方互換性）
                audio_files.append(audio_url)

        print(f"[local-job] Downloaded {len(audio_files)} audio files")

        # 4. PNG画像生成
        png_dir = temp_dir / "slides_png"
        renderer = SlideRenderer()
        png_files = renderer.render_all(slides_json, png_dir)
        print(f"[local-job] Generated {len(png_files)} PNG files")

        if not png_files:
            raise Exception("SlideRenderer produced no images")

        # 5. 音声ファイル数とPNGファイル数を合わせる
        if len(png_files) != len(audio_files):
            print(f"[local-job] WARNING: PNG count ({len(png_files)}) != audio count ({len(audio_files)})")
            min_count = min(len(png_files), len(audio_files))
            png_files = png_files[:min_count]
            audio_files = audio_files[:min_count]

        # 6. MoviePyで動画生成
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

        clips = []
        for i, (png_path, audio_path) in enumerate(zip(png_files, audio_files)):
            try:
                img_clip = ImageClip(str(png_path))
                audio_clip = AudioFileClip(audio_path)
                video_clip = img_clip.with_duration(audio_clip.duration).with_audio(audio_clip)
                clips.append(video_clip)
                print(f"[local-job] Processed clip {i+1}/{len(png_files)}")
            except Exception as e:
                print(f"[local-job] WARNING: Failed to process slide {i}: {str(e)[:100]}")
                continue

        if not clips:
            raise Exception("All clips failed to process")

        # 7. 動画を結合・エンコード
        print(f"[local-job] Concatenating {len(clips)} video clips")
        final_video = concatenate_videoclips(clips, method="compose")

        file_stem = _slugify_en(title)
        video_path = temp_dir / f"{file_stem}_video.mp4"

        final_video.write_videofile(
            str(video_path),
            fps=2,
            codec="libx264",
            audio_codec="aac",
            bitrate="2000k",
            preset="ultrafast"
        )
        print(f"[local-job] Video written to {video_path}")

        # 8. Supabase Storageにアップロード
        storage_path = f"{user_id}/{file_stem}_video.mp4"
        video_url = upload_to_storage(
            bucket="slide-files",
            file_path=storage_path,
            file_data=video_path.read_bytes(),
            content_type="video/mp4"
        )
        print(f"[local-job] Uploaded to {video_url}")

        # 9. slidesテーブルのvideo_urlを更新
        if slide_id:
            update_slide_video_url(slide_id, video_url)
            print(f"[local-job] Updated slide {slide_id} with video_url")

        # 10. ジョブステータスを completed に更新
        update_video_job(job_id, "completed", video_url=video_url)
        print(f"[local-job] Job completed successfully: {video_url}")

    except Exception as e:
        error_msg = str(e)[:500]
        print(f"[local-job] ERROR: {error_msg}")
        update_video_job(job_id, "failed", error_message=error_msg)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/render/video/async", response_model=AsyncVideoRenderResponse)
async def render_video_async(
    request: AsyncVideoRenderRequest,
    authenticated_user_id: str = Depends(verify_token)
):
    """
    非同期動画生成エンドポイント

    認証: 必須（JWT）

    - 本番環境（Cloud Run）: Cloud Run Jobをトリガー
    - ローカル環境（LOCAL_VIDEO_JOB=true）: バックグラウンドスレッドで実行

    クライアントは /video/status/{job_id} でステータスを確認する。
    """
    from app.core.supabase import create_video_job
    from app.core.cloud_run import trigger_video_job
    import os
    import threading

    print(f"[render] Received async video render request: {request.title}")

    # リクエストボディのuser_idと認証済みuser_idが一致するか検証
    if request.user_id != authenticated_user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only render videos for your own account"
        )

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

    # 2. ジョブ実行方法の分岐
    use_local_job = os.environ.get("LOCAL_VIDEO_JOB", "").lower() == "true"

    if use_local_job:
        # ローカル環境: バックグラウンドスレッドで実行
        print(f"[render] Running job locally in background thread: {job_id}")
        thread = threading.Thread(target=_run_video_job_local, args=(job_id,), daemon=True)
        thread.start()
    else:
        # 本番環境: Cloud Run JobをAPIでトリガー
        success = trigger_video_job(job_id)

        if success:
            print(f"[render] Triggered Cloud Run Job with JOB_ID={job_id}")
        else:
            print(f"[render] WARNING: Failed to trigger Cloud Run Job for {job_id}")

    return AsyncVideoRenderResponse(
        job_id=job_id,
        status="pending"
    )


@router.get("/video/status/{job_id}", response_model=VideoJobStatusResponse)
async def get_video_status(
    job_id: str,
    authenticated_user_id: str = Depends(verify_token)
):
    """
    動画生成ジョブのステータスを取得

    認証: 必須（JWT）

    クライアントはこのエンドポイントをポーリングして完了を待つ。
    """
    from app.core.supabase import get_video_job

    job = get_video_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # job所有者検証を追加
    if job["user_id"] != authenticated_user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only view your own jobs"
        )

    return VideoJobStatusResponse(
        job_id=job_id,
        status=job["status"],
        video_url=job.get("video_url"),
        error_message=job.get("error_message")
    )
