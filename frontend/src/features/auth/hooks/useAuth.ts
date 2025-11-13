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

    return () => subscription.unsubscribe();
  }, []);

  const login = async () => {
    // Supabase Auth で Google OAuth フロー開始
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

  const logout = async () => {
    await supabase.auth.signOut();
    setUser(null);
  };

  return {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
  };
}
