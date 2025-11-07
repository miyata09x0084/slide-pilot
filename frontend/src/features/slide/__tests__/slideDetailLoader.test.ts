/**
 * slideDetailLoader のテスト
 * React Query統合: キャッシュへの事前取得のみ行う
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { slideDetailLoader } from '../loaders/slideDetailLoader';
import { queryClient } from '@/lib/react-query';

// queryClient.ensureQueryData をモック
vi.mock('@/lib/react-query', () => ({
  queryClient: {
    ensureQueryData: vi.fn(),
  },
}));

describe('slideDetailLoader', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('正常系', () => {
    it('React QueryのensureQueryDataを呼び出す', async () => {
      const result = await slideDetailLoader({
        params: { slideId: 'slide-123' },
      } as any);

      // ensureQueryDataが正しく呼び出されたか確認
      expect(queryClient.ensureQueryData).toHaveBeenCalledTimes(1);
      expect(queryClient.ensureQueryData).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ['slide', 'detail', 'slide-123'],
        })
      );

      // loaderはnullを返す（データはReact Queryから取得）
      expect(result).toBeNull();
    });

    it('正しいslideIdでクエリキーを生成する', async () => {
      await slideDetailLoader({
        params: { slideId: 'test-slide-456' },
      } as any);

      expect(queryClient.ensureQueryData).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ['slide', 'detail', 'test-slide-456'],
        })
      );
    });
  });

  describe('異常系', () => {
    it('slideId が未指定の場合、エラーをthrowする', async () => {
      await expect(
        slideDetailLoader({ params: {} } as any)
      ).rejects.toThrow('Slide ID is required');

      // ensureQueryDataは呼ばれない
      expect(queryClient.ensureQueryData).not.toHaveBeenCalled();
    });

    it('ensureQueryDataが失敗した場合、エラーをthrowする', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // ensureQueryDataがエラーをthrowするようにモック
      const mockError = new Error('Failed to fetch slide: Not Found');
      (queryClient.ensureQueryData as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        mockError
      );

      await expect(
        slideDetailLoader({ params: { slideId: 'slide-999' } } as any)
      ).rejects.toThrow('Failed to fetch slide: Not Found');

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to prefetch slide:',
        mockError
      );

      consoleErrorSpy.mockRestore();
    });

    it('ネットワークエラーの場合、エラーをthrowする', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const mockError = new Error('Network error');
      (queryClient.ensureQueryData as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        mockError
      );

      await expect(
        slideDetailLoader({ params: { slideId: 'slide-999' } } as any)
      ).rejects.toThrow('Network error');

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to prefetch slide:',
        mockError
      );

      consoleErrorSpy.mockRestore();
    });
  });
});
