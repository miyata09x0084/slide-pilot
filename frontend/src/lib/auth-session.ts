/**
 * Auth Session Cache
 * Supabaseセッションのアクセストークンをメモリにキャッシュし、
 * APIリクエスト時の非同期getSession()呼び出しを排除する
 *
 * 設計:
 * - onAuthStateChangeを最初に登録（Supabase v2.39+ではINITIAL_SESSIONが
 *   同期的に発火するため、登録直後にキャッシュが利用可能になる）
 * - getSession()はフォールバックとして非同期で呼び出す
 * - AxiosインターセプターはgetCachedAccessToken()で同期的にトークン取得
 * - トークン期限切れ（残り60秒以内）の場合はバックグラウンドでリフレッシュを発火
 */

import { supabase } from './supabase';

let cachedAccessToken: string | null = null;
let initialized = false;
let subscription: { unsubscribe: () => void } | null = null;

/**
 * セッションキャッシュを初期化
 * アプリ起動時に1回だけ呼び出す（main.tsx）
 *
 * 重要: onAuthStateChangeをgetSession()より先に登録すること。
 * Supabase v2.39+ではINITIAL_SESSIONイベントが同期的に発火するため、
 * この関数の実行完了時点でcachedAccessTokenが利用可能になる。
 */
export function initAuthSessionCache(): void {
  if (initialized) return;
  initialized = true;

  // セッション変更を監視（ログイン/ログアウト/トークンリフレッシュ）
  // INITIAL_SESSIONイベントが同期的に発火し、キャッシュを即座にセットする
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
}

/**
 * セッションキャッシュを破棄（HMR・テスト用）
 */
export function destroyAuthSessionCache(): void {
  subscription?.unsubscribe();
  subscription = null;
  cachedAccessToken = null;
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
      // onAuthStateChangeリスナーがトークン更新時にキャッシュを自動更新する
      supabase.auth.getSession();
    }
  } catch {
    // JWTパース失敗時はトークンをそのまま返す
  }

  return cachedAccessToken;
}
