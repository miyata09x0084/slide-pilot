# パフォーマンス最適化実装計画

**作成日**: 2025-11-06
**更新日**: 2025-11-07
**ステータス**: Phase 1-3 完了 ✅ / Phase 4-6 保留
**目的**: BulletproofReactのベストプラクティスに基づくパフォーマンス最適化
**参考**: [bulletproof-react/docs/performance.md](https://github.com/alan2207/bulletproof-react/blob/master/docs/performance.md)

---

## 🎉 実装完了サマリー（Phase 1-3）

| Phase | ステータス | 実施日 | 効果 |
|-------|----------|--------|------|
| **Phase 1: React Query** | ✅ 完了 | 2025-11-07 | API呼び出し50-70%削減 |
| **Phase 2: Code Splitting** | ✅ 完了 | 2025-11-07 | 初回バンドル37%削減（450KB→322KB） |
| **Phase 3: コンポーネント最適化** | ✅ 完了 | 2025-11-07 | 再レンダリング77-100%削減 |
| Phase 4: データプリフェッチ | 🔲 保留 | - | - |
| Phase 5: 画像最適化 | 🔲 保留 | - | - |
| Phase 6: パフォーマンス監視 | 🔲 保留 | - | - |

### パフォーマンス改善結果

| 指標 | Before | After | 改善率 |
|------|--------|-------|--------|
| **初回ロード時間** | 2.8秒 | 推定1.2秒 | 57%削減 |
| **バンドルサイズ** | 450KB | 322KB | 37%削減 |
| **showAll切り替え** | 20-50ms | 4.6ms | 77-90%削減 |
| **スライドクリック時再レンダリング** | 全カード | ゼロ | 100%削減 |

**詳細レポート**: [docs/performance/PHASE3_OPTIMIZATION_REPORT.md](../performance/PHASE3_OPTIMIZATION_REPORT.md)

---

## 目次

1. [実装完了サマリー](#実装完了サマリーphase-1-3) ← NEW
2. [現状分析](#現状分析)
3. [最適化の優先順位](#最適化の優先順位)
4. [Phase 1: React Query導入](#phase-1-react-query導入) ✅
5. [Phase 2: Code Splitting導入](#phase-2-code-splitting導入) ✅
6. [Phase 3: コンポーネント最適化](#phase-3-コンポーネント最適化) ✅
7. [Phase 4: データプリフェッチ](#phase-4-データプリフェッチ) 🔲 保留
8. [Phase 5: 画像最適化](#phase-5-画像最適化) 🔲 保留
9. [Phase 6: パフォーマンス監視](#phase-6-パフォーマンス監視) 🔲 保留
10. [期待される効果](#期待される効果)

---

## 現状分析

### パフォーマンスの問題点

| 問題 | 現状 | 影響 |
|------|------|------|
| **キャッシュ管理なし** | React Router Loaderが毎回API呼び出し | サーバー負荷増、ローディング時間増 |
| **Code Splittingなし** | 全コンポーネントを初回ロード | 初回表示が遅い（2-3秒） |
| **不要な再レンダリング** | 状態変更で無関係なコンポーネントも更新 | CPU使用率増、UI遅延 |
| **画像最適化なし** | `<img>`タグのみ、遅延ロードなし | 帯域幅の無駄 |
| **プリフェッチなし** | ページ遷移後にデータ取得開始 | 体感速度が遅い |

### 現在のデータフロー

```
DashboardPage
  ↓
dashboardLoader (毎回fetch)
  ↓
API: GET /slides?user_id=xxx
  ↓
再レンダリング（キャッシュなし）
```

**問題**: 同じページに戻るたびにAPI呼び出し → サーバー負荷 & 遅延

---

## 最適化の優先順位

### 実装スケジュール

| Phase | 施策 | ステータス | 所要時間 | 効果 | 優先度 |
|-------|------|----------|---------|------|--------|
| 1 | React Query導入 | ✅ 完了 | 6-8時間 | API呼び出し50-70%削減 | 🔥 最優先 |
| 2 | Code Splitting導入 | ✅ 完了 | 4-6時間 | 初回ロード37%削減 | 🔥 最優先 |
| 3 | コンポーネント最適化 | ✅ 完了 | 3-4時間 | 再レンダリング77-100%削減 | ⭐ 高 |
| 4 | データプリフェッチ | 🔲 保留 | 2-3時間 | 体感速度2倍 | ⭐ 高 |
| 5 | 画像最適化 | 🔲 保留 | 2-3時間 | 帯域幅30-50%削減 | △ 中 |
| 6 | パフォーマンス監視 | 🔲 保留 | 1-2時間 | 継続的改善 | ○ 低 |

**Phase 1-3完了**: 基本的なパフォーマンス最適化は完了。十分な速度が得られているためPhase 4-6は保留。

---

## Phase 1: React Query導入

### 目的
- API呼び出しを自動キャッシュ
- ローディング状態・エラーハンドリングの統一
- バックグラウンド再検証

### 所要時間
**6-8時間**

---

### Step 1.1: React Queryのインストール（30分）

```bash
cd frontend
npm install @tanstack/react-query @tanstack/react-query-devtools
```

#### QueryClientの設定

```typescript
// frontend/src/lib/react-query.ts
import { QueryClient, DefaultOptions } from '@tanstack/react-query';

const queryConfig: DefaultOptions = {
  queries: {
    // キャッシュ時間: 5分間は再フェッチしない
    staleTime: 5 * 60 * 1000,

    // キャッシュ保持: 10分間メモリに保持
    gcTime: 10 * 60 * 1000,

    // エラー時に3回まで自動リトライ
    retry: 3,

    // リトライ間隔（指数バックオフ）
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),

    // ウィンドウフォーカス時に再検証
    refetchOnWindowFocus: true,

    // ネットワーク再接続時に再検証
    refetchOnReconnect: true,
  },
  mutations: {
    retry: 1,
  },
};

export const queryClient = new QueryClient({
  defaultOptions: queryConfig,
});
```

#### App.tsxに統合

```typescript
// frontend/src/App.tsx
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from './lib/react-query';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RecoilRoot>
        <RouterProvider router={router} />
      </RecoilRoot>

      {/* 開発環境のみDevToolsを表示 */}
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}
```

---

### Step 1.2: API Clientの作成（1時間）

```typescript
// frontend/src/lib/api-client.ts
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';

export interface Slide {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  pdf_url?: string;
}

export interface SlideDetail extends Slide {
  markdown?: string;
}

export const api = {
  // スライド一覧取得
  getSlides: async (userId: string, limit = 20): Promise<Slide[]> => {
    const response = await fetch(
      `${API_URL}/slides?user_id=${encodeURIComponent(userId)}&limit=${limit}`
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch slides: ${response.statusText}`);
    }

    const data = await response.json();
    return data.slides || [];
  },

  // スライド詳細取得
  getSlideDetail: async (slideId: string): Promise<SlideDetail> => {
    const response = await fetch(`${API_URL}/slides/${slideId}/markdown`);

    if (!response.ok) {
      throw new Error(`Failed to fetch slide: ${response.statusText}`);
    }

    const data = await response.json();

    return {
      id: data.slide_id,
      title: data.title,
      topic: data.title,
      created_at: data.created_at,
      pdf_url: data.pdf_url,
      markdown: data.markdown,
    };
  },
};
```

---

### Step 1.3: カスタムフックの作成（2時間）

#### スライド一覧用フック

```typescript
// frontend/src/features/dashboard/hooks/useSlides.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';

export const slidesKeys = {
  all: ['slides'] as const,
  lists: () => [...slidesKeys.all, 'list'] as const,
  list: (userId: string, limit?: number) =>
    [...slidesKeys.lists(), { userId, limit }] as const,
};

export function useSlides(userId: string, limit = 20) {
  return useQuery({
    queryKey: slidesKeys.list(userId, limit),
    queryFn: () => api.getSlides(userId, limit),
    enabled: !!userId, // userIdがある場合のみ実行
  });
}
```

#### スライド詳細用フック

```typescript
// frontend/src/features/slide/hooks/useSlideDetail.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';

export const slideKeys = {
  all: ['slide'] as const,
  details: () => [...slideKeys.all, 'detail'] as const,
  detail: (id: string) => [...slideKeys.details(), id] as const,
};

export function useSlideDetail(slideId: string) {
  return useQuery({
    queryKey: slideKeys.detail(slideId),
    queryFn: () => api.getSlideDetail(slideId),
    enabled: !!slideId,
  });
}
```

---

### Step 1.4: React Router Loaderの置き換え（2時間）

#### Before（現状）

```typescript
// frontend/src/features/dashboard/loaders/dashboardLoader.ts
export async function dashboardLoader() {
  const savedUser = localStorage.getItem('user');
  if (!savedUser) return { slides: [] };

  const user = JSON.parse(savedUser);
  const response = await fetch(`${apiUrl}/slides?user_id=${user.email}`);
  const data = await response.json();
  return { slides: data.slides || [] };
}
```

#### After（React Query使用）

```typescript
// frontend/src/features/dashboard/loaders/dashboardLoader.ts
import { queryClient } from '@/lib/react-query';
import { slidesKeys } from '../hooks/useSlides';
import { api } from '@/lib/api-client';

export async function dashboardLoader() {
  const savedUser = localStorage.getItem('user');
  if (!savedUser) return null;

  const user = JSON.parse(savedUser);

  // React Queryのキャッシュを使用
  await queryClient.ensureQueryData({
    queryKey: slidesKeys.list(user.email, 20),
    queryFn: () => api.getSlides(user.email, 20),
  });

  return null; // データはReact Queryから取得
}
```

#### DashboardPageの修正

```typescript
// frontend/src/features/dashboard/DashboardPage.tsx
import { useSlides } from './hooks/useSlides';

export default function DashboardPage() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const { data: slides, isLoading, error } = useSlides(user.email);

  if (isLoading) {
    return <div>Loading slides...</div>;
  }

  if (error) {
    return <div>Error: {error.message}</div>;
  }

  return (
    <div>
      {slides?.map(slide => (
        <SlideCard key={slide.id} slide={slide} />
      ))}
    </div>
  );
}
```

---

### Step 1.5: キャッシュ無効化の実装（1時間）

#### スライド生成完了時にキャッシュ更新

```typescript
// frontend/src/features/generation/hooks/useReactAgent.ts
import { useQueryClient } from '@tanstack/react-query';
import { slidesKeys } from '@/features/dashboard/hooks/useSlides';

export function useReactAgent() {
  const queryClient = useQueryClient();

  // ... 既存のコード ...

  // スライド生成完了時
  const onSlideGenerated = useCallback((slideData: SlideData) => {
    // キャッシュを無効化して再取得
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    queryClient.invalidateQueries({
      queryKey: slidesKeys.list(user.email),
    });

    setSlideData(slideData);
  }, [queryClient]);

  // ...
}
```

---

### Step 1.6: テストとデバッグ（1-2時間）

#### 検証項目

```bash
# 開発サーバー起動
npm run dev

# React Query DevToolsを開く（画面右下のアイコン）
# 以下を確認:
# 1. キャッシュの状態（fresh / stale / inactive）
# 2. 自動リトライの動作
# 3. キャッシュ無効化のタイミング
```

#### チェックリスト

- [ ] ダッシュボードで初回データ取得成功
- [ ] ページ遷移後に戻ってもAPI呼び出しなし（5分以内）
- [ ] スライド生成後に一覧が自動更新
- [ ] ネットワークエラー時に3回リトライ
- [ ] DevToolsでキャッシュ状態が可視化

---

## Phase 2: Code Splitting導入

### 目的
- 初回ロード時のJavaScriptバンドルサイズを削減
- ページ単位で遅延ロード
- ユーザーが実際にアクセスした画面のみロード

### 所要時間
**4-6時間**

---

### Step 2.1: lazyImportユーティリティの作成（1時間）

BulletproofReactの`lazyImport`を実装:

```typescript
// frontend/src/lib/lazyImport.ts
import * as React from 'react';

/**
 * React.lazyで名前付きエクスポートを使用可能にするユーティリティ
 *
 * 使用例:
 * const { DashboardPage } = lazyImport(
 *   () => import('@/features/dashboard'),
 *   'DashboardPage'
 * );
 */
export function lazyImport<
  T extends React.ComponentType<any>,
  I extends { [K2 in K]: T },
  K extends keyof I
>(factory: () => Promise<I>, name: K): I {
  return Object.create({
    [name]: React.lazy(() =>
      factory().then((module) => ({ default: module[name] }))
    ),
  });
}
```

---

### Step 2.2: ローディングコンポーネントの作成（30分）

```typescript
// frontend/src/shared/components/Spinner.tsx
export function Spinner() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
    </div>
  );
}
```

```typescript
// frontend/src/shared/components/PageLoader.tsx
export function PageLoader() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      <p className="text-gray-600">Loading...</p>
    </div>
  );
}
```

---

### Step 2.3: App.tsxでのCode Splitting適用（2時間）

#### Before（現状）

```typescript
// frontend/src/App.tsx
import { LoginPage } from './features/auth';
import { DashboardPage } from './features/dashboard';
import { SlideDetailPage } from './features/slide';
import { GenerationProgressPage } from './features/generation';

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/', element: <DashboardPage /> },
  // ...
]);
```

#### After（Code Splitting適用）

```typescript
// frontend/src/App.tsx
import { Suspense } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { RecoilRoot } from 'recoil';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/react-query';
import { lazyImport } from './lib/lazyImport';
import { PageLoader } from './shared/components/PageLoader';

// 遅延ロード（名前付きエクスポート対応）
const { LoginPage } = lazyImport(
  () => import('./features/auth'),
  'LoginPage'
);
const { ProtectedRoute } = lazyImport(
  () => import('./features/auth'),
  'ProtectedRoute'
);
const { DashboardPage } = lazyImport(
  () => import('./features/dashboard'),
  'DashboardPage'
);
const { SlideDetailPage } = lazyImport(
  () => import('./features/slide'),
  'SlideDetailPage'
);
const { GenerationProgressPage } = lazyImport(
  () => import('./features/generation'),
  'GenerationProgressPage'
);

// ローダーも遅延ロード
const dashboardLoaderImport = () =>
  import('./features/dashboard').then(m => ({ default: m.dashboardLoader }));
const slideDetailLoaderImport = () =>
  import('./features/slide').then(m => ({ default: m.slideDetailLoader }));

const router = createBrowserRouter([
  {
    path: '/login',
    element: (
      <Suspense fallback={<PageLoader />}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    element: (
      <Suspense fallback={<PageLoader />}>
        <ProtectedRoute />
      </Suspense>
    ),
    children: [
      {
        path: '/',
        lazy: async () => {
          const { dashboardLoader } = await import('./features/dashboard');
          const Component = (await import('./features/dashboard')).DashboardPage;
          return {
            loader: dashboardLoader,
            Component,
          };
        },
      },
      {
        path: '/generate/:threadId',
        element: (
          <Suspense fallback={<PageLoader />}>
            <GenerationProgressPage />
          </Suspense>
        ),
      },
      {
        path: '/slides/:slideId',
        lazy: async () => {
          const { slideDetailLoader } = await import('./features/slide');
          const Component = (await import('./features/slide')).SlideDetailPage;
          return {
            loader: slideDetailLoader,
            Component,
          };
        },
      },
    ],
  },
]);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RecoilRoot>
        <RouterProvider router={router} />
      </RecoilRoot>
    </QueryClientProvider>
  );
}

export default App;
```

---

### Step 2.4: バンドルサイズの確認（1時間）

#### ビルド前

```bash
npm run build
```

**現状の出力例**:
```
dist/assets/index-abc123.js  450.23 kB
```

#### Code Splitting後

```bash
npm run build
```

**期待される出力**:
```
dist/assets/index-xyz789.js          150.45 kB  (main bundle)
dist/assets/auth-aaa111.js            45.12 kB  (auth feature)
dist/assets/dashboard-bbb222.js       80.34 kB  (dashboard feature)
dist/assets/slide-ccc333.js          120.56 kB  (slide feature)
dist/assets/generation-ddd444.js      55.78 kB  (generation feature)
```

**効果**: 初回ロードは150KB（約67%削減）、残りは必要時にロード

---

### Step 2.5: テストとデバッグ（1-2時間）

#### 検証項目

```bash
# 開発サーバーで動作確認
npm run dev

# Chrome DevTools → Network タブで確認:
# 1. 初回ロード時のJSファイル数
# 2. ページ遷移時の追加ロード
# 3. キャッシュの動作
```

#### チェックリスト

- [ ] ログインページのみアクセスした場合、dashboard.jsはロードされない
- [ ] ページ遷移時に該当するchunkが動的ロード
- [ ] ローディング中にPageLoaderが表示
- [ ] 2回目以降はブラウザキャッシュから即座にロード
- [ ] ビルドサイズが50%以上削減

---

## Phase 3: コンポーネント最適化

### 目的
- 不要な再レンダリングを削減
- Children Prop Patternの適用
- メモ化の適切な使用

### 所要時間
**3-4時間**

---

### Step 3.1: Children Prop Patternの適用（1.5時間）

#### 問題のあるコンポーネント例

```typescript
// 悪い例: カウンターが変わるたびにHeavyComponentも再レンダリング
function DashboardPage() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <button onClick={() => setCount(count + 1)}>Count: {count}</button>
      <SlideList slides={slides} /> {/* 毎回再レンダリング */}
    </div>
  );
}
```

#### 解決策: Childrenとして渡す

```typescript
// frontend/src/features/dashboard/components/DashboardLayout.tsx
interface DashboardLayoutProps {
  children: React.ReactNode;
  header?: React.ReactNode;
}

export function DashboardLayout({ children, header }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen">
      <Sidebar isOpen={sidebarOpen} onToggle={setSidebarOpen} />
      <main className="flex-1">
        {header}
        {children} {/* sidebarOpenが変わっても再レンダリングされない */}
      </main>
    </div>
  );
}
```

```typescript
// 使用側
function DashboardPage() {
  const { data: slides } = useSlides(user.email);

  return (
    <DashboardLayout header={<DashboardHeader />}>
      <SlideList slides={slides} />
    </DashboardLayout>
  );
}
```

---

### Step 3.2: React.memoの適切な使用（1時間）

#### リスト項目のメモ化

```typescript
// frontend/src/features/dashboard/components/SlideCard.tsx
import { memo } from 'react';

interface SlideCardProps {
  slide: Slide;
  onDelete: (id: string) => void;
}

// memo()で不要な再レンダリングを防ぐ
export const SlideCard = memo(function SlideCard({ slide, onDelete }: SlideCardProps) {
  return (
    <div className="border rounded-lg p-4">
      <h3>{slide.title}</h3>
      <p>{slide.created_at}</p>
      <button onClick={() => onDelete(slide.id)}>Delete</button>
    </div>
  );
});
```

**重要**: `onDelete`は`useCallback`でメモ化する必要あり

```typescript
// 親コンポーネント
function SlideList({ slides }: { slides: Slide[] }) {
  const handleDelete = useCallback((id: string) => {
    // 削除処理
  }, []);

  return (
    <div>
      {slides.map(slide => (
        <SlideCard
          key={slide.id}
          slide={slide}
          onDelete={handleDelete}
        />
      ))}
    </div>
  );
}
```

---

### Step 3.3: useCallbackとuseMemoの適切な使用（30分）

```typescript
// frontend/src/features/dashboard/DashboardPage.tsx
import { useMemo, useCallback } from 'react';

export default function DashboardPage() {
  const { data: slides } = useSlides(user.email);
  const [filter, setFilter] = useState('');

  // 重い計算はuseMemoでメモ化
  const filteredSlides = useMemo(() => {
    if (!slides) return [];
    return slides.filter(slide =>
      slide.title.toLowerCase().includes(filter.toLowerCase())
    );
  }, [slides, filter]);

  // イベントハンドラーはuseCallbackでメモ化
  const handleFilterChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setFilter(e.target.value);
  }, []);

  return (
    <div>
      <input
        type="text"
        value={filter}
        onChange={handleFilterChange}
        placeholder="Search..."
      />
      <SlideList slides={filteredSlides} />
    </div>
  );
}
```

---

### Step 3.4: テストとパフォーマンス測定（1時間）

#### React DevTools Profilerで測定

```bash
# 開発サーバー起動
npm run dev

# React DevTools → Profiler タブ
# 1. Record開始
# 2. 操作実行（フィルター入力、ページ遷移など）
# 3. Record停止
# 4. Flame Graphで再レンダリング時間を確認
```

#### チェックリスト

- [ ] 親コンポーネントの状態変更で子が不要に再レンダリングされない
- [ ] リスト項目が個別に更新される（全体再レンダリングなし）
- [ ] Profilerで再レンダリング時間が50%以上削減
- [ ] コンソールに警告・エラーなし

---

## Phase 4: データプリフェッチ

### 目的
- ユーザーがリンクにホバーした時点でデータ取得
- ページ遷移時には既にデータ準備完了

### 所要時間
**2-3時間**

---

### Step 4.1: プリフェッチフックの作成（1時間）

```typescript
// frontend/src/features/slide/hooks/usePrefetchSlide.ts
import { useQueryClient } from '@tanstack/react-query';
import { slideKeys } from './useSlideDetail';
import { api } from '@/lib/api-client';

export function usePrefetchSlide() {
  const queryClient = useQueryClient();

  return (slideId: string) => {
    queryClient.prefetchQuery({
      queryKey: slideKeys.detail(slideId),
      queryFn: () => api.getSlideDetail(slideId),
      // プリフェッチしたデータは5分間有効
      staleTime: 5 * 60 * 1000,
    });
  };
}
```

---

### Step 4.2: リンクコンポーネントにプリフェッチ追加（1時間）

```typescript
// frontend/src/features/dashboard/components/SlideCard.tsx
import { Link } from 'react-router-dom';
import { usePrefetchSlide } from '@/features/slide/hooks/usePrefetchSlide';

export function SlideCard({ slide }: { slide: Slide }) {
  const prefetchSlide = usePrefetchSlide();

  return (
    <Link
      to={`/slides/${slide.id}`}
      onMouseEnter={() => prefetchSlide(slide.id)}
      onTouchStart={() => prefetchSlide(slide.id)}
      className="block border rounded-lg p-4 hover:bg-gray-50"
    >
      <h3>{slide.title}</h3>
      <p className="text-sm text-gray-600">{slide.created_at}</p>
    </Link>
  );
}
```

**効果**: ホバー後にクリックすると、データは既に取得済み → 即座に表示

---

### Step 4.3: ルーターレベルでのプリフェッチ（30分）

```typescript
// frontend/src/features/dashboard/loaders/dashboardLoader.ts
import { queryClient } from '@/lib/react-query';
import { slidesKeys } from '../hooks/useSlides';
import { slideKeys } from '@/features/slide/hooks/useSlideDetail';
import { api } from '@/lib/api-client';

export async function dashboardLoader() {
  const savedUser = localStorage.getItem('user');
  if (!savedUser) return null;

  const user = JSON.parse(savedUser);

  // スライド一覧をプリフェッチ
  const slides = await queryClient.ensureQueryData({
    queryKey: slidesKeys.list(user.email, 20),
    queryFn: () => api.getSlides(user.email, 20),
  });

  // 最新の3件をプリフェッチ（ユーザーがよく見る可能性が高い）
  slides?.slice(0, 3).forEach(slide => {
    queryClient.prefetchQuery({
      queryKey: slideKeys.detail(slide.id),
      queryFn: () => api.getSlideDetail(slide.id),
    });
  });

  return null;
}
```

---

### Step 4.4: テストと体感速度測定（30分）

#### 検証方法

```bash
# Chrome DevTools → Network タブ
# 1. ダッシュボードを開く
# 2. スライドカードにホバー
# 3. ネットワークタブでAPIリクエストを確認
# 4. クリック
# 5. 即座に表示されることを確認
```

#### チェックリスト

- [ ] ホバー時にプリフェッチが発動（NetworkタブでGETリクエスト）
- [ ] クリック後、ローディングなしで即座に表示
- [ ] React Query DevToolsで"prefetched"ステータス確認
- [ ] ホバーせずにクリックした場合も正常動作

---

## Phase 5: 画像最適化

### 目的
- 遅延ロードで初回表示速度向上
- Responsive Imagesで帯域幅削減

### 所要時間
**2-3時間**

---

### Step 5.1: 画像コンポーネントの作成（1.5時間）

```typescript
// frontend/src/shared/components/OptimizedImage.tsx
import { useState, useEffect, useRef } from 'react';

interface OptimizedImageProps {
  src: string;
  alt: string;
  className?: string;
  loading?: 'lazy' | 'eager';
  sizes?: string;
  srcSet?: string;
}

export function OptimizedImage({
  src,
  alt,
  className = '',
  loading = 'lazy',
  sizes,
  srcSet,
}: OptimizedImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (imgRef.current?.complete) {
      setIsLoaded(true);
    }
  }, []);

  return (
    <div className={`relative ${className}`}>
      {/* プレースホルダー */}
      {!isLoaded && (
        <div className="absolute inset-0 bg-gray-200 animate-pulse" />
      )}

      <img
        ref={imgRef}
        src={src}
        srcSet={srcSet}
        sizes={sizes}
        alt={alt}
        loading={loading}
        onLoad={() => setIsLoaded(true)}
        className={`transition-opacity duration-300 ${
          isLoaded ? 'opacity-100' : 'opacity-0'
        }`}
      />
    </div>
  );
}
```

---

### Step 5.2: サムネイル画像への適用（1時間）

```typescript
// frontend/src/features/dashboard/components/SlideCard.tsx
import { OptimizedImage } from '@/shared/components/OptimizedImage';

export function SlideCard({ slide }: { slide: Slide }) {
  return (
    <div className="border rounded-lg overflow-hidden">
      <OptimizedImage
        src={slide.thumbnail_url || '/placeholder-slide.png'}
        alt={slide.title}
        loading="lazy"
        className="w-full h-48 object-cover"
        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
      />
      <div className="p-4">
        <h3>{slide.title}</h3>
      </div>
    </div>
  );
}
```

---

### Step 5.3: テストとパフォーマンス測定（30分）

#### Lighthouse測定

```bash
# 本番ビルド
npm run build
npm run preview

# Chrome DevTools → Lighthouse タブ
# Performance計測実行
```

#### 改善指標

| 指標 | Before | After | 改善率 |
|------|--------|-------|--------|
| LCP (Largest Contentful Paint) | 3.5s | 1.8s | 49% |
| 画像サイズ合計 | 2.5MB | 1.2MB | 52% |
| 初回表示時間 | 2.8s | 1.5s | 46% |

---

## Phase 6: パフォーマンス監視

### 目的
- Web Vitalsの継続的測定
- パフォーマンス劣化の早期検知

### 所要時間
**1-2時間**

---

### Step 6.1: Web Vitals測定の導入（1時間）

```bash
npm install web-vitals
```

```typescript
// frontend/src/lib/reportWebVitals.ts
import { onCLS, onFID, onFCP, onLCP, onTTFB } from 'web-vitals';

export function reportWebVitals() {
  onCLS(console.log);  // Cumulative Layout Shift
  onFID(console.log);  // First Input Delay
  onFCP(console.log);  // First Contentful Paint
  onLCP(console.log);  // Largest Contentful Paint
  onTTFB(console.log); // Time to First Byte
}
```

```typescript
// frontend/src/main.tsx
import { reportWebVitals } from './lib/reportWebVitals';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// 開発環境でWeb Vitalsを測定
if (import.meta.env.DEV) {
  reportWebVitals();
}
```

---

### Step 6.2: パフォーマンス監視ダッシュボード（オプション）

```typescript
// frontend/src/lib/analytics.ts
export function sendAnalytics(metric: any) {
  // 本番環境では分析サービスに送信
  if (import.meta.env.PROD) {
    // Google Analytics 4 の例
    if (window.gtag) {
      window.gtag('event', metric.name, {
        value: Math.round(metric.value),
        metric_id: metric.id,
        metric_delta: Math.round(metric.delta),
      });
    }
  }
}
```

---

## 期待される効果

### 定量的効果

| 指標 | 現状 | 目標 | 改善率 |
|------|------|------|--------|
| **初回ロード時間** | 2.8秒 | 1.2秒 | 57% |
| **バンドルサイズ** | 450KB | 150KB (main) | 67% |
| **API呼び出し回数** | 10回/分 | 3回/分 | 70% |
| **LCP** | 3.5秒 | 1.8秒 | 49% |
| **TTI (Time to Interactive)** | 3.2秒 | 1.5秒 | 53% |
| **サーバー負荷** | 100% | 30% | 70% |

### 定性的効果

- ✅ ページ遷移が体感的に高速（ローディング時間削減）
- ✅ ネットワークエラー時の自動リカバリ（リトライ機能）
- ✅ オフライン時もキャッシュから閲覧可能（短時間）
- ✅ DevToolsでパフォーマンス可視化
- ✅ 継続的なパフォーマンス監視体制

---

## 実装スケジュール

### 推奨スケジュール（3週間）

#### Week 1（基盤整備）
- **Day 1-2**: Phase 1 React Query導入（Step 1.1-1.3）
- **Day 3-4**: Phase 1 React Query導入（Step 1.4-1.6）
- **Day 5**: テスト・デバッグ

#### Week 2（最適化実装）
- **Day 1-2**: Phase 2 Code Splitting導入
- **Day 3**: Phase 3 コンポーネント最適化
- **Day 4**: Phase 4 データプリフェッチ
- **Day 5**: テスト・デバッグ

#### Week 3（仕上げ）
- **Day 1**: Phase 5 画像最適化
- **Day 2**: Phase 6 パフォーマンス監視
- **Day 3-4**: 統合テスト・パフォーマンス測定
- **Day 5**: ドキュメント作成・レビュー

---

## 注意事項

### React Queryの注意点
- キャッシュ時間（`staleTime`）は機能によって調整が必要
- 楽観的更新（Optimistic Updates）は慎重に実装
- DevToolsは本番環境では無効化

### Code Splittingの注意点
- 過度な分割はリクエスト数増加でパフォーマンス低下
- ルートレベルでの分割が基本
- 共通コンポーネントは分割しない

### メモ化の注意点
- `memo()`や`useCallback()`は必要な場合のみ使用
- 全てをメモ化すると逆にパフォーマンス低下
- Profilerで計測してから適用

---

## ロールバックプラン

各Phaseはgitブランチで管理:

```bash
# ブランチ作成
git checkout -b feature/performance-phase1-react-query
git checkout -b feature/performance-phase2-code-splitting

# 問題が発生した場合
git checkout main
```

各Phaseは独立しているため、部分的なロールバックも可能。

---

## 参考資料

- [BulletproofReact - Performance](https://github.com/alan2207/bulletproof-react/blob/master/docs/performance.md)
- [React Query Documentation](https://tanstack.com/query/latest/docs/react/overview)
- [React - Code Splitting](https://react.dev/reference/react/lazy)
- [Web Vitals](https://web.dev/vitals/)

---

**作成者**: Claude Code
**最終更新**: 2025-11-06
