"""Slidevテストツール（LangChain Tool）

ハードコードされたSlidevスライドを生成し、PDF出力をテストする。
ReActエージェントから呼び出してSlidev動作確認を行う。

Phase 0（MVP検証用）:
- ハードコードされたマークダウン
- slidev export コマンドでPDF生成
- フロントエンドへのパス返却テスト
"""

from langchain_core.tools import tool
from typing import Optional
import json
from pathlib import Path
import subprocess
import shutil
import re

# 既存のmarp_agentからユーティリティ関数をインポート
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from marp_agent import _slugify_en


@tool
def generate_slidev_test(topic: str = "AI最新情報") -> str:
    """Slidevでテストスライドを生成（ハードコード版）

    ハードコードされたSlidevマークダウンからPDFスライドを生成。
    MVPとしてSlidev動作確認、フロントエンド統合テストに使用。

    処理フロー:
    1. ハードコードされたSlidevマークダウンを生成
    2. .mdファイルとして保存
    3. slidev export コマンドでPDF出力
    4. ファイルパスをJSON形式で返却

    Args:
        topic: スライドのトピック（デフォルト: "AI最新情報"）

    Returns:
        str: 生成されたスライドのパスと結果情報（JSON形式）
    """

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

    try:
        # ファイル保存
        slide_dir = Path(__file__).parent.parent / "slides"
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

                # 絶対パスから相対パスに変換（frontend/publicからアクセス可能にする）
                relative_path = str(pdf_path.relative_to(slide_dir.parent))

                return json.dumps({
                    "status": "success",
                    "message": f"✅ Slidevスライドを生成しました: {pdf_path.name}",
                    "title": topic,
                    "slide_path": relative_path
                }, ensure_ascii=False)

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
                "error": "slidevをインストールしてください: npm install -g slidev"
            }, ensure_ascii=False)

    except Exception as e:
        # 予期しないエラー
        return json.dumps({
            "status": "error",
            "message": f"❌ スライド生成例外: {str(e)}",
            "title": topic
        }, ensure_ascii=False)
