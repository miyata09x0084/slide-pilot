"""
動画生成ジョブ - Cloud Run Job 用エントリポイント

LangGraph Cloud からオフロードされた動画生成処理を実行する。
- ナレーション生成（OpenAI TTS）
- スライド画像生成（Playwright + SlideRenderer）
- 動画レンダリング（MoviePy + FFmpeg）
- Supabase Storage へのアップロード
"""

import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def generate_narration(
    slide_contents: List[str],
    temp_dir: Path,
    tts_model: str = "tts-1-hd",
    tts_voice: str = "shimmer",
    tts_speed: float = 1.0
) -> tuple[List[str], List[str]]:
    """
    各スライドのナレーション音声を生成（OpenAI TTS）

    Args:
        slide_contents: スライド内容のリスト
        temp_dir: 一時ディレクトリ
        tts_model: TTSモデル
        tts_voice: 音声タイプ
        tts_speed: 読み上げ速度

    Returns:
        (narration_scripts, audio_files) のタプル
    """
    from openai import OpenAI
    from app.prompts.narration_prompts import get_narration_prompt
    from app.core.llm import llm

    client = OpenAI()

    # Step 1: LLMでナレーション生成（並列）
    batch_prompts = [
        get_narration_prompt(slide_content=content)
        for content in slide_contents
    ]
    responses = llm.batch(batch_prompts, config={"max_concurrency": 5})

    narrations = []
    for i, msg in enumerate(responses):
        try:
            narration_text = msg.content.strip().strip('"').strip("'")
            narrations.append(narration_text)
        except Exception as e:
            narrations.append(f"{i+1}枚目のスライドです。")
            print(f"[narration] LLM parse error for slide {i}: {str(e)[:100]}")

    # Step 2: TTS音声生成（並列）
    def generate_audio(args):
        idx, narration_text = args
        response = client.audio.speech.create(
            model=tts_model,
            voice=tts_voice,
            input=narration_text,
            speed=tts_speed
        )
        audio_path = temp_dir / f"narration_{idx:03d}.mp3"
        with open(audio_path, 'wb') as f:
            f.write(response.content)
        return idx, str(audio_path)

    audio_results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(generate_audio, (i, narration))
            for i, narration in enumerate(narrations)
        ]
        for future in futures:
            result = future.result()
            audio_results.append(result)

    audio_results.sort(key=lambda x: x[0])
    audio_files = [path for _, path in audio_results]

    print(f"[narration] Generated {len(audio_files)} audio files")
    return narrations, audio_files


def parse_slide_to_json(slide_content: str, index: int) -> Dict[str, Any]:
    """
    スライドマークダウンを構造化JSONに変換
    """
    import re

    lines = [l for l in slide_content.strip().split("\n") if l.strip()]
    if not lines:
        return {"type": "content", "heading": f"スライド {index + 1}", "bullets": []}

    # タイトルスライド判定
    if lines[0].startswith("# ") and not any(l.strip().startswith("-") for l in lines):
        title = lines[0].lstrip("# ").strip()
        subtitle = ""
        for l in lines[1:]:
            if l.strip() and not l.startswith("#"):
                subtitle = l.strip()
                break
        return {"type": "title", "title": title, "subtitle": subtitle}

    content_str = "\n".join(lines)

    # mermaid図判定
    if "```mermaid" in content_str:
        heading = ""
        mermaid_code = ""
        mermaid_match = re.search(r"```mermaid\s*(.*?)\s*```", content_str, re.DOTALL)
        if mermaid_match:
            mermaid_code = mermaid_match.group(1).strip()
        for l in lines:
            if l.startswith("## "):
                heading = l.lstrip("## ").strip()
                break
        return {"type": "mermaid", "heading": heading or "図解", "mermaid_code": mermaid_code}

    # 通常のコンテンツスライド
    heading = ""
    bullets = []
    for l in lines:
        if l.startswith("## "):
            heading = l.lstrip("## ").strip()
        elif l.strip().startswith("-"):
            bullets.append(l.strip().lstrip("-").strip())

    return {
        "type": "content",
        "heading": heading or f"スライド {index + 1}",
        "bullets": bullets
    }


def render_video(
    slides_json: List[Dict[str, Any]],
    audio_files: List[str],
    title: str,
    user_id: str,
    slide_id: str,
    temp_dir: Path
) -> str:
    """
    PNG画像 + 音声 → MP4動画生成

    Args:
        slides_json: スライドのJSON構造
        audio_files: 音声ファイルパスのリスト
        title: スライドタイトル
        user_id: ユーザーID
        slide_id: スライドID
        temp_dir: 一時ディレクトリ

    Returns:
        video_url: アップロードされた動画URL
    """
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    from app.core.slide_renderer import SlideRenderer
    from app.core.storage import upload_to_storage
    from app.core.supabase import update_slide_video_url
    from app.core.utils import _slugify_en

    # 1. ファイル名生成
    file_stem = _slugify_en(title) or "ai-slide"

    # 2. SlideRenderer で PNG 画像生成
    png_dir = temp_dir / "slides_png"
    renderer = SlideRenderer()
    png_files = renderer.render_all(slides_json, png_dir)

    print(f"[video] Generated {len(png_files)} PNG files")

    if not png_files:
        raise RuntimeError("No PNG files generated by SlideRenderer")

    # 音声ファイル数とPNGファイル数の調整
    if len(png_files) != len(audio_files):
        print(f"[video] WARNING: PNG count ({len(png_files)}) != audio count ({len(audio_files)})")
        min_count = min(len(png_files), len(audio_files))
        png_files = png_files[:min_count]
        audio_files = audio_files[:min_count]

    # 3. MoviePyで画像+音声を合成
    clips = []
    for i, (png_path, audio_path) in enumerate(zip(png_files, audio_files)):
        try:
            img_clip = ImageClip(str(png_path))
            audio_clip = AudioFileClip(audio_path)
            video_clip = img_clip.with_duration(audio_clip.duration).with_audio(audio_clip)
            clips.append(video_clip)
        except Exception as e:
            print(f"[video] WARNING: Failed to process slide {i}: {str(e)[:100]}")
            continue

    if not clips:
        raise RuntimeError("No video clips created")

    # 4. 全スライドを結合
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

    print(f"[video] Rendered video: {video_path} ({video_path.stat().st_size / 1024 / 1024:.1f}MB)")

    # 5. Supabase Storageにアップロード
    storage_path = f"{user_id}/{file_stem}_video.mp4"
    video_url = upload_to_storage(
        bucket="slide-files",
        file_path=storage_path,
        file_data=video_path.read_bytes(),
        content_type="video/mp4"
    )

    print(f"[video] Uploaded to Supabase Storage: {video_url}")

    # 6. Supabase DBにvideo_urlを保存
    update_result = update_slide_video_url(slide_id, video_url)
    if "success" in update_result:
        print(f"[video] Updated slide_id={slide_id} with video_url")
    else:
        print(f"[video] DB update failed: {update_result.get('error', 'unknown')}")

    return video_url


def main(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    動画生成ジョブのメインエントリポイント

    Args:
        payload: {
            "slide_id": str,
            "user_id": str,
            "slide_md": str,
            "title": str
        }

    Returns:
        {"success": True, "video_url": str} or {"error": str}
    """
    slide_id = payload.get("slide_id")
    user_id = payload.get("user_id", "anonymous")
    slide_md = payload.get("slide_md", "")
    title = payload.get("title", "AIスライド")

    if not slide_id or not slide_md:
        return {"error": "Missing required fields: slide_id or slide_md"}

    print(f"[video_job] Starting video generation for slide_id={slide_id}")

    # 一時ディレクトリ作成
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # スライドを分割してJSONに変換
        slides = slide_md.split("\n---\n")
        slide_contents = []
        slides_json = []

        for idx, slide in enumerate(slides[1:]):  # frontmatterをスキップ
            content = "\n".join([
                line for line in slide.split("\n")
                if line.strip() and not line.strip().startswith("<!--")
            ])
            if content.strip():
                slide_contents.append(content)
                slides_json.append(parse_slide_to_json(content, idx))

        if not slide_contents:
            return {"error": "No slide content found"}

        print(f"[video_job] Parsed {len(slide_contents)} slides")

        # TTS設定
        tts_model = os.getenv("TTS_MODEL", "tts-1-hd")
        tts_voice = os.getenv("TTS_VOICE", "shimmer")
        tts_speed = float(os.getenv("TTS_SPEED", "1.0"))

        # ナレーション生成
        narrations, audio_files = generate_narration(
            slide_contents, temp_dir, tts_model, tts_voice, tts_speed
        )

        # 動画レンダリング
        video_url = render_video(
            slides_json, audio_files, title, user_id, slide_id, temp_dir
        )

        print(f"[video_job] Video generation completed: {video_url}")
        return {"success": True, "video_url": video_url}

    except Exception as e:
        print(f"[video_job] Error: {str(e)}")
        return {"error": str(e)}

    finally:
        # クリーンアップ
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    """
    コマンドライン実行時のエントリポイント

    Usage:
        python -m app.jobs.video_generator '{"slide_id": "xxx", "user_id": "yyy", "slide_md": "...", "title": "..."}'
    """
    if len(sys.argv) > 1:
        payload = json.loads(sys.argv[1])
    else:
        # 環境変数から取得（Cloud Run Job用）
        payload = {
            "slide_id": os.getenv("SLIDE_ID"),
            "user_id": os.getenv("USER_ID", "anonymous"),
            "slide_md": os.getenv("SLIDE_MD"),
            "title": os.getenv("TITLE", "AIスライド")
        }

    result = main(payload)
    print(json.dumps(result, ensure_ascii=False))

    if "error" in result:
        sys.exit(1)
