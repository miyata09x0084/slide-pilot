"""Slidev動的生成ツール - MVP-1/2統合版（Tavily検索 + オプショナルLLM統合）

Tavily検索結果を箇条書きに変換してSlidevスライドに埋め込む。
use_llm=Trueでオプショナルなし、LLMで検索結果を要約できる。

Phase 0.5 - MVP-1: Tavily検索結果を直接箇条書き化
Phase 0.5 - MVP-2: LLMで検索結果を5つの箇条書きに要約
"""

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from typing import Optional, Dict, List
import json
from pathlib import Path
import subprocess
import shutil
import os
import requests
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# APIキー
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("missing environment variable: TAVILY_API_KEY")

# LLMクライアント（MVP-2用）
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
    max_retries=2,
)


def _slugify_en(text: str, max_length: int = 80) -> str:
    """英数字のみのスラッグ生成（marp_agent.pyから複製）"""
    import re
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_length] or "slide"


def _tavily_search(
    query: str,
    max_results: int = 8,
    include_domains: Optional[List[str]] = None,
    time_range: str = "month",
) -> Dict:
    """Tavily検索APIを呼び出す"""
    endpoint = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "include_answers": True,
        "max_results": max_results,
        "time_range": time_range,
    }
    if include_domains:
        payload["include_domains"] = include_domains
    r = requests.post(endpoint, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def _create_simple_bullets(results: List[Dict]) -> List[str]:
    """検索結果からシンプルな箇条書きを生成（MVP-1: LLMなし）"""
    bullets = []
    for result in results[:3]:
        title = result.get("title", "")[:100]
        url = result.get("url", "")
        if title and url:
            bullets.append(f"- **{title}**\n  - [{url}]({url})")

    if not bullets:
        bullets = [
            "- **検索結果が見つかりませんでした**",
            "- 後でもう一度お試しください"
        ]

    return bullets


def _create_llm_summarized_bullets(results: List[Dict], vendor_name: str = "Microsoft AI", num_bullets: int = 5) -> List[str]:
    """検索結果をLLMで要約して箇条書きを生成（MVP-2/3: LLM統合）

    Args:
        results: 検索結果のリスト
        vendor_name: ベンダー名（デフォルト: "Microsoft AI"）
        num_bullets: 生成する箇条書きの数（デフォルト: 5）
    """
    # 検索結果をテキストに整形
    results_text = ""
    for i, result in enumerate(results[:3], 1):
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
        return _create_simple_bullets(results)


def _get_all_vendors_info() -> List[Dict]:
    """全6社のベンダー情報を返す（MVP-3用）"""
    return [
        {
            "name": "Microsoft AI",
            "emoji": "🏢",
            "domains": ["azure.microsoft.com", "news.microsoft.com", "learn.microsoft.com"],
            "query": "Microsoft AI updates Azure OpenAI",
            "gradient": "linear-gradient(135deg, #0078d4 0%, #00bcf2 100%)",
        },
        {
            "name": "OpenAI",
            "emoji": "🤖",
            "domains": ["openai.com"],
            "query": "OpenAI announcements updates",
            "gradient": "linear-gradient(135deg, #10a37f 0%, #1a7f64 100%)",
        },
        {
            "name": "Google Gemini",
            "emoji": "🌟",
            "domains": ["blog.google", "ai.googleblog.com", "research.google"],
            "query": "Google AI Gemini updates",
            "gradient": "linear-gradient(135deg, #4285f4 0%, #34a853 100%)",
        },
        {
            "name": "AWS Bedrock",
            "emoji": "☁️",
            "domains": ["aws.amazon.com"],
            "query": "AWS Bedrock AI updates",
            "gradient": "linear-gradient(135deg, #ff9900 0%, #f90 100%)",
        },
        {
            "name": "Meta AI",
            "emoji": "🦙",
            "domains": ["ai.meta.com"],
            "query": "Meta AI Llama updates",
            "gradient": "linear-gradient(135deg, #0668e1 0%, #0a7cff 100%)",
        },
        {
            "name": "Anthropic",
            "emoji": "🧠",
            "domains": ["anthropic.com"],
            "query": "Anthropic Claude updates",
            "gradient": "linear-gradient(135deg, #d4a574 0%, #c49a6c 100%)",
        },
    ]


def _fetch_multi_vendor_bullets(vendors: List[Dict], num_bullets_per_vendor: int = 3) -> tuple[List[Dict], int]:
    """複数ベンダーの検索結果を取得して箇条書きを生成（MVP-3用）

    Args:
        vendors: ベンダー情報のリスト
        num_bullets_per_vendor: 各ベンダーあたりの箇条書き数

    Returns:
        (vendor_bullets, total_results): ベンダーごとの箇条書き情報と総検索結果数
    """
    vendor_bullets = []
    total_results = 0

    for vendor in vendors:
        search_results = _tavily_search(
            query=vendor["query"],
            max_results=3,
            include_domains=vendor["domains"],
            time_range="month"
        )

        results = search_results.get("results", [])
        total_results += len(results)

        # LLMで箇条書きに要約
        bullets = _create_llm_summarized_bullets(results, vendor["name"], num_bullets=num_bullets_per_vendor)

        vendor_bullets.append({
            "name": vendor["name"],
            "emoji": vendor["emoji"],
            "bullets": bullets,
            "gradient": vendor["gradient"],
        })

    return vendor_bullets, total_results


def _generate_single_vendor_slides(topic: str, bullets: List[str], mvp_version: str) -> str:
    """単一ベンダー用のSlidevマークダウンを生成（Microsoft AIのみ）"""
    return f"""---
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
  <span class="px-2 py-1 rounded" style="background: #0078d4; color: white;">
    Microsoft AI Latest Updates
  </span>
</div>

---
layout: intro
class: text-left
---

## 📋 Agenda

<v-clicks>

- 🏢 **Microsoft AI** - 最新情報（直近1ヶ月）
- 💡 **まとめ** - 今後の展望

</v-clicks>

---
layout: two-cols
class: px-2
---

## 🏢 Microsoft AI 最新情報

<v-clicks>

{chr(10).join(bullets)}

</v-clicks>

::right::

<div class="flex items-center justify-center h-full">
  <div style="width: 300px; height: 200px; background: linear-gradient(135deg, #0078d4 0%, #00bcf2 100%); border-radius: 12px; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; font-weight: bold; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
    Azure AI
  </div>
</div>

---
layout: end
class: text-center
---

# ✨ まとめ

<div class="mt-8">

## 完了 🎉

AI最新情報をSlidevスライドに統合しました

</div>

<div style="position: absolute; bottom: 1.5rem; right: 1.5rem; font-size: 0.875rem; opacity: 0.5;">
  Generated by SlidePilot AI ({mvp_version})
</div>

"""


def _generate_multi_vendor_slides(topic: str, vendor_bullets: List[Dict], mvp_version: str) -> str:
    """複数ベンダー用のSlidevマークダウンを生成（全6社対応）"""
    # ヘッダー
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
    AI Industry Report 2025
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


@tool
def generate_slidev_mvp1(topic: str = "AI最新情報", use_llm: bool = True, multi_vendor: bool = True) -> str:
    """Slidev動的スライド生成 - MVP-1/2/3統合版

    Tavily検索でAI最新情報を取得し、Slidevスライドを生成する。
    デフォルトで全6社対応のAI Industry Reportを生成。

    処理フロー:
    1a. multi_vendor=True: 全6社（Microsoft, OpenAI, Google, AWS, Meta, Anthropic）検索（デフォルト）
    1b. multi_vendor=False: Microsoft AI のみ検索
    2a. use_llm=True: LLMで箇条書きに要約（デフォルト）
    2b. use_llm=False: タイトル+URLの箇条書き（フォールバック用）
    3. Slidevテンプレートに埋め込み
    4. PDF生成（slidev export コマンド）

    Args:
        topic: スライドのトピック（デフォルト: "AI最新情報"）
        use_llm: LLMで検索結果を要約するかどうか（デフォルト: True）
        multi_vendor: 全6社対応するかどうか（デフォルト: True）

    Returns:
        str: 生成されたスライドのパスと結果情報（JSON形式）
    """

    try:
        if multi_vendor:
            # 全6社対応
            vendors = _get_all_vendors_info()
            vendor_bullets, total_results = _fetch_multi_vendor_bullets(vendors, num_bullets_per_vendor=3)
            mvp_version = "AI Industry Report（全6社）"
            file_suffix = "dynamic_multi"
        else:
            # Microsoft AIのみ
            # 1. Tavily検索（Microsoft AI関連のみ、3件）
            search_results = _tavily_search(
                query="Microsoft AI updates Azure OpenAI",
                max_results=3,
                include_domains=["azure.microsoft.com", "news.microsoft.com", "learn.microsoft.com"],
                time_range="month"
            )

            results = search_results.get("results", [])
            total_results = len(results)

            # 2. 検索結果を箇条書きに変換
            if use_llm:
                bullets = _create_llm_summarized_bullets(results)
                mvp_version = "Microsoft AI Report"
            else:
                bullets = _create_simple_bullets(results)
                mvp_version = "Microsoft AI Report（簡易版）"

            file_suffix = "dynamic_single"

        # 3. Slidevマークダウン生成
        if multi_vendor:
            slide_content = _generate_multi_vendor_slides(topic, vendor_bullets, mvp_version)
        else:
            slide_content = _generate_single_vendor_slides(topic, bullets, mvp_version)

        # 4. ファイル保存
        slide_dir = Path(__file__).parent.parent / "slides"
        slide_dir.mkdir(parents=True, exist_ok=True)

        # ファイル名生成
        slug = _slugify_en(topic) or file_suffix
        md_path = slide_dir / f"{slug}_slidev_{file_suffix}.md"
        md_path.write_text(slide_content, encoding="utf-8")

        # 5. Slidev PDF出力
        pdf_path = slide_dir / f"{slug}_slidev_{file_suffix}.pdf"

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

                # 絶対パスから相対パスに変換
                relative_path = str(pdf_path.relative_to(slide_dir.parent))

                result_data = {
                    "status": "success",
                    "message": f"✅ Slidev {mvp_version}スライドを生成しました: {pdf_path.name}",
                    "title": topic,
                    "slide_path": relative_path,
                    "results_count": total_results
                }

                if multi_vendor:
                    result_data["vendors"] = len(_get_all_vendors_info())

                return json.dumps(result_data, ensure_ascii=False)

            except subprocess.TimeoutExpired:
                relative_path = str(md_path.relative_to(slide_dir.parent))
                return json.dumps({
                    "status": "error",
                    "message": "⚠️ PDF生成がタイムアウトしました（90秒超過）",
                    "title": topic,
                    "slide_path": relative_path,
                    "error": "Playwright初回インストール中の可能性があります。もう一度お試しください。"
                }, ensure_ascii=False)

            except subprocess.CalledProcessError as e:
                # PDF生成失敗時はMDのみ返す
                error_msg = e.stderr.decode() if e.stderr else str(e)
                relative_path = str(md_path.relative_to(slide_dir.parent))
                return json.dumps({
                    "status": "partial",
                    "message": "⚠️ PDF生成に失敗しました。Markdownのみ保存しました。",
                    "title": topic,
                    "slide_path": relative_path,
                    "error": f"詳細: {error_msg}"
                }, ensure_ascii=False)
        else:
            # slidev未インストール時
            relative_path = str(md_path.relative_to(slide_dir.parent))
            return json.dumps({
                "status": "md_only",
                "message": "⚠️ slidevが見つかりません。Markdownのみ保存しました。",
                "title": topic,
                "slide_path": relative_path,
                "error": "slidevをインストールしてください: npm install -g @slidev/cli"
            }, ensure_ascii=False)

    except Exception as e:
        # 予期しないエラー
        return json.dumps({
            "status": "error",
            "message": f"❌ スライド生成例外: {str(e)}",
            "title": topic
        }, ensure_ascii=False)
