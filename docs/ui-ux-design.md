# UI/UX設計方針書

**作成日**: 2025-10-29
**対象バージョン**: SlidePilot v2.0 (UI/UX改修)

## 目次
1. [設計コンセプト](#設計コンセプト)
2. [アーキテクチャ概要](#アーキテクチャ概要)
3. [ページ構成](#ページ構成)
4. [ルーティング設計](#ルーティング設計)
5. [コンポーネント設計](#コンポーネント設計)
6. [RAG統合設計](#rag統合設計)
7. [レスポンシブデザイン](#レスポンシブデザイン)
8. [技術スタック](#技術スタック)
9. [実装フェーズ](#実装フェーズ)

---

## 設計コンセプト

### ビジョン
**「常に隣にいてサポートしてくれる研究アシスタント」**

従来の「PDFアップロード→スライド生成」だけでなく、**各スライドごとに対話的な学習体験**を提供するプラットフォームへ進化。

### 主要な設計方針

#### 1. スライドごとの独立したチャット機能
- トップページは**ファイル/URLアップロード専用**（テキスト入力・チャット機能なし）
- 入力形式: PDFドロップ、URL入力（将来）、クイックテンプレートのみ
- 各スライド詳細ページに**専用チャットパネル**を配置
- RAGでPDF内容を参照した対話型学習を実現

#### 2. 明確なページ分離
```
トップページ (/)
  ↓ スライド生成
生成進行状況ページ (/generate/:threadId)
  ↓ 完了後自動遷移
スライド詳細ページ (/slides/:slideId)
  └─ RAG対応チャット
```

#### 3. URLベースのナビゲーション
- ブラウザの戻る/進むボタンで直感的に操作
- スライド共有が容易（`/slides/abc123` をURLコピー）
- SEO対応（将来的な公開スライド機能への布石）

---

## アーキテクチャ概要

### システム構成図

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React)                   │
├─────────────────────────────────────────────────────┤
│  Dashboard (/)                                       │
│    - スライド履歴表示                                │
│    - アシスタントパネル（生成提案）                   │
│    - クイックアクション                               │
├─────────────────────────────────────────────────────┤
│  GenerationProgress (/generate/:threadId)            │
│    - リアルタイム進行状況表示                         │
│    - SSEストリーミング                                │
├─────────────────────────────────────────────────────┤
│  SlideDetail (/slides/:slideId)                      │
│    - スライドビューア (左/上)                         │
│    - RAGチャットパネル (右/下)                        │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│              Backend API (FastAPI)                   │
├─────────────────────────────────────────────────────┤
│  /api/upload-pdf       - PDF アップロード             │
│  /api/slides           - スライド一覧取得             │
│  /api/slides/:id       - スライド詳細取得             │
│  /api/slides/:id/chat  - RAGチャット (新規)           │
│  /api/agent/*          - LangGraph proxy             │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│         Data Layer (Supabase + Vector DB)            │
├─────────────────────────────────────────────────────┤
│  Supabase                                            │
│    - slides テーブル (メタデータ)                     │
│    - users テーブル                                   │
│    - Storage (PDF/スライドファイル)                   │
├─────────────────────────────────────────────────────┤
│  Vector DB (ChromaDB / Pinecone)                     │
│    - スライドごとのEmbeddings                         │
│    - Namespace分離 (slide_id単位)                     │
└─────────────────────────────────────────────────────┘
```

---

## ページ構成

### 1. トップページ (`/`)

#### 役割
- **スライド生成の入り口**（PDFアップロード専用）
- 過去のスライド履歴管理
- クイックアクション提供
- **チャット機能なし**（入力はファイル/URLのみ）

#### レイアウト（デスクトップ）
```
┌─────────────────────────────────────────────────────────┐
│  [SlidePilot Logo]               [User Avatar] [Logout] │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────────────────┐  ┌──────────┐  │
│  │          │  │  👋 こんにちは!       │  │          │  │
│  │  過去の  │  │                      │  │  クイック│  │
│  │  スライド │  │  どの資料から        │  │  テンプレ│  │
│  │          │  │  スライドを作る？    │  │  ート    │  │
│  │  [カード]│  │                      │  │          │  │
│  │  [カード]│  │  📄 PDFドロップ      │  │ 🤖AI記事 │  │
│  │  [カード]│  │  [ファイル選択]       │  │ 📊論文   │  │
│  │  ...     │  │                      │  │          │  │
│  │          │  │  🔗 URL入力          │  │          │  │
│  │  [もっと]│  │  [URL] [生成開始]    │  │ [開始]   │  │
│  └──────────┘  │  (準備中)            │  └──────────┘  │
│                └──────────────────────┘                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### 3カラム構成
- **左サイドバー (300px)**
  - スライド履歴カードグリッド
  - カードクリック → `/slides/:id` へ遷移
  - 最新20件を表示、「もっと見る」ボタン

- **中央パネル (可変幅)**
  - アシスタントキャラクター表示（静的）
  - **PDFドロップゾーン**（メイン機能）
    - ドラッグ&ドロップ対応
    - クリックでファイル選択
    - 対応形式: PDF（最大100MB）
  - **URL入力フィールド**（将来実装）
    - YouTube、論文サイトなど
    - 現在は「準備中」表示
  - **テキスト入力なし**（チャット機能なし）

- **右サイドバー (300px)**
  - クイックテンプレートボタン
  - 「AI最新ニュース」ワンクリック生成
  - 「機械学習入門」テンプレート
  - 「教科書章立て」テンプレート
  - ※ クリックで自動的にLangGraph起動 → `/generate/:threadId`

#### 主要機能
1. **PDFアップロード**（メイン機能）
   - ドラッグ&ドロップ対応
   - ファイル選択ダイアログ
   - アップロード後 → 即座に `/generate/:threadId` へ遷移
   - バリデーション: PDF形式、100MB以下

2. **URL入力**（将来実装）
   - 入力フィールド表示
   - 現在は「準備中」表示
   - 実装後: YouTube, arXiv, 企業ブログなど

3. **スライド履歴表示**
   - カード形式（タイトル、作成日時、サムネイル）
   - ホバー時にプレビュー拡大
   - クリックで `/slides/:id` へ遷移

4. **クイックテンプレート**
   - 事前定義トピックからワンクリック生成
   - クリック → LangGraphに自動送信 → `/generate/:threadId`
   - 例: 「2025年のAI業界トレンド」「機械学習の基礎」

### 2. 生成進行状況ページ (`/generate/:threadId`)

#### 役割
- スライド生成の進行状況をリアルタイム表示
- LangGraphのSSEストリームを視覚化

#### レイアウト
```
┌─────────────────────────────────────────────────────────┐
│  [← Dashboard] スライド生成中...                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│               🤖 AIアシスタントが作業中                  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ✅ 資料を読んでいます...               (完了)       │  │
│  │ 🔄 要点をまとめています...             (実行中)     │  │
│  │ ⏳ 目次を作成します...                 (待機中)     │  │
│  │ ⏳ スライドを書いています...           (待機中)     │  │
│  │ ⏳ 評価しています...                   (待機中)     │  │
│  │ ⏳ PDFを出力しています...              (待機中)     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│             [進行状況: ████████░░░░░░░░ 40%]            │
│                                                          │
│  💬 AIからのメッセージ:                                 │
│  「5つのポイントを見つけました！                          │
│   これから読みやすいスライドに整理しますね。」           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### 主要機能
1. **リアルタイム進行状況**
   - LangGraphのノード実行状態を表示
   - アニメーション付きステップ表示

2. **ストーリーテリング**
   - 技術的な処理名ではなく親しみやすいメッセージ
   - 例: `collect_info` → 「資料を読んでいます...」

3. **自動遷移**
   - 生成完了時に `/slides/:slideId` へリダイレクト
   - トースト通知: 「スライドが完成しました！」

### 3. スライド詳細ページ (`/slides/:slideId`)

#### 役割
- スライド閲覧
- **RAG対応チャットで対話型学習**

#### レイアウト（デスクトップ）
```
┌─────────────────────────────────────────────────────────┐
│ [← Dashboard] "機械学習の基礎"                 [共有] [削除] │
├─────────────────────┬───────────────────────────────────┤
│                     │  📚 スライドについて質問           │
│   Slide Viewer      │                                   │
│   (60%)             │  ┌─────────────────────────────┐  │
│                     │  │ 🤖 このスライドは機械学習の  │  │
│   [Page 1/10]       │  │    基礎を説明しています。    │  │
│                     │  │    何か質問はありますか？    │  │
│   ┌─────────────┐   │  └─────────────────────────────┘  │
│   │             │   │                                   │
│   │   Slide     │   │  ┌─────────────────────────────┐  │
│   │   Preview   │   │  │ 👤 教師あり学習と教師なし   │  │
│   │             │   │  │    学習の違いは？           │  │
│   └─────────────┘   │  └─────────────────────────────┘  │
│                     │                                   │
│   [← Prev] [Next →]│  ┌─────────────────────────────┐  │
│                     │  │ 🤖 教師あり学習は、正解      │  │
│   [📥 PDF Download] │  │    ラベル付きデータから...   │  │
│   [📧 Email送信]    │  │    (詳細な説明)              │  │
│                     │  └─────────────────────────────┘  │
│                     │                                   │
│                     │  💡 こんな質問もできます:        │
│                     │  [専門用語を説明して]            │
│                     │  [具体例を教えて]                │
│                     │  [次のページを要約]              │
│                     │                                   │
│                     │  [質問を入力...          ] [送信] │
└─────────────────────┴───────────────────────────────────┘
```

#### 2ペイン構成
- **左ペイン (60%): スライドビューア**
  - PDF/画像ベースのスライド表示
  - ページナビゲーション
  - ダウンロードボタン
  - メール送信ボタン（ReActエージェント連携）

- **右ペイン (40%): RAGチャットパネル**
  - チャット履歴表示
  - 質問候補提示（Suggested Questions）
  - 入力欄
  - RAG検索結果の出典表示

#### 主要機能

##### 1. スライド閲覧
- ページ送り/戻し
- サムネイル一覧（オプション）
- フルスクリーンモード

##### 2. RAGチャット
**基本フロー**:
```
1. ユーザー質問入力
   ↓
2. フロントエンド → POST /api/slides/:id/chat
   ↓
3. バックエンド:
   a. Vector DBで関連チャンク検索
   b. チャンク + 質問をLLMに送信
   c. 回答生成
   ↓
4. フロントエンドで回答表示 + 出典リンク
```

**機能詳細**:
- スライド内容に基づいた回答生成
- 出典ページ番号の表示（「スライド3ページ目を参照」）
- 専門用語の自動検出と説明
- 質問履歴の保存（スライドごとにSupabaseに保存）

##### 3. Suggested Questions（質問候補）
AIが自動生成する質問例:
- 「このページの要点を3つにまとめて」
- 「〇〇という用語を中学生向けに説明して」
- 「具体例を教えて」
- 「次のページとの関連性は？」

---

## ルーティング設計

### React Router v6 構成

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

<BrowserRouter>
  <Routes>
    {/* 公開ルート */}
    <Route path="/login" element={<Login />} />

    {/* 認証必須ルート */}
    <Route element={<ProtectedRoute />}>
      {/* トップページ */}
      <Route path="/" element={<Dashboard />} />

      {/* スライド生成進行状況 */}
      <Route path="/generate/:threadId" element={<GenerationProgress />} />

      {/* スライド詳細 + RAGチャット */}
      <Route path="/slides/:slideId" element={<SlideDetail />} />

      {/* 存在しないルート */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Route>
  </Routes>
</BrowserRouter>
```

### URL設計

| パス | 説明 | 主要機能 |
|------|------|----------|
| `/` | トップページ | スライド生成、履歴表示 |
| `/login` | ログイン画面 | Google OAuth |
| `/generate/:threadId` | 生成進行状況 | SSEストリーミング |
| `/slides/:slideId` | スライド詳細 | 閲覧 + RAGチャット |

### ナビゲーションフロー

```
[ログイン画面] /login
    ↓ Google OAuth成功
[トップページ] /
    ↓ PDFアップロード
[生成進行状況] /generate/thread-abc123
    ↓ 生成完了
[スライド詳細] /slides/slide-xyz789
    ↓ ← Dashboardボタン
[トップページ] /
    ↓ 履歴カードクリック
[スライド詳細] /slides/slide-old456
```

---

## コンポーネント設計

### ディレクトリ構成

```
frontend/src/
├── pages/                    # ページコンポーネント
│   ├── Login.tsx
│   ├── Dashboard.tsx         # トップページ
│   ├── GenerationProgress.tsx
│   └── SlideDetail.tsx       # スライド詳細
│
├── components/
│   ├── layout/               # レイアウトコンポーネント
│   │   ├── DashboardLayout.tsx
│   │   ├── SlideDetailLayout.tsx
│   │   ├── Header.tsx
│   │   └── ProtectedRoute.tsx
│   │
│   ├── dashboard/            # Dashboard専用
│   │   ├── AssistantPanel.tsx
│   │   ├── SlideHistoryGrid.tsx
│   │   ├── QuickActionPanel.tsx
│   │   └── FileDropzone.tsx  # 既存を流用
│   │
│   ├── slide/                # SlideDetail専用
│   │   ├── SlideViewer.tsx   # 既存を流用
│   │   ├── ChatPanel.tsx
│   │   ├── RAGChatInput.tsx
│   │   ├── SuggestedQuestions.tsx
│   │   └── ChatMessage.tsx   # 既存を流用
│   │
│   ├── generation/           # GenerationProgress専用
│   │   ├── ProgressSteps.tsx
│   │   ├── ThinkingIndicator.tsx  # 既存を流用
│   │   └── AIMessage.tsx
│   │
│   └── common/               # 共通コンポーネント
│       ├── Button.tsx
│       ├── Card.tsx
│       ├── Modal.tsx
│       └── PageTransition.tsx
│
├── hooks/
│   ├── useReactAgent.ts      # 既存（LangGraph連携）
│   ├── useRAGChat.ts         # 新規（RAGチャット）
│   └── useAuth.ts            # 新規（認証状態管理）
│
├── utils/
│   ├── api.ts                # API通信関数
│   └── animations.ts         # Framer Motion設定
│
└── types/
    ├── slide.ts
    ├── chat.ts
    └── user.ts
```

### 主要コンポーネント詳細

#### 1. Dashboard.tsx（トップページ）

```tsx
// frontend/src/pages/Dashboard.tsx
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { AssistantPanel } from '@/components/dashboard/AssistantPanel';
import { SlideHistoryGrid } from '@/components/dashboard/SlideHistoryGrid';
import { QuickActionPanel } from '@/components/dashboard/QuickActionPanel';

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleSlideGenerate = async (file: File) => {
    // 1. PDFアップロード
    const { path } = await uploadPDF(file);

    // 2. スレッド作成
    const thread = await createThread();

    // 3. 生成進行状況ページへ遷移
    navigate(`/generate/${thread.id}`, {
      state: { pdfPath: path }
    });
  };

  return (
    <DashboardLayout>
      <LeftSidebar>
        <SlideHistoryGrid
          userEmail={user.email}
          onCardClick={(slideId) => navigate(`/slides/${slideId}`)}
        />
      </LeftSidebar>

      <CenterPanel>
        <AssistantPanel onGenerate={handleSlideGenerate} />
      </CenterPanel>

      <RightSidebar>
        <QuickActionPanel />
      </RightSidebar>
    </DashboardLayout>
  );
}
```

#### 2. SlideDetail.tsx（スライド詳細）

```tsx
// frontend/src/pages/SlideDetail.tsx
import { useParams } from 'react-router-dom';
import { SlideDetailLayout } from '@/components/layout/SlideDetailLayout';
import { SlideViewer } from '@/components/slide/SlideViewer';
import { ChatPanel } from '@/components/slide/ChatPanel';

export default function SlideDetail() {
  const { slideId } = useParams<{ slideId: string }>();
  const [slide, setSlide] = useState<Slide | null>(null);

  useEffect(() => {
    // スライド情報取得
    fetchSlide(slideId).then(setSlide);
  }, [slideId]);

  return (
    <SlideDetailLayout>
      <BackButton to="/" />

      <LeftPane>
        <SlideViewer slideId={slideId} />
        <SlideControls>
          <DownloadButton url={slide?.pdf_url} />
          <EmailButton slideId={slideId} />
        </SlideControls>
      </LeftPane>

      <RightPane>
        <ChatPanel slideId={slideId} />
      </RightPane>
    </SlideDetailLayout>
  );
}
```

#### 3. ChatPanel.tsx（RAGチャット）

```tsx
// frontend/src/components/slide/ChatPanel.tsx
import { useRAGChat } from '@/hooks/useRAGChat';
import { ChatMessage } from '@/components/ChatMessage';
import { SuggestedQuestions } from '@/components/slide/SuggestedQuestions';
import { RAGChatInput } from '@/components/slide/RAGChatInput';

interface ChatPanelProps {
  slideId: string;
}

export function ChatPanel({ slideId }: ChatPanelProps) {
  const { messages, isLoading, sendMessage } = useRAGChat(slideId);

  return (
    <div className="chat-panel">
      <ChatHeader>
        <h3>📚 スライドについて質問</h3>
        <p>RAGでPDF内容を参照して回答します</p>
      </ChatHeader>

      <ChatMessages>
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {isLoading && <ThinkingIndicator />}
      </ChatMessages>

      <SuggestedQuestions
        suggestions={['このページを要約', '専門用語を説明']}
        onSelect={sendMessage}
      />

      <RAGChatInput
        onSend={sendMessage}
        disabled={isLoading}
      />
    </div>
  );
}
```

#### 4. useRAGChat.ts（RAGチャットフック）

```tsx
// frontend/src/hooks/useRAGChat.ts
import { useState, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[]; // 出典ページ
}

export function useRAGChat(slideId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // 過去のチャット履歴を復元
  useEffect(() => {
    fetchChatHistory(slideId).then(setMessages);
  }, [slideId]);

  const sendMessage = async (content: string) => {
    // ユーザーメッセージを追加
    setMessages((prev) => [...prev, { role: 'user', content }]);
    setIsLoading(true);

    try {
      // RAG検索 + LLM回答取得
      const response = await fetch(
        `http://localhost:8001/api/slides/${slideId}/chat`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: content }),
        }
      );

      const data = await response.json();

      // アシスタント回答を追加
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          sources: data.sources, // 出典ページ番号
        },
      ]);

      // Supabaseにチャット履歴を保存
      await saveChatMessage(slideId, content, data.answer);
    } catch (err) {
      console.error('RAG chat error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return { messages, isLoading, sendMessage };
}
```

---

## RAG統合設計

### システム構成

```
┌─────────────────────────────────────────────────────────┐
│                Frontend (SlideDetail)                    │
│  質問入力 → POST /api/slides/:id/chat                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Backend API (FastAPI)                       │
│                                                          │
│  1. Supabaseからスライド情報取得                          │
│  2. Vector DBで関連チャンク検索                           │
│  3. LLM + RAGで回答生成                                  │
│  4. チャット履歴をSupabaseに保存                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│            Vector DB (ChromaDB / Pinecone)               │
│                                                          │
│  Collection: slide_embeddings                            │
│  - Namespace: slide_id                                   │
│  - Documents: PDFチャンク (500トークン/チャンク)          │
│  - Metadata: {page, slide_id, chunk_index}               │
└─────────────────────────────────────────────────────────┘
```

### バックエンドAPI実装

#### 1. エンドポイント定義

```python
# backend/app/routers/chat.py (新規作成)
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.rag import RAGEngine

router = APIRouter(prefix="/api/slides", tags=["chat"])

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]  # 出典ページ番号

@router.post("/{slide_id}/chat", response_model=ChatResponse)
async def chat_with_slide(
    slide_id: str,
    request: ChatRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine)
):
    """
    スライドの内容に基づいてRAG検索 + LLM回答を生成
    """
    try:
        # RAG検索
        relevant_chunks = await rag_engine.search(
            slide_id=slide_id,
            query=request.message,
            top_k=3
        )

        # LLM回答生成
        answer = await rag_engine.generate_answer(
            query=request.message,
            context=relevant_chunks
        )

        # 出典ページ抽出
        sources = [chunk['metadata']['page'] for chunk in relevant_chunks]

        return ChatResponse(answer=answer, sources=sources)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 2. RAGエンジン実装

```python
# backend/app/core/rag.py (新規作成)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA

class RAGEngine:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.vectorstore = Chroma(
            collection_name="slide_embeddings",
            embedding_function=self.embeddings,
            persist_directory="./data/chroma"
        )

    async def index_slide(self, slide_id: str, markdown_content: str):
        """
        スライドのマークダウンをチャンク化してVector DBに格納
        """
        # チャンク分割（500トークン/チャンク、100トークンオーバーラップ）
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            length_function=len
        )
        chunks = splitter.split_text(markdown_content)

        # Embeddingsを生成してVector DBに保存
        metadatas = [
            {"slide_id": slide_id, "chunk_index": i, "page": i // 3}
            for i in range(len(chunks))
        ]

        self.vectorstore.add_texts(
            texts=chunks,
            metadatas=metadatas,
            ids=[f"{slide_id}_{i}" for i in range(len(chunks))]
        )

        print(f"✅ Indexed {len(chunks)} chunks for slide {slide_id}")

    async def search(self, slide_id: str, query: str, top_k: int = 3):
        """
        Vector DBで関連チャンクを検索
        """
        results = self.vectorstore.similarity_search(
            query=query,
            k=top_k,
            filter={"slide_id": slide_id}  # スライドIDでフィルタ
        )

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in results
        ]

    async def generate_answer(self, query: str, context: list[dict]):
        """
        RAGで回答を生成
        """
        # コンテキストを結合
        context_text = "\n\n".join([c['content'] for c in context])

        # プロンプト構築
        prompt = f"""
以下のスライド内容を参照して、中学生でも理解できるように質問に答えてください。

スライド内容:
{context_text}

質問: {query}

回答:
"""

        # LLM実行
        response = self.llm.predict(prompt)
        return response
```

#### 3. スライド生成時の自動インデックス化

```python
# backend/app/agents/slide_workflow.py (既存ファイルに追加)

async def save_and_render_slidev(state: State):
    """
    スライド保存 + PDF出力 + Vector DB インデックス化
    """
    # ... 既存のスライド保存処理 ...

    # RAGのためにVector DBにインデックス化
    rag_engine = RAGEngine()
    await rag_engine.index_slide(
        slide_id=slide_id,
        markdown_content=state["slide_md"]
    )

    return {
        **state,
        "slide_path": slide_path,
        "slide_id": slide_id
    }
```

### データベース設計

#### Supabase テーブル拡張

```sql
-- chat_messages テーブル (新規)
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slide_id TEXT NOT NULL REFERENCES slides(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources TEXT[], -- 出典ページ番号の配列
    created_at TIMESTAMP DEFAULT NOW()
);

-- インデックス
CREATE INDEX idx_chat_messages_slide_id ON chat_messages(slide_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at DESC);
```

#### Vector DB スキーマ

```python
# ChromaDB Collection
{
    "name": "slide_embeddings",
    "metadata": {
        "description": "SlidePilot スライドのEmbeddings"
    },
    "documents": [
        {
            "id": "slide-123_0",
            "embedding": [0.123, 0.456, ...],  # 1536次元
            "metadata": {
                "slide_id": "slide-123",
                "chunk_index": 0,
                "page": 1,
                "title": "機械学習の基礎"
            },
            "document": "機械学習とは、コンピュータが..."
        }
    ]
}
```

---

## レスポンシブデザイン

### ブレークポイント

```css
/* Tailwind CSS ベース */
sm: 640px   /* モバイル */
md: 768px   /* タブレット */
lg: 1024px  /* デスクトップ */
xl: 1280px  /* ワイドスクリーン */
```

### レイアウト変更

#### 1. Dashboard（トップページ）

**デスクトップ (>1024px)**
```
[Left Sidebar 300px] [Center Panel] [Right Sidebar 300px]
```

**タブレット (768px - 1024px)**
```
[Center Panel (75%)] [Right Sidebar (25%)]
※ Left Sidebarは折りたたみメニューに
```

**モバイル (<768px)**
```
[Center Panel 100%]
※ タブ切り替え: [メイン] [履歴] [アクション]
```

#### 2. SlideDetail（スライド詳細）

**デスクトップ (>1024px)**
```
[Slide Viewer 60%] | [Chat Panel 40%]
```

**タブレット (768px - 1024px)**
```
[Slide Viewer 50%] | [Chat Panel 50%]
```

**モバイル (<768px)**
```
[タブ切り替え]
- [スライド]タブ: 100% Viewer
- [チャット]タブ: 100% Chat Panel
```

### Tailwind CSS 実装例

```tsx
// DashboardLayout.tsx
<div className="grid grid-cols-1 lg:grid-cols-[300px_1fr_300px] gap-4">
  {/* Left Sidebar */}
  <aside className="hidden lg:block">
    <SlideHistoryGrid />
  </aside>

  {/* Center Panel */}
  <main>
    <AssistantPanel />
  </main>

  {/* Right Sidebar */}
  <aside className="hidden md:block">
    <QuickActionPanel />
  </aside>
</div>

// SlideDetailLayout.tsx
<div className="flex flex-col lg:flex-row gap-4">
  {/* Slide Viewer */}
  <div className="w-full lg:w-3/5">
    <SlideViewer />
  </div>

  {/* Chat Panel */}
  <div className="w-full lg:w-2/5">
    <ChatPanel />
  </div>
</div>
```

---

## 技術スタック

### フロントエンド

| 技術 | バージョン | 用途 |
|------|-----------|------|
| React | 19.x | UIフレームワーク |
| TypeScript | 5.x | 型安全性 |
| Vite | 6.x | ビルドツール |
| React Router | 6.x | ルーティング |
| Framer Motion | 11.x | アニメーション |
| Tailwind CSS | 3.x | スタイリング |
| Zustand or Jotai | 4.x | 軽量状態管理 |
| react-hot-toast | 2.x | 通知UI |

### バックエンド

| 技術 | バージョン | 用途 |
|------|-----------|------|
| FastAPI | 0.115.x | APIフレームワーク |
| LangGraph | 0.2.x | エージェント制御 |
| LangChain | 0.3.x | RAGパイプライン |
| OpenAI GPT-4 | - | LLM |
| ChromaDB | 0.5.x | Vector DB (開発) |
| Pinecone | - | Vector DB (本番) |
| Supabase | - | データベース + Storage |

### インフラ

| 技術 | 用途 |
|------|------|
| Supabase | PostgreSQL + Storage + Auth |
| ChromaDB | Vector DB (ローカル開発) |
| Pinecone | Vector DB (本番環境) |
| Vercel | フロントエンドホスティング |
| Railway/Render | バックエンドホスティング |

---

## 実装フェーズ

### Phase 1: ルーティング基盤 (Week 1)
**目標**: React Routerでページ分離

- [ ] React Router v6 導入
- [ ] ProtectedRoute実装（認証ガード）
- [ ] Dashboard, GenerationProgress, SlideDetail の基本ページ作成
- [ ] ページ遷移の動作確認

**成果物**:
- `/`, `/generate/:id`, `/slides/:id` のルーティング
- 認証チェック機能

### Phase 2: トップページ改修 (Week 2)
**目標**: リサーチアシスタント型UIの実装

- [ ] DashboardLayout作成（3カラム）
- [ ] AssistantPanel実装（キャラクター + 吹き出し）
- [ ] SlideHistoryGrid実装（カードクリック → `/slides/:id`）
- [ ] QuickActionPanel実装（ワンクリック生成）
- [ ] Tailwind CSS導入 + レスポンシブ対応

**成果物**:
- 能動的な提案を行うトップページ
- 履歴カードからスライド詳細への遷移

### Phase 3: スライド詳細ページ (Week 3)
**目標**: 2ペインレイアウト + チャットUI（RAG機能なし）

- [ ] SlideDetailLayout作成（2ペイン）
- [ ] ChatPanel実装（UI のみ）
- [ ] RAGChatInput + SuggestedQuestions
- [ ] チャットメッセージ表示（ダミーデータ）
- [ ] レスポンシブ対応（タブ切り替え）

**成果物**:
- スライド閲覧 + チャットUIの統合画面

### Phase 4: RAGバックエンド (Week 4-5)
**目標**: Vector DB統合 + RAG機能実装

- [ ] ChromaDB導入
- [ ] RAGEngine実装（`backend/app/core/rag.py`）
- [ ] `/api/slides/{id}/chat` エンドポイント作成
- [ ] スライド生成時の自動インデックス化
- [ ] Supabase `chat_messages` テーブル作成

**成果物**:
- 動作するRAGチャット機能
- PDF内容に基づく回答生成

### Phase 5: UX強化 (Week 6)
**目標**: アニメーション + 細部の改善

- [ ] Framer Motion導入
- [ ] ページ遷移アニメーション
- [ ] Suggested Questions自動生成（LLM）
- [ ] 出典ページへのジャンプ機能
- [ ] react-hot-toast導入（通知UI）

**成果物**:
- スムーズなページ遷移
- 直感的なユーザー体験

### Phase 6: 本番環境対応 (Week 7)
**目標**: 本番デプロイ準備

- [ ] Pinecone移行（Vector DB）
- [ ] 環境変数管理（`.env.production`）
- [ ] エラーハンドリング強化
- [ ] パフォーマンス最適化
- [ ] E2Eテスト（Playwright）

**成果物**:
- 本番環境で動作するシステム

---

## 付録

### 参考リンク
- [React Router v6 公式ドキュメント](https://reactrouter.com/)
- [Framer Motion](https://www.framer.com/motion/)
- [LangChain RAG Tutorial](https://python.langchain.com/docs/use_cases/question_answering/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Tailwind CSS](https://tailwindcss.com/)

### 関連ドキュメント
- [CLAUDE.md](../CLAUDE.md) - プロジェクト全体の技術仕様
- [backend/README.md](../backend/README.md) - バックエンドAPI仕様
- [frontend/README.md](../frontend/README.md) - フロントエンドセットアップ

---

**最終更新**: 2025-10-29
**レビュー者**: -
**承認者**: -
