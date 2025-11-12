"""スライド評価用プロンプト定義

定数 + メソッドのハイブリッド設計:
- 評価基準は定数として定義（可読性・バージョン管理重視）
- メソッドで入力タイプに応じた評価基準を動的に切り替え
"""

from typing import List, Tuple
import json

# =======================
# 評価プロンプト（PDF用）
# =======================

EVAL_PDF_SYSTEM = """あなたはCloud Solution Architectです。以下のSlidevスライドMarkdownを、指定の観点・重みで厳密に採点します。出力はJSONのみ。"""

EVAL_PDF_GUIDE = """評価観点と重み:
- structure(0.20): スライドの流れ、章立て、1スライド1メッセージ + **結論スライドの配置**
- comprehensiveness(0.25): PDF全体の重要トピックをカバー + **Mermaid図解による情報量強化**
- clarity(0.25): 中学生にもわかる説明 + **図解による視覚的理解** + **結論の直感的理解**
- readability(0.15): 簡潔明瞭、視認性
- engagement(0.15): 興味を引く工夫 + **図解による理解促進**
合格: score >= 8.0

【重要】
- PDFの最初のページだけでなく、全体の流れを反映していること
- 専門用語は中学生にもわかる言葉で説明されていること
- 絵文字や視覚要素で視覚的に理解しやすいこと

【結論スライド評価基準（NEW）】
以下の基準で結論スライドを評価:

1. **配置とフォーマット** (structure への加点)
   - ✅ タイトル直後、目次の前に配置: 必須
   - ✅ 見出しなし（本文のみで構成）: 必須
   - ✅ `layout: center` を使用: 必須
   - ✅ 1文のみで構成（箇条書き・要点なし）: 必須
   - ❌ 箇条書きや複数の要点を含む: 減点
   - ❌ 「結論」などの見出しを含む: 減点
   - ❌ HTMLタグを含む: 減点

2. **直感的理解と実用性のバランス** (clarity への加点)
   - ✅ 比喩で理解しやすく、かつ実務での価値が自然に示されている: +0.7点
   - ✅ 中学生が「これ面白そう！役立ちそう！」と興味を持てる: +0.5点
   - ✅ 30-60文字程度（実利を含む適切な長さ）: +0.3点
   - ❌ 比喩だけで実利が不明: 減点
   - ❌ 実利の表現が説教臭い、固すぎる: 減点
   - ❌ 本編のトーン（中学生向け）と乖離: 減点
   - ❌ 専門用語をそのまま使用: 減点

3. **視覚的レイアウト** (readability への加点)
   - ✅ `layout: center` で中央配置: +0.2点
   - ✅ 太字（**...**）で全体を囲む: +0.2点
   - ❌ 通常の本文と同じレイアウト: 減点
   - ❌ 見出し（#や##）を使用: 減点
   - ❌ HTMLタグを使用: 減点

【Mermaid図解評価（加点要素）】
以下の基準でMermaid図解を評価:

1. **独自性と関連性** (comprehensiveness/engagement への加点)
   - ✅ PDFのトピック/内容に応じた独自の図解: +0.5点
   - ✅ 目次直後またはまとめ直前に配置され、内容と関連: +0.3点
   - ❌ 汎用的すぎる図(例: 単なる「データ入力→前処理→学習→評価」): 加点なし
   - ❌ トピックと無関係な図: 加点なし

2. **図解の種類と用途**
   - flowchart: 技術フロー、プロセス、アーキテクチャ
   - mindmap: 概念整理、活用例、分類
   - sequenceDiagram: 時系列の処理、対話フロー
   - その他: トピックに応じた適切な図形式

3. **品質基準**
   - ✅ Mermaid構文が正しい
   - ✅ 図解の直後に説明文がある
   - ✅ PDFの具体的な内容を反映している
   - ❌ 構文エラーまたは内容と無関係: 加点なし"""

EVAL_PDF_USER = """Topic: {topic}
TOC: {toc}

Slides (Slidev Markdown):
<<<SLIDES
{slide_md}
SLIDES

Evaluation Guide:
<<<EVAL
{eval_guide}
EVAL

Return strictly this JSON schema:
{{
  "score": number,
  "subscores": {{"structure": number, "comprehensiveness": number, "clarity": number, "readability": number, "engagement": number}},
  "reasons": {{"structure": string, "comprehensiveness": string, "clarity": string, "readability": string, "engagement": string}},
  "suggestions": [string],
  "risk_flags": [string],
  "pass": boolean,
  "feedback": string
}}"""


# =======================
# 評価プロンプト（AI情報用）
# =======================

EVAL_AI_SYSTEM = """あなたはCloud Solution Architectです。以下のSlidevスライドMarkdownを、指定の観点・重みで厳密に採点します。出力はJSONのみ。"""

EVAL_AI_GUIDE = """評価観点と重み:
- structure(0.20): スライドの流れ、章立て、1スライド1メッセージ
- practicality(0.25): 実務に使える具体性（手順、具体例、注意点）
- accuracy(0.25): 事実・用語の正確さ
- readability(0.15): 簡潔明瞭、視認性（箇条書きの粒度）
- conciseness(0.15): 冗長性の少なさ
合格: score >= 8.0"""

EVAL_AI_USER = """Topic: {topic}
TOC: {toc}

Slides (Slidev Markdown):
<<<SLIDES
{slide_md}
SLIDES

Evaluation Guide:
<<<EVAL
{eval_guide}
EVAL

Return strictly this JSON schema:
{{
  "score": number,
  "subscores": {{"structure": number, "practicality": number, "accuracy": number, "readability": number, "conciseness": number}},
  "reasons": {{"structure": string, "practicality": string, "accuracy": string, "readability": string, "conciseness": string}},
  "suggestions": [string],
  "risk_flags": [string],
  "pass": boolean,
  "feedback": string
}}"""


# =======================
# 評価プロンプト生成メソッド
# =======================

def get_evaluation_prompt(
    slide_md: str,
    toc: List[str],
    topic: str,
    input_type: str
) -> List[Tuple[str, str]]:
    """スライド評価プロンプトを生成（入力タイプで評価基準を切り替え）

    Args:
        slide_md: Slidevスライドのマークダウン
        toc: 目次リスト
        topic: スライドのトピック
        input_type: 入力タイプ（"pdf" | "youtube" | "text"）

    Returns:
        LLMプロンプト（system, user）のタプルリスト
    """
    toc_json = json.dumps(toc, ensure_ascii=False)

    # PDF用評価基準
    if input_type == "pdf":
        return [
            ("system", EVAL_PDF_SYSTEM),
            ("user", EVAL_PDF_USER.format(
                topic=topic,
                toc=toc_json,
                slide_md=slide_md,
                eval_guide=EVAL_PDF_GUIDE
            ))
        ]
    # AI情報用評価基準（デフォルト）
    else:
        return [
            ("system", EVAL_AI_SYSTEM),
            ("user", EVAL_AI_USER.format(
                topic=topic,
                toc=toc_json,
                slide_md=slide_md,
                eval_guide=EVAL_AI_GUIDE
            ))
        ]
