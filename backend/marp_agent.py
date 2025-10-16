# LangGraph × LangSmith × OpenAI × Tavily × Marp
# フロー:
# 0) Tavilyで情報収集 -> 1) アウトライン生成 -> 2) 目次生成 -> 3) スライド(Marp)本文生成 -> 4) 評価(>=8でOK/それ以外は2へループ) -> 5) スライドMarkdown保存(+ marp-cliでpdf/png/html出力)

from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from typing import Optional, Dict, Any, Union
from typing_extensions import TypedDict
import os
import re
import requests
from typing import List
from datetime import datetime, timedelta, timezone
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from langgraph.graph import StateGraph, START, END
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
# Slidev用ヘルパー関数 (Phase 1 - MVP-4)
# -------------------
def _get_all_vendors_info() -> List[Dict]:
  """全6社のベンダー情報を返す（Slidev用）"""
  return [
    {
      "name": "Microsoft AI",
      "emoji": "🏢",
      "domains": ["azure.microsoft.com", "news.microsoft.com", "learn.microsoft.com"],
      "queries": ["Microsoft AI updates", "Azure OpenAI updates"],
      "gradient": "linear-gradient(135deg, #0078d4 0%, #00bcf2 100%)",
    },
    {
      "name": "OpenAI",
      "emoji": "🤖",
      "domains": ["openai.com"],
      "queries": ["OpenAI announcements", "OpenAI updates"],
      "gradient": "linear-gradient(135deg, #10a37f 0%, #1a7f64 100%)",
    },
    {
      "name": "Google Gemini",
      "emoji": "🌟",
      "domains": ["blog.google", "ai.googleblog.com", "research.google"],
      "queries": ["Google AI updates", "Gemini updates"],
      "gradient": "linear-gradient(135deg, #4285f4 0%, #34a853 100%)",
    },
    {
      "name": "AWS Bedrock",
      "emoji": "☁️",
      "domains": ["aws.amazon.com"],
      "queries": ["AWS Bedrock updates", "Amazon AI updates"],
      "gradient": "linear-gradient(135deg, #ff9900 0%, #f90 100%)",
    },
    {
      "name": "Meta AI",
      "emoji": "🦙",
      "domains": ["ai.meta.com"],
      "queries": ["Meta AI updates", "Llama updates"],
      "gradient": "linear-gradient(135deg, #0668e1 0%, #0a7cff 100%)",
    },
    {
      "name": "Anthropic",
      "emoji": "🧠",
      "domains": ["anthropic.com"],
      "queries": ["Anthropic Claude updates", "Claude announcements"],
      "gradient": "linear-gradient(135deg, #d4a574 0%, #c49a6c 100%)",
    },
  ]

def _create_llm_summarized_bullets(results: List[Dict], vendor_name: str = "Microsoft AI", num_bullets: int = 3) -> List[str]:
  """検索結果をLLMで要約して箇条書きを生成（Slidev用）

  Args:
    results: Tavily検索結果のリスト
    vendor_name: ベンダー名
    num_bullets: 生成する箇条書きの数

  Returns:
    箇条書きのリスト
  """
  # 検索結果をテキストに整形
  results_text = ""
  for i, result in enumerate(results[:5], 1):
    title = result.get("title", "")
    content = result.get("content", "")[:300]
    url = result.get("url", "")
    results_text += f"\n### 記事 {i}\n"
    results_text += f"タイトル: {title}\n"
    results_text += f"内容: {content}\n"
    results_text += f"URL: {url}\n"

  if not results_text.strip():
    return [
      "- **検索結果が見つかりませんでした**",
      "- 後でもう一度お試しください"
    ]

  # LLMで箇条書きに要約
  prompt = [
    ("system", "あなたはAI技術のエキスパートです。検索結果から重要なポイントを抽出します。"),
    ("user",
     f"以下の{vendor_name}に関する検索結果から、重要なポイントを{num_bullets}つの箇条書きで簡潔にまとめてください。\n"
     f"各箇条書きは1-2文で、技術的に正確かつ分かりやすく記述してください。\n\n"
     f"{results_text}\n\n"
     f"出力形式:\n" + "\n".join([f"- ポイント{i+1}" for i in range(num_bullets)]))
  ]

  try:
    msg = llm.invoke(prompt)
    lines = msg.content.strip().split("\n")
    bullets = [line.strip() for line in lines if line.strip().startswith("-")][:num_bullets]

    # 指定数に満たない場合はパディング
    while len(bullets) < num_bullets:
      bullets.append("- （情報が不足しています）")

    return bullets

  except Exception as e:
    # LLM失敗時はシンプル版にフォールバック
    fallback = []
    for result in results[:num_bullets]:
      title = result.get("title", "")[:80]
      if title:
        fallback.append(f"- **{title}**")

    while len(fallback) < num_bullets:
      fallback.append("- （情報が不足しています）")

    return fallback[:num_bullets]

def _generate_multi_vendor_slides_integrated(topic: str, sources: Dict[str, List[Dict]], mvp_version: str = "AI Industry Report") -> str:
  """全ベンダーのSlidevマークダウンを生成（marp_agent統合版）

  Args:
    topic: スライドのトピック
    sources: collect_info()で取得したTavily検索結果
    mvp_version: バージョン表記

  Returns:
    Slidevマークダウン文字列
  """
  vendors = _get_all_vendors_info()
  vendor_bullets = []

  # 各ベンダーの検索結果から箇条書きを生成
  for vendor in vendors:
    # sourcesから該当するベンダーの検索結果を抽出
    vendor_results = []
    for query, items in sources.items():
      # クエリに該当するベンダーのドメインが含まれているか確認
      for domain in vendor["domains"]:
        if domain in str(items):
          vendor_results.extend(items)
          break

    # 重複除去
    seen_urls = set()
    unique_results = []
    for item in vendor_results:
      url = item.get("url", "")
      if url and url not in seen_urls:
        seen_urls.add(url)
        unique_results.append(item)

    # LLMで箇条書きに要約
    bullets = _create_llm_summarized_bullets(unique_results[:5], vendor["name"], num_bullets=3)

    vendor_bullets.append({
      "name": vendor["name"],
      "emoji": vendor["emoji"],
      "bullets": bullets,
      "gradient": vendor["gradient"],
    })

  # Slidevマークダウン生成
  slide_content = f"""---
theme: apple-basic
highlighter: shiki
class: text-center
drawings:
  persist: false
fonts:
  sans: 'Inter'
  serif: 'Roboto Slab'
  mono: 'Fira Code'
---

# 🚀 {topic}
## {mvp_version}

<div class="pt-12">
  <span class="px-2 py-1 rounded" style="background: #6366f1; color: white;">
    {month_ja()}
  </span>
</div>

---
layout: intro
class: text-left
---

## 📋 Agenda

<v-clicks>

"""

  # アジェンダ項目
  for vb in vendor_bullets:
    slide_content += f"- {vb['emoji']} **{vb['name']}** - 最新アップデート\n"

  slide_content += "\n</v-clicks>\n\n"

  # 各ベンダーのスライド
  for vb in vendor_bullets:
    slide_content += f"""---
layout: two-cols
class: px-2
---

## {vb['emoji']} {vb['name']}

<v-clicks>

{chr(10).join(vb['bullets'])}

</v-clicks>

::right::

<div class="flex items-center justify-center h-full">
  <div style="width: 280px; height: 180px; background: {vb['gradient']}; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; font-weight: bold; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
    {vb['name']}
  </div>
</div>

"""

  # まとめスライド
  slide_content += f"""---
layout: end
class: text-center
---

# ✨ まとめ

<div class="mt-8">

## 完了 🎉

全6社のAI最新情報を統合しました

</div>

<div style="position: absolute; bottom: 1.5rem; right: 1.5rem; font-size: 0.875rem; opacity: 0.5;">
  Generated by SlidePilot AI ({mvp_version})
</div>

"""

  return slide_content

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
# Slidev Test Tool (Phase 0: MVP)
# -------------------
@tool("generate_slidev_test")
def generate_slidev_test(topic: str = "AI最新情報") -> str:
  """Slidevで簡易スライドを生成（テスト用・ハードコード）"""

  # ハードコードされたSlidevマークダウン
  slide_content = f"""---
theme: apple-basic
layout: cover
background: #ffffff
---

# {topic}
2025年10月版

---
layout: intro
---

## Agenda
- Microsoft AI 最新情報
- OpenAI の動向
- Google Gemini アップデート
- まとめ

---

## Microsoft AI

- **Azure OpenAI Service**: GPT-4 Turbo対応
- **Copilot Studio**: ノーコードAI開発
- **Semantic Kernel**: エージェント開発フレームワーク

---
layout: two-cols
---

## OpenAI 最新情報

::left::

### GPT-4 Turbo
- コスト削減
- 128K context window
- JSON mode

::right::

### DALL-E 3
- より高精度な画像生成
- プロンプト理解向上

---

## Google Gemini

- **Gemini Pro**: マルチモーダルAI
- **Vertex AI統合**: エンタープライズ向け
- **Duet AI**: Google Workspace連携

---
layout: end
---

# まとめ

AI技術は急速に進化中
各社の最新情報をキャッチアップしましょう

"""

  # ファイル保存
  slide_dir = Path(__file__).parent / "slides"
  slide_dir.mkdir(parents=True, exist_ok=True)

  # ファイル名生成
  slug = _slugify_en(topic) or "test"
  md_path = slide_dir / f"{slug}_slidev_test.md"
  md_path.write_text(slide_content, encoding="utf-8")

  # Slidev PDF出力
  pdf_path = slide_dir / f"{slug}_slidev_test.pdf"

  slidev = shutil.which("slidev")
  if slidev:
    try:
      # Slidev export コマンド
      subprocess.run(
        ["slidev", "export", str(md_path),
         "--output", str(pdf_path),
         "--format", "pdf",
         "--timeout", "60000"],  # 60秒タイムアウト
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90  # プロセス全体のタイムアウト
      )
      return json.dumps({
        "status": "success",
        "slide_path": str(pdf_path.relative_to(slide_dir.parent)),
        "title": topic,
        "message": f"Slidevスライドを生成しました: {pdf_path.name}"
      }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
      return json.dumps({
        "status": "error",
        "slide_path": str(md_path.relative_to(slide_dir.parent)),
        "title": topic,
        "error": "PDF生成がタイムアウトしました（90秒超過）",
        "message": "Markdownファイルのみ保存しました"
      }, ensure_ascii=False)
    except subprocess.CalledProcessError as e:
      # PDF生成失敗時はMDのみ返す
      error_msg = e.stderr.decode() if e.stderr else str(e)
      return json.dumps({
        "status": "partial",
        "slide_path": str(md_path.relative_to(slide_dir.parent)),
        "title": topic,
        "error": f"PDF生成失敗: {error_msg}",
        "message": "Markdownファイルのみ保存しました"
      }, ensure_ascii=False)
  else:
    # slidev未インストール時
    return json.dumps({
      "status": "md_only",
      "slide_path": str(md_path.relative_to(slide_dir.parent)),
      "title": topic,
      "message": "slidevが見つかりません。Markdownのみ保存しました"
    }, ensure_ascii=False)


# -------------------
# State
# -------------------
class State(TypedDict):
  """LangGraphワークフローの状態管理"""

  # 入力
  topic: str                                    # スライドの主題

  # 情報収集 (Node A)
  sources: Dict[str, List[Dict[str, str]]]      # Tavily検索結果
  context_md: str                               # 検索結果のMarkdown

  # コンテンツ生成 (Node B-D)
  key_points: List[str]                         # 重要ポイント5個
  toc: List[str]                                # 目次5-8項目
  slide_md: str                                 # Marpスライド本文
  title: str                                    # スライドタイトル

  # 評価 (Node E)
  score: float                                  # 総合スコア (0-10)
  subscores: Dict[str, float]                   # 項目別スコア
  reasons: Dict[str, str]                       # 評価理由
  suggestions: List[str]                        # 改善提案
  risk_flags: List[str]                         # リスク事項
  passed: bool                                  # 合格判定 (>=8.0)
  feedback: str                                 # 総合フィードバック
  attempts: int                                 # リトライ回数 (最大3)

  # 出力 (Node F)
  slide_path: str                               # 保存ファイルパス

  # システム
  error: str                                    # エラーメッセージ
  log: List[str]                                # 実行ログ

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
        "あなたはMicrosoftのSolution Engineerで、Marp形式のスライドを作ります。"
        "出力はコードブロックで囲まず、スライド区切り（---）は入れないでください。"
        "各スライドは必ず H2 見出し（## ）で開始。タイトルスライドに発表者名は書かないでください。"
        "重要: 以下の“最新情報サマリ”の範囲内の事実のみに基づいて作成し、サマリに無い情報は書かないでください。"),
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
# Node D-Slidev: スライド本文（Slidev）生成 (Phase 1 - MVP-1)
# -------------------
@traceable(run_name="d_generate_slide_slidev")
def write_slides_slidev(state: State) -> Dict:
  """Slidev形式のスライドを生成（全6社対応）"""
  sources = state.get("sources") or {}
  topic = state.get("topic") or "AI最新情報"

  # タイトルは当月で固定
  ja_title = f"{month_ja()} AI最新情報まとめ"

  try:
    # Slidevマークダウン生成
    slide_md = _generate_multi_vendor_slides_integrated(
      topic=ja_title,
      sources=sources,
      mvp_version="AI Industry Report 2025"
    )

    return {
      "slide_md": slide_md,
      "title": ja_title,
      "error": "",
      "log": _log(state, f"[slides_slidev] generated ({len(slide_md)} chars, 6 vendors)")
    }

  except Exception as e:
    # エラー時はフォールバックスライドを生成
    fallback_md = f"""---
theme: apple-basic
highlighter: shiki
class: text-center
---

# 🚀 {ja_title}
## エラーが発生しました

<div class="pt-12">
  <span class="px-2 py-1 rounded" style="background: #ef4444; color: white;">
    Error: {str(e)}
  </span>
</div>

---

## ⚠️ エラー詳細

スライド生成中にエラーが発生しました。

- 検索結果の取得に失敗した可能性があります
- もう一度お試しください

"""
    return {
      "slide_md": fallback_md,
      "title": ja_title,
      "error": f"slides_slidev_error: {e}",
      "log": _log(state, f"[slides_slidev] EXCEPTION {e} - using fallback")
    }

# -------------------
# Node E: 評価（スライド前提）
# -------------------
# MAX_ATTEMPTS = 3
# @traceable(run_name="e_evaluate_slides")
# def evaluate_slides(state: State) -> Dict:
#   if state.get("error"):
#     return {}
#   slide_md = state.get("slide_md") or ""
#   toc = state.get("toc") or []
#   topic = state.get("topic") or ""
#   eval_guide = (
#         "評価観点と重み:\n"
#         "- structure(0.20): スライドの流れ、章立て、1スライド1メッセージ\n"
#         "- practicality(0.25): 実務に使える具体性（手順、コード例、注意点）\n"
#         "- accuracy(0.25): 事実・API仕様・用語の正確さ\n"
#         "- readability(0.15): 簡潔明瞭、視認性（箇条書きの粒度）\n"
#         "- conciseness(0.15): 冗長性の少なさ\n"
#         "合格: score >= 8.0\n"
#   )
#   prompt = [
#         ("system",
#          "あなたはCloud Solution Architectです。以下のMarpスライドMarkdownを、"
#          "指定の観点・重みで厳密に採点します。出力はJSONのみ。"),
#         ("user",
#          f"Topic: {topic}\nTOC: {json.dumps(toc, ensure_ascii=False)}\n\n"
#          "Slides (Marp Markdown):\n<<<SLIDES\n" + slide_md + "\nSLIDES\n\n"
#          "Evaluation Guide:\n<<<EVAL\n" + eval_guide + "\nEVAL\n\n"
#          "Return strictly this JSON schema:\n"
#          "{\n"
#          "  \"score\": number,\n"
#          "  \"subscores\": {\"structure\": number, \"practicality\": number, \"accuracy\": number, \"readability\": number, \"conciseness\": number},\n"
#          "  \"reasons\": {\"structure\": string, \"practicality\": string, \"accuracy\": string, \"readability\": string, \"conciseness\": string},\n"
#          "  \"suggestions\": [string],\n"
#          "  \"risk_flags\": [string],\n"
#          "  \"pass\": boolean,\n"
#          "  \"feedback\": string\n"
#          "}"
#         )]
#   try:
#     msg = llm.invoke(prompt)
#     raw = msg.content or ""
#     js = _find_json(raw) or raw
#     data = json.loads(js)
#
#     score = float(data.get("score", 0.0))
#     subscores = data.get("subscores") or {}
#     reasons = data.get("reasons") or {}
#     suggestions = data.get("suggestions") or []
#     risk_flags = data.get("risk_flags") or []
#     passed = bool(data.get("pass", score >= 8.0))
#     feedback = str(data.get("feedback", "")).strip()
#     attempts = (state.get("attempts") or 0) + 1
#
#     return {
#       "score": score,
#       "subscores": subscores,
#       "reasons": reasons,
#       "suggestions": suggestions,
#       "risk_flags": risk_flags,
#       "passed": passed,
#       "feedback": feedback,
#       "attempts": attempts,
#       "log": _log(state, f"[evaluate] score={score:.2f} pass={passed} attempts={attempts}")
#     }
#   except Exception as e:
#     return {"error": f"eval_error: {e}", "log": _log(state, f"[evaluate] EXCEPTION {e}")}
#
# def route_after_eval(state: State) -> str:
#     if (state.get("attempts") or 0) >= MAX_ATTEMPTS:
#         return "ok"
#     return "ok" if state.get("passed") else "retry"

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

  slide_dir = Path(__file__).parent / "slides"
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
# Node F-Slidev: 保存 & Slidevレンダリング (Phase 1 - MVP-2)
# -------------------
@traceable(run_name="f_save_and_render_slidev")
def save_and_render_slidev(state: State) -> Dict:
  """Slidev形式のスライドを保存してPDF生成"""
  if state.get("error"):
    return {}

  slide_md = state.get("slide_md") or ""
  title = state.get("title") or "AIスライド"

  # スライド内容が空の場合のエラーハンドリング
  if not slide_md.strip():
    return {
      "error": "slide_md is empty",
      "log": _log(state, "[save_slidev] ERROR: slide_md is empty")
    }

  # スライドファイル名の英語表記を生成
  slug_prompt = [
    ("system", "You create concise English slugs for filenames."),
    ("user",
     "Convert the following Japanese title into a short English filename base (<=6 words). "
     "Only letters and spaces; no punctuation or numbers.\n\n"
     f"Title: {title}")
  ]

  try:
    emsg = llm.invoke(slug_prompt)
    file_stem = _slugify_en(emsg.content.strip()) or _slugify_en(title)
  except Exception:
    file_stem = _slugify_en(title) or "ai-latest-info"

  slide_dir = Path(__file__).parent / "slides"
  slide_dir.mkdir(parents=True, exist_ok=True)
  slide_md_path = slide_dir / f"{file_stem}_slidev.md"
  slide_md_path.write_text(slide_md, encoding="utf-8")

  # Slidev PDF生成
  slidev = shutil.which("slidev")
  out_path = str(slide_md_path)

  if slidev and SLIDE_FORMAT == "pdf":
    pdf_file = slide_dir / f"{file_stem}_slidev.pdf"
    try:
      subprocess.run(
        ["slidev", "export", str(slide_md_path),
         "--output", str(pdf_file),
         "--format", "pdf",
         "--timeout", "60000"],  # 60秒タイムアウト
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90  # プロセス全体のタイムアウト
      )
      out_path = str(pdf_file)
      log_msg = f"[slidev] generated PDF -> {pdf_file.name}"
    except subprocess.TimeoutExpired:
      log_msg = f"[slidev] PDF generation timeout (90s) - MD saved at {slide_md_path.name}"
    except subprocess.CalledProcessError as e:
      error_msg = e.stderr.decode() if e.stderr else str(e)
      log_msg = f"[slidev] export failed: {error_msg[:100]} - MD saved"
  else:
    if not slidev:
      log_msg = "[slidev] slidev-cli not found – skipped rendering (left .md)."
    else:
      log_msg = f"[slidev] rendering skipped (SLIDE_FORMAT={SLIDE_FORMAT}, only pdf supported)."

  return {
    "slide_path": out_path,
    "log": _log(state, log_msg)
  }

# -------------------
# グラフ構築 (Phase 1 - MVP-3)
# -------------------
graph_builder = StateGraph(State)
graph_builder.add_node("collect_info", collect_info)
graph_builder.add_node("generate_key_points", generate_key_points)
graph_builder.add_node("generate_toc", generate_toc)

# Marpノード（参考用に保持、現在は未使用）
# graph_builder.add_node("write_slides", write_slides)
# graph_builder.add_node("save_and_render", save_and_render)

# Slidevノード（Phase 1で使用）
graph_builder.add_node("write_slides_slidev", write_slides_slidev)
graph_builder.add_node("save_and_render_slidev", save_and_render_slidev)

# 評価ノード（現在は無効化）
# graph_builder.add_node("evaluate_slides", evaluate_slides)

# エッジ定義（Slidevフロー）
graph_builder.add_edge(START, "collect_info")
graph_builder.add_edge("collect_info", "generate_key_points")
graph_builder.add_edge("generate_key_points", "generate_toc")
graph_builder.add_edge("generate_toc", "write_slides_slidev")
graph_builder.add_edge("write_slides_slidev", "save_and_render_slidev")
graph_builder.add_edge("save_and_render_slidev", END)

# Marpフロー（参考用にコメントアウト）
# graph_builder.add_edge("generate_toc", "write_slides")
# graph_builder.add_edge("write_slides", "save_and_render")
# graph_builder.add_edge("save_and_render", END)

# 評価ループ（現在は無効化）
# graph_builder.add_conditional_edges(
#   "evaluate_slides",
#   route_after_eval,
#   {"retry": "generate_key_points", "ok": "save_and_render"}
# )

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
    "metadata": {"env": "dev", "date": datetime.now(timezone.utc).isoformat()},
    "recursive_limit": 60,
  }
  out = graph.invoke(init, config=config)

  print("\n=== RESULT ===")
  if out.get("error"):
    print("ERROR:", out["error"])
  else:
    print("Title    :", out.get("title"))
    print("Slide    :", out.get("slide_path"))
    # print("Score    :", out.get("score"))
    # print("Passed   :", out.get("passed"))
  print("\n=== LOGS ===")
  for line in out.get("log", []):
    print(line)