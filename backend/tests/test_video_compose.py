"""core/video_compose.py の純粋ヘルパーの単体テスト。

動画レンダリング3経路から抽出した共通ロジックを固定する。
（LLM/moviepy 非依存。ネットワークは mock で遮断）
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.video_compose import (
    slugify_title,
    align_audio_and_images,
    download_audio_file,
    compose_video,
)


# --- slugify_title ---

def test_slugify_title_basic():
    assert slugify_title("Hello World") == "hello-world"


def test_slugify_title_strips_symbols_and_underscores():
    # 既存挙動を固定: 記号(!)とアンダースコア(_)は「削除」される（\s に _ は含まれないため
    # 最初の除去正規表現で消える）。空白のみがハイフンへ変換される。
    assert slugify_title("My_Cool Title!") == "mycool-title"


def test_slugify_title_empty_falls_back():
    assert slugify_title("") == "ai-slide"


def test_slugify_title_non_ascii_falls_back():
    # 英数字以外（日本語等）は除去され、空になればフォールバック
    assert slugify_title("日本語タイトル") == "ai-slide"


# --- align_audio_and_images ---

def test_align_equal_lengths_unchanged():
    png = [Path("a.png"), Path("b.png")]
    audio = ["a.mp3", "b.mp3"]
    assert align_audio_and_images(png, audio) == (png, audio)


def test_align_more_png_truncates_to_audio():
    png = [Path("a.png"), Path("b.png"), Path("c.png")]
    audio = ["a.mp3", "b.mp3"]
    p, a = align_audio_and_images(png, audio)
    assert p == [Path("a.png"), Path("b.png")]
    assert a == ["a.mp3", "b.mp3"]


def test_align_more_audio_truncates_to_png():
    png = [Path("a.png")]
    audio = ["a.mp3", "b.mp3", "c.mp3"]
    p, a = align_audio_and_images(png, audio)
    assert len(p) == 1 and len(a) == 1


# --- download_audio_file ---

def test_download_audio_file_success(tmp_path):
    dest = tmp_path / "out.mp3"
    fake_resp = MagicMock()
    fake_resp.content = b"audio-bytes"
    with patch("app.core.video_compose.requests.get", return_value=fake_resp) as mock_get:
        ok = download_audio_file("http://example/a.mp3", dest, timeout=5)
    assert ok is True
    assert dest.read_bytes() == b"audio-bytes"
    mock_get.assert_called_once_with("http://example/a.mp3", timeout=5)


def test_download_audio_file_failure_returns_false(tmp_path):
    dest = tmp_path / "out.mp3"
    with patch("app.core.video_compose.requests.get", side_effect=Exception("boom")):
        ok = download_audio_file("http://example/a.mp3", dest)
    assert ok is False
    assert not dest.exists()


# --- compose_video（moviepy は mock） ---

def test_compose_video_no_inputs_returns_none(tmp_path):
    # 入力が空 -> クリップ0 -> None（呼び出し側が空時の挙動を決める契約）
    assert compose_video([], [], tmp_path / "out.mp4", log_prefix="t") is None


def test_compose_video_all_clips_fail_returns_none(tmp_path):
    with patch("moviepy.ImageClip", side_effect=Exception("bad image")):
        result = compose_video([Path("a.png")], ["a.mp3"], tmp_path / "out.mp4", log_prefix="t")
    assert result is None


def test_compose_video_success_returns_metadata(tmp_path):
    png = [Path("a.png"), Path("b.png")]
    audio = ["a.mp3", "b.mp3"]

    fake_video_clip = MagicMock()
    fake_img = MagicMock()
    fake_img.with_duration.return_value.with_audio.return_value = fake_video_clip
    fake_audio = MagicMock()
    fake_audio.duration = 3.0
    fake_final = MagicMock()
    fake_final.duration = 6.0

    out = tmp_path / "out.mp4"
    with patch("moviepy.ImageClip", return_value=fake_img), \
         patch("moviepy.AudioFileClip", return_value=fake_audio), \
         patch("moviepy.concatenate_videoclips", return_value=fake_final) as mock_concat:
        result = compose_video(png, audio, out, log_prefix="t")

    assert result == {"num_clips": 2, "duration": 6.0}
    mock_concat.assert_called_once()
    fake_final.write_videofile.assert_called_once()
