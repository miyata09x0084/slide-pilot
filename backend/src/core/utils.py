"""共通ユーティリティ関数

含まれる機能:
- テキスト処理（slugify, JSON抽出, 箇条書き整形など）
- Marp/Slidev用Markdown整形関数
- 日時処理（JST対応）
- Slidev生成ロジック（マルチベンダー対応）
- Tavily検索API呼び出し
"""

from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any, Union, List
import os
import re
import requests
from datetime import datetime
from langchain_core.tools import tool
import json
from pathlib import Path
import shutil
import subprocess

from src.core.config import TAVILY_API_KEY, SLIDE_FORMAT, MARP_THEME, MARP_PAGINATE
from src.core.llm import llm

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

  # LLMで箇条書きに要約（Phase 2 - MVP-1: プロンプト最適化）
  prompt = [
    ("system", "あなたはAI技術のエキスパートです。検索結果から重要なポイントを抽出し、Slidevスライド向けに視覚的に魅力的な箇条書きを作成します。"),
    ("user",
     f"以下の{vendor_name}に関する検索結果から、重要なポイントを{num_bullets}つの箇条書きで簡潔にまとめてください。\n\n"
     f"【フォーマット要件】\n"
     f"- 各箇条書きは **太字** で技術用語を強調\n"
     f"- バージョン番号や数値などの具体的情報を含める\n"
     f"- **必ず日付を含める**（例: 2024年10月、10月1日など）\n"
     f"- 1行は40-60文字程度に収める\n"
     f"- 適切な絵文字を先頭に付ける（🚀 💡 ⚡ 🎯 📊 🔧 など）\n\n"
     f"【検索結果】\n{results_text}\n\n"
     f"【出力形式】\n" + "\n".join([f"- 絵文字 **キーワード** (日付): 説明文" for i in range(num_bullets)]))
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
    # sourcesから該当するベンダーの検索結果を抽出（Phase 2 - Bug Fix: URL-based domain matching）
    vendor_results = []
    seen_urls = set()

    for query, items in sources.items():
      # 各検索結果のURLがベンダーのドメインに含まれているか確認
      for item in items:
        url = item.get("url", "")
        if not url or url in seen_urls:
          continue

        # URLがベンダーのドメインのいずれかに含まれているか確認
        for domain in vendor["domains"]:
          if domain in url:
            vendor_results.append(item)
            seen_urls.add(url)
            break

    # LLMで箇条書きに要約
    bullets = _create_llm_summarized_bullets(vendor_results[:5], vendor["name"], num_bullets=3)

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

  # まとめスライド（Phase 2 - MVP-2: まとめスライド強化）
  slide_content += f"""---
layout: center
class: text-center
---

# ✨ 本日のまとめ

<div class="mt-8">

<v-clicks>

## 🔑 キーポイント

"""

  # 各ベンダーの最重要ポイントを1行ずつ表示
  for vb in vendor_bullets:
    first_bullet = vb['bullets'][0] if vb['bullets'] else "- 情報なし"
    # 日付や絵文字を除去してコンパクトに
    clean_bullet = first_bullet.lstrip('- ').split(':', 1)[-1].strip() if ':' in first_bullet else first_bullet.lstrip('- ')
    slide_content += f"- {vb['emoji']} **{vb['name']}**: {clean_bullet[:50]}...\n"

  slide_content += f"""
</v-clicks>

</div>

<div class="mt-12">
  <span class="px-4 py-2 rounded" style="background: #6366f1; color: white; font-weight: 600;">
    📚 詳細は各セクションをご確認ください
  </span>
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
  slide_dir = Path(__file__).parent.parent.parent / "data" / "slides"
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
