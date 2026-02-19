/**
 * auth-session.ts のテスト
 * セッションキャッシュの初期化、トークン取得、クリーンアップを検証
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Supabaseモック
const mockUnsubscribe = vi.fn();
let authStateCallback: ((event: string, session: any) => void) | null = null;
let mockSession: any = null;

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      onAuthStateChange: vi.fn((callback: any) => {
        authStateCallback = callback;
        // Supabase v2.39+: INITIAL_SESSIONを同期的に発火
        if (mockSession !== undefined) {
          callback('INITIAL_SESSION', mockSession);
        }
        return {
          data: {
            subscription: { unsubscribe: mockUnsubscribe },
          },
        };
      }),
      getSession: vi.fn(() =>
        Promise.resolve({
          data: { session: mockSession },
        })
      ),
    },
  },
}));

// テスト対象は各テストで動的にimportし直す
let initAuthSessionCache: typeof import('../auth-session').initAuthSessionCache;
let destroyAuthSessionCache: typeof import('../auth-session').destroyAuthSessionCache;
let getCachedAccessToken: typeof import('../auth-session').getCachedAccessToken;

// 有効期限付きのJWTを生成するヘルパー
function createMockJwt(expInSeconds: number): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(
    JSON.stringify({
      sub: 'user-123',
      exp: Math.floor(Date.now() / 1000) + expInSeconds,
    })
  );
  return `${header}.${payload}.fake-signature`;
}

describe('auth-session', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    authStateCallback = null;
    mockSession = null;

    // モジュールキャッシュをリセットして状態をクリア
    vi.resetModules();
    const mod = await import('../auth-session');
    initAuthSessionCache = mod.initAuthSessionCache;
    destroyAuthSessionCache = mod.destroyAuthSessionCache;
    getCachedAccessToken = mod.getCachedAccessToken;
  });

  afterEach(() => {
    destroyAuthSessionCache();
  });

  describe('初期化前', () => {
    it('initAuthSessionCache()呼び出し前はnullを返す', () => {
      expect(getCachedAccessToken()).toBeNull();
    });
  });

  describe('initAuthSessionCache', () => {
    it('onAuthStateChangeのINITIAL_SESSIONでトークンがセットされる', () => {
      const token = createMockJwt(3600);
      mockSession = { access_token: token };

      initAuthSessionCache();

      // INITIAL_SESSIONが同期的に発火するため即座に取得可能
      expect(getCachedAccessToken()).toBe(token);
    });

    it('セッションがnullの場合はトークンがnullのまま', () => {
      mockSession = null;

      initAuthSessionCache();

      expect(getCachedAccessToken()).toBeNull();
    });

    it('2回呼び出しても冪等（リスナーが重複登録されない）', async () => {
      const { supabase } = await import('@/lib/supabase');
      mockSession = { access_token: createMockJwt(3600) };

      initAuthSessionCache();
      initAuthSessionCache();

      expect(supabase.auth.onAuthStateChange).toHaveBeenCalledTimes(1);
    });
  });

  describe('トークン更新', () => {
    it('onAuthStateChangeで新しいトークンに更新される', () => {
      const oldToken = createMockJwt(3600);
      mockSession = { access_token: oldToken };

      initAuthSessionCache();
      expect(getCachedAccessToken()).toBe(oldToken);

      // トークンリフレッシュをシミュレート
      const newToken = createMockJwt(7200);
      authStateCallback!('TOKEN_REFRESHED', { access_token: newToken });

      expect(getCachedAccessToken()).toBe(newToken);
    });

    it('ログアウト時にトークンがクリアされる', () => {
      mockSession = { access_token: createMockJwt(3600) };

      initAuthSessionCache();
      expect(getCachedAccessToken()).not.toBeNull();

      // ログアウトをシミュレート
      authStateCallback!('SIGNED_OUT', null);

      expect(getCachedAccessToken()).toBeNull();
    });
  });

  describe('トークン期限チェック', () => {
    it('有効期限が十分にあるトークンはそのまま返す', async () => {
      const { supabase } = await import('@/lib/supabase');
      const token = createMockJwt(3600); // 1時間後に期限切れ
      mockSession = { access_token: token };

      initAuthSessionCache();

      const result = getCachedAccessToken();
      expect(result).toBe(token);
      // getSession()は初期化時の1回のみ（リフレッシュは不要）
      expect(supabase.auth.getSession).toHaveBeenCalledTimes(1);
    });

    it('期限切れ間近のトークンはバックグラウンドリフレッシュを発火する', async () => {
      const { supabase } = await import('@/lib/supabase');
      const token = createMockJwt(30); // 30秒後に期限切れ（閾値60秒未満）
      mockSession = { access_token: token };

      initAuthSessionCache();
      vi.clearAllMocks(); // 初期化呼び出しをリセット

      const result = getCachedAccessToken();
      expect(result).toBe(token); // 現在のトークンは返す
      expect(supabase.auth.getSession).toHaveBeenCalledTimes(1); // リフレッシュ発火
    });
  });

  describe('destroyAuthSessionCache', () => {
    it('クリーンアップでリスナーが解除されトークンがクリアされる', () => {
      mockSession = { access_token: createMockJwt(3600) };

      initAuthSessionCache();
      expect(getCachedAccessToken()).not.toBeNull();

      destroyAuthSessionCache();

      expect(mockUnsubscribe).toHaveBeenCalledTimes(1);
      expect(getCachedAccessToken()).toBeNull();
    });

    it('destroy後に再度initAuthSessionCacheが呼べる', () => {
      mockSession = { access_token: createMockJwt(3600) };

      initAuthSessionCache();
      destroyAuthSessionCache();

      mockSession = { access_token: createMockJwt(7200) };
      initAuthSessionCache();

      expect(getCachedAccessToken()).not.toBeNull();
    });
  });
});
