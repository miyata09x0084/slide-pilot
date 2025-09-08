# LangGraph × LangSmith × OpenAI × Tavily × Marp
# フロー:
# 0) Tavilyで情報収集 -> 1) アウトライン生成 -> 2) 目次生成 -> 3) スライド(Marp)本文生成 -> 4) 評価(>=8でOK/それ以外は2へループ) -> 5) スライドMarkdown保存(+ marp-cliでpdf/png/html出力)

from dotenv import load_dotenv

# -------------------
# 環境変数読み込み
# -------------------

load_dotenv()