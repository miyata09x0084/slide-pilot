"""スライド生成ツール（LangChain Tool）

既存のslide_agentグラフをLangChain Toolとしてラップ。
ReActエージェントから呼び出してAI最新情報スライドを生成する。
"""

from langchain_core.tools import tool
import json
from pathlib import Path
from typing_extensions import Annotated
from langgraph.prebuilt import InjectedState

# slide_workflowグラフをインポート
from app.agents.slide_workflow import graph, State


@tool
def generate_slides(
    topic: str = "AI最新情報",
    state: Annotated[dict, InjectedState] = None
) -> str:
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
        state: LangGraphから自動注入されるState（user_id含む）
               このパラメータはLLMのツールスキーマから除外される

    Returns:
        str: 生成されたスライドのパスと結果情報（JSON形式）
    """

    # user_idを取得（InjectedStateから）
    user_id = state.get("user_id", "anonymous") if state else "anonymous"
    print(f"[generate_slides] topic={topic[:50]}, user_id={user_id}")

    # 初期State設定
    init_state: State = {
        "topic": topic,
        "user_id": user_id,  # ← 追加
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
        slide_id = result.get("slide_id")  # Supabase slide ID (Issue #24)
        pdf_url = result.get("pdf_url")    # Supabase公開URL (Issue #24)
        # score = result.get("score", 0.0)
        # passed = result.get("passed", False)

        # 絶対パスからファイル名を抽出してAPIエンドポイント形式に変換
        filename = Path(slide_path).name
        api_url = f"http://localhost:8001/api/slides/{filename}"

        # JSON形式で返す（フロントエンドがパース可能）
        # Issue #24: slide_idとpdf_urlを追加してブラウザプレビューを有効化
        return json.dumps({
            "status": "success",
            "message": "✅ スライド生成完了",
            "title": title,
            "slide_path": api_url,
            "slide_id": slide_id,
            "pdf_url": pdf_url
        }, ensure_ascii=False)

    except Exception as e:
        # エラー時もJSON形式で返す
        return json.dumps({
            "status": "error",
            "message": f"❌ スライド生成例外: {str(e)}"
        }, ensure_ascii=False)
