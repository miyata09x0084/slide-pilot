"""環境変数設定と定数管理"""

from dotenv import load_dotenv
import os
from typing import Optional

# 環境変数読み込み
load_dotenv()

def _get_env(key: str, default: Optional[str] = None) -> str:
  value = os.getenv(key)
  if value is None:
    raise ValueError(f"missing environment variable: {key}")
  return value

# LangSmith
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

# OpenAI API
# API キーは環境変数 OPENAI_API_KEY から自動読み込み
# 明示的に読み込む場合のみ以下を使用
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Tavily
# NOTE: Tavily検索は text入力時のみ使用する。PDF/YouTube入力やテストでは不要なため、
#       モジュールimport時に fail-fast させず、未設定は None を許容する
#       （新しい統合設定 app/config.py:60 と同じ方針）。
#       実際にTavilyを呼び出す時点でガードし、明確なエラーを出す（utils.py: tavily_search 参照）。
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# PDF生成廃止: Slidev CLI のブロッキング処理を回避するため、MD保存のみに変更
# 動画生成はFastAPI経由で実行（render.py）

# =====================================
# 動画生成設定（Video Narration Feature）
# =====================================
# 動画生成は常に有効（VIDEO_ENABLED廃止）
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1-hd")  # tts-1 / tts-1-hd
TTS_VOICE = os.getenv("TTS_VOICE", "shimmer")   # alloy/echo/fable/onyx/nova/shimmer
TTS_SPEED = os.getenv("TTS_SPEED", "1.0")       # 0.25-4.0
