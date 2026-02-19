/**
 * useAuth Hook
 * Supabase Auth で Google OAuth 認証状態を管理
 *
 * Supabase SDKを動的importで遅延読み込み（初期バンドルから除外）
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import type { UserInfo } from '@/types';
import type { SupabaseClient } from '@supabase/supabase-js';

export function useAuth() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const supabaseRef = useRef<SupabaseClient | null>(null);

  // セッション復元（Supabase SDKを動的importで読み込み）
  useEffect(() => {
    let unsubscribe: (() => void) | null = null;

    import('@/lib/supabase').then(({ supabase }) => {
      supabaseRef.current = supabase;

      // 初回セッション取得
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (session?.user) {
          setUser({
            name: session.user.user_metadata.full_name || session.user.email || '',
            email: session.user.email || '',
            picture: session.user.user_metadata.avatar_url || '',
          });
        }
        setLoading(false);
      });

      // セッション変更を監視（ログイン/ログアウト時に自動更新）
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        (_event, session) => {
          if (session?.user) {
            setUser({
              name: session.user.user_metadata.full_name || session.user.email || '',
              email: session.user.email || '',
              picture: session.user.user_metadata.avatar_url || '',
            });
          } else {
            setUser(null);
          }
        }
      );
      unsubscribe = () => subscription.unsubscribe();
    });

    return () => {
      unsubscribe?.();
    };
  }, []);

  const login = useCallback(async () => {
    const client = supabaseRef.current;
    if (!client) return;
    const { error } = await client.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/`,
      },
    });
    if (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }, []);

  const loginWithGoogle = useCallback(async (googleCredential: string) => {
    const client = supabaseRef.current;
    if (!client) return;
    const { error } = await client.auth.signInWithIdToken({
      provider: 'google',
      token: googleCredential,
    });
    if (error) {
      console.error('[useAuth] Supabase Auth failed:', error);
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    const client = supabaseRef.current;
    if (!client) return;
    await client.auth.signOut();
    setUser(null);
  }, []);

  return {
    user,
    loading,
    login,
    loginWithGoogle,
    logout,
    isAuthenticated: !!user,
  };
}
