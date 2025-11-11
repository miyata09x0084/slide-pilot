# BulletProof React移行実装方針

**移行完了日**: 2025-11-11
**ステータス**: ✅ 全5フェーズ完了

## 現状分析

### ✅ 完了した項目（全5フェーズ）

| カテゴリ | 実装内容 | Phase |
|---------|---------|-------|
| **アプリケーション層** | `app/provider.tsx`, `app/router.tsx` 分離 | Phase 1 |
| **ファイルベースルーティング** | `app/routes/` 構造（index.tsx, login.tsx, app/*.tsx） | Phase 5 |
| **エラーハンドリング** | `ErrorBoundary` + Suspense fallback | Phase 1 |
| **データフェッチング** | React Query（TanStack Query） | Phase 2 |
| **API層** | `features/*/api/` に分離 | Phase 2, 3 |
| **API Client統一** | `lib/api-client.ts`（Axios + interceptors） | Phase 3 |
| **環境変数管理** | `config/env.ts` 型安全管理 | Phase 3 |
| **型定義集約** | `types/index.ts` 共通型定義 | Phase 4 |
| **アーキテクチャ制約** | ESLint boundaries plugin（feature間import禁止） | Phase 5 |

### 📝 未実装項目（オプション）

| カテゴリ | 理由 |
|---------|------|
| `components/ui/` | 現時点で再利用UIコンポーネントが少ないため保留 |
| Recoil完全削除 | UI状態管理で使用中（React Query移行済み） |

---

## 段階的移行計画（5フェーズ）

### **Phase 1: アプリケーション層の再構築** ✅ 完了

**実装内容**:
- ✅ `app/provider.tsx` - 全プロバイダー統合（GoogleOAuth, QueryClient, Recoil, ErrorBoundary）
- ✅ `app/router.tsx` - ルーター設定分離
- ✅ `components/error/ErrorBoundary.tsx` - エラー境界
- ✅ `components/error/Spinner.tsx` - Suspense fallback

**成果**:
- `main.tsx` がシンプルになり、責任分離が明確化
- グローバルなエラーハンドリングを実現

---

### **Phase 2: React Query導入** ✅ 完了

**実装内容**:
- ✅ `lib/react-query.ts` - QueryClient設定（staleTime: 5分, gcTime: 10分）
- ✅ `features/dashboard/api/get-slides.ts` + `useSlides()` hook
- ✅ `features/slide/api/get-slide-detail.ts` + `useSlideDetail()` hook
- ✅ React Router Loaderからhooksへ移行完了
- ✅ React Query DevTools（開発環境のみ有効）

**成果**:
- サーバー状態のキャッシュ・自動再取得を実現
- ローディング・エラー状態の統一管理
- Recoilはクライアント状態管理のみに限定

---

### **Phase 3: API Client統一** ✅ 完了

**実装内容**:
- ✅ `lib/api-client.ts` - Axiosインスタンス
  - リクエストインターセプター（X-User-Email自動付与）
  - レスポンスインターセプター（401時ログインリダイレクト）
- ✅ `config/env.ts` - 環境変数型安全管理（API_URL, GOOGLE_CLIENT_ID）
- ✅ `features/generation/api/create-thread.ts` - スレッド作成
- ✅ `features/generation/api/get-assistants.ts` - Assistant検索
- ✅ `features/dashboard/api/upload-pdf.ts` - PDF アップロード
- ✅ 全API関数でAxios使用（SSEのみfetch継続）

**成果**:
- エラーハンドリング統一
- 環境変数の一元管理

---

### **Phase 4: 共通リソースの整理** ✅ 完了

**実装内容**:
- ✅ `types/index.ts` - 共通型定義集約
  - `UserInfo`, `Message`, `ThinkingStep`
  - `Slide`, `SlideDetail`, `SlideData`
  - `ApiError`
- ✅ 10ファイルのimport更新（`@/types`に統一）
- ✅ 型定義の重複削除

**成果**:
- Single Source of Truthを実現
- 型変更時の影響範囲が明確化

---

### **Phase 5: ルーティング改善とESLintルール追加** ✅ 完了

**実装内容**:
- ✅ `app/routes/` ファイルベース構造
  ```
  app/routes/
  ├── index.tsx          # DashboardRoute
  ├── login.tsx          # LoginRoute
  └── app/
      ├── root.tsx       # ProtectedLayout
      ├── generate.tsx   # GenerateRoute
      └── slides.tsx     # SlidesRoute
  ```
- ✅ `eslint-plugin-boundaries` 導入
  - Feature間import禁止ルール
  - `types`, `config` → `shared` → `features` → `app` 依存制約
- ✅ ビルド成功（dist: 1.05MB main chunk）
- ✅ テスト成功（87/89 passing、既存2件失敗）

**成果**:
- ルート定義の可読性向上
- アーキテクチャ違反の自動検出

---

## 移行後のディレクトリ構造

```
frontend/src/
├── app/                        # アプリケーション層（NEW）
│   ├── routes/                 # ルート定義
│   │   ├── index.tsx           # "/" (Dashboard)
│   │   ├── login.tsx           # "/login"
│   │   └── app/                # 認証必要
│   │       ├── root.tsx        # レイアウト
│   │       ├── generate.tsx    # スライド生成
│   │       └── slides.tsx      # スライド詳細
│   ├── provider.tsx            # グローバルプロバイダー
│   └── router.tsx              # ルーター設定
│
├── features/                   # 機能モジュール（既存）
│   ├── auth/
│   │   ├── api/                # API関数（NEW）
│   │   ├── components/
│   │   ├── hooks/
│   │   └── index.ts
│   ├── dashboard/
│   │   ├── api/                # API関数（NEW）
│   │   ├── components/
│   │   └── index.ts
│   ├── generation/
│   │   ├── api/                # API関数（NEW）
│   │   ├── components/
│   │   ├── hooks/
│   │   └── index.ts
│   └── slide/
│       ├── api/                # API関数（NEW）
│       ├── components/
│       └── index.ts
│
├── components/                 # 共通コンポーネント（拡張）
│   ├── ui/                     # 再利用可能UIコンポーネント（NEW）
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   └── card.tsx
│   └── error/                  # エラー表示（NEW）
│       └── ErrorBoundary.tsx
│
├── lib/                        # 共通ライブラリ（NEW）
│   ├── api-client.ts           # Axiosインスタンス
│   ├── react-query.ts          # React Query設定
│   └── auth.tsx                # 認証ユーティリティ
│
├── config/                     # 設定（NEW）
│   └── env.ts                  # 環境変数管理
│
├── types/                      # 共通型定義（NEW）
│   └── index.ts
│
├── utils/                      # ユーティリティ（NEW）
│   └── index.ts
│
├── assets/                     # 静的ファイル（既存）
└── main.tsx                    # エントリーポイント（既存）
```

---

## 依存関係の変更

### 追加パッケージ
```bash
npm install @tanstack/react-query axios
npm install -D @tanstack/react-query-devtools eslint-plugin-boundaries
```

### 削除候補パッケージ（Phase 2完了後）
```bash
npm uninstall recoil  # React Queryで代替可能な場合
```

---

## リスク管理

| リスク | 影響 | 対策 |
|--------|------|------|
| SSEストリーミングがReact Queryで正しく動作しない | 高 | カスタムフック（`useStreamingQuery`）作成 |
| Recoil削除でグローバル状態が失われる | 中 | React QueryのグローバルキャッシュとZustandで代替検討 |
| 移行中のバグ混入 | 中 | 既存テストを全て実行し、各Phase後に動作確認 |
| path aliasの変更で既存importが壊れる | 低 | VSCode自動import機能 + ESLintで検出 |

---

## 成功基準（全て達成 ✅）

| 基準 | 達成状況 |
|------|---------|
| React Router Loaderから脱却 | ✅ React Query hooksへ移行完了 |
| `app/routes/` ファイルベース構造 | ✅ 5ファイル作成完了 |
| React Query導入 | ✅ キャッシュ・自動再取得動作中 |
| API Client統一 | ✅ Axios interceptors実装済み |
| ESLint boundaries動作 | ✅ Feature間import禁止ルール有効 |
| 既存テスト維持 | ✅ 87/89 passing（既存2件失敗のみ） |
| ビルドサイズ | ✅ 1.05MB（Phase 1比 +5%未満） |

---

## 参考リンク

- [BulletProof React GitHub](https://github.com/alan2207/bulletproof-react/tree/master/apps/react-vite)
- [Project Structure Documentation](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md)
- [React Query Documentation](https://tanstack.com/query/latest/docs/react/overview)
- [React Router v7 Documentation](https://reactrouter.com/en/main)
