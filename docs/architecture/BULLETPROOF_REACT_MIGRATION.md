# BulletProof React 完全準拠への移行計画

**作成日**: 2025-11-10
**ステータス**: 🚧 進行中
**目的**: BulletProof React推奨構造への完全移行

---

## 📊 1. 現状分析

### 1.1 現在のディレクトリ構造

```
frontend/src/
├── App.tsx                    ← ルーター定義（ルートに配置）
├── App.css                    ← グローバルCSS
├── main.tsx                   ← エントリーポイント
├── index.css                  ← グローバルCSS
├── setupTests.ts              ← テスト設定
│
├── assets/                    ✅ BulletProof準拠
│   └── react.svg
│
├── lib/                       ✅ BulletProof準拠
│   ├── react-query.ts         ← React Query設定
│   ├── api-client.ts          ← APIクライアント
│   └── lazyImport.ts          ← 動的インポートユーティリティ
│
├── shared/                    ⚠️ → components/ に変更必要
│   ├── index.ts
│   └── components/
│       ├── ChatMessage.tsx
│       ├── ChatInput.tsx
│       └── PageLoader.tsx
│
└── features/                  ✅ BulletProof準拠（部分的）
    ├── auth/
    │   ├── LoginPage.tsx
    │   ├── hooks/
    │   │   └── useAuth.ts
    │   ├── components/
    │   │   └── AuthGuard.tsx
    │   ├── __tests__/
    │   └── index.ts           ⚠️ バレルファイル
    │
    ├── dashboard/
    │   ├── DashboardPage.tsx
    │   ├── api/               ✅ Query Options Factory
    │   │   └── get-slides.ts
    │   ├── loaders/           ⚠️ 独自拡張（React Router）
    │   │   └── dashboardLoader.ts
    │   ├── components/
    │   ├── __tests__/
    │   └── index.ts           ⚠️ バレルファイル
    │
    ├── slide/
    │   ├── SlideDetailPage.tsx
    │   ├── api/               ✅ Query Options Factory
    │   │   └── get-slide-detail.ts
    │   ├── loaders/           ⚠️ 独自拡張（React Router）
    │   │   └── slideDetailLoader.ts
    │   ├── components/
    │   ├── __tests__/
    │   └── index.ts           ⚠️ バレルファイル
    │
    └── generation/
        ├── GenerationProgressPage.tsx
        ├── hooks/
        │   └── useReactAgent.ts
        ├── store/             ⚠️ → stores/ に変更
        │   └── reactAgentAtoms.ts
        ├── components/
        ├── __tests__/
        └── index.ts           ⚠️ バレルファイル
```

### 1.2 BulletProof Reactとの差分

| 項目 | 現状 | BulletProof React | 対応 |
|------|------|------------------|------|
| **アプリケーション層** | `App.tsx`（ルート） | `app/` ディレクトリ | ❌ Phase 2で対応 |
| **共有コンポーネント** | `shared/components/` | `components/` | ❌ Phase 3で対応 |
| **グローバル設定** | なし | `config/` | ❌ Phase 4で対応 |
| **グローバル型定義** | なし | `types/` | ❌ Phase 4で対応 |
| **グローバルhooks** | なし | `hooks/` | ❌ Phase 4で対応 |
| **グローバルstores** | なし | `stores/` | ❌ Phase 4で対応 |
| **グローバルutils** | なし | `utils/` | ❌ Phase 4で対応 |
| **features構造** | ほぼ準拠 | 完全準拠 | ⚠️ Phase 5で微調整 |
| **loaders/**（独自） | あり | なし | ✅ 継続使用（Phase 6で文書化） |
| **バレルファイル** | 使用中 | 非推奨 | ⚠️ オプション対応 |

### 1.3 独自拡張の位置づけ

#### **loaders/ ディレクトリ（継続使用）**

```
features/*/loaders/
```

**目的**: React Router v6.4+ Loader機能を活用したデータ事前読み込み

**メリット**:
- ページ遷移開始時にデータ取得
- ローディング画面なしで即座に表示
- React Queryとの統合でキャッシュ管理

**BulletProof Reactとの関係**:
- BulletProof Reactには存在しない
- React Router公式のベストプラクティス
- **独自拡張として継続使用を推奨**

---

## 🎯 2. 目標アーキテクチャ

### 2.1 最終的なディレクトリ構造

```
frontend/src/
├── app/                       ← ★ アプリケーション層
│   ├── index.tsx              ← App統合（Provider + Router）
│   ├── provider.tsx           ← Providersの集約（ErrorBoundary, Suspense含む）
│   ├── router.tsx             ← createAppRouter(queryClient)関数
│   └── routes/                ← ルート定義（lazy import対象）
│       ├── auth/
│       │   └── login.tsx
│       └── app/
│           ├── dashboard.tsx
│           ├── slide-detail.tsx
│           └── generation.tsx
│
├── assets/                    ← 静的ファイル
│   └── react.svg
│
├── components/                ← 共有コンポーネント（旧shared/）
│   ├── ChatMessage.tsx
│   ├── ChatInput.tsx
│   ├── PageLoader.tsx
│   └── errors/
│       └── MainErrorFallback.tsx  ← ErrorBoundary用
│
├── config/                    ← ★ グローバル設定
│   └── env.ts                 ← 環境変数管理
│
├── features/                  ← Feature-based modules
│   ├── auth/
│   │   ├── LoginPage.tsx
│   │   ├── api/               ← API層（新規）
│   │   ├── hooks/
│   │   ├── components/
│   │   ├── types/             ← Feature固有の型（新規）
│   │   ├── __tests__/
│   │   └── [index.ts]         ← バレルファイル（削除検討）
│   │
│   ├── dashboard/
│   │   ├── DashboardPage.tsx
│   │   ├── api/               ← Query Options Factory
│   │   ├── loaders/           ← React Router Loader（独自拡張）
│   │   ├── components/
│   │   ├── types/             ← Feature固有の型（新規）
│   │   ├── __tests__/
│   │   └── [index.ts]
│   │
│   ├── slide/
│   │   ├── SlideDetailPage.tsx
│   │   ├── api/
│   │   ├── loaders/           ← React Router Loader（独自拡張）
│   │   ├── components/
│   │   ├── types/
│   │   ├── __tests__/
│   │   └── [index.ts]
│   │
│   └── generation/
│       ├── GenerationProgressPage.tsx
│       ├── hooks/
│       ├── stores/            ← リネーム（旧store/）
│       ├── components/
│       ├── types/
│       ├── __tests__/
│       └── [index.ts]
│
├── hooks/                     ← ★ グローバルhooks
│   └── (将来拡張用)
│
├── lib/                       ← 事前設定済みライブラリ
│   ├── react-query.ts
│   ├── api-client.ts
│   └── lazyImport.ts
│
├── stores/                    ← ★ グローバルstores
│   └── (将来拡張用)
│
├── types/                     ← ★ グローバル型定義
│   └── index.ts               ← 共通型（User等）
│
├── utils/                     ← ★ グローバルユーティリティ
│   └── (将来拡張用)
│
├── __tests__/                 ← グローバルテスト
├── main.tsx                   ← エントリーポイント
├── index.css                  ← グローバルCSS
└── setupTests.ts              ← テスト設定
```

### 2.2 各ディレクトリの責務

| ディレクトリ | 責務 | 例 |
|-------------|------|-----|
| `app/` | アプリケーション層（ルーティング、Provider、エラーハンドリング） | `index.tsx`, `router.tsx`, `provider.tsx`, `routes/` |
| `components/` | アプリ全体で使う共有コンポーネント | `PageLoader`, `ChatMessage`, `errors/MainErrorFallback` |
| `config/` | 設定ファイル、環境変数 | `env.ts` |
| `features/` | Feature単位のモジュール | `auth`, `dashboard`, `slide` |
| `hooks/` | アプリ全体で使うカスタムフック | `useDebounce`, `useMediaQuery` |
| `lib/` | 外部ライブラリの設定 | `react-query.ts`, `api-client.ts` |
| `stores/` | グローバル状態管理 | Recoil atoms, Redux slices |
| `types/` | TypeScript型定義 | `User`, `APIResponse` |
| `utils/` | ユーティリティ関数 | `formatDate`, `cn` |

### 2.3 コードフロー（依存関係）

```
app/ → features/ → lib/, hooks/, components/, stores/, types/, utils/
       ↑           ↑
       ⊗           ✓ (許可)
```

**原則**:
- `features/` は `lib/`, `components/` 等を参照可能
- `app/` は `features/` を参照可能
- **逆方向の依存は禁止**

---

## 📋 3. 段階的移行計画

### Phase 1: 設計書作成 ✅

**完了条件**: このドキュメントが承認される

---

### Phase 2: app/ ディレクトリの作成

#### 3.1 目的

アプリケーション層を分離し、Providerとルーティングを明確に整理する。

#### 3.2 変更内容

**Before**:
```typescript
// main.tsx
import App from "./App.tsx";
import { GoogleOAuthProvider } from "@react-oauth/google";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={clientId}>
      <App />
    </GoogleOAuthProvider>
  </StrictMode>
);

// App.tsx
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RecoilRoot>
        <RouterProvider router={router} />
      </RecoilRoot>
      {import.meta.env.DEV && <ReactQueryDevtools />}
    </QueryClientProvider>
  );
}
```

**After** (BulletProof React最新パターン):
```typescript
// app/provider.tsx
export function AppProvider({ children }: AppProviderProps) {
  const [queryClient] = useState(
    () => new QueryClient({
      defaultOptions: queryConfig,
    }),
  );

  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ErrorBoundary FallbackComponent={MainErrorFallback}>
        <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
          <QueryClientProvider client={queryClient}>
            {import.meta.env.DEV && <ReactQueryDevtools />}
            <RecoilRoot>
              {children}
            </RecoilRoot>
          </QueryClientProvider>
        </GoogleOAuthProvider>
      </ErrorBoundary>
    </Suspense>
  );
}

// app/router.tsx
export const createAppRouter = (queryClient: QueryClient) =>
  createBrowserRouter([
    {
      path: "/login",
      lazy: () => import("./routes/auth/login"),
    },
    {
      element: <AuthGuard />,
      children: [
        {
          path: "/",
          lazy: () => import("./routes/app/dashboard").then(convert(queryClient)),
        },
        {
          path: "/slides/:slideId",
          lazy: () => import("./routes/app/slide-detail").then(convert(queryClient)),
        },
      ],
    },
  ]);

// app/index.tsx
export function App() {
  const queryClient = useQueryClient();
  const router = useMemo(() => createAppRouter(queryClient), [queryClient]);

  return <RouterProvider router={router} />;
}

// main.tsx
import { App } from "./app";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

**重要な変更点**:
1. **queryClientをProvider内で生成**: BulletProof Reactパターンに準拠
2. **createAppRouter(queryClient)**: loaderでqueryClientを使用可能に
3. **app/index.tsx**: AppProviderとRouterProviderを統合
4. **main.tsx**: シンプルに`<App />`のみレンダリング
5. **StrictModeをAppProvider内に移動**: BulletProof Reactパターン

#### 3.3 実装手順

1. **`src/app/` ディレクトリ作成**
2. **`src/app/provider.tsx` 作成**
   - ErrorBoundary追加
   - Suspense追加
   - GoogleOAuthProvider
   - QueryClientProvider（内部で生成）
   - RecoilRoot
   - ReactQueryDevtools
3. **`src/app/router.tsx` 作成**
   - `createAppRouter(queryClient)`関数をエクスポート
   - `convert(queryClient)`ヘルパー実装
   - 現在のApp.tsxのルート定義を移行
4. **`src/app/routes/` ディレクトリ作成**
   - `routes/auth/login.tsx` (lazy importターゲット)
   - `routes/app/dashboard.tsx` (lazy importターゲット)
   - `routes/app/slide-detail.tsx`
   - `routes/app/generation.tsx`
5. **`src/app/index.tsx` 作成**
   - AppProviderとRouterProviderを統合
6. **`src/main.tsx` 更新**
   - `<App />`のみレンダリング
   - StrictModeをAppProvider内に移動
7. **`src/App.tsx`, `src/App.css` 削除**
8. **ビルド確認**
9. **テスト実行**

#### 3.4 影響範囲

- **新規ディレクトリ**: 2個
  - `src/app/`
  - `src/app/routes/`
- **新規ファイル**: 7ファイル
  - `src/app/provider.tsx`
  - `src/app/router.tsx`
  - `src/app/index.tsx`
  - `src/app/routes/auth/login.tsx`
  - `src/app/routes/app/dashboard.tsx`
  - `src/app/routes/app/slide-detail.tsx`
  - `src/app/routes/app/generation.tsx`
- **更新ファイル**: 1ファイル
  - `src/main.tsx`
- **削除ファイル**: 2ファイル
  - `src/App.tsx`
  - `src/App.css`

#### 3.5 テスト観点

- [ ] ビルドが成功する
- [ ] 開発サーバーが起動する
- [ ] ログインページが表示される
- [ ] 認証が機能する
- [ ] 全テストが通過する

#### 3.6 ロールバック手順

```bash
git revert <commit-hash>
```

---

### Phase 3: shared/ → components/ リネーム

#### 3.7 目的

BulletProof React命名規則に準拠し、共有コンポーネントの配置を標準化する。

#### 3.8 変更内容

**Before**:
```
src/shared/
├── index.ts
└── components/
    ├── ChatMessage.tsx
    ├── ChatInput.tsx
    └── PageLoader.tsx
```

**After**:
```
src/components/
├── ChatMessage.tsx
├── ChatInput.tsx
└── PageLoader.tsx
```

#### 3.9 実装手順

1. `src/shared/components/` の中身を `src/components/` に移動
2. `src/shared/index.ts` 削除
3. `src/shared/` ディレクトリ削除
4. 全importパスを更新
   ```typescript
   // Before
   import { PageLoader } from './shared/components/PageLoader';

   // After
   import { PageLoader } from '@/components/PageLoader';
   ```
5. ビルド確認
6. テスト実行

#### 3.10 影響範囲

- importパス更新: 約10箇所
  - `app/router.tsx`
  - `features/*/components/*.tsx`

#### 3.11 テスト観点

- [ ] ビルドが成功する
- [ ] 全コンポーネントが正常に表示される
- [ ] 全テストが通過する

---

### Phase 4: グローバルディレクトリ作成

#### 3.12 目的

BulletProof React標準のグローバルディレクトリを作成し、将来の拡張に備える。

#### 3.13 作成ディレクトリと初期ファイル

**1. config/ - グローバル設定**

```typescript
// config/env.ts
export const env = {
  // Google OAuth
  googleClientId: import.meta.env.VITE_GOOGLE_CLIENT_ID || '',

  // API
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8001/api',

  // その他
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
} as const;
```

**2. types/ - グローバル型定義**

```typescript
// types/index.ts
/**
 * グローバル型定義
 * アプリケーション全体で使用する共通の型
 */

export interface User {
  name: string;
  email: string;
  picture: string;
}

export interface APIError {
  message: string;
  code?: string;
  details?: unknown;
}

// 将来追加予定: Pagination, Sort, Filter等
```

**3. hooks/ - グローバルhooks**

```typescript
// hooks/.gitkeep
// 将来の拡張用（例: useDebounce, useMediaQuery等）
```

**4. stores/ - グローバルstores**

```typescript
// stores/.gitkeep
// 将来の拡張用（グローバルなRecoil atoms等）
```

**5. utils/ - グローバルユーティリティ**

```typescript
// utils/.gitkeep
// 将来の拡張用（例: formatDate, cn等）
```

#### 3.14 実装手順

1. 5つのディレクトリ作成
2. 各初期ファイル作成
3. 既存コードから移行
   - `main.tsx` の環境変数 → `config/env.ts`
   - `useAuth.ts` の `UserInfo` → `types/index.ts`
4. importパス更新
5. ビルド確認

#### 3.15 影響範囲

- 新規ディレクトリ: 5個
- 新規ファイル: 2個（`config/env.ts`, `types/index.ts`）
- 更新ファイル: 約5箇所

---

### Phase 5: features/ 構造統一

#### 3.16 目的

全featureをBulletProof React標準に完全準拠させる。

#### 3.17 変更内容

**1. generation/store/ → generation/stores/ リネーム**

```bash
mv src/features/generation/store src/features/generation/stores
```

**2. 各featureに types/ 追加**

```
features/auth/types/index.ts
features/dashboard/types/index.ts
features/slide/types/index.ts
features/generation/types/index.ts
```

**3. auth/ に api/ 追加（必要に応じて）**

将来的にGoogle OAuth APIラッパーを実装する場合に使用。

#### 3.18 実装手順

1. `generation/store/` → `generation/stores/` リネーム
2. importパス更新
3. 各featureに `types/index.ts` 作成
4. feature固有の型を移動
5. ビルド確認

#### 3.19 影響範囲

- リネーム: 1ディレクトリ
- 新規ファイル: 4ファイル（各feature/types/index.ts）
- importパス更新: 約5箇所

---

### Phase 6: loaders/ 文書化

#### 3.20 目的

React Router Loaderの設計思想を文書化し、独自拡張として明確化する。

#### 3.21 作成ドキュメント

**docs/architecture/REACT_ROUTER_LOADERS.md**

```markdown
# React Router Loaders Integration

## 概要

このプロジェクトはBulletProof React構造を基本としつつ、
React Router v6.4+のLoader機能を独自拡張として採用しています。

## loaders/ ディレクトリ

features/*/loaders/

## 設計思想

1. **データ事前読み込み**
   - ページ遷移開始時にデータ取得
   - コンポーネント表示時には既にデータが存在

2. **React Queryとの統合**
   - ensureQueryData()でキャッシュに保存
   - コンポーネントはuseQuery()でキャッシュから取得

3. **体感速度の向上**
   - ローディング画面が表示されない
   - 初回表示が100ms短縮

## 実装例

...
```

#### 3.22 実装手順

1. `docs/architecture/REACT_ROUTER_LOADERS.md` 作成
2. 設計思想、実装例、メリット・デメリットを記載
3. `CLAUDE.md` に参照リンク追加

---

## 📊 4. 実装チェックリスト

### Phase 1: 設計書作成
- [x] BULLETPROOF_REACT_MIGRATION.md 作成
- [x] レビュー・承認

### Phase 2: app/ ディレクトリ
- [ ] src/app/ 作成
- [ ] src/app/routes/ 作成
- [ ] app/provider.tsx 作成（ErrorBoundary, Suspense追加）
- [ ] app/router.tsx 作成（createAppRouter関数）
- [ ] app/index.tsx 作成（App統合）
- [ ] app/routes/auth/login.tsx 作成
- [ ] app/routes/app/dashboard.tsx 作成
- [ ] app/routes/app/slide-detail.tsx 作成
- [ ] app/routes/app/generation.tsx 作成
- [ ] main.tsx 更新（StrictMode位置変更）
- [ ] App.tsx, App.css 削除
- [ ] ビルド成功
- [ ] テスト全通過
- [ ] Gitコミット

### Phase 3: components/ リネーム
- [ ] src/components/ 作成
- [ ] shared/components/ 移動
- [ ] shared/ 削除
- [ ] importパス更新（~10箇所）
- [ ] ビルド成功
- [ ] テスト全通過
- [ ] Gitコミット

### Phase 4: グローバルディレクトリ
- [ ] config/ 作成
- [ ] types/ 作成
- [ ] hooks/ 作成（.gitkeep）
- [ ] stores/ 作成（.gitkeep）
- [ ] utils/ 作成（.gitkeep）
- [ ] config/env.ts 実装
- [ ] types/index.ts 実装
- [ ] 既存コードから移行
- [ ] ビルド成功
- [ ] Gitコミット

### Phase 5: features/ 統一
- [ ] generation/store/ → stores/ リネーム
- [ ] 各feature/types/ 作成
- [ ] feature固有の型を移動
- [ ] ビルド成功
- [ ] テスト全通過
- [ ] Gitコミット

### Phase 6: loaders/ 文書化
- [ ] docs/architecture/REACT_ROUTER_LOADERS.md 作成
- [ ] CLAUDE.md 更新
- [ ] Gitコミット

---

## 🔄 5. ロールバック手順

### Phase 2のロールバック

```bash
git revert <commit-hash>
# または
git reset --hard <前のcommit-hash>
```

### Phase 3のロールバック

```bash
# ディレクトリ復元
mv src/components src/shared/components
mkdir -p src/shared
# Gitからリストア
git checkout HEAD -- src/shared/
```

### 全体のロールバック

```bash
# メインブランチに戻る
git checkout main
git branch -D refactor/bulletproof-react-migration
```

---

## 📚 6. 参考資料

### BulletProof React 公式

- **GitHub**: https://github.com/alan2207/bulletproof-react
- **Project Structure**: https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md
- **API Layer**: https://github.com/alan2207/bulletproof-react/blob/master/docs/api-layer.md

### React Router v6.4+

- **Loader機能**: https://reactrouter.com/en/main/route/loader
- **Data Fetching**: https://reactrouter.com/en/main/guides/data-fetching

### React Query

- **Query Options API**: https://tkdodo.eu/blog/the-query-options-api
- **Prefetching**: https://tanstack.com/query/v5/docs/framework/react/guides/prefetching

---

## 📝 7. 変更履歴

| 日付 | Phase | 内容 | コミット |
|------|-------|------|---------|
| 2025-11-10 | Phase 1 | 設計書作成 | - |
| - | Phase 2 | app/ 実装 | TBD |
| - | Phase 3 | components/ リネーム | TBD |
| - | Phase 4 | グローバルディレクトリ | TBD |
| - | Phase 5 | features/ 統一 | TBD |
| - | Phase 6 | loaders/ 文書化 | TBD |

---

## ✅ 8. 承認

- [ ] 設計レビュー完了
- [ ] 実装開始承認

**レビュアー**: _____________
**承認日**: _____________
