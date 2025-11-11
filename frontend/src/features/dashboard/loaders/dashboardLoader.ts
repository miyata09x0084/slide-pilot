/**
 * dashboardLoader - React Router Loader with React Query prefetch
 * ページ遷移前にスライド履歴をReact Queryキャッシュにプリフェッチ
 */

import { QueryClient } from '@tanstack/react-query';
import { getSlides } from '../api/get-slides';

export const createDashboardLoader = (queryClient: QueryClient) => {
  return async () => {
    // localStorageからユーザー情報取得
    const savedUser = localStorage.getItem('user');
    if (!savedUser) return null;

    try {
      const user = JSON.parse(savedUser);

      // React Queryキャッシュにプリフェッチ
      // prefetchQueryはエラーを無視するため、APIエラー時もnullを返す
      await queryClient.prefetchQuery({
        queryKey: ['slides', user.email, 20],
        queryFn: () => getSlides({ user_id: user.email, limit: 20 }),
      });

      return null; // Loaderからデータを返さない（キャッシュのみ使用）
    } catch (err) {
      // JSONパースエラーの場合のみここでキャッチ
      console.error('Failed to parse user data:', err);
      return null;
    }
  };
};
