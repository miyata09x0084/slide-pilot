# 動画表示問題の修正設計書

## 問題概要

動画が表示されるスライドと表示されないスライドがある。

## 原因分析

`video_url`がフロントエンドに正しく渡されていない箇所が3つある。

### 1. バックエンド: get_slides_by_user()のSELECTクエリ

**ファイル**: `backend/app/core/supabase.py`

一覧取得APIで`video_url`がSELECT対象に含まれていない。

```python
# 現状
.select("id, title, topic, created_at, pdf_url")

# あるべき姿
.select("id, title, topic, created_at, pdf_url, video_url")
```

### 2. フロントエンド: SlideData型定義

**ファイル**: `frontend/src/types/index.ts`

SSEストリーミングで受信したデータを保持する`SlideData`型に`video_url`フィールドがない。

```typescript
// 現状
export interface SlideData {
  path?: string;
  title?: string;
  slide_id?: string;
  pdf_url?: string;
}

// あるべき姿
export interface SlideData {
  path?: string;
  title?: string;
  slide_id?: string;
  pdf_url?: string;
  video_url?: string;
}
```

### 3. フロントエンド: useReactAgent.tsのsetSlideData()

**ファイル**: `frontend/src/features/generation/hooks/useReactAgent.ts`

SSEストリーミングでツール結果を受信した際、`video_url`を状態に保存していない。

```typescript
// 現状
setSlideData({
  path: result.slide_path || result.path,
  title: result.title || '動画',
  slide_id: result.slide_id,
  pdf_url: result.pdf_url
});

// あるべき姿
setSlideData({
  path: result.slide_path || result.path,
  title: result.title || '動画',
  slide_id: result.slide_id,
  pdf_url: result.pdf_url,
  video_url: result.video_url
});
```

## 影響範囲

- `SlideContentViewer.tsx`: 変更不要（既に`slide.video_url`を使った表示ロジックが実装済み）
- 詳細API（`/slides/{id}/markdown`）: 変更不要（既に`video_url`を返している）
- `Slide`型、`SlideDetail`型: 変更不要（既に`video_url`フィールドを持っている）

## 修正ファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `backend/app/core/supabase.py` | `get_slides_by_user()`のSELECTに`video_url`を追加 |
| `frontend/src/types/index.ts` | `SlideData`型に`video_url`フィールドを追加 |
| `frontend/src/features/generation/hooks/useReactAgent.ts` | `setSlideData()`に`video_url`を追加 |

## テスト項目

1. フロントエンドのビルドが通ること（`npm run build`）
2. ダッシュボード一覧APIのレスポンスに`video_url`が含まれること
3. スライド詳細ページで動画プレイヤーが表示されること
4. 生成直後のページ遷移で動画が表示されること
