/**
 * dashboardLoader のテスト
 * React Router Loader によるスライド履歴取得
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { dashboardLoader } from '../loaders/dashboardLoader';

// グローバル fetch をモック
global.fetch = vi.fn();

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

describe('dashboardLoader', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('未ログイン状態', () => {
    it('localStorage に user がない場合、空配列を返す', async () => {
      const result = await dashboardLoader();

      expect(result).toEqual({ slides: [] });
      expect(global.fetch).not.toHaveBeenCalled();
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

    it('正常にスライド一覧を取得できる', async () => {
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

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ slides: mockSlides }),
      } as Response);

      const result = await dashboardLoader();

      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8001/api/slides?user_id=test%40example.com&limit=20'
      );
      expect(result).toEqual({ slides: mockSlides });
    });

    it('スライドが0件の場合、空配列を返す', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ slides: [] }),
      } as Response);

      const result = await dashboardLoader();

      expect(result).toEqual({ slides: [] });
    });

    it('デフォルトで http://localhost:8001/api を使用する', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ slides: [] }),
      } as Response);

      await dashboardLoader();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/slides?user_id=test%40example.com&limit=20')
      );
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

    it('fetch がネットワークエラーの場合、空配列を返す', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Network error')
      );

      const result = await dashboardLoader();

      expect(result).toEqual({ slides: [] });
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to fetch slides:',
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });

    it('response.ok が false の場合、空配列を返す', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        statusText: 'Internal Server Error',
      } as Response);

      const result = await dashboardLoader();

      expect(result).toEqual({ slides: [] });
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to fetch slides:',
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });

    it('response.json() が失敗した場合、空配列を返す', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      } as unknown as Response);

      const result = await dashboardLoader();

      expect(result).toEqual({ slides: [] });
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to fetch slides:',
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });

    it('レスポンスに slides プロパティがない場合、空配列を返す', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      const result = await dashboardLoader();

      expect(result).toEqual({ slides: [] });
    });

    it('レスポンスの slides が null の場合、空配列を返す', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ slides: null }),
      } as Response);

      const result = await dashboardLoader();

      expect(result).toEqual({ slides: [] });
    });
  });

  describe('パラメータエンコーディング', () => {
    it('特殊文字を含むメールアドレスが正しくエンコードされる', async () => {
      const specialUser = {
        name: 'Special User',
        email: 'test+tag@example.com',
        picture: 'https://example.com/avatar.jpg',
      };

      localStorage.setItem('user', JSON.stringify(specialUser));

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ slides: [] }),
      } as Response);

      await dashboardLoader();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('user_id=test%2Btag%40example.com')
      );
    });
  });

  describe('localStorage のパース', () => {
    it('localStorage の user が不正なJSONの場合、エラーをキャッチして空配列を返す', async () => {
      localStorage.setItem('user', '{invalid json}');

      const result = await dashboardLoader();

      expect(result).toEqual({ slides: [] });
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });
});
