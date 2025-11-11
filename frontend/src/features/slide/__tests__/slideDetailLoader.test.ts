/**
 * slideDetailLoader のテスト
 * React Router Loader with React Query prefetch
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient } from '@tanstack/react-query';
import { createSlideDetailLoader } from '../loaders/slideDetailLoader';

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

import * as getSlideDetailModule from '../api/get-slide-detail';

describe('slideDetailLoader with prefetch', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // テスト時はリトライしない
        },
      },
    });
  });

  describe('正常系', () => {
    it('正常にスライド詳細をReact Queryキャッシュにプリフェッチできる', async () => {
      const mockSlide = {
        id: 'slide-123',
        title: 'テストスライド',
        topic: 'テストスライド',
        created_at: '2025-11-06T00:00:00Z',
        pdf_url: 'https://example.com/slide.pdf',
      };

      // getSlideDetail関数をモック
      vi.spyOn(getSlideDetailModule, 'getSlideDetail').mockResolvedValueOnce(mockSlide);

      const loader = createSlideDetailLoader(queryClient);
      const result = await loader({
        params: { slideId: 'slide-123' },
      } as any);

      // prefetchQueryが正しく呼び出されたことを確認
      expect(getSlideDetailModule.getSlideDetail).toHaveBeenCalledTimes(1);
      expect(getSlideDetailModule.getSlideDetail).toHaveBeenCalledWith('slide-123');

      // Loaderからはnullが返る（データはキャッシュに保存）
      expect(result).toBeNull();

      // キャッシュにデータが保存されていることを確認
      const cachedData = queryClient.getQueryData(['slide', 'slide-123']);
      expect(cachedData).toEqual(mockSlide);
    });

    it('pdf_url が存在しない場合も正常に処理できる', async () => {
      const mockSlide = {
        id: 'slide-456',
        title: 'PDFなしスライド',
        topic: 'PDFなしスライド',
        created_at: '2025-11-06T01:00:00Z',
      };

      vi.spyOn(getSlideDetailModule, 'getSlideDetail').mockResolvedValueOnce(mockSlide);

      const loader = createSlideDetailLoader(queryClient);
      await loader({
        params: { slideId: 'slide-456' },
      } as any);

      const cachedData = queryClient.getQueryData(['slide', 'slide-456']) as any;
      expect(cachedData.pdf_url).toBeUndefined();
      expect(cachedData.id).toBe('slide-456');
    });

    it('markdown が含まれる場合も正常に処理できる', async () => {
      const mockSlide = {
        id: 'slide-789',
        title: 'Markdownスライド',
        topic: 'Markdownスライド',
        created_at: '2025-11-06T02:00:00Z',
        markdown: '# タイトル\n\nコンテンツ',
      };

      vi.spyOn(getSlideDetailModule, 'getSlideDetail').mockResolvedValueOnce(mockSlide);

      const loader = createSlideDetailLoader(queryClient);
      await loader({
        params: { slideId: 'slide-789' },
      } as any);

      const cachedData = queryClient.getQueryData(['slide', 'slide-789']) as any;
      expect(cachedData.markdown).toBe('# タイトル\n\nコンテンツ');
    });
  });

  describe('異常系', () => {
    it('slideId が未指定の場合、エラーをthrowする', async () => {
      const loader = createSlideDetailLoader(queryClient);

      await expect(
        loader({ params: {} } as any)
      ).rejects.toThrow('Slide ID is required');

      expect(getSlideDetailModule.getSlideDetail).not.toHaveBeenCalled();
    });

    it('API呼び出しが失敗した場合、nullを返す', async () => {
      vi.spyOn(getSlideDetailModule, 'getSlideDetail').mockRejectedValueOnce(
        new Error('Not Found')
      );

      const loader = createSlideDetailLoader(queryClient);

      // prefetchQueryはエラーを無視するため、nullが返る
      const result = await loader({ params: { slideId: 'slide-999' } } as any);
      expect(result).toBeNull();

      // キャッシュにはデータが保存されていないことを確認
      const cachedData = queryClient.getQueryData(['slide', 'slide-999']);
      expect(cachedData).toBeUndefined();
    });

    it('ネットワークエラーの場合、nullを返す', async () => {
      vi.spyOn(getSlideDetailModule, 'getSlideDetail').mockRejectedValueOnce(
        new Error('Network error')
      );

      const loader = createSlideDetailLoader(queryClient);

      // prefetchQueryはエラーを無視するため、nullが返る
      const result = await loader({ params: { slideId: 'slide-999' } } as any);
      expect(result).toBeNull();

      // キャッシュにはデータが保存されていないことを確認
      const cachedData = queryClient.getQueryData(['slide', 'slide-999']);
      expect(cachedData).toBeUndefined();
    });
  });

  describe('QueryClient統合', () => {
    it('prefetchQuery経由でキャッシュにデータが保存される', async () => {
      const mockSlide = {
        id: 'cache-test',
        title: 'キャッシュテスト',
        topic: 'キャッシュテスト',
        created_at: '2025-11-06T00:00:00Z',
      };

      vi.spyOn(getSlideDetailModule, 'getSlideDetail').mockResolvedValueOnce(mockSlide);

      const prefetchSpy = vi.spyOn(queryClient, 'prefetchQuery');

      const loader = createSlideDetailLoader(queryClient);
      await loader({ params: { slideId: 'cache-test' } } as any);

      expect(prefetchSpy).toHaveBeenCalledWith({
        queryKey: ['slide', 'cache-test'],
        queryFn: expect.any(Function),
      });

      // キャッシュからデータを取得できることを確認
      const cachedData = queryClient.getQueryData(['slide', 'cache-test']);
      expect(cachedData).toEqual(mockSlide);
    });

    it('異なるslideIdで異なるキャッシュキーが使用される', async () => {
      const mockSlide1 = {
        id: 'slide-1',
        title: 'スライド1',
        topic: 'スライド1',
        created_at: '2025-11-06T00:00:00Z',
      };
      const mockSlide2 = {
        id: 'slide-2',
        title: 'スライド2',
        topic: 'スライド2',
        created_at: '2025-11-06T01:00:00Z',
      };

      const getSpy = vi
        .spyOn(getSlideDetailModule, 'getSlideDetail')
        .mockResolvedValueOnce(mockSlide1)
        .mockResolvedValueOnce(mockSlide2);

      const loader = createSlideDetailLoader(queryClient);

      await loader({ params: { slideId: 'slide-1' } } as any);
      await loader({ params: { slideId: 'slide-2' } } as any);

      expect(getSpy).toHaveBeenCalledTimes(2);

      // 両方のデータがそれぞれ別のキーでキャッシュされていることを確認
      const cachedData1 = queryClient.getQueryData(['slide', 'slide-1']);
      const cachedData2 = queryClient.getQueryData(['slide', 'slide-2']);

      expect(cachedData1).toEqual(mockSlide1);
      expect(cachedData2).toEqual(mockSlide2);
    });
  });
});
