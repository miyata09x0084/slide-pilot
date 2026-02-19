/**
 * dashboardLoader のテスト
 * 非ブロッキングprefetch（fire-and-forget）+ 認証ガードの動作を検証
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

// auth-session をモック
let mockToken: string | null = null;
vi.mock('@/lib/auth-session', () => ({
  getCachedAccessToken: () => mockToken,
}));

import * as getSlidesModule from '../api/get-slides';

describe('dashboardLoader (non-blocking prefetch)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    mockToken = null;
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  it('同期的にnullを返す（ルート遷移をブロックしない）', () => {
    mockToken = 'valid-token';
    vi.spyOn(getSlidesModule, 'getSlides').mockResolvedValueOnce({
      slides: [],
      message: '',
    });

    const loader = createDashboardLoader(queryClient);
    const result = loader();

    expect(result).toBeNull();
  });

  it('認証トークンがある場合、prefetchQueryを発火する', () => {
    mockToken = 'valid-token';
    const prefetchSpy = vi.spyOn(queryClient, 'prefetchQuery');
    vi.spyOn(getSlidesModule, 'getSlides').mockResolvedValueOnce({
      slides: [],
      message: '0件',
    });

    const loader = createDashboardLoader(queryClient);
    loader();

    expect(prefetchSpy).toHaveBeenCalledWith({
      queryKey: ['slides', 20],
      queryFn: expect.any(Function),
    });
  });

  it('認証トークンがない場合、prefetchQueryを発火しない', () => {
    mockToken = null;
    const prefetchSpy = vi.spyOn(queryClient, 'prefetchQuery');

    const loader = createDashboardLoader(queryClient);
    const result = loader();

    expect(result).toBeNull();
    expect(prefetchSpy).not.toHaveBeenCalled();
  });

  it('prefetchQueryの結果がキャッシュに反映される', async () => {
    mockToken = 'valid-token';
    const mockData = {
      slides: [{ id: '1', title: 'Test', created_at: '2025-11-06T00:00:00Z' }],
      message: '1件のスライドを取得しました',
    };
    vi.spyOn(getSlidesModule, 'getSlides').mockResolvedValueOnce(mockData);

    const loader = createDashboardLoader(queryClient);
    loader();

    await vi.waitFor(() => {
      const cachedData = queryClient.getQueryData(['slides', 20]);
      expect(cachedData).toEqual(mockData);
    });
  });

  it('prefetchQuery失敗時もloaderはnullを返す（エラーを握りつぶす）', () => {
    mockToken = 'valid-token';
    vi.spyOn(getSlidesModule, 'getSlides').mockRejectedValueOnce(
      new Error('Network error')
    );

    const loader = createDashboardLoader(queryClient);
    const result = loader();

    expect(result).toBeNull();
  });
});
