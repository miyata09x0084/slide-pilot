"""スライド生成ツール（LangChain Tool）

既存のslide_agentグラフをLangChain Toolとしてラップ。
ReActエージェントから呼び出してAI最新情報スライドを生成する。
"""

from langchain_core.tools import tool
from typing import Optional
import json
from pathlib import Path

# 既存のslide_agentをインポート
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from slide_agent import graph, State


@tool
def generate_slides(topic: str = "AI最新情報") -> str:
    """AI最新情報のスライドを生成

    Tavily検索で最新AIニュースを収集し、Slidevスライドを自動生成する。
    評価スコア8.0以上になるまで最大3回リトライ。

    処理フロー:
    1. Tavily検索（直近2ヶ月のAIニュース）
    2. キーポイント抽出
    3. 目次生成
    4. スライド生成
    5. 評価（8.0以上で合格）
    6. PDF/PNG/HTML保存

    Args:
        topic: スライドのトピック（デフォルト: "AI最新情報"）

    Returns:
        str: 生成されたスライドのパスと結果情報
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
