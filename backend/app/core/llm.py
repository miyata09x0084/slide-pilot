"""LLM クライアント（遅延初期化）。

ChatOpenAI を import 時に生成すると OPENAI_API_KEY が import 時必須になり、
このモジュールに（間接的にでも）依存する全モジュールが、キー未設定では
import すらできなくなる（テスト・CLIツール・PDF/YouTube専用フロー等が巻き添え）。

そこで実際に LLM を呼び出す瞬間まで ChatOpenAI の生成を遅延する。
既存の `from app.core.llm import llm; llm.invoke(...)` はプロキシ経由でそのまま動く。
新規コードは `get_llm()` を直接使うことを推奨。
"""

from functools import lru_cache

from langchain_openai import ChatOpenAI


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """ChatOpenAI インスタンスを返す（初回呼び出し時に生成し、以降はキャッシュ）。"""
    return ChatOpenAI(
        model="gpt-4o",  # 最新のGPT-4 Omniモデル（または "gpt-3.5-turbo" でコスト削減）
        temperature=0.2,
        max_retries=2,    # リトライ回数
        # api_key は環境変数 OPENAI_API_KEY から自動読み込み
    )


class _LazyLLM:
    """属性アクセス時に初めて実インスタンスを生成して委譲する遅延プロキシ。

    既存の `llm.invoke(...)` / `llm.batch(...)` をそのまま動かしつつ、
    import 時の ChatOpenAI 生成（= OPENAI_API_KEY 必須）を回避する。
    """

    def __getattr__(self, name: str):
        # __getattr__ は通常の属性解決で見つからない場合のみ発火する。
        # ここに来る = 実インスタンス側のメソッド/属性なので委譲する。
        return getattr(get_llm(), name)


# 後方互換: 既存コードは `from app.core.llm import llm` を使い続けられる。
llm = _LazyLLM()
