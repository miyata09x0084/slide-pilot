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
        audio_files = input_data["audio_files"]
        title = input_data["title"]
        user_id = job["user_id"]
        slide_id = job["slide_id"]

        print(f"[job] Processing: {len(slides_json)} slides, {len(audio_files)} audio files")

        # 4. PNG画像生成
        png_dir = temp_dir / "slides_png"
        renderer = SlideRenderer()
        png_files = renderer.render_all(slides_json, png_dir)
        print(f"[job] Generated {len(png_files)} PNG files")

        if not png_files:
            raise Exception("SlideRenderer produced no images")

        # 5. 音声ファイル数とPNGファイル数を合わせる
        if len(png_files) != len(audio_files):
            print(f"[job] WARNING: PNG count ({len(png_files)}) != audio count ({len(audio_files)})")
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
                print(f"[job] Processed clip {i+1}/{len(png_files)}")
            except Exception as e:
                print(f"[job] WARNING: Failed to process slide {i}: {str(e)[:100]}")
                continue

        if not clips:
            raise Exception("All clips failed to process")

        # 7. 動画を結合・エンコード
        print(f"[job] Concatenating {len(clips)} video clips")
        final_video = concatenate_videoclips(clips, method="compose")

        # ファイル名を生成
        import re
        def slugify(text: str) -> str:
            slug = text.lower()
            slug = re.sub(r'[^a-z0-9\s-]', '', slug)
            slug = re.sub(r'[\s_]+', '-', slug)
            slug = re.sub(r'-+', '-', slug).strip('-')
            return slug or "ai-slide"

        file_stem = slugify(title)
        video_path = temp_dir / f"{file_stem}_video.mp4"

        final_video.write_videofile(
            str(video_path),
            fps=2,
            codec="libx264",
            audio_codec="aac",
            bitrate="2000k",
            preset="ultrafast"
        )
        print(f"[job] Video written to {video_path}")

        # 8. Supabase Storageにアップロード
        storage_path = f"{user_id}/{file_stem}_video.mp4"
        video_url = upload_to_storage(
            bucket="slide-files",
            file_path=storage_path,
            file_data=video_path.read_bytes(),
            content_type="video/mp4"
        )
        print(f"[job] Uploaded to {video_url}")

        # 9. slidesテーブルのvideo_urlを更新
        if slide_id:
            update_slide_video_url(slide_id, video_url)
            print(f"[job] Updated slide {slide_id} with video_url")

        # 10. ジョブステータスを completed に更新
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
