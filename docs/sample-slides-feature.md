# サンプルスライド表示機能 実装ドキュメント

## 概要

新規ユーザーに使用イメージを即座に提供するため、ダッシュボードの**最上部**にサンプルスライドセクションを配置しました。サンプルを最初に見せることで、ユーザーが即座にAI生成スライドの品質を確認し、機能を体験できます。

## 目的

- **即座の体験**: 新規ユーザーがログイン直後にサンプルを発見できる
- **使用イメージの提供**: 空状態のダッシュボードでも魅力的なコンテンツを表示
- **コンバージョン促進**: 「自分も作りたい」という動機付けを最大化

## 戦略的決定

### サンプルセクションを最上部に配置

**理由**:
1. 新規ユーザーは履歴スライドを持っていない
2. スクロール不要で即座にサンプルを発見できる
3. 視覚的インパクトで機能の価値を伝達

**配置順序**:
```
1. ヒーローバナー「サンプルスライドで機能を体験」
2. サンプルカード（2件）
3. セクション区切り「あなたのスライド」
4. 新規作成カード
5. 履歴スライド
```

## アーキテクチャ（実装版）

### データモデル

#### Supabase実データ方式

サンプルスライドはSupabaseの`slides`テーブルに実データとして格納されています。

**固定UUID**:
- サンプル1: `11111111-1111-1111-1111-111111111111` - 「速いAIの秘密」
- サンプル2: `22222222-2222-2222-2222-222222222222` - 「AIアートの秘密」

**サンプルユーザーID**: `00000000-0000-0000-0000-000000000000`

**メリット**:
- 通常のスライドと同じAPIで取得可能
- Supabase Storageに実ファイルが存在
- RLSポリシーで適切にアクセス制御

### セキュリティ: RLSポリシー

```sql
CREATE POLICY "Sample slides are viewable by everyone"
ON public.slides
FOR SELECT
USING (user_id::text = '00000000-0000-0000-0000-000000000000');
```

**重要**:
- `user_id::text`にキャスト（UUID型とtext型の比較エラー回避）
- サンプルスライドのみ全員が閲覧可能
- ユーザースライドは通常のRLSポリシーで保護

### バックエンド実装

#### ファイル構成

```
backend/
├── app/
│   └── routers/
│       ├── samples.py          # サンプルスライドAPI（固定UUIDリスト返却）
│       └── slides.py           # スライドAPI（サンプルアクセス制御追加）
├── scripts/
│   ├── seed_sample_slides.py         # サンプル初期投入スクリプト
│   ├── update_sample_slides.py       # サンプル更新スクリプト
│   ├── add_sample_rls_policy.sql     # RLSポリシー追加SQL
│   └── cleanup_rls_policies.sql      # 開発用ポリシー削除SQL
└── data/
    └── samples/                      # 参考用ローカルファイル（オプション）
```

#### API実装: `backend/app/routers/samples.py`

```python
from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

# 固定サンプルスライドID（Supabaseに登録済み）
SAMPLE_SLIDE_IDS = [
    "11111111-1111-1111-1111-111111111111",  # 速いAIの秘密
    "22222222-2222-2222-2222-222222222222",  # AIアートの秘密
]

@router.get("/samples")
async def get_samples():
    """サンプルスライド一覧を取得（固定UUIDリスト）"""
    return {"samples": SAMPLE_SLIDE_IDS}
```

**設計思想**:
- シンプルな固定リスト返却（Supabase非依存）
- 詳細データは通常のスライドAPIで取得
- スケーラビリティ: サンプル追加時はIDを追加するだけ

#### アクセス制御: `backend/app/routers/slides.py`

```python
@router.get("/slides/{slide_id}/markdown")
async def get_slide_markdown(
    slide_id: str,
    user_id: str = Depends(verify_token)
) -> Dict[str, Any]:
    slide = get_slide_by_id(slide_id)
    if not slide:
        raise HTTPException(status_code=404, detail="スライドが見つかりません")

    # サンプルスライド（user_id = 00000000-...）は全員アクセス可能
    SAMPLE_USER_ID = "00000000-0000-0000-0000-000000000000"
    is_sample = slide.get("user_id") == SAMPLE_USER_ID

    # RLS + 念のためユーザーID照合（サンプルスライドは除外）
    if not is_sample and slide.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="アクセス権限がありません")

    return {
        "slide_id": slide["id"],
        "title": slide["title"],
        "markdown": slide["slide_md"],
        "created_at": slide["created_at"],
        "pdf_url": slide.get("pdf_url")
    }
```

**二重チェックの理由**:
1. **RLS**: データベースレベルのセキュリティ（最終防御）
2. **アプリケーション**: ビジネスロジックの明示（可読性、デバッグ容易性）

### フロントエンド実装

#### ファイル構成

```
frontend/src/features/dashboard/
├── DashboardPage.tsx           # メインダッシュボード（レイアウト変更）
├── api/
│   └── get-samples.ts          # サンプルデータ取得Hook
└── components/
    └── UnifiedCard.tsx         # カードコンポーネント（sampleバリアント追加）
```

#### API Hook: `frontend/src/features/dashboard/api/get-samples.ts`

```typescript
import { useQuery } from "@tanstack/react-query";

export interface Sample {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  pdf_url?: string;
  description?: string; // サンプルの説明文
  readTime?: string;    // 読了時間の目安
}

interface SamplesResponse {
  samples: Sample[];
}

export const useSamples = (options?: { enabled?: boolean }) => {
  return useQuery<SamplesResponse>({
    queryKey: ["samples"],
    queryFn: async () => {
      // 固定データを返す（将来的にAPIから取得も可能）
      return {
        samples: [
          {
            id: "11111111-1111-1111-1111-111111111111",
            title: "速いAIの秘密",
            topic: "速いAIの秘密",
            created_at: "2025-01-15T00:00:00Z",
            description: "Kimi Linearの仕組みを対話形式で理解",
            readTime: "3分",
          },
          {
            id: "22222222-2222-2222-2222-222222222222",
            title: "AIアートの秘密",
            topic: "AIアートの秘密",
            created_at: "2025-01-15T00:00:00Z",
            description: "ComfyUI-Copilotの使い方を初心者向けに解説",
            readTime: "3分",
          },
        ],
      };
    },
    staleTime: Infinity, // サンプルは静的なので無期限キャッシュ
    ...options,
  });
};
```

## UI/UX改善内容

### 1. ヒーローバナー

**目的**: サンプルの存在を強調し、価値提案を明確化

**デザイン**:
- グラデーション背景（#667eea → #764ba2）
- 大きなアイコン（📚 48px）
- メインメッセージ: 「サンプルスライドで機能を体験」
- サブメッセージ: 「まずはサンプルで、AIが生成するスライドの品質を確認してみましょう」

### 2. サンプルカードのデザイン強化

**アイコンサイズ**: 36px → 48px（視覚的インパクト向上）
**サブタイトル**: 説明文表示（例: 「Kimi Linearの仕組みを対話形式で理解」）
**ホバーアニメーション**:
- 上昇効果（`translateY(-4px)`）
- 強いシャドウ（`0 8px 16px rgba(0,0,0,0.15)`）

### 3. レイアウト最適化: グリッド分割方式

#### 課題

CSSグリッドの`gridAutoRows: minHeight(200px, auto)`がセクションタイトルにも適用され、余白が発生。

#### 解決策

グリッドを分割し、セクションタイトルをグリッド外に配置:

1. サンプルグリッド（独立したグリッドコンテナ）
2. セクションタイトル（通常のブロック要素）
3. ユーザースライドグリッド（上部padding削除）

**効果**: セクションタイトル下の余白 40px → 8px（-80%改善）

## サンプルコンテンツ

### 1. 「速いAIの秘密」

- **テーマ**: Kimi Linearの仕組み解説
- **フォーマット**: Slidev（YAMLフロントマター、apple-basic theme）
- **特徴**:
  - 先生-生徒の対話形式
  - Mermaid flowchart
  - 技術的な概念を初心者向けに解説
- **サンプルID**: `11111111-1111-1111-1111-111111111111`

### 2. 「AIアートの秘密」

- **テーマ**: ComfyUI-Copilotの使い方解説
- **フォーマット**: Slidev（YAMLフロントマター、apple-basic theme）
- **特徴**:
  - 先生-生徒の対話形式
  - Mermaid flowchart + mindmap
  - 初心者向けのツール紹介
- **サンプルID**: `22222222-2222-2222-2222-222222222222`

### サンプル選定基準

- ✅ 最新Slidev形式（YAMLフロントマター必須）
- ✅ Mermaid図を含む（視覚的魅力）
- ✅ 対話形式（わかりやすさ）
- ✅ 技術的に正確（品質担保）

## 実装手順

### Phase 1: Supabase準備 ✅

1. **RLSポリシー追加**
   ```bash
   # Supabase SQL Editorで実行
   cat backend/scripts/add_sample_rls_policy.sql
   ```

2. **サンプルデータ投入**（初回のみ）
   ```bash
   cd backend
   python3 scripts/seed_sample_slides.py
   ```

3. **サンプル更新**（コンテンツ変更時）
   ```bash
   cd backend
   python3 scripts/update_sample_slides.py
   ```

### Phase 2: バックエンド実装 ✅

1. `backend/app/routers/samples.py` 実装
2. `backend/app/routers/slides.py` にサンプルアクセス制御追加
3. `backend/app/main.py` にルーター登録

### Phase 3: フロントエンド実装 ✅

1. `frontend/src/features/dashboard/api/get-samples.ts` 実装
2. `frontend/src/features/dashboard/DashboardPage.tsx` 修正
3. `frontend/src/features/dashboard/components/UnifiedCard.tsx` 修正

### Phase 4: UI/UX最適化 ✅

1. サンプルセクション最上部配置
2. セクション区切りの余白問題解決
3. 視覚的階層の強化

## トラブルシューティング

### 問題: 403 Forbidden（サンプルスライドアクセス時）

**解決策**:
1. RLSポリシーを確認
2. `slides.py`のサンプル例外処理を確認
3. サンプルユーザーIDが正しいか確認

### 問題: セクションタイトル下の余白が大きい

**解決策**: グリッドを分割し、セクションタイトルをグリッド外に配置

### 問題: サンプルスライドが古いフォーマット

**解決策**: `backend/scripts/update_sample_slides.py`を実行

## 今後の拡張案

1. サムネイル画像追加
2. アニメーション改善
3. サンプルのバリエーション追加
4. 動的サンプル（管理画面）

## 参考資料

- Supabase RLS: `docs/supabase-rls-setup.md`
- UI/UX改善: `docs/sample-slides-ui-ux-improvements.md`
