# Issue #20 実装計画: 教育向けブラウザテーマ

**作成日**: 2025-11-12
**Issue**: https://github.com/miyata09x0084/slide-pilot/issues/20
**ブランチ**: `feature/20-educational-theme`
**前提**: Slidev廃止、ブラウザレビュー専用への移行

---

## 🎯 実装方針

### 基本原則
各ステップで**必ず動作確認**してから次に進む。1ステップ=10-20分以内。

### アーキテクチャ
**既存**: ReactMarkdown + Mermaid によるブラウザプレビュー（Issue #24実装済み）
**追加**: 教育向けテーマシステム（カラーパレット、進捗バー、アニメーション）

```
LLM → Markdown生成（template_type付き）
         ↓
  Supabaseに保存（markdown + template_type）
         ↓
  ブラウザでプレビュー
    - テーマ別カラー適用
    - 進捗バー表示
    - <v-clicks>アニメーション
    - 絵文字強調表示
```

### Slidev廃止に伴う変更点
- ❌ **削除**: `slidev export`によるPDF生成（60秒タイムアウト問題あり）
- ✅ **継続**: MarkdownはSupabaseに保存（既存フロー維持）
- ✅ **新規**: ブラウザレンダリングのみ（PDF必要時は別途Puppeteer等で対応）

---

## 📋 Phase 1: フロントエンドテーマシステム（3-4時間）

### なぜ最初にやるか
- ✅ バックエンドに依存しない（独立してテスト可能）
- ✅ 視覚的インパクトが大きい（即座に効果確認可能）
- ✅ 既存スライドに即座に適用できる

---

### Step 1.1: テーマカラーパレット定義（15分）

**作業内容**:
`frontend/src/features/slide/components/SlideContentViewer.tsx`にテーマ定数を追加

```typescript
const THEME_COLORS = {
  science: {
    primary: '#4A90E2',
    secondary: '#5BC0EB',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    accent: '#9333ea'
  },
  story: {
    primary: '#F5A623',
    secondary: '#FDD835',
    gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    accent: '#ec4899'
  },
  math: {
    primary: '#7ED321',
    secondary: '#50E3C2',
    gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    accent: '#10b981'
  },
  default: {
    primary: '#6c757d',
    secondary: '#adb5bd',
    gradient: 'linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%)',
    accent: '#6b7280'
  }
};
```

**成功基準**:
- ✅ TypeScript型エラーなし
- ✅ `npm run dev`が正常起動

**確認方法**:
```bash
cd frontend
npm run dev
# ブラウザで http://localhost:5173 が表示されること
```

---

### Step 1.2: スライドカードへのグラデーション適用（20分）

**作業内容**:
1. `SlideContent`インターフェースに`template_type`を追加
2. `slideCard`スタイルに`background`プロパティを動的に適用

```typescript
interface SlideContent {
  slide_id: string;
  title: string;
  markdown: string;
  created_at: string;
  pdf_url?: string;
  template_type?: 'science' | 'story' | 'math' | 'default'; // ← 追加
}

// スライドカードのスタイル生成
const getSlideCardStyle = (templateType: string = 'default') => ({
  ...styles.slideCard,
  background: THEME_COLORS[templateType as keyof typeof THEME_COLORS]?.gradient || THEME_COLORS.default.gradient
});
```

**成功基準**:
- ✅ 既存スライド（`template_type`未設定）が`default`テーマで表示される
- ✅ コンソールエラーなし

**確認方法**:
1. 既存スライドを開く
2. スライドカード背景がグレーグラデーション（default）になること
3. DevToolsでCSSを確認: `background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%)`

---

### Step 1.3: 進捗バーコンポーネント作成（30分）

**作業内容**:
`frontend/src/features/slide/components/ProgressBar.tsx`を新規作成

```typescript
interface ProgressBarProps {
  current: number;
  total: number;
  themeColor: string;
}

export function ProgressBar({ current, total, themeColor }: ProgressBarProps) {
  const percentage = (current / total) * 100;

  return (
    <div style={styles.container}>
      <div style={styles.label}>
        {current} / {total}
      </div>
      <div style={styles.barBackground}>
        <div
          style={{
            ...styles.barFill,
            width: `${percentage}%`,
            background: themeColor
          }}
        />
      </div>
    </div>
  );
}

const styles = {
  container: {
    position: 'sticky' as const,
    top: 0,
    zIndex: 10,
    background: 'white',
    padding: '12px 24px',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    alignItems: 'center',
    gap: '16px'
  },
  label: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#333',
    minWidth: '60px'
  },
  barBackground: {
    flex: 1,
    height: '8px',
    background: '#e0e0e0',
    borderRadius: '4px',
    overflow: 'hidden'
  },
  barFill: {
    height: '100%',
    transition: 'width 0.3s ease-in-out',
    borderRadius: '4px'
  }
};
```

**成功基準**:
- ✅ TypeScript型エラーなし
- ✅ コンポーネントが単体でレンダリング可能

**確認方法**:
```bash
npm run dev
# エラーが出ないこと
```

---

### Step 1.4: 進捗バーの統合（20分）

**作業内容**:
`SlideContentViewer.tsx`に進捗バーを追加

```typescript
import { ProgressBar } from './ProgressBar';
import { useState } from 'react';

export function SlideContentViewer({ slideId }: SlideContentViewerProps) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const templateType = slide?.template_type || 'default';
  const themeColor = THEME_COLORS[templateType].primary;

  return (
    <div style={styles.container}>
      {/* 進捗バー */}
      <ProgressBar
        current={currentSlide + 1}
        total={slides.length}
        themeColor={themeColor}
      />

      {/* 既存のスライド表示 */}
      <div style={styles.slidesContainer}>
        {slides.map((slideContent, index) => (
          <div
            key={index}
            style={getSlideCardStyle(templateType)}
            ref={(el) => {
              // スクロール位置に応じて currentSlide を更新
              if (el) observeSlide(el, index, setCurrentSlide);
            }}
          >
            {/* 既存のコンテンツ */}
          </div>
        ))}
      </div>
    </div>
  );
}
```

**成功基準**:
- ✅ 進捗バーが上部に固定表示される
- ✅ スクロールしても進捗バーが追従する
- ✅ スライド位置に応じて進捗が更新される

**確認方法**:
1. スライドを開く
2. 上部に「1 / 12」のような進捗表示が出ること
3. スクロールすると現在位置が更新されること

---

### Step 1.5: 絵文字強調スタイル（30分）

**作業内容**:
1. 絵文字検出用の正規表現を追加
2. ReactMarkdownのカスタムコンポーネントで絵文字を`<span>`でラップ

```typescript
// 絵文字正規表現（Unicode範囲）
const EMOJI_REGEX = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu;

// テキストコンテンツを絵文字強調版に変換
function enhanceEmojis(text: string): React.ReactNode {
  if (typeof text !== 'string') return text;

  const parts = text.split(EMOJI_REGEX);
  const emojis = text.match(EMOJI_REGEX) || [];

  return parts.map((part, i) => (
    <React.Fragment key={i}>
      {part}
      {emojis[i] && (
        <span style={styles.emojiLarge}>{emojis[i]}</span>
      )}
    </React.Fragment>
  ));
}

// ReactMarkdownコンポーネント拡張
components={{
  h1: ({ children }) => (
    <h1 style={styles.h1}>{enhanceEmojis(String(children))}</h1>
  ),
  h2: ({ children }) => (
    <h2 style={styles.h2}>{enhanceEmojis(String(children))}</h2>
  ),
  li: ({ children }) => (
    <li style={styles.listItem}>{enhanceEmojis(String(children))}</li>
  ),
  // ... 他のコンポーネントも同様
}}

// スタイル追加
const styles = {
  // ... 既存スタイル
  emojiLarge: {
    fontSize: '1.5em',
    verticalAlign: 'middle',
    display: 'inline-block',
    margin: '0 4px'
  }
};
```

**成功基準**:
- ✅ 見出しと箇条書きの絵文字が1.5倍サイズになる
- ✅ 絵文字以外のテキストは通常サイズ
- ✅ レイアウト崩れなし

**確認方法**:
1. 絵文字を含むスライドを開く（例: 「🔬 科学実験」）
2. 🔬 が通常テキストより大きく表示されること
3. DevToolsで`<span class="emoji-large">`が適用されていること

---

### Step 1.6: Phase 1 動作確認（20分）

**確認項目**:
- [ ] テーマカラーパレットが定義されている
- [ ] スライドカードにグラデーション背景が適用される
- [ ] 進捗バーが上部に固定表示される
- [ ] スクロールで進捗が更新される
- [ ] 絵文字が1.5倍サイズで表示される
- [ ] 既存スライド（`template_type`未設定）が正常動作する

**テスト方法**:
```bash
# 1. 開発サーバー起動
cd frontend
npm run dev

# 2. ブラウザで既存スライドを開く
# http://localhost:5173/slides/{slide_id}

# 3. 目視確認
# - グラデーション背景: ✅ / ❌
# - 進捗バー: ✅ / ❌
# - 絵文字拡大: ✅ / ❌
```

**エラー時の対応**:
- スタイル崩れ → DevToolsでCSS確認、`!important`追加
- 進捗更新されない → IntersectionObserverのthreshold調整
- 絵文字検出失敗 → 正規表現のUnicodeフラグ確認

---

## 📋 Phase 2: `<v-clicks>`アニメーション対応（2-3時間）

### なぜ2番目にやるか
- ✅ Phase 1のテーマシステムが基盤になる
- ✅ インタラクティブ性を追加（教育効果向上）
- ✅ バックエンド変更不要（フロントエンドのみ）

---

### Step 2.1: VClicksAnimationコンポーネント作成（40分）

**作業内容**:
`frontend/src/features/slide/components/VClicksAnimation.tsx`を新規作成

```typescript
import { useState, useEffect, Children } from 'react';

interface VClicksAnimationProps {
  children: React.ReactNode;
  autoPlay?: boolean;
  interval?: number; // ms
}

export function VClicksAnimation({
  children,
  autoPlay = false,
  interval = 2000
}: VClicksAnimationProps) {
  const [visibleIndex, setVisibleIndex] = useState(0);
  const childArray = Children.toArray(children);

  // キーボード操作
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        setVisibleIndex(prev => Math.min(prev + 1, childArray.length));
      } else if (e.key === 'ArrowLeft') {
        setVisibleIndex(prev => Math.max(prev - 1, 0));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [childArray.length]);

  // 自動再生
  useEffect(() => {
    if (!autoPlay || visibleIndex >= childArray.length) return;

    const timer = setTimeout(() => {
      setVisibleIndex(prev => prev + 1);
    }, interval);

    return () => clearTimeout(timer);
  }, [autoPlay, interval, visibleIndex, childArray.length]);

  return (
    <div style={styles.container}>
      {childArray.map((child, index) => (
        <div
          key={index}
          style={{
            ...styles.item,
            opacity: index < visibleIndex ? 1 : 0.3,
            transition: 'opacity 0.3s ease-in-out'
          }}
        >
          {child}
        </div>
      ))}

      {/* 進捗インジケーター */}
      <div style={styles.indicator}>
        {visibleIndex} / {childArray.length}
      </div>
    </div>
  );
}

const styles = {
  container: {
    position: 'relative' as const
  },
  item: {
    marginBottom: '8px'
  },
  indicator: {
    marginTop: '16px',
    fontSize: '12px',
    color: '#999',
    textAlign: 'right' as const
  }
};
```

**成功基準**:
- ✅ TypeScript型エラーなし
- ✅ コンポーネントが単体でレンダリング可能
- ✅ キーボード操作が動作する

**確認方法**:
```tsx
// テスト用コード（App.tsxなどに一時追加）
<VClicksAnimation>
  <p>ステップ1</p>
  <p>ステップ2</p>
  <p>ステップ3</p>
</VClicksAnimation>

// キーボード操作:
// - 右矢印/スペース: 次の項目表示
// - 左矢印: 前の項目に戻る
```

---

### Step 2.2: Markdown内の`<v-clicks>`検出と変換（40分）

**作業内容**:
`SlideContentViewer.tsx`に`<v-clicks>`パース処理を追加

```typescript
import { VClicksAnimation } from './VClicksAnimation';

// Markdownから<v-clicks>ブロックを抽出
function parseVClicks(markdown: string): string {
  // <v-clicks>...</v-clicks> を特殊マーカーに置換
  return markdown.replace(
    /<v-clicks>([\s\S]*?)<\/v-clicks>/g,
    (match, content) => {
      // コンテンツをBase64エンコードして埋め込み
      const encoded = btoa(encodeURIComponent(content));
      return `<!-- V_CLICKS:${encoded} -->`;
    }
  );
}

// ReactMarkdownのカスタムコンポーネント
components={{
  // コメントノードを検出
  'html-comment': ({ value }: { value: string }) => {
    const match = value.match(/V_CLICKS:(.*)/);
    if (match) {
      const content = decodeURIComponent(atob(match[1]));
      const items = content.split('\n').filter(s => s.trim());

      return (
        <VClicksAnimation>
          {items.map((item, i) => (
            <div key={i} dangerouslySetInnerHTML={{ __html: item }} />
          ))}
        </VClicksAnimation>
      );
    }
    return null;
  },
  // ... 既存のコンポーネント
}}
```

**成功基準**:
- ✅ `<v-clicks>`タグが正しくパースされる
- ✅ アニメーション付きで表示される
- ✅ `<v-clicks>`以外のMarkdownは通常通り表示される

**確認方法**:
1. テスト用Markdownを作成:
```markdown
# テストスライド

<v-clicks>

- ステップ1: データ収集
- ステップ2: 前処理
- ステップ3: 学習

</v-clicks>
```

2. スライドプレビューで確認
3. 矢印キーで項目が順次表示されること

---

### Step 2.3: remarkプラグインでの`<v-clicks>`処理（30分）

**作業内容**:
remarkプラグインを作成して`<v-clicks>`を適切に処理

```typescript
import { visit } from 'unist-util-visit';
import type { Plugin } from 'unified';

// remark-v-clicksプラグイン
const remarkVClicks: Plugin = () => {
  return (tree) => {
    visit(tree, 'html', (node: any) => {
      if (node.value.includes('<v-clicks>')) {
        // v-clicksタグをカスタムコンポーネントに変換
        node.type = 'jsx';
        node.value = node.value
          .replace(/<v-clicks>/g, '<VClicksAnimation>')
          .replace(/<\/v-clicks>/g, '</VClicksAnimation>');
      }
    });
  };
};

// ReactMarkdownに適用
<ReactMarkdown
  remarkPlugins={[remarkGfm, remarkVClicks]}
  components={{
    VClicksAnimation: VClicksAnimation,
    // ... 既存のコンポーネント
  }}
>
  {slideContent}
</ReactMarkdown>
```

**成功基準**:
- ✅ `<v-clicks>`が正しくVClicksAnimationコンポーネントに変換される
- ✅ ネストした要素（箇条書き、段落）が保持される
- ✅ Markdownパースエラーなし

**確認方法**:
```bash
npm install unist-util-visit
npm run dev
# 既存のテストスライドでアニメーション確認
```

---

### Step 2.4: Phase 2 動作確認（20分）

**確認項目**:
- [ ] `<v-clicks>`タグが検出される
- [ ] 箇条書きが順次表示される
- [ ] キーボード操作（矢印キー/スペース）が動作する
- [ ] 進捗インジケーターが表示される
- [ ] `<v-clicks>`以外のコンテンツは通常表示される

**テスト用Markdown**:
```markdown
# アニメーションテスト

## ステップ1: 導入

<v-clicks>

- まず、問題を理解します 🤔
- 次に、解決策を考えます 💡
- 最後に、実装します ✅

</v-clicks>

## ステップ2: まとめ

通常のテキストはアニメーションなしで表示されます。
```

**エラー時の対応**:
- アニメーション動作しない → useEffectの依存配列確認
- キーボード操作無効 → イベントリスナーの登録確認
- パースエラー → remarkプラグインのAST変換確認

---

## 📋 Phase 3: バックエンド - テンプレート自動判定（2-3時間）

### なぜ3番目にやるか
- ✅ Phase 1, 2でフロントエンド基盤完成
- ✅ 手動で`template_type`設定すれば先に動作確認可能
- ✅ 自動判定は最適化フェーズ（必須ではない）

---

### Step 3.1: State拡張（10分）

**作業内容**:
`backend/app/agents/slide_workflow.py`の`State`に`template_type`を追加

```python
class State(TypedDict, total=False):
    # ... 既存フィールド

    # ══════════════════════════════════════════════════════════
    # テンプレート種別 (Phase 3: Issue #20)
    # ══════════════════════════════════════════════════════════
    template_type: str  # "science" | "story" | "math" | "default"
```

**成功基準**:
- ✅ TypeScript型エラーなし
- ✅ 既存ワークフローが正常動作（後方互換性）

**確認方法**:
```bash
cd backend/app
python3 -m pytest tests/ -v
# または既存スライド生成をテスト
```

---

### Step 3.2: テンプレート判定プロンプト作成（30分）

**作業内容**:
`backend/app/prompts/slide_prompts.py`に新規プロンプトを追加

```python
# =======================
# テンプレート種別判定（PDF用）
# =======================

TEMPLATE_SELECTION_SYSTEM = "あなたは教育コンテンツの分類専門家です。PDFの内容から最適な教育テンプレートを選びます。"

TEMPLATE_SELECTION_USER = """以下のPDF内容から、最適な教育テンプレート種別を1つ選んでください。

【PDF冒頭】
{first_chunk}

【重要ポイント】
{points_text}

【テンプレート種別】
- science: 科学実験、技術解説、観察記録、システム構成（キーワード: 実験、観察、分析、技術、プロセス、フロー）
- story: 歴史、物語、時系列イベント、人物紹介（キーワード: 歴史、出来事、人物、ストーリー、時代、影響）
- math: 数学、論理、証明、計算手順（キーワード: 数式、証明、定理、計算、論理、公式）
- default: 上記に該当しない一般的な内容

【出力形式】
JSONで以下の形式で返してください:
{{
  "template_type": "science" | "story" | "math" | "default",
  "reason": "選択理由（1文）"
}}

判定理由を含めて出力してください:"""


def get_template_selection_prompt(
    chunks: List[str],
    key_points: List[str]
) -> List[Tuple[str, str]]:
    """PDFからテンプレート種別を判定

    Args:
        chunks: PDFチャンクのリスト
        key_points: 重要ポイントのリスト（最大3個使用）

    Returns:
        LLMプロンプト（system, user）のタプルリスト
    """
    first_chunk = chunks[0][:2000] if chunks else '内容なし'
    points_text = "\n".join([f"- {kp}" for kp in key_points[:3]])

    return [
        ("system", TEMPLATE_SELECTION_SYSTEM),
        ("user", TEMPLATE_SELECTION_USER.format(
            first_chunk=first_chunk,
            points_text=points_text
        ))
    ]
```

**成功基準**:
- ✅ Python構文エラーなし
- ✅ 型ヒントが正しい

**確認方法**:
```bash
cd backend/app
python3 -c "from prompts.slide_prompts import get_template_selection_prompt; print('OK')"
```

---

### Step 3.3: テンプレート判定ノード追加（40分）

**作業内容**:
`backend/app/agents/slide_workflow.py`に新規ノードを追加

```python
from app.prompts.slide_prompts import get_template_selection_prompt

# -------------------
# Node B.5: テンプレート種別判定（Issue #20）
# -------------------
@traceable(run_name="b5_select_template")
def select_template(state: State) -> Dict:
    """PDF内容からテンプレート種別を判定"""
    topic = state.get("topic", "")
    input_type = detect_input_type(topic)

    # PDF以外はデフォルトテンプレート
    if input_type != "pdf":
        return {
            "template_type": "default",
            "log": _log(state, "[template] text/youtube → default")
        }

    # PDFの場合は内容から判定
    sources = state.get("sources") or {}
    key_points = state.get("key_points") or []

    try:
        pdf_data = sources.get("pdf_content", [{}])[0]
        chunks = pdf_data.get("chunks", [])

        if not chunks:
            return {
                "template_type": "default",
                "log": _log(state, "[template] no chunks → default")
            }

        # LLMでテンプレート判定
        prompt = get_template_selection_prompt(
            chunks=chunks,
            key_points=key_points
        )

        msg = llm.invoke(prompt)
        raw = msg.content or ""
        js = _find_json(raw) or raw
        data = json.loads(js)

        template_type = data.get("template_type", "default")
        reason = data.get("reason", "")

        # バリデーション
        valid_types = ["science", "story", "math", "default"]
        if template_type not in valid_types:
            template_type = "default"

        return {
            "template_type": template_type,
            "log": _log(state, f"[template] {template_type} (reason: {reason})")
        }

    except Exception as e:
        return {
            "template_type": "default",
            "error": f"template_selection_error: {e}",
            "log": _log(state, f"[template] EXCEPTION {e} → default")
        }
```

**成功基準**:
- ✅ ノードが正常に実行される
- ✅ `template_type`が正しく返される
- ✅ エラー時に`default`にフォールバックする

**確認方法**:
```python
# テスト実行
if __name__ == "__main__":
    test_state: State = {
        "topic": "/path/to/test.pdf",
        "sources": {
            "pdf_content": [{
                "chunks": ["実験手順: 1. サンプル準備 2. 観察 3. 記録"]
            }]
        },
        "key_points": ["実験プロセスの理解", "観察方法の習得"]
    }

    result = select_template(test_state)
    print(result["template_type"])  # 期待値: "science"
```

---

### Step 3.4: ワークフローへのノード統合（20分）

**作業内容**:
`slide_workflow.py`のグラフにノードを追加

```python
# グラフ構築
graph_builder = StateGraph(State)
graph_builder.add_node("collect_info", collect_info)
graph_builder.add_node("generate_key_points", generate_key_points)
graph_builder.add_node("select_template", select_template)  # ← 追加
graph_builder.add_node("generate_toc", generate_toc)
# ... 既存ノード

# エッジ定義
graph_builder.add_edge(START, "collect_info")
graph_builder.add_edge("collect_info", "generate_key_points")
graph_builder.add_edge("generate_key_points", "select_template")  # ← 追加
graph_builder.add_edge("select_template", "generate_toc")  # ← 変更
# ... 既存エッジ
```

**成功基準**:
- ✅ グラフのコンパイルエラーなし
- ✅ ワークフローが正常実行される
- ✅ Stateに`template_type`が保存される

**確認方法**:
```bash
cd backend/app
python3 agents/slide_workflow.py
# ログに [template] science などが出力されること
```

---

### Step 3.5: YAMLフロントマターへの埋め込み（30分）

**作業内容**:
`write_slides_slidev`ノードでYAMLフロントマターに`template_type`を追加

```python
@traceable(run_name="d_generate_slide_slidev")
def write_slides_slidev(state: State) -> Dict:
    """Slidev形式のスライドを生成（テンプレート対応）"""
    # ... 既存の処理

    template_type = state.get("template_type", "default")

    # LLMでスライド生成
    msg = llm.invoke(prompt)
    slide_md = msg.content.strip()

    # コードブロック除去
    slide_md = _strip_whole_code_fence(slide_md)

    # YAMLフロントマターにtemplate_typeを追加
    if slide_md.startswith("---"):
        # 既存のフロントマターに追加
        frontmatter_end = slide_md.find("---", 3)
        if frontmatter_end > 0:
            frontmatter = slide_md[3:frontmatter_end]
            frontmatter += f"\ntemplate_type: {template_type}\n"
            slide_md = f"---{frontmatter}---{slide_md[frontmatter_end+3:]}"
    else:
        # フロントマターを新規作成
        frontmatter = f"""---
theme: apple-basic
template_type: {template_type}
---

"""
        slide_md = frontmatter + slide_md

    return {
        "slide_md": slide_md,
        "title": ja_title,
        "error": "",
        "log": _log(state, f"[slides_slidev] template={template_type}")
    }
```

**成功基準**:
- ✅ 生成されたMarkdownにYAMLフロントマターが含まれる
- ✅ `template_type`フィールドが正しい値
- ✅ Slidevパースエラーなし

**確認方法**:
1. スライド生成を実行
2. 生成されたMarkdownを確認:
```markdown
---
theme: apple-basic
template_type: science
---

# 🔬 科学実験スライド
...
```

---

### Step 3.6: Supabase保存時のメタデータ追加（20分）

**作業内容**:
`backend/app/core/supabase.py`の`save_slide_to_supabase`に`template_type`を追加

```python
def save_slide_to_supabase(
    user_id: str,
    title: str,
    topic: str,
    slide_md: str,
    pdf_url: Optional[str] = None,
    template_type: str = "default"  # ← 追加
) -> Dict[str, Any]:
    """スライドをSupabase DBに保存

    Args:
        template_type: テンプレート種別（science/story/math/default）
    """
    # ... 既存の処理

    slide_data = {
        "user_id": user_id,
        "title": title,
        "topic": topic,
        "markdown": slide_md,
        "pdf_url": pdf_url,
        "template_type": template_type  # ← 追加
    }

    result = supabase.table("slides").insert(slide_data).execute()
    # ... 残りの処理
```

**成功基準**:
- ✅ Supabaseのslidesテーブルに`template_type`カラムが存在する
- ✅ データが正常に保存される

**確認方法**:
```sql
-- Supabase SQLエディタで確認
SELECT id, title, template_type FROM slides ORDER BY created_at DESC LIMIT 5;
```

---

### Step 3.7: Phase 3 動作確認（20分）

**確認項目**:
- [ ] PDFアップロード → テンプレート自動判定される
- [ ] 判定結果がログに出力される（`[template] science`など）
- [ ] YAMLフロントマターに`template_type`が含まれる
- [ ] Supabaseに`template_type`が保存される
- [ ] フロントエンドで適切なテーマが適用される

**テストシナリオ**:
1. 科学実験系PDF（例: "AI学習プロセス.pdf"）をアップロード
   - 期待値: `template_type: science`（青紫グラデーション）

2. 歴史系PDF（例: "インターネット発展史.pdf"）をアップロード
   - 期待値: `template_type: story`（オレンジグラデーション）

3. 数学系PDF（例: "統計学入門.pdf"）をアップロード
   - 期待値: `template_type: math`（緑グラデーション）

**エラー時の対応**:
- 判定が常に`default` → LLMプロンプトのキーワード見直し
- YAML構文エラー → インデント確認、エスケープ処理
- Supabase保存失敗 → カラム型確認（VARCHAR(20)）

---

## 📋 Phase 4: プロンプト強化（1-2時間）

### Step 4.1: 絵文字活用指示の追加（20分）

**作業内容**:
`backend/app/prompts/slide_prompts.py`の`SLIDE_PDF_USER`を更新

```python
SLIDE_PDF_USER = """以下のPDF内容（抜粋）から、中学生向けのわかりやすいスライドを作成してください。

【PDF内容（セクション別抜粋）】
{full_summary}

【重要ポイント】
{points_text}

【目次】
{toc_text}

【基本要件】
- Slidev形式（YAMLフロントマター + Markdown）
- theme: apple-basic を使用
- タイトルスライド: # {ja_title}
- Agendaスライド: 目次を箇条書きで表示（<v-clicks>は使わない）
- 各セクション: 目次に基づいて5-8スライド作成
- 各スライドは簡潔に（1スライド1メッセージ）
- 中学生でもわかる言葉で説明
- まとめスライド: 【重要ポイント】で示した5個すべてを箇条書きで表示

【絵文字要件】★強化
- **見出し**: 各セクション見出しに関連絵文字を必ず付ける
  - 科学: 🔬 🧪 📊 🔍 ⚗️ 🧬 💡
  - 歴史: 📚 🏛️ 🗺️ ⏳ 👤 🌍 📜
  - 数学: 📐 📏 🧮 ➗ ➕ ✖️ 📈
  - 一般: ✅ ❌ ⚠️ 💡 🎯 🚀 ⭐
- **箇条書き**: 重要な箇条書きの先頭に絵文字
- **頻度**: 5個以上の絵文字を使用すること

【`<v-clicks>`アニメーション要件】★新規
- **3個以上の箇条書き**: 必ず`<v-clicks>`で囲む

  <v-clicks>

  - ✅ ステップ1: データ収集
  - 📊 ステップ2: 前処理
  - 🚀 ステップ3: 学習

  </v-clicks>

- **段階的説明**: 図解の後に説明を追加する場合も`<v-clicks>`使用
- **対話形式**: 質問と回答を別々の`<v-clicks>`に分離

【Mermaid図解の要件】
- **Agenda直後**: PDFの内容に応じた独自の技術フロー図またはアーキテクチャ図を作成
- **まとめ直前**: PDFの内容に応じた独自の活用例図または概念整理図を作成
- **図の種類**: flowchart, mindmap, sequenceDiagram等、内容に最適な形式を選択
- **必須**: 各図の直後に「**この図は〜を示しています**」形式の説明文を追加

出力はSlidevマークダウンのみ（コードブロック不要）:"""
```

**成功基準**:
- ✅ プロンプトに絵文字・アニメーション要件が明記される
- ✅ Python構文エラーなし

---

### Step 4.2: テンプレート別プロンプトの追加（30分）

**作業内容**:
テンプレート種別ごとに専用プロンプトを作成

```python
# =======================
# テンプレート別スライド生成プロンプト
# =======================

SLIDE_PDF_SCIENCE_EXTRA = """
【科学実験テンプレート追加要件】
- **実験手順**: 番号付きリストで明確に
- **観察結果**: 表やグラフで視覚化（Markdown table使用）
- **考察**: 「なぜ？」を考えさせる質問形式
- **絵文字**: 🔬 🧪 📊 🔍 を積極的に使用
"""

SLIDE_PDF_STORY_EXTRA = """
【歴史物語テンプレート追加要件】
- **時系列**: 年表形式で整理（タイムライン風）
- **人物紹介**: 名前・役割・功績を簡潔に
- **影響**: 「その後どうなった？」を説明
- **絵文字**: 📚 🏛️ 🗺️ ⏳ を積極的に使用
"""

SLIDE_PDF_MATH_EXTRA = """
【数学概念テンプレート追加要件】
- **問題提起**: 「こんな場面で使うよ」から始める
- **解法手順**: ステップバイステップで図解
- **例題**: 具体的な数値で練習問題
- **絵文字**: 📐 📏 🧮 ➗ を積極的に使用
"""


def get_slide_pdf_prompt(
    full_summary: str,
    key_points: List[str],
    toc: List[str],
    ja_title: str,
    template_type: str = "default"  # ← 追加
) -> List[Tuple[str, str]]:
    """PDF用Slidevスライド生成プロンプト（テンプレート対応）"""
    points_text = "\n".join([f"- {kp}" for kp in key_points[:5]])
    toc_text = "\n".join([f"- {t}" for t in toc[:8]])

    # テンプレート別の追加要件
    extra_requirements = {
        "science": SLIDE_PDF_SCIENCE_EXTRA,
        "story": SLIDE_PDF_STORY_EXTRA,
        "math": SLIDE_PDF_MATH_EXTRA,
    }.get(template_type, "")

    user_prompt = SLIDE_PDF_USER.format(
        full_summary=full_summary,
        points_text=points_text,
        toc_text=toc_text,
        ja_title=ja_title
    ) + extra_requirements

    return [
        ("system", SLIDE_PDF_SYSTEM),
        ("user", user_prompt)
    ]
```

**成功基準**:
- ✅ テンプレート種別に応じたプロンプトが生成される
- ✅ `template_type`未指定時はデフォルト動作

**確認方法**:
```python
# テスト
prompt = get_slide_pdf_prompt(
    full_summary="...",
    key_points=["..."],
    toc=["..."],
    ja_title="科学実験",
    template_type="science"
)

print(prompt[1][1])  # 科学実験テンプレート要件が含まれること
```

---

### Step 4.3: `write_slides_slidev`でのプロンプト切り替え（15分）

**作業内容**:
`slide_workflow.py`の`write_slides_slidev`ノードを更新

```python
@traceable(run_name="d_generate_slide_slidev")
def write_slides_slidev(state: State) -> Dict:
    # ... 既存の処理

    template_type = state.get("template_type", "default")

    # テンプレート対応プロンプトを使用
    prompt = get_slide_pdf_prompt(
        full_summary=full_summary,
        key_points=key_points,
        toc=toc,
        ja_title=ja_title,
        template_type=template_type  # ← 追加
    )

    msg = llm.invoke(prompt)
    slide_md = msg.content.strip()
    # ... 残りの処理
```

**成功基準**:
- ✅ テンプレート種別に応じたスライドが生成される
- ✅ 絵文字が5個以上含まれる
- ✅ `<v-clicks>`が3箇所以上含まれる

---

### Step 4.4: Phase 4 動作確認（15分）

**確認項目**:
- [ ] 科学実験PDFで実験手順が番号付きリストになる
- [ ] 歴史PDFで時系列が明確に示される
- [ ] 数学PDFで例題が含まれる
- [ ] すべてのスライドに絵文字が5個以上ある
- [ ] 箇条書きに`<v-clicks>`が使用される

**テスト方法**:
```bash
# 1. スライド生成
curl -X POST http://localhost:8001/api/upload-pdf -F "file=@test_science.pdf"

# 2. 生成されたMarkdownを確認
# - 絵文字数: grep -o "🔬\|🧪\|📊" slide.md | wc -l
# - <v-clicks>数: grep -c "<v-clicks>" slide.md
```

---

## 📋 Phase 5: 評価基準アップデート（1時間）

### Step 5.1: `visual_appeal`評価軸の追加（30分）

**作業内容**:
`backend/app/prompts/evaluation_prompts.py`を更新

```python
EVAL_PDF_GUIDE = """評価観点と重み:
- structure(0.15): スライドの流れ、章立て、1スライド1メッセージ
- comprehensiveness(0.25): PDF全体の重要トピックをカバー + **Mermaid図解による情報量強化**
- clarity(0.20): 中学生にもわかる説明 + **図解による視覚的理解**
- readability(0.15): 簡潔明瞭、視認性
- engagement(0.15): <v-clicks>活用、ストーリー性
- visual_appeal(0.10): 絵文字活用、カラフルさ、テンプレート適合度  # ← 新規
合格: score >= 8.0

【visual_appeal評価基準】★新規
1. **絵文字活用度** (0.4点)
   - ✅ 絵文字5個以上使用: +0.4点
   - ⚠️ 絵文字3-4個: +0.2点
   - ❌ 絵文字2個以下: 0点

2. **アニメーション活用度** (0.3点)
   - ✅ <v-clicks>が3箇所以上: +0.3点
   - ⚠️ <v-clicks>が1-2箇所: +0.15点
   - ❌ <v-clicks>なし: 0点

3. **テンプレート適合度** (0.3点)
   - ✅ template_typeがPDF内容と一致し、テンプレート要件を満たす: +0.3点
   - ⚠️ template_typeは一致するが要件不足: +0.15点
   - ❌ template_typeが不適切: 0点

【Mermaid図解評価】
以下の基準でMermaid図解を評価:
1. **独自性と関連性** (comprehensiveness/engagement への加点)
   - ✅ PDFのトピック/内容に応じた独自の図解: +0.5点
   - ✅ Agenda直後またはまとめ直前に配置され、内容と関連: +0.3点
   - ❌ 汎用的すぎる図: 加点なし
2. **図解の種類と用途**
   - flowchart: 技術フロー、プロセス、アーキテクチャ
   - mindmap: 概念整理、活用例、分類
   - sequenceDiagram: 時系列の処理、対話フロー
3. **品質基準**
   - ✅ Mermaid構文が正しい
   - ✅ 図解の直後に説明文がある
   - ✅ PDFの具体的な内容を反映している
"""
```

**成功基準**:
- ✅ 評価軸が6つになる（structure, comprehensiveness, clarity, readability, engagement, visual_appeal）
- ✅ 重みの合計が1.0（0.15+0.25+0.20+0.15+0.15+0.10=1.0）

---

### Step 5.2: 評価JSONスキーマの更新（15分）

**作業内容**:
`evaluation_prompts.py`のユーザープロンプトを更新

```python
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
  "subscores": {{
    "structure": number,
    "comprehensiveness": number,
    "clarity": number,
    "readability": number,
    "engagement": number,
    "visual_appeal": number  // ← 追加
  }},
  "reasons": {{
    "structure": string,
    "comprehensiveness": string,
    "clarity": string,
    "readability": string,
    "engagement": string,
    "visual_appeal": string  // ← 追加
  }},
  "suggestions": [string],
  "risk_flags": [string],
  "pass": boolean,
  "feedback": string
}}"""
```

**成功基準**:
- ✅ JSONスキーマが正しい
- ✅ `visual_appeal`フィールドが含まれる

---

### Step 5.3: Phase 5 動作確認（15分）

**確認項目**:
- [ ] 評価時に`visual_appeal`スコアが計算される
- [ ] 絵文字数・アニメーション数が評価に反映される
- [ ] テンプレート適合度が評価される
- [ ] 総合スコアが正しく計算される（重み付き平均）

**テスト方法**:
```python
# テストスライド生成 → 評価実行
# ログで確認:
# [evaluate_slidev] score=8.5 pass=True
# subscores={'visual_appeal': 0.9, ...}
```

---

## 📊 全体の成功基準

### 最終確認チェックリスト

#### フロントエンド
- [ ] テーマカラーパレットが定義されている
- [ ] スライドカードにテーマ別グラデーションが適用される
- [ ] 進捗バーが上部に固定表示される
- [ ] スクロールで進捗が更新される
- [ ] 絵文字が1.5倍サイズで表示される
- [ ] `<v-clicks>`でアニメーション表示される
- [ ] キーボード操作（矢印キー/スペース）が動作する

#### バックエンド
- [ ] PDFからテンプレート種別が自動判定される
- [ ] YAMLフロントマターに`template_type`が含まれる
- [ ] Supabaseに`template_type`が保存される
- [ ] テンプレート別プロンプトが適用される
- [ ] 絵文字が5個以上含まれる
- [ ] `<v-clicks>`が3箇所以上含まれる
- [ ] `visual_appeal`評価軸が動作する

#### 統合テスト
- [ ] 科学実験PDF → 青紫テーマ + 実験手順番号付き
- [ ] 歴史PDF → オレンジテーマ + 時系列表示
- [ ] 数学PDF → 緑テーマ + 例題含む
- [ ] 評価ループで8.0以上のスコア取得
- [ ] ブラウザプレビューでテーマが正しく表示される

---

## ⚠️ エラー時の対応

### フロントエンド
| エラー | 原因 | 対処法 |
|--------|------|--------|
| テーマが適用されない | `template_type`未取得 | APIレスポンス確認、デフォルト値設定 |
| 進捗バーが表示されない | `position: sticky`未対応 | `position: fixed`に変更 |
| アニメーション動作しない | イベントリスナー未登録 | useEffectの依存配列確認 |
| 絵文字が拡大されない | 正規表現マッチ失敗 | Unicodeフラグ(`u`)確認 |

### バックエンド
| エラー | 原因 | 対処法 |
|--------|------|--------|
| テンプレート判定が`default`のみ | LLMプロンプト不適切 | キーワードを追加、例示を増やす |
| YAML構文エラー | インデント不正 | YAMLパース処理を追加 |
| 評価スコアが低い | 要件未達成 | プロンプトを強化、例示を追加 |
| Supabase保存失敗 | カラム未存在 | マイグレーション実行 |

---

## 🚀 デプロイ準備

### 本番環境での注意点
1. **Supabaseマイグレーション**
   ```sql
   ALTER TABLE slides ADD COLUMN template_type VARCHAR(20) DEFAULT 'default';
   CREATE INDEX idx_slides_template_type ON slides(template_type);
   ```

2. **環境変数確認**
   - `OPENAI_API_KEY`: GPT-4アクセス権限
   - `SUPABASE_URL`, `SUPABASE_KEY`: 本番環境の認証情報

3. **フロントエンドビルド**
   ```bash
   cd frontend
   npm run build
   # dist/をFirebase Hostingにデプロイ
   ```

4. **Cloud Run再デプロイ**
   ```bash
   cd backend
   gcloud run deploy slide-pilot-backend --source .
   ```

---

## 📝 実装後のドキュメント更新

実装完了後、以下を更新:
- [ ] `CLAUDE.md` - 教育テーマシステムの説明追加
- [ ] `README.md` - スクリーンショット更新
- [ ] Issue #20をクローズ
- [ ] Pull Requestを作成（このドキュメントをリンク）

---

## 📚 参考資料

- [Issue #20](https://github.com/miyata09x0084/slide-pilot/issues/20) - 元Issue
- [Issue #24](https://github.com/miyata09x0084/slide-pilot/issues/24) - ブラウザプレビュー基盤
- [ReactMarkdown公式ドキュメント](https://github.com/remarkjs/react-markdown)
- [Mermaid公式ドキュメント](https://mermaid.js.org/)
- [Slidev公式ドキュメント](https://sli.dev/) - 参考（廃止予定）
