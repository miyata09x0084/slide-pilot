/**
 * dashboardLoader のテスト
 * React Router Loader with React Query prefetch
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient } from '@tanstack/react-query';
import { createDashboardLoader } from '../loaders/dashboardLoader';

// api-client をモック
vi.mock('@/lib/api-client', () => ({
  api: {
    get: vi.fn(),
  },
}));

// env をモック
vi.mock('@/config/env', () => ({
  env: {
    API_URL: 'http://localhost:8001/api',
  },
}));

import * as getSlidesModule from '../api/get-slides';

// localStorage をモック
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

describe('dashboardLoader with prefetch', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // テスト時はリトライしない
        },
      },
    });
  });

  describe('未ログイン状態', () => {
    it('localStorage に user がない場合、nullを返す', async () => {
      const loader = createDashboardLoader(queryClient);
      const result = await loader();

      expect(result).toBeNull();
    });
  });

  describe('ログイン状態', () => {
    const testUser = {
      name: 'Test User',
      email: 'test@example.com',
      picture: 'https://example.com/avatar.jpg',
    };

    beforeEach(() => {
      localStorage.setItem('user', JSON.stringify(testUser));
    });

    it('正常にスライド一覧をReact Queryキャッシュにプリフェッチできる', async () => {
      const mockSlides = [
        {
          id: '1',
          title: 'スライド1',
          created_at: '2025-11-06T00:00:00Z',
        },
        {
          id: '2',
          title: 'スライド2',
          created_at: '2025-11-06T01:00:00Z',
        },
      ];

      // getSlides関数をモック
      vi.spyOn(getSlidesModule, 'getSlides').mockResolvedValueOnce({
        slides: mockSlides,
      });

      const loader = createDashboardLoader(queryClient);
      const result = await loader();

      // prefetchQueryが正しく呼び出されたことを確認
      expect(getSlidesModule.getSlides).toHaveBeenCalledTimes(1);
      expect(getSlidesModule.getSlides).toHaveBeenCalledWith({
        user_id: 'test@example.com',
        limit: 20,
      });

      // Loaderからはnullが返る（データはキャッシュに保存）
      expect(result).toBeNull();

      // キャッシュにデータが保存されていることを確認
      const cachedData = queryClient.getQueryData(['slides', 'test@example.com', 20]);
      expect(cachedData).toEqual({ slides: mockSlides });
    });

    it('スライドが0件の場合もキャッシュに保存される', async () => {
      vi.spyOn(getSlidesModule, 'getSlides').mockResolvedValueOnce({
        slides: [],
      });

      const loader = createDashboardLoader(queryClient);
      await loader();

      const cachedData = queryClient.getQueryData(['slides', 'test@example.com', 20]);
      expect(cachedData).toEqual({ slides: [] });
    });
  });

  describe('エラーハンドリング', () => {
    const testUser = {
      name: 'Test User',
      email: 'test@example.com',
      picture: 'https://example.com/avatar.jpg',
    };

    beforeEach(() => {
      localStorage.setItem('user', JSON.stringify(testUser));
    });

    it('API呼び出しが失敗した場合、nullを返す', async () => {
      vi.spyOn(getSlidesModule, 'getSlides').mockRejectedValueOnce(
        new Error('Network error')
      );

      const loader = createDashboardLoader(queryClient);
      const result = await loader();

      // prefetchQueryはエラーを無視するため、nullが返る
      expect(result).toBeNull();

      // キャッシュにはデータが保存されていないことを確認
      const cachedData = queryClient.getQueryData(['slides', 'test@example.com', 20]);
      expect(cachedData).toBeUndefined();
    });

    it('localStorage のパースが失敗した場合、nullを返す', async () => {
      localStorage.setItem('user', '{invalid json}');

      const loader = createDashboardLoader(queryClient);
      const result = await loader();

      expect(result).toBeNull();
      expect(getSlidesModule.getSlides).not.toHaveBeenCalled();
    });
  });

  describe('QueryClient統合', () => {
    it('prefetchQuery経由でキャッシュにデータが保存される', async () => {
      const testUser = {
        email: 'cache@example.com',
      };
      localStorage.setItem('user', JSON.stringify(testUser));

      const mockData = { slides: [{ id: '1', title: 'Test', created_at: '2025-11-06T00:00:00Z' }] };
      vi.spyOn(getSlidesModule, 'getSlides').mockResolvedValueOnce(mockData);

      const prefetchSpy = vi.spyOn(queryClient, 'prefetchQuery');

      const loader = createDashboardLoader(queryClient);
      await loader();

      expect(prefetchSpy).toHaveBeenCalledWith({
        queryKey: ['slides', 'cache@example.com', 20],
        queryFn: expect.any(Function),
      });

      // キャッシュからデータを取得できることを確認
      const cachedData = queryClient.getQueryData(['slides', 'cache@example.com', 20]);
      expect(cachedData).toEqual(mockData);
    });
  });
});
