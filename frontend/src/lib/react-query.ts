/**
 * React Query Configuration
 * Centralizes QueryClient setup with default options
 */

import { QueryClient } from '@tanstack/react-query';
import type { DefaultOptions } from '@tanstack/react-query';

const queryConfig: DefaultOptions = {
  queries: {
    // データが古くなるまでの時間（デフォルト: 5分）
    staleTime: 1000 * 60 * 5,
    // キャッシュ時間（デフォルト: 10分）
    gcTime: 1000 * 60 * 10,
    // エラー時のリトライ設定
    retry: 1,
    // リフェッチの設定
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
  },
  mutations: {
    // ミューテーションのエラーハンドリング
    retry: 0,
  },
};

export const queryClient = new QueryClient({
  defaultOptions: queryConfig,
});
