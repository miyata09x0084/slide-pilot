/**
 * React Query Configuration
 * Centralizes QueryClient setup with default options
 */

import { QueryClient } from '@tanstack/react-query';
import type { DefaultOptions } from '@tanstack/react-query';

const queryConfig: DefaultOptions = {
  queries: {
    // データが古くなるまでの時間（30秒：高速化とデータ鮮度のバランス）
    staleTime: 30 * 1000,
    // キャッシュ時間（デフォルト: 10分）
    gcTime: 1000 * 60 * 10,
    // エラー時のリトライ設定
    retry: 1,
    // リフェッチの設定（マウント時に自動更新）
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
    refetchOnMount: true,
  },
  mutations: {
    // ミューテーションのエラーハンドリング
    retry: 0,
  },
};

export const queryClient = new QueryClient({
  defaultOptions: queryConfig,
});
