"""
FastAPI依存性注入
共通の依存関係を定義

Issue #29: Supabase Storage移行対応
- UPLOAD_DIR, SLIDES_DIRは削除（Supabase Storage使用）
"""

from app.config import settings


def get_max_file_size() -> int:
    """最大ファイルサイズを取得"""
    return settings.MAX_FILE_SIZE
