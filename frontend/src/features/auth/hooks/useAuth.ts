/**
 * useAuth Hook
 * Supabase Auth で Google OAuth 認証状態を管理
 *
 * Issue: Supabase Auth統合
 */

import { useState, useEffect } from 'react';
import type { UserInfo } from '@/types';
import { supabase } from '@/lib/supabase';

export function useAuth() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  // セッション復元（Supabase が自動管理）
  useEffect(() => {
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

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const login = async () => {
    // Supabase Auth で Google OAuth フロー開始（リダイレクト型）
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/`,
      },
    });
    if (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const loginWithGoogle = async (googleCredential: string) => {
    setAuthError(null);
    try {
      // Google JWT を Supabase に渡して検証
      const { error } = await supabase.auth.signInWithIdToken({
        provider: 'google',
        token: googleCredential,
      });

      if (error) {
        console.error('[useAuth] Supabase Auth failed:', error);
        setAuthError('ログインに失敗しました。しばらくしてから再度お試しください。');
        throw error;
      }
    } catch (e) {
      console.error('[useAuth] Login error:', e);
      if (!authError) {
        setAuthError('認証サービスに接続できません。ネットワーク接続を確認してください。');
      }
      throw e;
    }
  };

  const clearAuthError = () => {
    setAuthError(null);
  };

  const logout = async () => {
    await supabase.auth.signOut();
    setUser(null);
  };

  return {
    user,
    loading,
    authError,
    login, // リダイレクト型（フォールバック用）
    loginWithGoogle, // Google JWT 検証型（メイン）
    logout,
    clearAuthError,
    isAuthenticated: !!user,
  };
}
