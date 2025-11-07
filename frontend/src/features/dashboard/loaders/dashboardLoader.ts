/**
 * dashboardLoader - DashboardPageのReact Router Loader
 * React Queryのキャッシュを使用してスライド履歴を事前取得
 */

import { queryClient } from '@/lib/react-query';
import { slidesKeys } from '../hooks/useSlides';
import { api } from '@/lib/api-client';

export async function dashboardLoader() {
  const savedUser = localStorage.getItem('user');
  if (!savedUser) return null;

  try {
    const user = JSON.parse(savedUser);

    // React Queryのキャッシュを使用してデータを事前取得
    // ensureQueryDataはキャッシュがあればそれを返し、なければfetchする
    await queryClient.ensureQueryData({
      queryKey: slidesKeys.list(user.email, 20),
      queryFn: () => api.getSlides(user.email, 20),
    });

    // データはReact Queryから取得するため、nullを返す
    return null;
  } catch (err) {
    console.error('Failed to prefetch slides:', err);
    return null;
  }
}
