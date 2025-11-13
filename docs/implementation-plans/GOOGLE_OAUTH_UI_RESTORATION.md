# Google OAuth UI 復元 - 設計・実装方針

**作成日**: 2025-11-13
**ステータス**: 設計完了
**優先度**: High
**担当**: Claude Code

---

## 📋 概要

**目的**: Supabase Auth統合により消失したGoogle公式OAuth UIを復元し、UXを改善する

**背景**:
- Supabase Auth統合（コミット `28e1be9`）で `@react-oauth/google` を削除
- Google公式の洗練されたOAuth UI（ポップアップ、Googleロゴ付きボタン）が消失
- 現在は自作の青いボタン（`Sign in with Google`）のみ
- ユーザー体験が低下（Google公式UIの方が信頼性が高い）

**解決策**: ハイブリッド実装
- **UI**: `@react-oauth/google` の `<GoogleLogin>` コンポーネント（Google公式）
- **バックエンド**: Supabase Auth の `signInWithIdToken()` でセッション管理
- **メリット**: Google公式UIを保ちつつ、Supabaseの認証・JWT発行・RLSを利用

---

## 🔍 問題分析

### Supabase移行前（コミット `28e1be9^`）

**実装**:
```typescript
// frontend/src/features/auth/LoginPage.tsx
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { jwtDecode } from 'jwt-decode';

const handleLoginSuccess = (credentialResponse: CredentialResponse) => {
  if (credentialResponse.credential) {
    const decoded: any = jwtDecode(credentialResponse.credential);
    const userInfo = { name: decoded.name, email: decoded.email, picture: decoded.picture };
    login(userInfo); // localStorage に保存
    navigate('/', { replace: true });
  }
};

return <Login onSuccess={handleLoginSuccess} />;
```

**Login コンポーネント**:
```typescript
// frontend/src/features/auth/components/Login.tsx
import { GoogleLogin } from '@react-oauth/google';

<GoogleLogin
  onSuccess={onSuccess}
  onError={() => console.error('Login Failed')}
/>
```

**UI**: Google公式のOAuthボタン（ポップアップ型、Googleロゴ、洗練されたデザイン）

**問題点**:
- JWT をバックエンドに送信していない
- localStorage のみでセッション管理（改ざん可能）
- リフレッシュトークンなし

---

### Supabase移行後（現在）

**実装**:
```typescript
// frontend/src/features/auth/LoginPage.tsx
import { useAuth } from './hooks/useAuth';

const handleLogin = async () => {
  try {
    await login(); // Supabase OAuth フロー開始
  } catch (error) {
    console.error('Login failed:', error);
  }
};

return (
  <button onClick={handleLogin} style={{ /* 自作スタイル */ }}>
    Sign in with Google
  </button>
);
```

**useAuth フック**:
```typescript
// frontend/src/features/auth/hooks/useAuth.ts
const login = async () => {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: `${window.location.origin}/` },
  });
  if (error) throw error;
};
```

**UI**: 自作の青いボタン（シンプルだが、Google公式UIほど洗練されていない）

**メリット**:
- Supabase Auth で JWT 自動管理
- セッション永続化・リフレッシュトークン対応
- RLS（Row Level Security）対応

**問題点**:
- **Google公式UIが消失** → UX低下
- ユーザーが「これは本当にGoogleログインか?」と疑問を持つ可能性

---

## 🎯 解決策: ハイブリッド実装

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│ フロントエンド (React)                                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  LoginPage                                                    │
│    ↓                                                          │
│  <GoogleOAuthProvider> (from @react-oauth/google)             │
│    ↓                                                          │
│  <GoogleLogin onSuccess={handleSuccess} />                    │
│    │                                                          │
│    ├─ Google OAuth ポップアップ（Google公式UI）               │
│    │                                                          │
│    └─ onSuccess(credentialResponse)                           │
│         ↓                                                     │
│       credentialResponse.credential (Google JWT)              │
│         ↓                                                     │
│       Supabase Auth.signInWithIdToken({                       │
│         provider: 'google',                                   │
│         token: credential  // Google JWT を渡す               │
│       })                                                      │
│         ↓                                                     │
│       Supabase が Google JWT を検証 → セッション発行          │
│         ↓                                                     │
│       access_token, refresh_token 発行                        │
│         ↓                                                     │
│       useAuth フックで Session 管理                           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### データフロー

```
1. ユーザーが <GoogleLogin> ボタンをクリック
2. Google OAuth ポップアップ表示（Google公式UI）
3. ユーザーが Google アカウントを選択
4. Google が JWT 発行（credentialResponse.credential）
5. フロントエンドが Google JWT を取得
6. Supabase Auth.signInWithIdToken() を呼び出し
7. Supabase が Google JWT を検証（Google の公開鍵で署名検証）
8. Supabase が自身の JWT（access_token）を発行
9. Supabase Session 管理開始（localStorage 自動管理）
10. ダッシュボードへリダイレクト
```

### キーポイント

1. **UI**: `@react-oauth/google` の `<GoogleLogin>` で Google 公式 UI を提供
2. **認証**: Supabase の `signInWithIdToken()` で Google JWT を検証
3. **セッション管理**: Supabase が自動管理（リフレッシュトークン、永続化）
4. **バックエンド**: FastAPI は Supabase JWT を検証（既存実装を維持）

---

## 📐 実装計画

### Phase 1: 依存関係の再導入（10分）

#### 1-1. パッケージインストール

```bash
cd frontend
npm install @react-oauth/google
```

**注意**: `jwt-decode` は不要（Supabase が処理）

#### 1-2. 環境変数確認

**`frontend/.env.local`** に以下が設定済みか確認:
```bash
VITE_GOOGLE_CLIENT_ID=692318722679-j74jo1d8gecscbsr970cnuuun176pblv.apps.googleusercontent.com
VITE_SUPABASE_URL=https://smcgphoiyhroeqdwbvpr.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
```

**成功基準**:
- [ ] `@react-oauth/google` インストール完了
- [ ] 環境変数 `VITE_GOOGLE_CLIENT_ID` 設定済み

---

### Phase 2: AppProvider の修正（5分）

#### 2-1. GoogleOAuthProvider の復元

**修正ファイル**: `frontend/src/app/provider.tsx`

```typescript
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Before: GoogleOAuthProvider 削除済み
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import { Suspense } from 'react';
import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { RecoilRoot } from 'recoil';
import { ErrorBoundary } from '../components/error/ErrorBoundary';
import { Spinner } from '../components/error/Spinner';
import { queryClient } from '../lib/react-query';
import { env } from '../config/env';

export function AppProvider({ children }: AppProviderProps) {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RecoilRoot>
          <Suspense fallback={<Spinner />}>{children}</Suspense>
        </RecoilRoot>
        {env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// After: GoogleOAuthProvider 追加（Supabase Auth と併用）
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import { Suspense } from 'react';
import type { ReactNode } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { RecoilRoot } from 'recoil';
import { ErrorBoundary } from '../components/error/ErrorBoundary';
import { Spinner } from '../components/error/Spinner';
import { queryClient } from '../lib/react-query';
import { env } from '../config/env';

interface AppProviderProps {
  children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  return (
    <ErrorBoundary>
      <GoogleOAuthProvider clientId={env.GOOGLE_CLIENT_ID}>
        <QueryClientProvider client={queryClient}>
          <RecoilRoot>
            <Suspense fallback={<Spinner />}>{children}</Suspense>
          </RecoilRoot>
          {env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
        </QueryClientProvider>
      </GoogleOAuthProvider>
    </ErrorBoundary>
  );
}
```

**変更内容**:
- ✅ `GoogleOAuthProvider` を追加（最外部でラップ）
- ✅ `env.GOOGLE_CLIENT_ID` を渡す

**成功基準**:
- [ ] TypeScript エラーなし
- [ ] `GoogleOAuthProvider` が全体をラップ

---

### Phase 3: LoginPage のハイブリッド実装（20分）

#### 3-1. useAuth フック修正（signInWithIdToken 対応）

**修正ファイル**: `frontend/src/features/auth/hooks/useAuth.ts`

```typescript
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Before: signInWithOAuth のみ（リダイレクト型）
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const login = async () => {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: `${window.location.origin}/` },
  });
  if (error) throw error;
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// After: signInWithIdToken 追加（Google JWT 検証）
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const login = async () => {
  // ⚠️ この関数は使わない（後述の loginWithGoogle を使用）
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: `${window.location.origin}/` },
  });
  if (error) throw error;
};

const loginWithGoogle = async (googleCredential: string) => {
  // Google JWT を Supabase に渡して検証
  const { data, error } = await supabase.auth.signInWithIdToken({
    provider: 'google',
    token: googleCredential,
  });

  if (error) {
    console.error('Supabase Auth failed:', error);
    throw error;
  }

  console.log('✅ Supabase Auth success:', data.user?.email);
};

return {
  user,
  loading,
  login, // リダイレクト型（フォールバック用）
  loginWithGoogle, // Google JWT 検証型（メイン）
  logout,
  isAuthenticated: !!user,
};
```

**変更内容**:
- ✅ `loginWithGoogle(googleCredential: string)` メソッド追加
- ✅ `signInWithIdToken()` で Google JWT を検証
- ✅ 既存の `login()` は維持（フォールバック用）

---

#### 3-2. LoginPage 修正

**修正ファイル**: `frontend/src/features/auth/LoginPage.tsx`

```typescript
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Before: 自作ボタン（Supabase OAuth リダイレクト型）
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useAuth } from './hooks/useAuth';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleLogin = async () => {
    try {
      await login(); // Supabase OAuth フロー開始
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <div style={{ /* ... */ }}>
      <button onClick={handleLogin} style={{ /* 自作スタイル */ }}>
        Sign in with Google
      </button>
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// After: <GoogleLogin> コンポーネント（Google 公式 UI）
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import type { CredentialResponse } from '@react-oauth/google';
import { useAuth } from './hooks/useAuth';

export default function LoginPage() {
  const navigate = useNavigate();
  const { loginWithGoogle, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) {
      console.error('No credential received from Google');
      return;
    }

    try {
      // Google JWT を Supabase に渡してセッション作成
      await loginWithGoogle(credentialResponse.credential);
      navigate('/', { replace: true });
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  const handleGoogleError = () => {
    console.error('❌ [Google OAuth] Login Failed');
    console.error('  Client ID:', import.meta.env.VITE_GOOGLE_CLIENT_ID);
    console.error('  Current Origin:', window.location.origin);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: '#f5f5f5',
      }}
    >
      <div
        style={{
          background: 'white',
          padding: '40px',
          borderRadius: '10px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
          textAlign: 'center',
        }}
      >
        <h1 style={{ marginBottom: '10px', color: '#333' }}>
          ラクヨミ アシスタントAI
        </h1>
        <p style={{ marginBottom: '8px', color: '#666', fontWeight: '600' }}>
          あなた専用の学習パートナー
        </p>
        <p style={{ marginBottom: '6px', color: '#888', fontSize: '14px' }}>
          PDFをアップロードして、難しい資料を楽に読む
        </p>
        <p style={{ marginBottom: '30px', color: '#999', fontSize: '12px' }}>
          📄 対応形式: PDF
        </p>

        {/* Google 公式 OAuth UI */}
        <GoogleLogin
          onSuccess={handleGoogleSuccess}
          onError={handleGoogleError}
        />
      </div>
    </div>
  );
}
```

**変更内容**:
- ✅ `<GoogleLogin>` コンポーネント追加（Google 公式 UI）
- ✅ `handleGoogleSuccess` で Google JWT を取得
- ✅ `loginWithGoogle(credential)` で Supabase セッション作成
- ✅ 元のテキスト（「あなた専用の学習パートナー」等）を復元
- ✅ エラーハンドリング強化

**成功基準**:
- [ ] Google 公式 OAuth ボタンが表示される
- [ ] クリックで Google ポップアップが開く
- [ ] ログイン成功でダッシュボードへリダイレクト

---

### Phase 4: 動作確認（15分）

#### 4-1. ローカル環境起動

```bash
# ターミナル1: バックエンド
cd backend/app
python3 main.py

# ターミナル2: フロントエンド
cd frontend
npm run dev
```

#### 4-2. テストケース

##### テスト1: Google OAuth UI 表示

**手順**:
1. http://localhost:5173/login にアクセス
2. Google ログインボタンが表示されることを確認
3. ボタンデザインが Google 公式（青いボタン、Google ロゴ）であることを確認

**期待結果**:
- [ ] Google 公式 OAuth ボタンが表示される
- [ ] 自作ボタンではなく、Google のデザイン

---

##### テスト2: ログインフロー

**手順**:
1. Google ログインボタンをクリック
2. Google OAuth ポップアップが表示される
3. Google アカウントを選択
4. 認証完了後、ダッシュボードにリダイレクト

**期待結果**:
- [ ] ポップアップで Google OAuth 画面が開く
- [ ] アカウント選択後、自動的に閉じる
- [ ] ダッシュボード (`/`) にリダイレクトされる
- [ ] ユーザー情報（名前、アイコン）が表示される

**確認コマンド**（ブラウザコンソール）:
```javascript
// Supabase セッション確認
supabase.auth.getSession().then(s => console.log(s.data.session))
// → session.access_token が存在すること
```

---

##### テスト3: JWT 検証

**手順**:
```bash
# 1. ブラウザコンソールで JWT 取得
supabase.auth.getSession().then(s => console.log(s.data.session.access_token))

# 2. コピーした JWT で API リクエスト
curl -H "Authorization: Bearer <JWT>" http://localhost:8001/api/slides
```

**期待結果**:
```json
{
  "slides": [...],
  "message": "X件のスライドを取得しました"
}
```

- [ ] 200 OK レスポンス
- [ ] スライドデータが取得できる
- [ ] JWT が正常に検証される

---

##### テスト4: セッション永続化

**手順**:
1. ログイン成功
2. ブラウザをリロード（F5）
3. ログイン状態が維持されることを確認

**期待結果**:
- [ ] リロード後もログイン状態が維持される
- [ ] `/login` にリダイレクトされない
- [ ] ダッシュボードが表示される

---

##### テスト5: ログアウト

**手順**:
1. ダッシュボードでログアウトボタンをクリック
2. `/login` にリダイレクトされることを確認
3. Supabase セッションがクリアされることを確認

**期待結果**:
- [ ] `/login` にリダイレクトされる
- [ ] Google ログインボタンが表示される
- [ ] `supabase.auth.getSession()` が `null` を返す

---

## 📊 実装のメリット

| 項目 | Supabase OAuth のみ（現状） | ハイブリッド実装（提案） |
|------|----------------------|-------------------|
| **UI** | ❌ 自作ボタン（シンプル） | ✅ Google 公式 UI（洗練） |
| **UX** | ❌ 「これは本当に Google?」と疑問 | ✅ Google ブランド信頼性 |
| **セッション管理** | ✅ Supabase 自動管理 | ✅ Supabase 自動管理 |
| **JWT** | ✅ Supabase JWT 発行 | ✅ Supabase JWT 発行 |
| **RLS** | ✅ 対応 | ✅ 対応 |
| **リフレッシュトークン** | ✅ 対応 | ✅ 対応 |
| **実装コスト** | - | ⚠️ 中（パッケージ追加、コード修正） |

**結論**: ハイブリッド実装により、**UX を改善しつつ、Supabase のメリットを維持**できる

---

## ⚠️ 注意事項

### 1. Google Cloud Console 設定

**現状の OAuth 2.0 Client ID**:
```
692318722679-j74jo1d8gecscbsr970cnuuun176pblv.apps.googleusercontent.com
```

**承認済み JavaScript 生成元**:
- `http://localhost:5173` （ローカル開発）
- `https://<your-production-domain>` （本番環境）

**承認済みリダイレクト URI**:
- `http://localhost:5173` （ローカル開発）
- `https://<your-production-domain>` （本番環境）

**⚠️ 重要**: リダイレクト URI は不要（ポップアップ型なので）

---

### 2. signInWithIdToken の制約

**公式ドキュメント**: [Supabase - Sign in with ID Token](https://supabase.com/docs/reference/javascript/auth-signinwithidtoken)

**制約**:
- Google JWT の有効期限は **1時間**
- Supabase は Google の公開鍵で JWT を検証
- Google Cloud Console で OAuth 2.0 Client ID が有効である必要がある

**エラーハンドリング**:
```typescript
const { data, error } = await supabase.auth.signInWithIdToken({
  provider: 'google',
  token: googleCredential,
});

if (error) {
  console.error('Supabase Auth failed:', error);
  // エラーメッセージ例:
  // - "Invalid token" → Google JWT が無効
  // - "Token expired" → JWT の有効期限切れ
  // - "Provider not enabled" → Supabase Dashboard で Google Provider 無効
  throw error;
}
```

---

### 3. 本番環境への展開

**環境変数**:
```bash
# frontend/.env.production
VITE_GOOGLE_CLIENT_ID=692318722679-j74jo1d8gecscbsr970cnuuun176pblv.apps.googleusercontent.com
VITE_SUPABASE_URL=https://smcgphoiyhroeqdwbvpr.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
```

**Google Cloud Console**:
- 承認済み JavaScript 生成元に本番ドメインを追加
- OAuth consent screen で本番ドメインを検証

---

## 📚 参考資料

### 公式ドキュメント

- [Supabase - Sign in with ID Token](https://supabase.com/docs/reference/javascript/auth-signinwithidtoken)
- [@react-oauth/google - NPM](https://www.npmjs.com/package/@react-oauth/google)
- [Google OAuth 2.0 for Client-side Web Applications](https://developers.google.com/identity/protocols/oauth2/javascript-implicit-flow)

### 内部ドキュメント

- [SUPABASE_AUTH_INTEGRATION.md](../internal/SUPABASE_AUTH_INTEGRATION.md) - Supabase Auth 統合実装プラン
- [FRONTEND_AUTH_ISSUES.md](../internal/FRONTEND_AUTH_ISSUES.md) - フロントエンド認証修正完了レポート

---

## ✅ 実装チェックリスト

### Phase 1: 依存関係
- [ ] `npm install @react-oauth/google` 実行
- [ ] `VITE_GOOGLE_CLIENT_ID` 環境変数確認

### Phase 2: AppProvider
- [ ] `GoogleOAuthProvider` import 追加
- [ ] `<GoogleOAuthProvider clientId={...}>` で全体をラップ
- [ ] TypeScript エラーなし

### Phase 3: LoginPage
- [ ] `useAuth` フックに `loginWithGoogle` メソッド追加
- [ ] `LoginPage` に `<GoogleLogin>` コンポーネント追加
- [ ] `handleGoogleSuccess` で `loginWithGoogle` 呼び出し
- [ ] TypeScript エラーなし

### Phase 4: 動作確認
- [ ] Google OAuth ボタンが表示される
- [ ] ポップアップで Google OAuth 画面が開く
- [ ] ログイン成功でダッシュボードへリダイレクト
- [ ] Supabase セッション確認（JWT 取得）
- [ ] PDF アップロード・スライド一覧取得が正常動作
- [ ] ログアウト正常動作

---

## 🎯 成功基準

### 機能
- ✅ Google 公式 OAuth UI が表示される
- ✅ ポップアップでログイン可能
- ✅ Supabase セッション作成成功
- ✅ JWT 自動送信（既存実装を維持）
- ✅ セッション永続化（リロード後も維持）

### UX
- ✅ Google ブランド信頼性（公式 UI）
- ✅ ポップアップ型（リダイレクトなし）
- ✅ エラーハンドリング（詳細ログ）

### セキュリティ
- ✅ JWT 検証（Supabase）
- ✅ RLS（Row Level Security）対応
- ✅ リフレッシュトークン対応

### コード品質
- ✅ TypeScript エラーなし
- ✅ 既存実装を破壊しない
- ✅ コメント・ドキュメント完備

---

## 🚀 実装開始コマンド

```bash
# Phase 1: 依存関係
cd frontend
npm install @react-oauth/google

# Phase 2-3: コード修正
# - frontend/src/app/provider.tsx
# - frontend/src/features/auth/hooks/useAuth.ts
# - frontend/src/features/auth/LoginPage.tsx

# Phase 4: 動作確認
npm run dev
# → http://localhost:5173/login にアクセス
```

---

**最終更新**: 2025-11-13
**ステータス**: 設計完了 → 実装準備完了
