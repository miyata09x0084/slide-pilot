# サンプルスライド表示機能 設計書

## 概要

新規ユーザーに使用イメージを持たせるため、ダッシュボードに生成コンテンツのサンプルを表示する機能を追加する。

## 目的

- 新規ユーザーが具体的な使用イメージを持てるようにする
- 空状態のダッシュボードでもコンテンツが表示される
- サンプルから「自分も作りたい」という動機付けを行う

## 要件

### 機能要件

1. **サンプルスライドの表示**
   - ダッシュボードに「📖 サンプルスライド」セクションを追加
   - PDF解析系のスライドのみ表示（AI要約コンテンツは除外）
   - 2-3個のサンプルを固定表示

2. **サンプルの選定基準**
   - 品質の高いスライド（評価スコア8.0以上）
   - 多様なユースケースをカバー
   - 視覚的に魅力的なデザイン
   - 実用的な内容

3. **サンプルの候補**
   - `multilingual-ai-document-analysis_slidev.pdf` - 多言語AIで文書解析（PaddleOCR-VL）
   - `learning-spatial-understanding-2d-3d_slidev.pdf` - 2Dと3Dで学ぶ空間理解（Concerto）
   - その他のPDF解析系スライド

### 非機能要件

1. **パフォーマンス**
   - サンプルデータは静的に配信（キャッシュ可能）
   - 初回ロード時間への影響を最小化

2. **ユーザビリティ**
   - サンプルと自分のスライドの区別が明確
   - サンプルは閲覧専用（編集不可）

## アーキテクチャ

### バックエンド

#### 新規エンドポイント: `GET /api/samples`

**レスポンス例:**
```json
{
  "samples": [
    {
      "id": "sample-multilingual-ocr",
      "title": "多言語AIで文書解析",
      "pdf_path": "/samples/multilingual-ai-document-analysis_slidev.pdf",
      "md_path": "/samples/multilingual-ai-document-analysis_slidev.md",
      "thumbnail": "/samples/thumbnails/multilingual-ocr.png",
      "created_at": "2025-01-15T00:00:00Z",
      "is_sample": true
    },
    {
      "id": "sample-spatial-learning",
      "title": "2Dと3Dで学ぶ空間理解",
      "pdf_path": "/samples/learning-spatial-understanding-2d-3d_slidev.pdf",
      "md_path": "/samples/learning-spatial-understanding-2d-3d_slidev.md",
      "thumbnail": "/samples/thumbnails/spatial-learning.png",
      "created_at": "2025-01-15T00:00:00Z",
      "is_sample": true
    }
  ]
}
```

#### ディレクトリ構成

```
backend/
├── app/
│   └── routers/
│       └── samples.py          # 新規: サンプルスライドAPIルーター
├── data/
│   ├── samples/                # 新規: サンプルスライド専用ディレクトリ
│   │   ├── multilingual-ai-document-analysis_slidev.pdf
│   │   ├── multilingual-ai-document-analysis_slidev.md
│   │   ├── learning-spatial-understanding-2d-3d_slidev.pdf
│   │   ├── learning-spatial-understanding-2d-3d_slidev.md
│   │   └── thumbnails/         # オプション: サムネイル画像
│   │       ├── multilingual-ocr.png
│   │       └── spatial-learning.png
│   └── slides/                 # 既存: ユーザー生成スライド
```

#### 実装ファイル

**`backend/app/routers/samples.py`**
```python
from fastapi import APIRouter
from typing import List
import os

router = APIRouter(prefix="/api", tags=["samples"])

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "../../data/samples")

SAMPLE_SLIDES = [
    {
        "id": "sample-multilingual-ocr",
        "title": "多言語AIで文書解析",
        "pdf_path": "/samples/multilingual-ai-document-analysis_slidev.pdf",
        "md_path": "/samples/multilingual-ai-document-analysis_slidev.md",
        "created_at": "2025-01-15T00:00:00Z",
        "is_sample": True
    },
    {
        "id": "sample-spatial-learning",
        "title": "2Dと3Dで学ぶ空間理解",
        "pdf_path": "/samples/learning-spatial-understanding-2d-3d_slidev.pdf",
        "md_path": "/samples/learning-spatial-understanding-2d-3d_slidev.md",
        "created_at": "2025-01-15T00:00:00Z",
        "is_sample": True
    }
]

@router.get("/samples")
async def get_samples():
    """サンプルスライド一覧を取得"""
    return {"samples": SAMPLE_SLIDES}
```

**`backend/app/main.py`への追加**
```python
from app.routers import samples

app.include_router(samples.router)
```

### フロントエンド

#### UI設計

**ダッシュボードレイアウト**
```
┌─────────────────────────────────────────────┐
│  📚 ラクヨミ アシスタントAI             [User] │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │ 📄      │  │ 📊      │  │ 📊      │    │
│  │ 新規作成│  │ スライド1│  │ スライド2│    │
│  │         │  │ 2025/1/15│  │ 2025/1/14│    │
│  └─────────┘  └─────────┘  └─────────┘    │
│                                             │
│  📖 サンプルスライド                        │
│  ┌─────────┐  ┌─────────┐                 │
│  │ 📚      │  │ 🎯      │                 │
│  │多言語AI  │  │2D&3D    │                 │
│  │サンプル  │  │サンプル  │                 │
│  └─────────┘  └─────────┘                 │
│                                             │
└─────────────────────────────────────────────┘
```

#### コンポーネント修正

**`frontend/src/features/dashboard/DashboardPage.tsx`への追加**

```typescript
import { useSamples } from "./api/get-samples";

export default function DashboardPage() {
  // 既存コード...

  // サンプルスライドを取得
  const { data: samplesData } = useSamples({ enabled: !!user });
  const samples = samplesData?.samples || [];

  return (
    <div style={styles.container}>
      {/* ヘッダー */}
      {/* ... */}

      {/* カードグリッド */}
      <div className="dashboard-grid" style={styles.gridContainer}>
        {/* 新規作成カード */}
        <UnifiedCard
          icon="📄"
          title="新規作成"
          subtitle="PDFを理解する"
          onClick={handleNewSlide}
          variant="primary"
          className="card-default"
        />

        {/* ユーザーのスライド履歴 */}
        {displayedSlides.map((slide) => (
          <UnifiedCard
            key={slide.id}
            icon="📊"
            title={slide.title}
            subtitle={formattedDate}
            onClickWithArg={handleSlideClick}
            clickArg={slide.id}
            variant="history"
            className="card-default"
          />
        ))}

        {/* サンプルセクション区切り */}
        {samples.length > 0 && (
          <div style={styles.sectionDivider}>
            <h2 style={styles.sectionTitle}>📖 サンプルスライド</h2>
          </div>
        )}

        {/* サンプルスライドカード */}
        {samples.map((sample) => (
          <UnifiedCard
            key={sample.id}
            icon="📚"
            title={sample.title}
            subtitle="サンプル"
            onClickWithArg={handleSlideClick}
            clickArg={sample.id}
            variant="sample"
            className="card-sample"
          />
        ))}
      </div>
    </div>
  );
}
```

**新規API Hook: `frontend/src/features/dashboard/api/get-samples.ts`**

```typescript
import { useQuery } from "@tanstack/react-query";

interface Sample {
  id: string;
  title: string;
  pdf_path: string;
  md_path: string;
  created_at: string;
  is_sample: boolean;
}

interface SamplesResponse {
  samples: Sample[];
}

export const useSamples = (options?: { enabled?: boolean }) => {
  return useQuery<SamplesResponse>({
    queryKey: ["samples"],
    queryFn: async () => {
      const response = await fetch("http://localhost:8001/api/samples");
      if (!response.ok) {
        throw new Error("Failed to fetch samples");
      }
      return response.json();
    },
    staleTime: Infinity, // サンプルは静的なので無期限キャッシュ
    ...options,
  });
};
```

#### スタイル追加

**`DashboardPage.tsx`のスタイルオブジェクトに追加**

```typescript
const styles: Record<string, React.CSSProperties> = {
  // 既存スタイル...

  sectionDivider: {
    gridColumn: "1 / -1",
    marginTop: "20px",
    marginBottom: "10px",
  },
  sectionTitle: {
    fontSize: "18px",
    fontWeight: "600",
    color: "#374151",
    margin: 0,
  },
};
```

**`UnifiedCard.tsx`への`variant="sample"`追加**

```typescript
export interface UnifiedCardProps {
  // 既存props...
  variant?: "primary" | "history" | "more" | "sample"; // "sample"追加
}

// スタイル定義に追加
const sampleCardStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
  color: "white",
  border: "2px solid #667eea",
};
```

### スライド詳細ページの修正

**`frontend/src/features/slide/SlideDetailPage.tsx`**

サンプルスライドの場合、「サンプル」バッジを表示し、編集機能を非表示にする。

```typescript
export default function SlideDetailPage() {
  const { slideId } = useParams();
  const isSample = slideId?.startsWith("sample-");

  return (
    <div>
      {isSample && (
        <div style={styles.sampleBadge}>
          📚 サンプル（閲覧専用）
        </div>
      )}
      {/* 既存のスライド表示コード */}
    </div>
  );
}
```

## 実装手順

### Phase 1: バックエンド実装

1. サンプルスライドディレクトリ作成
   ```bash
   mkdir -p backend/data/samples
   ```

2. サンプルファイルを選定・コピー
   ```bash
   cp backend/data/slides/multilingual-ai-document-analysis_slidev.* backend/data/samples/
   cp backend/data/slides/learning-spatial-understanding-2d-3d_slidev.* backend/data/samples/
   ```

3. `backend/app/routers/samples.py`実装

4. `backend/app/main.py`にルーター追加

5. 動作確認
   ```bash
   curl http://localhost:8001/api/samples
   ```

### Phase 2: フロントエンド実装

1. `frontend/src/features/dashboard/api/get-samples.ts`実装

2. `frontend/src/features/dashboard/DashboardPage.tsx`修正
   - サンプル取得ロジック追加
   - セクション区切り追加
   - サンプルカード表示

3. `frontend/src/features/dashboard/components/UnifiedCard.tsx`修正
   - `variant="sample"`スタイル追加

4. `frontend/src/features/slide/SlideDetailPage.tsx`修正
   - サンプルバッジ表示

### Phase 3: テスト

1. **単体テスト**
   - サンプルAPI: `GET /api/samples`のレスポンス確認
   - React Hook: `useSamples()`のデータ取得確認

2. **統合テスト**
   - ダッシュボード表示: サンプルカードが正しく表示されるか
   - サンプルクリック: 詳細ページに遷移するか
   - サンプルバッジ: 「サンプル（閲覧専用）」が表示されるか

3. **E2Eテスト**
   - 新規ユーザーがログイン → サンプルが表示される
   - サンプルクリック → PDF/Markdown閲覧可能
   - 自分のスライドとサンプルの区別が明確

## セキュリティ考慮事項

- サンプルスライドは公開データのため、認証不要でアクセス可能
- サンプルのパスは固定値のみ許可（パストラバーサル対策）
- ユーザーはサンプルを編集・削除できない

## パフォーマンス最適化

- サンプルデータは静的配信（CDN可能）
- React Queryで無期限キャッシュ（`staleTime: Infinity`）
- サンプルファイルは最小限（2-3個）

## 今後の拡張案

1. **サムネイル画像生成**
   - Slidev PDFの1ページ目をサムネイル化
   - カードにプレビュー表示

2. **カテゴリフィルタ**
   - 「技術論文」「ビジネス文書」などカテゴリ分け
   - タグ機能追加

3. **サンプルのテンプレート化**
   - サンプルを元に新規作成
   - 「このサンプルを元に作成」ボタン

4. **動的サンプル**
   - 管理画面からサンプルを追加/削除
   - ユーザー投稿のベストプラクティス共有

## 参考資料

- 既存スライド例: `backend/data/slides/multilingual-ai-document-analysis_slidev.pdf`
- ダッシュボード実装: `frontend/src/features/dashboard/DashboardPage.tsx`
- React Query ドキュメント: https://tanstack.com/query/latest
