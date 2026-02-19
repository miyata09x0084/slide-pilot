/**
 * API Client Configuration
 * Centralized Axios instance with interceptors for authentication and error handling
 *
 * Issue: Supabase Auth統合（JWT自動送信）
 * Perf: セッションキャッシュを使用し、リクエストごとの非同期getSession()を排除
 */

import axios from 'axios';
import { env } from '@/config/env';
import { getCachedAccessToken } from './auth-session';

// Create Axios instance
export const api = axios.create({
  baseURL: env.API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
});

// Request interceptor - Add JWT authentication headers (synchronous)
api.interceptors.request.use(
  (config) => {
    // メモリキャッシュから同期的にトークン取得（非同期getSession不要）
    const accessToken = getCachedAccessToken();

    if (accessToken) {
      config.headers['Authorization'] = `Bearer ${accessToken}`;
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
  (error) => {
    // Handle specific error codes
    if (error.response) {
      const { status } = error.response;

      // 401 Unauthorized - Redirect to login
      if (status === 401) {
        localStorage.removeItem('user');
        window.location.href = '/login';
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
