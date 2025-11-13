/**
 * dashboardLoader - React Router Loader with React Query prefetch
 * ページ遷移前にスライド履歴をReact Queryキャッシュにプリフェッチ
 */

import { QueryClient } from '@tanstack/react-query';
import { getSlides } from '../api/get-slides';

export const createDashboardLoader = (queryClient: QueryClient) => {
  return async () => {
    // localStorageからユーザー情報取得（認証確認のみ）
    const savedUser = localStorage.getItem('user');
    if (!savedUser) return null;

    try {
      // React Queryキャッシュにプリフェッチ
      // prefetchQueryはエラーを無視するため、APIエラー時もnullを返す
      // user_idはJWTから自動取得されるため不要
      await queryClient.prefetchQuery({
        queryKey: ['slides', 20],
        queryFn: () => getSlides({ limit: 20 }),
      });

      return null; // Loaderからデータを返さない（キャッシュのみ使用）
    } catch (err) {
      // JSONパースエラーの場合のみここでキャッチ
      console.error('Failed to parse user data:', err);
      return null;
    }
  };
};
