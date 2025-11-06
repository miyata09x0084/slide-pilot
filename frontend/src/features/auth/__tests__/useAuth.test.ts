/**
 * useAuth hookのテスト
 * Phase 2で移行した認証フックの動作確認
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAuth } from '../hooks/useAuth';

describe('useAuth hook', () => {
  beforeEach(() => {
    // localStorageをクリア
    localStorage.clear();
  });

  it('should initialize with unauthenticated state', () => {
    const { result } = renderHook(() => useAuth());

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('should login user and persist to localStorage', () => {
    const { result } = renderHook(() => useAuth());

    const testUser = {
      name: 'Test User',
      email: 'test@example.com',
      picture: 'https://example.com/avatar.jpg',
    };

    act(() => {
      result.current.login(testUser);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(testUser);

    // localStorageに保存されているか確認
    const stored = localStorage.getItem('user');
    expect(stored).toBeTruthy();
    expect(JSON.parse(stored!)).toEqual(testUser);
  });

  it('should logout user and clear localStorage', () => {
    const { result } = renderHook(() => useAuth());

    const testUser = {
      name: 'Test User',
      email: 'test@example.com',
      picture: 'https://example.com/avatar.jpg',
    };

    // ログイン
    act(() => {
      result.current.login(testUser);
    });

    expect(result.current.isAuthenticated).toBe(true);

    // ログアウト
    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
  });

  it('should restore user from localStorage on mount', () => {
    const testUser = {
      name: 'Test User',
      email: 'test@example.com',
      picture: 'https://example.com/avatar.jpg',
    };

    // 事前にlocalStorageにユーザー情報をセット
    localStorage.setItem('user', JSON.stringify(testUser));

    const { result } = renderHook(() => useAuth());

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(testUser);
  });
});
