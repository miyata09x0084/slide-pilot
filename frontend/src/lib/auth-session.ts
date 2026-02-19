/**
 * Auth Session Cache
 * Supabaseセッションのアクセストークンをメモリにキャッシュし、
 * APIリクエスト時の非同期getSession()呼び出しを排除する
 *
 * 設計:
 * - Supabase SDKを動的importで遅延読み込み（初期バンドルに含めない）
 * - import完了後にonAuthStateChangeを登録しトークンをキャッシュ
 * - AxiosインターセプターはgetCachedAccessToken()で同期的にトークン取得
 * - Supabase SDK読み込み完了前はnullを返す（AuthGuardがスピナーを表示）
 * - トークン期限切れ（残り60秒以内）の場合はバックグラウンドでリフレッシュを発火
 */

import type { SupabaseClient } from '@supabase/supabase-js';

let cachedAccessToken: string | null = null;
let initialized = false;
let subscription: { unsubscribe: () => void } | null = null;
let supabaseRef: SupabaseClient | null = null;

/**
 * セッションキャッシュを初期化
 * アプリ起動時に1回だけ呼び出す（main.tsx）
 *
 * Supabase SDKを動的importで読み込み、初期バンドルから除外する。
 * import完了後にonAuthStateChangeを登録し、トークンをキャッシュする。
 */
export function initAuthSessionCache(): void {
  if (initialized) return;
  initialized = true;

  // Supabase SDKを動的import（別チャンクとして遅延読み込み）
  import('./supabase').then(({ supabase }) => {
    supabaseRef = supabase;

    // セッション変更を監視（ログイン/ログアウト/トークンリフレッシュ）
    const { data: { subscription: sub } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        cachedAccessToken = session?.access_token ?? null;
      }
    );
    subscription = sub;

    // フォールバック: onAuthStateChangeがINITIAL_SESSIONを発火しない場合に備える
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!cachedAccessToken && session?.access_token) {
        cachedAccessToken = session.access_token;
      }
    });
  });
}

/**
 * セッションキャッシュを破棄（HMR・テスト用）
 */
export function destroyAuthSessionCache(): void {
  subscription?.unsubscribe();
  subscription = null;
  cachedAccessToken = null;
  supabaseRef = null;
  initialized = false;
}

// トークン期限チェック用の閾値（秒）
const TOKEN_EXPIRY_BUFFER_SEC = 60;

/**
 * キャッシュされたアクセストークンを同期的に取得
 * Axiosインターセプター・SSEリクエストから呼び出す
 *
 * トークンの有効期限が60秒以内の場合、バックグラウンドで
 * セッションリフレッシュを発火する（onAuthStateChangeで自動更新）
 */
export function getCachedAccessToken(): string | null {
  if (!cachedAccessToken) return null;

  try {
    const payload = JSON.parse(atob(cachedAccessToken.split('.')[1]));
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp - now < TOKEN_EXPIRY_BUFFER_SEC) {
      // 期限切れ間近: バックグラウンドでリフレッシュ発火
      supabaseRef?.auth.getSession();
    }
  } catch {
    // JWTパース失敗時はトークンをそのまま返す
  }

  return cachedAccessToken;
}
