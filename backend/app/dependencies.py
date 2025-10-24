"""
FastAPI依存性注入
共通の依存関係を定義
"""

from pathlib import Path
from config import settings


def get_upload_dir() -> Path:
    """アップロードディレクトリを取得"""
    return settings.UPLOAD_DIR


def get_slides_dir() -> Path:
    """スライドディレクトリを取得"""
    return settings.SLIDES_DIR


def get_max_file_size() -> int:
    """最大ファイルサイズを取得"""
    return settings.MAX_FILE_SIZE
