# LangGraph × LangSmith × OpenAI × Tavily × Marp
# フロー:
# 0) Tavilyで情報収集 -> 1) アウトライン生成 -> 2) 目次生成 -> 3) スライド(Marp)本文生成 -> 4) 評価(>=8でOK/それ以外は2へループ) -> 5) スライドMarkdown保存(+ marp-cliでpdf/png/html出力)

from dotenv import load_dotenv
from typing import Optional
import os
import re
from typing import List
from langchain_openai import AzureChatOpenAI

# -------------------
# 環境変数読み込み
# -------------------

load_dotenv()

def _get_env(key: str, default: Optional[str] = None) -> str:
  value = os.getenv(key)
  if value is None:
    raise ValueError(f"missing environment variable: {key}")
  return value

# LangSmith
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

# Azure OpenAI
AZURE_OPENAI_ENDPOINT    = _get_env("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY     = _get_env("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = _get_env("AZURE_OPENAI_API_VERSION", "2024-06-01")
AZURE_OPENAI_DEPLOYMENT  = _get_env("AZURE_OPENAI_DEPLOYMENT")

# Tavily
TAVILY_API_KEY = _get_env("TAVILY_API_KEY")

# Marp 出力（PDF/PNG/HTML）。空なら .md に出力
SLIDE_FORMAT = os.getenv("SLIDE_FORMAT", "").lower().strip()
MARP_THEME = os.getenv("MARP_THEME", "default") # default/gaia/gaia-dark/gaia-light
MARP_PAGING = os.getenv("MARP_PAGING", "true") # true/false

# -------------------
# LLM クライアント
# -------------------
llm = AzureChatOpenAI(
  azure_endpoint=AZURE_OPENAI_ENDPOINT,
  api_key=AZURE_OPENAI_API_KEY,
  api_version=AZURE_OPENAI_API_VERSION,
  azure_deployment=AZURE_OPENAI_DEPLOYMENT,
  temperature=0.2,
)

# -------------------
# ユーティリティ
# -------------------
def _log(state: dict, msg: str) -> List[str]:
  return (state.get("logs") or []) + [msg]

def _strip_bullets(lines: List[str]) -> List[str]:
  output = []
  for line in lines:
    t = line.strip()
    if not t:
      continue
    t = t.lstrip("・-•* \t")
    output.append(t)
  return output

def _slugify_en(text: str, max_length: int = 80) -> str:
  text = (text or "").lower()
  text = re.sub(r"[^a-z0-9]+", "-", text)
  text = re.sub(r"-+", "-", text).strip("-")
  return text[:max_length] or "slide"

def _find_json(text: str) -> Optional[str]:
  t = text.strip()
  t = re.sub(r"^```(?:json)?\s*", "", t)
  t = re.sub(r"\s*```$", "", t)
  m = re.search(r"\{.*\}\s*$", t, flags=re.DOTALL)
  if m:
    return m.group(0)
  return None


