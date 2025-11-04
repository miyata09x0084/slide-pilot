# LangGraph × LangSmith × OpenAI × Tavily × Slidev
# スライド生成ワークフロー（PDF/YouTube/テキスト対応）
# フロー: 情報収集 -> キーポイント抽出 -> 目次生成 -> スライド生成 -> 評価 -> 保存

# 標準ライブラリ
import os
import re
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Union, List

# サードパーティライブラリ
from typing_extensions import TypedDict
from langsmith import traceable
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig

# ローカルモジュール
from app.config import settings
from app.core.config import TAVILY_API_KEY, SLIDE_FORMAT, MARP_THEME, MARP_PAGINATE
from app.core.llm import llm
from app.core.supabase import save_slide_to_supabase
from app.core.utils import (
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
from app.prompts.evaluation_prompts import get_evaluation_prompt
from app.prompts.slide_prompts import (
    get_key_points_map_prompt,
    get_key_points_reduce_prompt,
    get_key_points_ai_prompt,
    get_toc_pdf_prompt,
    get_toc_ai_prompt,
    get_slide_title_prompt,
    get_slide_pdf_prompt,
    get_slug_prompt,
)
from app.tools.pdf import process_pdf


# -------------------
# State
# -------------------
class State(TypedDict, total=False):
  """LangGraphワークフローの状態管理

  NOTE: user_id は実行コンテキスト情報（Read-Only）であり、
        ビジネスロジックデータではない。ノード内で変更禁止。
        将来 LangGraph v0.6+ では context_schema に移行予定。

  total=False を指定することで、全フィールドをオプショナルとし、
  後方互換性を確保している。
  """

  # ══════════════════════════════════════════════════════════
  # 実行コンテキスト（Read-Only、ノードで変更禁止）
  # ══════════════════════════════════════════════════════════
  user_id: str                                  # ユーザー識別子（デフォルト: "anonymous"）

  # ══════════════════════════════════════════════════════════
  # 入力
  # ══════════════════════════════════════════════════════════
  topic: str                                    # スライドの主題

  # ══════════════════════════════════════════════════════════
  # 情報収集 (Node A)
  # ══════════════════════════════════════════════════════════
  sources: Dict[str, List[Dict[str, str]]]      # Tavily検索結果
  context_md: str                               # 検索結果のMarkdown

  # ══════════════════════════════════════════════════════════
  # コンテンツ生成 (Node B-D)
  # ══════════════════════════════════════════════════════════
  key_points: List[str]                         # 重要ポイント5個
  toc: List[str]                                # 目次5-8項目
  slide_md: str                                 # Marpスライド本文
  title: str                                    # スライドタイトル

  # ══════════════════════════════════════════════════════════
  # 評価 (Node E)
  # ══════════════════════════════════════════════════════════
  score: float                                  # 総合スコア (0-10)
  subscores: Dict[str, float]                   # 項目別スコア
  reasons: Dict[str, str]                       # 評価理由
  suggestions: List[str]                        # 改善提案
  risk_flags: List[str]                         # リスク事項
  passed: bool                                  # 合格判定 (>=8.0)
  feedback: str                                 # 総合フィードバック
  attempts: int                                 # リトライ回数 (最大3)

  # ══════════════════════════════════════════════════════════
  # 図解生成 (Node D.5) - Issue #25
  # ══════════════════════════════════════════════════════════
  diagrams: Dict[str, Any]                      # 生成された図解のメタデータ

  # ══════════════════════════════════════════════════════════
  # 出力 (Node F)
  # ══════════════════════════════════════════════════════════
  slide_path: str                               # ローカルファイルパス
  slide_id: str                                 # Supabase slide ID（オプショナル）
  pdf_url: str                                  # Supabase公開URL（オプショナル）

  # ══════════════════════════════════════════════════════════
  # システム
  # ══════════════════════════════════════════════════════════
  error: str                                    # エラーメッセージ
  log: List[str]                                # 実行ログ

# =======================
# 入力タイプ自動判別
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
      result = process_pdf(topic)
      data = json.loads(result)

      if data["status"] == "success":
        # PDFコンテンツを整形（★全文保持に変更）
        pdf_filename = Path(topic).stem
        full_content = data['content']  # チャンク区切り "---" で結合済み
        context_md = f"# PDF: {pdf_filename}\n\n{full_content}"

        # sourcesに保存（チャンク情報も含める）
        chunks = full_content.split("\n\n---\n\n")
        sources = {
          "pdf_content": [{
            "title": pdf_filename,
            "url": topic,
            "content": data['content'][:500],  # プレビュー用
            "num_pages": data.get('num_pages', 0),
            "total_chars": data.get('total_chars', 0),
            "num_chunks": len(chunks),
            "chunks": chunks  # ★全チャンクを保持
          }]
        }

        return {
          "sources": sources,
          "context_md": context_md,
          "log": _log(state, f"[pdf] pages={data.get('num_pages')}, chars={data.get('total_chars')}, chunks={len(chunks)}")
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
  sources = state.get("sources") or {}

  # 入力タイプを判別
  input_type = detect_input_type(topic)

  # PDF処理の場合はMap-Reduce方式で全チャンクを処理
  if input_type == "pdf":
    try:
      # チャンクを取得
      pdf_data = sources.get("pdf_content", [{}])[0]
      chunks = pdf_data.get("chunks", [])

      if not chunks:
        # フォールバック: context_mdから分割
        full_content = ctx.replace("# PDF: ", "").split("\n\n", 1)[-1]
        chunks = full_content.split("\n\n---\n\n")

      # Map: 各チャンクから重要ポイントを抽出（最大3個）
      chunk_points = []
      for i, chunk in enumerate(chunks[:20]):  # 最大20チャンク（LLMコスト削減）
        if not chunk.strip():
          continue

        map_prompt = get_key_points_map_prompt(chunk=chunk, chunk_index=i+1)

        msg = llm.invoke(map_prompt)
        points = _strip_bullets(msg.content.splitlines())[:3]
        chunk_points.extend(points)

      # Reduce: 全ポイントを統合して5つに凝縮
      if chunk_points:
        reduce_prompt = get_key_points_reduce_prompt(chunk_points=chunk_points)

        msg = llm.invoke(reduce_prompt)
        lines = msg.content.splitlines()

        # 前置き行を除外（箇条書き記号または番号で始まる行のみ抽出）
        filtered_lines = [
          line for line in lines
          if line.strip() and (
            line.strip().startswith(('-', '•', '*', '・')) or
            re.match(r'^\d+\.', line.strip())
          )
        ]

        final_bullets = _strip_bullets(filtered_lines)[:5] if filtered_lines else chunk_points[:5]

        # 5個未満の場合はchunk_pointsから補充
        while len(final_bullets) < 5 and chunk_points:
          candidate = chunk_points.pop(0)
          if candidate not in final_bullets:  # 重複回避
            final_bullets.append(candidate)
      else:
        final_bullets = ["内容の抽出に失敗しました"]

      return {
        "key_points": final_bullets,
        "log": _log(state, f"[key_points_map_reduce] chunks={len(chunks)}, extracted={len(chunk_points)}, final={len(final_bullets)}")
      }

    except Exception as e:
      return {"error": f"key_points_pdf_error: {e}", "log": _log(state, f"[key_points_pdf] EXCEPTION {e}")}

  else:
    # AI最新情報の場合は既存のプロンプト
    prompt = get_key_points_ai_prompt(context_md=ctx, topic=topic)

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
    prompt = get_toc_pdf_prompt(key_points=key_points)
  else:
    # AI最新情報の場合は既存のプロンプト
    prompt = get_toc_ai_prompt(key_points=key_points)

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
# Mermaid図解生成ヘルパー関数（Issue #25）
# -------------------
# 以下の関数は廃止（LLMがプロンプトから独自の図を生成するため不要）
# def _generate_architecture_flowchart(key_points: List[str]) -> str:
# def _generate_use_case_mindmap(key_points: List[str]) -> str:


def _insert_after_section(slide_md: str, section_title: str, content: str) -> str:
    """指定セクション直後にコンテンツを挿入（h1/h2/h3対応）"""
    import re

    # "# section_title" または "## section_title" の後の "---" を見つけて挿入
    # contentの先頭と末尾の改行を削除してから、区切りを追加して挿入
    clean_content = content.strip('\n')
    pattern = rf'(#+\s+{re.escape(section_title)}.*?\n---\s*\n)'

    if re.search(pattern, slide_md, re.DOTALL):
        return re.sub(pattern, rf'\1\n{clean_content}\n\n---\n\n', slide_md, count=1, flags=re.DOTALL)
    else:
        # フォールバック: 目次/Agendaの後に挿入
        agenda_pattern = r'(#+\s+(?:目次|Agenda).*?\n---\s*\n)'
        if re.search(agenda_pattern, slide_md, re.DOTALL):
            return re.sub(agenda_pattern, rf'\1\n{clean_content}\n\n---\n\n', slide_md, count=1, flags=re.DOTALL)
        return slide_md


def _insert_before_section(slide_md: str, section_title: str, content: str) -> str:
    """指定セクション直前にコンテンツを挿入（h1/h2/h3対応）"""
    import re

    # contentの先頭と末尾の改行を削除
    clean_content = content.strip('\n')

    # パターン: --- の後に section_title がある箇所
    # マッチグループ1: --- + 改行、グループ2: section_title
    pattern = rf'(---\s*\n\n)(#+\s+{re.escape(section_title)})'

    if re.search(pattern, slide_md):
        # --- と section_title の間に図解を挿入
        return re.sub(pattern, rf'\1{clean_content}\n\n---\n\n\2', slide_md, count=1)
    else:
        # セクションが見つからない場合は末尾に追加
        return slide_md.rstrip('\n') + f'\n\n{clean_content}\n\n---\n\n'

# -------------------
# Node D: スライド本文（Slidev）生成
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
      # ★全チャンクから要約を作成してからスライド生成
      pdf_data = sources.get("pdf_content", [{}])[0]
      chunks = pdf_data.get("chunks", [])

      if not chunks:
        # フォールバック: context_mdから分割
        full_content = context_md.replace("# PDF: ", "").split("\n\n", 1)[-1]
        chunks = full_content.split("\n\n---\n\n")

      # PDFの内容からLLMでタイトルを生成
      title_prompt = get_slide_title_prompt(chunks=chunks, key_points=key_points)

      try:
        title_msg = llm.invoke(title_prompt)
        ja_title = title_msg.content.strip().replace('"', '').replace("'", '')
        # タイトルが長すぎる場合は切り詰め
        if len(ja_title) > 30:
          ja_title = ja_title[:30] + "..."
      except Exception as e:
        # フォールバック: ファイル名から生成
        pdf_filename = Path(topic).stem if topic.endswith('.pdf') else "PDF資料"
        # UUIDを除去
        if '_' in pdf_filename:
          pdf_filename = pdf_filename.split('_', 1)[1] if len(pdf_filename.split('_', 1)) > 1 else pdf_filename
        ja_title = f"{pdf_filename}"

      # チャンクを直接使用（要約なし・コスト削減版）
      chunk_texts = []
      total_chars = 0
      for i, chunk in enumerate(chunks[:20]):
        if not chunk.strip():
          continue

        # 各チャンクの先頭1500文字を使用
        chunk_preview = chunk[:1500]
        chunk_texts.append(f"## セクション{i+1}\n{chunk_preview}")
        total_chars += len(chunk_preview)

        # 合計15,000文字まで使用（スライド生成の上限）
        if total_chars > 15000:
          break

      # 全チャンクテキストを結合
      full_summary = "\n\n".join(chunk_texts)

      # LLMでSlidevマークダウンを生成（チャンク抜粋版を使用）
      prompt = get_slide_pdf_prompt(
        full_summary=full_summary,
        key_points=key_points,
        toc=toc,
        ja_title=ja_title
      )

      msg = llm.invoke(prompt)
      slide_md = msg.content.strip()

      # コードブロックがあれば除去
      slide_md = _strip_whole_code_fence(slide_md)

      return {
        "slide_md": slide_md,
        "title": ja_title,
        "error": "",
        "log": _log(state, f"[slides_slidev_pdf] generated ({len(slide_md)} chars) from {len(chunk_texts)} chunks (cost-optimized, no LLM summary)")
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
# Node D.5: Mermaid図解生成（Issue #25）
# -------------------
@traceable(run_name="d5_generate_diagrams")
# generate_diagrams ノードは廃止（LLMがプロンプトから独自の図を生成するため不要）
# Issue #25: テンプレート図の強制挿入を削除し、LLMによる独自図生成に移行
def generate_diagrams(state: State) -> Dict:
    """[DEPRECATED] このノードは使用されていません"""
    return {"log": _log(state, "[diagrams] deprecated - skipped")}

# -------------------
# Node E: 評価
# -------------------
MAX_ATTEMPTS = 3

# Slidev用評価ノード
@traceable(run_name="e_evaluate_slides_slidev")
def evaluate_slides_slidev(state: State) -> Dict:
  """Slidevスライドの品質評価（PDF/AI情報対応）"""
  if state.get("error"):
    return {}
  slide_md = state.get("slide_md") or ""
  toc = state.get("toc") or []
  topic = state.get("topic") or ""

  # 入力タイプを判別してPDF特有の評価基準を追加
  input_type = detect_input_type(topic)

  # プロンプトを取得（入力タイプで評価基準を切り替え）
  prompt = get_evaluation_prompt(
    slide_md=slide_md,
    toc=toc,
    topic=topic,
    input_type=input_type
  )
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
# Node F: 保存 & Slidevレンダリング
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
  slug_prompt = get_slug_prompt(title=title)

  try:
    emsg = llm.invoke(slug_prompt)
    file_stem = _slugify_en(emsg.content.strip()) or _slugify_en(title)
  except Exception:
    file_stem = _slugify_en(title) or "ai-latest-info"

  # 統一設定からスライドディレクトリを取得
  slide_dir = settings.SLIDES_DIR
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

  # ──────────────────────────────────────────────────────────────────────────
  # Supabase保存（オプショナル、失敗しても継続）
  # Issue #24: ブラウザプレビュー + Supabase履歴管理
  # ──────────────────────────────────────────────────────────────────────────
  result = {
    "slide_path": out_path,
    "log": _log(state, log_msg)
  }

  # 実行コンテキストからuser_idを取得（Read-Only）
  user_id = state.get("user_id", "anonymous")
  topic = state.get("topic", "AI最新情報")

  try:
    # PDFが生成された場合のみパスを渡す
    pdf_path = None
    if slidev and SLIDE_FORMAT == "pdf" and "pdf_file" in locals():
      pdf_path = pdf_file

    supabase_result = save_slide_to_supabase(
      user_id=user_id,
      title=title,
      topic=topic,
      slide_md=slide_md,
      pdf_path=pdf_path
    )

    if "slide_id" in supabase_result:
      result["slide_id"] = supabase_result["slide_id"]
      result["pdf_url"] = supabase_result.get("pdf_url")
      result["log"] = _log(state, f"[supabase] saved slide_id={supabase_result['slide_id']}")
    elif "error" in supabase_result:
      # Supabase未設定の場合もここに入る（警告のみ、継続）
      result["log"] = _log(state, f"[supabase] {supabase_result['error']}")

  except Exception as e:
    # Supabase保存失敗してもワークフローは継続（クリティカルエラーではない）
    result["log"] = _log(state, f"[supabase] save failed (non-critical): {str(e)[:100]}")

  return result

# -------------------
# グラフ構築
# -------------------
graph_builder = StateGraph(State)
graph_builder.add_node("collect_info", collect_info)
graph_builder.add_node("generate_key_points", generate_key_points)
graph_builder.add_node("generate_toc", generate_toc)
graph_builder.add_node("write_slides_slidev", write_slides_slidev)
graph_builder.add_node("generate_diagrams", generate_diagrams)
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