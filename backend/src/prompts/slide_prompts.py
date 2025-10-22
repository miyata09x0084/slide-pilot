"""スライド生成用プロンプト定義

定数 + メソッドのハイブリッド設計:
- プロンプト本文は定数として定義（可読性・バージョン管理重視）
- メソッドで型安全な呼び出しインターフェースを提供
"""

from typing import List, Tuple

# =======================
# キーポイント抽出（Map段階）
# =======================

KEY_POINTS_MAP_SYSTEM = "あなたは教育のプロフェッショナルです。中学生にも分かりやすく内容を説明する専門家です。"

KEY_POINTS_MAP_USER = """以下のテキストから、中学生にもわかるように重要なポイントを最大3個、短い箇条書きで抽出してください。

[テキスト部分 {chunk_index}]
{chunk}

箇条書き形式で出力してください（最大3個）:"""


def get_key_points_map_prompt(chunk: str, chunk_index: int) -> List[Tuple[str, str]]:
    """PDF各チャンクからキーポイントを抽出（Map段階）

    Args:
        chunk: PDFチャンクテキスト（最大3000文字まで使用）
        chunk_index: チャンク番号（1-indexed）

    Returns:
        LLMプロンプト（system, user）のタプルリスト
    """
    return [
        ("system", KEY_POINTS_MAP_SYSTEM),
        ("user", KEY_POINTS_MAP_USER.format(
            chunk_index=chunk_index,
            chunk=chunk[:3000]
        ))
    ]


# =======================
# キーポイント統合（Reduce段階）
# =======================

KEY_POINTS_REDUCE_SYSTEM = "あなたは教育のプロフェッショナルです。情報を整理統合するのが得意です。"

KEY_POINTS_REDUCE_USER = """以下の重要ポイントリストから、重複を削除し、最も重要な5個に絞り込んでください。

[抽出されたポイント]
{points_text}

【出力形式】
- 必ず箇条書き形式で出力（「-」または「1.」で始める）
- 必ず5個の箇条書き（4個や6個ではなく正確に5個）
- 「以下の5つのポイントは...」などの前置き文は不要
- 各ポイントは1行で簡潔に

中学生にもわかりやすい表現で、最重要な5個を選んでください:"""


def get_key_points_reduce_prompt(chunk_points: List[str]) -> List[Tuple[str, str]]:
    """抽出されたキーポイントを5つに統合（Reduce段階）

    Args:
        chunk_points: 各チャンクから抽出されたポイントのリスト

    Returns:
        LLMプロンプト（system, user）のタプルリスト
    """
    points_text = "\n".join([f"- {p}" for p in chunk_points])
    return [
        ("system", KEY_POINTS_REDUCE_SYSTEM),
        ("user", KEY_POINTS_REDUCE_USER.format(points_text=points_text))
    ]


# =======================
# キーポイント抽出（AI情報）
# =======================

KEY_POINTS_AI_SYSTEM = "あなたはSolution Engineerです。これからMarpスライドでAI最新情報を発表します。"

KEY_POINTS_AI_USER = """以下の「最新情報サマリ（出典付き）」を参考に、発表の重要ポイントを各社5個、短い箇条書きで。URLも含めてください。

[最新情報サマリ]
{context_md}

[トピック]
{topic}"""


def get_key_points_ai_prompt(context_md: str, topic: str) -> List[Tuple[str, str]]:
    """AI最新情報からキーポイントを抽出（Tavily検索結果用）

    Args:
        context_md: Tavily検索結果のMarkdown
        topic: スライドのトピック

    Returns:
        LLMプロンプト（system, user）のタプルリスト
    """
    return [
        ("system", KEY_POINTS_AI_SYSTEM),
        ("user", KEY_POINTS_AI_USER.format(
            context_md=context_md,
            topic=topic
        ))
    ]


# =======================
# 目次生成（PDF用）
# =======================

TOC_PDF_SYSTEM = "あなたは教育のプロフェッショナルです。中学生にも理解できるスライドの構成を考えるのが得意です。"

TOC_PDF_USER = """以下の重要ポイントから、中学生にもわかりやすい5〜8個の章立てを JSON の {{"toc": [ ... ]}} 形式で返してください。

各章タイトルはやさしい日本語で。構成に流れがあるようにしてください。

重要ポイント:
{points_text}

章立てはシンプルで親しみやすい言葉を使ってください。"""


def get_toc_pdf_prompt(key_points: List[str]) -> List[Tuple[str, str]]:
    """PDF用の目次生成（中学生向け）

    Args:
        key_points: 重要ポイントのリスト

    Returns:
        LLMプロンプト（system, user）のタプルリスト
    """
    points_text = "- " + "\n- ".join(key_points)
    return [
        ("system", TOC_PDF_SYSTEM),
        ("user", TOC_PDF_USER.format(points_text=points_text))
    ]


# =======================
# 目次生成（AI情報用）
# =======================

TOC_AI_SYSTEM = "あなたはSolution Engineerです。Marpスライドの構成（目次）を作ります。"

TOC_AI_USER = """以下の重要ポイントから、5〜8個の章立て（配列）を JSON の {{"toc": [ ... ]}} 形式で返してください。

重要ポイント:
{points_text}"""


def get_toc_ai_prompt(key_points: List[str]) -> List[Tuple[str, str]]:
    """AI最新情報用の目次生成

    Args:
        key_points: 重要ポイントのリスト

    Returns:
        LLMプロンプト（system, user）のタプルリスト
    """
    points_text = "- " + "\n- ".join(key_points)
    return [
        ("system", TOC_AI_SYSTEM),
        ("user", TOC_AI_USER.format(points_text=points_text))
    ]


# =======================
# スライドタイトル生成（PDF用）
# =======================

SLIDE_TITLE_SYSTEM = "あなたは教育のプロフェッショナルです。PDFの内容から魅力的なタイトルを作成します。"

SLIDE_TITLE_USER = """以下のPDF内容から、中学生向けスライドにふさわしい魅力的なタイトルを1行で生成してください。

【PDF冒頭】
{first_chunk}

【重要ポイント】
{points_text}

【要件】
- 中学生が興味を持つタイトル
- 簡潔でわかりやすい（15文字以内推奨）
- 絵文字は不要
- 例: 「AIの仕組みと未来」「地球温暖化を学ぼう」

タイトルのみを出力してください:"""


def get_slide_title_prompt(chunks: List[str], key_points: List[str]) -> List[Tuple[str, str]]:
    """PDFからスライドタイトルを生成

    Args:
        chunks: PDFチャンクのリスト
        key_points: 重要ポイントのリスト（最大3個使用）

    Returns:
        LLMプロンプト（system, user）のタプルリスト
    """
    first_chunk = chunks[0][:2000] if chunks else '内容なし'
    points_text = "\n".join([f"- {kp}" for kp in key_points[:3]])

    return [
        ("system", SLIDE_TITLE_SYSTEM),
        ("user", SLIDE_TITLE_USER.format(
            first_chunk=first_chunk,
            points_text=points_text
        ))
    ]


# =======================
# Slidevスライド生成（PDF用）
# =======================

SLIDE_PDF_SYSTEM = """あなたは教育のプロフェッショナルです。PDFの内容を中学生にもわかりやすく説明するSlidevスライドを作成します。各セクションでは、目次に基づいて短い物語や会話形式で説明してください。1枚のスライドには伝えたいポイントをひとつだけ載せ、絵文字も活用して子どもの興味を引いてください。専門用語は可能な限り避け、優しい口調で話しかけるように説明しましょう。"""

SLIDE_PDF_USER = """以下のPDF内容（抜粋）から、中学生向けのわかりやすいスライドを作成してください。

【PDF内容（セクション別抜粋）】
{full_summary}

【重要ポイント】
{points_text}

【目次】
{toc_text}

【要件】
- Slidev形式（YAMLフロントマター + Markdown）
- theme: apple-basic を使用
- タイトルスライド: # {ja_title}
- Agendaスライド: 目次を箇条書きで表示（<v-clicks>は使わない）
- 各セクション: 目次に基づいて5-8スライド作成
- 各スライドは簡潔に（1スライド1メッセージ）
- 中学生でもわかる言葉で説明
- 絵文字を活用して視覚的に
- できれば短いストーリーや、先生と生徒の会話形式も使ってください
- まとめスライド: 【重要ポイント】で示した5個すべてを箇条書きで表示してください
- PDF全体の流れを反映した論理的な構成にしてください

出力はSlidevマークダウンのみ（コードブロック不要）:"""


def get_slide_pdf_prompt(
    full_summary: str,
    key_points: List[str],
    toc: List[str],
    ja_title: str
) -> List[Tuple[str, str]]:
    """PDF用Slidevスライド生成プロンプト

    Args:
        full_summary: PDFチャンク要約（セクション別）
        key_points: 重要ポイントのリスト（最大5個）
        toc: 目次のリスト（最大8個）
        ja_title: スライドタイトル

    Returns:
        LLMプロンプト（system, user）のタプルリスト
    """
    points_text = "\n".join([f"- {kp}" for kp in key_points[:5]])
    toc_text = "\n".join([f"- {t}" for t in toc[:8]])

    return [
        ("system", SLIDE_PDF_SYSTEM),
        ("user", SLIDE_PDF_USER.format(
            full_summary=full_summary,
            points_text=points_text,
            toc_text=toc_text,
            ja_title=ja_title
        ))
    ]


# =======================
# ファイル名生成（英語slug）
# =======================

SLUG_SYSTEM = "You create concise English slugs for filenames."

SLUG_USER = """Convert the following Japanese title into a short English filename base (<=6 words). Only letters and spaces; no punctuation or numbers.

Title: {title}"""


def get_slug_prompt(title: str) -> List[Tuple[str, str]]:
    """スライドタイトルから英語ファイル名を生成

    Args:
        title: スライドタイトル（日本語）

    Returns:
        LLMプロンプト（system, user）のタプルリスト
    """
    return [
        ("system", SLUG_SYSTEM),
        ("user", SLUG_USER.format(title=title))
    ]
