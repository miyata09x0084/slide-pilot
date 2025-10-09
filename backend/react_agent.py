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

# ツールのインポート
from tools.gmail_tool import send_gmail
from tools.slide_generator import generate_slides

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

# システムプロンプト
# LLMにエージェントの役割と振る舞いを指示
SYSTEM_PROMPT = """あなたは親切なAIアシスタントです。

ユーザーの要望に応じて、以下のツールを使用できます:
- **send_gmail**: メール送信（添付ファイル対応）
- **generate_slides**: AI最新情報のスライドを自動生成

## 重要な指示

1. **ツールの使い分け**
   - スライド作成を求められたら → generate_slides
   - メール送信を求められたら → send_gmail
   - 両方なら → 順番に実行

2. **エラー処理**
   - ツールがエラーを返した場合、ユーザーに報告
   - 可能なら修正方法を提案（例: 無効なメールアドレス）

3. **自然な対話**
   - 思考過程を簡潔に説明
   - 結果を分かりやすく報告
   - 必要なら追加情報を質問

## 実行例

ユーザー: 「AI最新情報のスライド作って」
→ generate_slides ツールを使用

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
graph = create_react_agent(
    llm,
    tools,
    prompt=SYSTEM_PROMPT
)

# グラフの説明（LangGraph Studio用）
graph.name = "ReAct Agent (Gmail + Slides)"
graph.description = "対話的にGmail送信とスライド生成を実行するReActエージェント"
