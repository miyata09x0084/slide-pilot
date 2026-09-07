#!/usr/bin/env python3
"""
Cloud Run Job: 動画レンダリング

環境変数から入力を受け取り、動画を生成してSupabaseにアップロードする。
Cloud Run Jobとして実行され、最大24時間のタイムアウトが可能。

Usage:
    JOB_ID=xxx python video_render_job.py
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# backend/app をモジュールパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.supabase import get_video_job, update_video_job, update_slide_video_url
from app.core.storage import upload_to_storage
from app.core.slide_renderer import SlideRenderer
from app.core.video_compose import slugify_title, align_audio_and_images, download_audio_file, compose_video


def main():
    """メイン処理"""
    job_id = os.environ.get("JOB_ID")
    if not job_id:
        print("[job] ERROR: JOB_ID environment variable not set")
        sys.exit(1)

    print(f"[job] Starting video render job: {job_id}")

    # 1. ジョブデータを取得
    job = get_video_job(job_id)
    if not job:
        print(f"[job] ERROR: Job not found: {job_id}")
        sys.exit(1)

    if job["status"] != "pending":
        print(f"[job] WARNING: Job status is {job['status']}, skipping")
        sys.exit(0)

    # 2. ステータスを processing に更新
    update_video_job(job_id, "processing")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        # 3. 入力データをパース
        input_data = json.loads(job["input_data"])
        slides_json = input_data["slides_json"]
        audio_urls = input_data["audio_files"]  # Supabase Storage URL
        title = input_data["title"]
        user_id = job["user_id"]
        slide_id = job["slide_id"]

        print(f"[job] Processing: {len(slides_json)} slides, {len(audio_urls)} audio files")

        # 4. 音声ファイルをダウンロード（URLの場合）
        audio_dir = temp_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_files = []

        for i, audio_url in enumerate(audio_urls):
            if audio_url.startswith("http"):
                # URLからダウンロード
                local_path = audio_dir / f"narration_{i:03d}.mp3"
                print(f"[job] Downloading audio {i}: {audio_url[:80]}...")
                if not download_audio_file(audio_url, local_path):
                    raise Exception(f"Failed to download audio file {i}")
                audio_files.append(str(local_path))
            else:
                # ローカルパス（後方互換性）
                audio_files.append(audio_url)

        print(f"[job] Downloaded {len(audio_files)} audio files")

        # 5. PNG画像生成
        png_dir = temp_dir / "slides_png"
        renderer = SlideRenderer()
        png_files = renderer.render_all(slides_json, png_dir)
        print(f"[job] Generated {len(png_files)} PNG files")

        if not png_files:
            raise Exception("SlideRenderer produced no images")

        # 6. 音声ファイル数とPNGファイル数を合わせる
        png_files, audio_files = align_audio_and_images(png_files, audio_files)

        # 7-8. MoviePyで合成して書き出し
        file_stem = slugify_title(title)
        video_path = temp_dir / f"{file_stem}_video.mp4"
        if compose_video(png_files, audio_files, video_path, log_prefix="job") is None:
            raise Exception("All clips failed to process")
        print(f"[job] Video written to {video_path}")

        # 9. Supabase Storageにアップロード
        storage_path = f"{user_id}/{file_stem}_video.mp4"
        video_url = upload_to_storage(
            bucket="slide-files",
            file_path=storage_path,
            file_data=video_path.read_bytes(),
            content_type="video/mp4"
        )
        print(f"[job] Uploaded to {video_url}")

        # 10. slidesテーブルのvideo_urlを更新
        if slide_id:
            update_slide_video_url(slide_id, video_url)
            print(f"[job] Updated slide {slide_id} with video_url")

        # 11. ジョブステータスを completed に更新
        update_video_job(job_id, "completed", video_url=video_url)
        print(f"[job] Job completed successfully: {video_url}")

    except Exception as e:
        error_msg = str(e)[:500]
        print(f"[job] ERROR: {error_msg}")
        update_video_job(job_id, "failed", error_message=error_msg)
        sys.exit(1)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
