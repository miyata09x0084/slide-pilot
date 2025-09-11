# LangGraph × LangSmith × OpenAI × Tavily × Marp
# フロー:
# 0) Tavilyで情報収集 -> 1) アウトライン生成 -> 2) 目次生成 -> 3) スライド(Marp)本文生成 -> 4) 評価(>=8でOK/それ以外は2へループ) -> 5) スライドMarkdown保存(+ marp-cliでpdf/png/html出力)

from pydoc import plain
from turtle import title
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from typing import Optional, Dict, TypedDict, Any, Union
import os
import re
from pydantic.v1.typing import test_type
import requests
from typing import List
from datetime import datetime
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from langsmith import traceable
from datetime import timedelta
import json

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
    """箇条書きから不要な記号を除去"""
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
    MarkdownにMarp用のYAMLフロントマター（スライド設定のヘッダー部分）を設定する。
    既存のフロントマターは削除し、新しいテーマ・ページ番号設定等で置き換える。
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

def _remove_presenter_lines(md: str) -> str:
  """タイトルスライド（先頭～最初の'---'まで）から発表者行を除去"""
  parts = md.split("\n---\n", 1)
  head = parts[0]
  head = re.sub(r"^\s*(発表者|Presenter|Speaker)\s*[:：].*$", "", head, flags=re.MULTILINE)
  head = re.sub(r"\n{3,}", "\n\n", head).strip() + "\n"
  return head + ("\n---\n" + parts[1] if len(parts) == 2 else "")

# -------------------
# Tavily 検索
# -------------------
def tavily_search(
  query: str,
  max_results: int = 8,
  include_domains: Optional[List[str]] = None,
  time_range: str = "month", # day/week/month/year
  ) -> Dict:
  endpoint = "https://api.tavily.com/search"
  payload = {
    "api_key": TAVILY_API_KEY,
    "query": query,
    "search_depth": "advanced",
    "include_answers": True,
    "max_results": max_results,
    "time_range": time_range, # 直近の情報に限定
  }
  if include_domains:
    payload["include_domains"] = include_domains
  r = requests.post(endpoint, json=payload, timeout=60)
  r.raise_for_status()
  return r.json()

def tavily_collect_context(
  queries: List[Union[str, Dict[str, Any]]],
  max_per_query: int = 6,
  default_time_range: str = "month",
) -> Dict[str, List[Dict[str, str]]]:
  """
  queriesは以下の２形式をサポート:
    - "plain text"
    - {"q": "...", "include_domains": ["example.com", ...], "time_range": "week"}
  """
  seen = set()
  out: Dict[str, List[Dict[str, str]]] = {}
  for q in queries:
    if isinstance(q, dict):
      qtext = q.get("q", "")
      inc = q.get("include_domains")
      tr = q.get("time_range", default_time_range)
    else:
      qtext = q
      inc = None
      tr = default_time_range

    if not qtext:
      continue

    data = tavily_search(qtext, max_results=max_per_query, include_domains=inc, time_range=tr)
    items = []
    for r in data.get("results", []):
      url = r.get("url")
      if not url or url in seen:
        continue
      seen.add(url)
      items.append({
        "title": (r.get("title") or "")[:160],
        "url": url,
        "content": r.get("content" or "").replace("\n", " ")[:600],
      })
      out[qtext] = items
  return out

def context_to_bullets(ctx: List[Dict[str, str]]) -> List[str]:
  # LLMに渡しやすい、出典付きの短文箇条書きにする
  bullets = []
  for q, items in ctx.items():
    bullets.append(f"### Query: {q}")
    for it in items:
      title = it.get("title")
      url = it.get("url")
      content = it.get("content").replace("\n", " ")
      bullets.append(f"- {title} - {content} - [source]({url})")
    bullets.append("") # 空行で区切る
  return "\n".join(bullets)


# -------------------
# State
# -------------------
class State(TypedDict):
  topic: str
  outline: List[str]
  toc: List[str]
  slide_md: str
  score: float
  subscores: Dict[str, float]
  reasons: Dict[str, str]
  suggestions: List[str]
  risk_flags: List[str]
  passed: bool
  feedback: str
  title: str
  slide_path: str
  attempts: int
  error: str
  log: List[str]
  # 追加
  context_md: str # Tavilyからの要約（箇条書き）
  sources: Dict[str, List[Dict[str, str]]]

# =======================
# Node A: Tavily 情報収集 (直近2ヶ月 & 公式ドメイン)
# =======================
@traceable(run_name="a_tavily_collect")
def collect_info(state: State) -> State:
  topic = state.get("topic") or "AI最新情報"

  # JSTの現在日時 と　月英語表記を取得
  def month_en_for(dt: datetime) -> str:
    months = ["January","February","March","April","May","June",
              "July","August","September","October","November","December"]
    return f"{months[dt.month-1]} {dt.year}"

  now = now_jst()
  # 先月は、月末日の1日になる
  prev_month_dt = now.replace(day=1) - timedelta(days=1)
  # 直近2ヶ月
  month_labels = [month_en_for(now), month_en_for(prev_month_dt)]

  # ベンダー毎の公式ドメイン
  vendors_domains = [
        (["azure.microsoft.com","news.microsoft.com","learn.microsoft.com"],
         ["Microsoft AI updates", "Azure OpenAI updates"]),
        (["openai.com"], ["OpenAI announcements","OpenAI updates"]),
        (["blog.google","ai.googleblog.com","research.google"], ["Google AI updates", "Gemini updates"]),
        (["aws.amazon.com"], ["AWS Bedrock updates","Amazon AI updates"]),
        (["ai.meta.com"], ["Meta AI updates", "Llama updates"]),
        (["anthropic.com"], ["Anthropic Claude updates","Claude announcements"]),
    ]

  # ★ 直近2ヶ月 × 各社のパターンで検索クエリを構成
  queries: List[Dict[str, Any]] = []
  for m in month_labels:
    for domains, patterns in vendors_domains:
      for p in patterns:
        queries.append({"q": f"{p} {m}", "include_domains": domains, "time_range": "month"})
  try:
    sources = tavily_collect_context(queries, max_per_query=6, default_time_range="month")
    context_md = context_to_bullets(sources)
    return {
      "sources": sources,
      "context_md": context_md,
      "log": _log(state, f"[tavily] months={month_labels} queries={len(queries)}")
    }
  except Exception as e:
    return {"error": f"tavily_error: {e}", "log": _log(state, f"[tavily] EXCEPTION {e}")}

# -------------------
# Node B: アウトライン生成
# -------------------
@traceable(run_name="b_generate_outline")
def generate_outline(state: State) -> Dict:
  topic = state.get("topic") or "AI最新情報"
  ctx = state.get("context_md") or ""
  prompt = [
    ("system", "あなたはSolution Engineerです。これからMarpスライドでAI最新情報を発表します。"),
      ("user",
        "以下の“最新情報サマリ（出典付き）”を参考に、発表の重要ポイントを各社5個、"
        "短い箇条書きで。URLも含めてください。\n\n"
        f"[最新情報サマリ]\n{ctx}\n\n[トピック]\n{topic}")
  ]
  try:
    msg = llm.invoke(prompt)
    bullets = _strip_bullets(msg.content.splitlines())[:5] or [msg.content.strip()] # 箇条書きが取れなかったら、せめて元の文章をそのまま使う。
    return {"outline": bullets, "log": _log(state, f"[outline] {bullets}")}
  except Exception as e:
    return {"error": f"outline_error: {e}", "log": _log(state, f"[outline] EXCEPTION {e}")}

# -------------------
# Node C: 目次生成
# -------------------
@traceable(run_name="c_generate_toc")
def generate_toc(state: State) -> Dict:
  outline = state.get("outline") or []
  prompt = [
        ("system", "あなたはSolution Engineerです。Marpスライドの構成（目次）を作ります。"),
        ("user",
         "以下のアウトラインから、5〜8個の章立て（配列）を JSON の {\"toc\": [ ... ]} 形式で返してください。\n\n"
         "アウトライン:\n- " + "\n- ".join(outline))
  ]
  try:
    msg = llm.invoke(prompt)
    try:
      data = json.loads(_find_json(msg.content) or msg.content)
      toc = [s.strip() for s in data.get("toc", []) if s.strip()]
    except Exception as e:
      toc = _strip_bullets(msg.content.splitlines())
      toc = toc[:8] or ["はじめに", "背景", "実装手順", "評価と改善", "公開・運用", "まとめ"]
      return {"toc": toc, "error": "", "log": _log(state, f"[toc] {toc}")}
  except Exception as e:
     return {"error": f"toc_error: {e}", "log": _log(state, f"[toc] EXCEPTION {e}")}

