# フロントエンドリファクタリング実装方針

**作成日**: 2025-11-06
**目的**: Feature-first アーキテクチャへの移行によるコードの保守性・スケーラビリティ向上

---

## 目次

1. [現状分析](#現状分析)
2. [問題点](#問題点)
3. [目標アーキテクチャ](#目標アーキテクチャ)
4. [移行戦略](#移行戦略)
5. [段階的実装ステップ](#段階的実装ステップ)
6. [ファイル移動マッピング](#ファイル移動マッピング)
7. [自動化スクリプト](#自動化スクリプト)
8. [テスト戦略](#テスト戦略)
9. [ロールバックプラン](#ロールバックプラン)

---

## 現状分析

### 現在のディレクトリ構成

```
frontend/src/
├── App.tsx                      # ルーティング設定
├── main.tsx                     # エントリーポイント
├── App.tsx.backup               # ⚠️ 不要なバックアップファイル
│
├── __tests__/                   # テストファイル（2ファイル）
├── assets/                      # 静的リソース
│
├── components/                  # コンポーネント（17ファイル）
│   ├── slide/                  # スライド関連（4ファイル）
│   │   ├── ChatPanel.tsx
│   │   ├── SlideContentViewer.tsx
│   │   ├── SlideDetailLayout.tsx
│   │   └── SuggestedQuestions.tsx
│   │
│   ├── dashboard/              # ⚠️ 空ディレクトリ（未使用）
│   │
│   └── [ルートに散在]           # 分類されていない（13ファイル）
│       ├── ChatInput.tsx
│       ├── ChatMessage.tsx
│       ├── DropzoneCard.tsx
│       ├── InitialInputForm.tsx
│       ├── Login.tsx
│       ├── ProtectedRoute.tsx
│       ├── QuickActionMenu.tsx
│       ├── SectionHeader.tsx
│       ├── SlideHistory.test.tsx
│       ├── SlideHistory.tsx
│       ├── SlideViewer.tsx
│       ├── ThinkingIndicator.tsx
│       └── UnifiedCard.tsx
│
├── hooks/                      # カスタムフック（2ファイル）
│   ├── useAuth.ts
│   └── useReactAgent.ts
│
├── loaders/                    # React Router loader（1ファイル）
│   └── dashboardLoader.ts
│
├── pages/                      # ページコンポーネント（4ファイル）
│   ├── DashboardPage.tsx
│   ├── GenerationProgressPage.tsx
│   ├── LoginPage.tsx
│   └── SlideDetailPage.tsx
│
└── store/                      # Recoil状態管理（1ファイル）
    └── reactAgentAtoms.ts
```

### ファイル統計

| ディレクトリ | ファイル数 | 備考                     |
| ------------ | ---------- | ------------------------ |
| components/  | 17         | うち 13 個がルートに散在 |
| pages/       | 4          | ページコンポーネント     |
| hooks/       | 2          | カスタムフック           |
| loaders/     | 1          | React Router loader      |
| store/       | 1          | Recoil atoms             |
| **合計**     | **25**     | コア実装ファイル         |

---

## 問題点

### 1. **コンポーネントの無秩序な配置**

**問題**:

- `components/` ルートに 13 個のコンポーネントが散在
- 機能別・用途別の分類がない
- 新規コンポーネント追加時の配置ルールが不明確

**影響**:

- コードの発見性が低い（「このコンポーネントどこ？」）
- 関連ファイルが離れた場所に存在
- チーム開発時の混乱

### 2. **機能横断的な依存関係**

**問題**:

- ページコンポーネント（`pages/`）とビジネスロジック（`hooks/`, `loaders/`）が分離
- 1 つの機能を理解するために複数ディレクトリを横断する必要

**例**:

```
DashboardPage機能を理解するには...
├── pages/DashboardPage.tsx          # ページ本体
├── loaders/dashboardLoader.ts       # データ取得
├── components/UnifiedCard.tsx       # UI部品
├── components/QuickActionMenu.tsx   # UI部品
└── hooks/useReactAgent.ts           # ロジック（他機能と共有）
```

### 3. **スケーラビリティの欠如**

**問題**:

- 現在 25 ファイル → 将来 50-100 ファイルになると破綻
- 機能追加時にどこに配置すべきか不明
- リファクタリングの難易度が高い

### 4. **テストファイルの配置**

**問題**:

- `SlideHistory.test.tsx` が `components/` 内に混在
- 他のテストは `__tests__/` ディレクトリ
- 配置ルールの不統一

### 5. **不要ファイルの残存**

**問題**:

- `App.tsx.backup` がソースディレクトリに残存
- `components/dashboard/` が空ディレクトリとして放置

---

## 目標アーキテクチャ

### Feature-first アーキテクチャ

**設計原則**:

1. **機能単位でファイルをグループ化** - 関連するコードを 1 箇所に集約
2. **コロケーション** - ページ・コンポーネント・ロジック・テストを近くに配置
3. **明確な境界** - 機能間の依存を明示的にする
4. **スケーラブル** - 機能追加時の配置先が自明

### 新しいディレクトリ構成

```
frontend/src/
├── App.tsx
├── main.tsx
│
├── features/                          # 機能単位のディレクトリ
│   │
│   ├── dashboard/                     # ダッシュボード機能
│   │   ├── components/               # Dashboard専用コンポーネント
│   │   │   ├── UnifiedCard.tsx
│   │   │   ├── UnifiedCard.test.tsx
│   │   │   ├── QuickActionMenu.tsx
│   │   │   └── DropzoneCard.tsx
│   │   ├── loaders/
│   │   │   └── dashboardLoader.ts
│   │   ├── hooks/
│   │   │   └── useDashboard.ts      # （将来的に抽出）
│   │   ├── DashboardPage.tsx
│   │   └── index.ts                  # Public API（re-export）
│   │
│   ├── slide/                         # スライド表示・詳細機能
│   │   ├── components/
│   │   │   ├── SlideViewer.tsx
│   │   │   ├── SlideContentViewer.tsx
│   │   │   ├── SlideDetailLayout.tsx
│   │   │   ├── ChatPanel.tsx
│   │   │   └── SuggestedQuestions.tsx
│   │   ├── hooks/
│   │   │   └── useSlideDetail.ts    # （将来的に抽出）
│   │   ├── SlideDetailPage.tsx
│   │   └── index.ts
│   │
│   ├── generation/                    # スライド生成機能
│   │   ├── components/
│   │   │   ├── InitialInputForm.tsx
│   │   │   ├── SlideHistory.tsx
│   │   │   ├── SlideHistory.test.tsx
│   │   │   ├── SectionHeader.tsx
│   │   │   └── ThinkingIndicator.tsx
│   │   ├── hooks/
│   │   │   └── useReactAgent.ts     # useReactAgent移動
│   │   ├── store/
│   │   │   └── reactAgentAtoms.ts   # Recoil atoms移動
│   │   ├── GenerationProgressPage.tsx
│   │   └── index.ts
│   │
│   └── auth/                          # 認証機能
│       ├── components/
│       │   ├── Login.tsx
│       │   └── ProtectedRoute.tsx
│       ├── hooks/
│       │   └── useAuth.ts           # useAuth移動
│       ├── LoginPage.tsx
│       └── index.ts
│
├── shared/                            # 共通コンポーネント
│   ├── components/
│   │   ├── ChatInput.tsx            # 複数機能で使用
│   │   ├── ChatMessage.tsx
│   │   └── ui/                      # 汎用UIコンポーネント
│   │       └── Button.tsx           # （将来追加）
│   └── hooks/
│       └── useDebounce.ts           # （将来追加）
│
├── lib/                               # ユーティリティ・ヘルパー
│   ├── api.ts                        # API client
│   ├── constants.ts                  # 定数定義
│   └── utils.ts                      # 汎用関数
│
├── types/                             # 型定義
│   ├── slide.ts
│   ├── user.ts
│   └── index.ts
│
└── __tests__/                         # 統合テスト・E2Eテスト
    ├── integration/
    └── e2e/
```

---

## 移行戦略

### 基本方針

1. **段階的移行** - 一度に全てを変更せず、機能単位で段階的に実施
2. **ゼロダウンタイム** - 各フェーズで動作する状態を維持
3. **自動化優先** - スクリプトによる一括移動・import 修正
4. **テスト駆動** - 各フェーズ後にテスト実行

### 移行の優先順位

**Phase 1: 準備（影響小）** ⭐️ 最優先

- ディレクトリ名の修正
- 不要ファイルの削除
- 型定義の抽出

**Phase 2: 独立機能（依存少）**

- `auth/` 機能の移行
- `dashboard/` 機能の移行

**Phase 3: 依存機能（依存多）**

- `slide/` 機能の移行
- `generation/` 機能の移行

**Phase 4: 共通化（全体最適）**

- 共通コンポーネントの抽出
- ユーティリティの整理

---

## 段階的実装ステップ

### Phase 1: 準備・クリーンアップ（1-2 時間）

#### 目的

- 既存の問題を修正
- 移行の基盤を整備

#### 作業内容

**1.1 不要ファイル削除**

```bash
# バックアップファイル削除
rm frontend/src/App.tsx.backup

# 空ディレクトリ削除
rmdir frontend/src/components/dashboard
```

**1.2 ディレクトリ名修正**

```bash
# loaders/ → routeLoaders/
mv frontend/src/loaders frontend/src/routeLoaders

# import文修正
sed -i '' 's|from "./loaders/|from "./routeLoaders/|g' frontend/src/App.tsx
```

**1.3 型定義の抽出**

```typescript
// frontend/src/types/slide.ts を作成
export interface Slide {
  id: string;
  title: string;
  created_at: string;
}

// frontend/src/types/user.ts を作成
export interface User {
  name: string;
  email: string;
  picture: string;
}
```

**1.4 テストファイルの移動**

```bash
# コンポーネントと同じ場所にテストを配置
# (Phase 2以降で機能ごと移動)
```

#### 検証

```bash
cd frontend
npm run build     # ビルドエラーがないこと
npm run lint      # Lintエラーがないこと
npm run dev       # 開発サーバーが起動すること
```

#### コミット

```bash
git add .
git commit -m "refactor(frontend): Phase 1 - プロジェクト構成の準備とクリーンアップ

- 不要なバックアップファイル削除
- 空ディレクトリ削除
- loaders → routeLoaders にリネーム
- 型定義を types/ ディレクトリに抽出
"
```

---

### Phase 2: Auth 機能の移行（2-3 時間）

#### 目的

- 最も依存が少ない認証機能を移行
- 移行パターンを確立

#### 作業内容

**2.1 features/auth/ ディレクトリ作成**

```bash
mkdir -p frontend/src/features/auth/{components,hooks}
```

**2.2 ファイル移動**

```bash
# コンポーネント
mv frontend/src/components/Login.tsx frontend/src/features/auth/components/
mv frontend/src/components/ProtectedRoute.tsx frontend/src/features/auth/components/

# フック
mv frontend/src/hooks/useAuth.ts frontend/src/features/auth/hooks/

# ページ
mv frontend/src/pages/LoginPage.tsx frontend/src/features/auth/
```

**2.3 index.ts 作成（Public API）**

```typescript
// frontend/src/features/auth/index.ts
export { default as LoginPage } from "./LoginPage";
export { default as ProtectedRoute } from "./components/ProtectedRoute";
export { useAuth } from "./hooks/useAuth";
export type { UserInfo } from "./hooks/useAuth";
```

**2.4 import 文の自動修正**

```bash
# 自動修正スクリプト実行（後述）
node scripts/update-imports.js auth
```

**2.5 手動修正が必要な箇所**

```typescript
// Before
import { useAuth } from "../hooks/useAuth";

// After
import { useAuth } from "@/features/auth";
```

#### 検証

```bash
npm run build
npm run test -- auth
npm run dev
# ログイン・ログアウトが動作すること
```

#### コミット

```bash
git add .
git commit -m "refactor(frontend): Phase 2 - Auth機能をfeatures/auth/に移行

- Login, ProtectedRoute コンポーネントを移行
- useAuth フックを移行
- LoginPage を移行
- Public API (index.ts) を作成
"
```

---

### Phase 3: Dashboard 機能の移行（3-4 時間）

#### 目的

- ダッシュボード関連の機能を集約

#### 作業内容

**3.1 features/dashboard/ ディレクトリ作成**

```bash
mkdir -p frontend/src/features/dashboard/{components,loaders}
```

**3.2 ファイル移動**

```bash
# コンポーネント
mv frontend/src/components/UnifiedCard.tsx frontend/src/features/dashboard/components/
mv frontend/src/components/QuickActionMenu.tsx frontend/src/features/dashboard/components/
mv frontend/src/components/DropzoneCard.tsx frontend/src/features/dashboard/components/

# Loader
mv frontend/src/routeLoaders/dashboardLoader.ts frontend/src/features/dashboard/loaders/

# ページ
mv frontend/src/pages/DashboardPage.tsx frontend/src/features/dashboard/
```

**3.3 index.ts 作成**

```typescript
// frontend/src/features/dashboard/index.ts
export { default as DashboardPage } from "./DashboardPage";
export { dashboardLoader } from "./loaders/dashboardLoader";
```

**3.4 import 文修正**

```bash
node scripts/update-imports.js dashboard
```

**3.5 App.tsx の修正**

```typescript
// Before
import DashboardPage from "./pages/DashboardPage";
import { dashboardLoader } from "./routeLoaders/dashboardLoader";

// After
import { DashboardPage, dashboardLoader } from "@/features/dashboard";
```

#### 検証

```bash
npm run build
npm run dev
# ダッシュボードが正常に表示されること
# 新規作成、PDF アップロードが動作すること
```

#### コミット

```bash
git add .
git commit -m "refactor(frontend): Phase 3 - Dashboard機能をfeatures/dashboard/に移行

- UnifiedCard, QuickActionMenu, DropzoneCard を移行
- dashboardLoader を移行
- DashboardPage を移行
"
```

---

### Phase 4: Slide 機能の移行（3-4 時間）

#### 目的

- スライド表示・詳細機能を集約

#### 作業内容

**4.1 features/slide/ ディレクトリ作成**

```bash
mkdir -p frontend/src/features/slide/components
```

**4.2 ファイル移動**

```bash
# 既存のslideディレクトリ
mv frontend/src/components/slide/* frontend/src/features/slide/components/

# その他関連コンポーネント
mv frontend/src/components/SlideViewer.tsx frontend/src/features/slide/components/

# ページ
mv frontend/src/pages/SlideDetailPage.tsx frontend/src/features/slide/
```

**4.3 index.ts 作成**

```typescript
// frontend/src/features/slide/index.ts
export { default as SlideDetailPage } from "./SlideDetailPage";
export { default as SlideViewer } from "./components/SlideViewer";
```

**4.4 import 文修正**

```bash
node scripts/update-imports.js slide
```

#### 検証

```bash
npm run build
npm run dev
# スライド詳細ページが表示されること
# スライド表示、チャットパネルが動作すること
```

#### コミット

```bash
git add .
git commit -m "refactor(frontend): Phase 4 - Slide機能をfeatures/slide/に移行

- SlideViewer, SlideContentViewer, ChatPanel などを移行
- SlideDetailPage を移行
"
```

---

### Phase 5: Generation 機能の移行（3-4 時間）

#### 目的

- スライド生成関連の機能を集約

#### 作業内容

**5.1 features/generation/ ディレクトリ作成**

```bash
mkdir -p frontend/src/features/generation/{components,hooks,store}
```

**5.2 ファイル移動**

```bash
# コンポーネント
mv frontend/src/components/InitialInputForm.tsx frontend/src/features/generation/components/
mv frontend/src/components/SlideHistory.tsx frontend/src/features/generation/components/
mv frontend/src/components/SlideHistory.test.tsx frontend/src/features/generation/components/
mv frontend/src/components/SectionHeader.tsx frontend/src/features/generation/components/
mv frontend/src/components/ThinkingIndicator.tsx frontend/src/features/generation/components/

# フック
mv frontend/src/hooks/useReactAgent.ts frontend/src/features/generation/hooks/

# Store
mv frontend/src/store/reactAgentAtoms.ts frontend/src/features/generation/store/

# ページ
mv frontend/src/pages/GenerationProgressPage.tsx frontend/src/features/generation/
```

**5.3 index.ts 作成**

```typescript
// frontend/src/features/generation/index.ts
export { default as GenerationProgressPage } from "./GenerationProgressPage";
export { useReactAgent } from "./hooks/useReactAgent";
```

**5.4 import 文修正**

```bash
node scripts/update-imports.js generation
```

#### 検証

```bash
npm run build
npm run test
npm run dev
# スライド生成が動作すること
# 進捗表示が正常に表示されること
```

#### コミット

```bash
git add .
git commit -m "refactor(frontend): Phase 5 - Generation機能をfeatures/generation/に移行

- InitialInputForm, SlideHistory, ThinkingIndicator などを移行
- useReactAgent フックを移行
- reactAgentAtoms を移行
- GenerationProgressPage を移行
"
```

---

### Phase 6: 共通コンポーネントの整理（2-3 時間）

#### 目的

- 複数機能で使用するコンポーネントを shared/ に集約

#### 作業内容

**6.1 shared/ ディレクトリ作成**

```bash
mkdir -p frontend/src/shared/components
```

**6.2 共通コンポーネントの移動**

```bash
# ChatInput, ChatMessage は複数機能で使用
mv frontend/src/components/ChatInput.tsx frontend/src/shared/components/
mv frontend/src/components/ChatMessage.tsx frontend/src/shared/components/
```

**6.3 index.ts 作成**

```typescript
// frontend/src/shared/index.ts
export { default as ChatInput } from "./components/ChatInput";
export { default as ChatMessage } from "./components/ChatMessage";
```

**6.4 import 文修正**

```bash
node scripts/update-imports.js shared
```

#### 検証

```bash
npm run build
npm run dev
# チャット機能が正常に動作すること
```

#### コミット

```bash
git add .
git commit -m "refactor(frontend): Phase 6 - 共通コンポーネントをshared/に移行

- ChatInput, ChatMessage を shared/components/ に移動
"
```

---

### Phase 7: 最終クリーンアップ（1-2 時間）

#### 目的

- 古いディレクトリの削除
- パスエイリアスの設定

#### 作業内容

**7.1 空ディレクトリの削除**

```bash
# 全ファイル移動後
rmdir frontend/src/components/slide  # 空になったはず
rmdir frontend/src/components        # 空になったはず
rmdir frontend/src/pages             # 空になったはず
rmdir frontend/src/hooks             # 空になったはず
rmdir frontend/src/store             # 空になったはず
rmdir frontend/src/routeLoaders      # 空になったはず
```

**7.2 パスエイリアス設定**

```typescript
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@/features/*": ["src/features/*"],
      "@/shared/*": ["src/shared/*"],
      "@/lib/*": ["src/lib/*"],
      "@/types/*": ["src/types/*"]
    }
  }
}
```

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

**7.3 全体の import 文をパスエイリアスに統一**

```bash
node scripts/update-all-imports.js
```

#### 検証

```bash
npm run build
npm run test
npm run lint
npm run dev
# 全機能が正常に動作すること
```

#### コミット

```bash
git add .
git commit -m "refactor(frontend): Phase 7 - リファクタリング完了とパスエイリアス設定

- 旧ディレクトリ削除
- パスエイリアス設定 (@/, @/features/, etc.)
- 全importパスを統一
"
```

---

## ファイル移動マッピング

### 移動前 → 移動後

#### Auth 機能

| 移動前                          | 移動後                                        |
| ------------------------------- | --------------------------------------------- |
| `components/Login.tsx`          | `features/auth/components/Login.tsx`          |
| `components/ProtectedRoute.tsx` | `features/auth/components/ProtectedRoute.tsx` |
| `hooks/useAuth.ts`              | `features/auth/hooks/useAuth.ts`              |
| `pages/LoginPage.tsx`           | `features/auth/LoginPage.tsx`                 |

#### Dashboard 機能

| 移動前                            | 移動後                                              |
| --------------------------------- | --------------------------------------------------- |
| `components/UnifiedCard.tsx`      | `features/dashboard/components/UnifiedCard.tsx`     |
| `components/QuickActionMenu.tsx`  | `features/dashboard/components/QuickActionMenu.tsx` |
| `components/DropzoneCard.tsx`     | `features/dashboard/components/DropzoneCard.tsx`    |
| `routeLoaders/dashboardLoader.ts` | `features/dashboard/loaders/dashboardLoader.ts`     |
| `pages/DashboardPage.tsx`         | `features/dashboard/DashboardPage.tsx`              |

#### Slide 機能

| 移動前                                    | 移動後                                             |
| ----------------------------------------- | -------------------------------------------------- |
| `components/SlideViewer.tsx`              | `features/slide/components/SlideViewer.tsx`        |
| `components/slide/SlideContentViewer.tsx` | `features/slide/components/SlideContentViewer.tsx` |
| `components/slide/SlideDetailLayout.tsx`  | `features/slide/components/SlideDetailLayout.tsx`  |
| `components/slide/ChatPanel.tsx`          | `features/slide/components/ChatPanel.tsx`          |
| `components/slide/SuggestedQuestions.tsx` | `features/slide/components/SuggestedQuestions.tsx` |
| `pages/SlideDetailPage.tsx`               | `features/slide/SlideDetailPage.tsx`               |

#### Generation 機能

| 移動前                             | 移動後                                                 |
| ---------------------------------- | ------------------------------------------------------ |
| `components/InitialInputForm.tsx`  | `features/generation/components/InitialInputForm.tsx`  |
| `components/SlideHistory.tsx`      | `features/generation/components/SlideHistory.tsx`      |
| `components/SlideHistory.test.tsx` | `features/generation/components/SlideHistory.test.tsx` |
| `components/SectionHeader.tsx`     | `features/generation/components/SectionHeader.tsx`     |
| `components/ThinkingIndicator.tsx` | `features/generation/components/ThinkingIndicator.tsx` |
| `hooks/useReactAgent.ts`           | `features/generation/hooks/useReactAgent.ts`           |
| `store/reactAgentAtoms.ts`         | `features/generation/store/reactAgentAtoms.ts`         |
| `pages/GenerationProgressPage.tsx` | `features/generation/GenerationProgressPage.tsx`       |

#### 共通コンポーネント

| 移動前                       | 移動後                              |
| ---------------------------- | ----------------------------------- |
| `components/ChatInput.tsx`   | `shared/components/ChatInput.tsx`   |
| `components/ChatMessage.tsx` | `shared/components/ChatMessage.tsx` |

---

## 自動化スクリプト

### import 文自動修正スクリプト

```javascript
// scripts/update-imports.js
const fs = require("fs");
const path = require("path");
const glob = require("glob");

const IMPORT_MAPPINGS = {
  auth: {
    "hooks/useAuth": "features/auth",
    "components/Login": "features/auth",
    "components/ProtectedRoute": "features/auth",
    "pages/LoginPage": "features/auth",
  },
  dashboard: {
    "components/UnifiedCard": "features/dashboard/components/UnifiedCard",
    "components/QuickActionMenu":
      "features/dashboard/components/QuickActionMenu",
    "components/DropzoneCard": "features/dashboard/components/DropzoneCard",
    "routeLoaders/dashboardLoader": "features/dashboard",
    "pages/DashboardPage": "features/dashboard",
  },
  slide: {
    "components/SlideViewer": "features/slide/components/SlideViewer",
    "components/slide/": "features/slide/components/",
    "pages/SlideDetailPage": "features/slide",
  },
  generation: {
    "components/InitialInputForm":
      "features/generation/components/InitialInputForm",
    "components/SlideHistory": "features/generation/components/SlideHistory",
    "components/SectionHeader": "features/generation/components/SectionHeader",
    "components/ThinkingIndicator":
      "features/generation/components/ThinkingIndicator",
    "hooks/useReactAgent": "features/generation",
    "store/reactAgentAtoms": "features/generation/store/reactAgentAtoms",
    "pages/GenerationProgressPage": "features/generation",
  },
  shared: {
    "components/ChatInput": "shared/components/ChatInput",
    "components/ChatMessage": "shared/components/ChatMessage",
  },
};

function updateImports(feature) {
  const mappings = IMPORT_MAPPINGS[feature];
  if (!mappings) {
    console.error(`Unknown feature: ${feature}`);
    return;
  }

  // src配下の全tsx/tsファイルを対象
  const files = glob.sync("frontend/src/**/*.{ts,tsx}", {
    ignore: ["**/node_modules/**", "**/dist/**"],
  });

  let totalUpdates = 0;

  files.forEach((file) => {
    let content = fs.readFileSync(file, "utf8");
    let updated = false;

    Object.entries(mappings).forEach(([oldPath, newPath]) => {
      // 相対パスのインポートを検出
      const regex = new RegExp(
        `from ['"](\\.\\./)*${oldPath.replace(/\//g, "\\/")}['"]`,
        "g"
      );

      if (regex.test(content)) {
        // 相対パスを計算
        const fileDir = path.dirname(file);
        const targetPath = path.resolve("frontend/src", newPath);
        let relativePath = path.relative(fileDir, targetPath);

        // .ts/.tsx拡張子を除去
        relativePath = relativePath.replace(/\.(ts|tsx)$/, "");

        // 相対パス形式に修正
        if (!relativePath.startsWith(".")) {
          relativePath = "./" + relativePath;
        }

        content = content.replace(regex, `from '${relativePath}'`);
        updated = true;
      }
    });

    if (updated) {
      fs.writeFileSync(file, content, "utf8");
      console.log(`✅ Updated: ${file}`);
      totalUpdates++;
    }
  });

  console.log(
    `\n🎉 Total ${totalUpdates} files updated for feature: ${feature}`
  );
}

// コマンドライン引数から機能名を取得
const feature = process.argv[2];
if (!feature) {
  console.error("Usage: node update-imports.js <feature>");
  console.error("Available features:", Object.keys(IMPORT_MAPPINGS).join(", "));
  process.exit(1);
}

updateImports(feature);
```

### 使用方法

```bash
# package.jsonにスクリプト追加
npm pkg set scripts.refactor:imports="node scripts/update-imports.js"

# 実行
npm run refactor:imports auth
npm run refactor:imports dashboard
npm run refactor:imports slide
npm run refactor:imports generation
npm run refactor:imports shared
```

---

## テスト戦略

### 各フェーズでのテスト項目

#### 自動テスト

```bash
# ビルドエラーチェック
npm run build

# TypeScript型チェック
npm run type-check  # or tsc --noEmit

# Lintチェック
npm run lint

# ユニットテスト
npm run test

# カバレッジ確認
npm run test:coverage
```

#### 手動テスト（E2E シナリオ）

**Phase 2 (Auth) 完了後**:

- [ ] ログインページが表示される
- [ ] Google OAuth ログインが成功する
- [ ] ログアウトが正常に動作する
- [ ] 未認証時に保護ルートへアクセスするとログインページにリダイレクトされる

**Phase 3 (Dashboard) 完了後**:

- [ ] ダッシュボードが表示される
- [ ] スライド履歴が表示される
- [ ] 新規作成ボタンが動作する
- [ ] PDF アップロードが動作する
- [ ] クイックアクションメニューが表示される

**Phase 4 (Slide) 完了後**:

- [ ] スライド詳細ページが表示される
- [ ] スライドビューアが表示される
- [ ] チャットパネルが表示される
- [ ] 推奨質問が表示される

**Phase 5 (Generation) 完了後**:

- [ ] スライド生成ページが表示される
- [ ] 入力フォームが動作する
- [ ] 進捗表示が正常に動作する
- [ ] スライド生成が完了する
- [ ] 生成されたスライドが表示される

**Phase 7 (最終) 完了後**:

- [ ] 全機能が正常に動作する
- [ ] パフォーマンス低下がない
- [ ] コンソールエラーがない

---

## ロールバックプラン

### 各フェーズでのロールバック手順

#### Git 履歴を利用したロールバック

```bash
# 最新コミットを取り消す（Phase完了直後）
git reset --hard HEAD~1

# 特定のPhaseまで戻る
git log --oneline | grep "Phase"
git reset --hard <commit-hash>
```

#### 部分的なロールバック

```bash
# 特定のファイルだけ元に戻す
git checkout HEAD~1 -- frontend/src/features/auth

# 再ビルド
cd frontend && npm run build
```

#### 緊急ロールバック（本番環境）

```bash
# 前回のデプロイバージョンに戻す
git revert <commit-hash>
git push origin main

# CI/CDが自動デプロイ
```

---

## メリット・デメリット

### メリット

#### 開発効率の向上

- ✅ **コードの発見性が高い** - 機能名からファイルの場所がすぐわかる
- ✅ **関連コードが近くにある** - ページ・コンポーネント・ロジックが同じディレクトリ
- ✅ **新機能追加が容易** - `features/<新機能>/` を作るだけ

#### 保守性の向上

- ✅ **機能の独立性が高い** - 1 つの機能を削除・変更しても他に影響しにくい
- ✅ **テストが書きやすい** - コンポーネントとテストが同じ場所
- ✅ **依存関係が明確** - import 文を見れば依存が分かる

#### スケーラビリティ

- ✅ **ファイル数が増えても破綻しない** - 機能ごとに分離
- ✅ **チーム開発に最適** - 機能ごとに担当を分けられる
- ✅ **マイクロフロントエンドへの移行が容易** - 将来的な分割が簡単

### デメリット

#### 初期コスト

- ⚠️ **移行に時間がかかる** - 全 7 フェーズで約 20-30 時間
- ⚠️ **import 文の修正が大量** - 全ファイルの import 文を修正
- ⚠️ **学習コストがある** - チームメンバーへの周知が必要

#### 一時的なリスク

- ⚠️ **移行中のバグ混入リスク** - import 修正ミスなど
- ⚠️ **テスト実行時間の増加** - 各フェーズで全テスト実行
- ⚠️ **コンフリクトの可能性** - 並行開発中の場合

---

## 成功指標（KPI）

### 定量的指標

| 指標                             | 現状                 | 目標     | 測定方法             |
| -------------------------------- | -------------------- | -------- | -------------------- |
| ディレクトリ階層の深さ           | 3 階層               | 4-5 階層 | `find`コマンド       |
| 1 ディレクトリあたりのファイル数 | 13 個（components/） | 3-5 個   | `ls`コマンド         |
| import パスの平均長              | 20 文字              | 15 文字  | grep + awk           |
| ビルド時間                       | -                    | 変化なし | `time npm run build` |
| バンドルサイズ                   | -                    | 変化なし | vite build output    |

### 定性的指標

- [ ] 新規メンバーが機能の場所をすぐに見つけられる
- [ ] コードレビュー時に関連ファイルを探す時間が減る
- [ ] 機能追加時の配置場所で迷わない
- [ ] テストファイルとコンポーネントの対応が明確

---

## 参考資料

### アーキテクチャパターン

- [Feature-Sliced Design](https://feature-sliced.design/)
- [React + TypeScript: Feature-first architecture](https://www.robinwieruch.de/react-folder-structure/)
- [Atomic Design](https://bradfrost.com/blog/post/atomic-web-design/)

### 既存のベストプラクティス

- [Bulletproof React](https://github.com/alan2207/bulletproof-react)
- [React Folder Structure in 5 Steps](https://www.robinwieruch.de/react-folder-structure/)
- [Vertical Slice Architecture](https://www.jimmybogard.com/vertical-slice-architecture/)

---

## FAQ

### Q1: なぜ `pages/` を廃止するのか？

**A**: Feature-first では、ページも機能の一部として扱います。`DashboardPage.tsx` は `features/dashboard/` に配置することで、関連するコンポーネント・ロジックとコロケーションされます。

### Q2: 共通コンポーネントはどう扱うべきか？

**A**: 複数機能で使用するコンポーネントは `shared/` に配置します。ただし、最初から共通化せず、実際に 2 箇所以上で使用されてから移動するのが推奨です（YAGNI 原則）。

### Q3: 既存の import パスを全て書き換える必要があるか？

**A**: パスエイリアス（`@/features/auth`）を設定すれば、相対パス（`../../features/auth`）を避けられます。ただし、段階的に移行できるよう、両方のパスが動作する状態を維持することも可能です。

### Q4: テストはどこに配置するか？

**A**: コンポーネントと同じディレクトリに `*.test.tsx` として配置します。統合テスト・E2E テストは `__tests__/` に配置します。

```
features/dashboard/components/
├── UnifiedCard.tsx
└── UnifiedCard.test.tsx  ← ここ
```

### Q5: 全フェーズを一度に実施する必要があるか？

**A**: いいえ。各フェーズは独立しているため、Phase 1 だけ実施して様子を見ることも可能です。ただし、Phase 7（最終クリーンアップ）は全フェーズ完了後に実施してください。

---

## 実施タイミングの推奨

### 推奨タイミング

- ✅ **開発が一段落したタイミング** - 新機能開発の合間
- ✅ **大きな機能追加の前** - リファクタリング後に新機能を追加
- ✅ **チームメンバーが揃っているとき** - 知識共有が容易

### 避けるべきタイミング

- ❌ **リリース直前** - バグ混入リスクが高い
- ❌ **並行開発中** - コンフリクトが多発
- ❌ **緊急バグ修正中** - 優先度が低い

---

## まとめ

このリファクタリングにより、以下が実現されます：

1. **コードの発見性向上** - 機能名から即座にファイルの場所がわかる
2. **保守性の向上** - 関連コードが近くにあり、変更が容易
3. **スケーラビリティ** - ファイル数が増えても破綻しない構造
4. **チーム開発の効率化** - 機能ごとに担当を分けられる

段階的な実施により、既存機能を壊さずに安全に移行できます。

---

**作成者**: Claude Code
**最終更新**: 2025-11-06
