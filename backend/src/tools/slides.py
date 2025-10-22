"""スライド生成ツール（LangChain Tool）

既存のslide_agentグラフをLangChain Toolとしてラップ。
ReActエージェントから呼び出してAI最新情報スライドを生成する。
"""

from langchain_core.tools import tool
from typing import Optional
import json
from pathlib import Path

# slide_workflowグラフをインポート
from src.agents.slide_workflow import graph, State


@tool
def generate_slides(topic: str = "AI最新情報") -> str:
    """スライドを生成（PDF/YouTube/テキスト対応）

    入力に応じて自動的に処理方法を切り替えます:
    - PDF: PDFファイルからテキスト抽出してスライド生成
    - YouTube URL: 字幕取得してスライド生成（準備中）
    - テキスト: Tavily検索でAI最新情報を収集してスライド生成

    処理フロー:
    1. 入力タイプ自動判別（PDF/YouTube/テキスト）
    2. コンテンツ収集（PDF抽出/YouTube字幕/Tavily検索）
    3. キーポイント抽出
    4. 目次生成
    5. スライド生成
    6. 評価（8.0以上で合格、最大3回リトライ）
    7. Slidev形式でPDF保存

    Args:
        topic: スライドのトピック
               - PDFファイルパス（例: "/path/to/file.pdf"）
               - YouTube URL（例: "https://youtube.com/watch?v=..."）
               - テキスト（例: "AI最新情報"）

    Returns:
        str: 生成されたスライドのパスと結果情報（JSON形式）
    """

    # 初期State設定
    init_state: State = {
        "topic": topic,
        "key_points": [],
        "toc": [],
        "slide_md": "",
        "score": 0.0,
        "subscores": {},
        "reasons": {},
        "suggestions": [],
        "risk_flags": [],
        "passed": False,
        "feedback": "",
        "title": "",
        "slide_path": "",
        "attempts": 0,
        "error": "",
        "log": [],
        "context_md": "",
        "sources": {}
    }

    try:
        # marp_agentグラフを実行
        result = graph.invoke(init_state)

        # エラーチェック
        if result.get("error"):
            return json.dumps({
                "status": "error",
                "message": f"❌ スライド生成エラー: {result['error']}"
            }, ensure_ascii=False)

        # 成功時の情報を返す
        title = result.get("title", "AI最新情報スライド")
        slide_path = result.get("slide_path", "")
        # score = result.get("score", 0.0)
        # passed = result.get("passed", False)

        # 絶対パスから相対パスに変換（frontend/publicからアクセス可能にする）
        relative_path = str(Path(slide_path).relative_to(Path(__file__).parent.parent))

        # JSON形式で返す（フロントエンドがパース可能）
        return json.dumps({
            "status": "success",
            "message": "✅ スライド生成完了",
            "title": title,
            "slide_path": relative_path
        }, ensure_ascii=False)

    except Exception as e:
        # エラー時もJSON形式で返す
        return json.dumps({
            "status": "error",
            "message": f"❌ スライド生成例外: {str(e)}"
        }, ensure_ascii=False)
