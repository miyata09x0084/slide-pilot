# Feature再設計: テストファースト段階的実装プラン

**作成日**: 2025-11-11
**目的**: Bulletproof React準拠のFeature設計への移行

---

## 🎯 目標

`dashboard`と`generation`をFeatureから削除し、`slides` Featureに統合（Bulletproof React準拠）

### 現状の問題

```
features/
├── dashboard/     ❌ これはPageであってFeatureではない
├── generation/    ⚠️  曖昧（Slideのサブ機能？）
├── slide/         ✅ これは正しいFeature
└── auth/          ✅ これは正しいFeature
```

### Bulletproof Reactの"Feature"の定義

**Featureとは**: ビジネスドメイン概念（データモデル + ビジネスロジック）

- ✅ `users` - ユーザー管理（CRUD）
- ✅ `discussions` - ディスカッション機能
- ✅ `comments` - コメント機能
- ✅ `teams` - チーム管理
- ✅ `auth` - 認証

**Featureではないもの**: Page/Layout/View（複数featureを組み合わせた表示画面）

- ❌ `dashboard` - 複数featureを組み合わせた表示画面 → `app/routes/`で実装
- ❌ `home` - ランディングページ
- ❌ `settings` - 設定画面

---

## 📋 テスト戦略

- ✅ **シンプルなテスト**: コンポーネントレンダリング + インタラクション確認のみ
- ✅ **段階的実装**: 1ステップごとにテスト → 実装 → 検証
- ❌ **避ける**: E2Eテスト、複雑なモック、統合テスト

---

## 📝 実装ステップ（全6ステップ）

### **Step 1: Slides Feature構造準備** ⏱️ 15分

#### 1.1 テスト作成

```bash
# features/slides/__tests__/SlideCard.test.tsx（UnifiedCardを移行）
```

**テスト内容**:
- 基本レンダリング（title, icon表示確認）
- variant切り替え（primary, history, more）
- onClick動作確認

#### 1.2 実装

- `features/slides/` ディレクトリ作成
- `features/dashboard/components/UnifiedCard.tsx` → `features/slides/components/SlideCard.tsx` 移動
- Props名を`SlideCardProps`にリネーム
- テスト実行して動作確認

#### 1.3 検証

```bash
npm test features/slides/__tests__/SlideCard.test.tsx
git commit -m "Step 1: SlideCard component migration with tests"
```

---

### **Step 2: Slides API統合** ⏱️ 20分

#### 2.1 テスト作成

```bash
# features/slides/api/__tests__/get-slides.test.ts
```

**テスト内容**:
- `getSlidesQueryOptions()` が正しいqueryKeyを返す
- `useSlides()` がデータを取得できる（MSW使用）

#### 2.2 実装

**ファイル移動**:
- `features/dashboard/api/get-slides.ts` → `features/slides/api/get-slides.ts`
- `features/dashboard/api/upload-pdf.ts` → `features/slides/api/upload-pdf.ts`
- `features/slide/api/get-slide-detail.ts` → `features/slides/api/get-slide-detail.ts`

**QueryOptionsパターン追加** (Bulletproof React準拠):

```ts
// features/slides/api/get-slides.ts
export const getSlidesQueryOptions = (params: GetSlidesParams) => ({
  queryKey: ['slides', params.user_id, params.limit],
  queryFn: () => getSlides(params),
});

export const useSlides = (params: GetSlidesParams, options?) => {
  return useQuery({
    ...getSlidesQueryOptions(params),
    ...options,
  });
};
```

#### 2.3 検証

```bash
npm test features/slides/api/__tests__/get-slides.test.ts
git commit -m "Step 2: Slides API integration with QueryOptions"
```

---

### **Step 3: Slides Hooks作成** ⏱️ 20分

#### 3.1 テスト作成

```bash
# features/slides/hooks/__tests__/useSlideActions.test.ts
```

**テスト内容**:
- `uploadAndGenerate()` が呼ばれる
- `createSlideFromTopic()` が呼ばれる
- エラー時にエラーメッセージが返る

#### 3.2 実装

```ts
// features/slides/hooks/useSlideActions.ts
export function useSlideActions() {
  const navigate = useNavigate();
  const { createThread, sendMessage } = useThreads(); // Step 4で実装

  const uploadAndGenerate = async (file: File, userId: string) => {
    // ファイルサイズチェック
    if (file.size > 100 * 1024 * 1024) {
      throw new Error('ファイルサイズは100MB以下にしてください');
    }

    // アップロード
    const data = await uploadPdf({ file, user_id: userId });

    // スライド生成開始
    const threadId = await createThread();
    navigate(`/generate/${threadId}`, { state: { pdfPath: data.path } });
    await sendMessage(
      `このPDFから中学生向けのわかりやすいスライドを作成してください: ${data.path}`,
      threadId
    );

    return { threadId, pdfPath: data.path };
  };

  const createSlideFromTopic = async (topic: string) => {
    const threadId = await createThread();
    navigate(`/generate/${threadId}`, { state: { template: topic } });
    await sendMessage(topic, threadId);

    return { threadId, topic };
  };

  return { uploadAndGenerate, createSlideFromTopic };
}
```

#### 3.3 検証

```bash
npm test features/slides/hooks/__tests__/useSlideActions.test.ts
git commit -m "Step 3: Slides hooks with business logic"
```

---

### **Step 4: Threads Feature作成（Generation統合）** ⏱️ 25分

#### 4.1 テスト作成

```bash
# features/threads/__tests__/useThreads.test.ts
```

**テスト内容**:
- `createThread()` がthread_idを返す
- `sendMessage()` がメッセージ送信できる
- SSEストリーミングは実装確認のみ（モックなし）

#### 4.2 実装

**ディレクトリ作成**:
```bash
mkdir -p features/threads/{api,hooks,store,__tests__}
```

**ファイル移動**:
- `features/generation/api/create-thread.ts` → `features/threads/api/create-thread.ts`
- `features/generation/api/get-assistants.ts` → `features/threads/api/get-assistants.ts`
- `features/generation/hooks/useReactAgent.ts` → `features/threads/hooks/useThreads.ts` (リネーム)
- `features/generation/store/reactAgentAtoms.ts` → `features/threads/store/threadAtoms.ts` (リネーム)

**useThreads.ts リファクタリング**:
```ts
// features/threads/hooks/useThreads.ts
// 関数名を useReactAgent → useThreads に変更
// Atom名を reactAgentAtoms → threadAtoms に合わせて更新
export function useThreads() {
  // ... 実装は同じ
}
```

**index.ts作成**:
```ts
// features/threads/index.ts
export { useThreads } from './hooks/useThreads';
export { createThread } from './api/create-thread';
export { findAssistantByGraphId } from './api/get-assistants';
```

#### 4.3 検証

```bash
npm test features/threads/__tests__/useThreads.test.ts
git commit -m "Step 4: Threads feature extraction from generation"
```

---

### **Step 5: Dashboard Page移動** ⏱️ 30分

#### 5.1 テスト作成

```bash
# app/routes/__tests__/dashboard.test.tsx
```

**テスト内容**:
- ページがレンダリングされる
- スライド一覧が表示される
- 新規作成ボタンが動作する

#### 5.2 実装

**ファイル移動**:
- `features/dashboard/DashboardPage.tsx` → `app/routes/app/dashboard.tsx`

**Page固有UIの移動**:
```bash
mkdir -p app/routes/app/dashboard
```
- `features/dashboard/components/QuickActionMenu.tsx` → `app/routes/app/dashboard/QuickActionMenu.tsx`
- `features/dashboard/components/DropzoneCard.tsx` → `app/routes/app/dashboard/DropzoneCard.tsx`

**import更新**:
```tsx
// app/routes/app/dashboard.tsx
import { useAuth } from '@/features/auth';
import { useSlides } from '@/features/slides/api/get-slides';
import { useSlideActions } from '@/features/slides/hooks/useSlideActions';
import { SlideCard } from '@/features/slides/components/SlideCard';
import QuickActionMenu from './dashboard/QuickActionMenu';
```

**ルート定義更新**:
```tsx
// app/routes/index.tsx
export { DashboardRoute } from './app/dashboard';

// app/routes/app/dashboard.tsx
export function DashboardRoute() {
  const { user, logout } = useAuth();
  const { data } = useSlides({ user_id: user?.email || '', limit: 20 });
  const { uploadAndGenerate, createSlideFromTopic } = useSlideActions();

  // ... レンダリングロジック（既存のDashboardPage.tsxから移行）
}
```

#### 5.3 検証

```bash
npm test app/routes/__tests__/dashboard.test.tsx
npm run dev  # 手動で動作確認
git commit -m "Step 5: Dashboard page migration to app/routes"
```

---

### **Step 6: Generation Page移動とクリーンアップ** ⏱️ 20分

#### 6.1 テスト作成

```bash
# app/routes/__tests__/generate.test.tsx
```

**テスト内容**:
- ページがレンダリングされる
- 進行状況が表示される

#### 6.2 実装

**ファイル移動**:
- `features/generation/GenerationProgressPage.tsx` → `app/routes/app/generate.tsx`

**Page固有コンポーネント移動**:
```bash
mkdir -p app/routes/app/generate/components
```
- `features/generation/components/ThinkingIndicator.tsx` → `app/routes/app/generate/components/`
- `features/generation/components/SlideHistory.tsx` → `app/routes/app/generate/components/`
- 他のcomponentsも同様に移動

**import更新**:
```tsx
// app/routes/app/generate.tsx
import { useThreads } from '@/features/threads/hooks/useThreads';
import ThinkingIndicator from './generate/components/ThinkingIndicator';

export function GenerateRoute() {
  const { thinkingSteps, isThinking, slideData, error } = useThreads();

  // ... レンダリングロジック（既存のGenerationProgressPage.tsxから移行）
}
```

**ルート定義更新**:
```tsx
// app/routes/app/generate.tsx
export { GenerateRoute } from './app/generate';
```

**index.ts整理**:
```ts
// features/slides/index.ts（必要最小限のexport）
export { useSlides } from './api/get-slides';
export { useSlideDetail } from './api/get-slide-detail';
export { SlideCard } from './components/SlideCard';
export { SlideViewer } from './components/SlideViewer';
export { SlideContentViewer } from './components/SlideContentViewer';

// features/threads/index.ts
export { useThreads } from './hooks/useThreads';
export { createThread } from './api/create-thread';
```

#### 6.3 削除

```bash
rm -rf features/dashboard/
rm -rf features/generation/
```

#### 6.4 検証

```bash
npm test  # 全テスト実行
npm run build  # ビルド成功確認
npm run lint  # ESLint検証
npm run dev  # 動作確認
git commit -m "Step 6: Generation page migration and cleanup"
```

---

## 📁 最終的なディレクトリ構造

```
frontend/src/
├── app/
│   ├── routes/
│   │   ├── index.tsx                    # DashboardRoute export
│   │   ├── login.tsx
│   │   └── app/
│   │       ├── root.tsx                 # ProtectedLayout
│   │       ├── dashboard.tsx            ← 移動（339行→150行想定）
│   │       ├── dashboard/               ← Page固有UI
│   │       │   ├── QuickActionMenu.tsx
│   │       │   └── DropzoneCard.tsx
│   │       ├── generate.tsx             ← 移動
│   │       ├── generate/                ← Page固有コンポーネント
│   │       │   └── components/
│   │       │       ├── ThinkingIndicator.tsx
│   │       │       └── SlideHistory.tsx
│   │       └── slides.tsx
│   ├── provider.tsx
│   └── router.tsx
│
├── features/
│   ├── slides/                          🆕 統合Feature（ドメイン）
│   │   ├── api/
│   │   │   ├── get-slides.ts            ← dashboard/api/から移動
│   │   │   ├── get-slide-detail.ts      ← slide/api/から移動
│   │   │   └── upload-pdf.ts            ← dashboard/api/から移動
│   │   ├── components/
│   │   │   ├── SlideCard.tsx            ← UnifiedCard.tsxリネーム
│   │   │   ├── SlideViewer.tsx          ← slide/から移動
│   │   │   ├── SlideContentViewer.tsx   ← slide/から移動
│   │   │   ├── ChatPanel.tsx            ← slide/から移動
│   │   │   └── SlideDetailLayout.tsx    ← slide/から移動
│   │   ├── hooks/
│   │   │   ├── useSlides.ts
│   │   │   ├── useSlideDetail.ts
│   │   │   └── useSlideActions.ts       🆕 作成
│   │   ├── types/
│   │   │   └── index.ts                 🆕 作成（Feature固有型）
│   │   ├── loaders/
│   │   │   ├── dashboardLoader.ts       ← 維持（QueryOptions利用）
│   │   │   └── slideDetailLoader.ts     ← 維持（QueryOptions利用）
│   │   ├── __tests__/
│   │   │   ├── SlideCard.test.tsx
│   │   │   ├── ChatPanel.test.tsx
│   │   │   └── ...
│   │   └── index.ts                     # Public API（最小限）
│   │
│   ├── threads/                         🆕 LangGraphスレッド管理Feature
│   │   ├── api/
│   │   │   ├── create-thread.ts         ← generation/api/から移動
│   │   │   └── get-assistants.ts        ← generation/api/から移動
│   │   ├── hooks/
│   │   │   └── useThreads.ts            ← useReactAgent.tsリネーム
│   │   ├── store/
│   │   │   └── threadAtoms.ts           ← reactAgentAtoms.tsリネーム
│   │   ├── __tests__/
│   │   │   └── useThreads.test.ts
│   │   └── index.ts
│   │
│   └── auth/                            ✅ 維持
│       ├── components/
│       ├── hooks/
│       └── index.ts
│
├── components/
│   └── error/
│       ├── ErrorBoundary.tsx
│       └── Spinner.tsx
│
├── lib/
│   ├── api-client.ts
│   └── react-query.ts
│
├── config/
│   └── env.ts
│
├── types/
│   └── index.ts                         # 共通型定義
│
└── main.tsx
```

---

## 📊 変更サマリー

### 移動・統合

| Before | After | 理由 |
|--------|-------|------|
| `features/dashboard/` | `app/routes/app/dashboard.tsx` | PageであってFeatureではない |
| `features/generation/` | `app/routes/app/generate.tsx` | PageであってFeatureではない |
| `features/slide/` | `features/slides/` | ドメインFeatureとして維持（リネーム） |
| `features/generation/hooks/useReactAgent.ts` | `features/threads/hooks/useThreads.ts` | LangGraph管理を独立Feature化 |
| `features/dashboard/components/UnifiedCard.tsx` | `features/slides/components/SlideCard.tsx` | スライドドメインの一部 |

### 新規作成

| ファイル | 目的 |
|---------|------|
| `features/slides/hooks/useSlideActions.ts` | スライド作成ビジネスロジック |
| `features/slides/types/index.ts` | Feature固有型定義 |
| `features/threads/` | LangGraphスレッド管理Feature |
| `app/routes/app/dashboard/` | Dashboard Page固有UI |
| `app/routes/app/generate/components/` | Generate Page固有コンポーネント |

### 削除

- `features/dashboard/` 全体
- `features/generation/` 全体

---

## 判断基準: Feature vs Page

| 観点 | Feature | Page/Route |
|------|---------|-----------|
| **目的** | ドメインロジックの実装 | Featureの組み合わせ表示 |
| **例** | `slides`, `users`, `comments`, `threads` | `dashboard`, `home`, `profile` |
| **持つもの** | api, hooks, types, components | Layout, composition, Page固有UI |
| **再利用性** | 複数のPageから使われる | 1つのURL専用 |
| **依存方向** | 他Featureに依存しない | 複数Featureに依存OK |
| **テスト** | ユニットテスト中心 | 統合テスト・手動テスト |

---

## ✅ 成功基準

| 基準 | 確認方法 | 期待値 |
|------|---------|--------|
| 全テスト成功 | `npm test` | All tests passing |
| ビルド成功 | `npm run build` | No errors |
| ESLint違反なし | `npm run lint` | No errors |
| Feature間直接import 0件 | ESLint boundaries検証 | No violations |
| Dashboard動作確認 | 手動テスト | スライド一覧表示、新規作成 |
| Generation動作確認 | 手動テスト | スライド生成進行表示 |
| Slide Detail動作確認 | 手動テスト | 詳細表示、チャット動作 |

---

## ⏱️ 所要時間見積もり

| Step | 作業内容 | 所要時間 |
|------|---------|---------|
| Step 1 | Slides Feature構造準備 | 15分 |
| Step 2 | Slides API統合 | 20分 |
| Step 3 | Slides Hooks作成 | 20分 |
| Step 4 | Threads Feature作成 | 25分 |
| Step 5 | Dashboard Page移動 | 30分 |
| Step 6 | Generation Page移動とクリーンアップ | 20分 |
| **合計** | | **約2時間** |

---

## 🔄 ロールバック戦略

各Stepでgit commit作成:

```bash
git commit -m "Step 1: SlideCard component migration with tests"
git commit -m "Step 2: Slides API integration with QueryOptions"
git commit -m "Step 3: Slides hooks with business logic"
git commit -m "Step 4: Threads feature extraction from generation"
git commit -m "Step 5: Dashboard page migration to app/routes"
git commit -m "Step 6: Generation page migration and cleanup"
```

問題発生時は `git revert <commit-hash>` で前Stepに戻す

---

## 📚 参考資料

- [Bulletproof React - Project Structure](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md)
- [Bulletproof React - react-vite app](https://github.com/alan2207/bulletproof-react/tree/master/apps/react-vite)
- [React Query - Query Options](https://tanstack.com/query/latest/docs/react/guides/query-options)
- [前回の移行プラン](./BULLETPROOF_REACT_MIGRATION_PLAN.md)

---

## 🎯 期待される効果

### アーキテクチャ

- ✅ Bulletproof React準拠のFeature設計
- ✅ ドメイン境界の明確化
- ✅ Feature間依存の解消
- ✅ Page層とFeature層の責任分離

### コード品質

- ✅ DashboardPage.tsx の行数削減（339行 → 150行想定）
- ✅ ビジネスロジックのHooks化
- ✅ テストカバレッジの向上
- ✅ 再利用性の向上

### 開発体験

- ✅ Feature追加時の影響範囲が明確
- ✅ ESLintによるアーキテクチャ違反検出
- ✅ コードレビューしやすい構造
- ✅ 新規参画者の理解しやすさ向上
