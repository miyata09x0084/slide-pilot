# LangGraph × LangSmith × OpenAI × Tavily × Slidev
# スライド生成ワークフロー（PDF/YouTube/テキスト対応）
# フロー: 情報収集 -> キーポイント抽出 -> 目次生成 -> スライド生成 -> 評価 -> 保存

# 共通ロジックのインポート
from slide_core import (
    # 環境変数・定数
    TAVILY_API_KEY, SLIDE_FORMAT, MARP_THEME, MARP_PAGINATE,
    # LLMクライアント
    llm,
    # ユーティリティ関数
    _log, _strip_bullets, _slugify_en, _find_json,
    _ensure_marp_header, _insert_separators, _double_separators,
    _clean_title, _strip_whole_code_fence, _remove_presenter_lines,
    # 日時関数
    JST, now_jst, today_iso, month_ja, month_en, get_today_jst,
    # Slidev生成関数
    _get_all_vendors_info, _create_llm_summarized_bullets,
    _generate_multi_vendor_slides_integrated,
    # Tavily検索関数
    tavily_search, tavily_collect_context, context_to_bullets,
    # テストツール
    generate_slidev_test,
)

# ワークフロー固有のインポート
from typing_extensions import TypedDict
from typing import Optional, Dict, Any, Union, List
from langsmith import traceable
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
import os
import re
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


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
# 入力タイプ自動判別 (Issue #17)
# =======================
def detect_input_type(topic: str) -> str:
    """
    入力タイプを自動判別
    Returns: "pdf" | "youtube" | "text"
    """
    topic_lower = topic.lower()

    # YouTube URLパターン
    youtube_patterns = [
        r'youtube\.com/watch\?v=',
        r'youtu\.be/',
        r'youtube\.com/embed/',
    ]
    for pattern in youtube_patterns:
        if re.search(pattern, topic_lower):
            return "youtube"

    # PDFファイルパターン
    if topic_lower.endswith('.pdf') or '/uploads/' in topic_lower:
        return "pdf"

    # それ以外はテキスト（Tavily検索）
    return "text"

# =======================
# Node A: 情報収集（PDF/YouTube/Tavily対応）
# =======================
@traceable(run_name="a_collect_info")
def collect_info(state: State) -> State:
  topic = state.get("topic") or "AI最新情報"

  # 入力タイプを自動判別
  input_type = detect_input_type(topic)

  try:
    # PDF処理パイプライン
    if input_type == "pdf":
      # 条件付きインポート（パッケージ構造対応）
      try:
        from .tools.pdf_processor import process_pdf
      except ImportError:
        from tools.pdf_processor import process_pdf
      result = process_pdf(topic)
      data = json.loads(result)

      if data["status"] == "success":
        # PDFコンテンツを整形
        pdf_filename = Path(topic).stem
        context_md = f"# PDF: {pdf_filename}\n\n{data['content'][:10000]}"  # 最初の10000文字

        # sourcesに保存（後で参照可能に）
        sources = {
          "pdf_content": [{
            "title": pdf_filename,
            "url": topic,
            "content": data['content'][:500],  # プレビュー用
            "num_pages": data.get('num_pages', 0),
            "total_chars": data.get('total_chars', 0)
          }]
        }

        return {
          "sources": sources,
          "context_md": context_md,
          "log": _log(state, f"[pdf] pages={data.get('num_pages')}, chars={data.get('total_chars')}")
        }
      else:
        return {"error": f"PDF処理エラー: {data['message']}", "log": _log(state, f"[pdf] ERROR {data['message']}")}

    # YouTube処理パイプライン（将来実装）
    elif input_type == "youtube":
      return {"error": "YouTube処理は準備中です（Issue #18で実装予定）", "log": _log(state, "[youtube] NOT_IMPLEMENTED")}

    # テキスト処理（既存のTavily検索）
    else:
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

      sources = tavily_collect_context(queries, max_per_query=6, default_time_range="month")
      context_md = context_to_bullets(sources)
      return {
        "sources": sources,
        "context_md": context_md,
        "log": _log(state, f"[tavily] months={month_labels} queries={len(queries)}")
      }

  except Exception as e:
    return {"error": f"collect_info_error: {e}", "log": _log(state, f"[collect_info] EXCEPTION {e}")}

# -------------------
# Node B: 重要ポイント生成
# -------------------
@traceable(run_name="b_generate_key_points")
def generate_key_points(state: State) -> Dict:
  topic = state.get("topic") or "AI最新情報"
  ctx = state.get("context_md") or ""

  # 入力タイプを判別
  input_type = detect_input_type(topic)

  # PDF処理の場合は汎用的なポイント抽出
  if input_type == "pdf":
    prompt = [
      ("system", "あなたは教育のプロフェッショナルです。PDFの内容から重要なポイントを抽出します。"),
      ("user",
        f"以下のPDF内容から、中学生にもわかるように重要なポイントを5個、"
        f"短い箇条書きで抽出してください。\n\n"
        f"[PDF内容]\n{ctx[:4000]}\n\n"  # 最大4000文字
        f"箇条書き形式で出力してください:")
    ]
  else:
    # AI最新情報の場合は既存のプロンプト
    prompt = [
      ("system", "あなたはSolution Engineerです。これからMarpスライドでAI最新情報を発表します。"),
      ("user",
        "以下の「最新情報サマリ（出典付き）」を参考に、発表の重要ポイントを各社5個、"
        "短い箇条書きで。URLも含めてください。\n\n"
        f"[最新情報サマリ]\n{ctx}\n\n[トピック]\n{topic}")
    ]

  try:
    msg = llm.invoke(prompt)
    bullets = _strip_bullets(msg.content.splitlines())[:5] or [msg.content.strip()]
    return {"key_points": bullets, "log": _log(state, f"[key_points] {bullets}")}
  except Exception as e:
    return {"error": f"key_points_error: {e}", "log": _log(state, f"[key_points] EXCEPTION {e}")}

# -------------------
# Node C: 目次生成
# -------------------
@traceable(run_name="c_generate_toc")
def generate_toc(state: State) -> Dict:
  topic = state.get("topic") or ""
  key_points = state.get("key_points") or []

  # 入力タイプを判別
  input_type = detect_input_type(topic)

  # PDF処理の場合は中学生向けの章立て
  if input_type == "pdf":
    prompt = [
      ("system", "あなたは教育のプロフェッショナルです。中学生向けスライドの構成（目次）を作ります。"),
      ("user",
       "以下の重要ポイントから、中学生にもわかりやすい5〜8個の章立てを JSON の {\"toc\": [ ... ]} 形式で返してください。\n\n"
       "重要ポイント:\n- " + "\n- ".join(key_points) + "\n\n"
       "章立てはシンプルで親しみやすい言葉を使ってください。")
    ]
  else:
    # AI最新情報の場合は既存のプロンプト
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
# Node D: スライド本文（Slidev）生成 (Phase 1 - MVP-1)
# -------------------
@traceable(run_name="d_generate_slide_slidev")
def write_slides_slidev(state: State) -> Dict:
  """Slidev形式のスライドを生成（全6社対応 / PDF対応）"""
  sources = state.get("sources") or {}
  topic = state.get("topic") or "AI最新情報"
  context_md = state.get("context_md") or ""
  key_points = state.get("key_points") or []
  toc = state.get("toc") or []

  # 入力タイプを判別
  input_type = detect_input_type(topic)

  try:
    # PDF処理の場合は汎用的なスライドを生成
    if input_type == "pdf":
      # PDFファイル名からタイトル生成
      pdf_filename = Path(topic).stem if topic.endswith('.pdf') else "PDF資料"
      ja_title = f"{pdf_filename} - 中学生向け解説"

      # LLMでSlidevマークダウンを生成
      prompt = [
        ("system",
         "あなたは教育のプロフェッショナルです。PDFの内容を中学生にもわかりやすく説明するSlidevスライドを作成します。"),
        ("user",
         f"以下のPDF内容から、中学生向けのわかりやすいスライドを作成してください。\n\n"
         f"【PDF内容】\n{context_md[:8000]}\n\n"  # 最大8000文字
         f"【重要ポイント】\n" + "\n".join([f"- {kp}" for kp in key_points[:5]]) + "\n\n"
         f"【目次】\n" + "\n".join([f"- {t}" for t in toc[:8]]) + "\n\n"
         f"【要件】\n"
         f"- Slidev形式（YAMLフロントマター + Markdown）\n"
         f"- theme: apple-basic を使用\n"
         f"- タイトルスライド: # {ja_title}\n"
         f"- Agendaスライド: 目次を<v-clicks>で表示\n"
         f"- 各セクション: 目次に基づいて5-8スライド作成\n"
         f"- 各スライドは簡潔に（1スライド1メッセージ）\n"
         f"- 中学生でもわかる言葉で説明\n"
         f"- 絵文字を活用して視覚的に\n"
         f"- まとめスライド: 重要ポイントを3-5個に凝縮\n\n"
         f"出力はSlidevマークダウンのみ（コードブロック不要）:")
      ]

      msg = llm.invoke(prompt)
      slide_md = msg.content.strip()

      # コードブロックがあれば除去
      slide_md = _strip_whole_code_fence(slide_md)

      return {
        "slide_md": slide_md,
        "title": ja_title,
        "error": "",
        "log": _log(state, f"[slides_slidev_pdf] generated ({len(slide_md)} chars) from PDF")
      }

    # AI最新情報（Tavily）の場合は既存のマルチベンダー生成
    else:
      ja_title = f"{month_ja()} AI最新情報まとめ"
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
MAX_ATTEMPTS = 3

# Slidev用評価ノード (Phase 3)
@traceable(run_name="e_evaluate_slides_slidev")
def evaluate_slides_slidev(state: State) -> Dict:
  """Slidevスライドの品質評価"""
  if state.get("error"):
    return {}
  slide_md = state.get("slide_md") or ""
  toc = state.get("toc") or []
  topic = state.get("topic") or ""
  eval_guide = (
        "評価観点と重み:\n"
        "- structure(0.20): スライドの流れ、章立て、1スライド1メッセージ\n"
        "- practicality(0.25): 実務に使える具体性（手順、具体例、注意点）\n"
        "- accuracy(0.25): 事実・用語の正確さ\n"
        "- readability(0.15): 簡潔明瞭、視認性（箇条書きの粒度）\n"
        "- conciseness(0.15): 冗長性の少なさ\n"
        "合格: score >= 8.0\n"
  )
  prompt = [
        ("system",
         "あなたはCloud Solution Architectです。以下のSlidevスライドMarkdownを、"
         "指定の観点・重みで厳密に採点します。出力はJSONのみ。"),
        ("user",
         f"Topic: {topic}\nTOC: {json.dumps(toc, ensure_ascii=False)}\n\n"
         "Slides (Slidev Markdown):\n<<<SLIDES\n" + slide_md + "\nSLIDES\n\n"
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
      "log": _log(state, f"[evaluate_slidev] score={score:.2f} pass={passed} attempts={attempts}")
    }
  except Exception as e:
    return {"error": f"eval_error: {e}", "log": _log(state, f"[evaluate_slidev] EXCEPTION {e}")}

def route_after_eval_slidev(state: State) -> str:
    """評価結果に基づいてリトライまたは完了を判定"""
    if (state.get("attempts") or 0) >= MAX_ATTEMPTS:
        return "ok"
    return "ok" if state.get("passed") else "retry"

# -------------------
# Node F: 保存 & Slidevレンダリング (Phase 1 - MVP-2)
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
# グラフ構築
# -------------------
graph_builder = StateGraph(State)
graph_builder.add_node("collect_info", collect_info)
graph_builder.add_node("generate_key_points", generate_key_points)
graph_builder.add_node("generate_toc", generate_toc)
graph_builder.add_node("write_slides_slidev", write_slides_slidev)
graph_builder.add_node("save_and_render_slidev", save_and_render_slidev)
graph_builder.add_node("evaluate_slides_slidev", evaluate_slides_slidev)

# エッジ定義（Slidevフロー with 評価ループ）
graph_builder.add_edge(START, "collect_info")
graph_builder.add_edge("collect_info", "generate_key_points")
graph_builder.add_edge("generate_key_points", "generate_toc")
graph_builder.add_edge("generate_toc", "write_slides_slidev")
graph_builder.add_edge("write_slides_slidev", "evaluate_slides_slidev")

# 評価ループ（最大3回リトライ）
graph_builder.add_conditional_edges(
  "evaluate_slides_slidev",
  route_after_eval_slidev,
  {"retry": "generate_key_points", "ok": "save_and_render_slidev"}
)

graph_builder.add_edge("save_and_render_slidev", END)

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