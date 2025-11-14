"""
FastAPI依存性注入
共通の依存関係を定義

Issue #29: Supabase Storage移行対応
- UPLOAD_DIR, SLIDES_DIRは削除（Supabase Storage使用）
"""

from pathlib import Path
from app.config import settings


def get_max_file_size() -> int:
    """最大ファイルサイズを取得"""
    return settings.MAX_FILE_SIZE


def get_feedback_dir() -> Path:
    """フィードバック保存ディレクトリを取得（ローカルJSON保存用）"""
    feedback_dir = Path(__file__).parent.parent / "data" / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    return feedback_dir
