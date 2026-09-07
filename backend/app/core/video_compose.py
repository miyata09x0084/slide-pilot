"""動画レンダリング共通処理。

動画生成は3経路に重複していた（技術的負債）:
  - routers/render.py: _render_video_blocking（同期）
  - routers/render.py: _run_video_job_local（ローカルJob）
  - jobs/video_render_job.py: main（Cloud Run Job）

本モジュールは、3経路で verbatim 重複していた純粋ロジックを集約する。
MoviePy 合成本体（compose_video）は ffmpeg/moviepy 依存で重いため、別段階で抽出予定。

NOTE: moviepy など重い依存は module トップで import しない（import 副作用ゼロを維持）。
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple

import requests


def slugify_title(title: str) -> str:
    """タイトルを動画ファイル名用の英語スラッグへ変換する。

    render.py の _slugify_en と video_render_job.py の slugify が完全一致だったため統合。
    （core/utils._slugify_en は別実装・別用途なので統合対象外）
    """
    slug = (title or "").lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug or "ai-slide"


def align_audio_and_images(
    png_files: List[Path],
    audio_files: List[str],
) -> Tuple[List[Path], List[str]]:
    """PNG と音声の数を揃える（少ない方に合わせて切り詰める）。

    3経路で完全一致していた数合わせロジックを集約。戻り値: (png_files, audio_files)。
    """
    if len(png_files) != len(audio_files):
        n = min(len(png_files), len(audio_files))
        png_files = png_files[:n]
        audio_files = audio_files[:n]
    return png_files, audio_files


def download_audio_file(url: str, dest_path: Path, timeout: int = 120) -> bool:
    """URL から音声ファイルをダウンロードして dest_path に保存する。

    成功: True / 失敗: False。
    render.py(timeout=60) と video_render_job.py(timeout=120) で重複していたものを統合。
    タイムアウトは生成系の大きめファイルに合わせ 120 秒を既定とする。
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        dest_path.write_bytes(response.content)
        return True
    except Exception as e:
        print(f"[video_compose] Failed to download audio: {e}")
        return False


def compose_video(
    png_files: List[Path],
    audio_files: List[str],
    output_path: Path,
    *,
    log_prefix: str = "video",
) -> Optional[dict]:
    """PNG画像と音声を「1スライド=1クリップ」で合成し output_path に MP4 を書き出す。

    3経路（_render_video_blocking / _run_video_job_local / video_render_job.main）で
    verbatim 重複していた MoviePy 合成本体を集約したもの。

    Returns:
        成功時: {"num_clips": int, "duration": float}
        1つも合成できなかった場合: None
        （空/失敗時の振る舞い—dict返却 vs 例外送出—は呼び出し側に委ねる）

    NOTE: moviepy は重い依存なので関数内 import（import 副作用ゼロを維持）。
          エンコード設定(fps=2/libx264/aac/2000k/ultrafast)は従来の固定値を踏襲。
    """
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

    clips = []
    for i, (png_path, audio_path) in enumerate(zip(png_files, audio_files)):
        try:
            img_clip = ImageClip(str(png_path))
            audio_clip = AudioFileClip(audio_path)
            video_clip = img_clip.with_duration(audio_clip.duration).with_audio(audio_clip)
            clips.append(video_clip)
        except Exception as e:
            print(f"[{log_prefix}] WARNING: Failed to process slide {i}: {str(e)[:100]}")
            continue

    if not clips:
        return None

    print(f"[{log_prefix}] Concatenating {len(clips)} video clips")
    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(
        str(output_path),
        fps=2,
        codec="libx264",
        audio_codec="aac",
        bitrate="2000k",
        preset="ultrafast",
    )
    return {"num_clips": len(clips), "duration": float(final_video.duration)}
