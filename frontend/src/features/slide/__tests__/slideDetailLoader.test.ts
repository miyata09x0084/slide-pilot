/**
 * slideDetailLoader のテスト
 * React Router Loader によるスライド詳細取得
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { slideDetailLoader } from '../loaders/slideDetailLoader';

// グローバル fetch をモック
global.fetch = vi.fn();

describe('slideDetailLoader', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('正常系', () => {
    it('正常にスライド詳細を取得できる', async () => {
      const mockData = {
        slide_id: 'slide-123',
        title: 'テストスライド',
        created_at: '2025-11-06T00:00:00Z',
        pdf_url: 'https://example.com/slide.pdf',
      };

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      } as Response);

      const result = await slideDetailLoader({
        params: { slideId: 'slide-123' },
      } as any);

      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8001/api/slides/slide-123/markdown'
      );
      expect(result).toEqual({
        slide: {
          id: 'slide-123',
          title: 'テストスライド',
          topic: 'テストスライド',
          created_at: '2025-11-06T00:00:00Z',
          pdf_url: 'https://example.com/slide.pdf',
        },
      });
    });

    it('pdf_url が存在しない場合も正常に処理できる', async () => {
      const mockData = {
        slide_id: 'slide-456',
        title: 'PDFなしスライド',
        created_at: '2025-11-06T01:00:00Z',
      };

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      } as Response);

      const result = await slideDetailLoader({
        params: { slideId: 'slide-456' },
      } as any);

      expect(result.slide.pdf_url).toBeUndefined();
      expect(result.slide.id).toBe('slide-456');
    });

    it('デフォルトで http://localhost:8001/api を使用する', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          slide_id: '1',
          title: 'Test',
          created_at: '2025-11-06T00:00:00Z',
        }),
      } as Response);

      await slideDetailLoader({
        params: { slideId: '1' },
      } as any);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('http://localhost:8001/api/slides')
      );
    });
  });

  describe('異常系', () => {
    it('slideId が未指定の場合、エラーをthrowする', async () => {
      await expect(
        slideDetailLoader({ params: {} } as any)
      ).rejects.toThrow('Slide ID is required');

      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('fetchが失敗した場合、エラーをthrowする', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found',
      } as Response);

      await expect(
        slideDetailLoader({ params: { slideId: 'slide-999' } } as any)
      ).rejects.toThrow('Failed to fetch slide: Not Found');

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to fetch slide:',
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });

    it('ネットワークエラーの場合、エラーをthrowする', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Network error')
      );

      await expect(
        slideDetailLoader({ params: { slideId: 'slide-999' } } as any)
      ).rejects.toThrow('Network error');

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to fetch slide:',
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });

    it('response.json() が失敗した場合、エラーをthrowする', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      } as unknown as Response);

      await expect(
        slideDetailLoader({ params: { slideId: 'slide-999' } } as any)
      ).rejects.toThrow('Invalid JSON');

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to fetch slide:',
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });
  });
});
