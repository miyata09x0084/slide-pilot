# LangGraph × LangSmith × OpenAI × Tavily × Marp
# フロー:
# 0) Tavilyで情報収集 -> 1) アウトライン生成 -> 2) 目次生成 -> 3) スライド(Marp)本文生成 -> 4) 評価(>=8でOK/それ以外は2へループ) -> 5) スライドMarkdown保存(+ marp-cliでpdf/png/html出力)

from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from typing import Optional, Dict, TypedDict, Any, Union
import os
import re
import requests
from typing import List
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from langgraph.graph import StateGraph, START, END
from datetime import timedelta
import json
from pathlib import Path
import shutil
import subprocess

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

# OpenAI API
# API キーは環境変数 OPENAI_API_KEY から自動読み込み
# 明示的に読み込む場合のみ以下を使用
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Tavily
TAVILY_API_KEY = _get_env("TAVILY_API_KEY")

# Marp 出力（PDF/PNG/HTML）。空なら .md に出力
SLIDE_FORMAT = os.getenv("SLIDE_FORMAT", "").lower().strip()
MARP_THEME = os.getenv("MARP_THEME", "default") # default/gaia/gaia-dark/gaia-light
MARP_PAGINATE = os.getenv("MARP_PAGINATE", "true") # true/false

# -------------------
# LLM クライアント
# -------------------
llm = ChatOpenAI(
  model="gpt-4o",  # 最新のGPT-4 Omniモデル（または "gpt-3.5-turbo" でコスト削減）
  temperature=0.2,
  max_retries=2,    # リトライ回数
  # api_key は環境変数 OPENAI_API_KEY から自動読み込み
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
    if not md or md is None:
        return ""

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
    if not md or md is None:
        return ""

    # --- の連続や、--- の間の空行を潰す
    md = re.sub(r"(?:\n*\s*---\s*\n+){2,}", "\n---\n", md)
    # 先頭の余分な --- を1個に
    md = re.sub(r"^(?:\s*---\s*\n)+", "---\n", md)
    return md


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
  return t

def _remove_presenter_lines(md: str) -> str:
  """タイトルスライド（先頭～最初の'---'まで）から発表者行を除去"""
  if not md or md is None:
    return ""

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
  key_points: List[str]  # AI最新情報の重要ポイント（旧: outline）
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
# Node B: 重要ポイント生成
# -------------------
@traceable(run_name="b_generate_key_points")
def generate_key_points(state: State) -> Dict:
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
    return {"key_points": bullets, "log": _log(state, f"[key_points] {bullets}")}
  except Exception as e:
    return {"error": f"key_points_error: {e}", "log": _log(state, f"[key_points] EXCEPTION {e}")}

# -------------------
# Node C: 目次生成
# -------------------
@traceable(run_name="c_generate_toc")
def generate_toc(state: State) -> Dict:
  key_points = state.get("key_points") or []
  prompt = [
        ("system", "あなたはSolution Engineerです。Marpスライドの構成（目次）を作ります。"),
        ("user",
         "以下の重要ポイントから、5〜8個の章立て（配列）を JSON の {\"toc\": [ ... ]} 形式で返してください。\n\n"
         "重要ポイント:\n- " + "\n- ".join(key_points))
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

# -------------------
# Node D: スライド本文（Marp）生成
# -------------------
@traceable(run_name="d_generate_slide_md")
def write_slides(state: State) -> Dict:
  ctx = state.get("context_md") or "" # Tavilyからの要約（箇条書き）
  sources = state.get("sources") or {}

  # 参考リンク
  refs = []
  for items in sources.values():
    for it in items[:2]:
      refs.append(f"- **{it['title']}** — {it['url']}")
  refs_md = "\n".join(refs)

  # タイトルはLLMに任せず、当月で固定
  ja_title = f"{month_ja()} AI最新情報まとめ"

  prompt = [
    ("system",
      "あなたはSolution Engineerで、Marp形式のスライドを作ります。"
      "出力はコードブロックで囲まず、スライド区切り（---）は入れないでください。"
      "各スライドは必ず H2 見出し（## ）で開始。タイトルスライドに発表者名は書かないでください。"
      "重要: 以下の"最新情報サマリ"の範囲内の事実のみに基づいて作成し、サマリに無い情報は書かないでください。"),
    ("user",
      "最新情報サマリ（出典付き）:\n"
      f"{ctx}\n\n"
      "要件:\n"
      f"- タイトル（表紙の大見出し）: {ja_title}\n"
      "- 1ページ目は # 見出しと短いサブタイトルのみ（発表者名は書かない）\n"
      "- 2ページ目は Agenda（章立てを列挙）\n"
      "- 以降は各社ごとのAI最新情報を簡潔に。各項目にURLを含める\n"
      "- 各章は必ず H2（## ）で始める")
  ]

  try:
    msg = llm.invoke(prompt)

    # Null値チェックと処理
    if msg.content is None:
        print(f"[WARNING] write_slides: msg.content is None, using fallback")
        # フォールバックスライドを生成
        slide_md = f"""# {ja_title}

## Agenda
- Microsoft AI 最新情報
- Azure OpenAI 最新情報
- OpenAI 最新情報
- Google AI 最新情報
- まとめ

---

## Microsoft AI 最新情報

最新情報を取得中にエラーが発生しました。

---

## まとめ

AI技術の最新動向をお伝えしました。
"""
    else:
        slide_md = msg.content.strip()

    # 各種整形（コードブロックの除去、セパレータの挿入、重複セパレータの圧縮、ヘッダーの設定、発表者行の除去）
    if slide_md:
        slide_md = _strip_whole_code_fence(slide_md)
        slide_md = _insert_separators(slide_md)
        slide_md = _double_separators(slide_md)
        slide_md = _ensure_marp_header(slide_md, _clean_title(ja_title))
        slide_md = _remove_presenter_lines(slide_md)
    return {"slide_md": slide_md, "title": ja_title,
                "error": "", "log": _log(state, f"[slides] generated ({len(slide_md)} chars)")}
  except Exception as e:
    return {"error": f"slides_error: {e}", "log": _log(state, f"[slides] EXCEPTION {e}")}

# -------------------
# Node E: 評価（スライド前提）
# -------------------
MAX_ATTEMPTS = 3
@traceable(run_name="e_evaluate_slides")
def evaluate_slides(state: State) -> Dict:
  if state.get("error"):
    return {}
  slide_md = state.get("slide_md") or ""
  toc = state.get("toc") or []
  topic = state.get("topic") or ""
  eval_guide = (
        "評価観点と重み:\n"
        "- structure(0.20): スライドの流れ、章立て、1スライド1メッセージ\n"
        "- practicality(0.25): 実務に使える具体性（手順、コード例、注意点）\n"
        "- accuracy(0.25): 事実・API仕様・用語の正確さ\n"
        "- readability(0.15): 簡潔明瞭、視認性（箇条書きの粒度）\n"
        "- conciseness(0.15): 冗長性の少なさ\n"
        "合格: score >= 8.0\n"
  )
  prompt = [
        ("system",
         "あなたはCloud Solution Architectです。以下のMarpスライドMarkdownを、"
         "指定の観点・重みで厳密に採点します。出力はJSONのみ。"),
        ("user",
         f"Topic: {topic}\nTOC: {json.dumps(toc, ensure_ascii=False)}\n\n"
         "Slides (Marp Markdown):\n<<<SLIDES\n" + slide_md + "\nSLIDES\n\n"
         "Evaluation Guide:\n<<<EVAL\n" + eval_guide + "\nEVAL\n\n"
         "Return strictly this JSON schema:\n"
         "{\n"
         "  \"score\": number,\n"
         "  \"subscores\": {\"structure\": number, \"practicality\": number, \"accuracy\": number, \"readability\": number, \"conciseness\": number},\n"
         "  \"reasons\": {\"structure\": string, \"practicality\": string, \"accuracy\": string, \"readability\": string, \"conciseness\": string},\n"
         "  \"suggestions\": [string],\n"
         "  \"risk_flags\": [string],\n"
         "  \"pass\": boolean,\n"
         "  \"feedback\": string\n"
         "}"
        )]
  try:
    msg = llm.invoke(prompt)
    raw = msg.content or ""
    js = _find_json(raw) or raw
    data = json.loads(js)

    score = float(data.get("score", 0.0))
    subscores = data.get("subscores") or {}
    reasons = data.get("reasons") or {}
    suggestions = data.get("suggestions") or []
    risk_flags = data.get("risk_flags") or []
    passed = bool(data.get("pass", score >= 8.0))
    feedback = str(data.get("feedback", "")).strip()
    attempts = (state.get("attempts") or 0) + 1

    return {
      "score": score,
      "subscores": subscores,
      "reasons": reasons,
      "suggestions": suggestions,
      "risk_flags": risk_flags,
      "passed": passed,
      "feedback": feedback,
      "attempts": attempts,
      "log": _log(state, f"[evaluate] score={score:.2f} pass={passed} attempts={attempts}")
    }
  except Exception as e:
    return {"error": f"eval_error: {e}", "log": _log(state, f"[evaluate] EXCEPTION {e}")}

def route_after_eval(state: State) -> str:
    if (state.get("attempts") or 0) >= MAX_ATTEMPTS:
        return "ok"
    return "ok" if state.get("passed") else "retry"

# -------------------
# Node F: 保存 & Marpレンダリング
# -------------------
@traceable(run_name="f_save_and_render")
def save_and_render(state: State) -> Dict:
  if state.get("error"):
    return {}
  slide_md = state.get("slide_md") or ""
  title = state.get("title") or "AIスライド"

  # スライド内容が空の場合のエラーハンドリング
  if not slide_md.strip():
    return {"error": "slide_md is empty", "log": _log(state, "[save] ERROR: slide_md is empty")}

  # スライドファイル名の英語表記を生成
  slug_prompt = [
        ("system", "You create concise English slugs for filenames."),
        ("user",
         "Convert the following Japanese title into a short English filename base (<=6 words). "
         "Only letters and spaces; no punctuation or numbers.\n\n"
         f"Title: {title}")
    ]
  emsg = llm.invoke(slug_prompt)
  file_stem = _slugify_en(emsg.content.strip()) or _slugify_en(title)

  slide_dir = Path("slides")
  slide_dir.mkdir(parents=True, exist_ok=True)
  slide_md_path = slide_dir / f"{file_stem}_slides.md"
  slide_md_path.write_text(slide_md, encoding="utf-8")

  marp = shutil.which("marp")
  out_path = str(slide_md_path)
  if marp and SLIDE_FORMAT in ["pdf", "png", "html"]:
    ext = SLIDE_FORMAT
    out_file = slide_dir / f"{file_stem}.{ext}"
    try:
      subprocess.run(
                [marp, str(slide_md_path), f"--{ext}", "-o", str(out_file)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
      out_path = str(out_file)
      log_msg = f"[marp] generated {ext} -> {out_file}"
    except subprocess.CalledProcessError as e:
      log_msg = f"[marp] marp-cli failed: {e}"
  else:
    if not marp and SLIDE_FORMAT:
      log_msg = "[marp] marp-cli not found – skipped rendering (left .md)."
    else:
      log_msg = "[marp] rendering skipped (SLIDE_FORMAT not set)."
  return {
    "slide_path": out_path,
    "log": _log(state, log_msg)
  }

# -------------------
# グラフ構築
# -------------------
graph_builder = StateGraph(State)
graph_builder.add_node("collect_info", collect_info)
graph_builder.add_node("generate_key_points", generate_key_points)
graph_builder.add_node("generate_toc", generate_toc)
graph_builder.add_node("write_slides", write_slides)
graph_builder.add_node("evaluate_slides", evaluate_slides)
graph_builder.add_node("save_and_render", save_and_render)

graph_builder.add_edge(START, "collect_info")
graph_builder.add_edge("collect_info", "generate_key_points")
graph_builder.add_edge("generate_key_points", "generate_toc")
graph_builder.add_edge("generate_toc", "write_slides")
# 評価ノードをスキップして直接save_and_renderへ
graph_builder.add_edge("write_slides", "save_and_render")

# 評価関連のエッジをコメントアウト
# graph_builder.add_edge("write_slides", "evaluate_slides")
# graph_builder.add_conditional_edges(
#   "evaluate_slides",
#   route_after_eval,
#   {"retry": "generate_key_points", "ok": "save_and_render"}
# )

graph_builder.add_edge("save_and_render", END)

graph = graph_builder.compile()

# -------------------
# 実行
# -------------------
if __name__ == "__main__":
  print("LangSmith Tracing:", os.getenv("LANGCHAIN_TRACING_V2"),
      "| Project:", os.getenv("LANGCHAIN_PROJECT"))
  init: State = {
    "topic": "LangGraph × LangSmith × OpenAI × Tavilyで作る：最新AI動向スライド",
    "key_points": [], "toc": [], "slide_md": "",
    "score": 0.0,
    "subscores": {}, "reasons": {},
    "suggestions": [], "risk_flags": [],
    "passed": False, "feedback": "",
    "title": "", "slide_path": "",
    "attempts": 0, "error": "", "log": [],
    "context_md": "", "sources": {}
  }

  config: RunnableConfig = {
    "run_name": "tavily_marp_agent",
    "tags": ["marp", "langgraph", "langsmith", "openai", "tavily"],
    "metadata": {"env": "dev", "date": datetime.now(datetime.timezone.utc).isoformat()},
    "recursive_limit": 60,
  }
  out = graph.invoke(init, config=config)

  print("\n=== RESULT ===")
  if out.get("error"):
    print("ERROR:", out["error"])
  else:
    print("Title    :", out.get("title"))
    print("Slide    :", out.get("slide_path"))
    print("Score    :", out.get("score"))
    print("Passed   :", out.get("passed"))
  print("\n=== LOGS ===")
  for line in out.get("log", []):
    print(line)