/**
 * useAuth Hook
 * Google OAuth認証状態を管理
 */

import { useState, useEffect } from 'react';

export interface UserInfo {
  name: string;
  email: string;
  picture: string;
}

export function useAuth() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  // ページロード時にlocalStorageから復元
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (err) {
        console.error('Failed to parse user data:', err);
        localStorage.removeItem('user');
      }
    }
    setLoading(false);
  }, []);

  const login = (userInfo: UserInfo) => {
    setUser(userInfo);
    localStorage.setItem('user', JSON.stringify(userInfo));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  return {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
  };
}
