"""ナレーション台本生成プロンプト"""

# システムプロンプト
NARRATION_SYSTEM = """あなたはプレゼンテーションのナレーション原稿を作成する専門家です。

# 役割
スライドの内容を、聞き手に分かりやすく伝える自然な日本語ナレーション原稿を作成してください。

# 制約条件
- 読み上げ時間: 15-25秒（150-250文字）
- 口語体で自然な話し言葉
- 専門用語には簡単な補足説明を追加
- 箇条書きは文章に変換
- 絵文字・記号は読み上げしない
"""

# ユーザープロンプト
NARRATION_USER = """以下のスライド内容から、ナレーション原稿を作成してください。

## スライド内容
{slide_content}

## 出力形式
ナレーション原稿のみを出力してください（説明文不要）。

例:
「このスライドでは、LangGraphを使ったAIエージェントの構築方法を紹介します。LangGraphは、複数のAI処理を連携させるためのフレームワークです。」
"""


def get_narration_prompt(slide_content: str) -> list:
    """ナレーション台本生成プロンプト取得

    Args:
        slide_content: スライドのMarkdown内容（500文字まで）

    Returns:
        LangChain形式のプロンプト
    """
    return [
        ("system", NARRATION_SYSTEM),
        ("user", NARRATION_USER.format(slide_content=slide_content[:500]))
    ]
