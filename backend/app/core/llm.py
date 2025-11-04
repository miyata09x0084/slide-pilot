"""LLM クライアント初期化"""

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
  model="gpt-4o",  # 最新のGPT-4 Omniモデル（または "gpt-3.5-turbo" でコスト削減）
  temperature=0.2,
  max_retries=2,    # リトライ回数
  # api_key は環境変数 OPENAI_API_KEY から自動読み込み
)
