"""ReActエージェント（Gmail送信 + スライド生成）

対話的にユーザーの指示を理解し、適切なツールを選択・実行する。
Reasoning（思考）とActing（行動）を繰り返して複雑なタスクを解決。

利用可能なツール:
- send_gmail: Gmail送信（添付ファイル対応）
- generate_slides: AI最新情報スライド生成
"""

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState
from langsmith import traceable
from typing_extensions import TypedDict

# ツールのインポート
from app.tools.gmail import send_gmail
from app.tools.slides import generate_slides

# 環境変数読み込み
load_dotenv()

# LangSmith トレーシング設定
import os
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "react-agent")

# LLM設定（GPT-4o）
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,  # 決定的な応答（再現性重視）
)

# ツールリスト
tools = [send_gmail, generate_slides]

# MessagesStateを拡張してuser_idフィールド追加
# create_react_agentで必要なフィールドも含める
class State(MessagesState):
    user_id: str = "anonymous"  # ユーザー識別子（デフォルト: "anonymous"）
    remaining_steps: int = 10   # create_react_agentで必須（最大ステップ数）

# システムプロンプト
# LLMにエージェントの役割と振る舞いを指示
SYSTEM_PROMPT = """あなたは親切なAIアシスタントです。

ユーザーの要望に応じて、以下のツールを使用できます:
- **send_gmail**: メール送信（添付ファイル対応）
- **generate_slides**: スライド自動生成（PDF/YouTube/AI最新情報対応）
  - 引数: topic のみを指定してください
  - user_idは自動的にLangGraphから注入されます（明示的に渡す必要はありません）
  - **PDFファイル**（Storage形式: "user_id/filename.pdf" または "anonymous/filename.pdf"）→ PDFテキスト抽出してスライド生成
  - **YouTube URL**（例: "https://youtube.com/..."）→ 字幕取得してスライド生成（準備中）
  - **テキスト**（例: "AI最新情報"）→ Tavily検索でAI Industry Report生成
  - 入力は自動判別されます（`.pdf`で終わる → PDF、`youtube.com` → YouTube、その他 → テキスト）
  - LangGraphワークフローで品質評価（score ≥ 8.0）を実施
  - 評価基準: structure, practicality, accuracy, readability, conciseness

## 重要な指示

1. **入力タイプの自動判別**
   - ユーザーがPDFファイルパスを指定 → generate_slidesツールにそのまま渡す
   - ユーザーがYouTube URLを指定 → generate_slidesツールにそのまま渡す（準備中）
   - ユーザーがテキストを指定 → generate_slidesツールにそのまま渡す

2. **ツールの使い分け**
   - **スライド作成** → generate_slides（評価付き、高品質保証）
   - **メール送信** → send_gmail

3. **エラー処理**
   - ツールがエラーを返した場合、ユーザーに報告
   - 可能なら修正方法を提案

4. **自然な対話**
   - 思考過程を簡潔に説明
   - 結果を分かりやすく報告
   - 必要なら追加情報を質問

## 重要: user_idについて

- **generate_slidesにuser_idを渡してはいけません**
- user_idはLangGraphが自動的に注入します
- ツール呼び出し時はtopic引数のみを指定してください

## 実行例

ユーザー: 「このPDFから中学生向けのわかりやすいスライドを作成してください: anonymous/document.pdf」
→ generate_slides(topic="anonymous/document.pdf") を実行  ← user_idは渡さない

ユーザー: 「AI最新情報のスライド作って」
→ generate_slides(topic="AI最新情報") を実行  ← user_idは渡さない

ユーザー: 「それをtanaka@example.comに送って」
→ send_gmail ツールを使用（前回生成したスライドを添付）

ユーザー: 「スライド作ってdev@example.comに送って」
→ generate_slides → send_gmail を順番に実行
"""

# ReActエージェント作成
# create_react_agent: LangGraphのビルトイン関数
# - 自動的にReActループを構築
# - 思考 → ツール選択 → 実行 → 観察 を繰り返す
# システムプロンプトはprompt引数で渡す
# state_schema: カスタムState（user_idフィールド追加）を指定
graph = create_react_agent(
    llm,
    tools,
    prompt=SYSTEM_PROMPT,
    state_schema=State  # user_idフィールドを含むカスタムState
)

# グラフの説明（LangGraph Studio用）
graph.name = "ReAct Agent (Gmail + Slides)"
graph.description = "対話的にGmail送信とスライド生成を実行するReActエージェント"
