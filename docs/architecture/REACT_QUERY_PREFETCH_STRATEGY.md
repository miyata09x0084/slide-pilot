# React Query プリフェッチ戦略

**作成日**: 2025-11-11
**目的**: React Router LoaderからReact Query移行時に失われたプリフェッチ機能の復活

---

## 背景

### Phase 2移行で失われた機能

BulletProof React移行のPhase 2で、React Router LoaderからReact Queryへ移行した際、**ページ遷移前のデータプリフェッチ機能が失われました**。

| 項目 | React Router Loader（旧） | React Query（現状） |
|------|-------------------------|------------------|
| **実行タイミング** | ナビゲーション前（ルート遷移前） | コンポーネントマウント時 |
| **プリフェッチ** | ✅ 自動（ページ表示前に完了） | ❌ デフォルトなし |
| **キャッシュ** | ❌ なし | ✅ あり（5分間） |
| **ユーザー体験** | ページ即表示 | ローディング表示後にコンテンツ表示 |

### 影響を受けるページ

1. **Dashboard** (`/`)
   - 旧: `dashboardLoader()` でスライド一覧をプリフェッチ
   - 現: `useSlides()` でマウント後に取得
   - 影響: ログイン後の初期表示が遅延

2. **Slide Detail** (`/slides/:slideId`)
   - 旧: `slideDetailLoader()` でスライド詳細をプリフェッチ
   - 現: `useSlideDetail()` でマウント後に取得
   - 影響: スライド一覧からの遷移時にローディング表示

---

## 実装方針

### Option 1: React Router Loader + React Query統合（採用）

**アプローチ**: React Router v7のLoader機能を残し、React Queryの`prefetchQuery`でキャッシュにデータを事前投入

**メリット**:
- ✅ プリフェッチ機能を完全復活
- ✅ React Queryのキャッシュ機能も活用
- ✅ ページ表示前にデータ取得完了
- ✅ 既存のAPI層（`features/*/api/`）を再利用

**デメリット**:
- ⚠️ Loader関数が必要（完全なhooksベースではない）
- ⚠️ QueryClientインスタンスをLoaderに渡す必要あり

---

## 実装手順

### Step 1: Loader関数の作成（React Query版）

#### Dashboard Loader

**ファイル**: `frontend/src/features/dashboard/loaders/dashboardLoader.ts`

```typescript
/**
 * dashboardLoader - React Router Loader with React Query prefetch
 * ページ遷移前にスライド履歴をReact Queryキャッシュにプリフェッチ
 */

import { QueryClient } from '@tanstack/react-query';
import { getSlides } from '../api/get-slides';

export const createDashboardLoader = (queryClient: QueryClient) => {
  return async () => {
    // localStorageからユーザー情報取得
    const savedUser = localStorage.getItem('user');
    if (!savedUser) return null;

    try {
      const user = JSON.parse(savedUser);

      // React Queryキャッシュにプリフェッチ
      await queryClient.prefetchQuery({
        queryKey: ['slides', user.email, 20],
        queryFn: () => getSlides({ user_id: user.email, limit: 20 }),
      });

      return null; // Loaderからデータを返さない（キャッシュのみ使用）
    } catch (err) {
      console.error('Failed to prefetch slides:', err);
      return null;
    }
  };
};
```

#### Slide Detail Loader

**ファイル**: `frontend/src/features/slide/loaders/slideDetailLoader.ts`

```typescript
/**
 * slideDetailLoader - React Router Loader with React Query prefetch
 * ページ遷移前にスライド詳細をReact Queryキャッシュにプリフェッチ
 */

import type { LoaderFunctionArgs } from 'react-router-dom';
import { QueryClient } from '@tanstack/react-query';
import { getSlideDetail } from '../api/get-slide-detail';

export const createSlideDetailLoader = (queryClient: QueryClient) => {
  return async ({ params }: LoaderFunctionArgs) => {
    const { slideId } = params;

    if (!slideId) {
      throw new Error('Slide ID is required');
    }

    try {
      // React Queryキャッシュにプリフェッチ
      await queryClient.prefetchQuery({
        queryKey: ['slide-detail', slideId],
        queryFn: () => getSlideDetail(slideId),
      });

      return null;
    } catch (err) {
      console.error('Failed to prefetch slide:', err);
      throw err; // エラーバウンダリで処理
    }
  };
};
```

### Step 2: Router設定の更新

**ファイル**: `frontend/src/app/router.tsx`

```typescript
/**
 * Router Configuration
 * Phase 5: File-based routing with React Query prefetch loaders
 */

import { createBrowserRouter, Navigate } from 'react-router-dom';
import { queryClient } from '@/lib/react-query';
import { LoginRoute } from './routes/login';
import { DashboardRoute } from './routes';
import { ProtectedLayout } from './routes/app/root';
import { GenerateRoute } from './routes/app/generate';
import { SlidesRoute } from './routes/app/slides';

// Loaderファクトリー関数をimport
import { createDashboardLoader } from '@/features/dashboard/loaders/dashboardLoader';
import { createSlideDetailLoader } from '@/features/slide/loaders/slideDetailLoader';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginRoute />,
  },
  {
    element: <ProtectedLayout />,
    children: [
      {
        path: '/',
        element: <DashboardRoute />,
        loader: createDashboardLoader(queryClient), // プリフェッチ追加
      },
      {
        path: '/generate/:threadId',
        element: <GenerateRoute />,
        // このページはSSEストリーミングのためプリフェッチ不要
      },
      {
        path: '/slides/:slideId',
        element: <SlidesRoute />,
        loader: createSlideDetailLoader(queryClient), // プリフェッチ追加
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
```

### Step 3: コンポーネント側の変更（不要）

**重要**: コンポーネント側（`DashboardPage.tsx`, `SlideDetailPage.tsx`）は**変更不要**です。

理由:
- `useSlides()` と `useSlideDetail()` のqueryKeyがLoader内の`prefetchQuery`と一致
- React Queryが自動的にキャッシュを使用
- キャッシュヒット時は即座にデータ返却、ローディング表示なし

```typescript
// DashboardPage.tsx（変更なし）
const { data } = useSlides(
  { user_id: user?.email || '', limit: 20 },
  { enabled: !!user?.email }
);
const slides = data?.slides || [];
```

### Step 4: 既存Loader関数の置き換え

既存の`dashboardLoader.ts`と`slideDetailLoader.ts`を上記の新実装で**上書き**します。

---

## データフロー

### プリフェッチあり（実装後）

```
1. ユーザーがリンククリック
   ↓
2. React Router Loader実行
   ↓
3. queryClient.prefetchQuery()
   ├── API呼び出し（getSlides/getSlideDetail）
   └── React Queryキャッシュに保存
   ↓
4. ページコンポーネントマウント
   ↓
5. useSlides()/useSlideDetail()実行
   ├── queryKeyでキャッシュ検索
   └── キャッシュヒット → 即座にデータ返却
   ↓
6. ローディング表示なしでコンテンツ表示 ✅
```

### プリフェッチなし（現状）

```
1. ユーザーがリンククリック
   ↓
2. ページコンポーネントマウント
   ↓
3. useSlides()/useSlideDetail()実行
   ├── キャッシュなし
   └── API呼び出し開始
   ↓
4. ローディング表示 ⏳
   ↓
5. APIレスポンス受信
   ↓
6. コンテンツ表示
```

---

## テスト戦略

### 既存テストの更新

**`dashboardLoader.test.ts`と`slideDetailLoader.test.ts`**:
- QueryClientのモックを追加
- `prefetchQuery`の呼び出しを検証
- キャッシュへのデータ投入を確認

```typescript
import { describe, it, expect, vi } from 'vitest';
import { QueryClient } from '@tanstack/react-query';
import { createDashboardLoader } from '../loaders/dashboardLoader';

describe('dashboardLoader with prefetch', () => {
  it('should prefetch slides to React Query cache', async () => {
    const queryClient = new QueryClient();
    const prefetchSpy = vi.spyOn(queryClient, 'prefetchQuery');

    const loader = createDashboardLoader(queryClient);

    localStorage.setItem('user', JSON.stringify({
      email: 'test@example.com',
    }));

    await loader();

    expect(prefetchSpy).toHaveBeenCalledWith({
      queryKey: ['slides', 'test@example.com', 20],
      queryFn: expect.any(Function),
    });
  });
});
```

### E2Eテストでの確認

**Playwright テスト**:
```typescript
test('Dashboard loads without loading indicator', async ({ page }) => {
  await page.goto('/login');
  // ログイン処理...

  await page.click('a[href="/"]');

  // ローディング表示がないことを確認
  await expect(page.locator('text=Loading...')).not.toBeVisible();

  // スライド一覧が即座に表示されることを確認
  await expect(page.locator('[data-testid="slide-card"]').first()).toBeVisible();
});
```

---

## パフォーマンス考慮

### キャッシュ戦略

**現在の設定**（`lib/react-query.ts`）:
```typescript
queries: {
  staleTime: 1000 * 60 * 5,  // 5分間キャッシュ有効
  gcTime: 1000 * 60 * 10,    // 10分間メモリ保持
}
```

**プリフェッチの影響**:
- ✅ 初回アクセス: Loader内でAPI呼び出し → ページ表示前に完了
- ✅ 5分以内の再アクセス: キャッシュから即座に取得、API呼び出しなし
- ✅ 5分経過後: バックグラウンドで再取得、古いデータを表示しつつ更新

### ネットワーク最適化

**並列プリフェッチ（将来の拡張）**:
複数のリソースを同時にプリフェッチする場合:
```typescript
await Promise.all([
  queryClient.prefetchQuery({ ... }),
  queryClient.prefetchQuery({ ... }),
]);
```

---

## クリーンアップ

### 不要ファイルの削除候補

実装完了後、以下のファイルは不要になります（Loader関数は置き換え済み）:

- ❌ 削除不要: `loaders/dashboardLoader.ts`（新実装で上書き）
- ❌ 削除不要: `loaders/slideDetailLoader.ts`（新実装で上書き）
- ✅ 更新必要: `__tests__/dashboardLoader.test.ts`（QueryClientモック追加）
- ✅ 更新必要: `__tests__/slideDetailLoader.test.ts`（QueryClientモック追加）

---

## 今後の拡張

### Link hover時のプリフェッチ（オプション）

さらなるUX向上のため、リンクホバー時にプリフェッチを追加:

```typescript
// components/SlideCard.tsx
import { useQueryClient } from '@tanstack/react-query';
import { getSlideDetail } from '@/features/slide/api/get-slide-detail';

function SlideCard({ slide }) {
  const queryClient = useQueryClient();

  const handleMouseEnter = () => {
    queryClient.prefetchQuery({
      queryKey: ['slide-detail', slide.id],
      queryFn: () => getSlideDetail(slide.id),
    });
  };

  return (
    <Link to={`/slides/${slide.id}`} onMouseEnter={handleMouseEnter}>
      {slide.title}
    </Link>
  );
}
```

---

## 参考リンク

- [React Query Prefetching](https://tanstack.com/query/latest/docs/react/guides/prefetching)
- [React Router v7 Loaders](https://reactrouter.com/en/main/route/loader)
- [React Query + React Router Integration](https://tkdodo.eu/blog/react-query-meets-react-router)

---

## まとめ

この実装により、以下を実現します:

✅ **Phase 2で失われたプリフェッチ機能の完全復活**
✅ **React Queryのキャッシュ機能との統合**
✅ **既存コンポーネントの変更なし**
✅ **ページ遷移時のローディング表示を排除**
✅ **ネットワーク効率の向上**（重複リクエスト防止）
