/**
 * API Client Configuration
 * Centralized Axios instance with interceptors for authentication and error handling
 *
 * Issue: Supabase Auth統合（JWT自動送信）
 */

import axios from 'axios';
import { env } from '@/config/env';
import { supabase } from './supabase';

// Create Axios instance
export const api = axios.create({
  baseURL: env.API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
});

// Request interceptor - Add JWT authentication headers
api.interceptors.request.use(
  async (config) => {
    // Supabase Session から JWT 取得
    const { data: { session } } = await supabase.auth.getSession();

    // JWT が存在する場合は Authorization ヘッダーに追加
    if (session?.access_token) {
      config.headers['Authorization'] = `Bearer ${session.access_token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors globally
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  async (error) => {
    // Handle specific error codes
    if (error.response) {
      const { status } = error.response;

      // 401 Unauthorized - ログアウト処理（強制リダイレクトしない）
      if (status === 401) {
        console.error('[API Client] 401 Unauthorized - Signing out from Supabase');

        // Supabaseからログアウト（これによりonAuthStateChangeが発火）
        await supabase.auth.signOut();

        // ローカルストレージのクリーンアップ
        localStorage.removeItem('user');

        // window.location.href = '/login' は削除
        // onAuthStateChange → useAuth → AuthGuard が自動的に /login へリダイレクト
      }

      // Log other errors
      console.error('API Error:', {
        status,
        message: error.response.data?.message || error.message,
        url: error.config?.url,
      });
    } else if (error.request) {
      console.error('Network Error: No response received', error.request);
    } else {
      console.error('Request Error:', error.message);
    }

    return Promise.reject(error);
  }
);
