# スライド生成システムの統一設計方針

**作成日**: 2025-11-13
**ステータス**: 設計提案
**関連Issue**: スライド分割問題（PDFアップロード後のプレビュー表示）

---

## 📋 目次

- [概要](#概要)
- [設計原則](#設計原則)
- [現状の問題分析](#現状の問題分析)
- [統一設計アーキテクチャ](#統一設計アーキテクチャ)
- [実装詳細](#実装詳細)
- [移行計画](#移行計画)
- [期待される効果](#期待される効果)

---

## 概要

### 背景

現在のスライド生成システムには、**2つの独立したワークフロー**が存在します：

1. **AI情報スライド** (`_generate_multi_vendor_slides_integrated`)
   - Tavily検索結果から6社のAI最新情報をスライド化
   - Python側で機械的に構造を制御（YAMLフロントマター + `---` 区切り）
   - **堅牢で安定した動作**

2. **PDFスライド** (`write_slides_slidev`)
   - PDFテキストから教育向けスライドを生成
   - LLMに全て任せている（構造 + 内容）
   - **LLM依存で不安定** → フロントエンドで分割エラーが発生

### 問題

PDF版スライドでは、LLMが以下を出力することを期待していますが、実際には不安定です：

```markdown
---
theme: apple-basic
highlighter: shiki
---

# タイトル

---

## セクション1

内容

---

## セクション2

内容
```

LLMが `---` 区切りを出力しない、または不正な形式で出力するため、フロントエンドの `.split(/\n---\n/)` が正しく動作しません。

### 目的

**AI情報スライドの成功パターンをPDF版にも適用**し、両ワークフローで同じ堅牢な設計を実現します。

---

## 設計原則

### 核となる原則: **責任の分離 (Separation of Concerns)**

```
┌─────────────────────────────────────────────────┐
│  LLM (Large Language Model)                     │
│  ────────────────────────────────               │
│  責任: コンテンツ生成                            │
│  - 見出し（# または ## で開始）                  │
│  - 本文テキスト                                  │
│  - 箇条書き                                      │
│  - Mermaid図解（codeblock形式）                 │
│                                                  │
│  ❌ やらないこと:                                │
│  - YAMLフロントマター生成                        │
│  - スライド区切り（---）挿入                     │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│  Python (Backend Processing)                    │
│  ────────────────────────────────               │
│  責任: 構造制御                                  │
│  - YAMLフロントマター追加                        │
│  - `---` 区切りを機械的に挿入                    │
│  - コードブロック保護                            │
│  - 連続した `---` の圧縮                         │
│                                                  │
│  ✅ 保証すること:                                │
│  - Slidev仕様に準拠したMarkdown                 │
│  - フロントエンドで確実に分割可能                │
└─────────────────────────────────────────────────┘
```

### なぜこの設計が優れているか

| 従来（PDF版）| 新設計 | 利点 |
|-------------|--------|------|
| LLMに全て任せる | LLMは内容のみ | **安定性**: LLMの出力品質に依存しない |
| 構造の検証なし | Python側で構造保証 | **信頼性**: 100%正しいフォーマット |
| AI情報版と別実装 | 共通パターン | **保守性**: 一貫した設計、DRY原則 |
| デバッグ困難 | 構造問題はPython側 | **デバッグ容易性**: 問題の切り分けが明確 |

---

## 現状の問題分析

### AI情報スライド（正常動作）

**ファイル**: `backend/app/core/utils.py:300-399`

```python
def _generate_multi_vendor_slides_integrated(topic: str, sources: Dict, mvp_version: str) -> str:
    # ... LLMで各ベンダーの箇条書きを生成 ...

    # Python側で構造を完全に制御
    slide_content = f"""# 🚀 {topic}

## {mvp_version}

{month_ja()}

---

## 📋 目次

"""

    # 各ベンダーのスライド（---を機械的に挿入）
    for vb in vendor_bullets:
        slide_content += f"""---

## {vb['emoji']} {vb['name']}

{chr(10).join(vb['bullets'])}

"""

    # まとめスライド
    slide_content += f"""---

# ✨ 本日のまとめ

## 🔑 キーポイント
...
"""

    return slide_content
```

**特徴**:
- ✅ YAMLフロントマターなし（後で追加する設計）
- ✅ `---` を機械的に挿入（LLM依存なし）
- ✅ 構造はPython側で完全制御
- ✅ **100%確実に動作**

### PDFスライド（問題あり）

**ファイル**: `backend/app/agents/slide_workflow.py:468-542`

```python
def write_slides_slidev(state: State) -> Dict:
    if input_type == "pdf":
        # ... PDFチャンク処理 ...

        # LLMにSlidevマークダウン全体を生成させる
        prompt = get_slide_pdf_prompt(
            full_summary=full_summary,
            key_points=key_points,
            toc=toc,
            ja_title=ja_title
        )

        msg = llm.invoke(prompt)
        slide_md = msg.content.strip()  # ❌ LLMに全て任せている

        # コードブロック除去のみ
        slide_md = _strip_whole_code_fence(slide_md)

        return {
            "slide_md": slide_md,
            "title": ja_title,
            "error": "",
            "log": _log(state, f"[slides_slidev_pdf] generated")
        }
```

**プロンプト内容** (`backend/app/prompts/slide_prompts.py:234-288`):

```
【要件】
- Slidev形式（YAMLフロントマター + Markdown）  # ❌ LLMに構造生成を期待
- theme: apple-basic を使用                      # ❌ LLMがYAML生成
- タイトルスライド: # {ja_title}
- 目次スライド: 目次を箇条書きで表示
- 各セクション: 目次に基づいて5-8スライド作成
...
出力はSlidevマークダウンのみ（コードブロック不要）:  # ❌ 区切りも含めてLLM依存
```

**問題点**:
- ❌ LLMが `---` 区切りを生成することを期待
- ❌ LLMがYAMLフロントマターを生成することを期待
- ❌ LLMの出力品質に完全依存
- ❌ **不安定で予測不可能**

### 設計の分断

| 項目 | AI情報スライド | PDFスライド |
|------|---------------|------------|
| **Markdown生成** | Python (機械的) | LLM (生成的) |
| **YAMLフロントマター** | なし（後で追加） | LLMに生成させる |
| **`---` 区切り** | Python挿入 | LLMに生成させる |
| **信頼性** | ✅ 100%確実 | ❌ LLM依存で不安定 |
| **コード位置** | `utils.py` | `slide_workflow.py` + `slide_prompts.py` |

---

## 統一設計アーキテクチャ

### 全体フロー

```
┌─────────────────────────────────────────────────────────────┐
│  1. LLMによるコンテンツ生成（内容のみ）                      │
├─────────────────────────────────────────────────────────────┤
│  Input:  PDF chunks / Tavily search results                 │
│  Prompt: 「見出し（## ）と本文のみ生成、構造は不要」          │
│  Output: 生のMarkdown（YAMLなし、区切りなし）                │
│                                                              │
│  # タイトル                                                  │
│                                                              │
│  **結論1文**                                                 │
│                                                              │
│  ## 目次                                                     │
│  - 項目1                                                     │
│  - 項目2                                                     │
│                                                              │
│  ## セクション1                                              │
│  内容...                                                     │
│                                                              │
│  ## セクション2                                              │
│  内容...                                                     │
│                                                              │
│  ## まとめ                                                   │
│  - ポイント1                                                 │
│  - ポイント2                                                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Python側での構造制御（`write_slides_slidev`）            │
├─────────────────────────────────────────────────────────────┤
│  Step 1: コードブロック除去（既存）                          │
│    raw_content = _strip_whole_code_fence(msg.content)       │
│                                                              │
│  Step 2: 既存のフロントマター削除（保険）                    │
│    raw_content = re.sub(r'^---[\s\S]*?---\s*', '', ...)     │
│                                                              │
│  Step 3: YAMLフロントマター生成                              │
│    frontmatter = """---                                      │
│    theme: apple-basic                                        │
│    highlighter: shiki                                        │
│    class: text-center                                        │
│    ---                                                       │
│                                                              │
│    """                                                       │
│                                                              │
│  Step 4: 見出し前に`---`を機械的に挿入                       │
│    content_with_separators = _insert_separators(raw_content)│
│                                                              │
│  Step 5: 連続した`---`を圧縮                                 │
│    content_with_separators = _double_separators(...)        │
│                                                              │
│  Step 6: 最終Markdown生成                                    │
│    slide_md = frontmatter + content_with_separators         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  3. 最終出力（Slidev準拠のMarkdown）                         │
├─────────────────────────────────────────────────────────────┤
│  ---                                                         │
│  theme: apple-basic                                          │
│  highlighter: shiki                                          │
│  class: text-center                                          │
│  ---                                                         │
│                                                              │
│  # タイトル                                                  │
│                                                              │
│  **結論1文**                                                 │
│                                                              │
│  ---                                                         │
│                                                              │
│  ## 目次                                                     │
│  - 項目1                                                     │
│  - 項目2                                                     │
│                                                              │
│  ---                                                         │
│                                                              │
│  ## セクション1                                              │
│  内容...                                                     │
│                                                              │
│  ---                                                         │
│                                                              │
│  ## セクション2                                              │
│  内容...                                                     │
│                                                              │
│  ---                                                         │
│                                                              │
│  ## まとめ                                                   │
│  - ポイント1                                                 │
│  - ポイント2                                                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  4. Supabase保存 & フロントエンド表示                        │
├─────────────────────────────────────────────────────────────┤
│  - Supabase DB: `slides.slide_md` に保存                    │
│  - フロントエンド: `.split(/\n---\n/)` で確実に分割          │
│  - SlideContentViewer: 各スライドを個別カード表示            │
└─────────────────────────────────────────────────────────────┘
```

### 既存の補助関数（再利用）

**`backend/app/core/utils.py`**:

```python
def _insert_separators(md: str) -> str:
    """
    コードブロックを壊さず、H2(## )の直前に1つだけ '---' を入れる。
    """
    # ... 実装省略（既存コード）...
    # 重要: コードブロック内（```で囲まれた部分）は保護される

def _double_separators(md: str) -> str:
    """
    連続する区切り（---, 空行, --- ...) を1個に圧縮。
    """
    # 例: "\n---\n\n---\n" → "\n---\n"
    # 例: "\n\n\n---\n\n---\n\n" → "\n---\n"
```

---

## 実装詳細

### 1. プロンプト修正

**ファイル**: `backend/app/prompts/slide_prompts.py`

**修正前** (Line 245-268):
```python
【要件】
- Slidev形式（YAMLフロントマター + Markdown）
- theme: apple-basic を使用
- タイトルスライド: # {ja_title}
- **結論スライド（NEW）**: タイトル直後、目次の前に1枚追加
  - 見出しなし（内容のみで構成）
  - レイアウト: `layout: center` を使用して中央配置
  ...
- 目次スライド: 目次を箇条書きで表示（見出しは「目次」を使用、<v-clicks>は使わない）
- 各セクション: 目次に基づいて5-8スライド作成
...
出力はSlidevマークダウンのみ（コードブロック不要）:
```

**修正後**:
```python
【要件】
- **YAMLフロントマターは不要**（Python側で自動追加します）
- **スライド区切り（---）は不要**（Python側で自動挿入します）
- **重要**: 見出し（## ）と内容のみに集中してください
- タイトルスライド: # {ja_title}
- **結論スライド**: タイトル直後、目次の前に1枚追加
  - 見出しなし（内容のみで構成）
  - 専門的な内容を中学生でも直感的に理解でき、かつ実務での価値が分かる**1文のみ**で表現
  - 比喩＋実利のバランス：「〜のようなもの：〜できる」形式を推奨
  - 30-60文字程度
  - 箇条書き・要点は含めない
  - 大きな文字にするため、全体を太字（**...**）で囲む
  - 例:
    - 機械学習: 「**AIは試行錯誤で学ぶ職人：データの質を改善すれば、誰でも精度を上げられる**」
    - Transformer: 「**文章全体を一度に見る編集者：プロンプトの書き方次第で回答の質が変わる**」
- 目次スライド: ## 目次（見出しの後に目次を箇条書きで表示、<v-clicks>は使わない）
- 各セクション: 目次に基づいて5-8スライド作成、**各スライドは ## 見出しで始める**
- 各スライドは簡潔に（1スライド1メッセージ）
- 中学生でもわかる言葉で説明
- できれば短いストーリーや、先生と生徒の会話形式も使ってください
- まとめスライド: ## まとめ（【重要ポイント】で示した5個すべてを箇条書きで表示）
- PDF全体の流れを反映した論理的な構成にしてください

【絵文字使用ルール】厳守
- **タイトルスライド（#）**: 絵文字なし
- **見出しスライド（##）**: 絵文字なし
- **本文（箇条書き）**: 絵文字なし
- **会話形式のみ**: 👨‍🏫（先生）と🧑‍🎓（生徒）の2つの絵文字のみ使用可能

【Mermaid図解の要件】必須
- **目次直後**: PDFの内容に応じた独自の技術フロー図またはアーキテクチャ図を作成
  - 例: AIの学習プロセス、システム構成、処理フロー、データの流れ
- **まとめ直前**: PDFの内容に応じた独自の活用例図または概念整理図を作成
  - 例: ユースケース、応用分野、技術の分類、関連概念の整理
- **図の種類**: flowchart, mindmap, sequenceDiagram等、内容に最適な形式を選択
- **見出し**: 絵文字なし、内容を端的に表現（例: 「全体の構造」「活用シーン」）
- **説明文**: 図の下に説明文は追加しない

**出力形式**:
- YAMLフロントマター、スライド区切り（---）は一切出力しないでください
- 見出し（# または ##）と内容のみを出力してください
- Python側で自動的に構造化されます
```

### 2. ワークフロー修正

**ファイル**: `backend/app/agents/slide_workflow.py`

**修正箇所**: `write_slides_slidev()` 関数（Line 468-542）

**修正前**:
```python
def write_slides_slidev(state: State) -> Dict:
    if input_type == "pdf":
        # ... 既存のチャンク処理 ...

        msg = llm.invoke(prompt)
        slide_md = msg.content.strip()
        slide_md = _strip_whole_code_fence(slide_md)

        return {
            "slide_md": slide_md,
            "title": ja_title,
            "error": "",
            "log": _log(state, f"[slides_slidev_pdf] generated")
        }
```

**修正後**:
```python
def write_slides_slidev(state: State) -> Dict:
    if input_type == "pdf":
        # ... 既存のチャンク処理（変更なし）...

        msg = llm.invoke(prompt)
        raw_content = msg.content.strip()

        # Step 1: コードブロック除去（既存）
        raw_content = _strip_whole_code_fence(raw_content)

        # Step 2: 既存のフロントマター削除（LLMが勝手に生成した場合の保険）
        raw_content = re.sub(r'^---[\s\S]*?---\s*', '', raw_content.strip(), count=1)

        # Step 3: YAMLフロントマター生成（Python側で制御）
        frontmatter = """---
theme: apple-basic
highlighter: shiki
class: text-center
---

"""

        # Step 4: 見出し（## ）前に `---` を機械的に挿入
        content_with_separators = _insert_separators(raw_content)

        # Step 5: 連続した --- を圧縮（安全装置）
        content_with_separators = _double_separators(content_with_separators)

        # Step 6: 最終的なMarkdown生成
        slide_md = frontmatter + content_with_separators

        return {
            "slide_md": slide_md,
            "title": ja_title,
            "error": "",
            "log": _log(state, f"[slides_slidev_pdf] generated ({len(slide_md)} chars) with mechanical structure control")
        }
```

**必要なimport追加**:
```python
import re  # すでに存在する場合はスキップ
```

### 3. AI情報版にもフロントマター追加（一貫性のため）

**ファイル**: `backend/app/core/utils.py`

**修正箇所**: `_generate_multi_vendor_slides_integrated()` 関数（Line 300-399）

**修正前** (Line 344-355):
```python
# シンプルなMarkdown生成（Slidev廃止）
slide_content = f"""# 🚀 {topic}

## {mvp_version}

{month_ja()}

---

## 📋 目次

"""
```

**修正後**:
```python
# YAMLフロントマター追加（PDF版と統一）
frontmatter = """---
theme: apple-basic
highlighter: shiki
class: text-center
---

"""

# シンプルなMarkdown生成
slide_content = frontmatter + f"""# 🚀 {topic}

## {mvp_version}

{month_ja()}

---

## 📋 目次

"""
```

---

## 移行計画

### フェーズ1: プロンプト修正（即座に実施可能）

- [ ] `backend/app/prompts/slide_prompts.py` の `SLIDE_PDF_USER` を修正
- [ ] LLMに「YAMLフロントマター不要、区切り不要、内容のみ」と明示
- [ ] 見出しルール強化：「各スライドは ## で始める」

### フェーズ2: ワークフロー修正（核となる変更）

- [ ] `backend/app/agents/slide_workflow.py` の `write_slides_slidev()` 修正
- [ ] 6ステップの構造制御ロジックを追加
- [ ] `_insert_separators` と `_double_separators` を活用

### フェーズ3: AI情報版の統一（一貫性のため）

- [ ] `backend/app/core/utils.py` の `_generate_multi_vendor_slides_integrated()` 修正
- [ ] YAMLフロントマター追加

### フェーズ4: テスト & 検証

- [ ] PDFアップロード → スライド生成 → プレビュー表示のE2Eテスト
- [ ] 複数のPDFサンプルでテスト（技術文書、論文、教科書等）
- [ ] AI情報スライドの動作に影響がないか確認
- [ ] Supabaseに保存されたMarkdownの検証

### フェーズ5: ドキュメント更新

- [ ] `CLAUDE.md` に新しい設計方針を追記
- [ ] 開発者向けガイドに構造制御ロジックの説明を追加

---

## 期待される効果

### 1. 信頼性の向上

- **Before**: LLMが `---` を出力しないことがある → フロントエンドで分割エラー
- **After**: Python側で100%確実に `---` を挿入 → エラーゼロ

### 2. 保守性の向上

- **Before**: AI情報版とPDF版で別々の実装 → 修正が2箇所必要
- **After**: 共通の構造制御パターン → DRY原則、修正は1箇所

### 3. デバッグの容易性

- **Before**: 「LLMの出力が悪い？プロンプトが悪い？コードが悪い？」判別困難
- **After**: 「内容の問題 → プロンプト修正、構造の問題 → Python修正」明確

### 4. LLMトークン効率化

- **Before**: LLMが `---` やYAMLも生成 → 無駄なトークン消費
- **After**: LLMは内容のみ生成 → トークン節約、コスト削減

### 5. フロントエンドの安定性

- **Before**: Markdownの形式に依存 → エッジケースで壊れる
- **After**: Slidev仕様準拠を保証 → 堅牢な表示

---

## 参考: Slidev Markdown仕様

公式ドキュメント: https://sli.dev/guide/syntax.html

**スライド区切りの仕様**:
```markdown
---
theme: apple-basic
---

# スライド1

内容

---

# スライド2

内容

---

# スライド3

内容
```

**重要ポイント**:
- スライド区切りは `\n---\n`（前後に改行）
- YAMLフロントマターは最初の `---` で囲まれた部分
- H2以降（`##`）は自動的にスライド分割されない（明示的に `---` が必要）

---

## まとめ

この設計方針により、**LLMの強み（内容生成）とPythonの強み（構造制御）を分離**し、両者の責任を明確にします。

```
┌──────────────────────────────────────────────────┐
│  統一設計の核となる思想                           │
├──────────────────────────────────────────────────┤
│  "LLMは創造的なコンテンツ生成に専念し、          │
│   Pythonは機械的な構造制御を担保する"            │
│                                                   │
│  → 両者の責任を分離することで、                   │
│     信頼性・保守性・デバッグ容易性を実現          │
└──────────────────────────────────────────────────┘
```

この原則に従うことで、スライド生成システム全体が**予測可能で安定したアーキテクチャ**に進化します。
