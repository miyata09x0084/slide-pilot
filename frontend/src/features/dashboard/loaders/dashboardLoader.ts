/**
 * dashboardLoader - React Router Loader with React Query prefetch
 * ルート遷移をブロックせずにバックグラウンドでプリフェッチを開始する
 *
 * 設計: prefetchQueryをawaitしない（fire-and-forget）ことで、
 * loaderがルート遷移を即座に完了させる。データはReact Queryの
 * キャッシュ経由でコンポーネントに届く。
 */

import { QueryClient } from '@tanstack/react-query';
import { getSlides } from '../api/get-slides';
import { getCachedAccessToken } from '@/lib/auth-session';

export const createDashboardLoader = (queryClient: QueryClient) => {
  return () => {
    // 未認証の場合はプリフェッチをスキップ（無駄な401リクエストを防止）
    // 認証ガードは ProtectedLayout (AuthGuard) が担当する
    if (!getCachedAccessToken()) return null;

    // キャッシュが新鮮ならリクエストを発火しない（staleTime内）
    // キャッシュが古い or 未取得なら、バックグラウンドでfetch開始
    queryClient.prefetchQuery({
      queryKey: ['slides', 20],
      queryFn: () => getSlides({ limit: 20 }),
    });

    return null;
  };
};
