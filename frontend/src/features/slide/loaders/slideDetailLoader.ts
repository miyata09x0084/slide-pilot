/**
 * slideDetailLoader - SlideDetailPageのReact Router Loader
 * React Queryのキャッシュを使用してスライド詳細を事前取得
 */

import type { LoaderFunctionArgs } from 'react-router-dom';
import { queryClient } from '@/lib/react-query';
import { slideKeys } from '../hooks/useSlideDetail';
import { api } from '@/lib/api-client';

export async function slideDetailLoader({ params }: LoaderFunctionArgs) {
  const { slideId } = params;

  if (!slideId) {
    throw new Error('Slide ID is required');
  }

  try {
    // React Queryのキャッシュを使用してデータを事前取得
    await queryClient.ensureQueryData({
      queryKey: slideKeys.detail(slideId),
      queryFn: () => api.getSlideDetail(slideId),
    });

    // データはReact Queryから取得するため、nullを返す
    return null;
  } catch (err) {
    console.error('Failed to prefetch slide:', err);
    throw err; // React Routerのエラーバウンダリで処理
  }
}
