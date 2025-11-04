# RAG バックエンド設計書

**作成日**: 2025-10-30
**対象**: SlidePilot Phase 4 実装
**関連 Issue**: #XX (別途作成)

---

## 目次

1. [概要](#概要)
2. [アーキテクチャ方針](#アーキテクチャ方針)
3. [システム構成](#システム構成)
4. [実装手順](#実装手順)
5. [データベース設計](#データベース設計)
6. [実装チェックリスト](#実装チェックリスト)
7. [依存関係](#依存関係)
8. [テスト計画](#テスト計画)
9. [デプロイ手順](#デプロイ手順)
10. [トラブルシューティング](#トラブルシューティング)

---

## 概要

### 目的

スライド詳細ページ（`/slides/:slideId`）でRAG（Retrieval-Augmented Generation）チャット機能を実装し、スライド内容に基づく対話型学習を実現する。

### 主要機能

- スライド内容に基づく質問応答
- Vector検索による関連チャンク取得
- 出典ページ番号の表示
- チャット履歴の保存

### 成果物

✅ 動作するRAGチャット機能
✅ スライド内容に基づく回答生成
✅ LangGraph Studioでデバッグ可能
✅ デプロイが容易（Supabase Vector使用）

---

## アーキテクチャ方針

### 採用技術

#### 1. **Supabase Vector (pgvector)**

ChromaDBやPineconeの代わりにPostgreSQL拡張機能を使用

**選定理由:**
- 既にSupabaseを使用しているため、追加インフラ不要
- SQL実行のみでVector DB機能を追加可能
- 永続化ストレージ管理が不要（Supabaseが自動管理）
- 開発・本番で同じDBを使用可能

#### 2. **LangGraph RAGエージェント**

単純なエンドポイントではなく、ステートフルなエージェント実装

**選定理由:**
- 既存のスライド生成ワークフローと統一されたアーキテクチャ
- LangSmithでトレーシング可能
- 将来の拡張性（Web検索連携、Gmail送信など）
- SSEストリーミングで進行状況をリアルタイム表示可能

### 技術的な利点

| 項目 | ChromaDB/Pinecone | Supabase Vector + LangGraph |
|------|-------------------|----------------------------|
| **インフラ管理** | 専用サーバー必要 | 不要（Supabase統合） |
| **永続化** | ボリューム管理必要 | Supabase自動管理 |
| **コスト** | $10-50/月 | Supabase無料枠内 |
| **デプロイ** | Docker/K8s設定 | SQL実行のみ |
| **開発・本番統一** | 困難 | 同じDB使用 |
| **拡張性** | 限定的 | LangGraphで容易 |

---

## システム構成

### アーキテクチャ図

```
┌─────────────────────────────────────────────────────────┐
│                Frontend (SlideDetail)                    │
│  質問入力 → POST /api/slides/:id/chat                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Backend API (FastAPI)                       │
│                                                          │
│  FastAPIプロキシ → LangGraph API (port 2024)             │
│  /api/slides/:id/chat → /runs/stream                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│          LangGraph RAGエージェント (port 2024)           │
│                                                          │
│  ┌─────────────────────────────────────────────┐       │
│  │ RAGState:                                   │       │
│  │  - slide_id                                 │       │
│  │  - question                                 │       │
│  │  - context (Vector検索結果)                 │       │
│  │  - answer                                   │       │
│  │  - sources (出典ページ)                     │       │
│  └─────────────────────────────────────────────┘       │
│                                                          │
│  フロー: search_context → generate_answer → END         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│         Supabase (PostgreSQL + pgvector拡張)            │
│                                                          │
│  slide_embeddings テーブル                               │
│  - id: BIGSERIAL                                         │
│  - slide_id: TEXT (外部キー)                            │
│  - chunk_index: INT                                      │
│  - page: INT                                             │
│  - content: TEXT                                         │
│  - embedding: VECTOR(1536)  ← OpenAI Embeddings        │
│  - created_at: TIMESTAMP                                 │
│                                                          │
│  類似度検索: ivfflat インデックス                         │
│  match_slide_chunks() 関数で高速検索                     │
└─────────────────────────────────────────────────────────┘
```

### データフロー

1. **ユーザー入力**: フロントエンドでユーザーが質問を入力
2. **FastAPI プロキシ**: `/api/slides/:id/chat` → LangGraph API
3. **Vector検索**: Supabase VectorでTop-K類似チャンクを検索
4. **RAG回答生成**: 検索結果をコンテキストとしてLLMに送信
5. **回答返却**: 回答 + 出典ページ番号をフロントエンドに返却
6. **履歴保存**: Supabase `chat_messages`テーブルに保存

---

## 実装手順

### 1. Supabase Vector 有効化

Supabase DashboardのSQL Editorで以下を実行

```sql
-- 1. vector拡張を有効化
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. slide_embeddings テーブル作成
CREATE TABLE slide_embeddings (
  id BIGSERIAL PRIMARY KEY,
  slide_id TEXT NOT NULL REFERENCES slides(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  page INT,
  content TEXT NOT NULL,
  embedding VECTOR(1536),  -- OpenAI ada-002 embeddings
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- 3. 高速検索用インデックス（ivfflat: コサイン類似度）
CREATE INDEX ON slide_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. slide_id でのフィルタ用インデックス
CREATE INDEX ON slide_embeddings(slide_id);

-- 5. 類似度検索関数（PostgreSQL関数）
CREATE OR REPLACE FUNCTION match_slide_chunks(
  query_embedding VECTOR(1536),
  filter_slide_id TEXT,
  match_count INT DEFAULT 3
)
RETURNS TABLE (
  id BIGINT,
  slide_id TEXT,
  content TEXT,
  page INT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    slide_embeddings.id,
    slide_embeddings.slide_id,
    slide_embeddings.content,
    slide_embeddings.page,
    1 - (slide_embeddings.embedding <=> query_embedding) AS similarity
  FROM slide_embeddings
  WHERE slide_embeddings.slide_id = filter_slide_id
  ORDER BY slide_embeddings.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

### 2. RAGEngine 実装（Supabase Vector 使用）

**ファイル**: `backend/app/core/rag.py` (新規作成)

```python
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from app.core.supabase import get_supabase_client
from app.core.llm import llm

class RAGEngine:
    """Supabase Vector (pgvector) を使用したRAGエンジン"""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.client = get_supabase_client()

    def index_slide(self, slide_id: str, markdown: str) -> None:
        """スライドをチャンク化してSupabase Vectorに保存

        Args:
            slide_id: スライドID
            markdown: Slidev Markdown コンテンツ
        """
        # チャンク分割（500文字/チャンク、100文字オーバーラップ）
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            length_function=len
        )
        chunks = splitter.split_text(markdown)

        # Embeddings生成（バッチ処理）
        embeddings = self.embeddings.embed_documents(chunks)

        # Supabaseに一括挿入
        records = [
            {
                "slide_id": slide_id,
                "chunk_index": i,
                "page": i // 3,  # 1ページ=3チャンクと仮定
                "content": chunk,
                "embedding": embedding
            }
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        self.client.table("slide_embeddings").insert(records).execute()
        print(f"✅ Indexed {len(chunks)} chunks for slide {slide_id}")

    def search(self, slide_id: str, query: str, top_k: int = 3) -> List[Dict]:
        """Supabase Vectorで類似度検索

        Args:
            slide_id: スライドID（フィルタ条件）
            query: ユーザーの質問
            top_k: 取得件数

        Returns:
            検索結果のリスト（content, page, similarity）
        """
        # クエリのEmbedding生成
        query_embedding = self.embeddings.embed_query(query)

        # Supabase関数呼び出し（match_slide_chunks）
        result = self.client.rpc(
            "match_slide_chunks",
            {
                "query_embedding": query_embedding,
                "filter_slide_id": slide_id,
                "match_count": top_k
            }
        ).execute()

        return result.data

    def generate_answer(self, query: str, context: List[Dict]) -> str:
        """RAGで回答を生成

        Args:
            query: ユーザーの質問
            context: 検索結果のリスト

        Returns:
            LLMの回答
        """
        # コンテキストを結合
        context_text = "\n\n".join([
            f"[ページ {c['page']}]\n{c['content']}"
            for c in context
        ])

        # RAGプロンプト
        prompt = f"""以下のスライド内容を参照して、中学生でも理解できるように質問に答えてください。

【スライド内容】
{context_text}

【質問】
{query}

【回答】"""

        # LLM実行
        response = llm.predict(prompt)
        return response
```

### 3. LangGraph RAGエージェント実装

**ファイル**: `backend/app/agents/rag_agent.py` (新規作成)

```python
"""LangGraph RAGエージェント

スライド内容に基づく質問応答エージェント
Vector検索 → LLM回答生成のフロー
"""

from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END
from langsmith import traceable

from app.core.rag import RAGEngine

# -------------------
# State定義
# -------------------
class RAGState(TypedDict, total=False):
    """RAGエージェントの状態"""
    slide_id: str              # スライドID
    question: str              # ユーザーの質問
    context: List[Dict]        # Vector検索結果
    answer: str                # LLM回答
    sources: List[str]         # 出典ページ番号

# -------------------
# Nodes
# -------------------
rag_engine = RAGEngine()

@traceable(run_name="rag_search_context")
def search_context(state: RAGState) -> Dict:
    """Supabase Vectorで関連チャンクを検索"""
    results = rag_engine.search(
        slide_id=state["slide_id"],
        query=state["question"],
        top_k=3
    )
    return {
        "context": results,
        "sources": [str(r["page"]) for r in results]
    }

@traceable(run_name="rag_generate_answer")
def generate_answer(state: RAGState) -> Dict:
    """RAGで回答を生成"""
    answer = rag_engine.generate_answer(
        query=state["question"],
        context=state["context"]
    )
    return {"answer": answer}

# -------------------
# Graph構築
# -------------------
graph_builder = StateGraph(RAGState)
graph_builder.add_node("search_context", search_context)
graph_builder.add_node("generate_answer", generate_answer)

graph_builder.add_edge(START, "search_context")
graph_builder.add_edge("search_context", "generate_answer")
graph_builder.add_edge("generate_answer", END)

graph = graph_builder.compile()
```

### 4. FastAPI プロキシルーター

**ファイル**: `backend/app/routers/chat.py` (新規作成)

```python
"""RAGチャットルーター（LangGraph API プロキシ）"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests

router = APIRouter(prefix="/api/slides", tags=["chat"])

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]  # 出典ページ番号

@router.post("/{slide_id}/chat", response_model=ChatResponse)
async def chat_with_slide(slide_id: str, request: ChatRequest):
    """LangGraph RAGエージェントを呼び出し

    LangGraph API (port 2024) にプロキシして、
    RAGエージェントを実行する
    """
    try:
        # LangGraph APIにリクエスト
        response = requests.post(
            "http://localhost:2024/runs/stream",
            json={
                "assistant_id": "rag-agent",
                "input": {
                    "slide_id": slide_id,
                    "question": request.message
                },
                "stream_mode": ["values"]
            },
            stream=True
        )

        # SSEストリームから最終結果を取得
        final_state = None
        for line in response.iter_lines():
            if line:
                data = line.decode('utf-8')
                if data.startswith('data: '):
                    import json
                    final_state = json.loads(data[6:])

        # 回答と出典を返す
        return ChatResponse(
            answer=final_state["answer"],
            sources=final_state["sources"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 5. LangGraph設定に追加

**ファイル**: `backend/langgraph.json`

```json
{
  "dependencies": ["."],
  "graphs": {
    "slide_agent": "./app/agents/slide_workflow.py:graph",
    "rag_agent": "./app/agents/rag_agent.py:graph"
  },
  "env": ".env"
}
```

### 6. FastAPIルーター登録

**ファイル**: `backend/app/main.py` (既存ファイルに追加)

```python
from app.routers import chat

app.include_router(chat.router)
```

### 7. スライド生成時の自動インデックス化

**ファイル**: `backend/app/agents/slide_workflow.py` (既存ファイルに追加)

```python
from app.core.rag import RAGEngine

def save_and_render_slidev(state: State):
    """スライド保存 + PDF出力 + Vector DBインデックス化"""

    # ... 既存のスライド保存処理 ...

    # RAGのためにVector DBにインデックス化
    try:
        rag_engine = RAGEngine()
        rag_engine.index_slide(
            slide_id=slide_id,
            markdown=state["slide_md"]
        )
        result["log"] = _log(state, f"[rag] indexed {slide_id}")
    except Exception as e:
        # インデックス化失敗は警告のみ（クリティカルエラーではない）
        result["log"] = _log(state, f"[rag] index failed: {str(e)[:100]}")

    return result
```

---

## データベース設計

### Supabase テーブル

#### 1. slide_embeddings テーブル

```sql
CREATE TABLE slide_embeddings (
  id BIGSERIAL PRIMARY KEY,
  slide_id TEXT NOT NULL REFERENCES slides(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  page INT,
  content TEXT NOT NULL,
  embedding VECTOR(1536),
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. chat_messages テーブル

```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slide_id TEXT NOT NULL REFERENCES slides(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  sources TEXT[],
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_slide_id ON chat_messages(slide_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at DESC);
```

### スキーマ構成

```
slides テーブル（既存）
  ├── id: TEXT (PK)
  ├── title: TEXT
  ├── topic: TEXT
  ├── slide_md: TEXT
  ├── pdf_url: TEXT
  └── created_at: TIMESTAMP

slide_embeddings テーブル（新規）
  ├── id: BIGSERIAL (PK)
  ├── slide_id: TEXT (FK → slides.id)
  ├── chunk_index: INT
  ├── page: INT
  ├── content: TEXT
  ├── embedding: VECTOR(1536)
  └── created_at: TIMESTAMP

chat_messages テーブル（新規）
  ├── id: UUID (PK)
  ├── slide_id: TEXT (FK → slides.id)
  ├── role: TEXT
  ├── content: TEXT
  ├── sources: TEXT[]
  └── created_at: TIMESTAMP
```

### ER図

```
┌─────────────────┐
│     slides      │
│─────────────────│
│ id (PK)         │
│ title           │
│ slide_md        │
└─────────────────┘
        │
        │ 1:N
        ├─────────────────────────────┐
        │                             │
        ▼                             ▼
┌─────────────────┐         ┌─────────────────┐
│slide_embeddings │         │  chat_messages  │
│─────────────────│         │─────────────────│
│ id (PK)         │         │ id (PK)         │
│ slide_id (FK)   │         │ slide_id (FK)   │
│ content         │         │ role            │
│ embedding       │         │ content         │
│ page            │         │ sources[]       │
└─────────────────┘         └─────────────────┘
```

---

## 実装チェックリスト

### Supabase Vector 有効化
- [ ] `vector`拡張の有効化
- [ ] `slide_embeddings`テーブル作成
- [ ] `match_slide_chunks()`関数作成
- [ ] ivfflatインデックス作成

### RAGEngine 実装
- [ ] `index_slide()`: チャンク化 + Embeddings生成
- [ ] `search()`: Supabase Vector検索
- [ ] `generate_answer()`: RAGプロンプト + LLM回答

### LangGraph RAGエージェント
- [ ] `RAGState`定義
- [ ] `search_context`ノード実装
- [ ] `generate_answer`ノード実装
- [ ] グラフ構築

### FastAPI プロキシルーター
- [ ] `POST /api/slides/{id}/chat`エンドポイント
- [ ] LangGraph API (port 2024) へのプロキシ
- [ ] SSEストリーム処理

### LangGraph設定更新
- [ ] `langgraph.json`に`rag_agent`追加
- [ ] `main.py`にルーター登録

### スライド生成時の自動インデックス化
- [ ] `save_and_render_slidev()`にRAG indexing追加

### Supabase テーブル
- [ ] `chat_messages`テーブル作成

### 依存関係追加
- [ ] `pgvector>=0.3.0`
- [ ] `langchain-text-splitters>=0.3.0`

---

## 依存関係

### requirements.txt に追加

```txt
# RAG機能 (Phase 4)
pgvector>=0.3.0
langchain-text-splitters>=0.3.0
```

### インストール

```bash
cd backend
pip install pgvector langchain-text-splitters
```

---

## テスト計画

### 単体テスト

```python
# backend/tests/test_rag_engine.py
import pytest
from app.core.rag import RAGEngine

def test_index_slide():
    """スライドインデックス化のテスト"""
    engine = RAGEngine()
    engine.index_slide("test-123", "# Test Slide\n\nThis is a test.")
    # ... アサーション

def test_search():
    """Vector検索のテスト"""
    engine = RAGEngine()
    results = engine.search("test-123", "what is this?", top_k=3)
    assert len(results) <= 3
    # ... アサーション
```

### 統合テスト

```python
# backend/tests/test_rag_agent.py
from app.agents.rag_agent import graph

def test_rag_agent():
    """RAGエージェント統合テスト"""
    result = graph.invoke({
        "slide_id": "test-123",
        "question": "このスライドの要点は？"
    })
    assert "answer" in result
    assert "sources" in result
```

### E2Eテスト

```bash
# curlでAPIテスト
curl -X POST http://localhost:8001/api/slides/test-123/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "このスライドの要点は？"}'
```

---

## デプロイ手順

### ローカル開発

```bash
# 1. Supabase Vector有効化（Dashboard でSQL実行）

# 2. 依存関係インストール
cd backend
pip install -r requirements.txt

# 3. LangGraph dev server起動
python3.11 -m langgraph_cli dev --host 0.0.0.0 --port 2024

# 4. FastAPI server起動（別ターミナル）
cd backend/app
python3 main.py
```

### 本番環境

```bash
# 1. Supabase Production環境でSQL実行

# 2. 環境変数設定
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_KEY=your-service-key
export OPENAI_API_KEY=your-openai-key

# 3. Railway/Renderにデプロイ
# - LangGraph server: port 2024
# - FastAPI server: port 8001
```

---

## トラブルシューティング

### 1. Vector検索結果が0件

**原因**: スライドがインデックス化されていない

**解決策**:
```sql
-- slide_embeddingsを確認
SELECT slide_id, COUNT(*) FROM slide_embeddings GROUP BY slide_id;
```

### 2. Embeddingsエラー

**原因**: OpenAI APIキーが未設定

**解決策**:
```bash
export OPENAI_API_KEY=sk-...
```

### 3. LangGraph API接続エラー

**原因**: port 2024が起動していない

**解決策**:
```bash
# LangGraph dev serverを起動
python3.11 -m langgraph_cli dev --port 2024
```

### 4. Supabase RPC呼び出しエラー

**原因**: `match_slide_chunks()`関数が未作成

**解決策**:
```sql
-- SQLを再実行して関数を作成
CREATE OR REPLACE FUNCTION match_slide_chunks(...) ...
```

---

## 参考リンク

- [Supabase Vector (pgvector) Documentation](https://supabase.com/docs/guides/ai/vector-columns)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain RAG Tutorial](https://python.langchain.com/docs/use_cases/question_answering/)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)

---

**最終更新**: 2025-10-30
**実装状況**: 未実装（Phase 4）
**レビュー者**: -
**承認者**: -
