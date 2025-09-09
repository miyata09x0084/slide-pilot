# LangGraph × LangSmith × OpenAI × Tavily × Marp
# フロー:
# 0) Tavilyで情報収集 -> 1) アウトライン生成 -> 2) 目次生成 -> 3) スライド(Marp)本文生成 -> 4) 評価(>=8でOK/それ以外は2へループ) -> 5) スライドMarkdown保存(+ marp-cliでpdf/png/html出力)

from pydoc import plain
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from typing import Optional
import os
import re
from typing import List
from datetime import datetime
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool

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
MARP_PAGINATE = os.getenv("MARP_PAGINATE", "true") # true/false

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

def _ensure_marp_header(md: str, title: str) -> str:
    """
    MarkdownにMarp用のYAMLフロントマターを設定する
    既存のフロントマターは削除して新しいものに置き換える
    """
    # Marp用YAMLフロントマターを構築
    header = (
      "---\n"
          "marp: true\n"                    # Marp処理を有効化
          f"paginate: {MARP_PAGINATE}\n"     # ページ番号表示設定
          f"theme: {MARP_THEME}\n"           # テーマ設定
          f"title: {title}\n"                # スライドタイトル
          "---\n\n"
    )

    # 既存のフロントマター（---...---）を削除して本文のみ抽出
    body = re.sub(r"^---[\s\S]*?---\s*", "", md.strip(), count=1, flags=re.DOTALL)

    # 新ヘッダー + 本文を結合（末尾改行を保証）
    return header + (body + ("\n" if not body.endswith("\n") else ""))

def _insert_separators(md: str) -> str:
    """
    コードブロックを壊さず、H2(## )の直前に1つだけ '---' を入れる。
    """
    out = [] # 出力を格納するリスト
    in_code = False # コードブロック内かどうか
    fence = None # コードブロックの開始マーカー (``` or ~~~)
    prev = "" # 直前の行

    def need_sep(prev_line: str) -> bool:
      pl = prev_line.strip()
      # 直前がすでに --- なら不要
      return pl != "---"

    for line in md.splitlines():
      # コードブロックの検出
      if line.startswith("```") or line.startswith("~~~"):
        if not in_code:
          in_code, fence = True, line[:3]
        else:
          if fence and line.startswith(fence):
            in_code, fence = False, None
          out.append(line)
          prev = line
          continue

      # H2(## )の直前に1つだけ '---' を入れる
      if not in_code and line.startswith("## "):
        if need_sep(prev): # 前の行が"---"でなければ
          out.append("---") # セパレータ挿入
        out.append(line)
      else:
        out.append(line)
      prev = line

    return "\n".join(out).strip() + "\n"

def _double_separators(md: str) -> str:
    """
    連続する区切り（---, 空行, --- ...) を1個に圧縮。
    """
    # --- の連続や、--- の間の空行を潰す
    md = re.sub(r"(?:\n*\s*---\s*\n+){2,}", "\n---\n", md)
    # 先頭の余分な --- を1個に
    md = re.sub(r"^(?:\s*---\s*\n)+", "---\n", md)
    return md

def _strip_whole_code_fence(md: str) -> str:
    t = md.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\s*\n?", "", t, flags=re.DOTALL)
        t = re.sub(r"\n?```$", "", t.strip(), flags=re.DOTALL)
    return t

def _clean_title(raw: str) -> str:
    """
    LLMが『以下のようなタイトル…』など前置きや引用記号を混ぜても
    1行のタイトルだけにする。
    """
    t = (raw or "").strip()
    # 1行目だけ採用
    t = t.splitlines()[0]
    # 日本語引用や英語引用を除去
    t = re.sub(r"^[「『]*", "", t)
    # 典型的な前置きを除去
    t = re.sub(r"^(以下のようなタイトル.*|title:?|suggested:?|案:?)[\s：:]*", "", t, flags=re.IGNORECASE)
    return t or "AI最新情報"

# JSTの現在日時を取得
JST = ZoneInfo("Asia/Tokyo")

def now_jst() -> str:
  return datetime.now(JST)

def today_iso(fmt: str = "%Y-%m-%d") -> str:
  return now_jst().strftime(fmt)

def month_ja() -> str:
  dt = now_jst()
  # Windowsでも動くように %-m を使わず、0埋めもしない
  return f"{dt.year}年{dt.month}月"

def month_en() -> str:
  months = ["January","February","March","April","May","June",
              "July","August","September","October","November","December"]
  dt = now_jst()
  return f"{months[dt.month-1]} {dt.year}"

@tool("get_today_jst", return_direct=True)
def get_today_jst(fmt: str = "%Y-%m-%d") -> str:
  """JSTで今日の日付を返す（例: %Y-%m-%d, %Y年%m月 など）"""
  return datetime.now(JST).strftime(fmt)

def _clean_title(raw: str) -> str:
  t = (raw or "").strip().splitlines()[0]
  t = t.strip("「」『』\"' 　:：")
  t = re.sub(r"^(以下のようなタイトル.*|title:?|suggested:?|案:?)[\s：:]*", "", t, flags=re.IGNORECASE)
  return t or "[本日の日付] AI最新情報まとめ"

def _strip_whole_code_fence(md: str) -> str:
  t = md.strip()
  if t.startswith("```"):
    t = re.sub(r"^```[a-zA-Z0-9_-]*\s*\n?", "", t)
    t = re.sub(r"\n?```$", "", t.strip())