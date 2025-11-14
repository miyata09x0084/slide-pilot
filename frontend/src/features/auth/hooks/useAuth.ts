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
    console.log('[useAuth] Initializing useEffect...');

    // 初回セッション取得
    supabase.auth.getSession().then(({ data: { session } }) => {
      console.log('[useAuth] Initial getSession result:', {
        hasSession: !!session,
        userId: session?.user?.id,
        email: session?.user?.email,
        timestamp: new Date().toISOString()
      });

      if (session?.user) {
        setUser({
          name: session.user.user_metadata.full_name || session.user.email || '',
          email: session.user.email || '',
          picture: session.user.user_metadata.avatar_url || '',
        });
        console.log('[useAuth] User set from initial session');
      }
      setLoading(false);
      console.log('[useAuth] Loading set to false, isAuthenticated:', !!session);
    });

    // セッション変更を監視（ログイン/ログアウト時に自動更新）
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        console.log('[useAuth] onAuthStateChange fired:', {
          event,
          hasSession: !!session,
          userId: session?.user?.id,
          email: session?.user?.email,
          timestamp: new Date().toISOString()
        });

        if (session?.user) {
          setUser({
            name: session.user.user_metadata.full_name || session.user.email || '',
            email: session.user.email || '',
            picture: session.user.user_metadata.avatar_url || '',
          });
          console.log('[useAuth] User set from onAuthStateChange, isAuthenticated: true');
        } else {
          setUser(null);
          console.log('[useAuth] User cleared from onAuthStateChange, isAuthenticated: false');
        }
      }
    );

    return () => {
      console.log('[useAuth] Cleanup: unsubscribing from onAuthStateChange');
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
    console.log('[useAuth] loginWithGoogle called');

    // Google JWT を Supabase に渡して検証
    const { data, error } = await supabase.auth.signInWithIdToken({
      provider: 'google',
      token: googleCredential,
    });

    if (error) {
      console.error('[useAuth] Supabase Auth failed:', error);
      throw error;
    }

    console.log('[useAuth] Supabase Auth success:', {
      userId: data.user?.id,
      email: data.user?.email,
      hasSession: !!data.session
    });
  };

  const logout = async () => {
    await supabase.auth.signOut();
    setUser(null);
  };

  return {
    user,
    loading,
    login, // リダイレクト型（フォールバック用）
    loginWithGoogle, // Google JWT 検証型（メイン）
    logout,
    isAuthenticated: !!user,
  };
}
