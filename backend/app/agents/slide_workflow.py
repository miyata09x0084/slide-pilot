# LangGraph × LangSmith × OpenAI × Tavily × Slidev
# スライド生成ワークフロー（PDF/YouTube/テキスト対応）
# フロー: 情報収集 -> キーポイント抽出 -> 目次生成 -> スライド生成 -> 評価 -> 保存

# 標準ライブラリ
import os
import re
import json
import shutil
import subprocess
import tempfile
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
from app.core.config import TAVILY_API_KEY
from app.core.llm import llm
from app.core.supabase import save_slide_to_supabase
from app.core.storage import upload_to_storage
from app.core.utils import (
    _log,
    _strip_bullets,
    _slugify_en,
    _find_json,
    _insert_separators,
    _double_separators,
    _strip_whole_code_fence,
    _format_conversation,
    JST,
    now_jst,
    month_ja,
    _get_all_vendors_info,
    _create_llm_summarized_bullets,
    _generate_multi_vendor_slides_integrated,
    tavily_search,
    tavily_collect_context,
    context_to_bullets,
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
  # 動画生成 (Node G-H) - Video Narration Feature
  # ══════════════════════════════════════════════════════════
  slides_json: List[Dict[str, Any]]             # スライドデータ（HTML生成用）
  narration_scripts: List[str]                  # ナレーション台本
  audio_files: List[str]                        # 音声ファイルパス
  video_url: str                                # Supabase動画URL（同期版で使用）
  video_job_id: str                             # Cloud Run Job ID（非同期版で使用）
  _temp_narration_dir: str                      # 一時ディレクトリ（内部用）

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
# タイトル抽出ヘルパー関数
# =======================
def extract_clean_title(raw_title: str, fallback: str = "資料") -> str:
    """LLMレスポンスからタイトルを抽出（説明文・記号除去）

    Args:
        raw_title: LLMの生のレスポンス
        fallback: 抽出失敗時のフォールバックタイトル

    Returns:
        クリーンなタイトル（15文字以内）
    """
    if not raw_title or not raw_title.strip():
        return fallback

    # 説明文パターンを除去（「タイトル:」「このPDFは」等）
    cleaned = re.sub(r'^(?:タイトル[:：]|このPDFは|本資料は|内容[:：])\s*', '', raw_title.strip())

    # 引用符・改行を除去
    cleaned = cleaned.replace('"', '').replace("'", '').replace('\n', ' ').strip()

    # 複数行の場合は最初の行のみ使用
    if '\n' in cleaned:
        cleaned = cleaned.split('\n')[0].strip()

    # 15文字制限
    if len(cleaned) > 15:
        cleaned = cleaned[:15]

    # 最終検証: 空または短すぎる場合はフォールバック
    if not cleaned or len(cleaned) < 3:
        return fallback

    return cleaned

# =======================
# Node A: 情報収集（PDF/YouTube/Tavily対応）
# =======================
@traceable(run_name="a_collect_info")
def collect_info(state: State) -> State:
  topic = state.get("topic", "AI最新情報")
  if not topic or not topic.strip():
    topic = "AI最新情報"

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
  topic = state.get("topic", "AI最新情報")
  if not topic or not topic.strip():
    topic = "AI最新情報"
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
      # 並列処理で高速化（llm.batch使用）
      valid_chunks = [(i+1, chunk) for i, chunk in enumerate(chunks[:20]) if chunk.strip()]

      if not valid_chunks:
        return {"error": "No valid chunks to process", "log": _log(state, "[key_points_map] no valid chunks")}

      # バッチプロンプト生成
      batch_prompts = [
        get_key_points_map_prompt(chunk=chunk, chunk_index=idx)
        for idx, chunk in valid_chunks
      ]

      # 並列実行（最大5並列）
      responses = llm.batch(batch_prompts, config={"max_concurrency": 5})

      # 結果を統合
      chunk_points = []
      for msg in responses:
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
  topic = state.get("topic", "AI最新情報")
  if not topic or not topic.strip():
    topic = "AI最新情報"
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
  topic = state.get("topic", "AI最新情報")
  if not topic or not topic.strip():
    topic = "AI最新情報"
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

      # PDFファイル名からフォールバックタイトルを準備
      if topic.endswith('.pdf') or '/uploads/' in topic:
          pdf_filename = Path(topic).name.replace('.pdf', '')
          # UUID部分を除去（パターン: uuid_filename）
          if '_' in pdf_filename:
              parts = pdf_filename.split('_', 1)
              if len(parts) > 1 and len(parts[0]) > 30:  # UUIDっぽい長い文字列
                  pdf_filename = parts[1]
          fallback_title = pdf_filename[:15] if pdf_filename else "PDF資料"
      else:
          fallback_title = "資料"

      # PDFの内容からLLMでタイトルを生成
      title_prompt = get_slide_title_prompt(chunks=chunks, key_points=key_points)

      try:
        title_msg = llm.invoke(title_prompt)
        raw_title = title_msg.content.strip()
        ja_title = extract_clean_title(raw_title, fallback=fallback_title)
      except Exception as e:
        ja_title = fallback_title
        # エラーログ追加
        print(f"[slide_workflow] タイトル生成エラー (fallback使用): {str(e)[:100]}")

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
      raw_content = msg.content.strip()

      # ═══════════════════════════════════════════════════════════
      # 構造制御（Python側で機械的に実施）
      # 設計方針: docs/architecture/SLIDE_GENERATION_DESIGN.md
      # ═══════════════════════════════════════════════════════════

      # Step 1: コードブロック除去（既存）
      raw_content = _strip_whole_code_fence(raw_content)

      # Step 2: 既存のフロントマター削除（LLMが勝手に生成した場合の保険）
      raw_content = re.sub(r'^---[\s\S]*?---\s*', '', raw_content.strip(), count=1)

      # Step 3: YAMLフロントマター生成（Python側で制御）
      frontmatter = """---
theme: apple-basic
highlighter: shiki
class: text-center
---

"""

      # Step 4: 見出し（## ）前に `---` を機械的に挿入
      content_with_separators = _insert_separators(raw_content)

      # Step 4.5: 会話形式に改行を挿入（LLM出力の揺らぎに対応）
      content_with_separators = _format_conversation(content_with_separators)

      # Step 5: 連続した --- を圧縮（安全装置）
      content_with_separators = _double_separators(content_with_separators)

      # Step 6: 最終的なMarkdown生成
      slide_md = frontmatter + content_with_separators

      return {
        "slide_md": slide_md,
        "title": ja_title,
        "error": "",
        "log": _log(state, f"[slides_slidev_pdf] generated ({len(slide_md)} chars) from {len(chunk_texts)} chunks with mechanical structure control")
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
  topic = state.get("topic", "AI最新情報")
  if not topic or not topic.strip():
    topic = "AI最新情報"

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
  """Slidev形式のスライドを保存（PDF生成廃止、MD保存のみ）"""
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

  # ──────────────────────────────────────────────────────────────────────────
  # Supabase Storage & DB保存（オプショナル、失敗しても継続）
  # PDF生成廃止: MD保存のみ（ブロッキング処理回避）
  # ──────────────────────────────────────────────────────────────────────────

  user_id = state.get("user_id", "anonymous")
  topic = state.get("topic", "AI最新情報")
  md_url = None
  log_msg = ""

  try:
    # Markdownファイルをアップロード
    md_storage_path = f"{user_id}/{file_stem}_slidev.md"
    md_url = upload_to_storage(
      bucket="slide-files",
      file_path=md_storage_path,
      file_data=slide_md.encode("utf-8"),
      content_type="text/markdown"
    )
    log_msg = f"[save_slidev] MD uploaded to {md_url}"

  except Exception as e:
    log_msg = f"[save_slidev] Storage upload failed: {str(e)}"

  # Supabase DBにメタデータ保存
  result = {
    "slide_path": md_url,
    "md_url": md_url,
    "log": _log(state, log_msg)
  }

  try:
    supabase_result = save_slide_to_supabase(
      user_id=user_id,
      title=title,
      topic=topic,
      slide_md=slide_md,
      pdf_url=None  # PDF廃止
    )

    if "slide_id" in supabase_result:
      result["slide_id"] = supabase_result["slide_id"]
      result["log"] = _log(state, f"[supabase] saved slide_id={supabase_result['slide_id']}")
    elif "error" in supabase_result:
      result["log"] = _log(state, f"[supabase] {supabase_result['error']}")

  except Exception as e:
    result["log"] = _log(state, f"[supabase] save failed (non-critical): {str(e)[:100]}")

  return result

# -------------------
# Node G: ナレーション生成（OpenAI TTS）
# -------------------
def _parse_slide_to_json(slide_content: str, index: int) -> Dict[str, Any]:
    """
    スライドマークダウンを構造化JSONに変換

    Args:
        slide_content: スライドのマークダウン内容
        index: スライド番号（0始まり）

    Returns:
        スライドの構造化データ
    """
    import re

    lines = [l for l in slide_content.strip().split("\n") if l.strip()]
    if not lines:
        return {"type": "content", "heading": f"スライド {index + 1}", "bullets": []}

    # タイトルスライド判定（# で始まり、箇条書きがない）
    if lines[0].startswith("# ") and not any(l.strip().startswith("-") for l in lines):
        title = lines[0].lstrip("# ").strip()
        subtitle = ""
        for l in lines[1:]:
            if l.strip() and not l.startswith("#"):
                subtitle = l.strip()
                break
        return {"type": "title", "title": title, "subtitle": subtitle}

    content_str = "\n".join(lines)

    # mermaid図判定（```mermaid が含まれる）
    if "```mermaid" in content_str:
        heading = ""
        mermaid_code = ""

        # mermaidコードを抽出
        mermaid_match = re.search(r'```mermaid\n(.*?)\n```', content_str, re.DOTALL)
        if mermaid_match:
            mermaid_code = mermaid_match.group(1).strip()

        # 見出しを抽出
        for l in lines:
            if l.startswith("## "):
                heading = l.lstrip("## ").strip()
                break
            elif l.startswith("# "):
                heading = l.lstrip("# ").strip()
                break

        if mermaid_code:
            return {
                "type": "mermaid",
                "heading": heading or "図解",
                "mermaid_code": mermaid_code
            }

    # 会話形式判定（👨‍🏫 または 先生: が含まれる）
    if "👨‍🏫" in content_str or "先生:" in content_str or "🧑‍🎓" in content_str:
        heading = ""
        teacher = ""
        student = ""

        for l in lines:
            if l.startswith("## "):
                heading = l.lstrip("## ").strip()
            elif "👨‍🏫" in l or "先生:" in l:
                teacher = re.sub(r"^[-*]\s*", "", l)
                teacher = re.sub(r"(👨‍🏫|先生:?)\s*", "", teacher).strip()
            elif "🧑‍🎓" in l or "生徒:" in l:
                student = re.sub(r"^[-*]\s*", "", l)
                student = re.sub(r"(🧑‍🎓|生徒:?)\s*", "", student).strip()

        if teacher or student:
            return {
                "type": "conversation",
                "heading": heading or "会話",
                "teacher": teacher,
                "student": student
            }

    # まとめスライド判定
    if any(keyword in content_str for keyword in ["まとめ", "ポイント", "要点", "Summary"]):
        heading = ""
        points = []
        for l in lines:
            if l.startswith("## "):
                heading = l.lstrip("## ").strip()
            elif l.strip().startswith("-") or l.strip().startswith("*"):
                point = re.sub(r"^[-*]\s*", "", l.strip())
                if point:
                    points.append(point)

        if points:
            return {
                "type": "summary",
                "heading": heading or "まとめ",
                "points": points
            }

    # デフォルト: コンテンツスライド（見出し + 箇条書き）
    heading = ""
    bullets = []
    for l in lines:
        if l.startswith("## "):
            heading = l.lstrip("## ").strip()
        elif l.startswith("# "):
            heading = l.lstrip("# ").strip()
        elif l.strip().startswith("-") or l.strip().startswith("*"):
            bullet = re.sub(r"^[-*]\s*", "", l.strip())
            if bullet:
                bullets.append(bullet)
        elif l.strip() and not heading:
            # 見出しがまだない場合、最初の非空行を見出しに
            heading = l.strip()

    return {
        "type": "content",
        "heading": heading or f"スライド {index + 1}",
        "bullets": bullets
    }


@traceable(run_name="g_generate_narration")
def generate_narration(state: State) -> Dict:
    """各スライドのナレーション音声を生成（OpenAI TTS）+ slides_json生成

    並列処理:
    - LLMナレーション生成: llm.batch() で最大5並列
    - TTS音声生成: ThreadPoolExecutor で最大5並列
    """
    from openai import OpenAI
    from concurrent.futures import ThreadPoolExecutor
    from app.prompts.narration_prompts import get_narration_prompt

    if state.get("error"):
        return {}

    slide_md = state.get("slide_md", "")
    title = state.get("title", "AIスライド")

    # Slidevのスライド区切り（---）で分割
    slides = slide_md.split("\n---\n")

    # frontmatter（最初のYAML部分）をスキップ
    slide_contents = []
    slides_json = []

    for idx, slide in enumerate(slides[1:]):  # slides[0]はfrontmatter
        # 空白・コメント行を除去
        content = "\n".join([
            line for line in slide.split("\n")
            if line.strip() and not line.strip().startswith("<!--")
        ])
        if content.strip():
            slide_contents.append(content)
            # スライドをJSON形式に変換
            slide_data = _parse_slide_to_json(content, idx)
            slides_json.append(slide_data)

    if not slide_contents:
        return {
            "error": "No slide content found for narration",
            "log": _log(state, "[narration] ERROR: no valid slides")
        }

    # OpenAI TTSクライアント初期化
    client = OpenAI()  # OPENAI_API_KEYから自動認証

    # 設定値取得
    tts_model = getattr(settings, 'TTS_MODEL', 'tts-1-hd')
    tts_voice = getattr(settings, 'TTS_VOICE', 'shimmer')
    tts_speed = float(getattr(settings, 'TTS_SPEED', '1.0'))

    # 一時ディレクトリ作成
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # ========== Step 1: LLMナレーション生成（並列処理） ==========
        batch_prompts = [
            get_narration_prompt(slide_content=content)
            for content in slide_contents
        ]

        # 並列LLM実行（最大5並列）
        responses = llm.batch(batch_prompts, config={"max_concurrency": 5})

        # 結果を整形
        narrations = []
        for i, msg in enumerate(responses):
            try:
                narration_text = msg.content.strip().strip('"').strip("'")
                narrations.append(narration_text)
            except Exception as e:
                # LLMエラー時はフォールバック
                narrations.append(f"{i+1}枚目のスライドです。")
                print(f"[narration] LLM parse error for slide {i}: {str(e)[:100]}")

        # ========== Step 2: TTS音声生成（並列処理） ==========
        def generate_audio(args):
            """単一スライドの音声生成（スレッドプール用）"""
            idx, narration_text = args
            response = client.audio.speech.create(
                model=tts_model,
                voice=tts_voice,
                input=narration_text,
                speed=tts_speed
            )
            audio_path = temp_dir / f"narration_{idx:03d}.mp3"
            with open(audio_path, 'wb') as f:
                f.write(response.content)
            return idx, str(audio_path)

        # 並列TTS実行（最大5並列）
        audio_results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(generate_audio, (i, narration))
                for i, narration in enumerate(narrations)
            ]
            for future in futures:
                try:
                    result = future.result()
                    audio_results.append(result)
                except Exception as e:
                    # TTS失敗時は即座にエラー返却
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return {
                        "error": f"OpenAI TTS error: {str(e)}",
                        "log": _log(state, f"[narration] TTS API failed: {str(e)[:100]}")
                    }

        # 順序を維持してソート（インデックス順）
        audio_results.sort(key=lambda x: x[0])
        audio_files = [path for _, path in audio_results]

        return {
            "narration_scripts": narrations,
            "audio_files": audio_files,
            "slides_json": slides_json,  # HTML生成用の構造化データ
            "_temp_narration_dir": str(temp_dir),  # 後続ノードで使用
            "log": _log(state, f"[narration] generated {len(audio_files)} audio files, {len(slides_json)} slides_json (model={tts_model}, voice={tts_voice}, parallel=5)")
        }

    except Exception as e:
        # クリーンアップ
        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            "error": f"narration_error: {str(e)}",
            "log": _log(state, f"[narration] EXCEPTION {str(e)[:100]}")
        }

# -------------------
# Node H: 動画レンダリング（Cloud Run Job 非同期版）
# Cloud Run Jobをトリガーし、job_idを返す。実際の動画生成はバックグラウンドで実行。
# -------------------
@traceable(run_name="h_render_video")
def render_video(state: State) -> Dict:
    """PNG画像 + 音声 → MP4動画生成（Cloud Run Job 非同期版）

    Cloud Run Jobをトリガーし、video_job_idを返す。
    実際の動画生成はバックグラウンドで実行され、タイムアウトしない。
    クライアントは /api/video/status/{job_id} でステータスをポーリングする。

    重要: 音声ファイルはSupabase Storageにアップロードしてから渡す。
    ローカルの一時ファイルパスは非同期ジョブ実行時に存在しないため。
    """
    import httpx
    import os
    from pathlib import Path
    from app.core.storage import upload_to_storage

    print("[DEBUG] render_video: START (Cloud Run Job async)")

    if state.get("error"):
        print("[DEBUG] render_video: error in state, returning early")
        return {}

    audio_files = state.get("audio_files", [])
    slides_json = state.get("slides_json", [])
    temp_narration_dir = state.get("_temp_narration_dir")
    title = state.get("title", "AIスライド")
    user_id = state.get("user_id", "anonymous")
    slide_id = state.get("slide_id", "")

    print(f"[DEBUG] render_video: audio_files={len(audio_files)}, slides_json={len(slides_json)}")

    if not audio_files:
        print("[DEBUG] render_video: no audio files")
        return {
            "error": "No audio files for video rendering",
            "log": _log(state, "[video] ERROR: no audio files")
        }

    if not slides_json:
        print("[DEBUG] render_video: no slides_json")
        return {
            "error": "No slides_json for video rendering",
            "log": _log(state, "[video] ERROR: no slides_json data")
        }

    if not slide_id:
        print("[DEBUG] render_video: no slide_id (required for async)")
        return {
            "error": "No slide_id for async video rendering",
            "log": _log(state, "[video] ERROR: slide_id is required for async rendering")
        }

    # 音声ファイルをSupabase Storageにアップロード
    # 非同期ジョブはローカルの一時ファイルにアクセスできないため
    print("[DEBUG] render_video: uploading audio files to Supabase Storage")
    audio_urls = []
    try:
        for i, audio_path in enumerate(audio_files):
            audio_file = Path(audio_path)
            if not audio_file.exists():
                print(f"[DEBUG] render_video: audio file not found: {audio_path}")
                return {
                    "error": f"Audio file not found: {audio_path}",
                    "log": _log(state, f"[video] ERROR: audio file not found: {audio_path}")
                }

            # Supabase Storageにアップロード
            storage_path = f"{user_id}/narration/{slide_id}/narration_{i:03d}.mp3"
            audio_url = upload_to_storage(
                bucket="slide-files",
                file_path=storage_path,
                file_data=audio_file.read_bytes(),
                content_type="audio/mpeg"
            )
            audio_urls.append(audio_url)
            print(f"[DEBUG] render_video: uploaded audio {i} -> {audio_url}")

        print(f"[DEBUG] render_video: uploaded {len(audio_urls)} audio files")
    except Exception as e:
        print(f"[DEBUG] render_video: audio upload failed: {e}")
        return {
            "error": f"Audio upload failed: {str(e)}",
            "log": _log(state, f"[video] ERROR: audio upload failed: {str(e)[:100]}")
        }

    # FastAPI経由で非同期動画生成ジョブをトリガー
    fastapi_url = os.getenv("FASTAPI_URL", "http://localhost:8001")
    print(f"[DEBUG] render_video: calling FastAPI at {fastapi_url}/api/render/video/async")

    try:
        with httpx.Client(timeout=30) as client:  # ジョブ作成は30秒で十分
            response = client.post(
                f"{fastapi_url}/api/render/video/async",
                json={
                    "slides_json": slides_json,
                    "audio_files": audio_urls,  # ローカルパスではなくSupabase URLを渡す
                    "title": title,
                    "user_id": user_id,
                    "slide_id": slide_id
                }
            )
            response.raise_for_status()
            result = response.json()

        job_id = result.get("job_id", "")
        print(f"[DEBUG] render_video: async job created, job_id={job_id}")

        # ナレーション用一時ディレクトリのクリーンアップ
        if temp_narration_dir:
            shutil.rmtree(temp_narration_dir, ignore_errors=True)

        return {
            "video_job_id": job_id,
            "log": _log(state, f"[video] async job created: {job_id}")
        }

    except httpx.TimeoutException:
        print("[DEBUG] render_video: TIMEOUT creating job")
        return {
            "error": "Video job creation timeout",
            "log": _log(state, "[video] TIMEOUT creating async job")
        }
    except httpx.HTTPStatusError as e:
        print(f"[DEBUG] render_video: HTTP error {e.response.status_code}")
        return {
            "error": f"video_job_error: HTTP {e.response.status_code}",
            "log": _log(state, f"[video] FastAPI error: {e.response.text[:100]}")
        }
    except Exception as e:
        print(f"[DEBUG] render_video: ERROR {e}")
        return {
            "error": f"video_job_error: {str(e)}",
            "log": _log(state, f"[video] ERROR: {str(e)[:100]}")
        }


# -------------------
# 条件分岐: 動画生成
# -------------------
def route_after_save(state: State) -> str:
    """保存後の分岐: 常に動画生成へ"""
    # エラーがある場合はスキップ
    if state.get("error"):
        return END

    # 常に動画生成へ
    return "generate_narration"

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
graph_builder.add_node("generate_narration", generate_narration)
graph_builder.add_node("render_video", render_video)

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

# 動画生成フロー（条件分岐）
graph_builder.add_conditional_edges(
    "save_and_render_slidev",
    route_after_save,
    {"generate_narration": "generate_narration", END: END}
)

# 動画生成エッジ
graph_builder.add_edge("generate_narration", "render_video")
graph_builder.add_edge("render_video", END)

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