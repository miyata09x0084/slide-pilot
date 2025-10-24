"""
統合設定ファイル
環境変数とアプリケーション設定を一元管理
"""

from dotenv import load_dotenv
import os
from pathlib import Path
from typing import Optional

# 環境変数読み込み
load_dotenv()

# ベースディレクトリ（デフォルト）
BASE_DIR = Path(__file__).parent.parent


class Settings:
    """アプリケーション設定クラス"""

    # API設定
    API_TITLE: str = "SlidePilot API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "AI-powered presentation slide generation API"

    # サーバー設定
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # CORS設定
    CORS_ORIGINS: list = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
    ]

    # データディレクトリ（環境変数で制御可能）
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))

    # ファイルパス設定（DATA_DIRベース）
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    SLIDES_DIR: Path = DATA_DIR / "slides"
    TOKENS_DIR: Path = DATA_DIR / "tokens"

    # ファイルサイズ制限（100MB）
    MAX_FILE_SIZE: int = 100 * 1024 * 1024

    # LangSmith
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "true")
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "marp-agent")

    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")

    # スライド設定
    SLIDE_FORMAT: str = os.getenv("SLIDE_FORMAT", "").lower().strip()
    MARP_THEME: str = os.getenv("MARP_THEME", "default")
    MARP_PAGINATE: str = os.getenv("MARP_PAGINATE", "true")

    def __init__(self):
        """ディレクトリを自動作成"""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.SLIDES_DIR.mkdir(parents=True, exist_ok=True)
        self.TOKENS_DIR.mkdir(parents=True, exist_ok=True)

        # LangSmith環境変数設定
        os.environ.setdefault("LANGCHAIN_TRACING_V2", self.LANGCHAIN_TRACING_V2)
        os.environ.setdefault("LANGCHAIN_ENDPOINT", self.LANGCHAIN_ENDPOINT)


# シングルトンインスタンス
settings = Settings()
