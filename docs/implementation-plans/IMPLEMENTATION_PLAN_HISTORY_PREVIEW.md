# Implementation Plan: スライド履歴プレビュー機能 + user_id 問題修正

## 概要

**目的**: Supabase に保存されたスライド履歴をトップページから閲覧可能にし、かつ`user_id`が"anonymous"になる問題を修正する。

**関連 Issue**: (未作成 - このドキュメント作成後に Issue 登録推奨)

**ブランチ**: `feature/slide-history-preview`

---

## 背景と問題

### 現状

- ✅ Supabase 統合済み（`backend/app/core/supabase.py`）
- ✅ スライドリスト取得 API 実装済み（`GET /api/slides?user_id={email}`）
- ✅ Markdown 取得 API 実装済み（`GET /api/slides/{slide_id}/markdown`）
- ✅ `SlideViewer`コンポーネント実装済み（チャット画面のみ）

### 問題 1: user_id が"anonymous"になる

**症状**: Supabase の`slides`テーブルに登録される`user_id`が全て"anonymous"になっている

**根本原因（デバッグ結果）**:

#### 試行錯誤1: RunnableConfig経由（失敗）
```
agent.py: body["config"]["configurable"]["user_id"] = x_user_email
↓
LangGraph API: config渡す
↓
create_react_agent: ツールにconfigを渡さない ❌
```
**理由**: `create_react_agent`は`@tool`デコレータで定義されたツールに自動的に`config`を渡す機能がない。

#### 試行錯誤2: contextvars使用（失敗）
```
agent.py (PID: 94982): current_user_id.set("user@example.com")
↓ HTTPリクエスト（別プロセスへ）
LangGraph (PID: 94947): current_user_id.get() → "anonymous" ❌
```
**理由**: **FastAPI (port 8001) と LangGraph (port 2024) は別のPythonプロセス**で動作している。contextvarはプロセス内変数のため、プロセス間では値が共有されない。

```
FastAPI プロセス (PID: 94982)
  ├─ agent.py
  └─ current_user_id.set("user@example.com") ← ここでセット

（HTTPリクエスト経由で通信）

LangGraph プロセス (PID: 94947)
  ├─ react_agent.py
  ├─ tools/slides.py
  └─ current_user_id.get() → "anonymous" ← 別プロセスなので取得できない！
```

#### 最終解決策: InjectedState（LangGraph公式パターン）

LangGraphの標準パターンに従い、ReActエージェントの`State`に`user_id`フィールドを追加し、
ツール側で`InjectedState`アノテーションを使用してLangGraphに自動注入させる。

**重要**: システムプロンプトでLLMに`user_id=state.user_id`を渡すよう指示すると、
LLMは文字列リテラル`"state.user_id"`をツール引数として渡してしまう。
LangGraphの`create_react_agent`では、LLMはStateに直接アクセスできない。

**正しいデータフロー**:

```
フロントエンド
  ↓ X-User-Email ヘッダー
FastAPI (agent.py)
  ↓ body["input"]["user_id"] = x_user_email
LangGraph API
  ↓ CustomState(messages=[...], user_id="user@example.com")
ReActエージェント (LLM)
  ↓ generate_slides(topic="AI最新情報") ← user_idは渡さない
LangGraph ToolNode
  ↓ InjectedStateアノテーションを検出し、state["user_id"]を自動注入
generate_slides ツール
  ↓ state: Annotated[dict, InjectedState]
  ↓ user_id = state.get("user_id", "anonymous")
slide_workflow
  ↓ init_state["user_id"] = user_id
  ↓ Supabase保存: user_id="user@example.com" ✅
```

**参考ドキュメント**:
- [LangGraph InjectedState API Reference](https://langchain-ai.github.io/langgraph/reference/agents/)
- [Add context - LangGraph](https://langchain-ai.github.io/langgraph/agents/context/)

**データフロー図**:

```
[Frontend]
  localStorage.getItem('user') → { email: "user@example.com" }
  ↓
  fetch("/api/agent/threads/{id}/runs/stream", {
    headers: { "X-User-Email": "user@example.com" }
  })
  ↓
[Backend: agent.py]
  x_user_email = Header("X-User-Email")
  body["input"]["user_id"] = x_user_email  ← ここまでOK
  ↓
[LangGraph: ReActエージェント]
  MessagesState: { messages: [...] }
  ↓ LLMがgenerate_slidesツールを選択
[Tool: slides.py]
  @tool
  def generate_slides(topic: str):
    init_state = {"topic": topic, ...}  ← user_idが欠落！❌
    result = graph.invoke(init_state)
  ↓
[Workflow: slide_workflow.py]
  save_and_render_slidev(state):
    user_id = state.get("user_id", "anonymous")  ← "anonymous"になる
```

### 問題 2: 履歴表示機能がない

現在、スライド生成後に再度アクセスする手段がなく、ユーザーは過去のスライドを確認できない。

---

## 実装方針

### Phase 1: user_id 問題の修正（優先度: 高）

**方針**: `generate_slides`ツールの`init_state`に`user_id`を含める

**検討したアプローチ**:

| アプローチ                                          | メリット                                   | デメリット                            | 採用 |
| --------------------------------------------------- | ------------------------------------------ | ------------------------------------- | ---- |
| 1. ツール引数に追加 (`topic, user_id`)              | シンプル                                   | LLMが文字列リテラルを渡してしまう     | ❌   |
| 2. **InjectedState（LangGraph公式パターン）**       | LLMスキーマから除外、自動注入、公式サポート | なし                                  | ✅   |
| 3. RunnableConfig 経由                              | LangGraph標準の設計パターン                | 実装複雑度が高い、create_react_agent対応不明 | △    |
| 4. 環境変数/グローバル変数                          | 即座に実装可能                             | マルチユーザー環境で不適切            | ❌   |

**採用方針**: アプローチ2（InjectedState）を採用

**理由**:
- LangGraph公式ドキュメントで推奨されているパターン
- `create_react_agent`と完全に互換性がある
- LLMのツールスキーマから`state`パラメータが自動的に除外される
- ToolNodeが実行時に自動的に注入するため、LLMの誤動作がない

### Phase 2: 履歴表示機能の実装（優先度: 中）

**方針**: 既存の`SlideViewer`を再利用し、トップページに履歴セクションを追加

---

## Phase 1: user_id 問題の修正（最終版）

### ステップ 1.1: `react_agent.py` - State拡張

**ファイル**: `backend/app/agents/react_agent.py`

**変更内容**:

```python
# 修正前
from langgraph.graph import MessagesState

graph = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
```

```python
# 修正後
from langgraph.graph import MessagesState
from typing_extensions import TypedDict

# MessagesStateを拡張してuser_idフィールド追加
class State(MessagesState):
    user_id: str  # ユーザー識別子（デフォルト: "anonymous"）

graph = create_react_agent(
    llm,
    tools,
    prompt=SYSTEM_PROMPT,
    state_schema=State  # カスタムStateを指定
)
```

**システムプロンプト更新（重要）**:

```python
SYSTEM_PROMPT = """あなたは親切なAIアシスタントです。

ユーザーの要望に応じて、以下のツールを使用できます:
- **send_gmail**: メール送信（添付ファイル対応）
- **generate_slides**: スライド自動生成（PDF/YouTube/AI最新情報対応）
  - 引数: topic のみを指定してください
  - user_idは自動的にLangGraphから注入されます（明示的に渡す必要はありません）
  - 入力タイプ（PDF/YouTube/テキスト）は自動判別されます

## 重要な指示

1. **入力タイプの自動判別**
   - PDFファイルパス → generate_slidesにそのまま渡す
   - YouTube URL → generate_slidesにそのまま渡す
   - テキスト → generate_slidesにそのまま渡す

2. **user_idについて**
   - **generate_slidesにuser_idを渡してはいけません**
   - user_idはLangGraphが自動的に注入します

## 実行例

ユーザー: 「AI最新情報のスライドを作って」
→ generate_slides(topic="AI最新情報")  ← user_idは渡さない

ユーザー: 「このPDFからスライドを作成: /path/to/file.pdf」
→ generate_slides(topic="/path/to/file.pdf")  ← user_idは渡さない
"""
```

**理由**: LLMに`user_id=state.user_id`を渡すよう指示すると、LLMは文字列リテラル`"state.user_id"`を渡してしまう。
InjectedStateはLangGraphのToolNodeが自動的に注入するため、LLMは関与しない。

### ステップ 1.2: `routers/agent.py` - input にuser_id追加

**ファイル**: `backend/app/routers/agent.py`

**変更内容**:

```python
# contextvarsのimport削除
# from app.tools.slides import current_user_id  # 削除

# user_idをinputに追加
if x_user_email:
    if "input" not in body:
        body["input"] = {}
    body["input"]["user_id"] = x_user_email
    print(f"[agent] Injected user_id={x_user_email} into input")
```

### ステップ 1.3: `tools/slides.py` - InjectedState追加

**ファイル**: `backend/app/tools/slides.py`

**変更内容**:

```python
# 追加: InjectedStateのインポート
from typing_extensions import Annotated
from langgraph.prebuilt import InjectedState

@tool
def generate_slides(
    topic: str = "AI最新情報",
    state: Annotated[dict, InjectedState] = None  # ← InjectedState追加
) -> str:
    """スライドを生成（PDF/YouTube/テキスト対応）

    入力に応じて自動的に処理方法を切り替えます:
    - PDF: PDFファイルからテキスト抽出してスライド生成
    - YouTube URL: 字幕取得してスライド生成（準備中）
    - テキスト: Tavily検索でAI最新情報を収集してスライド生成

    Args:
        topic: スライドのトピック
        state: LangGraphから自動注入されるState（user_id含む）
              このパラメータはLLMのツールスキーマから除外される

    Returns:
        str: 生成結果（JSON形式）
    """

    # user_idを取得（InjectedStateから）
    user_id = state.get("user_id", "anonymous") if state else "anonymous"
    print(f"[generate_slides] topic={topic[:50]}, user_id={user_id}")

    init_state: State = {
        "topic": topic,
        "user_id": user_id,  # ← Stateから取得した値を設定
        "key_points": [],
        "toc": [],
        ...
    }

    result = graph.invoke(init_state)
    # ... 以降は既存のまま
```

**重要**:
- `InjectedState`アノテーションにより、`state`パラメータはLLMのツールスキーマから除外される
- LangGraphのToolNodeが実行時に自動的に`state`引数を注入する
- LLMは`generate_slides(topic="...")`のみを実行し、`user_id`は渡さない

**参考**: [LangGraph InjectedState API](https://langchain-ai.github.io/langgraph/reference/agents/)

### ステップ 1.4: テストと検証

**テスト手順**:

1. バックエンド起動:
   ```bash
   cd backend/app
   python3 main.py  # FastAPI (port 8001)
   ```

2. 別ターミナルでLangGraph起動（**重要**: state_schema変更を反映するため必ず再起動）:
   ```bash
   cd backend
   python3.11 -m langgraph_cli dev --host 0.0.0.0 --port 2024
   ```

3. フロントエンド起動:
   ```bash
   cd frontend
   npm run dev
   ```

4. ブラウザでログイン → PDF アップロード → スライド生成

5. ログ確認（ターミナル）:
   ```
   [agent] Injected user_id=user@example.com into input
   [generate_slides] topic=AI最新情報, user_id=user@example.com
   ```

6. Supabase ダッシュボードで確認:
   ```sql
   SELECT id, user_id, title, created_at
   FROM slides
   ORDER BY created_at DESC
   LIMIT 5;
   ```

**期待結果**:
- ✅ `user_id`が Google アカウントのメールアドレスになっている
- ❌ `user_id`が`"state.user_id"`や`"anonymous"`になっていない

**失敗時のデバッグ**:

1. **user_idが"state.user_id"のまま**
   - 原因: システムプロンプトに`user_id=state.user_id`の指示が残っている
   - 対処: react_agent.pyのSYSTEM_PROMPTを確認し、user_id引数の指示を完全削除

2. **user_idが"anonymous"のまま**
   - 原因: InjectedStateが正しく動作していない
   - 対処:
     - `langgraph.prebuilt.InjectedState`のインポートを確認
     - `state: Annotated[dict, InjectedState]`のアノテーション構文を確認
     - LangGraphサーバーを再起動（state_schema変更の反映）

3. **ツール実行時にエラー**
   - 原因: InjectedStateのデフォルト値が設定されていない
   - 対処: `state: Annotated[dict, InjectedState] = None`のように`= None`を追加

---

## Phase 2: 履歴表示機能の実装

### ステップ 2.1: `SlideHistory`コンポーネント作成

**ファイル**: `frontend/src/components/SlideHistory.tsx`（新規作成）

**機能要件**:

- ユーザーのスライド一覧を取得（`GET /api/slides?user_id={email}`）
- カード形式で表示（タイトル、作成日時、トピック）
- 「プレビュー」ボタン → `SlideViewer`モーダル表示

**実装イメージ**:

```tsx
import { useEffect, useState } from "react";

interface Slide {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  pdf_url?: string;
}

interface SlideHistoryProps {
  userEmail: string;
  onPreview: (slideId: string) => void;
}

export function SlideHistory({ userEmail, onPreview }: SlideHistoryProps) {
  const [slides, setSlides] = useState<Slide[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSlides = async () => {
      try {
        const response = await fetch(
          `http://localhost:8001/api/slides?user_id=${encodeURIComponent(
            userEmail
          )}&limit=20`
        );
        const data = await response.json();
        setSlides(data.slides || []);
      } catch (error) {
        console.error("Failed to fetch slides:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchSlides();
  }, [userEmail]);

  if (loading) {
    return <div>読み込み中...</div>;
  }

  if (slides.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "40px", color: "#999" }}>
        まだスライドがありません
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
        gap: "16px",
      }}
    >
      {slides.map((slide) => (
        <div
          key={slide.id}
          style={{
            background: "white",
            borderRadius: "8px",
            padding: "16px",
            boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
          }}
        >
          <h3 style={{ margin: "0 0 8px 0", fontSize: "16px" }}>
            {slide.title}
          </h3>
          <p style={{ fontSize: "14px", color: "#666", margin: "0 0 8px 0" }}>
            {new Date(slide.created_at).toLocaleString("ja-JP")}
          </p>
          <p style={{ fontSize: "13px", color: "#999", margin: "0 0 12px 0" }}>
            {slide.topic}
          </p>
          <button
            onClick={() => onPreview(slide.id)}
            style={{
              width: "100%",
              padding: "8px",
              background: "#007bff",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            📄 プレビュー
          </button>
        </div>
      ))}
    </div>
  );
}
```

### ステップ 2.2: `App.tsx` - 履歴セクション追加

**ファイル**: `frontend/src/App.tsx`

**変更箇所**: 136-189 行目（初回入力画面）

**変更内容**:

```tsx
// 追加: プレビュー用のstate
const [previewSlideId, setPreviewSlideId] = useState<string | null>(null);

// 初回入力画面
if (mode === "input") {
  return (
    <div style={{ minHeight: "100vh", background: "#f5f5f5" }}>
      {/* ヘッダー */}
      {/* ... 既存のヘッダー ... */}

      {/* 初回入力フォーム */}
      <InitialInputForm
        onPdfUpload={handlePdfUpload}
        onYoutubeSubmit={handleYoutubeSubmit}
      />

      {/* 追加: スライド履歴セクション */}
      <div
        style={{ maxWidth: "1200px", margin: "40px auto", padding: "0 24px" }}
      >
        <h2 style={{ fontSize: "20px", marginBottom: "16px" }}>
          📚 過去のスライド
        </h2>
        <SlideHistory
          userEmail={user.email}
          onPreview={(slideId) => setPreviewSlideId(slideId)}
        />
      </div>

      {/* プレビューモーダル */}
      {previewSlideId && (
        <SlideViewer
          slideId={previewSlideId}
          onClose={() => setPreviewSlideId(null)}
        />
      )}
    </div>
  );
}
```

### ステップ 2.3: テストと検証

**テスト手順**:

1. ログイン後、トップページに履歴セクションが表示される
2. 過去に生成したスライドがカード形式で表示される
3. 「プレビュー」ボタンをクリック → `SlideViewer`モーダルが開く
4. スライド内容が正しく表示される
5. モーダルを閉じる → トップページに戻る

**成功基準**:

- ✅ 履歴が時系列順（新しい順）で表示される
- ✅ 自分のスライドのみ表示される（他ユーザーのスライドは表示されない）
- ✅ プレビューが正常に動作する
- ✅ PDF URL が存在する場合、ダウンロードリンクが表示される

---

## ✅ 実装完了報告（2025-10-28）

### Phase 1 完了 ✅

**実装内容**:
1. `react_agent.py`: カスタムState定義（`user_id` + `remaining_steps`フィールド追加）
2. `react_agent.py`: `create_react_agent` に `state_schema=State` を渡す
3. `tools/slides.py`: `InjectedState` アノテーションで自動注入
4. システムプロンプト修正（user_idを渡さないよう明示）

**成功確認**:
- [x] Supabase の`slides`テーブルで`user_id`がメールアドレスになっている
- [x] `anonymous`ユーザーのレコードが増えなくなった
- [x] ログイン中のユーザーごとに異なる`user_id`が記録される
- [x] ログ出力で`user_id=user@example.com`が確認できる

**技術詳細**:
- **InjectedState**: LangGraph公式パターンを採用
  - `Annotated[dict, InjectedState]`でLLMスキーマから除外
  - ToolNodeが実行時に`state`を自動注入
  - LLMは`generate_slides(topic="...")`のみ呼び出し
- **remaining_steps**: `create_react_agent`の必須フィールド（最大10ステップ）
- **データフロー**: Frontend → FastAPI (`X-User-Email`) → LangGraph (`input["user_id"]`) → State → InjectedState → Supabase

### Phase 2 完了 ✅

**実装内容**:
1. `SlideHistory.tsx`: スライド履歴コンポーネント実装済み
2. `App.tsx`: トップページへの統合済み（187-220行目）
3. プレビューモーダル実装済み

**成功確認**:
- [x] トップページに「過去のスライド」セクションが表示される
- [x] 自分のスライドのみ表示される
- [x] プレビュー機能が動作する
- [x] Mermaid 図解が正しくレンダリングされる
- [x] PDF ダウンロードリンクが機能する

### エラー処理確認 ✅

- [x] Supabase 未設定時でもエラーにならない（警告のみ）
- [x] ネットワークエラー時に適切なメッセージが表示される
- [x] スライドが 0 件の場合、「まだスライドがありません」と表示される

---

## 最終確認チェックリスト（アーカイブ）

### Phase 1 完了確認（✅ 完了）

- [x] Supabase の`slides`テーブルで`user_id`がメールアドレスになっている
- [x] `anonymous`ユーザーのレコードが増えなくなった
- [x] ログイン中のユーザーごとに異なる`user_id`が記録される

### Phase 2 完了確認（✅ 完了）

- [x] トップページに「過去のスライド」セクションが表示される
- [x] 自分のスライドのみ表示される
- [x] プレビュー機能が動作する
- [x] Mermaid 図解が正しくレンダリングされる
- [x] PDF ダウンロードリンクが機能する

### エラー処理確認（✅ 完了）

- [x] Supabase 未設定時でもエラーにならない（警告のみ）
- [x] ネットワークエラー時に適切なメッセージが表示される
- [x] スライドが 0 件の場合、「まだスライドがありません」と表示される

---

## 実装で解決した課題

### 1. `remaining_steps` エラー

**症状**:
```
ValueError: Missing required key(s) {'remaining_steps'} in state_schema
```

**原因**: `create_react_agent` は `state_schema` に `remaining_steps` フィールドが必須

**解決策**:
```python
class State(MessagesState):
    user_id: str = "anonymous"
    remaining_steps: int = 10  # create_react_agentで必須
```

### 2. InjectedState の正しい使い方

**重要な学び**:
- `InjectedState` アノテーションはLLMのツールスキーマから自動的に除外される
- LangGraphのToolNodeが実行時に`state`引数を自動注入する
- LLMは`state`パラメータを見ないため、誤った値を渡すことがない

**参考**: [LangGraph InjectedState API](https://langchain-ai.github.io/langgraph/reference/agents/)

---

## 中断判断基準（アーカイブ - 全て解決済み）

以下のエラーが発生した場合は実装を中断し、Issue 報告:

1. **Phase 1 で user_id が依然として"anonymous"になる** → ✅ InjectedStateで解決

   - ~~原因: LangGraph/ReAct エージェントのアーキテクチャ制約~~
   - ~~対処: LangGraph v0.6+への移行が必要（大規模変更）~~

2. **Supabase API レート制限に達する** → 現時点で問題なし

   - 原因: 無料プランの制限
   - 対処: キャッシュ実装またはプラン変更

3. **SlideViewer で Mermaid 図解がレンダリングされない** → 正常動作確認済み
   - ~~原因: Mermaid ライブラリのバージョン問題~~
   - ~~対処: Issue #25 の再調査が必要~~

---

## 今後の改善案

### 短期（この PR に含めない）

- [ ] スライド削除機能（`DELETE /api/slides/{slide_id}`）
- [ ] スライド検索・フィルタリング（タイトル、日付範囲）
- [ ] ページネーション（20 件以上の場合）

### 長期（別 Issue 化）

- [x] ~~RunnableConfig 経由での user_id 注入（LangGraph 標準パターン）~~ → InjectedStateで実現済み
- [ ] サムネイル画像生成（PDF 1 ページ目のスクリーンショット）
- [ ] スライド編集機能（再生成）
- [ ] 共有機能（公開 URL 生成）

---

## 関連ドキュメント

- [CLAUDE.md](../../CLAUDE.md) - プロジェクト全体のアーキテクチャ
- [LangGraph InjectedState API](https://langchain-ai.github.io/langgraph/reference/agents/)
- [LangGraph - Add context to agents](https://langchain-ai.github.io/langgraph/agents/context/)

---

## 実装コミット履歴

以下のファイルが変更されました:

### バックエンド
- `backend/app/agents/react_agent.py`
  - カスタムState定義（`user_id` + `remaining_steps`）
  - `state_schema=State` を `create_react_agent` に渡す
  - システムプロンプトにuser_id自動注入の説明追加

- `backend/app/tools/slides.py`
  - `InjectedState` インポート追加
  - ツール引数を `(topic, state: Annotated[dict, InjectedState])` に変更
  - `user_id = state.get("user_id", "anonymous")` で取得

- `backend/app/routers/agent.py`
  - `body["input"]["user_id"] = x_user_email` は既に実装済み（変更なし）

### フロントエンド（Phase 2 - 既存実装）
- `frontend/src/components/SlideHistory.tsx` - 履歴コンポーネント
- `frontend/src/App.tsx` - 履歴セクション統合

### ドキュメント
- `docs/implementation-plans/IMPLEMENTATION_PLAN_HISTORY_PREVIEW.md` - この実装計画書
